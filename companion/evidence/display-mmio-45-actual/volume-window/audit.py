#!/usr/bin/env python3
"""Recompute window volume and register patterns from retained raw bytes."""
import pathlib,json,hashlib,collections
p=pathlib.Path(__file__).parent
prov=json.loads((p/'provenance.json').read_text())
for name,v in prov['files'].items():
 b=(p/name).read_bytes();assert len(b)==v['size'] and hashlib.sha256(b).hexdigest()==v['sha256']
a=json.loads((p/'trace-before-volume.json').read_text())['checkpoint'];z=json.loads((p/'trace-after-volume.json').read_text())['checkpoint'];assert (a['device'],a['inode'])==(z['device'],z['inode'])
b=(p/'guest-errors-prefix.log').read_bytes();assert len(b)==z['size']
j=[json.loads(l) for l in (p/'display-trace-control-prefix.jsonl').read_text().splitlines()];assert j[-1]['all_disabled']
q={}
for l in (p/'qmp-trace-excerpt.jsonl').read_text().splitlines():
 r=json.loads(l); x=json.loads(r['raw']);q[(r['direction'],x['id'])]=x
for r in j:
 if 'response' not in r:continue
 assert 'error' not in r['response'];i=r['response']['id'];assert q[('receive',i)]==r['response'];assert q[('send',i)]['arguments']=={'name':r['event'],'enable':r['stage']=='after-enable'}
e=[]
for l in b[a['size']:].decode().splitlines():
 if l.startswith('apple_adp_'):
  f=l.split();e.append((f[0],dict(x.split('=',1) for x in f[1:])))
u=collections.Counter();v=collections.defaultdict(set);active=False;cycles=0;out=[]
for name,f in e:
 if name=='apple_adp_unknown_mmio':
  k=(f['block'],f['pipe'],f['write'],f['offset']);u[k]+=1;v[k].add(f['value'])
 if name=='apple_adp_bh':
  if f['phase']=='enter':assert not active;active=True;out=[]
  else:assert active and out==[('0','drawn'),('1','disabled')];active=False;cycles+=1
 if name=='apple_adp_pipe':assert active;out.append((f['pipe'],f['outcome']))
assert not active
duration=j[-1]['time']-j[0]['time']
result={'bytes':z['size']-a['size'],'window_seconds':duration,'bytes_per_second':(z['size']-a['size'])/duration,'counts':dict(collections.Counter(n for n,f in e)),'complete_draw_cycles':cycles,'unknown_groups':[{'block':k[0],'pipe':int(k[1]),'write':bool(int(k[2])),'offset':k[3],'count':n,'values':sorted(v[k])} for k,n in u.most_common()],'interpretation':'This transition window contains 23 complete draws despite repeated unimplemented reads returning zero. It establishes feasible bounded trace volume, not the cause of boot44 missing submissions. No exact per-event or presentation timestamps.'}
(p/'audit.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k!='unknown_groups'}))
