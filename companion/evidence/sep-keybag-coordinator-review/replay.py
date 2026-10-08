#!/usr/bin/env python3
"""Historical component composition tests parser only, never a new combined execution."""
from pathlib import Path
import hashlib,json,sys
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'companion'))
from sep_keybag import verify_content
key_path=ROOT/'companion/evidence/keybag-initialization-serial.txt'
copy_path=Path('/home/brandonin/Documents/behavioral-iphone-inferno/.local-build/reports/disk-preparation-14/serial.log')
key=key_path.read_bytes();copy=copy_path.read_bytes()
start=copy.index(b'INFERNO_PREP_EXEC /sbin/mount_apfs -o rw /dev/disk0s1s3 /mnt2')
end=copy.index(b'\n',copy.index(b'INFERNO_SEP_COPY_COMPLETE:',start))+1
block=copy[start:end];place=key.index(b'INFERNO_PREP_EXEC /sbin/mount_apfs -o rw /dev/disk0s1s4 /mnt7')
composite=key[:place]+block+key[place:];positive=verify_content(composite)
cases={'historical_keybag_only':key,'missing_shutdown':composite.replace(b'--gigalocker-shutdown',b'--other-shutdown'), 'existing_bag':composite.replace(b'CREATE_RESULT status=0',b'CREATE_RESULT status=-4'), 'already_formatted':composite.replace(b'QUERY status=0 formatted=0',b'QUERY status=0 formatted=1'), 'failed_format':composite.replace(b'EFFACEABLE_FORMAT status=0',b'EFFACEABLE_FORMAT status=-1'), 'wrong_sep_path':composite.replace(b'sep-firmware.img4',b'other-firmware.img4'), 'missing_preboot_unmount':composite.replace(b"unmounting volume 'Preboot'",b"failed volume 'Preboot'"), 'truncated_completion':composite.rstrip(b'\r\n')}
neg={}
for name,raw in cases.items():
 try:verify_content(raw)
 except ValueError as e:neg[name]={'rejected':True,'error':str(e),'sha256':hashlib.sha256(raw).hexdigest()}
 else:raise RuntimeError('Negative unexpectedly accepted:'+name)
out={'scope':'Explicit synthetic composition of TWO distinct historical execution fragments to exercise combined parser. NOT actual combined new execution, keybag initialization or current input validation.', 'historical_components':{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in [key_path,copy_path]},'composite_sha256':hashlib.sha256(composite).hexdigest(),'positive_composite':positive,'negative_cases':neg,'source_sha256':{str(ROOT/'companion'/n):hashlib.sha256((ROOT/'companion'/n).read_bytes()).hexdigest() for n in ['sep_keybag.py','stage-sep-keybag.py']},'vm_started':False}
output=Path(sys.argv[1]);output.write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({'output':str(output),'synthetic_composite_accepted':True,'negatives_rejected':len(neg),'vm_started':False}))
