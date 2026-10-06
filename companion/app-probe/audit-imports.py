#!/usr/bin/env python3
"""Read-only export-trie audit for this fixture against an original monolithic cache.
SPDX-License-Identifier: AGPL-3.0-or-later
Self-authored file-format reader; no implementation symbols or binaries are copied.
"""
import argparse, hashlib, json, mmap, struct, subprocess
from pathlib import Path

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--cache',type=Path,required=True)
p.add_argument('--objdump',required=True)
p.add_argument('--output',type=Path,required=True)
p.add_argument('executables',type=Path,nargs='+')
a=p.parse_args()
f=a.cache.open('rb'); data=mmap.mmap(f.fileno(),0,access=mmap.ACCESS_READ)
def u32(off):return struct.unpack_from('<I',data,off)[0]
def z(off):return data[off:data.find(b'\0',off)].decode()
assert data[:7]==b'dyld_v1', 'expected original dyld cache'
mo,mc=struct.unpack_from('<II',data,16)
assert mo<0x18c,'split cache is not supported by this narrow audit'
mappings=[struct.unpack_from('<QQQ',data,mo+i*32) for i in range(mc)]
def fileoff(vm):
 for addr,size,off in mappings:
  if addr<=vm<addr+size:return off+vm-addr
 raise ValueError('unmapped image')
io,ic=struct.unpack_from('<II',data,24)
images={z(u32(io+i*32+24)):fileoff(struct.unpack_from('<Q',data,io+i*32)[0]) for i in range(ic)}
parsed={}
def image(path):
 if path in parsed:return parsed[path]
 base=images[path];assert u32(base)==0xfeedfacf
 off=base+32; deps=[]; rex=[]; start=size=0
 for _ in range(u32(base+16)):
  cmd,n=struct.unpack_from('<II',data,off);assert n>=8
  if cmd in (0xc,0x80000018,0x8000001f,0x80000023):
   dep=z(off+u32(off+8));deps.append(dep)
   if cmd==0x8000001f:rex.append(dep)
  if cmd==0x80000022 or cmd==0x22:start,size=struct.unpack_from('<II',data,off+40)
  if cmd==0x80000033:start,size=struct.unpack_from('<II',data,off+8)
  off+=n
 exports={}
 def uleb(pos):
  value=shift=0
  while True:
   byte=data[pos];pos+=1;value|=(byte&127)<<shift
   if byte<128:return value,pos
   shift+=7;assert shift<70
 def walk(relative,prefix,ancestors):
  assert relative<size and relative not in ancestors
  pos=start+relative;terminal,pos=uleb(pos);end=pos+terminal
  if terminal:
   flags,cursor=uleb(pos)
   if flags&8:
    ordinal,cursor=uleb(cursor);exports[prefix]={'reexport':deps[ordinal-1],'symbol':z(cursor) or prefix}
   else:exports[prefix]={'defined':True}
  count=data[end];pos=end+1
  for _ in range(count):
   edge=z(pos);pos+=len(edge.encode())+1;child,pos=uleb(pos)
   walk(child,prefix+edge,ancestors|{relative})
 if size:walk(0,'',set())
 parsed[path]=(exports,rex)
 return parsed[path]
def resolve(path,symbol,seen=None):
 seen=set() if seen is None else seen
 if (path,symbol) in seen or path not in images:return None
 seen=seen|{(path,symbol)};exports,rex=image(path)
 if symbol in exports:
  item=exports[symbol]
  if 'defined' in item:return [path]
  child=resolve(item['reexport'],item['symbol'],seen)
  return [path]+child if child else None
 for dep in rex:
  child=resolve(dep,symbol,seen)
  if child:return [path]+child
 return None
providers={'libSystem':'/usr/lib/libSystem.B.dylib','libobjc':'/usr/lib/libobjc.A.dylib',
 'Foundation':'/System/Library/Frameworks/Foundation.framework/Foundation',
 'UIKit':'/System/Library/Frameworks/UIKit.framework/UIKit',
 'CoreServices':'/System/Library/Frameworks/CoreServices.framework/CoreServices'}
results=[]
for exe in a.executables:
 raw=subprocess.check_output([a.objdump,'--macho','--bind','--lazy-bind',str(exe)],text=True)
 for line in raw.splitlines():
  fields=line.split()
  if not fields or not fields[0].startswith('__'):continue
  provider,symbol=fields[-2:];path=providers[provider];chain=resolve(path,symbol)
  results.append({'executable':str(exe),'symbol':symbol,'declared_provider':path,'export_chain':chain})
report={'cache':str(a.cache),'cache_sha256':hashlib.file_digest(f,'sha256').hexdigest(),
 'executables':{str(x):hashlib.sha256(x.read_bytes()).hexdigest() for x in a.executables},
 'method':'Mach-O export tries plus explicit reexports; local/debug symbol tables are not used',
 'results':results,'passed':all(x['export_chain'] for x in results)}
a.output.write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'passed':report['passed'],'imports':len(results),'missing':[x for x in results if not x['export_chain']]}))
raise SystemExit(0 if report['passed'] else 1)
