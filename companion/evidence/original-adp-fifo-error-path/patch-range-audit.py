import pathlib,struct,re,json,hashlib
root=pathlib.Path('/home/brandonin/Documents/behavioral-iphone-inferno');p=pathlib.Path('/home/brandonin/.local/share/inferno/native-probe/kernel-original-decoded').read_bytes();source=(root/'hw/arm/apple-silicon/kernel_patches.c').read_text()
def sections(off):
 result={};o=off+32
 for _ in range(struct.unpack_from('<I',p,off+16)[0]):
  cmd,size=struct.unpack_from('<II',p,o)
  if cmd==25:
   segment=p[o+8:o+24].split(b'\0')[0].decode()
   for j in range(struct.unpack_from('<I',p,o+64)[0]):
    q=o+72+j*80;name=p[q:q+16].split(b'\0')[0].decode();va,sz,fo=struct.unpack_from('<QQI',p,q+32);result[(segment,name)]=(va,sz,fo)
  o+=size
 return result
top=sections(0)
def readva(va,n):
 va|=0xffff000000000000
 for (_,s),(a,z,f) in top.items():
  if a<=va and va+n<=a+z:return p[f+va-a:f+va-a+n]
 raise ValueError(hex(va))
def offsetva(va):
 va|=0xffff000000000000
 for (_,s),(a,z,f) in top.items():
  if a<=va<a+z:return f+va-a
 raise ValueError(hex(va))
_,sz,fo=top['__PRELINK_INFO','__kmod_info'];_,_,so=top['__PRELINK_INFO','__kmod_start'];targets={}
for i in range(sz//8):
 info=struct.unpack_from('<Q',p,fo+8*i)[0];start=struct.unpack_from('<Q',p,so+8*i)[0];name=readva(info+16,128).split(b'\0')[0].decode()
 if name in ['com.apple.filesystems.apfs','com.apple.driver.AppleMobileFileIntegrity','com.apple.driver.AppleSEPManager','com.apple.security.AppleImage4']:
  sec=sections(offsetva(start));targets[name]={str(k):[hex(v[0]|0xffff000000000000),hex((v[0]|0xffff000000000000)+v[1])] for k,v in sec.items() if k in [('__TEXT_EXEC','__text'),('__TEXT','__cstring')]}
ranges=[(0xfffffff00975c160,0xfffffff00975c1d8),(0xfffffff009746fc4,0xfffffff009747010),(0xfffffff0097522c4,0xfffffff0097522d0),(0xfffffff00977b650,0xfffffff00977b680)]
va,size,fo=top['__TEXT_EXEC','__text'];blob=p[fo:fo+size];patterns=[]
for func in ['ck_kp_mac_mount_patch','ck_kp_kprintf_patch','ck_kp_amx_patch','ck_kp_cs_patches']:
 chunk=source[source.index('static void '+func):];chunk=chunk[:chunk.index('\nstatic ',1)]
 arrays={}
 for name,body in re.findall(r'static const uint8_t (\w+)\[\] = \{(.*?)\};',chunk,re.S):
  body=re.sub(r'//[^\n]*','',body)
  try:arrays[name]=bytes(int(x.strip(),0) for x in body.split(',') if x.strip())
  except ValueError:pass
 for name,pattern in arrays.items():
  if not (name.startswith('pattern') or name in ['new_pattern','alt']):continue
  maskname=('new_mask' if name=='new_pattern' else 'mask_alt' if name=='alt' else name.replace('pattern','mask'));mask=arrays.get(maskname,b'\xff'*len(pattern));assert len(mask)==len(pattern)
  regex=b''.join(re.escape(bytes([b])) if m==255 else b'.' if m==0 else b'['+b''.join(re.escape(bytes([x])) for x in range(256) if x&m==b)+b']' for b,m in zip(pattern,mask))
  hits=[va+m.start() for m in re.finditer(regex,blob,re.S) if m.start()%4==0]
  near=[hex(h) for h in hits if any(a-4096<=h<z+4096 for a,z in ranges)]
  patterns.append({'function':func,'pattern':name,'hits':[hex(h) for h in hits],'within4096_of_audited_ranges':near})
result={'kext_patch_text_ranges':targets,'global_scan_range':[hex(va),hex(va+size)],'global_pattern_anchors':patterns,'ppl_range':[hex(top['__PPLTEXT','__text'][0]),hex(sum(top['__PPLTEXT','__text'][:2]))],'audited_ranges':[[hex(a),hex(z)] for a,z in ranges]}
print(json.dumps(result,indent=2))
