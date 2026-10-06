#!/usr/bin/env python3
"""Recompute actual host resource samples and bound recorded observation activity."""
import argparse,hashlib,json,pathlib,re,time
p=argparse.ArgumentParser();p.add_argument('repository',type=pathlib.Path);a=p.parse_args();root=a.repository.resolve();source=root/'.local-build/reports/app-boot-53';out=pathlib.Path(__file__).resolve().parent
sha=lambda b:hashlib.sha256(b).hexdigest();files={}
def retain(src,name):
 b=src.read_bytes();(out/name).write_bytes(b);files[name]={'original':str(src),'bytes':len(b),'sha256':sha(b)};return b
def rows(b):
 result=[];offset=0
 for line in b.splitlines(keepends=True):result.append((json.loads(line),{'byte_start':offset,'byte_end':offset+len(line),'sha256':sha(line)}));offset+=len(line)
 return result
samples=rows(retain(source/'stopwatch-resources/samples.jsonl','samples.jsonl'));summary=json.loads(retain(source/'stopwatch-resources/summary.json','summary.json'));context=json.loads(retain(source/'stopwatch-measurement-context.json','measurement-context.json'));report_raw=retain(source/'report.json','runner-report-snapshot.json');report=json.loads(report_raw)
retain(source/'command.json','runner-command.json')
measure=retain(root/'companion/measure-process.py','measure-process-source.py');assert sha(measure)==summary['source_sha256'];retain(root/'companion/vnc-control.py','vnc-control-source.py')
qmp=rows(retain(source/'qmp-transcript.jsonl','qmp-prefix.jsonl'));control=rows(retain(source/'control-transcript.jsonl','control-prefix.jsonl'));serialin=rows(retain(source/'serial-input-transcript.jsonl','serial-input-prefix.jsonl'))
parsed=[]
for sample,ref in samples:
 raw=sample['proc_stat'];pid=int(raw.split(' ',1)[0]);fields=raw[raw.rindex(')')+2:].split();v={'user_ticks':int(fields[11]),'system_ticks':int(fields[12]),'threads':int(fields[17]),'start_ticks':int(fields[19]),'virtual_bytes':int(fields[20]),'resident_pages':int(fields[21])};assert v==sample['parsed'] and pid==summary['pid']==report['pid'] and v['start_ticks']==summary['start_ticks'];parsed.append(v)
assert len(samples)==summary['sample_count']==61 and summary['error']is None
for (prev,_),(cur,_)in zip(samples,samples[1:]):
 assert cur['time']>prev['time'] and cur['monotonic']>prev['monotonic']
 assert all(cur['parsed'][k]>=prev['parsed'][k]for k in ['user_ticks','system_ticks'])
first,last=samples[0][0],samples[-1][0];lo,hi=first['time'],last['time'];elapsed=last['monotonic']-first['monotonic'];ticks=sum(parsed[-1][k]-parsed[0][k]for k in ['user_ticks','system_ticks']);cpu=ticks/summary['clock_ticks_per_second'];rss=[v['resident_pages']*summary['page_size']for v in parsed];assert elapsed==summary['observed_seconds'] and cpu==summary['process_cpu_seconds'] and max(rss)==summary['peak_sampled_rss_bytes'] and 100*cpu/elapsed==summary['process_cpu_percent']
assert report['binary_sha256']==summary['binary_sha256'];binary=pathlib.Path(report['binary']);h=hashlib.sha256()
with binary.open('rb')as f:
 for b in iter(lambda:f.read(4*1024*1024),b''):h.update(b)
assert h.hexdigest()==summary['binary_sha256']
inside_control=[{'row':v,'reference':r}for v,r in control if lo<=v['time']<=hi];inside_input=[{'row':v,'reference':r}for v,r in serialin if lo<=v['time']<=hi];assert inside_control==inside_input==[]
inside_qmp=[{'row':v,'reference':r}for v,r in qmp if lo<=v['time']<=hi];captures=[]
for v,ref in qmp:
 if v['direction']!='send' or not lo<=v['time']<=hi:continue
 cmd=json.loads(v['raw']);assert cmd['execute']=='screendump';reply=[(r,rr)for r,rr in qmp if r['direction']=='receive'and json.loads(r['raw']).get('id')==cmd['id']];assert len(reply)==1 and json.loads(reply[0][0]['raw'])['return']=={}
 path=pathlib.Path(cmd['arguments']['filename']);data=path.read_bytes();hdr=re.match(rb'P6\s+(\d+)\s+(\d+)\s+255\s',data);assert hdr;w,h=map(int,hdr.groups());assert len(data)-hdr.end()==w*h*3;captures.append({'path':str(path),'sha256':sha(data),'bytes':len(data),'width':w,'height':h,'qmp_request':{'row':v,'reference':ref},'qmp_reply':{'row':reply[0][0],'reference':reply[0][1]},'visual_content':'not classified by this audit'})
