#!/usr/bin/env python3
"""Recompute same-emulator stopped-stopwatch interval, with explicit trace conditions."""
import argparse,hashlib,json,pathlib,re
p=argparse.ArgumentParser();p.add_argument('repository',type=pathlib.Path);a=p.parse_args();root=a.repository.resolve();src=root/'.local-build/reports/app-boot-53';out=pathlib.Path(__file__).parent
sha=lambda b:hashlib.sha256(b).hexdigest();sources={}
def retain(path,name):
 b=path.read_bytes();(out/name).write_bytes(b);sources[name]={'original':str(path),'sha256':sha(b),'bytes':len(b)};return b
def rows(b):
 offset=0;result=[]
 for line in b.splitlines(keepends=True):result.append((json.loads(line),{'byte_start':offset,'byte_end':offset+len(line),'sha256':sha(line)}));offset+=len(line)
 return result
active=json.loads((out/'audit.json').read_bytes());samples=rows(retain(src/'stopwatch-stopped-resources/samples.jsonl','stopped-samples.jsonl'));summary=json.loads(retain(src/'stopwatch-stopped-resources/summary.json','stopped-summary.json'));assert summary['error']is None and len(samples)==summary['sample_count']==61
assert summary['pid']==active['identity']['pid'] and summary['start_ticks']==active['identity']['start_ticks'] and summary['binary_sha256']==active['identity']['binary_sha256'];assert summary['source_sha256']==sha((out/'measure-process-source.py').read_bytes())
values=[]
for v,ref in samples:
 fields=v['proc_stat'][v['proc_stat'].rindex(')')+2:].split();parsed={'user_ticks':int(fields[11]),'system_ticks':int(fields[12]),'threads':int(fields[17]),'start_ticks':int(fields[19]),'virtual_bytes':int(fields[20]),'resident_pages':int(fields[21])};assert parsed==v['parsed'] and parsed['start_ticks']==summary['start_ticks'] and int(v['proc_stat'].split()[0])==summary['pid'];values.append(parsed)
for a,b in zip(values,values[1:]):assert a['user_ticks']<=b['user_ticks'] and a['system_ticks']<=b['system_ticks']
first,last=samples[0][0],samples[-1][0];lo,hi=first['time'],last['time'];elapsed=last['monotonic']-first['monotonic'];ticks=sum(values[-1][k]-values[0][k]for k in ['user_ticks','system_ticks']);cpu=ticks/summary['clock_ticks_per_second'];rss=[v['resident_pages']*summary['page_size']for v in values];assert elapsed==summary['observed_seconds'] and cpu==summary['process_cpu_seconds'] and max(rss)==summary['peak_sampled_rss_bytes']
qmp=rows(retain(src/'qmp-transcript.jsonl','paired-qmp-prefix.jsonl'));controls=rows(retain(src/'control-transcript.jsonl','paired-control-prefix.jsonl'));inputs=rows(retain(src/'serial-input-transcript.jsonl','paired-serial-input-prefix.jsonl'))
assert not[v for v,_ in controls+inputs if lo<=v['time']<=hi]
captures=[];trace_before={};transitions=[]
for v,ref in qmp:
 if v['direction']!='send':continue
 cmd=json.loads(v['raw']);name=cmd.get('execute');args=cmd.get('arguments',{})
 if name=='trace-event-set-state' and v['time']<=hi:
  replies=[(x,r)for x,r in qmp if x['direction']=='receive'and json.loads(x['raw']).get('id')==cmd['id']];assert len(replies)==1 and json.loads(replies[0][0]['raw'])['return']=={}
  entry={'enabled':args['enable'],'time':v['time'],'reference':ref,'reply':replies[0]}
  if v['time']<lo:trace_before[args['name']]=entry
  else:transitions.append({'event':args['name'],**entry})
 if lo<=v['time']<=hi:
  assert name in ('screendump','trace-event-set-state')
  if name=='screendump':
   replies=[(x,r)for x,r in qmp if x['direction']=='receive'and json.loads(x['raw']).get('id')==cmd['id']];assert len(replies)==1 and json.loads(replies[0][0]['raw'])['return']=={};path=pathlib.Path(args['filename']);raw=path.read_bytes();header=re.match(rb'P6\s+(\d+)\s+(\d+)\s+255\s',raw);assert header;w,h=map(int,header.groups());assert len(raw)-header.end()==w*h*3;captures.append({'path':str(path),'sha256':sha(raw),'dimensions':[w,h],'request':{'row':v,'reference':ref},'reply':replies[0],'visual_content':'not classified'})
vnc=[]
for path in sorted(src.glob('*/report.json')):
 raw=path.read_bytes();d=json.loads(raw)
 if d.get('kind')!='headless_unix_vnc_observation':continue
 times=[x.get('requested_time',x['time'])for x in d['captures']]+[x['time']for x in d['captures']];assert times and not(min(times)<=hi and max(times)>=lo);vnc.append({'path':str(path),'sha256':sha(raw),'first_capture':min(times),'last_capture':max(times),'completed':d.get('completed')})
stop=json.loads(retain(src/'stopwatch-stop/submission.json','stop-submission.json'));assert active['interval']['wall_end']<stop['started_time']<lo and stop['exit_code']==0
retain(src/'stopwatch-stopped/report.json','stopwatch-stopped-report.json')
post=src/'stopwatch-stopped-after-measure/report.json'
if post.exists():retain(post,'stopwatch-stopped-after-measure-report.json')
result={'scope':'One sequential same-process Clock running/stopped host-resource pair; no causal isolation, reliability, native, guest-only or cost claim.','sources':sources,'same_identity':active['identity'],'active_summary':active['interval'],'stopped_summary':{'wall_start':lo,'wall_end':hi,'elapsed_seconds':elapsed,'cpu_delta_ticks':ticks,'cpu_seconds':cpu,'average_logical_cpu_cores':cpu/elapsed,'rss_stat_bytes_min':min(rss),'rss_stat_bytes_max':max(rss),'rss_stat_GiB':max(rss)/2**30,'max_threads':max(v['threads']for v in values),'first_reference':samples[0][1],'last_reference':samples[-1][1]},'stopped_periodic_captures':captures,'trace_state_before_stopped_interval':trace_before,'trace_transitions_in_stopped_interval':transitions,'recorded_vnc_bounds':vnc,'explicit_stop':stop,'limits':['No recorded mailbox/serial input or VNC capture intervals overlap either interval; unlogged external clients are not independently excluded.','Active interval retained six enabled startup MT tracepoints; compare stopped state/transition records rather than treating trace conditions as identical.','Periodic QMP capture remains a measurement condition and can stimulate display refresh.','Visual stopped/running states require separately retained operator review. Snapshot hashes/dimensions do not interpret timer pixels.','Only one sequential pair; host load, guest background activity and trace condition changes are not controlled.']}
(out/'paired-audit.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result['stopped_summary']))
