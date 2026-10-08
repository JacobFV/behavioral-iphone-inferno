#!/usr/bin/env python3
import json,hashlib,stat
from pathlib import Path
ROOT=Path('/home/brandonin/Documents/behavioral-iphone-inferno');R=ROOT/'.local-build/reports/app-boot-91';V=ROOT/'companion/evidence/imported-fixture-91-visual';pins={}
def read(p):
 b=p.read_bytes();pins[str(p)]={'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()};return b
def js(p):return json.loads(read(p))
controls=[json.loads(x) for x in read(R/'control-transcript.jsonl').splitlines()];wire=[json.loads(x) for x in read(R/'serial-input-transcript.jsonl').splitlines()];qmp=[json.loads(x) for x in read(R/'qmp-transcript.jsonl').splitlines()]
names=['unlock-001','unlock-002','beta-close','setup-not-now','counter-tap'];actions=[]
for name in names:
 s=js(V/name/'submission.json');request=s['request_id'];c=[x for x in controls if json.loads(x['raw']).get('arguments',{}).get('request_id')==request];assert len(c)==1
 b=[x for x in wire if x['stage']=='before-send' and x['request_id']==request];a=[x for x in wire if x['stage']=='after-send' and x['response']['request_id']==request];assert len(b)==len(a)==1 and b[0]['raw']==s['expected_serial_wire'];assert a[0]['response']['transmission']=='written-to-serial-socket'
 actions.append({'name':name,'request_id':request,'submission_start':s['started_time'],'mailbox_created':json.loads(c[0]['raw'])['created'],'serial_before_send':b[0]['time'],'write_begin_monotonic':a[0]['response']['write_begin_monotonic'],'write_end_monotonic':a[0]['response']['write_end_monotonic'],'wire':b[0]['raw']})
intervals=[]
for i,(name,target) in enumerate([('unlock-gap',396),('unlock2-to-beta',43),('beta-to-setup',18),('setup-to-counter',13)]):
 x,y=actions[i:i+2];v={key:y[key]-x[key] for key in ['submission_start','mailbox_created','serial_before_send','write_begin_monotonic']};intervals.append({'name':name,'target_seconds':target,'actual_intervals_seconds':v,'submission_start_minus_target':v['submission_start']-target})
r=js(R/'report.json');assert r['attempt_completed'] is True and r['exit_code']==0 and r.get('error') is None and r['probe_journey']['completed'] is True
ret=js(R/'stopped-disk-hashes.json');v=js(R/'stopped-disk-hashes-verification.json');assert len(ret)==7 and v['failed_attempt_opt_in'] is False
files={}
for name,item in ret.items():
 s=Path(item['path']).lstat();assert s.st_size==item['bytes'] and stat.S_ISREG(s.st_mode)
 files[name]={'path':item['path'],'bytes':s.st_size,'mode':oct(s.st_mode),'device':s.st_dev,'inode':s.st_ino,'recorded_sha256_not_rehashed':item['sha256']}
for pid in [1195600,1196912]:assert not Path('/proc',str(pid)).exists()
serial=read(R/'serial.log');eventrefs=[];off=0
for line in serial.splitlines(keepends=True):
 if any(x in line for x in [b'INFERNO_EVENT_RELAY_RAW',b'INFERNO_EVENT_VALIDATED',b'INFERNO_UIKIT_PROBE_V1',b'INFERNO_HID_ACK']):eventrefs.append({'byte_start':off,'text':line.rstrip(b'\r\n').decode('ascii'),'sha256':hashlib.sha256(line).hexdigest()})
 off+=len(line)
assert sum('INFERNO_EVENT_RELAY_RAW' in x['text'] and ' tap 1' in x['text'] for x in eventrefs)==1
requests=[json.loads(x['raw']) for x in controls];assert not any(x.get('execute')=='swapwait-cpu-window' for x in requests)
assert not any(json.loads(x['raw']).get('execute')=='human-monitor-command' and 'cpu' in json.loads(x['raw']).get('arguments',{}).get('command-line','') for x in qmp if x['direction']=='send')
journey=js(Path('/tmp/inferno-fixture91-independent-journey.json'));assert journey['status']=='verified'
for n in ['probe-before.png','probe-after.png']:read(V/n)
result={'scope':'Independent raw host timing, strict verifier replay, manually reviewed retained pixels and normal-stop/retention metadata; no disk payload rehash','inputs':pins,'actions':actions,'intervals':intervals,'elapsed_seconds':r['elapsed_seconds'],'strict':{'status':journey['status'],'boot_uuid':journey['boot_uuid'],'app_pid':journey['app_pid'],'chronology_basis':journey['chronology_basis']},'event_references':eventrefs,'seven_file_metadata':files,'cpu_window_submissions':0,'pids_absent':[1195600,1196912],'visual_review':'Personally viewed retained probe-before.png counter0 and probe-after.png counter1; these are reviewed actual screenshots, not inferred from ACK.','limits':['Submission start, mailbox creation and serial write are distinct host boundaries; no guest event time subtracted from host epoch.','Short43/18/13second targets missed by16.331195/8.410700/45.702257seconds at submission-start boundary.','Healthy interaction does not test the intended short-delay condition or resolve intermittent failures.','Retention hashes are referenced with current file metadata; no full image hash repeated.']}
for p,x in pins.items():assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==x['sha256']
Path(__file__).with_name('audit.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(intervals,indent=2))
