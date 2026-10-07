#!/usr/bin/env python3
"""Read-only fixture input + disposable host-copy checks, no recovery execution."""
import argparse,hashlib,importlib.util,json,pathlib,shutil,struct,subprocess,tempfile
p=argparse.ArgumentParser();p.add_argument('--manifest',type=pathlib.Path,required=True);p.add_argument('--importer',type=pathlib.Path,required=True);p.add_argument('--stage-validator',type=pathlib.Path,required=True);p.add_argument('--output',type=pathlib.Path,required=True);a=p.parse_args()
def module(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
i=module('importer',a.importer);v=module('stage',a.stage_validator);validated=i.validate_import_manifest(a.manifest);pin=validated['tree_sha256'];m,root,records,plan=v.validate(a.manifest,sha(a.manifest),pin)
assert struct.unpack_from('<8sIIQ',plan)==(b'IFAPP001',2,1,75930)
assert len(plan)==408+528*len(records)
for index,r in enumerate(records):
 path,mode,kind,size=struct.unpack_from('<512sIIQ',plan,408+528*index)
 assert path.rstrip(b'\0').decode()==r['path'] and (mode,kind,size)==(r['mode'],r['type'],r['bytes'])
assert struct.unpack_from('<I',v.validate(a.manifest,sha(a.manifest))[3],12)[0]==0
neg=[]
for name in ('bad-manifest-pin','bad-fixture-pin','extra-file','changed-bytes','symlink'):
 with tempfile.TemporaryDirectory(prefix='inferno-stage-check-') as d:
  d=pathlib.Path(d);shutil.copytree(a.manifest.parent/'bundle',d/'bundle');mp=d/'manifest.json';mp.write_bytes(a.manifest.read_bytes());bundle=d/m['bundle']['relative_path']
  if name=='extra-file':(bundle/'unexpected.txt').write_text('owned negative test')
  if name=='changed-bytes':(bundle/'Info.plist').write_bytes(b'owned negative test')
  if name=='symlink':(bundle/'Info.plist').unlink();(bundle/'Info.plist').symlink_to(root/'Info.plist')
  try:v.validate(mp,'0'*64 if name=='bad-manifest-pin' else sha(mp),'0'*64 if name=='bad-fixture-pin' else pin);raise AssertionError('accepted '+name)
  except ValueError as e:neg.append({'case':name,'error':str(e)})
result={'scope':'Host importer+stager validator integration; no guest copy/mount/build/launch claim','input_manifest':str(a.manifest.resolve()),'manifest_sha256':sha(a.manifest),'importer_sha256':sha(a.importer),'stage_validator_sha256':sha(a.stage_validator),'tree_sha256':pin,'plan_sha256':hashlib.sha256(plan).hexdigest(),'plan_bytes':len(plan),'header':{'count':len(records),'allow_identical_fixture':1,'bytes':75930},'files':records,'negative_cases':neg}
with a.output.open('x') as f:json.dump(result,f,indent=2);f.write('\n')
