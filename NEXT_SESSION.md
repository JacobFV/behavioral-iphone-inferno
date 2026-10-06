# Start the next session here

Working directory: `/home/brandonin/Documents/behavioral-iphone-inferno`

Suggested opening instruction:

> Read AGENTS.md, PROGRESS.md and NEXT_SESSION.md. Continue this Inferno fork
> toward a real headless iOS boot and one owned app journey. Use parallel workers
> for independent tasks, commit progress, and keep working across status questions.
> Prefer integrated execution over adding routine unit tests. Never use my main
> display. Do not resume the archived framework reimplementation.

## What is ready

- Local fork of ChefKiss Inferno; upstream remote, branch companion/linux-runner.
  There is no GitHub-hosted fork or origin remote yet.
- Actual aarch64 emulator built on this Ubuntu24.04 ARM64 host.
- Local pinned dependencies/toolchain under `.local-build`; no sudo required.
- Minimal upstream integration changes link LZFSE, explicitly select simulated
  SEP without data encryption, and allow an explicit recovery NAND argument.
  Default upstream behavior is preserved; source/flags are in each build manifest.
- Independent QMP check passed, including real t8030 machine enumeration.
- Real iOS 14.0 beta 5 recovery boot now works with simulated SEP: kernel,
  `md0`, launchd, restored_external waiting for host, 828x1792 recovery framebuffer.
  This is not installed iOS/SpringBoard or an app journey. See PROGRESS.md and
  committed `companion/evidence/recovery-ramdisk*` raw evidence.
- Previous project and backup: `../behavioral-iphone` and
  `../behavioral-iphone-handoff.bundle`. Its workers/services are stopped.

Run from this directory:

```sh
./companion/run status
./companion/run check
./companion/run boot --profile /home/brandonin/.local/share/inferno/images/ios14b5/verified-profile/profile.json --seconds 120
```

Rebuild only when source/build inputs change:

```sh
./companion/run build --jobs 8 --simulated-sep
```

The build intentionally uses committed source. Commit source changes before
rebuilding. It preserves a detached source checkout and all dependencies beneath
`.local-build`, with no dependency on the previous session's /tmp worktrees. Keep
that directory together: the binary references local libraries/resources.

## Current execution boundary

Keep working; no handoff or missing user input. Full-system SpringBoard/backboardd
processes now execute and frames show actual Apple boot/migration progress after
pinned upstream software-rendering patches. This is not yet visible SpringBoard
or an owned UIKit app. Full guest cache hashes and raw boot logs are committed.

Current long run is `.local-build/reports/app-boot-3` (1800s, started about02:07
local), preserving stopped app-boot-2 migration state. Near its planned boundary,
reviewed frame58 shows Apple migration progress, not setup/home UI. Preserve the
stopped root and all six auxiliary namespaces, export the latest migration stack,
and determine whether the next boot resumes work or restarts migration.

Independent `.local-build/reports/app-boot-4` started about02:31 local, with
stage26 System launcher and exactly five upstream-documented unsupported services
disabled. Its owned readiness job and SpringBoard/backboardd run, but no launcher
marker or launcher process appeared in early snapshots. Investigate direct mobile
launchd context (including console stdio setup); a root wrapper dropping to mobile
has already executed the exact System launcher bytes successfully. Data execution
returned EPERM for both root/mobile despite successful header reads. Raw evidence
is in `companion/evidence/app-exec-matrix*`. Do not infer the underlying policy or
claim app execution from this location comparison.

The app job loads from merged `/System/Library/xpc/launchd.plist` through the
original `launchd_unsecure_cache=1` mode (`--launchd-unsecure-cache`). Signatures
remain unchanged. Linux USB run9 is headless KVM/EHCI with loopback SSH22325;
full-system lockdown responds with version14.0/build18A5351d, while starting the
syslog service returns PASSWORD_PROTECTED. No syslog stream was obtained.

Native postboot report export and UUID-matched symbolication show LaunchServices
seeding waited on active installd bundle-metadata parsing, not a proven deadlock.
Boot3 advanced to SystemAppMigrator. `companion/vnc-control.py` captures the live
private Unix VNC socket and can inject bounded pointer events without host windows;
capture is proven, actual touch response remains unproven. Latest source/evidence
and worker ownership are in PROGRESS.md and companion/app-probe/native-probe
READMEs. Continue toward a reviewed app screenshot plus actual tap/count change.

## Next concrete work

The initial firmware/profile/recovery milestone below has now executed. Continue
with the isolated Linux USB companion and a joint USB enumeration run; see
companion/USB.md and the latest PROGRESS.md entries. `companion/run boot` accepts
`--usb-socket /absolute/private/usb.sock` for a running companion. Full installed
disk boot still needs an evidence-backed path that obeys the no-forged-signatures
rule; do not silently follow upstream's ticket-forging restore instructions.
No user input is needed for repeating the proven recovery run.

1. Read the pinned Inferno setup documentation and the actual t8030 initialization
   in `hw/arm/apple-silicon/t8030.c`. Determine one supported image/OS/device
   combination and its complete input provenance. Do not equate version branches
   in source with proven boot/app support.
2. The official Apple IPSW and verified kernel/DTB/trustcache/ramdisk profile are
   now outside Git in `/home/brandonin/.local/share/inferno/images/ios14b5/`.
   `companion/run prepare` reproduces extraction and manifest/hash verification.
   The user has a MacBook Air with limited memory available if preparation
   needs macOS; prefer Linux work where feasible. Ask for only genuinely missing
   inputs after identifying a concrete path.
3. Build a headless boot profile with isolated writable disk state, serial logs,
   QMP and local-only VNC. Prove boot/display/input through actual execution.
   t8030 defaults to 4GiB guest RAM; CPU/KVM compatibility must be measured.
4. Run one owned, unencrypted app and capture a real interaction journey before
   adding fleet orchestration or importing the old dashboard.
5. Measure real boot/app memory, latency, reliability and parallel density.
   The image-free QMP check provides no iOS performance or compatibility evidence.

## Important source facts

- `-machine none -accel tcg -S` is our image-free control-plane check. It creates
  no guest CPU and proves no iOS execution.
- t8030 initialization requires DTB and kernel; additional trustcache, disk,
  ramdisk/ticket/SEP inputs depend on the selected upstream boot path.
- Upstream direct-kernel startup invokes kernel patches. Do not call future
  runs unmodified iOS or treat them as native-device reference captures.
- Linux companion KVM acceleration executed and was verified by QMP. iOS uses
  TCG; iOS KVM and Metal/app compatibility remain unmeasured.
- Current bootstrap is locked for Ubuntu24.04 ARM64. x86/Linux or another OS
  requires a reviewed host-specific dependency setup.
- Default upstream data encryption rejects simulated SEP. The current working
  build explicitly uses `--simulated-sep`; an ordinary build without this flag
  restores upstream's encrypted mode. Original binary/manifest are retained in
  `.local-build/binaries/emulated-sep/`.

## User preferences that must persist

Keep implementation moving across status questions. Use subagents when work can
be divided cleanly. Commit as you go and document actual outcomes. Avoid routine
unit-test proliferation; prioritize complete build/boot/app journeys. All UI work
must stay off the user's main display. Continue active execution; do not turn these continuity notes into a pause or
handoff unless the user requests one.
