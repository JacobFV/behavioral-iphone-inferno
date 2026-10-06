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

At05:15 local, **app-boot-15 is stopped and firmware-only stage36 is running**,
native session13795. Stopped15 rootSHA
8cf8592076adef4f9daa20ff6520cc2bf157c81009561fc58041e07e91c24182 and all six paired
auxiliary disks are preserved in app-boot-15; QMPquit/emulator0 after960.150192s.
Stage36 uses this stopped tuple with the archived stable recovery binary. Boot15
was an identical successful retry from
verified observer-only stage35 root
SHAdd1062ad10cf09dc3b18f1c84d8bc2eb6d2d6ed2ff54bdc2c546284d44d403de and all six
paired namespaces in .local-build/reports/disk-preparation-35. Stage35 derives
from stopped12 root20a20cd1288df1bd556c0ff460a39b399f023c89e1918defd233ee09987eeb37.
Actual guest binary/job readback69,159bytes matched; unmount/QMP exit succeeded.
Only owned readiness observer changed: fresh-exec, bounded read-only IOKit
snapshots of AppleHIDTransportDeviceSPI/aop-gpio and immediate relations. No
property dumps, userclient calls, entitlement/cache/job/app/unlock changes.

Boot13 stopped normally and its paired hashes are being retained. It repeated
Hello setup, unlock0/first0->1 and registrationYES, but FrontBoard launcherror1.
Three nondestructive register snapshots showed AOP GPIO34 config0x6020e (masked
mode under the emulator decode), SPI CTRL0/CFG0x4018/PIN2/counts0. The original
matched GPIO class must be identified before inferring a driver/model mismatch.
Boot12 real VNC and QMP input reached MT-SPI and queued make/move/break reports;
no traced dequeue, drain or control consumption occurred. No coordinate changes
are justified. Original configureSPI can send four zero bytes during initial
poweroff, so one RESET first-byte trace alone does not prove firmware boot.

Boot14 emulatorSHAfda9447b41d7bd170a0abf6b56f4b0db822ff9ca84add3e648299d2aa7f59505,
source9f92661b1b3154fb19de51ef9c9a1a6ed6e97d4f adds only trace phase/buffer metadata
for completed RESET, queued boot reply and consumed INT_ACK. Actual build and
control-only smoke passed; neither proves guest success. Runner enables six
MT trace events before cont and automatically disables after180seconds. Private
control mailbox supports query-mice and seven fixed nondestructive touch-register
reads. Never attach a second QMP client or read SPI RXDATA. Root owns all live
input. Same7200seconds maximum,30secondframes,strictjourney,guest-errors,noUSB.
Boot14 exited after9.127seconds with the same early framebuffer bandwidth failure
and panicPC00979a36c seen in historical prep16. Prep17 previously succeeded with
identical inputs to16. No observer ran in14; its raw evidence and all seven disks
are retained. Retry15 uses identical35 inputs and has reached Early boot complete. RESET trace
now proves four-byte completion and queued two-byte reply; no INT_ACK observed.
Initial fixed-register snapshot matches13. Two observer snapshots completed with all statuses0: aop-gpio has original
AppleS5L8960XGPIOIC child; transport has only AppleHIDTransportBootloaderHBPP child
and no operational protocol. Actual original initVector produces6020e exactly;
mode encoding matches emulator. No GPIO behavior change is justified. Original
unlock0/first0->1 repeated. Frame0025 shows white setup surface/status/info/home
indicator (Hello animation between words); no owned app. Root sent no touch.

Next candidate is an honest unsigned outer IMG4 preserving byte-identical IPSW
N104_Multitouch.im4p, without any synthesized manifest/signature/ticket. Original
FUD and kernel parsers permit an absent optional manifest; full execution remains
unproven. Original restore deploys this missing component; normal updater expects
Preboot/<boot-manifest-hash>/usr/standalone/firmware/FUD/Multitouch.img4. Original
System MSUDataAccessor method/table corroborate this path, and this simulated
VM already uses96zero hash directory alongside SEP. Native prepares narrow
Preboot-only install/readback option. Do not stage from live15: once candidate
is built/reviewed, stop15 normally and use its complete paired stopped tuple.
No new validation bypass, fake personalization, GPIO fix or DT property added.
Candidate was reviewed and independent original-byte equality verified; stage36
now installs only the unsigned583090byte container SHA
871a03fb79413e696d3bf952991ac46552a4007585c85f18cb6abbcdbf4943a2. Helper41 SHA
81aadde6112c88709d46b6f50f7db43e1e91b8ceb3721c5dac8b740228486630 from3419586187.
Require actual byte/metadata readback, normal unmount/QMP0 and all seven stopped
hashes before boot16. Same trace emulator fda9447b...59505 and observer thereafter.
Verified obsolete generated prep31-34 disk copies were retired, reclaiming
30,630,694,912bytes; all reports/sources and actual boot disks persist.
Await actual registry/phase results before behavior changes or more gestures.

Boot11 reached original Hello setup UI (reviewedframe0017 and finalRussianHello).
Padded state response works: originalqueryraw0/noerror, unlock0,first0->1. Rawstate0
remains uninterpreted. Callback initiallyPOSIX60timeout thenFrontBoarderror1 while
setupvisible. Nilconfiguration originallyadds LSBlockUntilComplete=true, recorded
in open-path-inspection.json. Boot11stoppednormally1127.465699s/QMPemulator0; full
rawlogs/finalframe/allsevenhashescommitted app-first-setup-stopped*.

Fast and slow VNC swipes/info taps completed RFBdelivery without confirmed UI
navigation. Languageanimation is nottouchproof. Existing source has correctleft
button/absolute coordinates; nocoordinate ordevicebehaviorfix made. Newtraces
observe hostevent→reportenqueue→SPIpacketdequeue/transmitdrain; draindoesnotprove
UIKitacceptance. Enableonlyboundedwindow throughcompanion/qmp_control.py then
disable. SeeQMP_CONTROL.md, useexistingrunnerowner, neversecondQMPclient.
Root VNC helper nowacceptsbounded --hold-seconds/--swipe-seconds/--settle-seconds,
defaultspreserved. Must read12command.json foritsnewprivateVNCsocket;11socketstale.

LiveUSBcannotreconnectafterinitialENOENT; noreset/activation/pairingworkaround.
Stopped32/33/34comparisonsandallactualbootstatesremain. Around42GiBfree.

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

1. Inspect actual app-boot-14 registry/trace phase results, unlock and registration
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
