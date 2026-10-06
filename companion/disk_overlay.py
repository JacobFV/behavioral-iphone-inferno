#!/usr/bin/env python3
"""Opt-in qcow2 overlays over retained read-only bases with bounded recorded chains.

Bootstrap pinned Ubuntu24.04 arm64 tools outside Git:
    python3 companion/disk_overlay.py bootstrap [--tools-root PATH]
Then boot.py --root-overlay uses that directory (or --overlay-tools-root PATH).
The raw base must have every write permission bit cleared before use. Retain it
at its recorded absolute path for the entire lifetime of every dependent overlay.
This is an operational immutability contract, not protection against a privileged
process changing the file. Startup and shutdown hashes detect such changes.
Never pass an overlay as --root-image. Use --overlay-base-report for a normally
stopped owned attempt; exporting/flattening is not implemented.
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



def reject_writable_handles(identity):
    """Mode bits do not revoke a writer that opened the inode before freezing."""
    for process in Path('/proc').iterdir():
        if not process.name.isdigit():
            continue
        try:
            for descriptor in (process / 'fd').iterdir():
                try:
                    current = descriptor.stat()
                    if (current.st_dev, current.st_ino) != (identity.st_dev, identity.st_ino):
                        continue
                    flags = next(line.split()[1] for line in
                                 (process / 'fdinfo' / descriptor.name).read_text().splitlines()
                                 if line.startswith('flags:'))
                    if int(flags, 8) & os.O_ACCMODE != os.O_RDONLY:
                        raise ValueError('Backing inode still has an open writable descriptor: ' + str(descriptor))
                except (FileNotFoundError, PermissionError, ProcessLookupError):
                    pass
        except (FileNotFoundError, PermissionError, ProcessLookupError):
            pass

def validate_base(base, expected, image_format="raw"):
    base = base.resolve(strict=True)
    before = base.stat()
    if not stat.S_ISREG(before.st_mode) or before.st_mode & 0o222:
        raise ValueError('Overlay backing must be a regular file with all write mode bits cleared')
    reject_writable_handles(before)
    with base.open('rb') as stream:
        is_qcow = stream.read(4) == b'QFI\xfb'
        if is_qcow != (image_format == 'qcow2'):
            raise ValueError('Backing format does not match the recorded raw/qcow2 type')
    if digest(base) != expected:
        raise ValueError('Overlay backing base SHA256 mismatch')
    after = base.stat()
    fields = ('st_dev', 'st_ino', 'st_size', 'st_mtime_ns', 'st_ctime_ns', 'st_mode')
    if any(getattr(before, key) != getattr(after, key) for key in fields):
        raise ValueError('Overlay backing base changed during verification')
    return {'path': str(base), 'format': image_format, 'sha256': expected, 'bytes': after.st_size,
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
    if record['schema'] == 'inferno.recorded-overlay-chain.v1':
        chain = load_stopped_overlay(Path(record['backing_report']), record['tool'])
        if (chain['layers'] != record['dependencies'] or
                chain['report_sha256'] != record['backing_report_sha256'] or
                chain['stopped_manifest_sha256'] != record['stopped_manifest_sha256']):
            raise ValueError('Recorded overlay dependency chain changed')
        return {'unchanged': True, 'layers': chain['layers']}
    current = validate_base(Path(record['backing']['path']), record['backing']['sha256'])
    if current != record['backing']:
        raise ValueError('Overlay backing identity changed since creation')
    return {'unchanged': True, 'sha256': current['sha256']}


MAX_OVERLAY_DEPTH = 4
AUXILIARY_SIZES = {'firmware.raw': 8 << 20, 'syscfg.raw': 128 << 10,
                   'ctrl_bits.raw': 8 << 10, 'nvram.raw': 8 << 10,
                   'effaceable.raw': 4 << 10, 'panic_log.raw': 1 << 20}


def load_stopped_overlay(report_path, tool, seen=()):
    """Accept only recorded owned stopped layers, never arbitrary qcow2 paths."""
    if report_path.is_dir():
        report_path = report_path / 'report.json'
    report_path = report_path.resolve(strict=True)
    if str(report_path) in seen or len(seen) >= MAX_OVERLAY_DEPTH:
        raise ValueError('Overlay report cycle or depth limit exceeded')
    seen = (*seen, str(report_path))
    directory = report_path.parent
    report_hash = digest(report_path)
    report = json.loads(report_path.read_text())
    if report.get('kind') not in ('t8030_direct_root_experiment', 't8030_recovery_ramdisk_experiment',
                                  'firmware_free_qemu_overlay_block_execution'):
        raise ValueError('Backing source must be an owned boot/block-test report')
    if report.get('exit_code') != 0 or not isinstance(report.get('quit_response'), dict):
        raise ValueError('Backing source must record normal emulator exit0 and QMP quit acknowledgement')
    quit_response = report['quit_response']
    if quit_response.get('return') != {} or not isinstance(quit_response.get('id'), int):
        raise ValueError('Invalid recorded QMP quit acknowledgement')
    transcript = [json.loads(line) for line in (directory / 'qmp-transcript.jsonl').read_text().splitlines()]
    sent = [json.loads(x['raw']) for x in transcript if x['direction'] == 'send']
    received = [json.loads(x['raw']) for x in transcript if x['direction'] == 'receive']
    if not (any(x.get('execute') == 'quit' and x.get('id') == quit_response['id'] for x in sent)
            and quit_response in received
            and any(x.get('event') == 'SHUTDOWN' and x.get('data', {}).get('reason') == 'host-qmp-quit'
                    for x in received)):
        raise ValueError('Raw QMP transcript does not establish normal shutdown')
    manifest_path = directory / 'stopped-disk-hashes.json'
    manifest = json.loads(manifest_path.read_text())
    if set(manifest) != {'root.qcow2', *AUXILIARY_SIZES}:
        raise ValueError('Stopped manifest must contain exactly root.qcow2 and six raw namespaces')
    root_path = directory / 'disks/root.qcow2'
    for name, entry in manifest.items():
        path = directory / 'disks' / name
        if entry['path'] != str(path) or path.is_symlink() or path.stat().st_size != entry['bytes']:
            raise ValueError('Stopped namespace path/size mismatch: ' + name)
        if name in AUXILIARY_SIZES:
            if entry['bytes'] != AUXILIARY_SIZES[name] or digest(path) != entry['sha256']:
                raise ValueError('Stopped auxiliary hash/size mismatch: ' + name)
    own = validate_base(root_path, manifest['root.qcow2']['sha256'], 'qcow2')
    record = json.loads((directory / 'root-overlay.json').read_text())
    if record != report.get('root_overlay') or record.get('path') != str(root_path):
        raise ValueError('Root overlay sidecar does not match its owned stopped report')
    if record.get('backing_after_stop', {}).get('unchanged') is not True:
        raise ValueError('Source did not verify backing after shutdown')
    if record['schema'] == 'inferno.raw-backed-overlay.v1':
        verify_backing(record)
        layers = [own, record['backing']]
    elif record['schema'] == 'inferno.recorded-overlay-chain.v1':
        parent = load_stopped_overlay(Path(record['backing_report']), tool, seen)
        if (parent['layers'] != record['dependencies'] or parent['report_sha256'] != record['backing_report_sha256'] or
                parent['stopped_manifest_sha256'] != record['stopped_manifest_sha256']):
            raise ValueError('Ancestor recorded identity or report hash changed')
        layers = [own, *parent['layers']]
    else:
        raise ValueError('Unsupported owned overlay record schema')
    if len(layers) > MAX_OVERLAY_DEPTH:  # Adding a child makes len(layers) qcow2 layers.
        raise ValueError('New child would exceed four qcow2 layers')
    info = json.loads(tool_run(tool, 'info', '--output=json', '-f', 'qcow2', root_path))
    if (info.get('backing-filename') != layers[1]['path'] or
            info.get('backing-filename-format') != layers[1]['format'] or
            info['virtual-size'] != layers[-1]['bytes']):
        raise ValueError('Actual qcow2 header differs from tracked dependency chain')
    if digest(report_path) != report_hash:
        raise ValueError('Backing report changed during verification')
    return {'report': str(report_path), 'report_sha256': report_hash,
            'stopped_manifest': str(manifest_path), 'stopped_manifest_sha256': digest(manifest_path),
            'layers': layers, 'virtual_size': info['virtual-size'], 'auxiliary': manifest}


def protect_dependencies(layers, child):
    """Extra filename makes historical exact-seven-raw-file retirement fail."""
    markers = []
    for identity in layers:
        marker = Path(identity['path']).parent / 'KEEP-OVERLAY-BACKING.json'
        if marker.exists():
            existing = json.loads(marker.read_text())
            backing = existing.get('backing', {})
            if backing.get('path') != identity['path'] or backing.get('sha256') != identity['sha256']:
                raise ValueError('Existing retention marker does not match immutable dependency')
        else:
            with marker.open('x') as stream:
                json.dump({'backing': identity, 'consumer_overlay': str(child),
                           'retirement_prohibited_while_dependent_overlays_exist': True,
                           'guard': 'Extra file intentionally rejects historical exact-seven-file retirement.'}, stream, indent=2)
                stream.write('\n')
        markers.append(str(marker))
    return markers


def create_recorded_overlay(path, source_report, tool):
    chain = load_stopped_overlay(source_report, tool)
    if path.exists():
        raise ValueError('Overlay destination already exists')
    markers = protect_dependencies(chain['layers'], path)
    tool_run(tool, 'create', '-f', 'qcow2', '-F', 'qcow2', '-b', chain['layers'][0]['path'],
             '-o', 'compat=1.1,lazy_refcounts=off', path)
    info = json.loads(tool_run(tool, 'info', '--output=json', '-f', 'qcow2', path))
    if (info.get('backing-filename') != chain['layers'][0]['path'] or
            info.get('backing-filename-format') != 'qcow2' or info['virtual-size'] != chain['virtual_size']):
        raise ValueError('Created overlay does not match recorded parent')
    return {'schema': 'inferno.recorded-overlay-chain.v1', 'path': str(path), 'format': 'qcow2',
            'backing_report': chain['report'], 'backing_report_sha256': chain['report_sha256'],
            'stopped_manifest': chain['stopped_manifest'], 'stopped_manifest_sha256': chain['stopped_manifest_sha256'],
            'dependencies': chain['layers'], 'retention_markers': markers, 'tool': tool,
            'image_info': info, 'source_sha256': digest(Path(__file__)),
            'dependency_warning': 'Retain every immutable layer and recorded report at its exact absolute path.'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['bootstrap'])
    parser.add_argument('--tools-root', type=Path, default=DEFAULT_TOOLS)
    args = parser.parse_args()
    print(json.dumps(bootstrap(args.tools_root), indent=2))
