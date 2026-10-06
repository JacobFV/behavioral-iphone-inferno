#!/usr/bin/env python3
"""Reproduce raw timing and milestone audit without changing source reports."""
import argparse, hashlib, json, re, shutil, subprocess, sys
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('repository',type=Path);p.add_argument('--output',type=Path,required=True);a=p.parse_args();root=a.repository.resolve();out=a.output.resolve();out.mkdir(parents=True,exist_ok=True)
def sha(b):return hashlib.sha256(b).hexdigest()
def load(p):return json.loads(p.read_bytes())
def save(p,d):p.write_text(json.dumps(d,indent=2)+'\n')
def digest(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(4*1024*1024),b''):h.update(b)
 return h.hexdigest()
def rows(p):
 result=[];offset=0
 for line in p.read_bytes().splitlines(keepends=True):
  result.append((json.loads(line),{'source':str(p),'byte_start':offset,'byte_end':offset+len(line),'sha256':sha(line)}));offset+=len(line)
 return result
def one(rs,pred):
 r=[(x,ref) for x,ref in rs if pred(x)];assert len(r)==1,len(r);return {'raw':r[0][0],'reference':r[0][1]}
def command(x):return json.loads(x['raw'])
def refs(x):
 if isinstance(x,dict):
  if all(k in x for k in ['byte_start','byte_end','sha256']):yield x
  for v in x.values():yield from refs(v)
 elif isinstance(x,list):
  for v in x:yield from refs(v)
source_hashes={}
for name in ['launch-timing.py','boot_milestones.py','boot.py','qmp_control.py','probe_journey.py']:
 src=root/'companion'/name;target=out/'source'/name;target.parent.mkdir(exist_ok=True);shutil.copyfile(src,target);source_hashes[name]=sha(src.read_bytes())
