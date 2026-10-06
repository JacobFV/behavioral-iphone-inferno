import pathlib,re,subprocess,json,struct,uuid,mmap,hashlib
base=pathlib.Path('/home/brandonin/.local/share/inferno/native-probe/spindump-inspection');cache=pathlib.Path('/home/brandonin/.local/share/inferno/fs-patcher-input/System/Library/Caches/com.apple.dyld/dyld_shared_cache_arm64e');fh=cache.open('rb');d=mmap.mmap(fh.fileno(),0,access=mmap.ACCESS_READ)
cacheuuid=str(uuid.UUID(bytes=d[88:104])).upper();mo,mc=struct.unpack_from('<II',d,16);maps=[struct.unpack_from('<QQQ',d,mo+i*32)for i in range(mc)]
def fileoff(vm):
 for a,n,o in maps:
  if a<=vm<a+n:return o+vm-a
 raise ValueError(hex(vm))
def z(o):return d[o:d.find(b'\0',o)].decode()
io,ic=struct.unpack_from('<II',d,24);images={z(struct.unpack_from('<I',d,io+i*32+24)[0]):struct.unpack_from('<Q',d,io+i*32)[0]for i in range(ic)}
def imageuuid(buf,off):
 n=struct.unpack_from('<I',buf,off+16)[0];p=off+32
 for _ in range(n):
  cmd,size=struct.unpack_from('<II',buf,p)
  if cmd==0x1b:return str(uuid.UUID(bytes=buf[p+8:p+24])).upper()
  p+=size
patch=pathlib.Path('/home/brandonin/.local/share/inferno/fs-patcher-modified/software-rendering.infrpat').read_bytes();count=struct.unpack_from('<I',patch,16)[0];pos=24;ranges=[]
for _ in range(count):
 off,n,_=struct.unpack_from('<QII',patch,pos);ranges.append((off,off+n));pos+=16+2*n
for target in ['backboardd','springboard']:
 p=base/f'boot49-{target}-001';text=(p/'output.bin').read_text();actualuuid=re.search(r'Shared Cache:\s+(\S+)',text)[1];assert actualuuid==cacheuuid;slide=int(re.search(r', slide (0x[0-9a-f]+)',text)[1],16)
 addresses=sorted({int(x,16)for x in re.findall(r'\[(0x[0-9a-f]+)\]',text)if 0x180000000<=int(x,16)<0x200000000});r=subprocess.run([str(base.parent/'symbolize-cache'),str(cache)],input=''.join(f'{a-slide:x}\n'for a in addresses),text=True,capture_output=True,check=True);(p/'symbolizer-raw.txt').write_text(r.stdout);(p/'symbolizer-stderr.txt').write_text(r.stderr);table={int(l.split('\t')[0],16)+slide:l.split('\t',1)[1]for l in r.stdout.splitlines()if '\t'in l};lines=[]
 for l in text.splitlines():
  m=re.search(r'\[(0x[0-9a-f]+)\]',l)
  if m and int(m[1],16)in table:l+='  => '+table[int(m[1],16)]
  lines.append(l)
 (p/'symbolized.txt').write_text('\n'.join(lines)+'\n');checks=[]
 for l in text.splitlines():
  m=re.match(r'\s+(0x[0-9a-f]+) -\s+(?:0x[0-9a-f]+|\?\?\?).*?<([A-F0-9-]+)>\s+(/.*)$',l)
  if not m:continue
  path=m[3]
  if path in images:
   vm=images[path];found=imageuuid(d,fileoff(vm));assert found==m[2];assert int(m[1],16)-slide==vm;checks.append({'path':path,'uuid':found,'preferred_base':hex(vm),'runtime_base':m[1]})
  elif path=='/usr/libexec/backboardd':
   original=base.parent/'hid-routing-inspection/Volume1/usr/libexec/backboardd';found=imageuuid(original.read_bytes(),0);assert found==m[2];checks.append({'path':path,'uuid':found,'runtime_base':m[1],'scope':'standalone frames retained as original image+offset'})
 overlaps=[]
 for a in addresses:
  o=fileoff(a-slide)
  if any(o<z and o+4>x for x,z in ranges):overlaps.append(hex(a))
 audit={'cache_uuid':cacheuuid,'actual_slide':hex(slide),'mapped_unique_cache_PCs':len(addresses),'image_uuid_and_base_checks':checks,'sparse_patch_plan_sha256':hashlib.sha256(patch).hexdigest(),'sampled_PC_instruction_patch_overlaps':overlaps,'scope':'Nearest-symbol original cache attribution; no kernel mapping. Empty sampled-PC overlap does not prove patched functions absent elsewhere in call paths.'};(p/'symbolication-audit.json').write_text(json.dumps(audit,indent=2)+'\n');print(target,len(addresses),len(checks),overlaps)
