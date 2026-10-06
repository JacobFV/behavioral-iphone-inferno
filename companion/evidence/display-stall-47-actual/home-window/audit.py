#!/usr/bin/env python3
import pathlib,json,hashlib,collections
p=pathlib.Path(__file__).parent
for n,v in json.loads((p/'provenance.json').read_text())['files'].items():
 b=(p/n).read_bytes();assert len(b)==v['size']and hashlib.sha256(b).hexdigest()==v['sha256']
a=json.loads((p/'trace-before-home.json').read_text())['checkpoint']['size'];assert a==58015;b=(p/'guest-errors-prefix.log').read_bytes();c=collections.Counter();u=collections.Counter()
for l in b[a:].decode().splitlines():
 if not l.startswith('apple_adp_'):continue
 f=l.split();n=f[0];v=dict(x.split('=',1)for x in f[1:]);c[n]+=1
 assert n not in('apple_adp_submit','apple_adp_bh','apple_adp_pipe','apple_adp_gp_config_write')
 if n=='apple_adp_unknown_mmio':
  k=(v['block'],v['pipe'],v['write'],v['offset'],v['value']);u[k]+=1
  assert k in[('gp','0','0','0x184','0x0'),('gp','1','0','0x184','0x0'),('main','-1','0','0x45004','0x0')]
j=[json.loads(l)for l in(p/'display-trace-control-prefix.jsonl').read_text().splitlines()];starts=[x for x in j if x['stage']=='start'];assert len(starts)==2 and j[-1]['all_disabled']
q={}
for l in(p/'qmp-trace-excerpt.jsonl').read_text().splitlines():
 r=json.loads(l);x=json.loads(r['raw']);q[(r['direction'],x['id'])]=x
for r in j:
 if 'response'not in r:continue
 i=r['response']['id'];assert 'error'not in r['response']and q[('receive',i)]==r['response'];assert q[('send',i)]['arguments']=={'name':r['event'],'enable':r['stage']=='after-enable'}
f=json.loads((p/'continuous-report.json').read_text());hashes=[x['sha256']for x in f['captures']];assert len(set(hashes))==1
result={'bytes':[a,len(b)],'counts':dict(c),'unknown_reads':[{'key':k,'count':v}for k,v in u.items()],'window_seconds':j[-1]['time']-starts[-1]['time'],'all_disabled':True,'capture_count':len(hashes),'capture_hashes':sorted(set(hashes)),'interpretation':['One ordinary F6 Home has genuine same-PID299/main6452403977 resign/background records; initial combined CLI parse error is not another input.','No submissions or configuration/unknown writes despite Home lifecycle. Same three zero reads and ready/W1C continue, supporting upstream submission stall beyond owned counter handler.','Healthy46 Home/reopen brackets had11/15 complete draw cycles. No single unknown register return distinguishes47; no behavioral register patch justified.','Root reviewed stale counter0; raw capture equality retained. Buffer offsets are not device timestamps; live prefix is not final-run evidence.']}
(p/'audit.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items()if k not in('interpretation','unknown_reads')}))
