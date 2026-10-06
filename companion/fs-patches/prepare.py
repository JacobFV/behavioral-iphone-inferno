#!/usr/bin/env python3
"""Add a bounded reviewed plan to an isolated recovery ramdisk; no disk patching."""
import argparse,hashlib,json,pathlib,struct,subprocess
p=argparse.ArgumentParser(description=__doc__)
for key in ('base-preparer','profile','raw-ramdisk','probe','hfsplus','helper','plan','output'):
 p.add_argument('--'+key,type=pathlib.Path,required=True)
for key in ('plan-sha256','original-sha256','patched-sha256'):p.add_argument('--'+key,required=True)
a=p.parse_args()
sha=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
plan=a.plan.read_bytes()
if sha(a.plan)!=a.plan_sha256:p.error('plan SHA256 mismatch')
if len(plan)<24 or len(plan)>16*1024*1024:p.error('plan size invalid')
magic,size,count,reserved=struct.unpack_from('<8sQII',plan)
if magic!=b'INFRPAT1' or reserved or not 0<size<=8*1024**3 or not 0<count<=65536:p.error('invalid header')
pos=24;last=0
for i in range(count):
 if pos+16>len(plan):p.error('truncated record')
 offset,n,reserved=struct.unpack_from('<QII',plan,pos);pos+=16
 if reserved or not 0<n<=4096 or offset<last or offset+n>size or pos+2*n>len(plan):p.error('invalid record')
 last=offset+n;pos+=2*n
if pos!=len(plan):p.error('trailing plan bytes')
try:digests=bytes.fromhex(a.original_sha256+a.patched_sha256)
except ValueError:p.error('invalid digests')
if len(a.original_sha256)!=64 or len(a.patched_sha256)!=64 or len(digests)!=64:p.error('invalid digest lengths')
subprocess.run(['python3',str(a.base_preparer),'--profile',str(a.profile),'--raw-ramdisk',str(a.raw_ramdisk),'--probe',str(a.probe),'--hfsplus',str(a.hfsplus),'--disk-helper',str(a.helper),'--output',str(a.output)],check=True)
raw=a.output/'ramdisk.raw';hashfile=a.output/'cache.sha256';hashfile.write_bytes(digests)
operations=[]
for source,dest in [(a.plan,'/usr/share/inferno-cache.patch'),(hashfile,'/usr/share/inferno-cache.sha256')]:
 for args in [('add',str(source),dest),('chmod','644',dest),('extract',dest,str(a.output/('readback-'+source.name)))]:
  r=subprocess.run([str(a.hfsplus),str(raw),*args],capture_output=True,text=True,check=True)
  operations.append({'args':args,'stdout':r.stdout,'stderr':r.stderr})
 if sha(a.output/('readback-'+source.name))!=sha(source):raise RuntimeError('ramdisk readback mismatch')
profile=json.loads((a.output/'profile.json').read_text());profile['ramdisk']['sha256']=sha(raw);profile['ramdisk']['size']=raw.stat().st_size
profile['provenance']['cache_patch']={'plan_sha256':a.plan_sha256,'original_sha256':a.original_sha256,'patched_sha256':a.patched_sha256,'records':count,'file_bytes':size,'fixed_path':'/System/Library/Caches/com.apple.dyld/dyld_shared_cache_arm64e'}
(a.output/'profile.json').write_text(json.dumps(profile,indent=2)+'\n')
(a.output/'cache-preparation.json').write_text(json.dumps({'base_preparer_sha256':sha(a.base_preparer),'helper_sha256':sha(a.helper),'plan_sha256':a.plan_sha256,'operations':operations,'profile':profile},indent=2)+'\n')
print(a.output/'profile.json')
