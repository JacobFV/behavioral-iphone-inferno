# SPDX-License-Identifier: AGPL-3.0-or-later
"""Strict original-API growth serial validation; two-file consistency only."""
import hashlib
import re

REQUESTED_BYTES = 34358669312
FILES = ('/mnt1/System/Library/CoreServices/SystemVersion.plist', '/mnt1/sbin/launchd')

def verify_content(raw):
    if not isinstance(raw, bytes) or len(raw) > 64 << 20:
        raise ValueError('Expected bounded serial bytes')
    rows = []
    offset = 0
    for line in raw.split(b'\n'):
        value = line.rstrip(b'\r')
        if b'INFERNO_GROW_' in value:
            if offset + len(line) >= len(raw) or value.count(b'INFERNO_GROW_') != 1:
                raise ValueError('Ambiguous or truncated growth record')
            start = value.index(b'INFERNO_GROW_'); text = value[start:].decode('ascii')
            rows.append({'text': text, 'byte_start': offset + start, 'byte_end': offset + len(value),
                         'sha256': hashlib.sha256(value[start:]).hexdigest()})
        elif b'INFERNO_' in value and b'INFERNO_OWNED_NATIVE_PROBE_V1: executed arm64 Darwin syscalls' not in value:
            raise ValueError('Unexpected owned guest operation')
        if b'panic(cpu' in value:
            raise ValueError('Guest panic')
        offset += len(line) + 1
    texts = [r['text'] for r in rows]
    if len(texts) != 13 or texts[0] != f'INFERNO_GROW_BEGIN device=/dev/disk0s1 requested_bytes={REQUESTED_BYTES}':
        raise ValueError('Incomplete/extra/wrong growth record sequence')
    spaces=[]; fingerprints=[]
    for start in (1,7):
        if texts[start] != 'INFERNO_GROW_MOUNT raw_status=0':raise ValueError('Read-only mount failed')
        match=re.fullmatch(r'INFERNO_GROW_SPACE block_size=4096 blocks=([0-9]+) available=([0-9]+)',texts[start+1])
        if not match:raise ValueError('Invalid statfs result')
        blocks,available=map(int,match.groups())
        if not 0<blocks or available>blocks:raise ValueError('Invalid statfs bounds')
        spaces.append({'block_size':4096,'blocks':blocks,'available':available})
        pair=[]
        for j,path in enumerate(FILES):
            match=re.fullmatch(re.escape('INFERNO_GROW_FILE '+path)+r' bytes=([0-9]+) fnv1a64=([0-9a-f]{16})',texts[start+2+j])
            if not match or int(match[1])<=0:raise ValueError('Invalid file fingerprint')
            pair.append({'path':path,'bytes':int(match[1]),'fnv1a64':match[2]})
        fingerprints.append(pair)
        if not re.fullmatch(r'INFERNO_GROW_UNMOUNT result=0 errno=-?[0-9]+',texts[start+4]):raise ValueError('Unmount failed')
    if texts[6]!='INFERNO_GROW_API_RETURN status=0 hex=00000000':raise ValueError('Original resize API failed')
    before,after=spaces
    if before['blocks']>=REQUESTED_BYTES//4096 or after['blocks']<=before['blocks'] or after['blocks']*4096<31<<30 or after['blocks']>REQUESTED_BYTES//4096:
        raise ValueError('Container capacity did not grow within requested geometry')
    if fingerprints[0]!=fingerprints[1]:raise ValueError('Original System fingerprints differ')
    if texts[12]!=f"INFERNO_GROW_COMPLETE before_blocks={before['blocks']} after_blocks={after['blocks']} file_consistency=pass":raise ValueError('Wrong completion totals')
    # Require actual original filesystem unmount text in both inspection intervals.
    for first,last in ((1,5),(7,11)):
        region=raw[rows[first]['byte_start']:rows[last]['byte_end']]
        if b"unmounting volume 'AzulSeed18A5351d.N104N841DeveloperOS'" not in region or b'(numMountedAPFSVolumes 0)' not in region:
            raise ValueError('Missing original clean System unmount evidence')
    return {'schema':'inferno.grow-data-content.v1','content_verified':True,'ipa_runtime_ready':False,
            'serial_bytes':len(raw),'serial_sha256':hashlib.sha256(raw).hexdigest(),'records':rows,
            'requested_bytes':REQUESTED_BYTES,'spaces':spaces,'fingerprints':fingerprints,
            'scope':'Original APFSContainerResize return0, capacity increase and two System file length/FNV consistency checks; no whole-Data postgrowth equality or runtime readiness.'}
