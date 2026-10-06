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

Keep working; no handoff or missing user input. Real full-system SpringBoard and
backboardd processes execute, and reviewed frames show Apple migration progress.
Visible setup/home UI, owned UIKit execution and an actual tap/count journey are
still unproven. Do not return to firmware acquisition or the archived framework
implementation: firmware, original System/Data preparation, keybag creation,
software-renderer cache patching and full-system launchd execution are established.

At03:17 local, app-boot-6 has been stopped normally with preserved evidence. It uses advanced stopped
app-boot-3 state, corrected System launcher, a root wrapper dropping to mobile,
and a single empty-passcode unlock helper for our freshly created null-secret VM
keybag. All three owned jobs eventually started after roughly ten minutes.
Original workspace registration actually returns NO for the Data-path app, with
an invalid proxy. The unlock helper printed only BEGIN and is absent from later
completed ps listings; no before/after state or unlock call was observed. Its
outcome is unknown, not an observed API failure. Host CPU load reached77 on20cores;
raw read-only pressure/thread observations are in app-boot-6/host-contention.json.
Do not stop or reprioritize unrelated host processes.

Disk-preparation-30 failed its owned app readback because of a nested bundle
directory and was rejected before boot. Corrected disk-preparation-31 passed all
byte/metadata checks and normal unmounts, preserving stopped29 paired lineage. It adds the exact unchanged owned bundle under
`/Applications/InfernoProbe.app`, wrapper9 `--system-app`, phase-instrumented
single-call unlock helper35 with600s watchdog, and extended process observer35.
The original Data bundle remains. Bootworker has started this as app-boot-7 with
7200s maximum,30s frames, guest-errors and strict probe journey; it is now the
only live iOS VM. Input root SHA256 is
c7033cac5a06b7ea924535c780d4baa54363dad88b73ab28d733e211eba56418, paired with
`.local-build/reports/disk-preparation-31`. Stopped29 is a
prepared comparison, not an independently executed successful boot.

The launcher fix uses the original LSApplicationWorkspace registerApplication:
method and logs its BOOL result honestly. The earlier LSRegisterURL was a local,
non-exported symbol; actual dyld abort and negative export audit agree. Corrected
launcher/app53 imports resolve through actual original-cache export tries and
reexports. Root mobile System execution is proven, while the earlier Data launcher
returned EPERM despite successful reads. Console open succeeded as mobile; the
console-permission hypothesis was rejected. Exact inputs and commits are in the
app-probe/native-probe READMEs and committed raw evidence.

Full migration reports show SystemAppMigrator returned NO after a wait for app
demotion, then MobileSlideShow's assetsd waited for first unlock. Advancing plugins
is not proof of successful migration. UUID-matched symbolization and full raw
exports are in `companion/evidence/migration-first-unlock/`. Original MKB supports
a normal NULL-secret unlock for the own NULL-secret keybag. Query first-unlock
returns0/1 or negative errors; do not label raw MKB lock-state enum values without
proof. No fabricated notification, policy bypass, real-device key extraction,
Apple signature forging or activation impersonation is authorized.

## Next concrete work

1. Inspect actual app-boot-7 unlock phase/state/return markers and registration
   BOOL/proxy results. Keep source revisions, hashes, raw logs and stopped root
   plus all six auxiliary namespaces paired. Do not treat helper JSON as proof.
2. Resolve the concrete next failure using original APIs and narrow owned code.
   The unlocked-since-boot bit must change through the original API; do not fake
   notifications or claim success from an attempted call. Keep the currently
   running integrated attempt intact when useful, rather than resetting migration
   at arbitrary status checkpoints.
3. Review actual frames. `companion/vnc-control.py` captures/interacts through the
   VM's private Unix VNC socket without a host window while the runner owns QMP.
   Capture is proven; touch needs a visible guest response. If the real app appears,
   complete and retain a before/after counter tap journey. An accepted launch
   request is insufficient. Serial app markers may not be inherited through LS;
   manual VNC input plus reviewed actual counter frames can provide direct evidence.
4. Only after a successful owned app journey, measure actual cold/warm launch,
   memory, CPU, reliability and parallel density. Current CPU-contended timings
   are not comparative benchmarks. Reuse old fixtures/dashboard only where this
   real backend supports them.

Linux USB run9 shut down normally at09:40:13UTC, emulator0, after full-system
lockdown queries. Its stopped QCOW2 can resume when needed. Syslog StartService
returned PASSWORD_PROTECTED; no syslog stream exists. No active USB VM is needed
for the current serial/VNC journey.

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
