# Reviewed sparse dyld-cache patch application

This module carries a small plan into an isolated recovery ramdisk, then applies
it to a disposable root clone. It does not carry the 2 GiB cache in the ramdisk,
change code signatures, or sign Apple code. It uses an ad-hoc signature only for
our owned helper. Firmware, caches, original-byte sidecars, plans and build outputs
remain outside Git.

The upstream patch producer is [InfernoFSPatcher](https://git.chefkiss.dev/AppleHax/InfernoFSPatcher),
revision `3008aaaa0909824a71ee3040c9edc58703c250f5`, licensed AGPL-3.0-or-later.
The generator below consumes its `.InfernoOriginalBytes` sidecar and the two cache
copies; it does not embed or copy upstream implementation code.

`make-plan.py --original PATH --patched PATH --sidecar PATH --output PATH
--original-sha256 HASH --patched-sha256 HASH --patcher-revision REV` validates
sidecar old bytes, obtains replacement bytes from the patched copy, and streams
both entire files to prove every byte outside the records is identical. Both full
input hashes must match. It emits the plan and a provenance JSON sidecar.

The binary format is little endian: 8-byte `INFRPAT1` magic, uint64 expected file
size, uint32 record count, uint32 zero. Each record is uint64 offset, uint32 length,
uint32 zero, then length old bytes and length replacement bytes. Offsets must be
sorted and nonoverlapping. Limits are 65536 records, 4096 bytes per record, 16 MiB
plan size and 8 GiB cache size. Digest pairs are a separate fixed 64-byte sidecar.

For new reproducible builds, use `build-cache-helper.py --help`. Supply explicit
absolute `--clang`, `--linker`, and `--ldid` invocations with each tool's SHA256,
and a new external `--output` directory. The producer requires committed source,
checks source and tools before and after compilation, records actual command logs,
and reads back the owned helper's entitlement dictionary. It creates no guest
or cache patch. `companion/evidence/reproducible-cache-helper-build-1/` retains
an actual successful build; fresh guest application remains a separate milestone.

`build.sh LD64_LLD LDID OUTPUT_DIRECTORY` builds the SDK-free helper and records
source/tool/binary hashes. `prepare.py --help` lists required inputs; it delegates
the tested recovery cloning and launch job installation to an explicitly supplied
native-probe preparer, then installs the small plan and two full cache SHA256s,
verifies HFS readback and updates the profile's ramdisk hash. The plan hash is an
explicit preparation input.

The guest invocation requires `--disposable-root-copy`. The only target is
`/mnt1/System/Library/Caches/com.apple.dyld/dyld_shared_cache_arm64e`, after mounting
`/dev/disk0s1s1` on `/mnt1`. It validates the whole plan before mount, then exact
cache size, full original SHA256, and every original byte before any pwrite.
It checks every write, fsyncs, reads every replacement back, verifies unchanged
size and full patched SHA256, and normally unmounts. Only
`INFERNO_CACHE_RESULT status=0` after successful unmount is success. A failed
partial-write attempt is a failed disposable clone, never a usable output.

Whole-file hashing under TCG is intentionally bounded by a generous experiment
run duration (600 seconds for this cache), not treated as instantaneous. The helper
has no network operations, key extraction, or signing operations. Its SHA256
implementation was checked against the standard empty and `abc` vectors on the
host; actual guest hashes must also match independently calculated host hashes.

## Actual application evidence

`.local-build/reports/cache-patching-1/serial.log` records both full guest hashes:

- Original: `59fdf288034e947c39b087b7c405ed149de3fea9f8af4a5ae2611fa03d4081e1`.
- Patched: `af1001abe5b075afd337bf110562746c3e006e9d93951e163fc5daae062aeab8`.

All 45 records (180 replacement bytes) were validated before writes. The entire
2,052,489,216-byte file was hashed before and after, and byte readback passed.
Serial ends with `INFERNO_CACHE_UNMOUNT status=0` and
`INFERNO_CACHE_RESULT status=0`. The experiment used a copy of app-staging-1 root
and all auxiliary namespaces. After helper success, the runner was intentionally
interrupted to execute its finally-block QMP quit; quit was acknowledged. Its
`attempt_completed: false`/KeyboardInterrupt is the deliberate early runner
stop, not a helper failure or installed-OS boot claim. Stopped disk identities
are recorded in `cache-patching-1/stopped-disk-hashes.json`.

The durable generator independently reproduced the 1104-byte plan SHA256
`c20a73ee8aa777ea36595cf60fb1ed86b9fc4a3bad42645a34045536ab01b079`,
including a complete outside-record comparison. Local build, preparation, plan
and upstream provenance are under `~/.local/share/inferno/fs-patcher-modified/`.
