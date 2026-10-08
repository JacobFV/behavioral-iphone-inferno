# SPDX-License-Identifier: AGPL-3.0-or-later
"""Independent small-file host artifact audit; no disk hashing, VM or Apple exports."""
import copy,hashlib,importlib.util,json,plistlib,sys
from pathlib import Path
sys.dont_write_bytecode=True
base=Path('/home/brandonin/.local/share/inferno/app-import/fresh-runtime-artifacts-2')
main=Path('/home/brandonin/Documents/behavioral-iphone-inferno')
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
record_path=base/'fresh-runtime-artifacts.json';assert sha(record_path)=='95f72bc41d35e0b6d4131dba714dc17ba2ad4d3df9f3cb637e62b79e20155274'
v=json.loads(record_path.read_bytes());assert v['status']=='host-prepared-not-staged' and v['ipa_runtime_ready'] is False
assert not any((base/n).exists() for n in ('INCOMPLETE.json','failure.json'))
pins={str(record_path):sha(record_path)}
for p,h in v['input_source_sha256'].items():
 assert Path(p).stat().st_size<=64<<20 and sha(p)==h,p
 pins[p]=h
for row in v['outputs'].values():assert sha(row['path'])==row['sha256'];pins[row['path']]=row['sha256']
inputs={name:json.loads(Path(row['path']).read_bytes()) for name,row in v['inputs'].items()}
for row in v['inputs'].values():assert sha(row['path'])==row['sha256']
inspection=inputs['inspection'];assert inspection['predecessor']==v['inputs']['keybag_stage']
assert inspection['runtime_base_eligible'] is False and inputs['keybag_stage']['backing_depth']==3
source=Path('/tmp/inferno-runtime-inspector-framing/companion/runtime-inspector/result.py')
spec=importlib.util.spec_from_file_location('artifact_audit_inspector',source);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
content,export=m.verify_content(Path(inspection['report']).with_name('serial.log').read_bytes());assert content==inspection['content'] and export==Path(inspection['launchd_export']['path']).read_bytes()
original=plistlib.loads(export);actual_bytes=(base/'launchd.plist').read_bytes();actual=plistlib.loads(actual_bytes)
policy={'com.apple.voicemail.vmd','com.apple.CommCenter','com.apple.CommCenterMobileHelper','com.apple.CommCenterRootHelper','com.apple.locationd'}
assert set(v['policy']['disabled_original_labels'])==policy and len(v['policy']['disabled_original_labels'])==5
jobs={name:plistlib.loads((base/name).read_bytes()) for name in v['jobs']}
assert set(jobs)=={'org.inferno.app-probe.plist','org.inferno.readiness.plist','org.inferno.unlock-empty.plist'}
assert jobs['org.inferno.app-probe.plist']==plistlib.loads((main/'companion/app-probe/org.inferno.app-probe-system-app.plist').read_bytes())
for label,program in [('readiness','inferno-readiness'),('unlock-empty','inferno-unlock-empty')]:
 expected={'Label':'org.inferno.'+label,'ProgramArguments':['/usr/bin/'+program],'RunAtLoad':True,'UserName':'root','StandardOutPath':'/dev/console','StandardErrorPath':'/dev/console'}
 if label=='unlock-empty':expected['KeepAlive']=False
 assert jobs['org.inferno.'+label+'.plist']==expected
expected=copy.deepcopy(original);disabled=[]
for key,job in expected['LaunchDaemons'].items():
 if job.get('Label') in policy:disabled.append(job['Label']);job['Disabled']=True
assert len(disabled)==5 and set(disabled)==policy
for name,job in jobs.items():
 key='/System/Library/LaunchDaemons/'+name;assert key not in expected['LaunchDaemons'];expected['LaunchDaemons'][key]=job
# Type-sensitive equality avoids treating bool/int substitutions as preservation.
def equal(a,b):
 if type(a) is not type(b):return False
 if isinstance(a,dict):return a.keys()==b.keys() and all(equal(a[k],b[k]) for k in a)
 if isinstance(a,list):return len(a)==len(b) and all(equal(x,y) for x,y in zip(a,b))
 return a==b
assert equal(actual,expected)
changed=[]
for key,old in original['LaunchDaemons'].items():
 new=actual['LaunchDaemons'][key]
 if not equal(old,new):
  assert old.get('Label') in policy and equal({**old,'Disabled':True},new);changed.append(old['Label'])
