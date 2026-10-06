#!/usr/bin/env python3
"""Hash the separately operator-reviewed images; do not infer timer OCR."""
import argparse,hashlib,json,pathlib
from PIL import Image
p=argparse.ArgumentParser();p.add_argument('repository',type=pathlib.Path);a=p.parse_args();root=a.repository.resolve();src=root/'.local-build/reports/app-boot-53';out=pathlib.Path(__file__).parent;sha=lambda b:hashlib.sha256(b).hexdigest()
conversion=json.loads((src/'stopwatch-qmp-conversion.json').read_bytes());checks=[]
for record,label in zip(conversion,['00:20.63','00:32.80']):
 ppm=root/record['ppm'];png=root/record['png'];assert sha(ppm.read_bytes())==record['ppm_sha256'] and sha(png.read_bytes())==record['png_sha256']
 with Image.open(ppm)as a,Image.open(png)as b:assert a.convert('RGB').tobytes()==b.convert('RGB').tobytes() and a.size==b.size
 checks.append({**record,'rgb_equality_independently_verified':True,'timer_label_reported_by_parent_operator':label})
images=[]
for name,label in [('stopwatch-after-measure/observed-0001.png','02:11.04'),('stopwatch-after-measure/observed-0008.png','02:18.78')]:
 image=src/name;images.append({'path':str(image),'sha256':sha(image.read_bytes()),'timer_label_reported_by_parent_operator':label})
start_raw=(src/'stopwatch-start/submission.json').read_bytes();start=json.loads(start_raw);(out/'start-submission.json').write_bytes(start_raw)
serial=(src/'serial.log').read_bytes();offset=0;clock=[]
for line in serial.split(b'\n'):
 if offset==len(serial):break
 raw=line+(b'\n'if offset+len(line)<len(serial)else b'')
 if b'/Applications/MobileTimer.app/MobileTimer'in line and line.strip().startswith(b'349 '):clock.append({'text':line.rstrip(b'\r').decode(),'byte_start':offset,'byte_end':offset+len(raw),'sha256':sha(raw)})
 offset+=len(raw)
result={'scope':'Separate parent-operator timer readings. This script verifies image identity/lossless conversion, not OCR or visual interpretation.','periodic_qmp_images':checks,'post_active_vnc_images':images,'start_host_submission_time':start['started_time'],'start_request_id':start['request_id'],'serial_clock_identity':{'snapshot_bytes':len(serial),'snapshot_sha256':sha(serial),'records':clock},'limits':['Periodic QMP timer labels advance but lag host time since Start submission. No continuous or real-time rendering claim during the no-observed-VNC interval.','Post-measurement VNC frames advance; connecting/capturing can stimulate display updates and does not establish prior presentation cadence.','Guest timer displays and host submission timestamps are different observables; no clock calibration performed.']}
(out/'visual-context.json').write_text(json.dumps(result,indent=2)+'\n')
