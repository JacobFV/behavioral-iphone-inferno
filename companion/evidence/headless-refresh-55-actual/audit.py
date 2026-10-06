#!/usr/bin/env python3
"""Independently audit actual55 observer lifecycle; no guest or runtime actions."""
import argparse,hashlib,json,pathlib,re,time
p=argparse.ArgumentParser();p.add_argument('repository',type=pathlib.Path);a=p.parse_args();root=a.repository.resolve();src=root/'.local-build/reports/app-boot-55';out=pathlib.Path(__file__).parent;sha=lambda b:hashlib.sha256(b).hexdigest();files={}
def retain(source,name):
 raw=source.read_bytes();(out/name).write_bytes(raw);files[name]={'original':str(source),'bytes':len(raw),'sha256':sha(raw)};return raw
def rows(raw):
 result=[];offset=0
 for line in raw.split(b'\n'):
  if offset==len(raw):break
  part=line+(b'\n'if offset+len(line)<len(raw)else b'');result.append((json.loads(line),{'byte_start':offset,'byte_end':offset+len(part),'sha256':sha(part)}));offset+=len(part)
 return result
life=json.loads(retain(src/'headless-refresh/lifecycle.json','lifecycle.json'));observer_raw=retain(src/'headless-refresh/observer/report.json','observer-report.json');observer=json.loads(observer_raw);samples=rows(retain(src/'headless-refresh/resources.jsonl','resources.jsonl'));report=json.loads(retain(src/'report.json','runner-report.json'));qmp=rows(retain(src/'qmp-transcript.jsonl','qmp-transcript.jsonl'));control=rows(retain(src/'control-transcript.jsonl','control-transcript.jsonl'));wire=rows(retain(src/'serial-input-transcript.jsonl','serial-input-transcript.jsonl'));serial=retain(src/'serial.log','serial.log')
for source,name,key in [('headless_refresh.py','headless-refresh-source.py','lifecycle_source_sha256'),('vnc-control.py','vnc-control-source.py','script_sha256')]:assert sha(retain(root/'companion'/source,name))==life[key]
assert report['headless_refresh']==life and sha(observer_raw)==life['observer_report_sha256'] and observer==life['observer_report'];assert report['exit_code']==0 and report.get('error')is None and report['probe_journey']['completed']
assert life['requested_seconds']==300 and life['exit_code']==life['cleanup_child_exit_code']==0 and not life.get('forced_kill') and not life.get('cleanup_errors') and not life.get('error')
assert not life['automatic_input'] and not life['auto_restart'] and not life['requested_phase_completed'] and not life['coverage_complete_for_whole_boot'] and not life['coverage_active'];assert observer['stop_requested'] and observer['stop_reason']=='signal 15' and not observer['completed'] and not observer['pointer_events'] and not observer['home_button_events']
parsed=[]
for sample,ref in samples:
 raw=sample['proc_stat'];f=raw[raw.rindex(')')+2:].split();assert int(raw.split()[0])==life['pid'];v={'start_ticks':int(f[19]),'cpu_ticks':int(f[11])+int(f[12]),'rss_bytes':int(f[21])*life['page_size']};assert all(sample[k]==v[k]for k in v) and v['start_ticks']==life['start_ticks'];parsed.append(v)
assert len(samples)>1 and samples[0][0]==life['resource_first'] and samples[-1][0]==life['resource_last']
for (first,_),(last,_)in zip(samples,samples[1:]):assert first['monotonic']<last['monotonic'] and first['cpu_ticks']<=last['cpu_ticks']
cpu=(parsed[-1]['cpu_ticks']-parsed[0]['cpu_ticks'])/life['clock_ticks_per_second'];rss=max(v['rss_bytes']for v in parsed);elapsed=samples[-1][0]['monotonic']-samples[0][0]['monotonic'];assert cpu==life['cpu_observed_seconds'] and rss==life['rss_peak_bytes']
connected=life['connection_established_time'];firstframe=life['first_frame_received_time'];stopping=life['stop_requested_time'];closed=life['connection_closed_time'];reaped=life['exit_observed_time'];assert life['spawn_time']<=connected<=firstframe<stopping<=closed<=reaped
commands=[(v,r,json.loads(v['raw']))for v,r in control];gestures=[(v,r,c)for v,r,c in commands if c['execute']=='guest-hid-gesture'];assert len(gestures)==4
gestureproof=[]
for v,ref,cmd in gestures:
 args=cmd['arguments'];rid=args['request_id'];sent=[(x,r)for x,r in wire if x.get('stage')=='before-send'and x.get('request_id')==rid];done=[(x,r)for x,r in wire if x.get('stage')=='after-send'and x.get('response',{}).get('request_id')==rid];assert len(sent)==len(done)==1;assert firstframe<v['time']<=sent[0][0]['time']<=done[0][0]['time']<closed;assert sha(sent[0][0]['raw'].encode())==sent[0][0]['sha256'] and done[0][0]['response']['transmission']=='written-to-serial-socket';assert re.search(rf'INFERNO_HID_ACK request_id={rid} attempt_status=0 ',serial.decode());gestureproof.append({'command':v,'reference':ref,'serial_send':sent[0],'serial_completion':done[0]})
