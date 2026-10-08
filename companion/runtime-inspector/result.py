# SPDX-License-Identifier: AGPL-3.0-or-later
"""Reconstruct only the fixed launchd cache; never treat a partial export as usable."""
import hashlib
import plistlib
import re

def verify_content(raw):
    if not isinstance(raw,bytes) or len(raw)>64<<20:raise ValueError('Serial size/type bound')
    records=[];offset=0
    for line in raw.split(b'\n'):
        value=line.rstrip(b'\r')
        if b'INFERNO_INSPECT_' in value:
            if value.count(b'INFERNO_INSPECT_')!=1 or offset+len(line)>=len(raw):raise ValueError('Ambiguous/truncated inspector line')
            pos=value.index(b'INFERNO_INSPECT_'); text=value[pos:].decode('ascii')
            records.append({'text':text,'byte_start':offset+pos,'byte_end':offset+len(value),'sha256':hashlib.sha256(value[pos:]).hexdigest()})
        elif b'INFERNO_' in value and b'INFERNO_OWNED_NATIVE_PROBE_V1: executed arm64 Darwin syscalls' not in value:raise ValueError('Unexpected owned operation')
        if b'panic(cpu' in value:raise ValueError('Guest panic')
        offset+=len(line)+1
    texts=[x['text'] for x in records]
    if len(texts)<9 or texts[:2]!=['INFERNO_INSPECT_BEGIN version=1 fixed_files=2','INFERNO_INSPECT_MOUNT status=0 mode=ro']:raise ValueError('Missing/extra BEGIN/mount')
    def file(line,name,maximum,exact=None):
        m=re.fullmatch(r'INFERNO_INSPECT_FILE name='+name+r' bytes=([0-9]+) mode=([0-9]+) uid=0 gid=([0-9]+)',line)
        if not m:raise ValueError('Wrong file metadata')
        size,mode,gid=map(int,m.groups())
        if not 0<size<=maximum or mode&0xf000!=0x8000 or (exact and size!=exact):raise ValueError('Invalid file bound/type')
        return {'bytes':size,'mode':mode,'uid':0,'gid':gid}
    launchd=file(texts[2],'launchd',2<<20);decoded=bytearray();index=3
    while index<len(texts) and texts[index].startswith('INFERNO_INSPECT_DATA '):
        m=re.fullmatch(r'INFERNO_INSPECT_DATA name=launchd offset=([0-9]+) bytes=([0-9]+) hex=([0-9a-f]+)',texts[index])
        if not m:raise ValueError('Malformed export chunk')
        off,n=int(m[1]),int(m[2]);chunk=bytes.fromhex(m[3])
        if off!=len(decoded) or not 0<n<=512 or len(chunk)!=n or len(decoded)+n>launchd['bytes']:raise ValueError('Chunk gap/duplicate/length/bound')
        decoded.extend(chunk);index+=1
    def digest(line,name,size):
        m=re.fullmatch(r'INFERNO_INSPECT_HASH name='+name+r' bytes='+str(size)+r' sha256=([0-9a-f]{64})',line)
        if not m:raise ValueError('Missing/wrong file hash')
        return m[1]
    if index+5!=len(texts) or len(decoded)!=launchd['bytes']:raise ValueError('Incomplete or extra inspector records')
    launchd['sha256']=digest(texts[index],'launchd',len(decoded))
    if hashlib.sha256(decoded).hexdigest()!=launchd['sha256']:raise ValueError('Export hash mismatch')
    dyld=file(texts[index+1],'dyld',2052489216,2052489216);dyld['sha256']=digest(texts[index+2],'dyld',dyld['bytes'])
    if not re.fullmatch(r'INFERNO_INSPECT_UNMOUNT status=0 errno=-?[0-9]+',texts[index+3]) or texts[index+4]!='INFERNO_INSPECT_RESULT status=0':raise ValueError('Unmount/result failed')
    tail=raw[records[index+2]['byte_end']:records[index+3]['byte_start']]
    if b"unmounting volume 'AzulSeed18A5351d.N104N841DeveloperOS'" not in tail or b'(numMountedAPFSVolumes 0)' not in tail:raise ValueError('Missing original clean unmount')
    cache=plistlib.loads(decoded)
    if not isinstance(cache,dict) or not isinstance(cache.get('LaunchDaemons'),dict) or not 0<len(cache['LaunchDaemons'])<=4096:raise ValueError('Unsupported original launchd configuration')
    if any(not isinstance(k,str) or not isinstance(v,dict) for k,v in cache['LaunchDaemons'].items()):raise ValueError('Malformed launchd entries')
    # Do not retain exported bytes in the metadata manifest or tracked evidence.
    compact=[{k:v for k,v in row.items() if k!='text'} if row['text'].startswith('INFERNO_INSPECT_DATA ') else row for row in records]
    return {'schema':'inferno.runtime-inspector-content.v1','content_verified':True,'ipa_runtime_ready':False,
            'serial_bytes':len(raw),'serial_sha256':hashlib.sha256(raw).hexdigest(),'records':compact,
            'launchd':launchd,'launchd_jobs':len(cache['LaunchDaemons']),'dyld':dyld,
            'scope':'Two fixed original System files read-only; launchd bytes reconstructed, full dyld hash only. No patch/install/runtime readiness.'},bytes(decoded)
