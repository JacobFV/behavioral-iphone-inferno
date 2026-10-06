#!/usr/bin/env bash
# Downstream owned probe; host clang plus LLVM's Mach-O linker, no Apple SDK.
set -euo pipefail
if [[ $# != 2 && $# != 3 ]]; then echo "usage: $0 /absolute/ld64.lld /absolute/output-directory [absolute/ldid]" >&2; exit 2; fi
linker=$(realpath -s "$1")
output=$(realpath -m "$2")
source_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
mkdir -p "$output"
clang --target=arm64-apple-ios14 -c "$source_dir/probe.S" -o "$output/probe.o"
"$linker" -arch arm64 -platform_version ios 14.0 14.0 -e _start -needed_library "$source_dir/libSystem.tbd" -no_uuid -adhoc_codesign -o "$output/inferno-probe" "$output/probe.o"
clang --target=arm64-apple-ios14 -ffreestanding -fno-stack-protector -fno-builtin -O2 -c "$source_dir/prepare-root.c" -o "$output/prepare-root.o"
"$linker" -arch arm64 -platform_version ios 14.0 14.0 -e _main -needed_library "$source_dir/libSystem.tbd" -no_uuid -adhoc_codesign -o "$output/inferno-prepare-root" "$output/prepare-root.o"
clang --target=arm64-apple-ios14 -ffreestanding -fno-stack-protector -fno-builtin -O2 -c "$source_dir/readiness.c" -o "$output/readiness.o"
"$linker" -arch arm64 -platform_version ios 14.0 14.0 -e _main -needed_library "$source_dir/libSystem.tbd" -no_uuid -adhoc_codesign -o "$output/inferno-readiness" "$output/readiness.o"
if [[ $# == 3 ]]; then
    "$3" -Cadhoc -S"$source_dir/entitlements.plist" "$output/inferno-prepare-root"
    "$3" -e "$output/inferno-prepare-root" > "$output/helper-entitlements.plist"
fi
python3 - "$source_dir" "$linker" "$output" "${3:-}" <<'PY'
import hashlib, json, pathlib, shutil, subprocess, sys
source, linker, output = map(pathlib.Path, sys.argv[1:4])
paths = [source / 'readiness.c', output / 'inferno-readiness', source / 'probe.S', source / 'build.sh', source / 'libSystem.tbd', source / 'prepare-root.c', source / 'entitlements.plist', pathlib.Path(shutil.which('clang')).resolve(), linker.resolve(), output / 'inferno-probe', output / 'inferno-prepare-root']
if sys.argv[4]: paths += [pathlib.Path(sys.argv[4]).resolve(), output / 'helper-entitlements.plist']
data = {'helper_entitlements': bool(sys.argv[4]), 'files': {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}, 'clang': subprocess.check_output(['clang', '--version'], text=True), 'linker': subprocess.check_output([str(linker), '--version'], text=True), 'source_revision': subprocess.check_output(['git', '-C', str(source), 'rev-parse', 'HEAD'], text=True).strip(), 'signing': 'Owned code only: LLVM ad-hoc marker; helper additionally ldid ad-hoc with explicit xart entitlement when requested; no Apple identity/certificate/signature'}
(output / 'build.json').write_text(json.dumps(data, indent=2) + '\n')
PY
