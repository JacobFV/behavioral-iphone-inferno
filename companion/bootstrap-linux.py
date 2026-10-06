#!/usr/bin/env python3
"""Extract verified development packages locally; never invoke package install."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import urllib.request

root = Path(sys.argv[1]).resolve()
lock = Path(__file__).with_name('linux-dependencies-arm64.json')
if subprocess.check_output(['dpkg', '--print-architecture'], text=True).strip() != 'arm64':
    raise SystemExit('This dependency lock is Ubuntu 24.04 arm64; create/review a host-specific lock for another host.')
archive = root / 'downloads'; archive.mkdir(parents=True, exist_ok=True)
prefix = root / 'packages'; prefix.mkdir(exist_ok=True)
for package in json.loads(lock.read_text())['packages']:
    output = archive / Path(package['Filename']).name
    if not output.exists():
        url = 'https://ports.ubuntu.com/ubuntu-ports/' + package['Filename']
        print('Downloading', url, flush=True)
        with urllib.request.urlopen(url, timeout=90) as response:
            output.write_bytes(response.read())
    if hashlib.sha256(output.read_bytes()).hexdigest() != package['SHA256']:
        raise SystemExit('Hash mismatch: ' + str(output))
    subprocess.run(['dpkg-deb', '-x', str(output), str(prefix)], check=True)
# Only relocate the locally extracted pkg-config files, never upstream source.
for pc in prefix.rglob('*.pc'):
    text = pc.read_text().replace('prefix=/usr', 'prefix=' + str(prefix / 'usr'))
    pc.write_text(text)
print('Local packages ready:', prefix, flush=True)
