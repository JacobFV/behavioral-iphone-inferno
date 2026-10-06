#!/usr/bin/env python3
"""Read-only actual51 trace snapshot and bounded comparison; no guest actions."""
import argparse,collections,hashlib,json,pathlib,time
p=argparse.ArgumentParser();p.add_argument('repository',type=pathlib.Path);a=p.parse_args();root=a.repository.resolve();src=root/'.local-build/reports/app-boot-51';out=pathlib.Path(__file__).resolve().parent
sha=lambda b:hashlib.sha256(b).hexdigest()
def write(name,b): (out/name).write_bytes(b)
def load(name):return json.loads((out/name).read_bytes())
provenance={}
for source,name in [('counter-001/submission.json','counter-submission.json'),('trace-after-counter-review.json','trace-after-counter-review.json'),('display-trace-control.jsonl','display-trace-control-prefix.jsonl'),('qmp-transcript.jsonl','qmp-prefix.jsonl'),('control-transcript.jsonl','control-prefix.jsonl'),('serial-input-transcript.jsonl','serial-input-prefix.jsonl'),('report.json','report-snapshot.json')]:
 data=(src/source).read_bytes();write(name,data);provenance[name]={'original':str(src/source),'bytes':len(data),'sha256':sha(data),'scope':'snapshot; original live file may grow or be rewritten'}
sub=load('counter-submission.json');before=sub['trace_before'];after=load('trace-after-counter-review.json')['checkpoint'];assert before['size']==45283 and sub['trace_after']['size']==45283 and after['size']==90264
stat=(src/'guest-errors.log').stat();assert(stat.st_dev,stat.st_ino)==(before['device'],before['inode'])==(after['device'],after['inode'])
with(src/'guest-errors.log').open('rb')as f:data=f.read(after['size'])
assert len(data)==after['size'];write('guest-errors-prefix.log',data);provenance['guest-errors-prefix.log']={'original':str(src/'guest-errors.log'),'bytes':len(data),'sha256':sha(data),'scope':'exact byte prefix through after-review checkpoint'}
def rows(raw):
 offset=0;result=[]
 for line in raw.split(b'\n'):
  if offset==len(raw):break
  record=line+(b'\n'if offset+len(line)<len(raw)else b'');result.append((line.rstrip(b'\r'),{'byte_start':offset,'byte_end':offset+len(record),'sha256':sha(record)}));offset+=len(record)
 return result
def events(raw,start,end):
 result=[]
 for line,ref in rows(raw):
  if start<=ref['byte_start']<end and line.startswith(b'apple_adp_'):
   assert ref['byte_end']<=end;parts=line.decode().split();result.append({'event':parts[0],'fields':dict(x.split('=',1)for x in parts[1:]),'reference':ref})
 return result
def region(raw,start,end):
 es=events(raw,start,end);counts=collections.Counter(x['event']for x in es);active=False;cycles=0;draws=[];sources=[];unknown=collections.Counter()
 for x in es:
  n,f=x['event'],x['fields']
  if n=='apple_adp_bh':
   if f['phase']=='enter':assert not active;active=True;draws=[]
   else:assert active and draws==[('0','drawn'),('1','disabled')];active=False;cycles+=1
  if n=='apple_adp_pipe':
   assert active;draws.append((f['pipe'],f['outcome']))
   if f['outcome']=='drawn':sources.append(f['source'])
  if n=='apple_adp_unknown_mmio':unknown[tuple((k,f[k])for k in ['block','pipe','write','offset','value'])]+=1
 assert not active and counts.get('apple_adp_submit',0)==cycles
 return {'bytes':[start,end],'sha256':sha(raw[start:end]),'counts':dict(counts),'complete_cycles':cycles,'draw_sources':sources,'unknown_mmio':[{'fields':dict(k),'count':v}for k,v in unknown.items()]},es
counter,eventrefs=region(data,before['size'],after['size']);assert counter['complete_cycles']==7
j=[json.loads(line)for line in(out/'display-trace-control-prefix.jsonl').read_text().splitlines()];qrows=[(json.loads(line),ref)for line,ref in rows((out/'qmp-prefix.jsonl').read_bytes())];proof=[]
for x in j:
 if 'response'not in x:continue
 matches=[(v,r)for v,r in qrows if v['direction']=='receive' and json.loads(v['raw']).get('id')==x['response']['id']];assert len(matches)==1 and json.loads(matches[0][0]['raw'])==x['response'] and x['response']['return']=={}
 sent=[(v,r)for v,r in qrows if v['direction']=='send' and json.loads(v['raw']).get('id')==x['response']['id']];assert len(sent)==1 and json.loads(sent[0][0]['raw'])['arguments']=={'name':x['event'],'enable':x['stage']=='after-enable'};proof.append({'trace_control':x,'qmp_send':sent[0],'qmp_reply':matches[0]})
