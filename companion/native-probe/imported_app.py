"""Revalidate imported owned bytes and generate the bounded recovery copy plan."""
import hashlib
import json
import os
from pathlib import Path
import plistlib
import re
import stat
import struct

MAX_ENTRIES = 4096
MAX_BYTES = 128 * 1024 * 1024


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def safe_path(value):
    if not isinstance(value, str) or len(value.encode('ascii')) > 511:
        raise ValueError('Imported relative path exceeds ASCII bound')
    parts = value.split('/')
    if len(parts)>16 or any(x in ('','.', '..') or not re.fullmatch(r'[A-Za-z0-9_. -]+',x) for x in parts):
        raise ValueError('Unsafe imported relative path')
    return value


def validate(path, manifest_sha256, fixture_pin=None):
    if path.is_symlink() or not path.is_file() or digest(path)!=manifest_sha256:
        raise ValueError('Imported manifest must be regular and explicitly hash-pinned')
    m=json.loads(path.read_text())
    if m.get('schema')!='inferno.owned-ipa-import.v1' or m.get('status')!='validated-not-executed':
        raise ValueError('Unsupported import manifest')
    bundle=m['bundle'];name=safe_path(bundle['directory_name'])
    if '/' in name or not name.endswith('.app') or len(name.encode())>=128:
        raise ValueError('Unsupported bundle directory name')
    identifier=bundle['identifier'];executable=safe_path(bundle['executable'])
    if '/' in executable or not re.fullmatch(r'[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+',identifier) or identifier.lower().startswith('com.apple.') or len(identifier)>=256:
        raise ValueError('Unsafe or Apple bundle identity')
    if bundle['relative_path']!='bundle/'+name or bundle['guest_path']!='/Applications/'+name:
        raise ValueError('Manifest bundle paths disagree')
    root=path.parent/'bundle'/name
    if (path.parent/'bundle').is_symlink() or root.is_symlink() or not root.is_dir():
        raise ValueError('Imported bundle cannot be a symlink')
    files=m['files'];dirs=m['directories']
    if not files or len(files)+len(dirs)>MAX_ENTRIES:
        raise ValueError('Imported tree entry bound exceeded')
    expected={};folded=set();total=0
    for d in dirs:
        d=safe_path(d)
        if d in expected or d.casefold() in folded:raise ValueError('Duplicate/casefold collision')
        expected[d]={'path':d,'type':1,'mode':493,'bytes':0};folded.add(d.casefold())
    for f in files:
        if set(f)!={'path','bytes','sha256','mode'}:raise ValueError('Unexpected file record fields')
        name_=safe_path(f['path'])
        if name_ in expected or name_.casefold() in folded or type(f['bytes']) is not int or not 0<=f['bytes']<=64*1024*1024 or f['mode'] not in (420,493) or not re.fullmatch('[a-f0-9]{64}',f['sha256']):raise ValueError('Invalid file record')
        expected[name_]={**f,'type':2};folded.add(name_.casefold());total+=f['bytes']
    if total>MAX_BYTES:raise ValueError('Imported tree byte bound exceeded')
    actual=set()
    for current, children, names in os.walk(root,followlinks=False):
        for n in children+names:
            p=Path(current)/n;r=p.relative_to(root).as_posix();st=p.lstat();actual.add(r)
            if r not in expected or not (stat.S_ISDIR(st.st_mode) or stat.S_ISREG(st.st_mode)) or st.st_nlink>1 and stat.S_ISREG(st.st_mode):raise ValueError('Extra/special/hardlinked tree entry')
            e=expected[r]
            if (e['type']==1)!=stat.S_ISDIR(st.st_mode) or stat.S_IMODE(st.st_mode)!=e['mode']:raise ValueError('Imported metadata differs')
            if e['type']==2 and (st.st_size!=e['bytes'] or digest(p)!=e['sha256']):raise ValueError('Imported bytes differ')
    if actual!=set(expected):raise ValueError('Imported tree has missing entries')
    canonical=json.dumps({'directories':sorted(dirs),'files':sorted(files,key=lambda x:x['path'])},sort_keys=True,separators=(',',':'),ensure_ascii=True).encode('ascii')
    tree=hashlib.sha256(canonical).hexdigest()
    if tree!=m['tree_sha256']:raise ValueError('Tree hash mismatch')
    info=plistlib.loads((root/'Info.plist').read_bytes())
    if info.get('CFBundleIdentifier')!=identifier or info.get('CFBundleExecutable')!=executable or info.get('CFBundlePackageType')!='APPL':raise ValueError('Info identity mismatch')
    if executable not in expected or expected[executable]['type']!=2 or expected[executable]['mode']!=493:raise ValueError('Missing executable')
    ipa=Path(m['input']['path'])
    if not ipa.is_file() or ipa.is_symlink() or ipa.stat().st_size!=m['input']['bytes'] or digest(ipa)!=m['input']['sha256']:raise ValueError('Source IPA provenance mismatch')
    allow=bool(fixture_pin)
    if allow and (fixture_pin!=tree or bundle['directory_name']!='InfernoProbe.app' or identifier!='org.inferno.companion.probe' or executable!='InfernoProbe' or dirs or set(expected)!={'Info.plist','InfernoProbe'}):raise ValueError('Only explicitly pinned identical owned fixture may collide')
    records=sorted(expected.values(),key=lambda x:(x['path'].count('/'),x['type'],x['path']))
    def cstring(s,n):
        b=s.encode('ascii')
        if len(b)>=n:raise ValueError('Copy plan field too long')
        return b+bytes(n-len(b))
    plan=struct.pack('<8sIIQ128s256s',b'IFAPP001',len(records),int(allow),total,cstring(bundle['directory_name'],128),cstring(identifier,256))
    for e in records:plan+=struct.pack('<512sIIQ',cstring(e['path'],512),e['mode'],e['type'],e['bytes'])
    return m,root,records,plan
