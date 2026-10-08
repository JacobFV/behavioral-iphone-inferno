from pathlib import Path
import json,sys,argparse,importlib.util,hashlib,time
root=Path('/tmp/inferno-sep-keybag');sys.path.insert(0,str(root/'companion'));spec=importlib.util.spec_from_file_location('keybag',root/'companion/stage-sep-keybag.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
prior=json.loads((root/'companion/evidence/data-seed-coordinator-review/replay-result.json').read_text())['input_arguments']
prior.pop('initial_stage');prior.pop('initial_stage_sha256')
for k in list(prior):
 if not k.endswith('_sha256'):prior[k]=Path(prior[k])
prior['grown_stage']=Path('/home/brandonin/.local/share/inferno/app-import/grow-data-stage-1/grown-data.json');prior['grown_stage_sha256']='5825856bf0fdb53542437d578dd09eb466c24edf703f8880d2b6c57c23d9c358'
prior['sep_payload']=Path('/home/brandonin/.local/share/inferno/native-probe/sep-original.im4p');prior['sep_payload_sha256']='76587673e56bbb89e178a015ebbe20fee29f841d07fa6f6cce0e9dad6800dfbe'
prior['sep_record']=Path('/home/brandonin/.local/share/inferno/native-probe/sep-original.json');prior['sep_record_sha256']=m.sha(prior['sep_record'])
r={'scope':'Read-only actual grown-input validation; no VM/ramdisk preparation/newkeybag','started':time.time(),'argv_inputs':{k:str(v) for k,v in prior.items()},'source_sha256':m.sources()}
try:
 paths,pins,verified=m.validate_inputs(argparse.Namespace(**prior));m.check_base_metadata(verified);m.unchanged(r['source_sha256']);r.update(status='passed',input_sha256=pins,verified=verified)
except Exception as e:r.update(status='failed',error=str(e))
r['finished']=time.time();Path('/tmp/sep-keybag-input-preflight-2.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({'status':r['status'],'error':r.get('error'),'output':'/tmp/sep-keybag-input-preflight-2.json'}))
