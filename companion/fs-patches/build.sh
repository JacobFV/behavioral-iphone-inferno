#!/usr/bin/env bash
set -euo pipefail
if [[ $# != 3 ]]; then echo 'usage: build.sh LD64_LLD LDID OUTPUT_DIRECTORY' >&2; exit 2; fi
linker=$(realpath -s "$1")
signer=$(realpath "$2")
output=$(realpath -m "$3")
source_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
mkdir -p "$output"
clang --target=arm64-apple-ios14 -ffreestanding -fno-stack-protector -fno-builtin -O2 -c "$source_dir/cache-patch.c" -o "$output/cache-patch.o"
"$linker" -arch arm64 -platform_version ios 14.0 14.0 -e _main -needed_library "$source_dir/libSystem.tbd" -no_uuid -adhoc_codesign -o "$output/inferno-cache-patch" "$output/cache-patch.o"
"$signer" -Cadhoc -S"$source_dir/entitlements.plist" "$output/inferno-cache-patch"
python3 - "$source_dir" "$linker" "$signer" "$output" <<'PY'
import pathlib,hashlib,json,subprocess,sys
source,linker,signer,output=map(pathlib.Path,sys.argv[1:])
files=[source/'cache-patch.c',source/'libSystem.tbd',source/'entitlements.plist',source/'build.sh',linker,signer,output/'inferno-cache-patch']
(output/'build.json').write_text(json.dumps({'files':{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in files},'revision':subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD'],text=True).strip(),'clang':subprocess.check_output(['clang','--version'],text=True),'signing':'Owned helper ad-hoc only; no Apple signature edits'},indent=2)+'\n')
PY