enables=[x for x in j if x['stage']=='after-enable'];disables=[x for x in j if x['stage']=='after-disable'];assert len(enables)==len(disables)==7 and j[-1]['all_disabled'];assert max(x['time']for x in enables)<before['wall_time']<after['wall_time']<min(x['time']for x in disables)
serial=(src/'serial.log').read_bytes();selected=[]
for line,ref in rows(serial):
 if sub['request_id'].encode()in line or line==b'INFERNO_UIKIT_PROBE_V1 event=tap count=1' or (line.startswith(b'INFERNO_EVENT_RELAY_RAW ')and line.endswith(b' tap 1')):selected.append({'text':line.decode(),'reference':ref})
assert any(x['text']=='INFERNO_UIKIT_PROBE_V1 event=tap count=1'for x in selected)
comparisons=[]
for boot,folder,rawname,lo,hi in [(50,'display-mmio-50-actual','guest-errors-prefix.log',39790,85322)]:
 path=root/'companion/evidence'/folder/rawname;raw=path.read_bytes();summary,_=region(raw,lo,hi);summary.update(boot=boot,raw_source=str(path),raw_source_sha256=sha(raw));comparisons.append(summary)
report=load('report-snapshot.json');assert report['exit_code']==0 and report.get('error')is None
quit_requests=[(v,r)for v,r in qrows if v['direction']=='send' and json.loads(v['raw']).get('execute')=='quit'];assert len(quit_requests)==1;quitid=json.loads(quit_requests[0][0]['raw'])['id'];quit_replies=[(v,r)for v,r in qrows if v['direction']=='receive' and json.loads(v['raw']).get('id')==quitid];assert len(quit_replies)==1 and json.loads(quit_replies[0][0]['raw'])==report['quit_response'] and report['quit_response']['return']=={}
shutdown=[(v,r)for v,r in qrows if v['direction']=='receive' and json.loads(v['raw']).get('event')=='SHUTDOWN'];assert len(shutdown)==1 and json.loads(shutdown[0][0]['raw'])['data']=={'guest':False,'reason':'host-qmp-quit'}
input_rows=[json.loads(x)for x in(out/'serial-input-prefix.jsonl').read_text().splitlines()];assert all(x.get('operation')not in('OPEN','SAMPLE')for x in input_rows)
prior_path=root/'companion/evidence/display-mmio-50-actual/report-snapshot.json';prior=json.loads(prior_path.read_bytes());assert prior['binary_sha256']==report['binary_sha256'] and prior['profile_sha256']==report['profile_sha256'] and prior['root_overlay']['backing_report_sha256']==report['root_overlay']['backing_report_sha256'] and prior['root_overlay']['dependencies']==report['root_overlay']['dependencies'];assert report['probe_journey']['completed']
result={'boot':51,'same_baseline50':{'source':str(prior_path),'sha256':sha(prior_path.read_bytes()),'binary_sha256':report['binary_sha256'],'backing_report':report['root_overlay']['backing_report'],'backing_report_sha256':report['root_overlay']['backing_report_sha256'],'dependency_identity_comparison':'exact equality'},'captured_time':time.time(),'live_snapshot':False,'counter':counter,'cycle_references':[e for e in eventrefs if e['event'] in ('apple_adp_submit','apple_adp_bh','apple_adp_pipe')],'trace_control_qmp_proof':proof,'window_disable':j[-1],'normal_shutdown':{'quit_request':quit_requests[0],'quit_reply':quit_replies[0],'shutdown':shutdown[0],'exit_code':report['exit_code']},'checkpoint_scope':'File-visible boundaries only. Trace backend lacks timestamps and may buffer output; no exact device-event time or individual draw attribution to a tap.','serial_counter':{'prefix_bytes':len(serial),'prefix_sha256':sha(serial),'original':str(src/'serial.log'),'records':selected},'comparisons':comparisons,'identity':{k:report.get(k)for k in ['binary_sha256','profile_sha256','runner_sha256','build_manifest']},'limits':['Complete draw cycles are compared over file-visible counter brackets only. This is a bounded observed difference, not proof of a fix or cause.','Visual counter0→1 review is the parent operator evidence, not inferred from trace rows or marker alone.','51 repeats the same frozen55 baseline as50; bounded successes do not establish reliability or a display-stall fix.','No SAMPLE or OPEN commands occur in51 retained input records; no runtime controls were performed during this audit.']}
write('audit.json',(json.dumps(result,indent=2)+'\n').encode());write('provenance.json',(json.dumps({'files':provenance,'audit_source_sha256':sha(pathlib.Path(__file__).read_bytes())},indent=2)+'\n').encode());print(json.dumps({'counter':counter['counts'],'comparisons':[(x['boot'],x['complete_cycles'])for x in comparisons]}))
