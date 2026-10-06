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

Host 7-Zip extraction from the stopped grown container independently matched
SHA256 for SystemVersion.plist (620 bytes,
`2ca623c3d0866ae86a58f6836d9184245295a1517bc0f6456de94ef3a1d55f5b`)
and sbin/launchd (400400 bytes,
`50307ff547f84a8c5e03b51fcc6b9be31cea876b39bb829d0dd6e42aa5dd4598`).
The final grown disk SHA256 is
`298fe787029085dbbdaf30d066a115f5575aed05dc5a97a73fd5f5b6b0364d00`;
local verification details are in the run's `growth-verification.json`.

## Prepared-volume follow-up

A second independent experiment starts with the stopped `disk-preparation-14`
root, SHA256 `39c82acf4ca222d7bfcab23ec064067bebc88537497b8459d600a30b394d040e`,
which contains System, Data, Preboot, xART, Hardware and Update plus the gigalocker
and untouched SEP IM4P. Growth preserves existing volume contents; it does not
validate or fix the separately investigated compressed Data seed issue.
The expanded GPT wrapper is `prepared-14-32g.raw` outside Git, SHA256
`c02eb9352b9c40cd415c7c58f2ae30c05ffd698b7f96960d1a6469bad568e72c`.
The same owned helper and prepared recovery profile run in
`.local-build/reports/container-growth-2/`, on another disposable copy.

The second guest also returned API status 0, grew the container from 1,878,803
to 8,388,347 blocks, preserved both System file fingerprints, and cleanly
unmounted. System statfs reports 8,379,643 total and 6,557,917 available blocks;
this is smaller than the container total because other prepared roles reserve
space. Growth does not require creating the prepared volumes again.

The stopped prepared grown disk is `container-growth-2/disks/root.raw`, SHA256
`ad7f097b696dd3f12a0409fcd4da659a2e18ab1449c66bef9c11f733c1549ae5`.
QMP acknowledged quit. Host extraction independently matched all four baseline
files: SystemVersion.plist, launchd, the entire 6 MiB gigalocker
(SHA256 `b69dae56a14d1a8314ed40664c4033ea0a550eea2673e04df42a66ac6b9faf2c`),
and the entire original SEP IM4P
(SHA256 `76587673e56bbb89e178a015ebbe20fee29f841d07fa6f6cce0e9dad6800dfbe`).
The run's `growth-verification.json` records the extraction hashes.
