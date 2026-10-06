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

The helper executes ordered `newfs_apfs -A` additions for Preboot (`role=b`),
xART (`role=x`, 10 MiB) and Hardware (`role=h`, 24 MiB) in `/dev/disk0s1`.
It never uses the destructive container-create `-C` switch. It discovers actual
volume identities by mounting existing device nodes read-only and querying names;
the System volume is recognized by its SystemVersion.plist and original firmware
path. It then mounts System read-only and Preboot writable, and copies the original
firmware subtree into `Preboot/<96 zero characters>/usr/standalone/firmware`.
The zero directory matches the existing direct-kernel no-ticket boot-manifest
hash; it is not a forged ticket. This phase does not create Data or seed user data.
Every subprocess argv and wait status is printed. Any failure stops the helper.
Only `INFERNO_PREP_COMPLETE` establishes completion, and raw logs must be reviewed.

The owned C code declares only the ABI it calls, with no SDK headers or copied
implementation. `copyfile` preserves data/metadata and symlinks recursively using
the guest implementation; it avoids a handcrafted dirent layout. ABI references:
[Darwin attr.h](https://github.com/apple-oss-distributions/xnu/blob/xnu-7195.141.2/bsd/sys/attr.h),
[copyfile.h](https://github.com/apple-oss-distributions/copyfile/blob/main/copyfile.h).
Role arguments were observed in an
[upstream actual restore log](https://github.com/ChefKissInc/Inferno/discussions/219).
