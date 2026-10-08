# Rebuild the owned preparation helper

`build-prepare-helper.py` reproduces helper60's three compile/link/ad-hoc signing
commands with the current committed four preparation sources. It adds an actual
entitlement readback and records source/tool hashes and subprocess logs. It does
not change guest code, create a runtime descriptor, stage a disk or launch a VM.
It signs only the newly built owned helper with its existing entitlement plist.

Use a stable committed checkout and a new output directory outside Git:

```sh
python3 companion/native-probe/build-prepare-helper.py \
  --clang /absolute/clang --clang-sha256 CLANG_SHA256 \
  --linker /absolute/ld64.lld --linker-sha256 RESOLVED_LLD_SHA256 \
  --ldid /absolute/ldid --ldid-sha256 LDID_SHA256 \
  --output /external/NEW-helper
```

Tool hashes must come from your reviewed installed tool artifacts. Symlink
invocations are allowed and their resolved binaries are pinned; retain the
`ld64.lld` driver name. All commands have a120s host timeout and no retry.
`build.json` provides the strict `sources` and `outputs.inferno-prepare-root`
fields consumed by prepare-import. Only use it when INCOMPLETE/failure markers
are absent; errors retain the failed new directory. The broader legacy build.sh
keeps its existing format unchanged.

For a NEW runtime descriptor, use the resulting helper/build.json pins. Retain
the original profile/probe/cache/base provenance and all other required inputs;
this build does not supply or waive them. Never rewrite an existing session's
runtime or historical helper60 evidence. Subsequent host preparation and actual
recovery readback remain required. Byte equality with a historical helper, when
observed, is a reproducibility check rather than new guest execution evidence.
