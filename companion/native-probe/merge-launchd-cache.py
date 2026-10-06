#!/usr/bin/env python3
"""Merge explicit owned jobs into a cloned launchd configuration; never sign it."""
import argparse, hashlib, json, plistlib
from pathlib import Path
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--cache',type=Path,required=True)
p.add_argument('--job',type=Path,action='append',required=True)
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
assert all(result['LaunchDaemons'][k]==v for k,v in original['LaunchDaemons'].items())
a.output.parent.mkdir(parents=True,exist_ok=True)
with a.output.open('xb') as f:f.write(plistlib.dumps(result,fmt=plistlib.FMT_BINARY,sort_keys=False))
record={'source':str(a.cache.resolve()),'source_sha256':sha(a.cache),'original_jobs':len(original['LaunchDaemons']),'merged_jobs':len(result['LaunchDaemons']),'added':jobs,'output_sha256':sha(a.output),'note':'Configuration merge only; original entries preserved; no signature generated or modified.'}
a.output.with_suffix(a.output.suffix+'.json').write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps(record,indent=2))
