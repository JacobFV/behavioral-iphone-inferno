# SPDX-License-Identifier: AGPL-3.0-or-later
"""Raw original Data seed path gates. Successful copy calls are not tree equality."""
import hashlib
import re
from initial_volumes import SYSTEM_NAME, COMPLETE

BEGIN = 'INFERNO_PREP_BEGIN: disposable /dev/disk0s1 existing=1 roles=0 gigalocker=0'
DATA_COMPLETE = 'INFERNO_DATA_COMPLETE: original var seeded; Update and Hardware mount paths prepared'
NEWFS = ['/sbin/newfs_apfs -A -o role=d -v Data /dev/disk0s1',
         '/sbin/newfs_apfs -A -o role=p -v Update /dev/disk0s1']


def verify_content(raw):
    if not isinstance(raw, bytes) or len(raw) > 64 << 20:
        raise ValueError('Serial must be bytes bounded64MiB')
    records = []; offset = 0
    for line in raw.split(b'\n'):
        value = line.rstrip(b'\r')
        if b'panic(cpu' in value:
            raise ValueError('Guest panic')
        if b'INFERNO_' in value:
            if offset + len(line) >= len(raw) or value.count(b'INFERNO_') != 1:
                raise ValueError('Truncated/ambiguous owned record')
            at = value.index(b'INFERNO_')
            text = value[at:].decode('ascii')
            if text != 'INFERNO_OWNED_NATIVE_PROBE_V1: executed arm64 Darwin syscalls':
                records.append({'text': text, 'byte_start': offset + at,
                                'byte_end': offset + len(value), 'sha256': hashlib.sha256(value[at:]).hexdigest()})
        offset += len(line) + 1
    texts = [r['text'] for r in records]
    if not texts or texts.count(BEGIN) != 1 or texts.count(COMPLETE) != 1 or texts.count(DATA_COMPLETE) != 1 or texts[0] != BEGIN or texts[-2:] != [DATA_COMPLETE, COMPLETE]:
        raise ValueError('Missing/duplicate/wrong seed BEGIN/DATA_COMPLETE/COMPLETE')
    commands = []; pending = None; volumes = {}; spaces = {}; copies = []; phase = 'discovery'
    for row in records[1:-2]:
        text = row['text']
        if text.startswith('INFERNO_PREP_EXEC '):
            if pending is not None:
                raise ValueError('EXEC missing status')
            pending = text.removeprefix('INFERNO_PREP_EXEC ')
        elif text.startswith('INFERNO_PREP_STATUS '):
            if pending is None or text != 'INFERNO_PREP_STATUS raw=0':
                raise ValueError('Unpaired/failed original utility status')
            commands.append(pending); pending = None
        elif text.startswith('INFERNO_PREP_VOLUME '):
            m = re.fullmatch(r'INFERNO_PREP_VOLUME (/dev/disk0s1s[1-9][0-9]?) name=(.+)', text)
            if phase != 'discovery' or not m or m[2] in volumes or m[1] in volumes.values() or not commands or commands[-1] != '/sbin/mount_apfs -o ro ' + m[1] + ' /mnt1':
                raise ValueError('Ambiguous/unmounted discovery volume')
            volumes[m[2]] = m[1]
        elif text.startswith('INFERNO_SPACE '):
            m = re.fullmatch(r'INFERNO_SPACE (before|after)-data-seed block_size=(\d+) available_blocks=(\d+) available_bytes=(\d+)', text)
            if not m or m[1] in spaces or int(m[2]) * int(m[3]) != int(m[4]) or int(m[2]) <= 0 or int(m[4]) <= 0:
                raise ValueError('Invalid/duplicate seed capacity record')
            if m[1] == 'before':
                if phase != 'discovery' or set(volumes) != {SYSTEM_NAME, 'Preboot', 'xART', 'Hardware', 'Data', 'Update'} or commands[-2:] != ['/sbin/mount_apfs -o ro ' + volumes[SYSTEM_NAME] + ' /mnt1', '/sbin/mount_apfs -o rw ' + volumes['Data'] + ' /mnt2']:
                    raise ValueError('Before-space must follow exact seed mounts')
                phase = 'var'
            else:
                if phase != 'var' or not copies:
                    raise ValueError('After-space before original var copy')
                phase = 'hardware'
            spaces[m[1]] = {'block_size': int(m[2]), 'available_blocks': int(m[3]), 'available_bytes': int(m[4])}
        elif text.startswith('INFERNO_COPY '):
            prefix, target = ('/mnt1/private/var/', '/mnt2/') if phase == 'var' else ('/mnt1/System/Library/Caches/com.apple.factorydata/', '/mnt4/FactoryData/System/Library/Caches/com.apple.factorydata/')
            if phase not in ('var', 'hardware'):
                raise ValueError('Copy outside seed phase')
            if phase == 'hardware' and (not commands or commands[-1] != '/sbin/mount_apfs -o rw ' + volumes['Hardware'] + ' /mnt4'):
                raise ValueError('Factory data copy lacks Hardware mount')
            match = re.fullmatch('INFERNO_COPY ' + re.escape(prefix) + r'([^/\x00\r\n]+) -> ' + re.escape(target) + r'\1', text)
            if not match or match[1] in ('.', '..') or text in copies:
                raise ValueError('Unexpected/duplicate copy path')
            copies.append(text)
        elif re.fullmatch(r'INFERNO_PREP_DEVICE [A-Za-z0-9]+ type=[0-9]+', text) or re.fullmatch(r'INFERNO_PREP_DISK0_OFFSET4096 [0-9a-f]{64}', text):
            if commands:
                raise ValueError('Late device inventory')
        else:
            raise ValueError('Unexpected seed operation/failure: ' + text)
    if pending or set(volumes) != {SYSTEM_NAME, 'Data', 'Update', 'Preboot', 'xART', 'Hardware'} or set(spaces) != {'before', 'after'}:
        raise ValueError('Incomplete seed operations/inventory/capacity')
    expected = NEWFS + ['/sbin/mount_apfs -o ro ' + d + ' /mnt1' for d in volumes.values()] + [
        '/sbin/mount_apfs -o ro ' + volumes[SYSTEM_NAME] + ' /mnt1',
        '/sbin/mount_apfs -o rw ' + volumes['Data'] + ' /mnt2',
        '/sbin/mount_apfs -o rw ' + volumes['Hardware'] + ' /mnt4']
    if commands != expected:
        raise ValueError('Unexpected utility commands/order')
    last = next(r for r in reversed(records) if r['text'].startswith('INFERNO_PREP_EXEC '))
    tail = raw[last['byte_end']:records[-2]['byte_start']]; cursor = 0
    for marker in [b"unmounting volume 'Hardware'", b"unmounting volume 'Data'", ("unmounting volume '" + SYSTEM_NAME + "'").encode(), b'(numMountedAPFSVolumes 0)']:
        found = tail.find(marker, cursor)
        if found < 0:
            raise ValueError('Missing ordered clean seed unmount evidence')
        cursor = found + len(marker)
    return {'schema': 'inferno.data-seed-content.v1', 'status': 'seeded-not-byteverified',
            'copy_path_succeeded': True, 'tree_bytes_verified': False, 'ipa_runtime_ready': False,
            'serial_bytes': len(raw), 'serial_sha256': hashlib.sha256(raw).hexdigest(),
            'records': records, 'commands': commands, 'volumes': volumes, 'space': spaces, 'copies': copies,
            'scope': 'Original utility/copy/unmount path only. Requires separate read-only tree comparison; no keybag, setup, launch or IPA readiness.'}