assert len(original['LaunchDaemons'])==432 and len(actual['LaunchDaemons'])==435 and set(changed)==policy
assert len(actual_bytes)==596664 and sha(base/'launchd.plist')=='06291b66b9ed5e7886a2893f5c6094c0ae7e3de2fe7ddeef951e67c278e1b843'
launcher=inputs['launcher_build'];app=inputs['app_manifest'];assert launcher['manifest_path']==v['inputs']['app_manifest']['path'] and launcher['manifest_sha256']==v['inputs']['app_manifest']['sha256'] and launcher['target']==app['bundle']
assert app['bundle']['identifier']=='org.inferno.companion.ipademo' and app['bundle']['guest_path']=='/Applications/ImportedDemo.app'
for f in app['files']:
 p=Path(v['inputs']['app_manifest']['path']).parent/app['bundle']['relative_path']/f['path'];assert p.stat().st_size==f['bytes'] and sha(p)==f['sha256']
fragment=v['prepare_arguments_fragment'];assert fragment[0]=='--disk-helper-existing' and len(fragment[1:])%2==0
args=dict(zip(fragment[1::2],fragment[2::2]));assert len(args)==len(fragment[1:])//2
assert set(args)=={'--readiness-probe','--hid-input-helper','--unlock-helper','--disk-helper','--system-launcher','--exec-wrapper','--imported-app-manifest','--imported-app-manifest-sha256','--launchd-cache','--launchd-cache-sha256'}
for name in ('runtime_build','prepare_build'):
 assert inputs[name]['command_records'] and all(r['exit_code']==0 for r in inputs[name]['command_records'])
 folder=Path(v['inputs'][name]['path']).parent;assert not any((folder/n).exists() for n in ['INCOMPLETE.json','failure.json'])
assert args['--launchd-cache']==str(base/'launchd.plist') and args['--launchd-cache-sha256']==sha(base/'launchd.plist')
for flag,name in [('--readiness-probe','inferno-readiness'),('--hid-input-helper','inferno-hid-input'),('--unlock-helper','inferno-unlock-empty')]:
 p=Path(v['inputs']['runtime_build']['path']).parent/name;assert args[flag]==str(p) and sha(p)==inputs['runtime_build']['outputs'][name]['sha256']
assert sha(args['--disk-helper'])==inputs['prepare_build']['outputs']['inferno-prepare-root']['sha256']
for flag,name in [('--system-launcher','inferno-launcher'),('--exec-wrapper','inferno-exec-launcher')]:assert sha(args[flag])==launcher['outputs'][name]
assert args['--imported-app-manifest']==v['inputs']['app_manifest']['path'] and args['--imported-app-manifest-sha256']==v['inputs']['app_manifest']['sha256']
command_path=base.parent/'fresh-runtime-artifact-input-1/production-2-command.json';command=json.loads(command_path.read_bytes());assert command['exit_code']==0
assert command['argv']==['python3',str(main/'companion/prepare-fresh-runtime.py'),'--input',command['input']['path'],'--input-sha256',command['input']['sha256'],'--output',str(base)]
for p,h in command['logs'].items():assert sha(p)==h;pins[p]=h
assert json.loads((command_path.parent/'production-2.stdout').read_bytes())=={'status':'host-prepared-not-staged','ipa_runtime_ready':False}
assert (base/'merge.stdout').read_bytes()==(base/'launchd.plist.json').read_bytes() and not (base/'merge.stderr').read_bytes()
merge=json.loads((base/'merge.stdout').read_bytes());assert merge['source_sha256']==inspection['launchd_export']['sha256'] and merge['output_sha256']==sha(base/'launchd.plist')
assert merge['original_jobs']==432 and merge['merged_jobs']==435
failed=base.with_name('fresh-runtime-artifacts-1');assert (failed/'INCOMPLETE.json').exists() and (failed/'failure.json').exists() and not (failed/'fresh-runtime-artifacts.json').exists()
pins[str(command_path)]=sha(command_path)
for p,h in pins.items():assert sha(p)==h,p
summary={'status':'PASS-independent-host-artifact-audit','scope':'Actual host production only; no disk eligibility, renderer, staging, readiness or app execution claim. Full decoded Apple configuration and serial remain external.',
 'result':{'path':str(record_path),'sha256':sha(record_path)},'original_launchd':inspection['launchd_export'],'original_jobs':432,'merged_jobs':435,'exact_disabled_labels':sorted(changed),'exact_owned_additions':sorted(jobs),'whole_decoded_tree_type_sensitive_equality':True,
 'actual_cache':{'path':str(base/'launchd.plist'),'bytes':len(actual_bytes),'sha256':sha(base/'launchd.plist')},'input_pins':v['inputs'],'verified_source_input_output_pin_count':len(pins),'raw_production_command':{'path':str(command_path),'sha256':sha(command_path),'exit_code':command['exit_code'],'started':command['started'],'finished':command['finished'],'logs':command['logs']},'prepare_arguments_fragment':fragment,'merge_command':v['merge_command'],'prior_failure_preserved':{'failure_path':str(failed/'failure.json'),'failure_sha256':sha(failed/'failure.json'),'incomplete_sha256':sha(failed/'INCOMPLETE.json')},'ipa_runtime_ready':False}
print(json.dumps(summary,indent=2))
