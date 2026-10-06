# Bounded APFS growth experiment

`grow-gpt4k.py` makes a new 32 GiB disposable copy of the verified 4 KiB GPT
wrapper. It checks both source GPT header and partition-table CRCs, retains disk
and partition GUIDs and the partition start, expands the partition end, relocates
the backup GPT, and verifies the original APFS extent's SHA256 is unchanged.
It does not resize APFS or modify APFS metadata. The sidecar records that explicitly.

The separately owned `../native-probe/grow-container.c` then requests growth using
the recovery image's original APFS framework. It requires the explicit
`--disposable-root-copy` argument, mounts the original System volume read-only to
record space and two file fingerprints, unmounts it, calls the API, records its
numeric return, mounts read-only again, checks increased capacity and identical
file bytes/length fingerprints, and unmounts before returning. Fingerprints are
FNV-1a consistency checks, not cryptographic hashes; host verification uses SHA256.
The runner must finish before host inspection of the resulting disk.

## ABI evidence

The original iOS 14 beta 5 recovery APFS framework SHA256 is
`61d8b7be3c92fb06f32a77b8af62828b38361e3473a54e2f87c45338e0030159`.
Its exported `APFSContainerResize` at VM address `0x3635c` sets x2 to zero and
branches directly to `APFSContainerResizeEx` at `0x36364`. The latter preserves
x0 as the device C string and x1 as the requested 64-bit size, opens the container
IOKit user client, and sends the request through method 2. The helper uses only
`int APFSContainerResize(const char *device, unsigned long long bytes)`;
it makes no assumption about the optional ResizeEx output pointer.

The SDK-free owned helper uses the same linking convention as native-probe, plus
libSystem exports `dlopen`, `dlsym`, and `dlerror`. Its own ad-hoc signature grants
`com.apple.private.security.disk-device-access` and
`com.apple.security.iokit-user-client-class = [AppleAPFSUserClient]`, both observed
in the original newfs_apfs entitlements. This signs only our code and does not
fabricate an Apple signature. No Apple binaries are tracked or patched.

## Local experiment inputs

The immutable original wrapper SHA256 is
`93f97dae602a8fc844f0f88819d3fe358b1cf14ee5e193b0beb7009376032594`.
The GPT-expanded image SHA256 is
`e4805e577ffad6637a3ff5ef29740aefbe45c790a4ece414f3a324109c5a22f4`.
Its partition spans 4096-byte LBAs 256 through 8388602, or 34,358,669,312 bytes.
The original APFS extent SHA256 remains
`54f0ea7d88b76756b43263eaf40cd5580aaf8871c7e15218822152e73fede44f`.

Build and preparation records reside outside Git at
`~/.local/share/inferno/native-probe/grow-build-1/build.json` and
`~/.local/share/inferno/native-probe/grow-attempt-1/preparation.json`.
The bounded headless guest run uses `.local-build/reports/container-growth-1/`.

## Executed result

The 100-second `container-growth-1` run completed with QMP quit acknowledged.
Actual serial lines 426–535 show readonly mount, clean unmount, kernel
`nx_resize` growth from 1,878,803 to 8,388,347 blocks, API return 0, readonly
remount, identical fingerprints, and a second clean unmount. Available blocks
increased from 110,070 to 6,606,346. The System volume was unmounted before QMP quit.
This proves container growth, not installed iOS boot or app execution.
