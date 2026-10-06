#!/usr/bin/env python3
"""Verify InfernoFSPatcher's original-byte sidecar and emit a bounded guest plan."""
import argparse,hashlib,json,pathlib,struct
p=argparse.ArgumentParser(description=__doc__)
for key in ('original','patched','sidecar','output'):p.add_argument('--'+key,type=pathlib.Path,required=True)
for key in ('original-sha256','patched-sha256','patcher-revision'):p.add_argument('--'+key,required=True)
a=p.parse_args()
if a.output.exists() or a.output.with_suffix(a.output.suffix+'.json').exists():p.error('output already exists')
size=a.original.stat().st_size
if not 0<size<=8*1024**3 or a.patched.stat().st_size!=size:p.error('cache size mismatch or unsupported size')
if a.sidecar.stat().st_size>1024*1024:p.error('sidecar exceeds bound')
records=[]
for line in a.sidecar.read_text().splitlines():
 if not line.strip():continue
 try:
  offset_s,data_s=line.split(':',1);offset=int(offset_s,16)
  old=bytes(int(v,16) for v in data_s.split())
 except (ValueError,OverflowError):p.error('malformed original-byte sidecar')
 if not 0<len(old)<=4096 or offset<0 or offset+len(old)>size:p.error('invalid sidecar record')
 records.append((offset,old))
records.sort()
if not 0<len(records)<=65536:p.error('record count out of bounds')
last=0
for offset,old in records:
 if offset<last:p.error('overlapping records')
 last=offset+len(old)
plan=bytearray(struct.pack('<8sQII',b'INFRPAT1',size,len(records),0))
original_hash=hashlib.sha256();patched_hash=hashlib.sha256()
with a.original.open('rb') as original,a.patched.open('rb') as patched:
 cursor=0
 def identical(n):
  while n:
   count=min(n,8*1024*1024);left=original.read(count);right=patched.read(count)
   if len(left)!=count or len(right)!=count or left!=right:p.error('difference outside listed patch records or unexpected EOF')
   original_hash.update(left);patched_hash.update(right);n-=count
 for offset,old in records:
  identical(offset-cursor)
  left=original.read(len(old));new=patched.read(len(old))
  if left!=old or len(new)!=len(old):p.error(f'original sidecar bytes mismatch at {offset:#x}')
  original_hash.update(left);patched_hash.update(new)
  plan.extend(struct.pack('<QII',offset,len(old),0)+old+new);cursor=offset+len(old)
 identical(size-cursor)
 if original.read(1) or patched.read(1):p.error('input changed while reading')
if len(plan)>16*1024*1024:p.error('plan exceeds bound')
if original_hash.hexdigest()!=a.original_sha256 or patched_hash.hexdigest()!=a.patched_sha256:p.error('input SHA256 mismatch')
a.output.parent.mkdir(parents=True,exist_ok=True)
with a.output.open('xb') as f:f.write(plan)
record={'upstream_repository':'https://git.chefkiss.dev/AppleHax/InfernoFSPatcher','upstream_revision':a.patcher_revision,'license':'AGPL-3.0-or-later','original':str(a.original.resolve()),'original_sha256':original_hash.hexdigest(),'patched':str(a.patched.resolve()),'patched_sha256':patched_hash.hexdigest(),'sidecar_sha256':hashlib.sha256(a.sidecar.read_bytes()).hexdigest(),'plan_sha256':hashlib.sha256(plan).hexdigest(),'records':len(records),'replacement_bytes':sum(len(old) for _,old in records),'file_bytes':size,'entire_remaining_file_identical':True,'generator_sha256':hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest(),'guest_applied':False}
a.output.with_suffix(a.output.suffix+'.json').write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps(record,indent=2))
