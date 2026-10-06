#!/usr/bin/env python3
"""Reconstruct actual encoded sample payloads independently of result assertions."""
import pathlib,json,hashlib
p=pathlib.Path(__file__).parent;prov=json.loads((p/'provenance.json').read_text())
for n,v in prov['files'].items():
 b=(p/n).read_bytes();assert len(b)==v['size']and hashlib.sha256(b).hexdigest()==v['sha256']
s=(p/'serial-prefix.log').read_bytes();results=[]
for name in ['backboardd','springboard']:
 t=p/name;r=json.loads((t/'result.json').read_text());out=bytearray();chunks=0;last=None
 for row in r['records']:
  ref=row['reference'];raw=s[ref['byte_start']:ref['byte_end']];assert hashlib.sha256(raw).hexdigest()==ref['sha256'];text=raw.rstrip(b'\n').rstrip(b'\r').decode();assert text==ref['text'];fields=dict(x.split('=',1)for x in text.split()[1:]);assert fields==row['fields']
  if row['kind']=='DATA':
   data=bytes.fromhex(fields['hex']);assert int(fields['offset'])==len(out)and int(fields['bytes'])==len(data);out.extend(data);chunks+=1
  if row['kind']=='END':last=fields
 assert last and all(last[k]=='0'for k in ['truncated','read_errno','output_error','raw_status','wait_errno','killed']);assert all(last[k]=='1'for k in ['eof','reaped','target_post_match','complete']);assert len(out)==int(last['bytes'])and chunks==int(last['chunks']);assert bytes(out)==(t/'original-output.txt').read_bytes();assert b'20 (100ms sampling interval)'in out
 results.append({'target':name,'bytes':len(out),'chunks':chunks,'sha256':hashlib.sha256(out).hexdigest(),'pid':int(last['pid']),'unique':int(last['unique']),'idversion':int(last['idversion']),'transport_and_tool_complete':True,'actual_20_samples':True})
(p/'audit.json').write_text(json.dumps(results,indent=2)+'\n');print(json.dumps(results))
