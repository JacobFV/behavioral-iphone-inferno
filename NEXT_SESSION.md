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

Keep working; no handoff or missing user input. Actual installed iOS reaches the
original Hello setup UI. Owned app registration and the original first-unlock API
transition are proven. Owned UIKit execution, touch navigation and a counter
journey remain unproven. Do not return to the archived framework implementation.

At 05:55 local, **app-boot-17 is live**, bootworker session72753, from verified
stage37 root SHA256
`860a6fe36cfbce1fcb2b3c906d42f326fe2af88e5399161980a1a3a1d6827617` and all six
paired namespaces in `.local-build/reports/disk-preparation-37`.
Emulator SHA256 `fda9447b41d7bd170a0abf6b56f4b0db822ff9ca84add3e648299d2aa7f59505`,
source `9f92661b1b3154fb19de51ef9c9a1a6ed6e97d4f`; private serial/mailbox,900second
startup trace,30second frames,strictjourney,maximum7200seconds,noUSB.
Actual helper runs and console is ready, but original IOHIDUserDeviceCreate
returnsNULL (backend-103), so no virtual service or HID report yet.

**Actual console roundtrip:** root sent one TAP after reviewed Hello, request
`b1b5fc18ecbd4c0e9af9838aefbfba1b`, x29400 y31250 duration150ms. Original UART to
/dev/console worked: guest parsed the same ID, retried Create (NULL), ACK-103.
No report was emitted, no info screen opened; before/after show Hello animation
only. Evidence `app-guest-console-roundtrip-live*` and local17/hid-info-tap-1.
Root owns input; do not replay that ID or claim API/ACK success as UI delivery.
Native now prepares exact original IOHIDResource matching/open/close diagnostics
to distinguish failure stages. HIDOpenReportDescriptor is not an exported API;
no original-parser success is claimed. Keep17 live until next candidate reviewed.

**Firmware boundary:** stage36 added one 583090-byte unsigned IMG4 container to
Preboot/<96-zero boot hash>/usr/standalone/firmware/FUD/Multitouch.img4. It preserves
the original IPSW IM4P byte for byte, with no manifest/signature/ticket generated.
Original guest byte/metadata readback matched; clean unmount, QMP0 and seven
stopped hashes retained. Original FUD discovers the file, enters IMG4 validation,
then fails copying the absent manifest digest: callback34,
kFWValidationFailed0xe0000001. Packaging success is not firmware-load success.
Do not fabricate a manifest or add another validation bypass. Evidence:
`companion/evidence/system-app-preparation/stage36/boot16-loader-observation/`.

**Touch diagnosis:** actual VNC/QMP gestures in12 reached current absolute Apple
Multitouch HID SPI and queued reports, but no dequeue/drain/control consumption.
Boot15/16 registry: AppleHIDTransportDeviceSPI below multi-touch/AppleARMSPIDevice,
only AppleHIDTransportBootloaderHBPP child; no operational HIDSPI protocol.
Original firmware supplies the HIDSPI configuration. AOP GPIO driver is original
AppleS5L8960XGPIOIC; its initVector produces observed0x6020e exactly and its mode
encoding matches emulator. No GPIO or coordinate fix is justified. Completed
four-byte RESET queues two-byte reply, no INT_ACK; that transfer is also used by
original initial poweroff configuration. SPI CTRL0/CFG0x4018/PIN2/counts0 persist.

**Current implementation work:** reviewed runnable virtual touchscreen candidate
is integrated as44a179cad2 (native sourcef15ba1987a), with optional private serial
runner transport44814e939f. Root checked actual helper-build42 bytes and extracted
singleton entitlement `com.apple.developer.hid.virtual.device=true`.
HID helper68736bytes SHA256
`3619b68952b5b6fa324f1055b74dd04250fc6c764e4241b5525cbe7e1ac0df74`;
readiness68672bytes SHA256
`3c360cba34c8d7616fc1ac173af4e7ebd21226f69addc9f11a2fcd6c0e8bcba1`.
Stage37 installed these two owned binaries and identical535byte descriptor
from stopped16; actual readbacks68736 and69207 matched, clean unmount/QMP0 and
all seven hashes retained. No new cachejob or app/firmware change.

