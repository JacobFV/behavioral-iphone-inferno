# SPDX-License-Identifier: AGPL-3.0-or-later
from pathlib import Path
import json,hashlib,re,collections,importlib.util,sys,shutil
R=Path('/home/brandonin/Documents/behavioral-iphone-inferno');P=R/'.local-build/reports/app-boot-71';G=P/'guarded-setup-counter-002';D=Path(__file__).resolve().parent
H=lambda b:hashlib.sha256(b).hexdigest()
manifest={}
for n in ['serial.log','guest-errors.log','stderr.log','qmp-transcript.jsonl','control-transcript.jsonl','serial-input-transcript.jsonl','display-trace-control.jsonl','report.json','command.json','build-manifest.json']:
 b=(P/n).read_bytes();(D/n).write_bytes(b);manifest[n]={'bytes':len(b),'sha256':H(b)}
for n in ['sequence.json','not-now/request.json','not-now/submission.json','counter/request.json','counter/submission.json']:
 b=(G/n).read_bytes();(D/n).parent.mkdir(exist_ok=True);(D/n).write_bytes(b);manifest[n]={'bytes':len(b),'sha256':H(b)}
s=json.loads((D/'sequence.json').read_text());
for name,digest in s['source_hashes'].items():
 assert H((R/'companion'/name).read_bytes())==digest, ('source changed',name)
serial=(D/'serial.log').read_bytes();wire=[json.loads(x) for x in (D/'serial-input-transcript.jsonl').read_text().splitlines()];q=[json.loads(x) for x in (D/'qmp-transcript.jsonl').read_text().splitlines()];controls=[json.loads(x) for x in (D/'control-transcript.jsonl').read_text().splitlines()]
sends=[];acks=[]
for name in ['not-now','counter']:
 rid=s[name.replace('-','_')]['request_id'];req=json.loads((D/name/'request.json').read_text());sub=json.loads((D/name/'submission.json').read_text());a=[x for x in wire if x.get('stage')=='before-send' and x.get('request_id')==rid];z=[x for x in wire if x.get('stage')=='after-send' and x.get('response',{}).get('request_id')==rid];assert len(a)==len(z)==1
 response=z[0]['response'];assert response['transmission']=='written-to-serial-socket' and response['bytes_sent']==len(a[0]['raw'].encode()) and H(a[0]['raw'].encode())==a[0]['sha256'];assert response['write_begin_monotonic']<response['send_deadline_monotonic'] and not response['write_end_after_deadline'];assert response['send_deadline_monotonic']==req['send_deadline_monotonic'];assert a[0]['raw']==sub['expected_serial_wire'];sends.append({'before':a[0],'after':z[0]})
 hits=list(re.finditer(rb'^INFERNO_HID_ACK request_id='+rid.encode()+rb' attempt_status=0[^\n]*\n',serial,re.M));assert len(hits)==1;acks.append({'offset':hits[0].start(),'text':hits[0].group().decode().rstrip()})
for item in ['identity_before','identity_before_counter']:
 ident=s[item];assert H(serial[:ident['serial_bytes']])==ident['serial_sha256'];assert ident['boot']==s['identity_before']['boot'] and ident['pid']==s['identity_before']['pid']
interval=sends[1]['after']['response']['write_begin_monotonic']-sends[0]['after']['response']['write_begin_monotonic'];assert abs(interval-10)<=.5 and interval==s['actual_send_interval_seconds']
# Replay exact pre-state reference classifier; no live capture or control.
sys.path.insert(0,str(R/'companion'));spec=importlib.util.spec_from_file_location('guard',R/'companion/guarded-setup-counter.py');guard=importlib.util.module_from_spec(spec);spec.loader.exec_module(guard);refs=guard.references(R/'companion/evidence/guarded-setup-counter/references.json',s['references_sha256']);frames=[]
for x in s['captures']:
 p=Path(x['path']);b=p.read_bytes();assert H(b)==x['sha256'];frames.append({'name':p.name,'sha256':H(b),'received_time':x['received_time'],'state':guard.classify(p,refs) if p.name in ['overlay-initial.png','overlay-pre-input.png','zero-pre-counter.png'] or p.name.startswith('poll-') else 'manual-review-required'})
