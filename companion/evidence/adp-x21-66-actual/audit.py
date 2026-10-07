# SPDX-License-Identifier: AGPL-3.0-or-later
import collections,hashlib,importlib.util,json,re,shutil
from pathlib import Path
R=Path('/home/brandonin/Documents/behavioral-iphone-inferno');P=R/'.local-build/reports/app-boot-66';D=Path(__file__).resolve().parent
parser=R/'companion/evidence/original-adp-fifo-error-path/correlate-callers.py';spec=importlib.util.spec_from_file_location('callers',parser);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
h=lambda b:hashlib.sha256(b).hexdigest()
files=['guest-errors.log','stderr.log','serial.log','display-trace-control.jsonl','qmp-transcript.jsonl','control-transcript.jsonl','serial-input-transcript.jsonl','report.json','command.json','build-manifest.json','x21-startup-before.json','x21-startup-after.json']+[n+'/submission.json' for n in ['close-beta-alert','setup-not-now','open-from-home-001','counter-001']]
manifest={}
for f in files:
 b=(P/f).read_bytes();manifest[f]={'bytes':len(b),'sha256':h(b)};(D/f).parent.mkdir(parents=True,exist_ok=True);(D/f).write_bytes(b)
b=(D/'guest-errors.log').read_bytes();slide=int(m.SLIDE.search((D/'stderr.log').read_bytes()).group(1),16)
rows=[];offset=0
for line in b.split(b'\n'):
 if line.startswith(b'apple_adp_'):rows.append({'offset':offset,'event':line.split()[0].decode(),'fields':dict(re.findall(r'(\w+)=([^ ]+)',line.decode()))})
 offset+=len(line)+1
start=json.loads((D/'x21-startup-before.json').read_text())['checkpoint']['size'];end=json.loads((D/'x21-startup-after.json').read_text())['checkpoint']['size'];counter=json.loads((D/'counter-001/submission.json').read_text())['trace_before']['size']
results=[]
for name,a,z in [('startup',start,end),('between-startup-checkpoint-and-counter',end,counter),('counter-to-final-flush',counter,len(b))]:
 rr=[x for x in rows if a<=x['offset']<z];counts=collections.Counter(x['event'] for x in rr);reads=[(i,x) for i,x in enumerate(rr) if x['event']=='apple_adp_status_read'];pairs=[]
 for i,x in reads:
  y=rr[i+1] if i+1<len(rr) else None
  pairs.append(bool(y and y['event']=='apple_adp_irq_write' and y['fields'].get('kind')=='status-w1c' and x['fields']['value']==y['fields']['value']==y['fields']['before'] and y['fields']['status']=='0x0'))
 c=m.correlate(b[a:z],slide);pending=collections.Counter(str(x['handler_pending_bit10']) for x in c['records'] if x['category']=='interrupt_handler_ready_gate')
 results.append({'name':name,'byte_range':[a,z],'slice_sha256':h(b[a:z]),'event_counts':dict(counts),'status_values':dict(collections.Counter(x['fields']['value'] for _,x in reads)),'immediate_equal_w1c_pairs':sum(pairs),'status_reads':len(reads),'caller_counts':c['counts'],'handler_pending_bit10':dict(pending),'exposed_pc_counts':dict(collections.Counter(x['exposed_pc'] for x in c['records']))})
j=[json.loads(x) for x in (D/'display-trace-control.jsonl').read_text().splitlines()];q=[json.loads(x) for x in (D/'qmp-transcript.jsonl').read_text().splitlines()];windows=[]
for x in j:
 if x['stage']=='start':windows.append({'start':x,'enables':[],'disables':[]})
 elif x['stage'] in ['after-enable','after-disable']:
  assert x['response'].get('return')=={} and any(y['direction']=='receive' and json.loads(y['raw'])==x['response'] for y in q)
  windows[-1]['enables' if x['stage']=='after-enable' else 'disables'].append(x)
 elif x['stage']=='stop-result':windows[-1]['stop']=x
for w in windows:assert len(w['enables'])==len(w['disables'])==9 and w['stop']['all_disabled']
commands=[json.loads(x['raw']) for x in q if x['direction']=='send'];assert not any(x.get('execute')=='human-monitor-command' for x in commands)
r=json.loads((D/'report.json').read_text());assert r['exit_code']==0 and r['attempt_completed'];assert any(x['direction']=='receive' and json.loads(x['raw']).get('data',{}).get('reason')=='host-qmp-quit' for x in q);assert any(x['direction']=='receive' and json.loads(x['raw'])==r['quit_response'] for x in q)
serial=(D/'serial.log').read_bytes();refs=[];offset=0
for line in serial.split(b'\n'):
 if line.startswith(b'INFERNO_') and (b'395' in line or b'367' in line or b'41653cc6c599409f83817331bafbc29b' in line or b'5438cdab75fb469085caa67701088c72' in line):refs.append({'offset':offset,'text':line.rstrip(b'\r').decode(errors='replace')})
 offset+=len(line)+1
out={'source_report':str(P),'manifest':manifest,'parser_sha256':h(parser.read_bytes()),'kernel_slide':hex(slide),'phases':results,'windows':windows,'serial_refs':refs,'normal_quit':r['quit_response'],'cpu_diagnostic':r.get('swapwait_cpu_diagnostic'),'limitations':['Byte slices are file-visible boundaries; buffered logs lack event timestamps. The middle slice includes untraced intervals and explicit alert/setup/OPEN activity, not a pure per-action window.','Counter window was requested60s but cleanup stopped it early.','Visible0→1 is parent visual review, not inferred from trace or classified here.','Initial PID367 identity failure, later explicitOPEN toPID395, slow unlocking and different observation timing confound comparisons to65.','Read/W1C and x21 bits do not establish completed callbacks or presentation latency.']}
(D/'audit.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(results,indent=2))