The helper uses original IOHIDUserDevice APIs and an owned standard touchscreen
report descriptor. Product/Manufacturer identify Inferno; Transport Virtual and
Built-In=true describe this VM's integrated display. Original kernel retains
HIDVirtualDevice=true. No IOClass/provider override, guessed sender/context,
admin or manager entitlement. Original driver supplies normalized coordinates,
display-integrated field and actual service identity. Helper creates device at
startup but sends no report automatically. Before an operator gesture it waits
boundedly for its descendant IOHIDEventService, logs actual IDs/classes and sends
7-byte down/move/up reports with a release attempt on controlled interruption.

Current17 uses `--guest-hid-serial --control-mailbox`. Runner connects to private
Unix serial socket before cont and drains it continuously; QEMU preserves exact
serial output in logfile. Mailbox `guest-hid-gesture` accepts only tap/swipe,
32hex requestID, integer coords0..32767 and duration1..2000ms. Exact protocol in
QMP_CONTROL.md; no arbitrary commands, automatic gestures or replay. Image-free
monitor-frontend smoke proved transport plumbing only. Actual UART roundtrip is now proven; virtual service creation and visible input
remain unproven. The one root-triggered test is described above.

**Live control:** root exclusively owns input. Runner owns the sole QMP connection;
use `companion/qmp_control.py --report .local-build/reports/app-boot-17 ...`.
Never attach a second QMP client or read SPI RXDATA. Fixed seven register reads
are allowlisted. Trace events must remain bounded and disabled afterward. VNC
socket comes from current17 command.json; earlier socket paths are stale. No host
windows, network display endpoints, clipboard or arbitrary guest commands.

**Lineage and retention:** stopped15 root
`8cf8592076adef4f9daa20ff6520cc2bf157c81009561fc58041e07e91c24182` plus paired15
feeds36; normal QMP0 after960.150192s. Observer-only35 came from stopped12.
Boot14 failed before userland at framebuffer panicPC00979a36c; identical15 retry
succeeded, matching an older prep16/17 transient precedent. All actual boot tuples
and reports remain. Verified redundant generated prep24/25/26/28/29/30/31/32/33/34/35/36
disk copies were retired; their hashes/evidence/sources remain. Do not refer to
retired preparation disks as available. Check actual free space before new copies.

**Other proven behavior:** original empty-secret MKBUnlockDevice(NULL,NULL)
returns0 and unlocked-since-boot changes0->1 through the guarded simulated SEP
implementation. State query raw0 has no API error but is not assigned an invented
lock-state enum. No unlock notification was injected. Dictionary LaunchServices
registration returnsYES with valid proxy at /Applications/InfernoProbe.app.
Original callback open request currently returns FBSOpenApplicationServiceErrorDomain
code1; nil configuration uses original LSBlockUntilComplete behavior. No UIKit
markers. Data-path X_OK/execEPERM persists, while the System-owned helper executes.
Evidence and exact original-code inspection are under companion/evidence/.

## Next concrete work

1. Review/build exact original service match/open/close diagnostic candidate, then
   stop17 normally and stage from its complete paired state. Keep the successful
   command transport unchanged. Resolve actual API failure before more gestures;
   never widen entitlements from a NULL return alone.
2. Stage from a normally stopped paired tuple only after the next candidate is
   ready. Commit source, actual build manifests, readbacks, raw logs and hashes.
   Never copy or hash a live disk as an immutable source.
3. Root triggers bounded ordinary setup gestures after reviewing the live screen.
   No account sign-in, activation impersonation or fabricated notifications. If
   the owned app appears, retain actual before/after counter frames and markers.
4. Only after the real app journey, measure launch, memory, CPU, reliability and
   parallel density. Host load has varied heavily; present timings accordingly.
   Reuse old fixtures/dashboard only where this real backend supports them.

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
