#!/usr/bin/env python3
"""Clone a verified raw recovery ramdisk and add owned/nonmutating launch probes."""
import argparse
import hashlib
import json
import plistlib
import shutil
import subprocess
from pathlib import Path

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--profile', required=True, type=Path)
p.add_argument('--raw-ramdisk', required=True, type=Path)
p.add_argument('--probe', required=True, type=Path)
p.add_argument('--hfsplus', required=True, type=Path)
p.add_argument('--output', required=True, type=Path)
a = p.parse_args()
for required in (a.profile, a.raw_ramdisk, a.probe, a.hfsplus):
    if not required.is_file():
        p.error(f'missing input: {required}')
a.output.mkdir(parents=True, exist_ok=False)
sha = lambda f: hashlib.sha256(f.read_bytes()).hexdigest()
profile = json.loads(a.profile.read_text())
raw = a.output / 'ramdisk.raw'
shutil.copyfile(a.raw_ramdisk, raw)
log = []
def hfs(*args):
    result = subprocess.run([str(a.hfsplus), str(raw), *map(str, args)], capture_output=True, text=True, check=True)
    log.append({'args': list(map(str, args)), 'stdout': result.stdout, 'stderr': result.stderr})
hfs('add', a.probe, '/usr/bin/inferno-probe')
hfs('chmod', '755', '/usr/bin/inferno-probe')
for name, args in [('native', ['/usr/bin/inferno-probe']), ('asr-help', ['/usr/sbin/asr', '--help']), ('apfs-help', ['/sbin/newfs_apfs', '-h'])]:
    label = 'org.inferno.probe.' + name
    local = a.output / (label + '.plist')
    local.write_bytes(plistlib.dumps({'Label': label, 'ProgramArguments': args, 'RunAtLoad': True, 'StandardOutPath': '/dev/console', 'StandardErrorPath': '/dev/console', 'UserName': 'root'}))
    destination = '/System/Library/LaunchDaemons/' + local.name
    hfs('add', local, destination)
    hfs('chmod', '644', destination)
hfs('ls', '/System/Library/LaunchDaemons')
hfs('extract', '/usr/bin/inferno-probe', a.output / 'readback-probe')
assert sha(a.output / 'readback-probe') == sha(a.probe)
profile['ramdisk'] = {'path': str(raw.resolve()), 'size': raw.stat().st_size, 'sha256': sha(raw)}
profile['provenance']['preparation'] = 'Cloned decoded HFSX recovery ramdisk; added owned ad-hoc Mach-O and three diagnostic launchd plists. No original assets changed.'
(a.output / 'profile.json').write_text(json.dumps(profile, indent=2) + '\n')
(a.output / 'preparation.json').write_text(json.dumps({'source_profile': str(a.profile), 'source_raw_sha256': sha(a.raw_ramdisk), 'probe_sha256': sha(a.probe), 'hfsplus_sha256': sha(a.hfsplus), 'output_ramdisk_sha256': sha(raw), 'operations': log}, indent=2) + '\n')
print(a.output / 'profile.json')
