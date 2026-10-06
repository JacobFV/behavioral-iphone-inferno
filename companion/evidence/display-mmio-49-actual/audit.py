#!/usr/bin/env python3
"""Read-only actual49 trace snapshot and bounded comparison; no guest actions."""
import argparse,collections,hashlib,json,pathlib,time
p=argparse.ArgumentParser();p.add_argument('repository',type=pathlib.Path);a=p.parse_args();root=a.repository.resolve();src=root/'.local-build/reports/app-boot-49';out=pathlib.Path(__file__).resolve().parent
sha=lambda b:hashlib.sha256(b).hexdigest()
def write(name,b): (out/name).write_bytes(b)
def load(name):return json.loads((out/name).read_bytes())
provenance={}
for source,name in [('counter-001/submission.json','counter-submission.json'),('trace-after-counter-review.json','trace-after-counter-review.json'),('display-trace-control.jsonl','display-trace-control-prefix.jsonl'),('qmp-transcript.jsonl','qmp-prefix.jsonl'),('control-transcript.jsonl','control-prefix.jsonl'),('serial-input-transcript.jsonl','serial-input-prefix.jsonl'),('report.json','report-snapshot.json')]:
 data=(src/source).read_bytes();write(name,data);provenance[name]={'original':str(src/source),'bytes':len(data),'sha256':sha(data),'scope':'snapshot; original live file may grow or be rewritten'}
sub=load('counter-submission.json');before=sub['trace_before'];after=load('trace-after-counter-review.json')['checkpoint'];assert before['size']==39601 and sub['trace_after']['size']==39601 and after['size']==84582
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
for boot,folder,rawname,lo,hi in [(45,'display-mmio-45-actual/counter-window','guest-errors-final.log',284895,324709),(46,'display-mmio-46-actual','guest-errors.log',45244,89883),(47,'display-stall-47-actual','guest-errors-prefix.log',40424,46108)]:
 path=root/'companion/evidence'/folder/rawname;raw=path.read_bytes();summary,_=region(raw,lo,hi);summary.update(boot=boot,raw_source=str(path),raw_source_sha256=sha(raw));comparisons.append(summary)
report=load('report-snapshot.json');result={'boot':49,'captured_time':time.time(),'live_snapshot':True,'counter':counter,'event_references':eventrefs,'trace_control_qmp_proof':proof,'window_disable':j[-1],'checkpoint_scope':'File-visible boundaries only. Trace backend lacks timestamps and may buffer output; no exact device-event time or individual draw attribution to a tap.','serial_counter':{'prefix_bytes':len(serial),'prefix_sha256':sha(serial),'original':str(src/'serial.log'),'records':selected},'comparisons':comparisons,'identity':{k:report.get(k)for k in ['binary_sha256','profile_sha256','runner_sha256','build_manifest']},'limits':['Seven complete rendering cycles in49 bracket; six in45, seven in46, zero in47 counterpart. This is a bounded observed difference, not proof of a fix or cause.','Visual counter0→1 review is the parent operator evidence, not inferred from trace rows or marker alone.','49 uses newly staged helper/retention metadata; this is not an identical-bits statistical experiment.','No guest sample content inspected; separate worker owns original-tool sample audit.']}
write('audit.json',(json.dumps(result,indent=2)+'\n').encode());write('provenance.json',(json.dumps({'files':provenance,'audit_source_sha256':sha(pathlib.Path(__file__).read_bytes())},indent=2)+'\n').encode());print(json.dumps({'counter':counter['counts'],'comparisons':[(x['boot'],x['complete_cycles'])for x in comparisons]}))