assert len(captures)==2
trace_states={}
for v,ref in qmp:
 if v['direction']=='send'and v['time']<=hi:
  cmd=json.loads(v['raw'])
  if cmd.get('execute')=='trace-event-set-state':
   replies=[r for r,_ in qmp if r['direction']=='receive'and json.loads(r['raw']).get('id')==cmd['id']];assert len(replies)==1 and json.loads(replies[0]['raw'])['return']=={};trace_states[cmd['arguments']['name']]={'enabled':cmd['arguments']['enable'],'last_set_time':v['time'],'reference':ref}
assert all(not v['enabled']for k,v in trace_states.items()if k.startswith('apple_adp_'));assert all(v['enabled']for k,v in trace_states.items()if k.startswith('apple_mt_spi_'))
vnc=[]
for path in sorted(source.glob('*/report.json')):
 raw=path.read_bytes();d=json.loads(raw)
 if d.get('kind')!='headless_unix_vnc_observation':continue
 times=[x.get('requested_time',x['time'])for x in d['captures']]+[x['time']for x in d['captures']]
 assert times and not(min(times)<=hi and max(times)>=lo)
 vnc.append({'report':str(path),'sha256':sha(raw),'completed':d.get('completed'),'first_capture_request':min(times),'last_capture_time':max(times),'script_sha256':d.get('script_sha256')})
for name in ['stopwatch-running','stopwatch-after-measure']:
 retain(source/name/'report.json',name+'-report.json')
prior=max((x for x in vnc if x['last_capture_time']<lo),key=lambda x:x['last_capture_time']);following=min((x for x in vnc if x['first_capture_request']>hi),key=lambda x:x['first_capture_request'])
status_rss=[int(re.search(r'^VmRSS:\s+(\d+) kB$',s['proc_status'],re.M).group(1))*1024 for s,_ in samples]
result={'scope':'Whole emulator host-process resource audit during an operator-started original Clock stopwatch interval. No guest app RSS, native performance, density or cost inference.','source_snapshots':files,'captured_time':time.time(),'identity':{'pid':summary['pid'],'start_ticks':summary['start_ticks'],'binary_sha256':summary['binary_sha256'],'binary_fresh_hash_verified':True,'runner_start_report_hash_matches_snapshot':sha(report_raw)==summary['runner_report_sha256_at_start'],'sample_count':len(samples)},'interval':{'wall_start':lo,'wall_end':hi,'monotonic_start':first['monotonic'],'monotonic_end':last['monotonic'],'elapsed_seconds':elapsed,'cpu_delta_ticks':ticks,'tick_rate':summary['clock_ticks_per_second'],'cpu_seconds':cpu,'average_logical_cpu_cores':cpu/elapsed,'cpu_percent':100*cpu/elapsed,'rss_stat_bytes_min':min(rss),'rss_stat_bytes_max':max(rss),'rss_stat_GiB':max(rss)/2**30,'rss_status_bytes_min':min(status_rss),'rss_status_bytes_max':max(status_rss),'max_threads':max(v['threads']for v in parsed),'first_raw_reference':samples[0][1],'last_raw_reference':samples[-1][1]},'control_records_in_interval':inside_control,'serial_input_records_in_interval':inside_input,'qmp_records_in_interval':inside_qmp,'periodic_captures':captures,'trace_state_at_interval_end':trace_states,'recorded_vnc_observations':vnc,'nearest_vnc_before':prior,'nearest_vnc_after':following,'limits':['No recorded mailbox/serial input or VNC capture intervals overlap the sample interval. Logs cannot exclude an unrecorded external VNC client; this is not an independent socket-occupancy measurement.','Six startup multitouch trace events remained enabled through this interval; display tracing was disabled. Two periodic QMP screendumps occurred and can stimulate display refresh.','Clock running pixels and post-measurement progression require separate operator review; context prose is not pixel evidence.','RSS summary is specifically proc/stat resident_pages times recorded page size. Separately retained proc/status VmRSS values differ and were not substituted.','Resource samples are sequential /proc reads, not atomic snapshots. Recorded system tick rate/page size come from source os.sysconf at measurement time.']}
(out/'audit.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result['interval']))
