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
clang --target=arm64-apple-ios14 -ffreestanding -fno-stack-protector -fno-builtin -O2 -Wall -Wextra -Werror -DIOREG_TOUCH_LIBRARY -c "$source_dir/ioreg-touch.c" -o "$output/ioreg-touch.o"
clang --target=arm64-apple-ios14 -ffreestanding -fno-stack-protector -fno-builtin -O2 -Wall -Wextra -Werror -c "$source_dir/app-event-relay.c" -o "$output/app-event-relay.o"
clang --target=arm64-apple-ios14 -ffreestanding -fno-stack-protector -fno-builtin -O2 -Wall -Wextra -Werror -c "$source_dir/app-event-proc.c" -o "$output/app-event-proc.o"
clang --target=arm64-apple-ios14 -ffreestanding -fno-stack-protector -fno-builtin -O2 -c "$source_dir/readiness.c" -o "$output/readiness.o"
"$linker" -arch arm64 -platform_version ios 14.0 14.0 -e _main -needed_library "$source_dir/libSystem.tbd" -no_uuid -adhoc_codesign -needed_library "$source_dir/IOKit.tbd" -o "$output/inferno-readiness" "$output/readiness.o" "$output/ioreg-touch.o" "$output/app-event-relay.o" "$output/app-event-proc.o"
clang --target=arm64-apple-ios14 -ffreestanding -fno-stack-protector -fno-builtin -O2 -c "$source_dir/unlock-empty.c" -o "$output/unlock-empty.o"
"$linker" -arch arm64 -platform_version ios 14.0 14.0 -e _main -needed_library "$source_dir/libSystem.tbd" -no_uuid -adhoc_codesign -o "$output/inferno-unlock-empty" "$output/unlock-empty.o"
clang --target=arm64-apple-ios14 -ffreestanding -fno-stack-protector -fno-builtin -O2 -Wall -Wextra -Werror -c "$source_dir/hid-input.c" -o "$output/hid-input.o"
clang --target=arm64-apple-ios14 -ffreestanding -fno-stack-protector -fno-builtin -O2 -Wall -Wextra -Werror -c "$source_dir/hid-user-device.c" -o "$output/hid-user-device.o"
"$linker" -arch arm64 -platform_version ios 14.0 14.0 -e _main -needed_library "$source_dir/libSystem.tbd" -no_uuid -adhoc_codesign -o "$output/inferno-hid-input" "$output/hid-input.o" "$output/hid-user-device.o"
if [[ $# == 3 ]]; then
    "$3" -Cadhoc -S"$source_dir/hid-entitlements.plist" "$output/inferno-hid-input"
    "$3" -e "$output/inferno-hid-input" > "$output/hid-helper-entitlements.plist"
    "$3" -Cadhoc -S"$source_dir/entitlements.plist" "$output/inferno-prepare-root"
    "$3" -e "$output/inferno-prepare-root" > "$output/helper-entitlements.plist"
    "$3" -Cadhoc -S"$source_dir/unlock-entitlements.plist" "$output/inferno-unlock-empty"
    "$3" -e "$output/inferno-unlock-empty" > "$output/unlock-helper-entitlements.plist"
fi
python3 - "$source_dir" "$linker" "$output" "${3:-}" <<'PY'
import hashlib, json, pathlib, shutil, subprocess, sys
source, linker, output = map(pathlib.Path, sys.argv[1:4])
paths = [source.parent / 'app-probe' / 'UIKitNarrow.h', source.parent / 'app-probe' / 'stubs' / 'Foundation.tbd', source.parent / 'app-probe' / 'stubs' / 'CoreServices.tbd', source.parent / 'app-probe' / 'stubs' / 'libobjc.tbd', source / 'app-event-proc.c', source / 'app-event-relay.c', source.parent / 'app-probe' / 'EventRecord.h', source / 'hid-input.c', source / 'hid-input.h', source / 'hid-user-device.c', source / 'hid-entitlements.plist', output / 'inferno-hid-input', source / 'ioreg-touch.c', source / 'IOKit.tbd', source / 'unlock-entitlements.plist', source / 'unlock-empty.c', output / 'inferno-unlock-empty', source / 'readiness.c', output / 'inferno-readiness', source / 'probe.S', source / 'build.sh', source / 'libSystem.tbd', source / 'prepare-root.c', source / 'entitlements.plist', pathlib.Path(shutil.which('clang')).resolve(), linker.resolve(), output / 'inferno-probe', output / 'inferno-prepare-root']
if sys.argv[4]: paths += [pathlib.Path(sys.argv[4]).resolve(), output / 'helper-entitlements.plist', output / 'unlock-helper-entitlements.plist', output / 'hid-helper-entitlements.plist']
data = {'helper_entitlements': bool(sys.argv[4]), 'files': {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}, 'clang': subprocess.check_output(['clang', '--version'], text=True), 'linker': subprocess.check_output([str(linker), '--version'], text=True), 'source_revision': subprocess.check_output(['git', '-C', str(source), 'rev-parse', 'HEAD'], text=True).strip(), 'signing': 'Owned code only: LLVM ad-hoc marker; preparation helper additionally ldid ad-hoc with its explicit preparation entitlements, unlock helper with only com.apple.keystore.device when requested; HID helper with developer virtual-device entitlement and explicit IOHIDResourceDeviceUserClient class permission; no Apple identity/certificate/signature'}
(output / 'build.json').write_text(json.dumps(data, indent=2) + '\n')
PY
