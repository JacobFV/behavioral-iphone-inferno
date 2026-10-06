#!/usr/bin/env bash
# Build only our observation helper; no SDK or Apple implementation inputs.
set -euo pipefail
if [[ $# != 2 ]]; then echo "usage: $0 /absolute/ld64.lld /absolute/output" >&2; exit 2; fi
linker=$(realpath -s "$1")
output=$(realpath -m "$2")
source_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
mkdir -p "$output"
clang --target=arm64-apple-ios14 -ffreestanding -fno-stack-protector -fno-builtin -O2 -Wall -Wextra -Werror -c "$source_dir/ioreg-touch.c" -o "$output/ioreg-touch.o"
"$linker" -arch arm64 -platform_version ios 14.0 14.0 -e _main -needed_library "$source_dir/libSystem.tbd" -needed_library "$source_dir/IOKit.tbd" -no_uuid -adhoc_codesign -o "$output/inferno-ioreg-touch" "$output/ioreg-touch.o"
python3 - "$source_dir" "$linker" "$output" <<'PY'
import hashlib,json,pathlib,shutil,subprocess,sys
source,linker,output=map(pathlib.Path,sys.argv[1:])
paths=[source/x for x in ('ioreg-touch.c','IOKit.tbd','libSystem.tbd','build-ioreg.sh')]+[pathlib.Path(shutil.which('clang')).resolve(),linker.resolve(),output/'inferno-ioreg-touch']
report={'source_revision':subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD'],text=True).strip(),'files':{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},'signing':'Own LLVM ad-hoc signature, no entitlements or Apple identity','status':'built only; guest execution not yet observed'}
(output/'build.json').write_text(json.dumps(report,indent=2)+'\n')
PY
