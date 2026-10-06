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

Keep working; no handoff or missing user input. SpringBoard and backboardd execute.
Original owned app registration, normal first-unlock and visible Hello setup UI
are now proven. Owned UIKit execution and actual touch response remain unproven. Firmware, System/Data preparation, keybag creation and renderer patches
are established; do not return to the archived framework implementation.

At04:04 local, **app-boot-11 is active** from verified stopped stage34:
root SHA663e93ee73882086d2077b8562fe5e82aa5a920bb74d1300e9f3426063805c75,
paired with .local-build/reports/disk-preparation-34. It uses the diagnostic
launcher at the existing System path, exact unchanged owned app and unlock helper,
and emulator SHA3eacda5c06578e64653313b8ed6774729846d57808e4dec88457a0b58e41b9bd
from source6fce1464b8. 7200-second maximum,30-second frames,strictjourney,guest-errors,
no USB, private Unix VNC. Bootworker owns session41036 and evidence.

**04:21 local live update:** Boot11 reached original Hello setup UI (reviewed
frame0017, committed setup-ui-first-live evidence). Padded state response works:
original query raw0/noerror, unlock0, first0->1. Rawstate0 remains uninterpreted.
Launch callback first returned POSIX60 timeout, then FrontBoardServiceErrorDomain1
while setup is visible. Nilconfiguration originally adds LSBlockUntilComplete=true;
that semantic correction is recorded in open-path-inspection.json.

Root owns all live VNC input. Fast and slow swipes/info taps completed RFBdelivery
but did not show confirmed UI response; language animation is not touchproof.
Current task: bootworker adds narrow single-owner QMP request mailbox and initial
query-mice recording; diskworker adds disabled-by-default MT-SPI delivery trace
points, no behavior change. Root will review/build then boot12 from STOPPED11
paired state, preserving progressed setup. Do not reset11 until both are ready.
No second QMP client: runner owns its connection. Live USB cannot reconnect from
initial ENOENT; no restart/reset or activation/pairing workaround was attempted.

Completed causal sequence:
- Boot7: original unlock selector9 e00002e2/public-2. Original kernel proved
  missing com.apple.keystore.device entitlement on owned helper before SEP.
- Stage32 adds only that singleton entitlement. Boot8 reached unsupported SEP
  opcode18; request echo had wrong response shape, e00002bc/public-1.
- Guarded INFERNO_SIMULATED_SEP partial model supports only validated system0,
  operation0,options0,empty-secret transition. Normal queries report proven
  first-unlock bit2 and xART bit22; other transitions return errors. Boot9 proved
  original unlock return0 and original first-unlock0->1. No notification injected.
- Query options0 and1 share original DER shape. After accepting both, boot10
  still showed selector17 e00002bc. Original __blob decoder proved DER13 requires
  transport padding to16bytes. Current binary fixes only that padding; original
  state-query success still needs boot11 verification. No sls enum is guessed.
- URL app registration skipped the unknown-app path because dictionary was NULL.
  Stage33 dictionary launcher uses exact owned Info.plist plus actual Path.
  Boot10 proved registrationYES/proxyvalid/correct bundle path. Open requests
  returnedNO repeatedly, with roughly10-second delay. No app marker or UI.
- Stage34 adds only original openApplicationWithBundleIdentifier:configuration:
  completionHandler: callback diagnostics, configurationnil, exact BOOL/NSError
  ABI. Log bounded error domain/code/description; no fabricated metadata or
  entitlement. Guest68480-byte readback0mismatch/unmount/QMPstop passed; import
  audit90symbols passed. Prior launcher variants remain unchanged and archived.

Actual raw logs/build manifests/source inspection/stopped hashes are committed
under companion/evidence/. Stage32/33/34 remain immutable paired comparisons.
Obsolete generated prep24/25/26/28/30 disk copies were retired only after complete
hash/evidence checks; logs/reports/sources and every actualboot tuple remain.
Host CPU contention prevents benchmark claims; do not alter unrelated processes.

Migration reports previously showed SystemAppMigrator returnedNO and assetsd
waited in PLFirstUnlockProtection. First-unlock query success does not itself
prove all migration or notifications complete. Current full guest observation is
required. Latest reviewed boot10 frame was black; never label black as ready.
No fake notification, guard suppression, Apple signature forging, real-device
key extraction or activation impersonation is authorized.

## Next concrete work

1. Inspect actual app-boot-11 unlock phase/state/return markers and registration
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
