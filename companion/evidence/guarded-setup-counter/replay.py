#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
# Host-only actual-frame and private Unix transport replay; no guest actions.
from pathlib import Path
import importlib.util,sys,json,hashlib,tempfile,socket,threading,time,os
from PIL import Image
import argparse
ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--candidate',type=Path,required=True);ap.add_argument('--retained-repository',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);args=ap.parse_args()
w=args.candidate.resolve(strict=True);main=args.retained_repository.resolve(strict=True);sys.path.insert(0,str(w/'companion'))
sp=importlib.util.spec_from_file_location('g',w/'companion/guarded-setup-counter.py');g=importlib.util.module_from_spec(sp);sp.loader.exec_module(g)
out=args.output.resolve();out.mkdir(parents=True,exist_ok=False);manifest=w/'companion/evidence/guarded-setup-counter/references.json';tmp=Path(tempfile.mkdtemp(prefix='guarded-reference-replay-'));(tmp/'guarded').mkdir();(tmp/'guarded/references.json').write_bytes(manifest.read_bytes())
for n in ('owned-extended-69-visual','owned-strict-70-visual'):(tmp/n).symlink_to(main/'companion/evidence'/n,target_is_directory=True)
refs=g.references(tmp/'guarded/references.json',g.sha(manifest.read_bytes()));results=[]
for run,sub,expected in [(69,'after-alert/settled.png','overlay'),(69,'after-setup-not-now/settled.png','zero'),(70,'after-alert/settled.png','overlay'),(70,'after-setup-not-now/settled.png','zero'),(70,'beta-settled/before.png','unknown'),(70,'beta-settled/settled.png','unknown'),(70,'after-counter/settled.png','unknown'),(70,'boot-view/before.png','unknown'),(68,'stopwatch-view/settled.png','unknown')]:
 p=main/f'.local-build/reports/app-boot-{run}'/sub;state=g.classify(p,refs);assert state==expected,(p,state);results.append({'path':str(p),'sha256':g.sha(p.read_bytes()),'state':state,'expected':expected,'kind':'actual retained frame'})
base=Image.open(main/'.local-build/reports/app-boot-70/after-setup-not-now/settled.png').copy();overlay=Image.open(main/'.local-build/reports/app-boot-70/after-alert/settled.png').copy()
for name,im,expected in [('synthetic-alpha-blend',Image.blend(base,overlay,.5),'unknown'),('synthetic-clock-change',base.copy(),'zero')]:
 if name=='synthetic-clock-change':im.paste((255,0,255),(0,0,832,90))
 p=tmp/(name+'.png');im.save(p);state=g.classify(p,refs);assert state==expected;results.append({'kind':'synthetic pixel mutation, not guest execution','name':name,'state':state,'sha256':g.sha(p.read_bytes())})
qmp=main/'.local-build/reports/app-boot-70/probe-before.ppm'
try:g.classify(qmp,refs);raise AssertionError('QMP accepted')
except ValueError:results.append({'path':str(qmp),'sha256':g.sha(qmp.read_bytes()),'state':'rejected dimensions/mode','kind':'actual QMP frame'})
# Replay initial prefix only; no retroactive claim that runtime guarded sequence ran.
b=(main/'.local-build/reports/app-boot-70/serial.log').read_bytes();cut=b.index(b'INFERNO_HID_V1 427c43');rdir=tmp/'report';rdir.mkdir();(rdir/'serial.log').write_bytes(b[:cut]);ident=g.identity(rdir,'8F02ACA8-4597-4153-A965-4D27829C7DBA');assert ident['pid']==259
(out/'frame-replay.json').write_text(json.dumps({'scope':'Offline actual-frame replay plus explicitly synthetic negatives; no guest control','manifest_sha256':g.sha(manifest.read_bytes()),'crop_pixels':832*1300,'results':results,'actual_initial_identity_prefix':ident,'prefix_end':cut},indent=2)+'\n')
# Existing SerialGestureTransport with a real private Unix socket; no QEMU/iOS.
q=g.qmp_control;d=Path(tempfile.mkdtemp(prefix='guarded-deadline-fixture-'));server=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM);server.bind(str(d/'serial.sock'));server.listen();t=q.SerialGestureTransport(d/'serial.sock',d);t.connect();peer,_=server.accept();peer.settimeout(.1)
def args(n):return {'kind':'tap','request_id':f'{n:032x}','duration_ms':150,'x':11028,'y':18432}
a=args(1);a['send_deadline_monotonic']=time.monotonic()+2;expected=q.gesture_line(a);first=t.transmit(a);assert peer.recv(200)==expected and first['transmission']=='written-to-serial-socket'
expired=args(2);expired['send_deadline_monotonic']=time.monotonic()-1
try:q.validate({'execute':'guest-hid-gesture','arguments':expired,'created':time.time()});raise AssertionError('expired accepted')
except ValueError as e:expired_error=str(e)
original=t._record
def delayed(record):
 original(record)
 if record.get('stage')=='before-send':time.sleep(.05)
t._record=delayed;a=args(3);a['send_deadline_monotonic']=time.monotonic()+.02;last=t.transmit(a);assert last['transmission']=='rejected-deadline-before-write' and last['bytes_sent']==0
try:peer.recv(200);raise AssertionError('late bytes observed')
except socket.timeout:pass
t._record=original;a=args(4);expected=q.gesture_line(a);default=t.transmit(a);assert peer.recv(200)==expected
try:t.transmit(args(3));raise AssertionError('replay accepted')
except ValueError as e:duplicate=str(e)
t.close();peer.close();server.close()
(out/'deadline-fixture.json').write_text(json.dumps({'scope':'Real private Unix socket, existing transport, no QEMU or guest. Injected50ms journal delay solely fixture case.','timely':first,'expired_queued_validation':expired_error,'expired_after_journal':last,'expired_no_peer_bytes':True,'replay_rejected':duplicate,'default_without_deadline':default,'journal_path':str(d/'serial-input-transcript.jsonl'),'journal_sha256':g.sha((d/'serial-input-transcript.jsonl').read_bytes())},indent=2)+'\n');(out/'deadline-fixture-serial.jsonl').write_bytes((d/'serial-input-transcript.jsonl').read_bytes());print('frame and real socket deadline checks passed')