runs=[];common=None
for n in [39,40]:
 reportdir=root/f'.local-build/reports/app-boot-{n}';dest=out/str(n);dest.mkdir(exist_ok=True);retained={}
 for name in ['serial.log','control-transcript.jsonl','qmp-transcript.jsonl','serial-input-transcript.jsonl','report.json','root-overlay.json','stopped-disk-hashes.json','counter-tap-request.json','build-manifest.json','command.json']:
  src=reportdir/name;shutil.copyfile(src,dest/name);retained[name]={'original':str(src),'sha256':sha(src.read_bytes()),'bytes':src.stat().st_size}
 subprocess.run([sys.executable,str(out/'source/launch-timing.py'),'--report',str(reportdir),'--output',str(out/f'launch-{n}.json')],check=True,capture_output=True)
 timing=load(out/f'launch-{n}.json');assert timing['status']=='complete';data=(dest/'serial.log').read_bytes();assert timing['serial']['sha256']==sha(data)
 timingrefs=list(refs(timing))
 for ref in timingrefs:assert sha(data[ref['byte_start']:ref['byte_end']])==ref['sha256']
 arrival_src=reportdir/'event-arrivals/observations.jsonl';shutil.copyfile(arrival_src,dest/'arrivals.jsonl');retained['arrivals.jsonl']={'original':str(arrival_src),'sha256':sha(arrival_src.read_bytes()),'bytes':arrival_src.stat().st_size}
 report=load(dest/'report.json');overlay=load(dest/'root-overlay.json');assert report['exit_code']==0 and not report.get('error');assert report['milestone_source_sha256']==source_hashes['boot_milestones.py']
 milestone_refs=[]
 for name,m in report['milestones'].items():
  assert m['state']=='observed'
  for ref in m['evidence']:
   raw=data[ref['byte_start']:ref['byte_end']];assert ref['sha256']==sha(data) and raw.rstrip(b'\r\n').decode()==ref['text'];milestone_refs.append({'milestone':name,**ref,'slice_sha256':sha(raw)})
 assert report['ios_booted'] is None and report['app_executed'] is True
 controls=rows(dest/'control-transcript.jsonl');qmp=rows(dest/'qmp-transcript.jsonl');inputs=rows(dest/'serial-input-transcript.jsonl');counter=load(dest/'counter-tap-request.json')
 before=one(controls,lambda x:command(x)['execute']=='probe-capture-before');after=one(controls,lambda x:command(x)['execute']=='probe-capture-after');finish=one(controls,lambda x:command(x)['execute']=='finish-run')
 for item in [before,after,finish]:assert command(item['raw'])['arguments']=={}
 taps=[(x,r) for x,r in controls if command(x)['execute']=='guest-hid-gesture' and command(x)['arguments'].get('kind')=='tap' and command(x)['arguments'].get('x')==counter['x'] and command(x)['arguments'].get('y')==counter['y']]
 assert len(taps)==1 and command(taps[0][0])['arguments']==counter
 sent=one(inputs,lambda x:x.get('stage')=='before-send' and x.get('request_id')==counter['request_id'])
 assert before['raw']['time']<sent['raw']['time']<after['raw']['time']<finish['raw']['time']
 arrivals=rows(dest/'arrivals.jsonl');arrival_refs=[]
 for event in ['appeared','tap']:
  marker=('INFERNO_UIKIT_PROBE_V1 event='+event+' count='+('0' if event=='appeared' else '1')).encode();offset=data.index(marker);observed=one(arrivals,lambda x:x['byte_start']==offset);v=observed['raw'];assert not v['preexisting'];assert data[v['byte_start']:v['byte_end']][:-1].hex()==v['raw_hex'];arrival_refs.append(observed)
 assert arrival_refs[0]['raw']['observed_time']<before['raw']['time']<sent['raw']['time']<arrival_refs[1]['raw']['observed_time']<after['raw']['time']
 assert finish['raw']['response']['return']['finish_requested'] and after['raw']['response']['return']['state']=='completed'
 captures=[]
 for role in ['probe-before','probe-after']:
  path=reportdir/(role+'.ppm');raw=path.read_bytes();h=re.match(rb'P6\s+(\d+)\s+(\d+)\s+255\s',raw);assert h;w,height=map(int,h.groups());assert(w,height)==(828,1792) and len(raw)-h.end()==w*height*3
  assert sha(raw)==report['probe_journey']['captures'][role]['sha256']
  req=one(qmp,lambda x:x['direction']=='send' and command(x).get('execute')=='screendump' and command(x).get('arguments',{}).get('filename')==str(path));qid=command(req['raw'])['id'];reply=one(qmp,lambda x:x['direction']=='receive' and command(x).get('id')==qid);assert command(reply['raw'])['return']=={}
  captures.append({'role':role,'path':str(path),'sha256':sha(raw),'width':w,'height':height,'request':req,'reply':reply})
 quitreq=one(qmp,lambda x:x['direction']=='send' and command(x).get('execute')=='quit');qid=command(quitreq['raw'])['id'];quitreply=one(qmp,lambda x:x['direction']=='receive' and command(x).get('id')==qid);assert command(quitreply['raw'])['return']=={}
 stopped=load(dest/'stopped-disk-hashes.json');assert len(stopped)==7
 for item in stopped.values():assert Path(item['path']).stat().st_size==item['bytes'] and digest(Path(item['path']))==item['sha256']
 assert overlay['backing_after_stop']['unchanged'] and overlay['backing_after_stop']['layers']==overlay['dependencies']
 for dep in overlay['dependencies']:
  s=Path(dep['path']).stat();assert s.st_size==dep['bytes'] and not(s.st_mode&0o222)
 identity={k:report[k] for k in ['binary_sha256','profile_sha256','runner_sha256','probe_journey_source_sha256','auxiliary_base']};identity['dependencies']=overlay['dependencies'];identity['backing_report']=overlay['backing_report']
 if common is None:common=identity
 else:assert common==identity
 runs.append({'boot':n,'boot_uuid':timing['boot_uuid'],'pid':timing['app_pid'],'timing_raw_references_verified':len(timingrefs),'retained':retained,'milestone_raw_references':milestone_refs,'host_observed_marker_arrivals':arrival_refs,'operator_before':before,'one_counter_tap':{'raw':taps[0][0],'reference':taps[0][1]},'serial_transmission':sent,'operator_after':after,'finish_run':finish,'captures':captures,'quit_request':quitreq,'quit_reply':quitreply,'all_seven_stopped_hashes_freshly_verified':True,'dependency_scope':'Recorded pre/post identity and hash equality; current size/read-only mode independently checked. This audit does not repeat the 32GiB ancestor hash.'})
assert runs[0]['boot_uuid']!=runs[1]['boot_uuid']
save(out/'audit.json',{'runs':runs,'common_identity':common,'source_hashes':source_hashes,'milestone_audit':'All finalized serial byte references and frame hashes match actual data. Independent raw mailbox and QMP requests/replies corroborate before/after/finish and normal quit.','limits':['Two concurrent controlled VM runs, no reliability distribution or native-device timing claim.','Timing measures captured guest hook ticks, not frame presentation or host log arrival.','Visual interpretation remains the parent operator review; this audit checks raw PPM dimensions/hash, not pixels semantically.','Milestone observer itself trusts in-memory operator flags and capture hashes; this independent audit additionally checks raw control/QMP transcripts.','TCP peer PID is unauthenticated; relay verifies claimed PID/UID/executable.'],'proposed_next_gap':'A reusable read-only verify-report CLI that replays raw serial/control/QMP and timing checks into a portable source-hashed evidence bundle. Current independent audits are per-run scripts; milestone observation does not itself verify external transcript chronology. No implementation authorized here.'})
