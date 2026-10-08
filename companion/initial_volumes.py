# SPDX-License-Identifier: AGPL-3.0-or-later
"""Narrow original-System/role-only preparation gates; no VM or disk mutation."""
import hashlib
import re
from pathlib import Path
from import_stage import strict_json

ORIGINAL_ROOT_SHA = '93f97dae602a8fc844f0f88819d3fe358b1cf14ee5e193b0beb7009376032594'
ORIGINAL_APFS_SHA = '54f0ea7d88b76756b43263eaf40cd5580aaf8871c7e15218822152e73fede44f'
SYSTEM_NAME = 'AzulSeed18A5351d.N104N841DeveloperOS'
BEGIN = 'INFERNO_PREP_BEGIN: disposable /dev/disk0s1 existing=0 roles=1 gigalocker=0'
COMPLETE = 'INFERNO_PREP_COMPLETE: requested preparation operations succeeded'
NEWFS = [
 '/sbin/newfs_apfs -A -o role=b -v Preboot /dev/disk0s1',
 '/sbin/newfs_apfs -s10485760 -A -o role=x -v xART /dev/disk0s1',
 '/sbin/newfs_apfs -s25165824 -A -o role=h -v Hardware /dev/disk0s1',
]


def verify_content(raw):
    if not isinstance(raw, bytes) or len(raw) > 64 << 20:
        raise ValueError('Serial must be bytes bounded64MiB')
    records = []
    offset = 0
    for line in raw.split(b'\n'):
        value = line.rstrip(b'\r')
        if b'INFERNO_PREP_' in value:
            if offset + len(line) >= len(raw):
                raise ValueError('Truncated final preparation line')
            if value.count(b'INFERNO_PREP_') != 1:
                raise ValueError('Ambiguous preparation record')
            position = value.index(b'INFERNO_PREP_')
            text = value[position:].decode('ascii')
            # A kernel diagnostic can precede a helper record on the same LF line.
            records.append({'text': text, 'byte_start': offset + position,
                            'byte_end': offset + len(value),
                            'sha256': hashlib.sha256(value[position:]).hexdigest()})
        if b'INFERNO_' in value and b'INFERNO_PREP_' not in value and b'INFERNO_OWNED_NATIVE_PROBE_V1: executed arm64 Darwin syscalls' not in value:
            raise ValueError('Unexpected owned operation outside role-only phase')
        if b'panic(cpu' in value or b'INFERNO_TREE_MISMATCH' in value:
            raise ValueError('Guest failure in serial')
        offset += len(line) + 1
    texts = [r['text'] for r in records]
    if texts.count(BEGIN) != 1 or texts.count(COMPLETE) != 1 or texts[0] != BEGIN or texts[-1] != COMPLETE:
        raise ValueError('Missing/duplicate/wrong role-only BEGIN or COMPLETE')
    commands = []
    pending = None
    volumes = {}
    for row in records[1:-1]:
        text = row['text']
        if text.startswith('INFERNO_PREP_EXEC '):
            if pending is not None:
                raise ValueError('EXEC missing status')
            pending = text.removeprefix('INFERNO_PREP_EXEC ')
        elif text.startswith('INFERNO_PREP_STATUS '):
            if pending is None or text != 'INFERNO_PREP_STATUS raw=0':
                raise ValueError('Unpaired/failed original utility status')
            commands.append(pending)
            pending = None
        elif text.startswith('INFERNO_PREP_VOLUME '):
            match = re.fullmatch(r'INFERNO_PREP_VOLUME (/dev/disk0s1s[1-9][0-9]?) name=(.+)', text)
            if not match or match[2] in volumes or match[1] in volumes.values():
                raise ValueError('Ambiguous discovered volume')
            if not commands or commands[-1] != '/sbin/mount_apfs -o ro ' + match[1] + ' /mnt1':
                raise ValueError('Volume lacks successful discovery mount')
            volumes[match[2]] = match[1]
        elif re.fullmatch(r'INFERNO_PREP_DEVICE [A-Za-z0-9]+ type=[0-9]+', text):
            pass
        elif re.fullmatch(r'INFERNO_PREP_DISK0_OFFSET4096 [0-9a-f]{64}', text):
            pass
        else:
            raise ValueError('Unexpected preparation operation/failure: ' + text)
    if pending is not None or set(volumes) != {SYSTEM_NAME, 'Preboot', 'xART', 'Hardware'}:
        raise ValueError('Incomplete command/volume set')
    discovered = ['/sbin/mount_apfs -o ro ' + device + ' /mnt1' for device in volumes.values()]
    final = ['/sbin/mount_apfs -o ro ' + volumes[SYSTEM_NAME] + ' /mnt1',
             '/sbin/mount_apfs -o rw ' + volumes['Preboot'] + ' /mnt2']
    if commands != NEWFS + discovered + final:
        raise ValueError('Unexpected role commands/order or extra mounts')
    # Original helper returns before COMPLETE on copyfile or unmount failure.
    # Also retain original filesystem output after the final writable mount.
    final_exec = next(r for r in reversed(records) if r['text'].startswith('INFERNO_PREP_EXEC '))
    tail = raw[final_exec['byte_end']:records[-1]['byte_start']]
    expected = [b"unmounting volume 'Preboot'", ("unmounting volume '" + SYSTEM_NAME + "'").encode(),
                b'(numMountedAPFSVolumes 0)']
    cursor = 0
    for marker in expected:
        found = tail.find(marker, cursor)
        if found < 0:
            raise ValueError('Missing ordered original final unmount evidence')
        cursor = found + len(marker)
    return {'schema': 'inferno.initial-volumes-content.v1', 'content_verified': True,
            'ipa_runtime_ready': False, 'serial_bytes': len(raw),
            'serial_sha256': hashlib.sha256(raw).hexdigest(), 'records': records,
            'commands': commands, 'volumes': volumes,
            'scope': 'Role-only copy/unmount code path corroborated by original logs; no firmware-tree byte readback, Data/keybag/cache/setup or cryptographic boot nonce.'}


def bounded_record(path):
    path = Path(path)
    if path.stat().st_size > 16 << 20:
        raise ValueError('Metadata exceeds16MiB')
    return strict_json(path.read_bytes())
