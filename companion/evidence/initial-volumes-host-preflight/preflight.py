import importlib.util,sys,pathlib,json,hashlib,types,subprocess,os
root=pathlib.Path('/tmp/inferno-initial-volumes/companion');sys.path.insert(0,str(root));spec=importlib.util.spec_from_file_location('initial_coordinator',root/'stage-initial-volumes.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
def sha(p):
 with pathlib.Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
b=pathlib.Path('/home/brandonin/.local/share/inferno');runtime=json.loads((b/'app-import/prepare-session-demo-1-inputs/runtime.json').read_text());a={}
for name,key in [('profile','profile'),('probe','probe'),('hfsplus','hfsplus'),('binary','emulator'),('build_manifest','emulator_build')]:a[name]=pathlib.Path(runtime['inputs'][key]['path']);a[name+'_sha256']=runtime['inputs'][key]['sha256']
for name,path in [('raw_recovery_record',b/'images/ios14b5/raw-recovery-reproduced-1/extraction.json'),('root_copy_record',b/'images/ios14b5/initial-volumes-source-1/copy.json'),('helper_build',b/'native-probe/reproducible-helper-build-1/build.json')]:a[name]=path;a[name+'_sha256']=sha(path)
a['overlay_tools_root']=pathlib.Path(runtime['overlay_tools_root']);paths,pins,verified=m.validate_inputs(types.SimpleNamespace(**a));assert verified['base']['layers'][0]['sha256']==m.ORIGINAL_ROOT_SHA
old=pathlib.Path('/home/brandonin/Documents/behavioral-iphone-inferno/.local-build/reports/disk-preparation-8/serial.log');raw=old.read_bytes()
try:m.verify_content(raw)
except ValueError as e:rejection=str(e)
else:raise AssertionError('Historical older-ABI run unexpectedly accepted')
result={'scope':'Actual read-only input preflight only; no coordinator main/VM','arguments':{k:str(v) for k,v in a.items()},'input_pins':pins,'verified_inputs':verified,'historical_serial':{'path':str(old),'sha256':sha(old),'expected_rejection':rejection},'source_hashes':m.sources()}
output=b/'images/ios14b5/initial-volumes-source-1/host-preflight.json';output.write_text(json.dumps(result,indent=2)+'\n');print(output)
