#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Small explicitly synthetic framing check; not guest execution evidence."""
import hashlib, importlib.util, json, plistlib, sys
from pathlib import Path
source=Path(__file__).resolve().parents[1]/'result.py'
spec=importlib.util.spec_from_file_location('inspector_result',source)
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
owned=plistlib.dumps({'LaunchDaemons':{'org.inferno.synthetic':{'Label':'org.inferno.synthetic','ProgramArguments':['/owned/synthetic']}}},fmt=plistlib.FMT_BINARY)
chunks=[owned[i:i+64] for i in range(0,len(owned),64)]
lines=['INFERNO_INSPECT_BEGIN version=1 fixed_files=2','INFERNO_INSPECT_MOUNT status=0 mode=ro',f'INFERNO_INSPECT_FILE name=launchd bytes={len(owned)} mode=33188 uid=0 gid=0']
offset=0
for chunk in chunks:
    lines.append(f'INFERNO_INSPECT_DATA name=launchd offset={offset} bytes={len(chunk)} hex={chunk.hex()}');offset+=len(chunk)
lines += [f'INFERNO_INSPECT_HASH name=launchd bytes={len(owned)} sha256={hashlib.sha256(owned).hexdigest()}', 'INFERNO_INSPECT_FILE name=dyld bytes=2052489216 mode=33188 uid=0 gid=0','INFERNO_INSPECT_HASH name=dyld bytes=2052489216 sha256='+'0'*64,"unmounting volume 'AzulSeed18A5351d.N104N841DeveloperOS' (numMountedAPFSVolumes 0)",'INFERNO_INSPECT_UNMOUNT status=0 errno=0','INFERNO_INSPECT_RESULT status=0']
raw=('\r\r\n'.join(lines)+'\r\r\n').encode()
result,decoded=module.verify_content(raw)
assert decoded==owned
cases={'missing_result':raw[:raw.rfind(b'INFERNO_INSPECT_RESULT')], 'offset_gap':raw.replace(b'offset=0 ',b'offset=1 ',1),'wrong_hash':raw.replace(hashlib.sha256(owned).hexdigest().encode(),b'1'*64),'duplicate_begin':raw+lines[0].encode()+b'\n','failed_unmount':raw.replace(b'UNMOUNT status=0',b'UNMOUNT status=-1')}
rejected={}
for name,case in cases.items():
    try:module.verify_content(case)
    except (ValueError,IndexError) as error:rejected[name]=str(error)
    else:raise AssertionError('Accepted '+name)
print(json.dumps({'scope':'Explicitly synthetic host parser fixture; no guest or actual dyld hash claim','source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'serial_sha256':hashlib.sha256(raw).hexdigest(),'physical_line_ending':'CRCRLF','positive_decoded_sha256':hashlib.sha256(decoded).hexdigest(),'negative_rejections':rejected},indent=2))
