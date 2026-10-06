#!/usr/bin/env python3
"""Audit the distinct third condition: original Clock plus continuous headless VNC."""
import argparse,hashlib,json,pathlib,re
p=argparse.ArgumentParser();p.add_argument('repository',type=pathlib.Path);a=p.parse_args();root=a.repository.resolve();src=root/'.local-build/reports/app-boot-53';out=pathlib.Path(__file__).parent;sha=lambda b:hashlib.sha256(b).hexdigest();sources={}
def retain(path,name):
 b=path.read_bytes();(out/name).write_bytes(b);sources[name]={'original':str(path),'sha256':sha(b),'bytes':len(b)};return b
def rows(raw):
 result=[];offset=0
 for line in raw.splitlines(keepends=True):result.append((json.loads(line),{'byte_start':offset,'byte_end':offset+len(line),'sha256':sha(line)}));offset+=len(line)
 return result
baseline=json.loads((out/'audit.json').read_bytes());summary=json.loads(retain(src/'stopwatch-continuous-resources/summary.json','continuous-summary.json'));samples=rows(retain(src/'stopwatch-continuous-resources/samples.jsonl','continuous-samples.jsonl'));viewer=json.loads(retain(src/'stopwatch-continuous-view/report.json','continuous-view-report.json'))
assert summary['error']is None and len(samples)==summary['sample_count']==61
for k in ['pid','start_ticks','binary_sha256']:assert summary[k]==baseline['identity'][k]
assert summary['source_sha256']==sha((out/'measure-process-source.py').read_bytes());assert viewer['script_sha256']==sha((out/'vnc-control-source.py').read_bytes())
values=[]
for sample,ref in samples:
 raw=sample['proc_stat'];f=raw[raw.rindex(')')+2:].split();v={'user_ticks':int(f[11]),'system_ticks':int(f[12]),'threads':int(f[17]),'start_ticks':int(f[19]),'virtual_bytes':int(f[20]),'resident_pages':int(f[21])};assert v==sample['parsed'] and v['start_ticks']==summary['start_ticks'] and int(raw.split()[0])==summary['pid'];values.append(v)
for (prev,_),(cur,_)in zip(samples,samples[1:]):assert cur['monotonic']>prev['monotonic'] and cur['time']>prev['time'] and all(cur['parsed'][k]>=prev['parsed'][k]for k in ['user_ticks','system_ticks'])
first,last=samples[0][0],samples[-1][0];lo,hi=first['time'],last['time'];elapsed=last['monotonic']-first['monotonic'];ticks=sum(values[-1][k]-values[0][k]for k in ['user_ticks','system_ticks']);cpu=ticks/summary['clock_ticks_per_second'];rss=[x['resident_pages']*summary['page_size']for x in values];assert elapsed==summary['observed_seconds'] and cpu==summary['process_cpu_seconds'] and max(rss)==summary['peak_sampled_rss_bytes']
qmp=rows(retain(src/'qmp-transcript.jsonl','continuous-qmp-prefix.jsonl'));control=rows(retain(src/'control-transcript.jsonl','continuous-control-prefix.jsonl'));wire=rows(retain(src/'serial-input-transcript.jsonl','continuous-serial-input-prefix.jsonl'));assert not[v for v,_ in control+wire if lo<=v['time']<=hi]
state={};captures=[]
for v,ref in qmp:
 if v['direction']!='send':continue
 cmd=json.loads(v['raw'])
 if cmd.get('execute')=='trace-event-set-state'and v['time']<=hi:
  reply=[(x,r)for x,r in qmp if x['direction']=='receive'and json.loads(x['raw']).get('id')==cmd['id']];assert len(reply)==1 and json.loads(reply[0][0]['raw'])['return']=={};assert v['time']<lo;state[cmd['arguments']['name']]={'enabled':cmd['arguments']['enable'],'time':v['time'],'reference':ref,'reply':reply[0]}
 if lo<=v['time']<=hi:
  assert cmd['execute']=='screendump';reply=[(x,r)for x,r in qmp if x['direction']=='receive'and json.loads(x['raw']).get('id')==cmd['id']];assert len(reply)==1 and json.loads(reply[0][0]['raw'])['return']=={};path=pathlib.Path(cmd['arguments']['filename']);data=path.read_bytes();h=re.match(rb'P6\s+(\d+)\s+(\d+)\s+255\s',data);assert h;w,height=map(int,h.groups());assert len(data)-h.end()==w*height*3;captures.append({'path':str(path),'sha256':sha(data),'dimensions':[w,height],'request':{'row':v,'reference':ref},'reply':reply[0],'visual_content':'not classified'})
assert all(not v['enabled']for k,v in state.items()if k.startswith(('apple_adp_','apple_mt_spi_')))
assert viewer['completed'] and not viewer['pointer_events'] and not viewer['home_button_events']
for cap in viewer['captures']:
 path=pathlib.Path(cap['path']);path=path if path.is_absolute()else root/path;assert sha(path.read_bytes())==cap['sha256'];assert cap['requested_time']<=cap['received_time']<=cap['time']
first_view=min(c['requested_time']for c in viewer['captures']);last_view=max(c['time']for c in viewer['captures']);assert first_view<lo<hi<last_view
inside=[c for c in viewer['captures']if lo<=c['received_time']<=hi];assert len(inside)==48
written_inside=[c for c in viewer['captures']if lo<=c['time']<=hi]
review=[]
for name,label in [('observed-0012.png','07:21.72'),('observed-0036.png','07:52.17'),('observed-0059.png','08:21.35')]:
 caps=[c for c in viewer['captures']if pathlib.Path(c['path']).name==name];assert len(caps)==1;review.append({'capture':caps[0],'timer_label_reported_by_parent_operator':label})
interval={'wall_start':lo,'wall_end':hi,'monotonic_start':first['monotonic'],'monotonic_end':last['monotonic'],'elapsed_seconds':elapsed,'cpu_delta_ticks':ticks,'cpu_seconds':cpu,'average_logical_cpu_cores':cpu/elapsed,'rss_stat_bytes_min':min(rss),'rss_stat_bytes_max':max(rss),'rss_stat_GiB':max(rss)/2**30,'max_threads':max(v['threads']for v in values),'first_raw_reference':samples[0][1],'last_raw_reference':samples[-1][1]}
result={'scope':'Distinct third same-emulator condition: original Clock stopwatch with continuous headless VNC observation; not a causal experiment.','source_snapshots':sources,'same_process_identity':baseline['identity'],'interval':interval,'viewer_coverage':{'first_capture_request':first_view,'last_capture_time':last_view,'frames_received_in_measurement':len(inside),'PNG_completion_records_in_measurement':len(written_inside),'maximum_gap_between_inside_receive_times':max(b['received_time']-a['received_time']for a,b in zip(inside,inside[1:])),'all_retained_frame_hashes_freshly_verified':True,'viewer_source_sha256':viewer['script_sha256']},'operator_visual_review':review,'trace_states':state,'qmp_periodic_captures':captures,'control_records_in_interval':[],'serial_input_records_in_interval':[],'limits':['No recorded input commands during measurement; VNC observation is intentional and can stimulate guest display work.','All recorded display and startup multitouch trace events were disabled before the interval, unlike the first running condition.','Timer labels are separately parent-reviewed; image hashes and receipt times are not guest presentation timing.','CPU/RSS cover only the emulator, excluding the host VNC observer process and its PNG work.','One third sequential condition, same emulator PID/start time; guest state, host background load and observation conditions differ. No native parity, isolated VNC cost, throughput, reliability or cost inference.']}
(out/'continuous-audit.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(interval))
