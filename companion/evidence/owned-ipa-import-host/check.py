#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Host-only owned fixture archive checks; all binary products stay external."""
import argparse, hashlib, importlib.util, json, pathlib, stat, struct, zipfile
p=argparse.ArgumentParser();p.add_argument('--importer',type=pathlib.Path,required=True);p.add_argument('--fixture',type=pathlib.Path,required=True);p.add_argument('--output',type=pathlib.Path,required=True);a=p.parse_args()
a.output.mkdir(parents=True,exist_ok=False)
s=importlib.util.spec_from_file_location('app_import',a.importer);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
files={x.name:x.read_bytes() for x in sorted(a.fixture.iterdir()) if x.is_file()}
def archive(name, changes=None, extra=None):
    path=a.output/(name+'.ipa')
    with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED) as z:
        for key,data in files.items():
            item=zipfile.ZipInfo('Payload/InfernoProbe.app/'+key);item.external_attr=(stat.S_IFREG|(0o755 if key=='InfernoProbe' else 0o644))<<16
            z.writestr(item,(changes or {}).get(key,data))
        if extra:
            z.writestr(*extra)
    return path
source=archive('owned-original');manifest=m.import_ipa(source,a.output/'imported');valid=m.validate_manifest(a.output/'imported/manifest.json')
checks=[]
def rejected(name,source):
    try:m.import_ipa(source)
    except (ValueError,zipfile.BadZipFile) as e:checks.append({'case':name,'rejected':True,'reason':str(e),'sha256':m.digest(source.read_bytes())})
    else:raise RuntimeError('Accepted negative '+name)
rejected('traversal',archive('traversal',extra=('../escape',b'x')))
rejected('case-collision',archive('case-collision',extra=('Payload/InfernoProbe.app/info.plist',b'x')))
item=zipfile.ZipInfo('Payload/InfernoProbe.app/link');item.external_attr=(stat.S_IFLNK|0o777)<<16
rejected('symlink',archive('symlink',extra=(item,b'/tmp/target')))
rejected('nested-code',archive('nested-code',extra=('Payload/InfernoProbe.app/extra',files['InfernoProbe'])))
original=files['InfernoProbe'];positions=[];pos=32
for _ in range(struct.unpack_from('<I',original,16)[0]):
    cmd,size=struct.unpack_from('<II',original,pos);positions.append((cmd,pos,size));pos+=size
platform=bytearray(original);cmd,pos,size=next(x for x in positions if x[0]==0x32);struct.pack_into('<I',platform,pos+8,7)
rejected('simulator-platform',archive('simulator-platform',{'InfernoProbe':platform}))
# Replace a >=24-byte command with an encryption command in a synthetic malformed input.
encrypted=bytearray(original);cmd,pos,size=next(x for x in positions if x[2]>=24 and x[0]!=0x32);struct.pack_into('<IIIIII',encrypted,pos,0x2c,size,0,0,1,0)
rejected('encrypted-mach-o',archive('encrypted-mach-o',{'InfernoProbe':encrypted}))
minos=bytearray(original);cmd,pos,size=next(x for x in positions if x[0]==0x32);struct.pack_into('<I',minos,pos+12,15<<16)
rejected('minimum-ios15',archive('minimum-ios15',{'InfernoProbe':minos}))
# Revalidate the successful tree after corrupting a copy, not the retained positive.
corrupt=a.output/'corrupt';m.import_ipa(source,corrupt);exe=corrupt/'bundle/InfernoProbe.app/InfernoProbe';data=bytearray(exe.read_bytes());data[-1]^=1;exe.write_bytes(data)
try:m.validate_manifest(corrupt/'manifest.json')
except ValueError as e:checks.append({'case':'modified-extracted-file','rejected':True,'reason':str(e)})
else:raise RuntimeError('Accepted modified tree')
result={'scope':'Host-only import and synthetic malformed-input checks; no guest execution/signature trust claim','importer':{'path':str(a.importer.resolve()),'sha256':m.digest(a.importer.read_bytes())},'fixture':{'path':str(a.fixture),'files':[{ 'path':k,'bytes':len(v),'sha256':m.digest(v)} for k,v in files.items()]},'manifest_path':str(a.output/'imported/manifest.json'),'manifest_sha256':m.digest((a.output/'imported/manifest.json').read_bytes()),'input':manifest['input'],'tree_sha256':manifest['tree_sha256'],'preserved_original_bytes':all((a.output/'imported/bundle/InfernoProbe.app'/k).read_bytes()==v for k,v in files.items()),'validator_resolved_bundle_path':valid['resolved_bundle_path'],'negative_checks':checks}
(a.output/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
