# Behavioral iPhone on Inferno

This local fork builds on ChefKiss Inferno instead of reimplementing UIKit and
Foundation. Upstream history and notices are preserved. The initial upstream pin
is recorded in upstream.json; the remote is named `upstream`. This checkout has
not been published to a GitHub account.

The objective is a reproducible Linux runner for real iOS app execution, with
headless control, screenshots, repeatable journeys and measured resource use.
The older clean-room effort is preserved in ../behavioral-iphone. Its fixtures,
strict image comparisons and dashboard may be reused as integration tools; its
synthetic references are not native iOS acceptance evidence.

## Quick commands

From this repository, run `./companion/run status` to inspect readiness,
`./companion/run check` for a fresh headless execution check, and
`./companion/run build` when committed source changes require rebuilding.
For the next coding session, start with [NEXT_SESSION.md](../NEXT_SESSION.md).

The 2026-10-06 execution reached installed iOS14 beta5, completed the ordinary
setup choices, and resumed to the original lock screen and SpringBoard Home.
Owned virtual-HID input opened original Clock and then the owned UIKit fixture.
Boot26 captured the owned app's counter at0 and, after one explicit tap, at1.
The original launch gate accepted its corrected System classification after a
normal restart; correcting our NSObject header fixed the actual startup crash.
Boots33 and34 completed the strict owned-app journey from the same frozen state:
actual lifecycle and tap records, reviewed counter0→1, both QMP captures and
normal emulator exit0. Boots35/36 also recorded original guest monotonic launch
clocks. Live37 completed three Home/reopen cycles with the same corroborated app
process and retained counter1. Whole-emulator resource samples are recorded;
broader reliability, fresh-process launch and density measurements remain active work. See [BOOT.md](BOOT.md) for the image profile and headless runner,
[USB.md](USB.md) for the isolated USB companion, and `evidence/` for raw execution.

## Initial milestones

1. Build the actual upstream aarch64 system emulator with Apple-device support.
2. Execute the firmware-free QMP smoke and retain the binary/source identity.
3. Prepare an explicitly documented iOS image profile outside Git, then establish
   a real boot, display and input path. Recovery-userland boot and a framebuffer
   capture now work; installed iOS reaches Hello and accepts ordinary gestures
   through an owned virtual touchscreen. Normal setup, first-unlock, Home, stock Clock and the owned visual counter journey are proven; actual app-event collection and strict before/after capture completion are proven.
4. Install one owned, unencrypted application and execute an end-to-end journey.
5. Measure cold/warm launch, memory, CPU, reliability and parallel density before
   claiming cheap runner economics. Add the existing visualization dashboard only
   after real backend captures are available.

`python3 companion/smoke.py --binary PATH` starts `-machine none -accel tcg -S`
with no display, guest image or CPU, talks QMP, verifies that the executable lists
`t8030`, and shuts it down. It reports control-plane results only; it does not
claim iOS boot or app compatibility. The working build instructions follow; local execution evidence is recorded in
PROGRESS.md.

## Build and run the control-plane check

The initial dependency lock targets Ubuntu24.04 ARM64, matching the current host.
It is not yet a universal distribution/x86 bootstrap. Existing system tools are
Python3 with venv, GCC/Make, m4, CMake, pkg-config, Git, curl, dpkg-deb and development
headers for GLib, Pixman, zlib and PNG. Additional locked packages are extracted
locally; Nettle3.10.2 is compiled locally. No sudo or system-wide installation is
used. Meson and Ninja wheels and downloaded packages have explicit hash checks.

From the repository root:

```sh
companion/build-linux.sh --build-root "$PWD/.local-build" --jobs 8
python3 companion/smoke.py --binary .local-build/build/qemu-system-aarch64
```

Build identity is recorded in `.local-build/build-manifest.json`; raw QMP results
and stderr go under `.local-build/reports/`. Neither report is an iOS acceptance
claim. The build enables TCG, Pixman/PNG, VNC, slirp, LZFSE, Nettle and GnuTLS and
uses no GTK/SDL window frontend. Retain the entire build root: the executable
uses local dependency paths and upstream branding resources, so it is not a
standalone redistributable binary. The smoke itself exposes only a temporary local
Unix socket and starts no VNC server.

## Source facts and limits

At the pinned source, t8030 defaults to 4 GiB guest RAM and an 828x1792 display.
It requires a device tree and kernel during initialization; unlike `none`, it
cannot be used for an image-free smoke. Its direct-kernel path invokes upstream
kernel patches, so future runs must not be called unmodified iOS. See
hw/arm/apple-silicon/t8030.c and hw/core/null-machine.c.

Inferno's iOS18.5 boot issue is marked done, but that is not a complete app or
Metal compatibility guarantee. Linux KVM support remains an open upstream issue.
No numerical throughput or cost claim has been verified in this fork.

- Source: https://github.com/ChefKissInc/Inferno
- KVM: https://github.com/ChefKissInc/Inferno/issues/87
- iOS18.5: https://github.com/ChefKissInc/Inferno/issues/241
- eShard UI work: https://www.eshard.com/blog/emulating-ios-14-with-qemu-part2

All original licenses remain in force. Companion additions are identified as
downstream AI-assisted work; the upstream README describes the upstream project.
