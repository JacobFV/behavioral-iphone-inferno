# SPDX-License-Identifier: AGPL-3.0-or-later
"""Fresh original SEP/keybag raw path gates; not destination-byte or runtime proof."""
import hashlib
import re
from initial_volumes import SYSTEM_NAME, COMPLETE

SEP_SHA256 = '76587673e56bbb89e178a015ebbe20fee29f841d07fa6f6cce0e9dad6800dfbe'
SEP_SHA384 = 'd3ac9fc14a4405ced2d52ddc06433a1b7612ac8be1d15379e7d3be41b5d8adff42578aa993c7c08669f1d69a1ef1cb87'
SEP_BYTES = 7783790
SEP_MEMBER = 'Firmware/all_flash/sep-firmware.n104.RELEASE.im4p'
SEP_DESTINATION = '/' + '0' * 96 + '/usr/standalone/firmware/sep-firmware.img4'
BEGIN = 'INFERNO_PREP_BEGIN: disposable /dev/disk0s1 existing=1 roles=0 gigalocker=0'
COPY_COMPLETE = 'INFERNO_SEP_COPY_COMPLETE: supplied bytes copied to loader path'
KEYBAG_COMPLETE = 'INFERNO_KEYBAG_COMPLETE: original framework created or found system keybag'


