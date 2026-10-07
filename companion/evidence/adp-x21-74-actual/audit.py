# SPDX-License-Identifier: AGPL-3.0-or-later
"""Read-only stopped74 trace/control audit; no disk hashing or VM interaction."""
import collections,hashlib,importlib.util,json,re
from pathlib import Path
R=Path('/home/brandonin/Documents/behavioral-iphone-inferno');P=R/'.local-build/reports/app-boot-74';D=Path(__file__).resolve().parent
h=lambda b:hashlib.sha256(b).hexdigest()
manifest={}
def raw(name):
 b=(P/name).read_bytes();manifest[name]={'bytes':len(b),'sha256':h(b)};return b
def obj(name):return json.loads(raw(name))
def rows(name):return [json.loads(x) for x in raw(name).split(b'\n') if x]
guest=raw('guest-errors.log');serial=raw('serial.log');stderr=raw('stderr.log');report=obj('report.json');overlay=obj('root-overlay.json');command=obj('command.json');build=obj('build-manifest.json');profile=obj('profile.json')
journal=rows('display-trace-control.jsonl');qmp=rows('qmp-transcript.jsonl');control=rows('control-transcript.jsonl');wire=rows('serial-input-transcript.jsonl')
starts=[x for x in journal if x['stage']=='start'];stops=[x for x in journal if x['stage']=='stop-result'];assert len(starts)==len(stops)==1 and starts[0]['seconds']==10 and stops[0]['all_disabled'] and stops[0]['pending']==[]
for stage,enable in [('after-enable',True),('after-disable',False)]:
 rr=[x for x in journal if x['stage']==stage];assert len(rr)==9 and {x['event'] for x in rr}==set(starts[0]['events'])
 for x in rr:
  assert x['response'].get('return')=={}
  sends=[y for y in qmp if y['direction']=='send' and json.loads(y['raw']).get('id')==x['response']['id']];assert len(sends)==1
  req=json.loads(sends[0]['raw']);assert req['execute']=='trace-event-set-state' and req['arguments']=={'name':x['event'],'enable':enable}
  assert any(y['direction']=='receive' and json.loads(y['raw'])==x['response'] for y in qmp)
requests=[{'time':x['time'],**json.loads(x['raw']),'response':x['response']} for x in control]
assert not any(starts[0]['time']<=x['time']<=stops[0]['time'] and x['execute'] in ['guest-hid-gesture','guest-stack-sample','guest-open-app','input-send-event'] for x in requests)
assert not any(x['execute'] in ['swapwait-cpu-window','query-display-registers','guest-open-app','probe-capture-after'] for x in requests)
assert not any(json.loads(x['raw']).get('execute') in ['human-monitor-command','input-send-event'] for x in qmp if x['direction']=='send')
assert not any(x['operation'] in ['OPEN'] for x in wire if x['stage']=='before-send')
trace=[];offset=0
for line in guest.split(b'\n'):
 if line.startswith(b'apple_adp_'):trace.append({'offset':offset,'bytes':len(line)+1,'event':line.split()[0].decode(),'fields':dict(re.findall(r'(\w+)=([^ ]+)',line.decode()))})
 offset+=len(line)+1
counts=collections.Counter(x['event'] for x in trace);reads=[(i,x) for i,x in enumerate(trace) if x['event']=='apple_adp_status_read'];pairs=[]
for i,x in reads:
 y=trace[i+1] if i+1<len(trace) else None
 pairs.append(bool(y and y['event']=='apple_adp_irq_write' and y['fields'].get('kind')=='status-w1c' and x['fields']['value']==y['fields']['value']==y['fields']['before'] and y['fields']['status']=='0x0'))
parser=R/'companion/evidence/original-adp-fifo-error-path/correlate-callers.py';spec=importlib.util.spec_from_file_location('callers',parser);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);slide=int(m.SLIDE.search(stderr).group(1),16);c=m.correlate(guest,slide)
refs=[];offset=0
for line in serial.split(b'\n'):
 if line.startswith((b'INFERNO_EVENT_RELAY',b'INFERNO_HID_ACK',b'INFERNO_SAMPLE_REQUEST',b'INFERNO_SAMPLE_BEGIN',b'INFERNO_SAMPLE_END',b'INFERNO_SAMPLE_CHILD_STOP',b'INFERNO_SAMPLE_CHILD_END')):
  refs.append({'offset':offset,'bytes':len(line)+1,'sha256':h(line+b'\n'),'text':line.rstrip(b'\r').decode(errors='replace')})
 offset+=len(line)+1
counter=obj('counter-001/submission.json');rid=counter['request_id'];matches=[x for x in requests if x.get('arguments',{}).get('request_id')==rid];assert len(matches)==1 and matches[0]['execute']=='guest-hid-gesture' and matches[0]['response']['transmission']=='written-to-serial-socket';assert counter['finished_time']<starts[0]['time']
images=[]
for name in ['after-counter','after-counter-confirm','during-samples']:
 v=obj(name+'/report.json');hashes=[]
 for capture in v['captures']:
  p=R/capture['path'];b=p.read_bytes();assert h(b)==capture['sha256'];hashes.append(h(b))
 assert len(set(hashes))==1 and not v['pointer_events'] and not v['home_button_events']
 images.append({'directory':name,'capture_count':len(hashes),'all_same_sha256':hashes[0],'first_time':v['captures'][0]['time'],'last_time':v['captures'][-1]['time'],'observation_seconds':v['observation_seconds']})
