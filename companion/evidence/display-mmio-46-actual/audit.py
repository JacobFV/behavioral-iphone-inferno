#!/usr/bin/env python3
"""Recompute separate counter and warm draw brackets from original trace."""
import pathlib,json,hashlib,collections
p=pathlib.Path(__file__).parent
for n,v in json.loads((p/'provenance.json').read_text())['files'].items():
 b=(p/n).read_bytes();assert len(b)==v['size'] and hashlib.sha256(b).hexdigest()==v['sha256']
r=json.loads((p/'report.json').read_text());assert r['exit_code']==0 and r.get('error')is None
b=(p/'guest-errors.log').read_bytes();events=[];off=0
for l in b.splitlines(keepends=True):
 if l.startswith(b'apple_adp_'):
  f=l.decode().split();events.append((off,f[0],dict(x.split('=',1) for x in f[1:])))
 off+=len(l)
j=[json.loads(l)for l in(p/'display-trace-control.jsonl').read_text().splitlines()];assert j[-1]['all_disabled'];q={}
for l in(p/'qmp-trace-excerpt.jsonl').read_text().splitlines():
 x=json.loads(l);y=json.loads(x['raw']);q[(x['direction'],y['id'])]=y
for x in j:
 if 'response'not in x:continue
 i=x['response']['id'];assert 'error'not in x['response'] and q[('receive',i)]==x['response'];assert q[('send',i)]['arguments']=={'name':x['event'],'enable':x['stage']=='after-enable'}
def cp(n):return json.loads((p/n).read_text())['checkpoint']['size']
s=json.loads((p/'counter-submission.json').read_text());assert s['trace_before']['size']==s['trace_after']['size']==45244
regions=[]
for name,a,z in [('counter',45244,cp('trace-after-counter-review.json')),('Home',cp('trace-before-home.json'),cp('trace-after-home-review.json')),('after_Home_through_reopen_review',cp('trace-after-home-review.json'),cp('trace-after-reopen-review.json'))]:
 es=[e for e in events if a<=e[0]<z];c=collections.Counter(e[1]for e in es);sources=[];u=collections.Counter();active=False;cycles=0;draws=[]
 for o,n,f in es:
  if n=='apple_adp_bh':
   if f['phase']=='enter':assert not active;active=True;draws=[]
   else:assert active and draws==[('0','drawn'),('1','disabled')];active=False;cycles+=1
  if n=='apple_adp_pipe':
   assert active;draws.append((f['pipe'],f['outcome']))
   if f['outcome']=='drawn':sources.append(f['source'])
  if n=='apple_adp_unknown_mmio'and f['write']=='0':u[(f['block'],f['pipe'],f['offset'],f['value'])]+=1
 assert not active
 regions.append({'name':name,'bytes':[a,z],'counts':dict(c),'complete_cycles':cycles,'sources':sources,'unknown_reads':[{'block':k[0],'pipe':k[1],'offset':k[2],'value':k[3],'count':v}for k,v in u.items()]})
assert regions[0]['complete_cycles']==7
result={'regions':regions,'windows':[{'stage':x['stage'],'time':x['time'],'seconds':x.get('seconds'),'all_disabled':x.get('all_disabled')}for x in j if x['stage']in('start','stop-result')],'limits':['File-visible boundaries do not establish per-event times or causally attribute individual draws to gestures.','No unknown-MMIO trace exists for stalled44; only known submit/BH/pipe absence can be compared.','Healthy46 repeats45 behavior and supports continued rendering across Home/reopen; not a fix for41/44.']}
(p/'audit.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps([{k:v for k,v in x.items()if k not in('sources','unknown_reads')}for x in regions]))