assert next(x for x in frames if x['name']=='overlay-initial.png')['state']=='overlay';assert next(x for x in frames if x['name']=='overlay-pre-input.png')['state']=='overlay';assert next(x for x in frames if x['name']=='zero-pre-counter.png')['state']=='zero'
j=[json.loads(x) for x in (D/'display-trace-control.jsonl').read_text().splitlines()];idx=[i for i,x in enumerate(j) if x['stage']=='start'][-1];window=j[idx:];en=[x for x in window if x['stage']=='after-enable'];ds=[x for x in window if x['stage']=='after-disable'];assert len(en)==len(ds)==9
for x in en+ds:assert x['response'].get('return')=={} and any(y['direction']=='receive' and json.loads(y['raw'])==x['response'] for y in q)
assert window[-1]['all_disabled'] and window[-1]['reason']=='deadline';assert window[0]['time']<sends[0]['before']['time']<sends[1]['before']['time']<s['end_checkpoint']['wall_time']<window[-1]['time']
assert not any(json.loads(x['raw']).get('execute')=='human-monitor-command' for x in q if x['direction']=='send')
r=json.loads((D/'report.json').read_text());assert r['exit_code']==0 and any(x['direction']=='receive' and json.loads(x['raw'])==r['quit_response'] for x in q)
assert any(x['direction']=='receive' and json.loads(x['raw']).get('data')=={'guest':False,'reason':'host-qmp-quit'} for x in q)
trace=(D/'guest-errors.log').read_bytes();a=json.loads((D/'counter/submission.json').read_text())['trace_before']['size'];ends=[s['end_checkpoint']['size'],len(trace)];spec=importlib.util.spec_from_file_location('callers',R/'companion/evidence/original-adp-fifo-error-path/correlate-callers.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);slide=int(m.SLIDE.search((D/'stderr.log').read_bytes()).group(1),16);phases=[]
for z in ends:
 b=trace[a:z];rows=[x.decode() for x in b.split(b'\n') if x.startswith(b'apple_adp_')];counts=collections.Counter(x.split()[0] for x in rows);status=collections.Counter();pairs=0
 for i,x in enumerate(rows):
  if x.startswith('apple_adp_status_read '):
   value=re.search('value=(\\S+)',x).group(1);status[value]+=1;y=rows[i+1];assert y.startswith('apple_adp_irq_write kind=status-w1c ') and f'value={value} before={value} status=0x0' in y;pairs+=1
 c=m.correlate(b,slide);phases.append({'bytes':[a,z],'sha256':H(b),'counts':dict(counts),'status_values':dict(status),'immediate_equal_w1c_pairs':pairs,'caller_counts':c['counts'],'handler_pending_bit10':dict(collections.Counter(str(x['handler_pending_bit10']) for x in c['records'] if x['category']=='interrupt_handler_ready_gate'))})
out={'scope':'Actual guard002 execution audit; helper001 failure remains separately preserved.','sources':manifest,'source_hashes_recorded':s['source_hashes'],'actual_send_interval_seconds':interval,'sends':sends,'acks':acks,'prestate_frame_replay':frames,'trace_window':window,'ADP_post_counter':phases,'normal_quit':r['quit_response'],'limits':['Root reviewed after028 counter1; this audit does not classify post-action pixels.','Minutes of idle overlay during host fix mean this does not reproduce full run65 cadence; it validates guarded10s send-start interval.','Send-start timestamps are host monotonic, not guest delivery or render latency.','VNC observation stimulates refresh; exact pre-state matching does not establish frame presentation time.','No CPU/SAMPLE, guest actions or disk hashing by reviewer.']};(D/'audit.json').write_text(json.dumps(out,indent=2)+'\n');print(interval);print(json.dumps(phases,indent=2))
