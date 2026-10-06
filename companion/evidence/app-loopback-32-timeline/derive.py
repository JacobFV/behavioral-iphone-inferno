#!/usr/bin/env python3
"""Derive only host-observed timings from retained boot32 raw evidence."""
import argparse, datetime, hashlib, json
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('repository',type=Path);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
root=a.repository.resolve();report=root/'.local-build/reports/app-boot-32';obs=root/'companion/evidence/app-loopback-32-observations'
sources={}
def digest(b):return hashlib.sha256(b).hexdigest()
def load(path):
 b=path.read_bytes();key=str(path.relative_to(root));sources[key]={'sha256':digest(b),'bytes':len(b)};return b,key
def rows(path):
 b,key=load(path);out=[];offset=0
 for n,line in enumerate(b.splitlines(keepends=True),1):
  out.append((json.loads(line),{'source':key,'line':n,'byte_start':offset,'byte_end':offset+len(line),'sha256':digest(line)}));offset+=len(line)
 return out
serial,serial_key=load(report/'serial.log')
arrivals=rows(obs/'event-arrivals/observations.jsonl')
for row,ref in arrivals:
 raw=serial[row['byte_start']:row['byte_end']]
 assert raw.endswith(b'\n') and raw[:-1].hex()==row['raw_hex'] and digest(raw[:-1])==row['sha256']
controls=rows(report/'control-transcript.jsonl');qmp=rows(report/'qmp-transcript.jsonl');inputs=rows(report/'serial-input-transcript.jsonl')
samples=rows(obs/'resources-after-counter/samples.jsonl')
meta=json.loads(load(obs/'event-arrivals/context.json')[0]);summary=json.loads(load(obs/'resources-after-counter/summary.json')[0]);finished=json.loads(load(report/'report.json')[0]);load(report/'probe-before.ppm')
def utc(t):return datetime.datetime.fromtimestamp(t,datetime.timezone.utc).isoformat()
def point(label,t,ref,**more):return {'label':label,'host_unix_seconds':t,'utc':utc(t),'raw_reference':ref,**more}
def event(name):
 row,ref=next((r,f) for r,f in arrivals if r['text'].startswith('INFERNO_UIKIT_PROBE_V1 event='+name+' '))
 assert not row['preexisting']
 return point(name+'_record_observed',row['observed_time'],ref,host_monotonic_seconds=row['monotonic'],serial_reference={'source':serial_key,'byte_start':row['byte_start'],'byte_end':row['byte_end'],'sha256_excluding_final_lf':row['sha256']},preexisting=False)
main=event('main');appeared=event('appeared');tap=event('tap')
controw,contref=next((r,f) for r,f in qmp if r['direction']=='send' and json.loads(r['raw']).get('execute')=='cont')
strictrow,strictref=next((r,f) for r,f in qmp if r['direction']=='send' and 'probe-before.ppm' in r['raw'])
strictreply,strictreplyref=next((r,f) for r,f in qmp if r['direction']=='receive' and json.loads(r['raw']).get('id')==25)
assert json.loads(strictreply['raw']).get('return')=={}
tap_request='ce3d639e941a4898b878a28aacb2fdaf'
controlrow,controlref=next((r,f) for r,f in controls if tap_request in r['raw'])
sendrow,sendref=next((r,f) for r,f in inputs if r.get('stage')=='before-send' and r.get('request_id')==tap_request)
afterrow,afterref=next((r,f) for r,f in inputs if r.get('stage')=='after-send' and r.get('response',{}).get('request_id')==tap_request)
points=[point('qmp_cont_send',controw['time'],contref),main,appeared,point('strict_before_screendump_send',strictrow['time'],strictref),point('strict_before_screendump_reply',strictreply['time'],strictreplyref),point('counter_tap_request_created',json.loads(controlrow['raw'])['created'],controlref),point('counter_tap_serial_before_send',sendrow['time'],sendref,request_id=tap_request),point('counter_tap_serial_after_send',afterrow['time'],afterref),tap]
# Reparse raw Linux /proc/PID/stat rather than trusting the summary assertions.
parsed=[]
for row,ref in samples:
 fields=row['proc_stat'].split(') ',1)[1].split()
 parsed.append({'time':row['time'],'monotonic':row['monotonic'],'ticks':int(fields[11])+int(fields[12]),'start_ticks':int(fields[19]),'rss_pages':int(fields[21]),'threads':int(fields[17])})
