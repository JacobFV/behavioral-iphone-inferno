#!/usr/bin/env python3
"""Independent raw trace bracket audit; no guest execution."""
import pathlib,json,hashlib,collections
p=pathlib.Path(__file__).parent
for n,v in json.loads((p/'provenance.json').read_text())['files'].items():
 b=(p/n).read_bytes();assert len(b)==v['size'] and hashlib.sha256(b).hexdigest()==v['sha256']
r=json.loads((p/'report-final.json').read_text());assert r['exit_code']==0 and r.get('error') is None
s=json.loads((p/'counter-submission.json').read_text());a=s['trace_after']['size'];assert a==s['trace_before']['size']==39601
z=json.loads((p/'trace-after-counter-review.json').read_text())['checkpoint'];assert z['size']==84582 and z['inode']==s['trace_after']['inode']
b=(p/'guest-errors-final.log').read_bytes();e=[];offset=0
for l in b.splitlines(keepends=True):
 if l.startswith(b'apple_adp_'):
  f=l.decode().split();e.append((offset,f[0],dict(x.split('=',1) for x in f[1:])))
 offset+=len(l)
e=[x for x in e if a<=x[0]<z['size']];c=collections.Counter(x[1] for x in e);active=False;cycles=0;out=[];sources=[];unknown=collections.Counter()
for off,n,f in e:
 if n=='apple_adp_bh':
  if f['phase']=='enter':assert not active;active=True;out=[]
  else:assert active and out==[('0','drawn'),('1','disabled')];active=False;cycles+=1
 if n=='apple_adp_pipe':
  assert active;out.append((f['pipe'],f['outcome']))
  if f['outcome']=='drawn':sources.append(f['source'])
 if n=='apple_adp_unknown_mmio' and f['write']=='0':unknown[(f['block'],f['pipe'],f['offset'],f['value'])]+=1
assert not active and cycles==c['apple_adp_submit']==7
j=[json.loads(l) for l in (p/'display-trace-control-final.jsonl').read_text().splitlines()];assert j[-1]['all_disabled']
q={}
for l in (p/'qmp-trace-excerpt.jsonl').read_text().splitlines():
 x=json.loads(l);d=json.loads(x['raw']);q[(x['direction'],d['id'])]=d
for x in j:
 if 'response'not in x:continue
 i=x['response']['id'];assert 'error'not in x['response'] and q[('receive',i)]==x['response'];assert q[('send',i)]['arguments']=={'name':x['event'],'enable':x['stage']=='after-enable'}
result={'bracket':[a,z['size']],'counts':dict(c),'complete_cycles':cycles,'draw_sources_in_order':sources,'unknown_reads':[{'block':k[0],'pipe':k[1],'offset':k[2],'value':k[3],'count':v} for k,v in unknown.items()],'event_offsets':e,'limitations':['Seven complete draws occur between file-visible counter submission and reviewed frame checkpoints; these are not seven causally attributed counter draws.','No per-event timestamps or surface contents; no presentation-latency attribution.','All repeated unknown read values are zero, including GP +0x184/main +0x45004 23 times and other offsets seven times. These coexist with successful draws.','Stalled44 traced no unknown-MMIO category, so absence/presence or values at those offsets cannot be compared retrospectively. Its known submit/BH/pipe absence is the supported contrast.','49 is a healthy diagnostic run with unchanged rendering semantics, not a fix or causal explanation of41/44.']}
(p/'audit.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k not in ['event_offsets','unknown_reads','limitations']}))
