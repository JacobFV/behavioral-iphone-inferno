#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Import one owned, unencrypted device IPA into an external validated tree.

Host validation only: neither code-signature trust nor guest execution is implied.
"""
import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import plistlib
import re
import stat
import struct
import subprocess
import zipfile

MAX_ENTRIES = 4096
MAX_TOTAL = 128 * 1024 * 1024
MAX_FILE = 64 * 1024 * 1024
MAGICS = {bytes.fromhex(x) for x in ('cffaedfe','cefaedfe','feedfacf','feedface','cafebabe','bebafeca','cafebabf','bfbafeca')}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def version(value):
    if not isinstance(value, str) or not re.fullmatch(r'[0-9]{1,3}(?:\.[0-9]{1,3}){0,2}', value):
        raise ValueError('Expected numeric OS version')
    parts = tuple(map(int, value.split('.')))
    return parts + (0,) * (3-len(parts))


def unpack_version(value):
    return (value >> 16, (value >> 8) & 255, value & 255)


def safe_path(name):
    if not isinstance(name, str) or not name or len(name.encode('utf-8')) > 511:
        raise ValueError('Empty or oversized archive path')
    parts = name.split('/')
    if len(parts) > 16 or any(x in ('', '.', '..') or not re.fullmatch(r'[A-Za-z0-9_. -]{1,127}', x) for x in parts):
        raise ValueError('Unsupported or escaping archive path: '+repr(name))
    return parts


def macho(data):
    if len(data) < 32 or data[:4] != bytes.fromhex('cffaedfe'):
        raise ValueError('First subset requires thin little-endian ARM64 Mach-O; fat/32-bit unsupported')
    _, cpu, subtype, kind, ncmds, sizeofcmds, flags, reserved = struct.unpack_from('<8I', data)
    if cpu != 0x0100000c or subtype & 0x00ffffff != 0 or kind != 2:
        raise ValueError('Require ARM64_ALL device MH_EXECUTE; arm64e/simulator-only unsupported')
    if not 1 <= ncmds <= 4096 or not 8*ncmds <= sizeofcmds <= len(data)-32:
        raise ValueError('Invalid Mach-O command extent')
    pos, end = 32, 32+sizeofcmds
    minimums, dependencies, rpaths, signatures, entrypoints, loaders = [], [], [], [], [], []
    for _ in range(ncmds):
        if pos+8 > end:
            raise ValueError('Truncated Mach-O command')
        cmd, size = struct.unpack_from('<II', data, pos)
        if size < 8 or size % 8 or pos+size > end:
            raise ValueError('Invalid Mach-O command size')
        def string_at(offset, minimum=8):
            if offset < minimum or offset >= size:
                raise ValueError('Invalid Mach-O string offset')
            stop = data.find(b'\0', pos+offset, pos+size)
            if stop < 0:
                raise ValueError('Unterminated Mach-O string')
            return data[pos+offset:stop].decode('ascii')
        if cmd == 0x19:
            if size < 72:
                raise ValueError('Truncated segment command')
            fileoff, filesize = struct.unpack_from('<QQ', data, pos+40)
            nsects = struct.unpack_from('<I', data, pos+64)[0]
            if size != 72+80*nsects or fileoff+filesize > len(data):
                raise ValueError('Invalid segment extent')
        elif cmd == 0x32:
            if size < 24:
                raise ValueError('Truncated build version')
            platform, minos, sdk, tools = struct.unpack_from('<4I', data, pos+8)
            if platform != 2 or 24+8*tools != size:
                raise ValueError('Require iOS device platform, not simulator/Catalyst')
            minimums.append(unpack_version(minos))
        elif cmd == 0x25:
            if size != 16:
                raise ValueError('Invalid minimum iPhoneOS command')
            minimums.append(unpack_version(struct.unpack_from('<I', data, pos+8)[0]))
        elif cmd in (0x24, 0x2f, 0x30):
            raise ValueError('Unsupported non-iPhoneOS platform command')
        elif cmd in (0x21, 0x2c):
            if size < (24 if cmd == 0x2c else 20):
                raise ValueError('Truncated encryption command')
            cryptoff, cryptsize, cryptid = struct.unpack_from('<3I', data, pos+8)
            if cryptid or cryptoff+cryptsize > len(data):
                raise ValueError('Encrypted or invalid encrypted range; no decryption supported')
        elif cmd in (0xc, 0x80000018, 0x8000001f, 0x80000023):
            if size < 24:
                raise ValueError('Truncated dylib command')
            name = string_at(struct.unpack_from('<I', data, pos+8)[0], 24)
            if not name.startswith(('/usr/lib/', '/System/Library/Frameworks/', '/System/Library/PrivateFrameworks/')) or '..' in name.split('/') or '\\' in name:
                raise ValueError('First subset permits system dependencies only: '+name)
            dependencies.append({'path':name, 'weak':cmd == 0x80000018})
        elif cmd == 0x20:
            raise ValueError('Lazy dylib dependencies unsupported in first subset')
        elif cmd == 0xe:
            if size < 16:
                raise ValueError('Truncated dylinker command')
            loader = string_at(struct.unpack_from('<I', data, pos+8)[0], 12)
            if loader != '/usr/lib/dyld':
                raise ValueError('Only original system /usr/lib/dyld loader supported')
            loaders.append(loader)
        elif cmd == 0x8000001c:
            if size < 16:
                raise ValueError('Truncated rpath command')
            rpaths.append(string_at(struct.unpack_from('<I', data, pos+8)[0], 12))
        elif cmd == 0x1d:
            if size != 16:
                raise ValueError('Invalid code-signature command')
            off, length = struct.unpack_from('<II', data, pos+8)
            if not length or off+length > len(data):
                raise ValueError('Invalid code-signature extent')
            signatures.append({'offset':off, 'bytes':length, 'sha256':digest(data[off:off+length])})
        elif cmd == 0x80000028:
            if size != 24:
                raise ValueError('Invalid LC_MAIN')
            off = struct.unpack_from('<Q', data, pos+8)[0]
            if off >= len(data):
                raise ValueError('LC_MAIN entry outside file')
            entrypoints.append(off)
        pos += size
    if pos != end or len(minimums) != 1 or len(entrypoints) != 1 or len(signatures) > 1 or len(loaders) != 1:
        raise ValueError('Ambiguous/missing platform or entrypoint metadata')
    if not (0, 0, 0) < minimums[0] <= (14, 0, 0):
        raise ValueError('Minimum iOS version exceeds supported14.0 guest')
    return {'architecture':'arm64', 'platform':'ios-device', 'minimum_os':'.'.join(map(str, minimums[0])),
            'dependencies':dependencies, 'rpaths':rpaths, 'code_signatures':signatures,
            'entry_file_offset':entrypoints[0], 'encrypted':False,
            'scope':'Structure/compatibility preflight; dependency availability, signature trust and execution unverified'}


def external_output(output):
    output = output.expanduser().absolute()
    if output.exists() or output.is_symlink():
        raise ValueError('Output must be new')
    parent = output.parent.resolve(strict=True)
    probe = subprocess.run(['git','-C',str(parent),'rev-parse','--show-toplevel'], capture_output=True)
    if probe.returncode == 0:
        raise ValueError('Extracted apps must be outside every Git worktree, including ignored directories')
    if probe.returncode != 128:
        raise ValueError('Unable to establish external output location')
    return parent/output.name


def import_ipa(source, output=None):
    output = external_output(output) if output is not None else None
    source = source.resolve(strict=True)
    with source.open('rb') as f:
        before = os.fstat(f.fileno())
        if not stat.S_ISREG(before.st_mode) or not 0 < before.st_size <= MAX_TOTAL:
            raise ValueError('IPA must be a bounded regular file')
        raw = f.read(MAX_TOTAL+1)
        after = os.fstat(f.fileno())
    if (before.st_dev,before.st_ino,before.st_size,before.st_mtime_ns,before.st_ctime_ns) != (after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns,after.st_ctime_ns) or len(raw)!=before.st_size:
        raise ValueError('Input changed during read')
    entries, directories, aliases = {}, set(), {}
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        infos = archive.infolist()
        if not 1 <= len(infos) <= MAX_ENTRIES:
            raise ValueError('Archive entry count exceeds limit')
        total = 0
        for info in infos:
            # zipfile truncates embedded NUL; reject that normalization too.
            if info.orig_filename != info.filename:
                raise ValueError('Normalized/NUL ZIP name unsupported')
            name = info.filename[:-1] if info.is_dir() else info.filename
            parts = safe_path(name)
            folded = name.casefold()
            if folded in aliases:
                raise ValueError('Duplicate/case-colliding archive entry')
            aliases[folded] = name
            mode = info.external_attr >> 16
            typ = stat.S_IFMT(mode)
            if info.flag_bits & 1 or typ not in (0, stat.S_IFDIR if info.is_dir() else stat.S_IFREG):
                raise ValueError('Encrypted ZIP/symlink/specialfile unsupported')
            if info.compress_type not in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED):
                raise ValueError('Unsupported ZIP compression')
            if info.file_size > MAX_FILE or info.file_size > max(1024*1024,100*info.compress_size):
                raise ValueError('Archive member exceeds size/ratio bound')
            total += info.file_size
            if total > MAX_TOTAL:
                raise ValueError('Expanded archive exceeds128MiB')
            if info.is_dir():
                if info.file_size:
                    raise ValueError('Nonempty directory entry')
                directories.add(name)
            else:
                data = archive.read(info)
                if len(data) != info.file_size:
                    raise ValueError('Archive read size mismatch')
                entries[name] = (data, mode)
        all_paths = set(entries) | directories
        for name in list(all_paths):
            parts = name.split('/')
            for i in range(1,len(parts)):
                parent = '/'.join(parts[:i])
                if parent in entries or (parent.casefold() in aliases and aliases[parent.casefold()] != parent):
                    raise ValueError('File/directory or implicit case collision')
                aliases[parent.casefold()] = parent
                directories.add(parent)
        apps = {x.split('/')[1] for x in all_paths if x.startswith('Payload/') and len(x.split('/'))>=2}
        if len(apps) != 1:
            raise ValueError('Require exactlyone Payload app')
        app = next(iter(apps))
        if not app.endswith('.app') or app.casefold().startswith('com.apple.'):
            raise ValueError('Unsupported bundle directory')
        prefix = 'Payload/'+app+'/'
        if any(not x.startswith(prefix) for x in entries) or any(x not in ('Payload','Payload/'+app) and not x.startswith(prefix) for x in directories):
            raise ValueError('First subset accepts Payload/one.app only, no auxiliary payloads')
        files = {x[len(prefix):]:value for x,value in entries.items()}
        dirs = sorted(x[len(prefix):] for x in directories if x.startswith(prefix))
    if 'Info.plist' not in files:
        raise ValueError('Missing root Info.plist')
    info = plistlib.loads(files['Info.plist'][0])
    if not isinstance(info,dict) or info.get('CFBundlePackageType')!='APPL':
        raise ValueError('Require APPL Info.plist')
    identifier, executable = info.get('CFBundleIdentifier'), info.get('CFBundleExecutable')
    if not isinstance(identifier,str) or not re.fullmatch(r'[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+',identifier) or len(identifier)>255 or identifier.lower().startswith('com.apple.'):
        raise ValueError('Require valid non-Apple owned bundle identifier')
    if not isinstance(executable,str) or len(safe_path(executable))!=1 or executable not in files or executable=='Info.plist':
        raise ValueError('Invalid or missing executable')
    if info.get('UIDeviceFamily') not in ([1],[1,2],[2,1]) or any(type(x) is not int for x in info['UIDeviceFamily']):
        raise ValueError('First subset requires explicit iPhone device family')
    minimum = version(info.get('MinimumOSVersion'))
    if not (0,0,0)<minimum<=(14,0,0):
        raise ValueError('Unsupported plist minimumOS')
    details = macho(files[executable][0])
    if version(details['minimum_os']) != minimum:
        raise ValueError('Contradictory plist/Mach-O minimumOS')
    if len(files)+len(dirs) > MAX_ENTRIES:
        raise ValueError('Expanded tree entry count exceeds limit')
    for name in list(files)+dirs:
        if any(x.lower() in ('frameworks','plugins','watch','appclips') or x.lower().endswith(('.appex','.framework','.app')) for x in name.split('/')):
            raise ValueError('Nested code/app extensions unsupported in first subset')
    for name,(data,mode) in files.items():
        if name != executable and data[:4] in MAGICS:
            raise ValueError('Nested Mach-O unsupported in first subset')
        if name != executable and mode & 0o111:
            raise ValueError('Additional executable files unsupported in first subset')
    records = [{'path':name,'bytes':len(data),'sha256':digest(data),'mode':0o755 if name==executable else 0o644} for name,(data,_) in sorted(files.items())]
    tree = {'directories':dirs,'files':records}
    manifest = {'schema':'inferno.owned-ipa-import.v1','status':'validated-not-executed',
        'input':{'path':str(source),'bytes':len(raw),'sha256':digest(raw)},
        'bundle':{'relative_path':'bundle/'+app,'directory_name':app,'identifier':identifier,'executable':executable,'guest_path':'/Applications/'+app,'minimum_os':info['MinimumOSVersion']},
        **tree,'tree_sha256':digest(json.dumps(tree,sort_keys=True,separators=(',',':'),ensure_ascii=True).encode('ascii')),
        'mach_o':details,'limits':{'max_entries':MAX_ENTRIES,'max_expanded_bytes':MAX_TOTAL,'max_file_bytes':MAX_FILE,'max_path_bytes':511,'max_depth':16},
        'importer_sha256':digest(Path(__file__).read_bytes()),
        'scope':'Owned unencrypted thinarm64 iOSdevice app; system dependencies only. Bytes preserved; modes normalized. No signing, guest installation, launch or visual success claimed.'}
    if output is None:
        return manifest
    output.mkdir(mode=0o700)
    target = output/'bundle'/app
    target.mkdir(parents=True,mode=0o755)
    for name in dirs:
        (target/name).mkdir(mode=0o755,parents=True,exist_ok=True)
    for record in records:
        path = target/record['path']
        with path.open('xb') as f:
            f.write(files[record['path']][0])
        path.chmod(record['mode'])
        if digest(path.read_bytes()) != record['sha256']:
            raise ValueError('Extracted file readback mismatch')
    (output/'manifest.json').write_text(json.dumps(manifest,sort_keys=True,indent=2)+'\n')
    return manifest


def validate_manifest(path):
    """Revalidate retained IPA and exact extracted tree; never modify either.

    Return original manifest plus resolved_bundle_path and manifest_path for callers.
    The original IPA is an explicit retained dependency, not optional provenance.
    """
    path = Path(path).expanduser().absolute()
    if path.resolve(strict=True) != path or path.is_symlink() or not path.is_file():
        raise ValueError('Manifest must be an unaliased regular path')
    if path.stat().st_size > 4*1024*1024:
        raise ValueError('Manifest exceeds bound')
    probe = subprocess.run(['git','-C',str(path.parent),'rev-parse','--show-toplevel'],capture_output=True)
    if probe.returncode != 128:
        raise ValueError('Imported tree must remain outside Git')
    raw = path.read_bytes()
    manifest = json.loads(raw)
    expected = import_ipa(Path(manifest['input']['path']))
    if set(manifest) != set(expected):
        raise ValueError('Unexpected manifest fields')
    for key in expected:
        if key != 'importer_sha256' and manifest[key] != expected[key]:
            raise ValueError('Manifest does not match revalidated IPA: '+key)
    if not isinstance(manifest['importer_sha256'],str) or not re.fullmatch('[0-9a-f]{64}',manifest['importer_sha256']):
        raise ValueError('Malformed importer provenance hash')
    target = path.parent / manifest['bundle']['relative_path']
    if target.resolve(strict=True) != target or not target.is_dir() or stat.S_IMODE(target.stat().st_mode) != 0o755:
        raise ValueError('Aliased or missing bundle tree')
    expected_files = {x['path']:x for x in manifest['files']}
    expected_dirs = set(manifest['directories'])
    found_files, found_dirs = set(), set()
    for current, dirs, files in os.walk(target,followlinks=False):
        for name in dirs+files:
            item = Path(current)/name
            relative = item.relative_to(target).as_posix()
            mode = item.lstat().st_mode
            if stat.S_ISDIR(mode):
                if stat.S_IMODE(mode) != 0o755:
                    raise ValueError('Unexpected directory mode')
                found_dirs.add(relative)
            elif stat.S_ISREG(mode):
                record = expected_files.get(relative)
                if record is None or item.stat().st_nlink != 1 or stat.S_IMODE(mode) != record['mode']:
                    raise ValueError('Unexpected file, hardlink or mode')
                before = item.stat()
                if before.st_size != record['bytes'] or digest(item.read_bytes()) != record['sha256']:
                    raise ValueError('Extracted file differs from original IPA')
                after = item.stat()
                if (before.st_dev,before.st_ino,before.st_size,before.st_mtime_ns,before.st_ctime_ns) != (after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns,after.st_ctime_ns):
                    raise ValueError('Extracted file changed during validation')
                found_files.add(relative)
            else:
                raise ValueError('Symlink or specialfile in extracted tree')
    if found_files != set(expected_files) or found_dirs != expected_dirs:
        raise ValueError('Imported tree entries differ from manifest')
    if path.read_bytes() != raw:
        raise ValueError('Manifest changed during validation')
    return {**manifest,'resolved_bundle_path':str(target),'manifest_path':str(path)}


validate_import_manifest = validate_manifest


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--ipa',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    try:
        result=import_ipa(a.ipa,a.output)
    except (OSError,ValueError,KeyError,TypeError,struct.error,zipfile.BadZipFile,RuntimeError) as exc:
        p.exit(1,'IPA import rejected: '+str(exc)+'\n')
    print(json.dumps({'status':result['status'],'manifest':str(a.output/'manifest.json'),'tree_sha256':result['tree_sha256']}))


if __name__=='__main__':
    main()