assert len({x['all_same_sha256'] for x in images})==1
samples=[]
for name in ['sample-backboardd','sample-springboard']:
 submission=obj(name+'-001/submission.json');result=obj(name+'-result/result.json');assert submission['started_time']>stops[0]['time'] and result['transport_complete']
 for record in result['records']:
  ref=record['reference'];chunk=serial[ref['byte_start']:ref['byte_end']];assert h(chunk)==ref['sha256']
 samples.append({'name':name,'submission':submission,'target_pid':result['target_pid'],'decoded_bytes':result['decoded_bytes'],'decoded_sha256':result['decoded_sha256'],'transport_complete':True,'first_raw_offset':result['records'][0]['reference']['byte_start'],'last_raw_offset':result['records'][-1]['reference']['byte_end']})
assert samples[0]['last_raw_offset']<samples[1]['first_raw_offset']
base=Path(overlay['backing_report']);basebytes=base.read_bytes();assert h(basebytes)==overlay['backing_report_sha256'];basereport=json.loads(basebytes)
stage_profile_raw=(base.parent/'profile.json').read_bytes();stage_import=json.loads(stage_profile_raw)['provenance']['imported_app'];assert stage_import['guest_path']=='/Applications/InfernoProbe.app' and stage_import['tree_sha256']=='697b73b118021ae7f225a9ed65009e6ca0aa91c62a2b430e60e7d2b648370125'
stage_serial=(base.parent/'serial.log').read_bytes();stage_refs=[];off=0
for line in stage_serial.split(b'\n'):
 if line.startswith((b'INFERNO_IMPORTED_APP_',b'INFERNO_PREP_COMPLETE')):stage_refs.append({'offset':off,'text':line.rstrip(b'\r').decode()})
 off+=len(line)+1
assert b'INFERNO_IMPORTED_APP_FINISH result=0 unmount=0' in stage_serial and b'INFERNO_PREP_COMPLETE' in stage_serial
assert report['exit_code']==0 and not report['attempt_completed'] and any(x['direction']=='receive' and json.loads(x['raw'])==report['quit_response'] for x in qmp)
assert any(x['direction']=='receive' and json.loads(x['raw']).get('data',{}).get('reason')=='host-qmp-quit' for x in qmp)
(D/'guest-errors.log').write_bytes(guest);(D/'display-trace-control.jsonl').write_bytes((P/'display-trace-control.jsonl').read_bytes())
out={'report':str(P),'manifest':manifest,'source_revision':report['companion_revision'],'binary_sha256':report['binary_sha256'],'parser_sha256':h(parser.read_bytes()),'kernel_slide':hex(slide),'trace_window':{'start':starts[0],'stop':stops[0],'event_byte_extent':[trace[0]['offset'],trace[-1]['offset']+trace[-1]['bytes']],'event_counts':{name:counts[name] for name in starts[0]['events']},'status_values':dict(collections.Counter(x['fields']['value'] for _,x in reads)),'immediate_matching_w1c_pairs':sum(pairs),'caller_counts':c['counts'],'handler_pending_bit10':dict(collections.Counter(str(x['handler_pending_bit10']) for x in c['records'] if x['category']=='interrupt_handler_ready_gate'))},'counter':counter,'control_requests':requests,'serial_refs':refs,'image_checks':images,'samples':samples,'lineage':{'base_report':str(base),'base_report_sha256':h(basebytes),'stage_serial_sha256':h(stage_serial),'stage_serial_refs':stage_refs,'stage_profile_sha256':h(stage_profile_raw),'imported_app':stage_import,'dependencies':overlay['dependencies'],'backing_after_stop':overlay['backing_after_stop'],'scope':'Recorded dependency chain and stage raw success markers checked, no duplicate full disk hashing.'},'stop':{'error':report.get('error'),'attempt_completed':report['attempt_completed'],'exit_code':report['exit_code'],'quit_response':report['quit_response']},'limits':['ADP trace begins after the first20s frozen-frame confirmation; no initial counter-submit trace exists. Counts concern sole bounded10s enabled window, not complete time since tap.','Events lack timestamps; file offsets and host trace ACKs delimit coverage, not guest frame timing.','All checked VNC bytes identical; counter0 interpretation is parent visual review, not automatic pixel classification.','Later two samples are separate from trace and sequential; their stack interpretation remains native independent audit.','Zero submits/BH plus ready status400 and pendingbit10 matches a previously observed failure pattern, not proof of identical cause or importer-induced failure. Staging/recovery and host timing differ from65.','Strict visual journey failed and forensic stop remains attempt_completedfalse despite orderly QMPquit/exit0.']}
comparison_path=R/'companion/evidence/adp-x21-66-actual/comparison.json';comparison_raw=comparison_path.read_bytes();out['comparison65']={'source':str(comparison_path),'sha256':h(comparison_raw),'post_counter':json.loads(comparison_raw)['matched_post_counter_file_boundaries'][0],'limit':'65 begins at counter host checkpoint whereas74 begins only after20s confirmation; both zero-submit patterns but durations/timing/staging differ.'}
(D/'audit.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out['trace_window'],indent=2))