def verify_content(raw):
    if not isinstance(raw, bytes) or len(raw) > 64 << 20: raise ValueError('Expected serial bytes bounded64MiB')
    rows=[];offset=0
    for line in raw.split(b'\n'):
        value=line.rstrip(b'\r')
        if b'panic(cpu' in value: raise ValueError('Guest panic')
        if b'INFERNO_' in value:
            if offset+len(line)>=len(raw) or value.count(b'INFERNO_')!=1: raise ValueError('Ambiguous/truncated owned record')
            at=value.index(b'INFERNO_');text=value[at:].decode('ascii')
            if text!='INFERNO_OWNED_NATIVE_PROBE_V1: executed arm64 Darwin syscalls':
                rows.append({'text':text,'byte_start':offset+at,'byte_end':offset+len(value),'sha256':hashlib.sha256(value[at:]).hexdigest()})
        offset+=len(line)+1
    texts=[r['text'] for r in rows]
    if not texts or texts[0]!=BEGIN or texts[-2:]!=[KEYBAG_COMPLETE,COMPLETE] or any(texts.count(v)!=1 for v in (BEGIN,COPY_COMPLETE,KEYBAG_COMPLETE,COMPLETE)):
        raise ValueError('Missing/duplicate/wrong combined fresh SEP/keybag markers')
    commands=[];pending=None;volumes={};events=[];event_rows=[];bag=None
    for row in rows[1:-2]:
        text=row['text']
        if text.startswith('INFERNO_PREP_EXEC '):
            if pending: raise ValueError('EXEC without prior status')
            pending=text.removeprefix('INFERNO_PREP_EXEC ')
        elif text.startswith('INFERNO_PREP_STATUS '):
            if not pending or text!='INFERNO_PREP_STATUS raw=0': raise ValueError('Unpaired/failed utility')
            commands.append(pending);pending=None
        elif text.startswith('INFERNO_PREP_VOLUME '):
            m=re.fullmatch(r'INFERNO_PREP_VOLUME (/dev/disk0s1s[1-9][0-9]?) name=(.+)',text)
            if not m or events or pending or m[2] in volumes or m[1] in volumes.values() or not commands or commands[-1]!='/sbin/mount_apfs -o ro '+m[1]+' /mnt1': raise ValueError('Invalid discovery inventory')
            volumes[m[2]]=m[1]
        elif re.fullmatch(r'INFERNO_PREP_DEVICE [A-Za-z0-9]+ type=[0-9]+',text) or re.fullmatch(r'INFERNO_PREP_DISK0_OFFSET4096 [0-9a-f]{64}',text):
            if commands: raise ValueError('Late device inventory')
        else:
            if pending: raise ValueError('Stage event before utility success')
            if set(volumes)!={SYSTEM_NAME,'Data','Update','Preboot','xART','Hardware'}: raise ValueError('Stage event before six-volume inventory')
            if text==COPY_COMPLETE:
                if commands[-1]!='/sbin/mount_apfs -o rw '+volumes['Preboot']+' /mnt2': raise ValueError('SEP copy lacks writable Preboot')
            elif text in ('INFERNO_EFFACEABLE_QUERY status=0 formatted=0 count=1','INFERNO_EFFACEABLE_FORMAT status=0','INFERNO_EFFACEABLE_RECHECK status=0 formatted=1','INFERNO_KEYBAG_CREATE_BEGIN') or text.startswith('INFERNO_KEYBAG_CREATE_RESULT '):
                if commands[-1]!='/usr/libexec/seputil --wait --load /mnt1'+SEP_DESTINATION: raise ValueError('Fresh API event before original SEP load')
                if text.startswith('INFERNO_KEYBAG_CREATE_RESULT '):
                    m=re.fullmatch(r'INFERNO_KEYBAG_CREATE_RESULT status=0 stat=0 size=([1-9][0-9]*) mode=([0-7]+)',text)
                    if not m or int(m[2],8)&0o170000!=0o100000: raise ValueError('Expected fresh success/nonempty regular keybag; existing -4 is not creation')
                    bag={'size':int(m[1]),'mode':m[2],'status':0,'stat':0}
            else: raise ValueError('Unexpected operation or failed fresh initialization: '+text)
            events.append(text);event_rows.append(row)
    expected_events=[COPY_COMPLETE,'INFERNO_EFFACEABLE_QUERY status=0 formatted=0 count=1','INFERNO_EFFACEABLE_FORMAT status=0','INFERNO_EFFACEABLE_RECHECK status=0 formatted=1','INFERNO_KEYBAG_CREATE_BEGIN']
    if pending or bag is None or events[:-1]!=expected_events or not events[-1].startswith('INFERNO_KEYBAG_CREATE_RESULT '): raise ValueError('Incomplete/extra fresh initialization path')
    expected=['/sbin/mount_apfs -o ro '+d+' /mnt1' for d in volumes.values()]+[
        '/sbin/mount_apfs -o rw '+volumes['Preboot']+' /mnt2',
        '/sbin/mount_apfs -o rw '+volumes['xART']+' /mnt7',
        '/sbin/mount_apfs -o ro '+volumes['Preboot']+' /mnt1',
        '/sbin/mount_apfs -o rw '+volumes['Data']+' /mnt2',
        '/usr/libexec/seputil --gigalocker-init',
        '/usr/libexec/seputil --wait --load /mnt1'+SEP_DESTINATION,
        '/usr/libexec/seputil --gigalocker-shutdown']
    if commands!=expected: raise ValueError('Unexpected utility sequence or extra flags')
    copyrow=event_rows[0];copymount=next(r for r in rows if r['text']=='INFERNO_PREP_EXEC '+expected[-7])
    tail=raw[copymount['byte_end']:copyrow['byte_start']]
    if b"unmounting volume 'Preboot'" not in tail or b'(numMountedAPFSVolumes 0)' not in tail: raise ValueError('SEP copy not cleanly unmounted before completion')
    shutdown=next(r for r in rows if r['text']=='INFERNO_PREP_EXEC /usr/libexec/seputil --gigalocker-shutdown')
    if shutdown['byte_start']<=event_rows[-1]['byte_end']: raise ValueError('Shutdown before keybag result')
    tail=raw[shutdown['byte_end']:rows[-2]['byte_start']];cursor=0
    for marker in [b"unmounting volume 'Data'",b"unmounting volume 'Preboot'",b"unmounting volume 'xART'",b'(numMountedAPFSVolumes 0)']:
        at=tail.find(marker,cursor)
        if at<0: raise ValueError('Missing ordered normal keybag unmounts')
        cursor=at+len(marker)
    return {'schema':'inferno.sep-keybag-content.v1','status':'fresh-keybag-created-not-runtime-ready','serial_bytes':len(raw),'serial_sha256':hashlib.sha256(raw).hexdigest(),'records':rows,'commands':commands,'volumes':volumes,'keybag':bag,'fresh_effaceable_transition':[0,1],'sep_destination_bytes_verified':False,'postgrowth_full_data_verified':False,'ipa_runtime_ready':False,'scope':'Original simulated-SEP loader, fresh effaceable and MobileKeyBag API path only; no keybag contents, real SEP security, first unlock or runtime readiness.'}
