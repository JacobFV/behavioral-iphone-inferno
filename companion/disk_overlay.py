#!/usr/bin/env python3
"""Opt-in qcow2 overlays over retained read-only raw bases (no overlay chains).

Bootstrap pinned Ubuntu24.04 arm64 tools outside Git:
    python3 companion/disk_overlay.py bootstrap [--tools-root PATH]
Then boot.py --root-overlay uses that directory (or --overlay-tools-root PATH).
The raw base must have every write permission bit cleared before use. Retain it
at its recorded absolute path for the entire lifetime of every dependent overlay.
This is an operational immutability contract, not protection against a privileged
process changing the file. Startup and shutdown hashes detect such changes.
Never pass an overlay as --root-image; exporting/flattening is not implemented.
"""
# SPDX-License-Identifier: AGPL-3.0-or-later
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import stat
import subprocess
import urllib.request

DEFAULT_TOOLS = Path.home() / '.local/share/inferno/disk-overlay-tools'
PACKAGES = (
    ('qemu-utils', 'pool/main/q/qemu/qemu-utils_8.2.2+ds-0ubuntu1.18_arm64.deb',
     'a7f7ded1090721ea524ad4616fb4ea8111c45b5690bbb066d7d703e63fcef7c6'),
    ('liburing2', 'pool/main/libu/liburing/liburing2_2.5-1build1_arm64.deb',
     'eb386221b1c7a1480c0abdbc8ddb989297a362e3768e4fb541df06757b37929d'),
)


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def bootstrap(root):
    if platform.machine() != 'aarch64':
        raise ValueError('Pinned overlay tools require Ubuntu24.04 arm64')
    root = root.resolve()
    (root / 'downloads').mkdir(parents=True, exist_ok=True)
    packages = []
    for name, member, expected in PACKAGES:
        archive = root / 'downloads' / (name + '.deb')
        url = 'https://ports.ubuntu.com/ubuntu-ports/' + member
        if not archive.exists():
            with urllib.request.urlopen(url, timeout=60) as src, archive.open('xb') as dst:
                while chunk := src.read(1024 * 1024):
                    dst.write(chunk)
        if digest(archive) != expected:
            raise ValueError(f'Package hash mismatch: {archive}')
        subprocess.run(['dpkg-deb', '-x', str(archive), str(root / 'root')], check=True)
        packages.append({'url': url, 'sha256': expected})
    files = {str(p.relative_to(root)): digest(p) for p in (root / 'root').rglob('*')
             if p.is_file() and not p.is_symlink()}
    provenance = {'schema': 'inferno.overlay-tools.v1', 'packages': packages, 'files': files,
                  'host_dependencies': 'Ubuntu24.04 arm64 system shared libraries; not a standalone tool bundle'}
    (root / 'tool-provenance.json').write_text(json.dumps(provenance, indent=2) + '\n')
    return validate_tools(root)


def validate_tools(root):
    root = root.resolve(strict=True)
    provenance = json.loads((root / 'tool-provenance.json').read_text())
    if provenance.get('schema') != 'inferno.overlay-tools.v1':
        raise ValueError('Unsupported overlay tool provenance')
    if [p['sha256'] for p in provenance['packages']] != [p[2] for p in PACKAGES]:
        raise ValueError('Overlay tools do not match pinned packages')
    for name, expected in provenance['files'].items():
        path = root / name
        if not path.resolve().is_relative_to(root) or digest(path) != expected:
            raise ValueError(f'Overlay tool file hash mismatch: {name}')
    binary = root / 'root/usr/bin/qemu-img'
    relative = str(binary.relative_to(root))
    if relative not in provenance['files']:
        raise ValueError('qemu-img missing from tool inventory')
    return {'root': str(root), 'binary': str(binary), 'sha256': digest(binary),
            'provenance': str(root / 'tool-provenance.json'),
            'provenance_sha256': digest(root / 'tool-provenance.json')}


def tool_run(tool, *arguments):
    env = os.environ.copy()
    env['LD_LIBRARY_PATH'] = str(Path(tool['root']) / 'root/usr/lib/aarch64-linux-gnu')
    return subprocess.run([tool['binary'], *map(str, arguments)], check=True,
                          capture_output=True, text=True, env=env).stdout


def validate_base(base, expected):
    base = base.resolve(strict=True)
    before = base.stat()
    if not stat.S_ISREG(before.st_mode) or before.st_mode & 0o222:
        raise ValueError('Overlay raw base must be a regular file with all write mode bits cleared')
    with base.open('rb') as stream:
        if stream.read(4) == b'QFI\xfb':
            raise ValueError('Overlay chains are not supported; backing base must be raw')
    if digest(base) != expected:
        raise ValueError('Overlay backing base SHA256 mismatch')
    after = base.stat()
    fields = ('st_dev', 'st_ino', 'st_size', 'st_mtime_ns', 'st_ctime_ns', 'st_mode')
    if any(getattr(before, key) != getattr(after, key) for key in fields):
        raise ValueError('Overlay backing base changed during verification')
    return {'path': str(base), 'format': 'raw', 'sha256': expected, 'bytes': after.st_size,
            'device': after.st_dev, 'inode': after.st_ino, 'mtime_ns': after.st_mtime_ns,
            'ctime_ns': after.st_ctime_ns, 'mode': oct(stat.S_IMODE(after.st_mode))}


def create_overlay(path, base, expected, tool):
    identity = validate_base(base, expected)
    if path.exists():
        raise ValueError('Overlay destination already exists')
    tool_run(tool, 'create', '-f', 'qcow2', '-F', 'raw', '-b', identity['path'],
             '-o', 'compat=1.1,lazy_refcounts=off', path)
    info = json.loads(tool_run(tool, 'info', '--output=json', '-f', 'qcow2', path))
    if (info['format'] != 'qcow2' or info['backing-filename'] != identity['path'] or
            info.get('backing-filename-format') != 'raw' or
            info['virtual-size'] != identity['bytes']):
        raise ValueError('Created overlay does not match backing identity')
    return {'schema': 'inferno.raw-backed-overlay.v1', 'path': str(path), 'format': 'qcow2',
            'backing': identity, 'tool': tool, 'image_info': info,
            'dependency_warning': 'Retain this immutable raw base at the exact recorded path; overlay is not standalone.',
            'source_sha256': digest(Path(__file__))}


def verify_backing(record):
    current = validate_base(Path(record['backing']['path']), record['backing']['sha256'])
    if current != record['backing']:
        raise ValueError('Overlay backing identity changed since creation')
    return {'unchanged': True, 'sha256': current['sha256']}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['bootstrap'])
    parser.add_argument('--tools-root', type=Path, default=DEFAULT_TOOLS)
    args = parser.parse_args()
    print(json.dumps(bootstrap(args.tools_root), indent=2))
