#!/usr/bin/env python3
"""Decode only retained fixed-register HMP replies; no guest interaction."""
import json,re,hashlib,pathlib
P=pathlib.Path(__file__).parent
base=0x230000000
registers=[('int_status',0x45818),('int_enable',0x4581c),('version',0x46020),('frame_size',0x4603c)]+[(f'gp{p}_{n}',0x50000+p*0x8000+o) for p in range(2) for n,o in [('control',4),('pixel_format',28),('data_start',48),('data_end',64),('stride',96),('src_dimensions',112),('dest_dimensions',128)]]
results=[]
for path in sorted(P.glob('display-*.json')):
 r=json.loads(path.read_text());v={}
 for row,(name,offset) in zip(r['registers'],registers,strict=True):
  m=re.fullmatch(r'([0-9a-f]+): 0x([0-9a-f]{8})\r\n',row['response']['return'])
  assert m and row['name']==name and int(m[1],16)==int(row['address'],16)==base+offset
  v[name]=int(m[2],16)
 result={'file':path.name,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'read_span_ms':(r['end_monotonic_ns']-r['start_monotonic_ns'])/1e6,'raw_values':v,'status_and_enable':v['int_status']&v['int_enable'],'pipes':[]}
 for p in range(2):
  k=f'gp{p}_';dim=v[k+'src_dimensions'];width,height=dim>>16,dim&65535
  result['pipes'].append({'pipe':p,'run':bool(v[k+'control']&1),'enabled':bool(v[k+'control']&(1<<31)),'compressed':bool(v[k+'pixel_format']&(1<<30)),'width':width,'height':height,'stride':v[k+'stride'],'read_bytes':height*v[k+'stride'],'data_range_bytes':v[k+'data_end']-v[k+'data_start']})
 results.append(result)
(P/'audit.json').write_text(json.dumps({'snapshots':results,'limits':['Sequential nonconsuming register snapshots, not frame counters or atomic hardware state.','Status0 does not imply no interrupts or frames occurred. Enabled GP0 does not establish a draw callback ran or DMA pixels changed.','Buffer addresses are stored register values; no DMA/framebuffer memory read by this query.','Source mapping/read provenance retained in display-register-query/inspection.json and original-dt-fields.json.']},indent=2)+'\n')
