#!/usr/bin/env python3
"""Record build inputs/artifact identity; this is not an execution oracle."""
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys

root = Path(sys.argv[1]).resolve()
scripts = Path(__file__).resolve().parent
source = root / 'source'
binary = root / 'build/qemu-system-aarch64'

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def output(args):
    return subprocess.check_output(args, text=True).strip()

files = [scripts / name for name in ('build-linux.sh', 'bootstrap-linux.py',
          'linux-dependencies-arm64.json', 'build-tools-arm64.txt')]
files += [root / 'downloads/nettle-3.10.2.tar.gz']
record = {
    'schema': 'inferno.local-linux-build.v1',
    'purpose': 'build provenance only; no guest boot or firmware execution claim',
    'source_revision': output(['git', '-C', str(source), 'rev-parse', 'HEAD']),
    'source_diff': output(['git', '-C', str(source), 'diff', '--stat']),
    'mlib_revision': output(['git', '-C', str(source / 'util/mlib'), 'rev-parse', 'HEAD']),
    'host_machine': platform.machine(),
    'host_platform': platform.platform(),
    'python': platform.python_version(),
    'compiler': output(['cc', '--version']).splitlines()[0],
    'meson': output([str(root / 'venv/bin/meson'), '--version']),
    'ninja': output([str(root / 'venv/bin/ninja'), '--version']),
    'inputs': {str(p): sha(p) for p in files},
    'binary': {'path': str(binary), 'sha256': sha(binary), 'bytes': binary.stat().st_size},
    'system_dependencies': {},
}
for name in ('glib-2.0', 'pixman-1', 'zlib'):
    record['system_dependencies'][name] = output(['pkg-config', '--modversion', name])
for name in ('config-host.mak', 'config.status', 'meson-info/intro-buildoptions.json'):
    path = root / 'build' / name
    if path.is_file(): record['inputs'][str(path)] = sha(path)
for name in ('keycodemapdb',):
    path = source / 'subprojects' / name
    if (path / '.git').exists():
        record[name + '_revision'] = output(['git', '-C', str(path), 'rev-parse', 'HEAD'])
(root / 'build-manifest.json').write_text(json.dumps(record, indent=2) + '\n')
