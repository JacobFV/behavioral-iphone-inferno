#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Clone recovery ramdisk and add only owned app-staging assets and launch job."""
import argparse
import hashlib
import json
from pathlib import Path
import plistlib
import shutil
import subprocess


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--profile', required=True, type=Path)
    p.add_argument('--raw-ramdisk', required=True, type=Path)
    p.add_argument('--raw-sha256', required=True)
    p.add_argument('--build', required=True, type=Path)
    p.add_argument('--hfsplus', required=True, type=Path)
    p.add_argument('--output', required=True, type=Path)
    a = p.parse_args()
    if sha(a.raw_ramdisk) != a.raw_sha256:
        p.error('decoded ramdisk SHA256 mismatch')
    if a.output.resolve().is_relative_to(Path(__file__).resolve().parents[2]):
        p.error('output must be outside repository')
    build = json.loads((a.build / 'build-evidence.json').read_text())
    assets = {
        'inferno-stage-app': (a.build / 'InfernoProbe.app/InfernoProbe', build['bundle']['InfernoProbe']),
        'inferno-stage-info': (a.build / 'InfernoProbe.app/Info.plist', build['bundle']['Info.plist']),
        'inferno-stage-launcher': (a.build / 'inferno-launcher', build['launcher_sha256']),
        'inferno-stage-job': (a.build / 'org.inferno.app-probe.plist', build['sources']['org.inferno.app-probe.plist']),
    }
    stager = a.build / 'inferno-stage-app'
    if sha(stager) != build['stager_sha256']:
        p.error('stager SHA256 mismatch')
    for path, expected in assets.values():
        if sha(path) != expected:
            p.error(f'asset SHA256 mismatch: {path}')
    a.output.mkdir(parents=True, exist_ok=False)
    raw = a.output / 'ramdisk.raw'
    shutil.copyfile(a.raw_ramdisk, raw)
    operations = []

    def hfs(*args):
        argv = [str(a.hfsplus), str(raw), *map(str, args)]
        result = subprocess.run(argv, capture_output=True, text=True, timeout=30)
        operations.append({'argv': argv, 'returncode': result.returncode,
                           'stdout': result.stdout, 'stderr': result.stderr})
        (a.output / 'operations.json').write_text(json.dumps(operations, indent=2) + '\n')
        result.check_returncode()

    hfs('mv', '/System/Library/LaunchDaemons/com.apple.restored_external.plist',
        '/usr/share/com.apple.restored_external.plist.disabled')
    for name, (path, expected) in assets.items():
        destination = '/usr/share/' + name
        hfs('add', path, destination)
        hfs('chmod', '644', destination)
        readback = a.output / ('readback-' + name)
        hfs('extract', destination, readback)
        if sha(readback) != expected:
            raise RuntimeError(f'ramdisk readback mismatch: {name}')
    hfs('add', stager, '/usr/bin/inferno-stage-app')
    hfs('chmod', '755', '/usr/bin/inferno-stage-app')
    hfs('extract', '/usr/bin/inferno-stage-app', a.output / 'readback-stager')
    if sha(a.output / 'readback-stager') != build['stager_sha256']:
        raise RuntimeError('ramdisk stager readback mismatch')
    job = a.output / 'org.inferno.stage-app.plist'
    job.write_bytes(plistlib.dumps({
        'Label': 'org.inferno.stage-app',
        'ProgramArguments': ['/usr/bin/inferno-stage-app', '--disposable-app-stage'],
        'RunAtLoad': True, 'UserName': 'root',
        'StandardOutPath': '/dev/console', 'StandardErrorPath': '/dev/console',
    }))
    hfs('add', job, '/System/Library/LaunchDaemons/org.inferno.stage-app.plist')
    hfs('chmod', '644', '/System/Library/LaunchDaemons/org.inferno.stage-app.plist')
    profile = json.loads(a.profile.read_text())
    profile['ramdisk'] = {'path': str(raw.resolve()), 'size': raw.stat().st_size, 'sha256': sha(raw)}
    profile['provenance']['app_staging'] = {
        'source_raw_sha256': a.raw_sha256, 'build_evidence_sha256': sha(a.build / 'build-evidence.json'),
        'hfsplus_sha256': sha(a.hfsplus), 'preparer_sha256': sha(Path(__file__)),
        'description': 'Cloned recovery with owned assets and staging job; moved original restored job without deleting HFS attributes.',
    }
    (a.output / 'profile.json').write_text(json.dumps(profile, indent=2) + '\n')
    print(a.output / 'profile.json')


if __name__ == '__main__':
    main()
