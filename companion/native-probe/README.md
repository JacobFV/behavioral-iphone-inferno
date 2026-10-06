# Owned recovery native probe

This SDK-free arm64 Mach-O writes a deterministic marker using Darwin syscalls
and exits. An owned linker declaration requests the existing guest libSystem
for dyld bootstrap; no SDK headers or Apple binaries are copied. It is an execution checkpoint in patched iOS recovery userland,
not a UIKit app, installed iOS journey, or performance benchmark. LLVM generates
an ad-hoc signature for our code; it does not forge an Apple signature.

Build outside Git with the host clang and LLVM Mach-O linker:

```sh
companion/native-probe/build.sh /absolute/ld64.lld /absolute/probe-build
python3 companion/native-probe/prepare.py \
  --profile /absolute/verified-profile/profile.json \
  --raw-ramdisk /absolute/verified-profile/ramdisk-payload.raw \
  --probe /absolute/probe-build/inferno-probe \
  --hfsplus /absolute/hfsplus --output /absolute/fresh-probe-profile
python3 companion/boot.py --profile /absolute/fresh-probe-profile/profile.json \
  --seconds 150 --output /absolute/fresh-report
```

Preparation refuses an existing output directory, clones the decoded HFSX
ramdisk, adds our executable and three root launchd jobs, and verifies the
executable by extracting it again. The other two jobs only request usage from
`/usr/sbin/asr --help` and `/sbin/newfs_apfs -h`. They do not restore or format
anything. All stdout/stderr go to `/dev/console`. The original profile, ramdisk,
Apple tools and trustcache stay unchanged. The derived profile records the
changed ramdisk hash; preparation.json records transformations and tool hashes.

## Local HFSX writer

Ubuntu hfsplus 1.0.4 rejects this HFSX v5 ramdisk with `Neither Wrapper nor native
HFS+ volume header found`. The standalone HFS writer in
https://github.com/planetbeing/xpwn at revision
`20c32e5c12d1b22a9d55a59a0ff6267f539b77f4` reads/writes it. Only its HFS filesystem
sources and generic file helpers are compiled; none of its firmware, patching,
decryption or signing tools are built or run. Preserve its upstream license in
the external checkout. From that pinned external checkout:

```sh
gcc -O2 -fcommon -I includes hfs/*.c common/abstractfile.c common/base64.c \
  -lz -o /absolute/hfsplus
```

On Ubuntu 24.04 arm64, `apt download lld-18` followed by `dpkg-deb -x` into a
local directory supplies ld64.lld-18; the host already supplies libLLVM18.
No root privileges or system installation are needed. Keep downloaded packages,
all tools, firmware, cloned disks and reports outside Git.

## Loader findings

