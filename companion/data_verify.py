# SPDX-License-Identifier: AGPL-3.0-or-later
"""Read-only Data tree verification gates; no VM or disk mutation."""
import hashlib
import re
from pathlib import Path
from import_stage import strict_json

SYSTEM_NAME = 'AzulSeed18A5351d.N104N841DeveloperOS'
BEGIN = 'INFERNO_PREP_BEGIN: disposable /dev/disk0s1 existing=1 roles=0 gigalocker=0'
COMPLETE = 'INFERNO_PREP_COMPLETE: requested preparation operations succeeded'


def verify_content(raw):
    if not isinstance(raw, bytes) or len(raw) > 64 << 20:
        raise ValueError('Serial must be bytes bounded64MiB')
    records = []
    offset = 0
    for line in raw.split(b'\n'):
        value = line.rstrip(b'\r')
        if b'INFERNO_PREP_' in value or b'INFERNO_TREE_' in value:
            if offset + len(line) >= len(raw):
                raise ValueError('Truncated final preparation line')
            if value.count(b'INFERNO_PREP_') + value.count(b'INFERNO_TREE_') != 1:
                raise ValueError('Ambiguous preparation record')
            position = value.index(b'INFERNO_PREP_' if b'INFERNO_PREP_' in value else b'INFERNO_TREE_')
            text = value[position:].decode('ascii')
            # A kernel diagnostic can precede a helper record on the same LF line.
            records.append({'text': text, 'byte_start': offset + position,
                            'byte_end': offset + len(value),
                            'sha256': hashlib.sha256(value[position:]).hexdigest()})
        if b'INFERNO_' in value and b'INFERNO_PREP_' not in value and b'INFERNO_TREE_' not in value and b'INFERNO_OWNED_NATIVE_PROBE_V1: executed arm64 Darwin syscalls' not in value:
            raise ValueError('Unexpected owned operation outside Data verification phase')
        if b'panic(cpu' in value or b'INFERNO_TREE_MISMATCH' in value:
            raise ValueError('Guest failure in serial')
        offset += len(line) + 1
    texts = [r['text'] for r in records]
    if texts.count(BEGIN) != 1 or texts.count(COMPLETE) != 1 or texts[0] != BEGIN or texts[-1] != COMPLETE:
        raise ValueError('Missing/duplicate/wrong Data verification BEGIN or COMPLETE')
    commands = []
    pending = None
    volumes = {}
    tree = None
    progress = None
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
        elif text.startswith('INFERNO_TREE_'):
            match = re.fullmatch(r'INFERNO_TREE_RESULT entries=([0-9]+) files=([0-9]+) links=([0-9]+) bytes=([0-9]+) mismatches=0', text)
            step = re.fullmatch(r'INFERNO_TREE_PROGRESS entries=([0-9]+) bytes=([0-9]+) mismatches=0', text)
            if tree is not None or pending is not None or not commands or commands[-1] != '/sbin/mount_apfs -o ro ' + volumes.get('Data', '?') + ' /mnt2':
                raise ValueError('Tree result/progress outside final read-only Data mount')
            if match:
                values = list(map(int, match.groups()))
                if not values[0] or not values[1] or not values[3] or values[0] < values[1] + values[2]:
                    raise ValueError('Invalid tree totals')
                if progress and (values[0] < progress[0] or values[3] < progress[1]):
                    raise ValueError('Tree totals regress')
                tree = dict(zip(('entries', 'files', 'links', 'bytes'), values))
            elif step:
                values = tuple(map(int, step.groups()))
                if progress and (values[0] < progress[0] or values[1] < progress[1]):
                    raise ValueError('Tree progress regresses')
                progress = values
            else:
                raise ValueError('Malformed or failed tree result')
        elif re.fullmatch(r'INFERNO_PREP_DEVICE [A-Za-z0-9]+ type=[0-9]+', text):
            pass
        elif re.fullmatch(r'INFERNO_PREP_DISK0_OFFSET4096 [0-9a-f]{64}', text):
            pass
        else:
            raise ValueError('Unexpected preparation operation/failure: ' + text)
    if pending is not None or set(volumes) != {SYSTEM_NAME, 'Preboot', 'xART', 'Hardware', 'Data', 'Update'} or tree is None:
        raise ValueError('Incomplete command/volume set')
    discovered = ['/sbin/mount_apfs -o ro ' + device + ' /mnt1' for device in volumes.values()]
    final = ['/sbin/mount_apfs -o ro ' + volumes[SYSTEM_NAME] + ' /mnt1',
             '/sbin/mount_apfs -o ro ' + volumes['Data'] + ' /mnt2']
    if commands != discovered + final:
        raise ValueError('Unexpected verification commands/order or extra mounts')
    # Original helper returns before COMPLETE on copyfile or unmount failure.
    # Also retain original filesystem output after the final writable mount.
    final_exec = next(r for r in records if r['text'].startswith('INFERNO_TREE_RESULT '))
    tail = raw[final_exec['byte_end']:records[-1]['byte_start']]
    expected = [b"unmounting volume 'Data'", ("unmounting volume '" + SYSTEM_NAME + "'").encode(),
                b'(numMountedAPFSVolumes 0)']
    cursor = 0
    for marker in expected:
        found = tail.find(marker, cursor)
        if found < 0:
            raise ValueError('Missing ordered original final unmount evidence')
        cursor = found + len(marker)
    return {'schema': 'inferno.data-verify-content.v1', 'content_verified': True,
            'ipa_runtime_ready': False, 'serial_bytes': len(raw),
            'serial_sha256': hashlib.sha256(raw).hexdigest(), 'records': records,
            'commands': commands, 'volumes': volumes, 'tree': tree,
            'scope': 'Original System var versus Data: bytes, modes, owners, symlink targets and missing/extra entries; not xattrs, ACLs, timestamps or compression encoding. No keybag/cache/setup/app readiness.'}
