#!/usr/bin/env python3
"""Synthetic parser framing only; never an actual guest preparation claim."""
import hashlib,json,sys,subprocess
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
import fresh_runtime_stage as F
m={'bundle':{'directory_name':'OwnedDemo.app','identifier':'org.inferno.synthetic.demo','guest_path':'/Applications/OwnedDemo.app'},'files':[{'path':'OwnedDemo','bytes':123},{'path':'Info.plist','bytes':456},{'path':'resource.txt','bytes':7}],'directories':[]}
s={'hid_input':101,'readiness':202,'unlock_helper':303,'exec_wrapper':404,'system_launcher':505,'launchd_cache':606}
u="unmounting volume 'AzulSeed18A5351d.N104N841DeveloperOS' (numMountedAPFSVolumes 0)"
lines=['INFERNO_PREP_BEGIN: disposable /dev/disk0s1 existing=1 roles=0 gigalocker=0','INFERNO_HID_INPUT_READBACK bytes=101 mismatches=0',u,'INFERNO_HID_INPUT_INSTALLED: operator-only virtual device; no automatic gestures','INFERNO_READINESS_READBACK bytes=202 mismatches=0',u,'INFERNO_READINESS_INSTALLED','INFERNO_EXEC_WRAPPER_READBACK bytes=404 mismatches=0',u,'INFERNO_SYSTEM_LAUNCHER_READBACK bytes=505 mismatches=0',u,'INFERNO_UNLOCK_HELPER_READBACK bytes=303 mismatches=0',u,'INFERNO_IMPORTED_APP_PLAN bundle=OwnedDemo.app identifier=org.inferno.synthetic.demo entries=3 bytes=586 identical_fixture=0','INFERNO_IMPORTED_APP_PARENT stat=0 errno=0 mode=40775 uid=0 gid=80 nlink=105 path_result=0','INFERNO_IMPORTED_APP_DIR_METADATA_BEFORE target=/mnt1/Applications/OwnedDemo.app source_stat=0 source_mode=40755 source_uid=0 source_gid=0 target_stat=0 target_mode=40755 target_uid=0 target_gid=80','INFERNO_IMPORTED_APP_DIR_METADATA_AFTER target=/mnt1/Applications/OwnedDemo.app copy=0 copy_errno=0 stat=0 mode=40755 uid=0 gid=0','INFERNO_IMPORTED_APP_READBACK bundle=OwnedDemo.app bytes=586 entries=3 mismatches=0',u,'INFERNO_IMPORTED_APP_FINISH result=0 unmount=0 errno=0','INFERNO_CACHE_READBACK bytes=606 mismatches=0',u,'INFERNO_LAUNCHD_CACHE_INSTALLED: explicit configuration only; signature unchanged','INFERNO_PREP_COMPLETE: requested preparation operations succeeded']
raw=('\n'.join(lines)+'\n').encode();result=F.verify_content(raw,m,s)
cases={'wrong-helper-size':raw.replace(b'bytes=101 ',b'bytes=102 '),'missing-unmount':raw.replace(u.encode(),b'no unmount',1),'extra-sep':raw+b'INFERNO_SEP_COPY_COMPLETE: extra\n','duplicate-complete':raw+lines[-1].encode()+b'\n','missing-complete':raw[:raw.rindex(lines[-1].encode())],'app-mismatch':raw.replace(b'entries=3 mismatches=0',b'entries=3 mismatches=1'),'helper-reordered':raw.replace(b'INFERNO_HID_INPUT_READBACK',b'INFERNO_UNLOCK_HELPER_READBACK',1),'panic':raw+b'panic(cpu 0)\n'}
rejected=[]
for name,data in cases.items():
 try:F.verify_content(data,m,s)
 except ValueError as exc:rejected.append({'case':name,'error':str(exc)});continue
 raise RuntimeError('Accepted malformed case '+name)
print(json.dumps({'scope':'Synthetic framing and manifest-size parser check only; no guest, HFS preparation or predecessor validation executed.','source_sha256':F.sources(),'fixture_sha256':hashlib.sha256(raw).hexdigest(),'positive':result,'rejected':rejected},indent=2))
