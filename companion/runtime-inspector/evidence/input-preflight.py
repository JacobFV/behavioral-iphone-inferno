import argparse,hashlib,importlib.util,json,sys,time
from pathlib import Path
root=Path('/tmp/inferno-runtime-inspector');sys.path.insert(0,str(root/'companion/runtime-inspector'));sys.path.insert(0,str(root/'companion'))
spec=importlib.util.spec_from_file_location('inspector_stage',root/'companion/runtime-inspector/stage.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
base=Path('/home/brandonin/.local/share/inferno')
args=argparse.Namespace(profile=base/'images/ios14b5/verified-profile/profile.json',profile_sha256='7939d609b99b8223863dba0b0af9d181526b420c0023cc9520563fd7e0979ed8',raw_recovery_record=base/'images/ios14b5/raw-recovery-reproduced-1/extraction.json',raw_recovery_record_sha256='500127c92ff6d3692513ae50ea1d7592fe3f4f4005d059b27fb23b0782372f9f',keybag_stage=base/'app-import/sep-keybag-stage-1/sep-keybag.json',keybag_stage_sha256='04547b9971e6d8fa01b674e26fd7e0b05cd28dc7bb2524145e456590ed00ab09',helper_build=base/'native-probe/runtime-inspector-build-1/build.json',helper_build_sha256='38c3445b602f761da5c772fe18e51e47fab1cf2a3694a84db2c634c3edeeb99a',probe=base/'native-probe/helper-build-42/inferno-probe',probe_sha256='7def2d54fb9a0737666cbe175b38ad442eea5340a07fac202ffd1fda2df849c9',hfsplus=base/'native-probe/tools/hfsplus',hfsplus_sha256='2b38fd84323addc7487587738d4c4dd5b0d012d7e895e77e9e8ef1840fac7454',binary=Path('/home/brandonin/Documents/behavioral-iphone-inferno/.local-build/build/qemu-system-aarch64'),binary_sha256='0889bfe40c6bbb3e6eb9d493ada2bb86637e1d7acb61e36699e16da2568563f2',build_manifest=Path('/home/brandonin/Documents/behavioral-iphone-inferno/.local-build/build-manifest.json'),build_manifest_sha256='1c0ca353df0b88956f071503654a9a0a3f1e22346270e89accdfaa911391f096',overlay_tools_root=base/'disk-overlay-tools',output=base/'app-import/runtime-inspection-stage-1')
record={'scope':'Actual read-only inspector input validation; no preparation, VM or new disk','started':time.time(),'source_sha256':m.sources(),'arguments':{k:str(v) for k,v in vars(args).items()}}
argv=[sys.executable,str(root/'companion/runtime-inspector/stage.py')]
for k,v in vars(args).items():argv.extend(['--'+k.replace('_','-'),str(v)])
record['planned_argv']=argv
try:
    destination=m.CO.IMPORTER.external_output(args.output);record['proc_preflight']=m.CO.no_running_emulator();record['free_bytes']=m.shutil.disk_usage(destination.parent).free
    if record['free_bytes']<2<<30:raise ValueError('Insufficient reserve')
    paths,pins,verified=m.validate_inputs(args);m.unchanged(record['source_sha256']);m.check_base_metadata(verified)
    record.update(status='PASS-read-only-inputs',input_sha256=pins,verified_inputs=verified,paths={k:str(v) for k,v in paths.items()})
except BaseException as exc:
    record.update(status='FAIL',error=str(exc),error_type=type(exc).__name__)
finally:
    record['finished']=time.time();out=base/'app-import/runtime-inspection-stage-1-preflight.json'
    with out.open('x') as f:json.dump(record,f,indent=2);f.write('\n')
    print(json.dumps({'status':record['status'],'output':str(out),'sha256':hashlib.sha256(out.read_bytes()).hexdigest(),'error':record.get('error')}),flush=True)
if record['status']!='PASS-read-only-inputs':raise SystemExit(1)
