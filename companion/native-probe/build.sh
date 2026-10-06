#!/usr/bin/env bash
# Downstream owned probe; host clang plus LLVM's Mach-O linker, no Apple SDK.
set -euo pipefail
if [[ $# != 2 ]]; then echo "usage: $0 /absolute/ld64.lld /absolute/output-directory" >&2; exit 2; fi
linker=$(realpath -s "$1")
output=$(realpath -m "$2")
source_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
mkdir -p "$output"
clang --target=arm64-apple-ios14 -c "$source_dir/probe.S" -o "$output/probe.o"
"$linker" -arch arm64 -platform_version ios 14.0 14.0 -e _start -needed_library "$source_dir/libSystem.tbd" -no_uuid -adhoc_codesign -o "$output/inferno-probe" "$output/probe.o"
python3 - "$source_dir" "$linker" "$output" <<'PY'
import hashlib, json, pathlib, shutil, subprocess, sys
source, linker, output = map(pathlib.Path, sys.argv[1:])
paths = [source / 'probe.S', source / 'build.sh', source / 'libSystem.tbd', pathlib.Path(shutil.which('clang')).resolve(), linker.resolve(), output / 'inferno-probe']
data = {'files': {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}, 'clang': subprocess.check_output(['clang', '--version'], text=True), 'linker': subprocess.check_output([str(linker), '--version'], text=True), 'source_revision': subprocess.check_output(['git', '-C', str(source), 'rev-parse', 'HEAD'], text=True).strip(), 'signing': 'LLVM ad-hoc signature of owned code only; no Apple identity or signature'}
(output / 'build.json').write_text(json.dumps(data, indent=2) + '\n')
PY
