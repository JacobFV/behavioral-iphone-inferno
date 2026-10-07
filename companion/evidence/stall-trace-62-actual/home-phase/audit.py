# SPDX-License-Identifier: AGPL-3.0-or-later
import collections,hashlib,json,re
from pathlib import Path
D=Path(__file__).resolve().parent
h=lambda b:hashlib.sha256(b).hexdigest()
b=(D/'guest-errors.delta.log').read_bytes();assert len(b)==7097
rows=[];off=12964
for line in b.split(b'\n'):
 if off>=12964 and line.startswith(b'apple_adp_'):
  s=line.decode();rows.append({'offset':off,'sha256':h(line+b'\n'),'event':s.split()[0],'fields':dict(re.findall(r'(\w+)=([^ ]+)',s))})
 off+=len(line)+1
counts=collections.Counter(x['event'] for x in rows)
assert counts=={'apple_adp_output_ready':20,'apple_adp_irq_write':19,'apple_adp_unknown_mmio':57}
w=[x for x in rows if x['event']=='apple_adp_irq_write'];assert all(x['fields']=={'kind':'status-w1c','value':'0x400','before':'0x400','status':'0x0','enable':'0xc0180c08'} for x in w)
u=[x for x in rows if x['event']=='apple_adp_unknown_mmio'];assert all(x['fields']['write']=='0' and x['fields']['value']=='0x0' for x in u)
q=[json.loads(x) for x in (D/'qmp.prefix.jsonl').read_text().splitlines()];j=[json.loads(x) for x in (D/'trace-control.prefix.jsonl').read_text().splitlines()]
en=[x for x in j if x['stage']=='after-enable'][-7:];ds=[x for x in j if x['stage']=='after-disable'][-7:];assert len(en)==len(ds)==7
for x in en+ds:assert x['response']['return']=={} and any(y['direction']=='receive' and json.loads(y['raw'])==x['response'] for y in q)
assert not any(json.loads(x['raw']).get('execute') in ['human-monitor-command','input-send-event','send-key'] for x in q if x['direction']=='send')
start=[x['time'] for x in j if x['stage']=='start'][-1];end=[x['time'] for x in j if x['stage']=='stop-result'][-1]
wire=[json.loads(x) for x in (D/'serial-input.prefix.jsonl').read_text().splitlines()];assert not any(start<=x['time']<=end for x in wire)
result={'range':[12964,20061],'bytes':7097,'delta_sha256':h(b),'event_counts':counts,'events':rows,'trace_start':start,'trace_all_disabled':end,'no_recorded_serial_input_during_window':True,'status_reads':'Unavailable: archived emulator has seven events, no status-read trace. W1C values are not substituted for missing status reads.','unknown_reads':collections.Counter((x['fields']['block']+':'+x['fields']['offset']) for x in u),'limits':['No trace of the initial counter drawing interval; this window began after the stall was observed.','VNC refresh continues during window. Identical PNG bytes prove repeated identical captured images, not intrinsic guest presentation timestamps.','No SAMPLE capability exists in unchanged HID54; no sampling attempted.','No causal attribution to HID revision or emulator revision; one predecessor-state reproduction.']}
(D/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k!='events'},indent=2))