assert len({x['start_ticks'] for x in parsed})==1
first,last=parsed[0],parsed[-1];elapsed=last['monotonic']-first['monotonic'];cpu=(last['ticks']-first['ticks'])/summary['clock_ticks_per_second'];rss=max(x['rss_pages'] for x in parsed)*summary['page_size']
assert abs(cpu-summary['process_cpu_seconds'])<1e-9 and rss==summary['peak_sampled_rss_bytes']
points += [point('resource_first_sample',first['time'],samples[0][1]),point('resource_last_sample',last['time'],samples[-1][1])]
result={'scope':'Host-observed lifecycle/control/relay timeline and whole-emulator resource interval; not intrinsic guest application latency.','timeline':points,'intervals_seconds':{'qmp_cont_send_to_main_record_observed':main['host_unix_seconds']-controw['time'],'main_to_appeared_record_observed_monotonic':appeared['host_monotonic_seconds']-main['host_monotonic_seconds'],'strict_before_reply_to_counter_serial_before_send':sendrow['time']-strictreply['time'],'counter_request_created_to_tap_record_observed':tap['host_unix_seconds']-json.loads(controlrow['raw'])['created'],'counter_serial_before_send_to_tap_record_observed':tap['host_unix_seconds']-sendrow['time'],'tap_record_observed_to_resource_first_sample_monotonic':first['monotonic']-tap['host_monotonic_seconds']},'preexisting_entries':[{'text':r['text'],'reference':f,'excluded_from_arrival_intervals':True} for r,f in arrivals if r['preexisting']],'resource':{'samples':len(samples),'emulator_pid':summary['pid'],'process_start_ticks':first['start_ticks'],'clock_ticks_per_second':summary['clock_ticks_per_second'],'page_size':summary['page_size'],'observed_monotonic_seconds':elapsed,'process_cpu_seconds':cpu,'average_host_cpu_cores':cpu/elapsed,'peak_sampled_rss_bytes':rss,'peak_sampled_rss_GiB':rss/(1024**3),'max_sampled_threads':max(x['threads'] for x in parsed)},'completion':{'strict_journey_completed':finished['probe_journey']['completed'],'state':finished['probe_journey']['state'],'runner_error':finished['error'],'emulator_exit_code':finished['exit_code'],'signal_origin':'Unknown; do not infer from exit_code0 that strict journey finished.'},'limitations':['Arrival observer polls every0.05seconds; relay scheduling, TCP transfer, serial logging and host polling are included. Same-poll events do not establish equal guest timestamps.','Main/appeared gaps are differences between record observations, not cold/warm launch duration or intrinsic UIKit execution time.','Control wall-clock timestamps and event wall-clock timestamps are host clocks, distinct from guest HID ticks and guest log time. No cross-clock subtraction is used.','Preexisting bytes have no measured arrival time; early boot is excluded.','Strict-before QMP success establishes capture timing; visual counter0 interpretation comes from separately reviewed retained capture, not JSON alone.','Resource sample is whole emulator after the counter interaction, not app RSS, CPU attribution, active-tap cost, reliability, throughput or host density.','Boot32 lacks strict operator-after completion; actual lifecycle/tap relay and before image do not make its strict journey complete.'],'arrival_poll_seconds':meta['poll_seconds'],'verified_arrival_rows_against_serial_bytes':len(arrivals),'source_files':sources}
a.output.write_text(json.dumps(result,indent=2)+'\n')
