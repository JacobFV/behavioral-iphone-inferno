#!/usr/bin/env python3
"""Offline original-cache attribution for one preserved spindump text.
Output is a fresh directory. Original Apple binaries remain external inputs.
"""
import argparse, pathlib, re, subprocess, json, struct, uuid, mmap, hashlib

def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def imageuuid(buf,off):
    assert struct.unpack_from('<I',buf,off)[0]==0xfeedfacf
    n=struct.unpack_from('<I',buf,off+16)[0];p=off+32
    for _ in range(n):
        cmd,size=struct.unpack_from('<II',buf,p);assert size>=8
        if cmd==0x1b:return str(uuid.UUID(bytes=buf[p+8:p+24])).upper()
        p+=size
    raise ValueError('missing LC_UUID')

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    for key in ('sample','cache','patch-plan','symbolizer','standalone','output'):ap.add_argument('--'+key,type=pathlib.Path,required=True)
    a=ap.parse_args();assert not a.output.exists(),'output must be new'
    text=a.sample.read_text();fh=a.cache.open('rb');d=mmap.mmap(fh.fileno(),0,access=mmap.ACCESS_READ)
    cacheuuid=str(uuid.UUID(bytes=d[88:104])).upper();mo,mc=struct.unpack_from('<II',d,16);maps=[struct.unpack_from('<QQQ',d,mo+i*32)for i in range(mc)]
    def fileoff(vm):
        for base,n,o in maps:
            if base<=vm<base+n:return o+vm-base
        raise ValueError(hex(vm))
    def z(o):return d[o:d.find(b'\0',o)].decode()
    io,ic=struct.unpack_from('<II',d,24);images={z(struct.unpack_from('<I',d,io+i*32+24)[0]):struct.unpack_from('<Q',d,io+i*32)[0]for i in range(ic)}
    header=re.findall(r'Shared Cache:\s+(\S+) slid base address (0x[0-9a-f]+), slide (0x[0-9a-f]+)',text);assert len(header)==1
    actualuuid,slidbase,slide=header[0];slide=int(slide,16);assert actualuuid==cacheuuid;assert int(slidbase,16)-slide==min(x[0] for x in maps)
    target=sorted(set(re.findall(r'^Path:\s+(.+)$',text,re.M)));assert len(target)==1
    checks=[];intervals=[];unvalidated=[]
    for l in text.splitlines():
        m=re.match(r'\s+(0x[0-9a-f]+) -\s+(0x[0-9a-f]+|\?\?\?).*?<([A-F0-9-]+)>\s+(/.*)$',l)
        if not m:continue
        runtime,end,uid,path=m.groups();base=int(runtime,16)
        if path in images:
            vm=images[path];found=imageuuid(d,fileoff(vm));assert found==uid;assert base-slide==vm;assert end!='???'
            finish=int(end,16)+1;assert finish>base
            checks.append({'path':path,'uuid':found,'preferred_base':hex(vm),'runtime_base':runtime,'runtime_end_exclusive':hex(finish)})
            intervals.append((base,finish,path))
        elif path==target[0]:
            found=imageuuid(a.standalone.read_bytes(),0);assert found==uid
            checks.append({'path':path,'uuid':found,'runtime_base':runtime,'scope':'standalone LC_UUID checked; frames retained as original image+offset, not symbolized'})
        else:unvalidated.append({'path':path,'uuid':uid,'runtime_base':runtime,'reason':'not in supplied original cache; left unmapped'})
    assert any(c['path']==target[0] for c in checks),'target executable UUID not validated'
    allpcs=sorted({int(x,16)for x in re.findall(r'\[(0x[0-9a-f]+)\]',text)})
    addresses=[pc for pc in allpcs if any(lo<=pc<hi for lo,hi,_ in intervals)]
    unknown=[hex(pc) for pc in allpcs if pc not in addresses]
    r=subprocess.run([str(a.symbolizer),str(a.cache)],input=''.join(f'{pc-slide:x}\n'for pc in addresses),text=True,capture_output=True,check=True)
    table={int(l.split('\t')[0],16)+slide:l.split('\t',1)[1]for l in r.stdout.splitlines()if '\t'in l};assert set(table)==set(addresses)
    for pc,v in table.items():assert any(lo<=pc<hi and v.split('\t')[0]==path for lo,hi,path in intervals),'nearest image disagrees with validated image interval'
    lines=[]
    for l in text.splitlines():
        m=re.search(r'\[(0x[0-9a-f]+)\]',l)
        if m and int(m[1],16) in table:l+='  => '+table[int(m[1],16)]
        lines.append(l)
    patch=a.patch_plan.read_bytes();count=struct.unpack_from('<I',patch,16)[0];pos=24;ranges=[]
    for _ in range(count):
        off,n,_=struct.unpack_from('<QII',patch,pos);ranges.append((off,off+n));pos+=16+2*n
    overlaps=[]
    for pc in addresses:
        off=fileoff(pc-slide)
        if any(off<end and off+4>start for start,end in ranges):overlaps.append(hex(pc))
    audit={'cache_uuid':cacheuuid,'actual_slide':hex(slide),'mapped_unique_cache_PCs':len(addresses),'image_uuid_and_base_checks':checks,'unvalidated_images':unvalidated,'unmapped_PCs':unknown,'sampled_PC_instruction_patch_overlaps':overlaps,'provenance':{key:{'path':str(getattr(a,key).resolve()),'sha256':sha(getattr(a,key))}for key in ('sample','cache','patch_plan','symbolizer','standalone')},'scope':'Nearest original symbol within UUID/base/range-validated image, not symbol size proof. Unknown/kernel/standalone frames unchanged. Empty4-byte sampled-PC overlap does not exclude patched functions/dependencies elsewhere. No guest execution by this script.'}
    a.output.mkdir();(a.output/'symbolizer-raw.txt').write_text(r.stdout);(a.output/'symbolizer-stderr.txt').write_text(r.stderr);(a.output/'symbolized.txt').write_text('\n'.join(lines)+'\n');(a.output/'symbolication-audit.json').write_text(json.dumps(audit,indent=2)+'\n')
    print(json.dumps({'target':target[0],'slide':hex(slide),'cache_PCs':len(addresses),'image_checks':len(checks),'unknown_PCs':len(unknown),'overlaps':overlaps}))
if __name__=='__main__':main()
