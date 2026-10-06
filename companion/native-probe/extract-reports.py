#!/usr/bin/env python3
"""Validate bounded guest console exports and retain reports outside Git."""
import argparse,hashlib,json,re
from pathlib import Path
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--serial',type=Path,required=True)
p.add_argument('--output',type=Path,required=True)
a=p.parse_args();raw=a.serial.read_bytes().replace(b'\r',b'')
a.output.mkdir(parents=True,exist_ok=False);records=[]
pattern=rb'INFERNO_REPORT_EXPORT_BEGIN name=([^\n]+) size=(\d+) limit=524288\n(.*?)\nINFERNO_REPORT_EXPORT_END bytes=(\d+) fnv1a64=([0-9a-f]+) complete=(\d)'
for m in re.finditer(pattern,raw,re.S):
 name=m[1].decode();body=m[3];fnv=14695981039346656037
 for byte in body:fnv=((fnv^byte)*1099511628211)&0xffffffffffffffff
 if Path(name).name!=name:raise ValueError('unsafe report filename')
 if len(body)!=int(m[4]) or f'{fnv:016x}'!=m[5].decode():raise ValueError('console export integrity mismatch: '+name)
 if m[6]!=b'1' or len(body)!=int(m[2]):raise ValueError('incomplete report export: '+name)
 (a.output/name).write_bytes(body)
 records.append({'name':name,'bytes':len(body),'sha256':hashlib.sha256(body).hexdigest(),'fnv1a64':f'{fnv:016x}'})
pattern=rb'INFERNO_OWNED_HEX_BEGIN path=([^\n]+) size=(\d+)\n(.*?)INFERNO_OWNED_HEX_END bytes=(\d+) complete=(\d)'
for m in re.finditer(pattern,raw,re.S):
 name='owned-'+Path(m[1].decode()).name;body=bytes.fromhex(m[3].decode())
 if m[5]!=b'1' or len(body)!=int(m[2]) or len(body)!=int(m[4]):raise ValueError('incomplete owned export')
 (a.output/name).write_bytes(body);records.append({'name':name,'bytes':len(body),'sha256':hashlib.sha256(body).hexdigest()})
record={'serial':str(a.serial.resolve()),'serial_sha256':hashlib.sha256(a.serial.read_bytes()).hexdigest(),'files':records,'normalization':'Serial console CR removed; report byte count and guest FNV1a64 validated before writing.'}
(a.output/'exports.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record,indent=2))
