# SPDX-License-Identifier: AGPL-3.0-or-later
"""Audit retained run59 third/fourth-window delta without runtime operations."""
import collections,hashlib,json,re
from pathlib import Path
D=Path(__file__).resolve().parent
h=lambda b:hashlib.sha256(b).hexdigest()
b=(D/'guest-errors.345699-459473.log').read_bytes();assert len(b)==459473-345699
results={}
for name,start,end in [('home',345699,409395),('open',409395,459473)]:
 rows=[];pos=start
 for line in b[start-345699:end-345699].splitlines(keepends=True):
  if line.startswith(b'apple_adp_'):
   s=line.decode().strip();rows.append((pos,len(line),h(line),s.split()[0],dict(re.findall(r'(\w+)=([^ ]+)',s))))
  pos+=len(line)
 reads=[x for x in rows if x[3]=='apple_adp_status_read'];writes=[x for x in rows if x[3]=='apple_adp_irq_write' and x[4]['kind']=='status-w1c'];assert len(reads)==len(writes)
 pairs=[]
 for r,w in zip(reads,writes):
  assert r[0]<w[0]
  rv=int(r[4]['value'],16);v=int(w[4]['value'],16);pre=int(w[4]['before'],16);post=int(w[4]['status'],16)
  assert rv==v and post==pre&~v
  intervening=[x for x in rows if r[0]<x[0]<w[0]];assert not intervening
  pairs.append({'read_offset':r[0],'read_sha256':r[2],'write_offset':w[0],'write_sha256':w[2],'value':hex(rv),'before':hex(pre),'after':hex(post)})
 u=[x for x in rows if x[3]=='apple_adp_unknown_mmio' and x[4]['block']=='main' and x[4]['offset']=='0x45004'];assert all(x[4]['value']=='0x0' and x[4]['write']=='0' for x in u)
 results[name]={'range':[start,end],'bytes':end-start,'range_sha256':h(b[start-345699:end-345699]),'events':collections.Counter(x[3] for x in rows),'read_values':collections.Counter(x[4]['value'] for x in reads),'pairs':pairs,'unknown_45004_zero_read_offsets':[x[0] for x in u]}
q=[json.loads(x) for x in (D/'qmp.prefix.jsonl').read_text().splitlines()]
commands=[json.loads(x['raw']) for x in q if x['direction']=='send'];assert not any(x['execute'] in ['human-monitor-command','input-send-event','send-key'] for x in commands)
j=[json.loads(x) for x in (D/'trace-control.prefix.jsonl').read_text().splitlines()]
starts=[i for i,x in enumerate(j) if x['stage']=='start'];assert len(starts)==4
for idx,name in [(2,'home'),(3,'open')]:
 window=j[starts[idx]:starts[idx+1] if idx+1<len(starts) else len(j)]
 en=[x for x in window if x['stage']=='after-enable'];ds=[x for x in window if x['stage']=='after-disable'];assert len(en)==len(ds)==8
 for x in en+ds:
  assert x['response']['return']=={}
  assert any(y['direction']=='receive' and json.loads(y['raw'])==x['response'] for y in q)
 results[name]['enable_times']=[x['time'] for x in en];results[name]['disable_times']=[x['time'] for x in ds]
sub=json.loads((D/'open-submission.json').read_text())
wire=[json.loads(x) for x in (D/'serial-input.prefix.jsonl').read_text().splitlines()]
sent=[x for x in wire if x.get('request_id')=='062c71ec8bfb4287b2627b0569cddd9f' and x['stage']=='before-send']
assert len(sent)==1 and sent[0]['raw']==sub['expected_serial_wire']
assert h(sent[0]['raw'].encode())==sent[0]['sha256']
results['open']['serial_send_time']=sent[0]['time']
results['scope']='Trace order and file-visible brackets only. Home start is the prior counter checkpoint, not an immediate pre-Home checkpoint. No per-event/frame timing or causal attribution.'
(D/'result.json').write_text(json.dumps(results,indent=2)+'\n')
print(json.dumps({k:{z:v[z] for z in ['range','bytes','events','read_values']} for k,v in results.items() if isinstance(v,dict)},indent=2))
