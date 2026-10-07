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
clocks. Boots37/38 each completed three Home/reopen cycles with the same original
process identity and retained counter1. Boot38 additionally launched a genuinely
new owned process after normal app-switcher dismissal and observed absence of the
old process. Boots39/40 completed the strict journey concurrently, then a shared
60-second resource observation and normal shutdown. Their combined average CPU
was64.57% of one host core; peak sampled PSS sum was10.76GiB. This is a measured
pair with an idle foreground fixture, not a maximum-capacity result. See
[OWNED_JOURNEY.md](OWNED_JOURNEY.md) for the repeatable operator workflow.
Boot41 then exposed a persistent display freeze after a genuine tap: both VNC
and QMP retained counter0 despite responsive lifecycle events. That attempt is
retained as a failure. Comparison42 completed the tracked strict/warm workflow
with read-only display diagnostics. Runs44 and47 reproduced the freeze with
bounded display traces: interrupts were acknowledged but drawing submissions
stopped. Healthy45/46 provide comparison traces. Run49 completed another strict
journey and captured twenty original-tool stackshots each of SpringBoard and
backboardd, establishing a healthy user-stack reference. The intermittent
freeze remains under investigation. Run53 extended the journey through original Clock
stopwatch measurements and back to the owned app. It also showed that periodic
QMP captures can lag guest animation when no VNC observer drives regular display
refresh. Headless VNC observation restored advancing stopwatch frames; this is
separate from the persistent no-submit failures44/47. Actual resource conditions
and their tracing/observer limits are retained in
`evidence/stopwatch-resources-53-actual/`. Run55 then validated the optional
`--headless-refresh-seconds 1..300` runner-owned observer through strict counter
0→1 and graceful early shutdown. Its actual coverage and separate resource use
are recorded; the option remains disabled by default. Run56 verified that default
creates no observer, then completed a fresh app process launch after a reviewed
App Switcher dismissal and an original process listing proving absence. Run57
verified natural observer expiry after60s, followed by a separately observed
strict counter0→1 journey and normal shutdown. Both final strict verification
and disk preservation passed. These observer checks do not resolve the earlier
persistent freeze.
Run62 reproduced the persistent freeze on the archived emulator and original
stage50 guest state: a genuine counter1 event left both VNC and QMP at0, even
through continuous observation and an ordinary Home transition. Drawing
submissions stopped while interrupt acknowledgments continued. The incomplete
journey and all seven disks are retained as a forensic failure. Runs63/64 reproduced the freeze on the same original state with diagnostic
caller tracing. Run64 observed the original interrupt handler with its ready bit
set, but subsequent drawing submissions stopped. Run65 then reproduced it on a verified sampling-enabled branch from the original
disk state and captured complete original-tool samples of backboardd and
SpringBoard during the freeze. The failed journey, frozen images, samples and
all disks are preserved. Original-image stack analysis places some failed-state
backboardd samples in SwapWait and its retry path. Run68 then established actual
coverage of two kernel addresses in a separate healthy Clock calibration:
pending and successful returns coexist with advancing frames. These snapshots
have no process/thread identity and cannot be paired as calls. We still need the
same bounded observation during a reproduced freeze; no rendering fix is claimed.

Runs69–72 completed the strict visual journey, and69 also passed three
Home/reopen/tap cycles ending at counter4. Runs71/72 executed the guarded
setup-to-counter sequence with actual receiver write intervals of10.25/10.24s.
Their source pins, raw logs, reviewed frames and normal disk preservation are
retained. They do not resolve the intermittent display freeze.

The first developer release targets already-built, unencrypted developer IPAs,
as selected by the user. Xcode-project building is deferred until a Mac is
available. The [release roadmap](RELEASE.md) separates execution proof from
remaining compatibility, setup and reliability work.

Manifest import, bounded recovery staging and app-bound launch helpers now exist.
The first imported fixture installed and launched in74, but its actual tap left
the display frozen at0. That failed interactive journey and original guest
samples are retained; the intermittent freeze remains unresolved. A separately
named resource-loading demo is being exercised through fresh installation and
the general launcher. General IPA compatibility is not yet claimed.

Broader reliability and active-workload measurements remain ongoing. See [BOOT.md](BOOT.md) for the image profile and headless runner,
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
