#!/usr/bin/env python3
"""Recompute first stalled seven-event MMIO window from retained raw prefix."""
import pathlib,json,hashlib,collections
p=pathlib.Path(__file__).parent;prov=json.loads((p/'provenance.json').read_text())
for n,v in prov['files'].items():
 b=(p/n).read_bytes();assert len(b)==v['size'] and hashlib.sha256(b).hexdigest()==v['sha256']
b=(p/'guest-errors-prefix.log').read_bytes();s=json.loads((p/'counter-submission.json').read_text());a=s['trace_before']['size'];assert a==s['trace_after']['size']==40424
z=json.loads((p/'trace-after-counter-review.json').read_text())['checkpoint'];assert z['size']==46108
for c in(s['trace_before'],s['trace_after'],z):assert c['inode']==prov['guest_log_identity']['inode']and c['device']==prov['guest_log_identity']['device']
e=[];off=0
for l in b.splitlines(keepends=True):
 if l.startswith(b'apple_adp_'):
  f=l.decode().split();e.append((off,f[0],dict(x.split('=',1)for x in f[1:])))
 off+=len(l)
j=[json.loads(l)for l in(p/'display-trace-control-prefix.jsonl').read_text().splitlines()];assert j[-1]['all_disabled']and len(j[0]['events'])==7
q={}
for l in(p/'qmp-trace-excerpt.jsonl').read_text().splitlines():
 r=json.loads(l);x=json.loads(r['raw']);q[(r['direction'],x['id'])]=x
for r in j:
 if 'response'not in r:continue
 i=r['response']['id'];assert 'error'not in r['response']and q[('receive',i)]==r['response'];assert q[('send',i)]['arguments']=={'name':r['event'],'enable':r['stage']=='after-enable'}
regions=[]
for label,lo,hi in [('before_counter',0,a),('counter_through_review',a,z['size']),('review_through_disabled_prefix',z['size'],len(b))]:
 es=[x for x in e if lo<=x[0]<hi];c=collections.Counter(x[1]for x in es);u=collections.Counter((x[2]['block'],x[2]['pipe'],x[2]['write'],x[2]['offset'],x[2]['value'])for x in es if x[1]=='apple_adp_unknown_mmio')
 regions.append({'label':label,'bytes':[lo,hi],'counts':dict(c),'unknown_mmio':[{'block':k[0],'pipe':k[1],'write':k[2],'offset':k[3],'value':k[4],'count':v}for k,v in u.items()]})
for o,n,f in e:
 if o<a:continue
 assert n not in('apple_adp_submit','apple_adp_bh','apple_adp_pipe','apple_adp_gp_config_write')
 if n=='apple_adp_unknown_mmio':assert(f['block'],f['pipe'],f['write'],f['offset'],f['value'])in[('gp','0','0','0x184','0x0'),('gp','1','0','0x184','0x0'),('main','-1','0','0x45004','0x0')]
active=False;cycles=0;draws=[]
for o,n,f in e:
 if n=='apple_adp_bh':
  if f['phase']=='enter':assert not active;active=True;draws=[]
  else:assert active and draws==[('0','drawn'),('1','disabled')];active=False;cycles+=1
 if n=='apple_adp_pipe':assert active;draws.append((f['pipe'],f['outcome']))
assert not active and cycles==5
capture=json.loads((p/'continuous-report.json').read_text());hashes=[x['sha256']for x in capture['captures']]
result={'regions':regions,'completed_pre_counter_draw_cycles':cycles,'last_submit':next(x for x in reversed(e)if x[1]=='apple_adp_submit'),'last_bh_exit':next(x for x in reversed(e)if x[1]=='apple_adp_bh'and x[2]['phase']=='exit'),'window_seconds':j[-1]['time']-j[0]['time'],'capture_count':len(hashes),'capture_hashes':sorted(set(hashes)),'comparison':['Healthy45 counter bracket contains6 complete draws; healthy46 contains7. Their same three unimplemented read addresses also return0, interleaved with submissions/configuration.','Stalled47 aftercounter has no submit/BH/pipe/GPconfig trace and no unknown writes. Only ready IRQs, guest W1C and three repeated unknown zero reads remain.','Therefore no newly exposed unknown-MMIO write or unique zero-read value establishes a register fix. Missing submissions remain upstream of modeled submit.','Original compositor stack sampling is a next diagnostic, not a recovery operation.','Trace file offsets are buffered host-visible boundaries; no individual event timestamps or causal per-tap presentation attribution.','Live prefix after deadline, not final-run evidence; capture equality is raw fact, counter0 interpretation belongs to parent visual review.']}
(p/'audit.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items()if k not in('regions','comparison')}));print(json.dumps([{k:v for k,v in r.items()if k!='unknown_mmio'}for r in regions]))
