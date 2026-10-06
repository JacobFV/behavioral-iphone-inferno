#!/usr/bin/env python3
"""Merge explicit owned jobs into a cloned launchd configuration; never sign it."""
import argparse, hashlib, json, plistlib
from pathlib import Path
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--cache',type=Path,required=True)
p.add_argument('--job',type=Path,action='append',default=[])
p.add_argument('--replace-owned-job',type=Path,action='append',default=[])
p.add_argument('--disable-unsupported-services',action='store_true',help='set Disabled=true only for the five services documented by upstream')
p.add_argument('--output',type=Path,required=True)
a=p.parse_args()
original=plistlib.loads(a.cache.read_bytes())
if not isinstance(original.get('LaunchDaemons'),dict):p.error('expected LaunchDaemons mapping')
result=dict(original);result['LaunchDaemons']=dict(original['LaunchDaemons'])
sha=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
jobs={}
for path in a.job:
 job=plistlib.loads(path.read_bytes())
 if not str(job.get('Label','')).startswith('org.inferno.'):p.error('only explicitly owned org.inferno jobs permitted')
 key='/System/Library/LaunchDaemons/'+path.name
 if key in result['LaunchDaemons']:p.error('refusing to replace existing cache entry: '+key)
 result['LaunchDaemons'][key]=job;jobs[key]={'label':job['Label'],'sha256':sha(path)}
replaced=set()
for path in a.replace_owned_job:
 job=plistlib.loads(path.read_bytes());label=str(job.get('Label',''))
 if not label.startswith('org.inferno.'):p.error('replacement must be explicitly owned org.inferno job')
 keys=[k for k,v in original['LaunchDaemons'].items() if v.get('Label')==label]
 if len(keys)!=1:p.error('replacement requires exactly one existing owned label')
 key=keys[0];result['LaunchDaemons'][key]=job;replaced.add(key)
 jobs[key]={'label':label,'sha256':sha(path),'operation':'replace-owned-job'}
disabled=[]
if a.disable_unsupported_services:
 labels=('com.apple.voicemail.vmd','com.apple.CommCenter','com.apple.CommCenterMobileHelper','com.apple.CommCenterRootHelper','com.apple.locationd')
 for label in labels:
  keys=[k for k,v in original['LaunchDaemons'].items() if v.get('Label')==label]
  if len(keys)!=1:p.error('expected exactly one documented service: '+label)
  key=keys[0];result['LaunchDaemons'][key]=dict(result['LaunchDaemons'][key]);result['LaunchDaemons'][key]['Disabled']=True
  disabled.append(key)
assert all(result['LaunchDaemons'][k]==v for k,v in original['LaunchDaemons'].items() if k not in replaced and k not in disabled)
assert all({k:v for k,v in result['LaunchDaemons'][key].items() if k!='Disabled'}=={k:v for k,v in original['LaunchDaemons'][key].items() if k!='Disabled'} for key in disabled)
a.output.parent.mkdir(parents=True,exist_ok=True)
with a.output.open('xb') as f:f.write(plistlib.dumps(result,fmt=plistlib.FMT_BINARY,sort_keys=False))
record={'source':str(a.cache.resolve()),'source_sha256':sha(a.cache),'original_jobs':len(original['LaunchDaemons']),'merged_jobs':len(result['LaunchDaemons']),'explicit_jobs':jobs,'disabled_documented_services':disabled,'output_sha256':sha(a.output),'note':'Configuration merge only; original entries preserved except explicit owned-job replacements and requested five documented Disabled flags; no signature generated or modified.'}
a.output.with_suffix(a.output.suffix+'.json').write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps(record,indent=2))
