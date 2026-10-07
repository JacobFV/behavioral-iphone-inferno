# SPDX-License-Identifier: AGPL-3.0-or-later
import collections,hashlib,json,re
from pathlib import Path
D=Path(__file__).resolve().parent
b=(D/'trace.62449-76767.log').read_bytes();assert len(b)==14318
rows=[];off=62449
for l in b.split(b'\n'):
 if l.startswith(b'apple_adp_'):
  s=l.decode();rows.append({'offset':off,'event':s.split()[0],'fields':dict(re.findall(r'(\w+)=([^ ]+)',s)),'sha256':hashlib.sha256(l+b'\n').hexdigest()})
 off+=len(l)+1
counts=collections.Counter(x['event'] for x in rows);reads=[x for x in rows if x['event']=='apple_adp_status_read'];w=[x for x in rows if x['event']=='apple_adp_irq_write'];assert len(reads)==len(w)
for a,z in zip(reads,w):
 assert a['offset']<z['offset'] and a['fields']['value']==z['fields']['value']==z['fields']['before']=='0x400' and z['fields']['status']=='0x0'
 assert not any(a['offset']<x['offset']<z['offset'] for x in rows)
assert not any(counts[n] for n in ['apple_adp_submit','apple_adp_bh','apple_adp_pipe','apple_adp_gp_config_write'])
j=[json.loads(x) for x in (D/'trace-control.prefix.jsonl').read_text().splitlines()];start=[i for i,x in enumerate(j) if x['stage']=='start'][-1];j=j[start:];en=[x for x in j if x['stage']=='after-enable'];ds=[x for x in j if x['stage']=='after-disable'];assert len(en)==len(ds)==9
q=[json.loads(x) for x in (D/'qmp.prefix.jsonl').read_text().splitlines()]
for x in en+ds:assert x['response']['return']=={} and any(y['direction']=='receive' and json.loads(y['raw'])==x['response'] for y in q)
assert not any(json.loads(x['raw']).get('execute') in ['human-monitor-command','input-send-event','send-key'] for x in q if x['direction']=='send')
window=[j[0]['time'],[x['time'] for x in j if x['stage']=='stop-result'][-1]]
wire=[json.loads(x) for x in (D/'serial-input.prefix.jsonl').read_text().splitlines()];assert not any(window[0]<=x['time']<=window[1] for x in wire)
caller=json.loads((D/'callers.json').read_text())
r={'range':[62449,76767],'trace_sha256':hashlib.sha256(b).hexdigest(),'counts':counts,'read_w1c_pairs':len(reads),'window':window,'caller_result':caller,'events':rows,'scope':'Explicit VNC Home input; no QMP/HMP or serial input in window. Exposed PC/LR only; callback completion and presentation timing not established.'}
(D/'result.json').write_text(json.dumps(r,indent=2)+'\n');print(counts);print('pairs',len(reads));print('caller',caller.keys())