The first LC_MAIN executable had no library dependency and dyld rejected it with
`libdyld.dylib support not present for LC_MAIN`. A dependency-free UNIXTHREAD
variant was rejected by the kernel; retaining dyld produced `no valid entry
point`. The arm64e build of dyld does not implement UNIXTHREAD entry dispatch
([Apple dyld-750.6 source](https://github.com/apple-oss-distributions/dyld/blob/dyld-750.6/src/ImageLoaderMachO.cpp)).
The build therefore keeps LLVM's ordinary LC_MAIN and ad-hoc signing, and uses
`libSystem.tbd` solely to request the unmodified libSystem already in recovery.

## Executed checkpoint (2026-10-06)

The bounded headless run `.local-build/reports/native-probe-5/serial.log` contains
`INFERNO_OWNED_NATIVE_PROBE_V1: executed arm64 Darwin syscalls` at line 408.
This establishes our own code executing inside real iOS recovery userland.
The profile is `/home/brandonin/.local/share/inferno/native-probe/attempt-5/profile.json`.
Failed attempts remain in native-probe-1 through native-probe-4 report directories.
The guest newfs_apfs help job also prints its real command syntax. No usage output
was observed for the asr job, so its successful execution is not established.

## Disposable root preparation helper

`build.sh` also builds `inferno-prepare-root`. Preparation adds it only when
`--disk-helper /absolute/inferno-prepare-root` is explicitly supplied. That profile
must be booted with `--root-image` pointing to the original System-volume wrapper
and `--root-sha256` matching it: boot.py creates a separate disposable copy before
execution. Never use this helper with a non-disposable guest disk.

The helper executes `newfs_apfs -A` to add Preboot (`role=b`) in `/dev/disk0s1`.
The default adds only Preboot. Explicit `--disk-helper-roles` also adds xART and
Hardware using the entitled owned helper described below. The original attempt
without the parent entitlement returned exit77; the entitled run succeeded.
It never uses the destructive container-create `-C` switch. It discovers actual
volume identities by mounting existing device nodes read-only and querying names;
the System volume is recognized by its SystemVersion.plist and original firmware
path. It then mounts System read-only and Preboot writable, and copies the original
firmware subtree into `Preboot/<96 zero characters>/usr/standalone/firmware`.
The zero directory matches the existing direct-kernel no-ticket boot-manifest
hash; it is not a forged ticket. The default phase does not create xART or Hardware. Neither mode creates Data
or seeds user data.
Every subprocess argv and wait status is printed. Any failure stops the helper.
Only `INFERNO_PREP_COMPLETE` establishes completion, and raw logs must be reviewed.

The owned C code declares only the ABI it calls, with no SDK headers or copied
implementation. `copyfile` preserves data/metadata and symlinks recursively using
the guest implementation; it avoids a handcrafted dirent layout. ABI references:
[Darwin attr.h](https://github.com/apple-oss-distributions/xnu/blob/xnu-7195.141.2/bsd/sys/attr.h),
[copyfile.h](https://github.com/apple-oss-distributions/copyfile/blob/main/copyfile.h).
Role arguments were observed in an
[upstream actual restore log](https://github.com/ChefKissInc/Inferno/discussions/219).

Use `--ramdisk-boot` when executing this helper: ordinary recovery mode creates
a dummy NVMe device because firmware update is incomplete. Non-restore md0 boot
exposes the actual copied root container while still running recovery launchd.

## Executed Preboot preparation (2026-10-06)

The run below used source `bd3166ab28` and a fresh copy of the immutable original
System wrapper. Actual serial in `disk-preparation-6/serial.log` records Preboot
creation, discovering System as disk0s1s1 and Preboot as disk0s1s3, mounting System
read-only and Preboot writable, and `INFERNO_PREP_COMPLETE`. Both volumes were
cleanly unmounted before that marker. The runner then received SIGTERM and shut
QEMU down through QMP with exit0; its bounded-attempt flag is false because of
this deliberate early stop, not a claim of completed installed-iOS boot.

```sh
./companion/run boot \
  --binary "$PWD/.local-build/binaries/simulated-sep-tcg/qemu-system-aarch64" \
  --manifest "$PWD/.local-build/binaries/simulated-sep-tcg/build-manifest.json" \
  --profile /home/brandonin/.local/share/inferno/native-probe/helper-attempt-5/profile.json \
  --ramdisk-boot \
  --root-image /home/brandonin/.local/share/inferno/images/ios14b5/os-inspection/official-os-4k.raw \
  --root-sha256 93f97dae602a8fc844f0f88819d3fe358b1cf14ee5e193b0beb7009376032594 \
  --seconds 150 --output .local-build/reports/disk-preparation-6
```

The stopped output disk SHA256 is
`53af49ef3f3b04bd948def736fa81eb3100613c3b6bfbfbf5bee6082399fcc51` at
`.local-build/reports/disk-preparation-6/disks/root.raw`. Treat it as an immutable
base for a subsequent disk-boot experiment, letting boot.py copy it again.

A saved executable is not standalone: relocation changes its runtime data search
paths. Preserve `.local-build/binaries/share/` alongside this snapshot. It contains
`icons/hicolor/512x512/apps/CKQEMUBootSplash@2x.png` copied from upstream's
`source/ui/icons/CKQEMUBootSplash_512x512@2x.png`, and `qemu/keymaps/` copied from
upstream's `source/pc-bios/keymaps/`. Attempts3 and4 failed before guest execution
because the relocated icon and then VNC `en-us` keymap were missing. The original
local dependency libraries and build manifest must also remain available.

A separate read-only 7-Zip verification extracted the firmware tree from the
original official System image, the prepared System volume, and prepared Preboot.
All 19 files (2,578,484 bytes), relative paths and directory entries matched;
each file SHA256 matched across all three trees. Raw reader logs and the detailed
inventory are outside Git under `/home/brandonin/.local/share/inferno/native-probe/`
as `verification-original.log`, `verification-prepared.log`, and
`firmware-verification.json`. No prepared disk bytes were changed for inspection.

## Explicit xART parent entitlement experiment

The original newfs_apfs code checks its **parent's** `com.apple.private.apfs.xart`
entitlement before creating role256: read-only disassembly shows `getppid()`,
`csops(parent, CS_OPS_ENTITLEMENTS_BLOB, ...)`, then that dictionary key. The first
helper had no entitlements. This explains its userland exit77 independently of
any later encryption or kernel restriction; successful role creation still
requires actual execution evidence.

Pass a third absolute `ldid` path to `build.sh` to sign our owned helper with its
explicit `entitlements.plist`, and pass `--disk-helper-roles` to `prepare.py` to
request xART+Hardware after Preboot. No Apple executable is modified. The signer
uses ad-hoc mode, no identity, certificate or private key. The build manifest
records signer and entitlement hashes, and the extracted entitlement blob is
retained beside the binary. The marker itself remains LLVM ad-hoc signed.

Local signer source: https://github.com/ProcursusTeam/ldid revision
`af86971ae72ec3ed3d0a699107c4e882324c941b`. Its original license remains in the
external checkout. Build it locally with libplist and OpenSSL development packages
extracted with `apt download`/`dpkg-deb -x`; no system installation is necessary.
The exact local build output is `native-probe/ldid-build.log` outside Git.


## Executed entitled role preparation

Source `99bd636c95`, built under `helper-build-6/` with the pinned local ldid,
produced `helper-attempt-6/profile.json` using `--disk-helper-roles`. Actual run
`.local-build/reports/disk-preparation-8/serial.log` shows all three newfs commands
return status0, then independently mounted names System on disk0s1s1, Preboot on
s3, xART on s4, and Hardware on s5. Firmware copy and clean unmounts completed.
The original exit77 was the parent entitlement check, not an observed encryption
restriction. No Apple binary was changed to enable these operations.

After QMP shutdown and emulator exit0, the prepared disk hash was
`8103442bd0bf6f4e1aca44c203ee4c0793c87b740dd9395a399e08b604679afc` at
`.local-build/reports/disk-preparation-8/disks/root.raw`. Full signer source,
compiler, downloaded-package, binary and build-log hashes are outside Git in
`/home/brandonin/.local/share/inferno/native-probe/signer-build.json`.

The separate `--recovery-preserve-disk` mode test in preparation7 still exposed
only a dummy NVMe device despite `nand-enable-reformat=0`; it performed no helper
writes. The successful full-role run used the proven `--ramdisk-boot` mode.

## Original gigalocker initialization

The next disk boot mounted xART and Preboot but stopped at `data-protection`
because the host-UUID `.gl` file was absent. Original recovery seputil has an
explicit `--gigalocker-init` operation: it uses `/mnt7`, creates a missing file
through its own implementation, and invokes the SEP user client. The boot alias
`init_data_protection` instead uses `/private/xarts` and requires an existing file.
No blob is fabricated by the helper.

`prepare.py --disk-helper-existing --disk-helper-gigalocker` uses already prepared
volumes, mounts discovered xART on `/mnt7`, executes the original seputil init operation, syncs, and unmounts. Use only a disposable copy of
the prepared root as always. `INFERNO_GIGALOCKER_COMPLETE` requires the original init
call and clean unmount to succeed; absence or errors must remain explicit.

Explicit disk-helper profiles move the cloned ramdisk's
`com.apple.restored_external.plist` job outside LaunchDaemons into `/usr/share/`. Disk preparation does not request a restore
transaction, and that daemon otherwise shuts the guest down after its 120-second
host-wait timeout. The original daemon binary and original recovery profile stay
unchanged; the preparation operation log records the moved plist. Ordinary
marker profiles continue to run the original recovery job.

The initial attempts9 and10 returned0 from original gigalocker initialization but
hung in the separate seputil shutdown utility. The enabled guest-errors trace had
no SEP or XART opcode during that wait. They do not establish clean completion.
The helper therefore tests initialization followed by sync and normal unmount;
it does not claim the separate shutdown utility succeeded.

`--disk-helper-data` adds empty Data and Update role volumes, copies each original
System `private/var` child into the Data root with metadata, and prepares Hardware's
`FactoryData/System/Library/Caches/com.apple.factorydata` directory. It reports
Darwin statfs available bytes before and after the Data seed. This operation is
explicit and only intended for a new disposable copy without those volumes.
A successful compile is not proof of successful guest seeding; require the
`INFERNO_DATA_COMPLETE` marker plus reviewed tool and filesystem logs.

Preparation11 failed before helper execution after the old HFS writer deleted
the restore plist: the kernel reported an HFS attributes-node error and launchd
exec errno8, although extracted launchd SHA256 remained unchanged. Preparation
now moves the job catalog entry without deleting its file/attribute records.

Preparation12 executed the original gigalocker initializer successfully and then
cleanly unmounted xART. Its raw serial includes the original tool's initialization
message, status0, APFS unmount completion, and `INFERNO_GIGALOCKER_COMPLETE`.
The relocated restore plist profile also passed an independent 7-Zip archive test
of all 775 files. This establishes initialization and normal unmount; it does not
retroactively establish success for the hanging shutdown calls in attempts9/10.

## Executed Data and Update seed

Preparation13 used source `8a075ed69f` and a disposable copy of the clean
gigalocker-initialized preparation12 disk. Original newfs returned0 for Data
(disk0s1s2) and Update (disk0s1s6). The helper copied the original var children into
Data, preserved root metadata, prepared Hardware's factory-data path, synced and
cleanly unmounted all volumes. Actual serial records `INFERNO_DATA_COMPLETE` and
`INFERNO_PREP_COMPLETE`. Guest statfs available bytes changed from 412,479,488 to
260,640,768. These are preparation observations, not app-runner capacity claims.

## Original SEP payload experiment

Direct-root4 found and initialized the gigalocker, then failed because the loader
could not open `Preboot/<96 zeros>/usr/standalone/firmware/sep-firmware.img4`.
`prepare.py --sep-payload FILE --sep-sha256 HASH` explicitly adds a hash-checked
payload to the cloned ramdisk and asks the owned helper to copy it byte-for-byte
to that loader path on a disposable Preboot volume. This is only file staging;
a completed copy does not prove loader format acceptance or SEP startup.

The first payload is the untouched `Firmware/all_flash/sep-firmware.n104.RELEASE.im4p`
from the official 18A5351d IPSW, 7,783,790 bytes, SHA256
`76587673e56bbb89e178a015ebbe20fee29f841d07fa6f6cce0e9dad6800dfbe`.
Its SHA384 matches the n104ap Research Developer Erase Install SEP BuildManifest
entry. Extraction provenance is in external `native-probe/sep-original.json`.
No decryption, ticket, Apple signature, payload edit or format wrapper is involved
in this first test; it retains IM4P bytes despite the loader-required filename.

Independent host verification found that 12,465 seeded compressed Data files
extract as zero bytes with 7-Zip despite nonzero original System files. The seed
is therefore not yet byte-validated. `--disk-helper-verify-data` performs a
read-only guest size and streaming byte comparison of the identified Measure
localization sample, distinguishing a host-reader issue from a guest-visible
copy problem before choosing a repair. Generated profile provenance now records
the actual helper flags, moved restore job and optional unchanged SEP payload.

The guest sample read in disk-preparation-15 returned 3,286 bytes on each side
and exact equality. The verifier now traverses the entire original var tree and
Data, checks regular-file bytes, modes and ownership, symlink targets and extra
destination paths. Both volumes are mounted read-only. Its Darwin stat ABI is
declared from xnu-7195.141.2/bsd/sys/stat.h, with a 144-byte compile-time check.
A nonzero mismatch count fails preparation after clean volume unmounts.

Direct-root-5 accepted the staged original IM4P and activated the simulated SEP
endpoints. It passed phase-two mounts and FIPS checks, then stopped at the missing
Data keybag. This does not demonstrate execution of real SEP firmware or a UIKit
app. The next preparation step uses the original MobileKeyBag implementation.

`--disk-helper-keybag` is an explicit disposable-volume experiment. It mounts
existing xART/Data writable and Preboot read-only, invokes the original
`seputil --gigalocker-init` and `seputil --wait --load` using the staged original
payload, then calls `MKBKeyBagCreateSystem(NULL, "/mnt2")` from the original
MobileKeyBag framework. The ABI and arguments are observed in the original
restored_external and framework, which creates its own keybags directory and
atomic keybag file. The owned code neither constructs nor edits keybag bytes.
It logs the API result and output size, then syncs and unmounts. A returned
existing-bag status (-4) is accepted only when a nonempty keybag is present.

The first keybag invocation (run18) loaded SEP successfully, created a 223-byte
file, but returned -1 after a kernel denial for AppleEffaceableStorageUserClient.
That failed run is not treated as completed initialization. The next owned
ad-hoc signature adds only that observed IOKit user-client class entitlement.
After SEP activation the original gigalocker shutdown command is needed before
unmount; this differs from the pre-bootstrap hang in the earlier init-only run.