exchanges=[]
for v,ref in qmp:
 if v['direction']!='send':continue
 cmd=json.loads(v['raw']);name=cmd.get('execute')
 if name not in ('screendump','quit'):continue
 reply=[(x,r)for x,r in qmp if x['direction']=='receive'and json.loads(x['raw']).get('id')==cmd['id']];assert len(reply)==1 and json.loads(reply[0][0]['raw'])['return']=={}
 if name=='quit':quit_exchange={'request':v,'reference':ref,'reply':reply[0]};continue
 path=pathlib.Path(cmd['arguments']['filename'])
 if path.name not in ('probe-before.ppm','probe-after.ppm','framebuffer.ppm'):continue
 raw=path.read_bytes();header=re.match(rb'P6\s+(\d+)\s+(\d+)\s+255\s',raw);assert header;w,h=map(int,header.groups());assert len(raw)-header.end()==w*h*3;assert firstframe<v['time']<reply[0][0]['time']<stopping;exchanges.append({'path':str(path),'sha256':sha(raw),'dimensions':[w,h],'request':v,'reference':ref,'reply':reply[0]})
assert len(exchanges)==3
byname={pathlib.Path(x['path']).name:x for x in exchanges};counter_time=gestures[-1][0]['time'];assert byname['probe-before.ppm']['reply'][0]['time']<counter_time<byname['probe-after.ppm']['request']['time']
finishes=[(v,r)for v,r,c in commands if c['execute']=='finish-run'];assert len(finishes)==1 and finishes[0][0]['response']['return']['finish_requested'];assert byname['probe-after.ppm']['reply'][0]['time']<finishes[0][0]['time']<byname['framebuffer.ppm']['request']['time']<stopping
assert reaped<quit_exchange['request']['time'];assert json.loads(quit_exchange['reply'][0]['raw'])==report['quit_response'];shutdown=[(v,r)for v,r in qmp if v['direction']=='receive'and json.loads(v['raw']).get('event')=='SHUTDOWN'];assert len(shutdown)==1 and json.loads(shutdown[0][0]['raw'])['data']=={'guest':False,'reason':'host-qmp-quit'}
# Validate full fixed argv rather than infer no input from a summary Boolean.
assert life['command']==['/usr/bin/python3',str(root/'companion/vnc-control.py'),'--socket',life['socket'],'--output',str(src/'headless-refresh/observer'),'--observe-seconds','300','--runner-observer','--settle-seconds','0']
review=[]
for capture in observer['captures']:
 path=pathlib.Path(capture['path']);path=path if path.is_absolute()else root/path;assert sha(path.read_bytes())==capture['sha256'];assert connected<=capture['requested_time']<=capture['received_time']<=capture['time']<=closed
 name=path.name;labels={'observed-0039.png':'lock','observed-0063.png':'lock','observed-0088.png':'lock','observed-0114.png':'beta alert','observed-0140.png':'counter0','observed-0165.png':'counter1'}
 if name in labels:review.append({'capture':capture,'label_reported_by_parent_operator':labels[name]})
assert len(review)==6
result={'scope':'Actual runner-owned bounded observer lifecycle and separately sampled observer-child resources. No input or runtime actions by this auditor.','sources':files,'connection_to_cleanup':{'spawn':life['spawn_time'],'connected':connected,'first_frame':firstframe,'stop_requested':stopping,'closed':closed,'reap_observed':reaped,'quit_request':quit_exchange['request']['time'],'observed_connection_seconds':closed-connected},'gesture_proof':gestureproof,'strict_and_final_captures':exchanges,'finish_run':finishes[0],'quit':quit_exchange,'shutdown':shutdown,'observer_resource_recomputation':{'pid':life['pid'],'start_ticks':life['start_ticks'],'sample_count':len(samples),'clock_ticks_per_second':life['clock_ticks_per_second'],'page_size':life['page_size'],'elapsed_between_samples':elapsed,'cpu_delta_ticks':parsed[-1]['cpu_ticks']-parsed[0]['cpu_ticks'],'cpu_seconds':cpu,'sample_interval_average_host_cores':cpu/elapsed,'peak_sampled_rss_bytes':rss,'peak_sampled_rss_MiB':rss/2**20,'first_reference':samples[0][1],'last_reference':samples[-1][1]},'visual_review_refs':review,'observer_frame_count':len(observer['captures']),'limits':['Controlled SIGTERM ended the observer before its requested300s phase; requested_phase_completed remains false. Actual coverage enclosed four gestures, strict captures and final framebuffer request.','Connection/capture receipt does not establish continuous guest rendering or a display-freeze fix. Visual labels above are parent operator review, not parser classification.','CPU is delta across retained child samples, not exact lifetime cost. RSS peak is sampled; emulator and runner resources are excluded.','Fixed-child shutdown and reap are supported by original Popen lifecycle/source and final exit records; no process signals issued by auditor.']}
(out/'audit.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result['observer_resource_recomputation']))
