#!/usr/bin/env python3
"""Read-only historical raw replay and real initial-stage input validation; no VM."""
import argparse, hashlib, importlib.util, json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'companion'))
from data_seed import verify_content
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args()
spec=importlib.util.spec_from_file_location('seed',ROOT/'companion/stage-seed-data.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
raw=(ROOT/'companion/evidence/data-preparation-serial.txt').read_bytes()
positive=verify_content(raw)
mutations={
 'failed_newfs':raw.replace(b'INFERNO_PREP_STATUS raw=0',b'INFERNO_PREP_STATUS raw=256',1),
 'missing_copy_completion':raw.replace(b'INFERNO_DATA_COMPLETE:',b'OTHER_DATA_COMPLETE:',1),
 'missing_normal_unmount':raw.replace(b"unmounting volume 'Hardware'",b"failed-to-unmount 'Hardware'"),
 'wrong_copy_target':raw.replace(b' -> /mnt2/preferences',b' -> /mnt3/preferences'),
 'extra_operation':raw.replace(b'INFERNO_DATA_COMPLETE:',b'INFERNO_KEYBAG_COMPLETE: unexpected\nINFERNO_DATA_COMPLETE:'),
 'zero_remaining_space':raw.replace(b'available_blocks=63633 available_bytes=260640768',b'available_blocks=0 available_bytes=0'),
 'truncated_complete':raw.rstrip(b'\r\n'),
 'verify_instead_of_seed':(ROOT/'companion/evidence/data-guest-verification-serial.txt').read_bytes(),
}
negatives={}
for name,value in mutations.items():
 try:verify_content(value)
 except Exception as e:negatives[name]={'rejected':True,'error':str(e),'sha256':hashlib.sha256(value).hexdigest()}
 else:raise RuntimeError('Unexpected acceptance: '+name)
initial=Path('/home/brandonin/.local/share/inferno/app-import/initial-volumes-stage-2/initial-volumes.json')
launch=json.loads((initial.parent/'launch.json').read_text());pins=launch['input_sha256'];pairs={}
selectors={'profile':'verified-profile/profile.json','raw_recovery_record':'raw-recovery-reproduced-1/extraction.json','helper_build':'reproducible-helper-build-1/build.json','probe':'helper-build-42/inferno-probe','hfsplus':'tools/hfsplus','binary':'build/qemu-system-aarch64','build_manifest':'.local-build/build-manifest.json'}
for k,suffix in selectors.items():
 matches=[(path,sha) for path,sha in pins.items() if path.endswith(suffix)]
 if len(matches)!=1:raise RuntimeError('Ambiguous input '+k)
 pairs[k]=Path(matches[0][0]);pairs[k+'_sha256']=matches[0][1]
pairs['initial_stage']=initial;pairs['initial_stage_sha256']='af68573561e4a123034dca2d29951e38405b6fb3d2e7052966d631c1cc8eff16'
pairs['overlay_tools_root']=Path('/home/brandonin/.local/share/inferno/disk-overlay-tools')
paths,inputs,verified=m.validate_inputs(argparse.Namespace(**pairs));m.check_base_metadata(verified)
result={'scope':'Read-only historical actual seed serial replay and fresh actual initial-stage validation. No seed VM or byte-equality claim.', 'sources':m.sources(),'historical_serial_sha256':hashlib.sha256(raw).hexdigest(),'positive':positive,'negative_cases':negatives,'input_arguments':{k:str(v) for k,v in pairs.items()},'initial_validation':verified,'source_unchanged':None}
m.unchanged(result['sources']);result['source_unchanged']=True
a.output.parent.mkdir(parents=True,exist_ok=True)
with a.output.open('x') as f:json.dump(result,f,indent=2);f.write('\n')
print(json.dumps({'output':str(a.output),'historical_copy_path':'accepted-not-byteverified','negative_rejections':len(negatives),'initial_layers':len(verified['base']['layers']),'vm_started':False}))
