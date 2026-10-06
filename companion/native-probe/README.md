# Owned recovery native probe

This SDK-free arm64 Mach-O writes a deterministic marker using Darwin syscalls
and exits. It is an execution checkpoint in patched iOS recovery userland,
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
