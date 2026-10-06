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

Keep working; no handoff or missing user input. **Boot19 normal stop requested**
at06:29, worker session82240. Next20 must run directly from normally stopped19
and all paired namespaces, with no guest staging/change. New emulator SHA256
`2a0e467ba6261fbb6da4f1fa8f46bec09cc822a43954b1d3a0a2f06c09e32cf9`, source
`1d8b129c88aae9ed23b4d017f0504bb677c2cc78`, compiled and actual QMP control check
passed (0d269b2bea). QMP smoke is not guest verification. Same serial/mailbox,
900second traces,30second frames,noUSB,7200maximum. Root owns all input.

**New exact correction:** missing DER sls defaults0, which original SBF and
ManagedConfiguration interpret as unlocked WITH a passcode. Original state3
means disabled/no passcode; actual CreateSystem(NULL) passed pointerNULL/length0.
Evidence10a04e0619/5edc796294. Simulator now returns sls INTEGER3 beside unchanged
ss/first-unlock bits. DER23 padded24; all request/transition guards unchanged.
No notification, passcode guess or policy bypass. Original API/rawstate3 and
visible UI behavior must be verified in20. Old fda944 emulator+manifest archived
at .local-build/binaries/simulated-sep-9f92661b1b31. Capacity13GiB before20copy;
only one new tuple needed. Native candidate sourceef4007df33 integrated1d8b129c88.

**Visible touch is proven in19:** root reviewed Hello then sent exactly two:
- info tap f3c727904558499385ca652ec1bf65a5,29400/31250,150ms;
- upward swipe93d5678a3a6d4a4c88b265183844687f,16384/32270 to16384/9145,1500ms.
Original report/ACK results0. Immediate frame was still Hello; later1791292900
capture shows information panel, settled1791292946 capture shows Enter Passcode.
Both requests preceded the first changed capture; no isolated latency claim.
Exact frames/journals preserved throughd654c5e48b. Original IOHIDResource open0,
Create1, owned IOHIDUserDevice4294968461 and IOHIDEventDriver4294968464 are proven.
No input beyond these two, no credentials entered. Owned UIKit remains unproven.

At 06:18 local, **app-boot-18 is normally stopped**, QMPquit49/emulator0 after
946.498589seconds. Root SHA256
`868fd033c50a409e793862ec760d56ac88d458e57e601e9e1ba9acac629414ea` and all six
paired namespaces are preserved. Stage39 used this stopped tuple. Boot18 used verified stage38 root SHA256
`78de9f6dc03f5481f6f8428997eb6f205c044ad7dc5a87f9b21ed2d1c64fc161`, emulatorfda9447b
/source9f92661b, private serial/mailbox,900second startup trace,30second frames,
strictjourney,maximum7200seconds,noUSB. Actual raw QMP confirms all six trace
disables at the900second deadline. No input or HID report was sent in18.

Actual diagnostic build43 finds original IOHIDResource registryID4294968036,
but type0 IOServiceOpen returns0xe00002e2/connection0 and Create returnsNULL.
Original kernel and Sandbox policy analysis now proves the exact missing class
allowlist entitlement. Candidate44 adds only
`com.apple.security.iokit-user-client-class = [IOHIDResourceDeviceUserClient]`
alongside `com.apple.developer.hid.virtual.device = true`. No policy patch or
manager/admin grant. Root independently verified actual69168byte binary SHA256
`89d623ff804b02bba4096df1a33f3ddef574c3c6ac720feadd7996b033954d36`, extracted
entitlements and equality of every file-backed Mach-O section against43.
Source/evidence integrated as9718260ef9/c82e3c8442.

Stage39 replaced only HID helper with44 and reused unchanged build42 readiness/
535byte job. Actual69168 and69207byte readbacks had zero mismatches; clean
unmount and QMPquit6/emulator0 confirmed. All seven stopped hashes retained, root
`29c65e9d70aefe2ff3c2cdea7bd3c04ff68540049c29fa7a0f07807fe825e03d`.
Bootworker then runs19 with unchanged emulator and private serial transport;
root exclusively owns input after reviewing actual device creation and screen.
Free space is22GiB after stage39 and verified retirement of redundant prep38
disks (b0700b140e); recheck before boot19. All real boot tuples
remain preserved. Redundant generated preparation27/37 disks also retired after
full verification (012fec5293); do not treat them as available.

Stage38 installed only the diagnostic HID bytes; prior readiness/job unchanged,
actual readbacks68976 and69207 matched, clean unmount/QMP0/all7 hashes retained.
Stopped17 root0f3cbf476afa0e1842a2cc477ca658c6e518c599fda112be30f9c62019f30015
and paired17 are preserved; normal QMP0 after635.876seconds. Native source453e802ac6,
integrated33e6e96ec7. Current serial socket comes from18 command.json;17 is stopped.

**Actual console roundtrip:** root sent one TAP after reviewed Hello, request
`b1b5fc18ecbd4c0e9af9838aefbfba1b`, x29400 y31250 duration150ms. Original UART to
/dev/console worked: guest parsed the same ID, retried Create (NULL), ACK-103.
No report was emitted, no info screen opened; before/after show Hello animation
only. Evidence `app-guest-console-roundtrip-live*` and local17/hid-info-tap-1.
Root owns input; do not replay that ID or claim API/ACK success as UI delivery.
Those diagnostics executed in18 as recorded above. HIDOpenReportDescriptor is not
an exported API; no original-parser success is claimed.

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

Current runs use `--guest-hid-serial --control-mailbox`. Runner connects to private
Unix serial socket before cont and drains it continuously; QEMU preserves exact
serial output in logfile. Mailbox `guest-hid-gesture` accepts only tap/swipe,
32hex requestID, integer coords0..32767 and duration1..2000ms. Exact protocol in
QMP_CONTROL.md; no arbitrary commands, automatic gestures or replay. Image-free
monitor-frontend smoke proved transport plumbing only. Actual UART roundtrip is now proven; virtual service creation and visible input
remain unproven. The one root-triggered test is described above.

**Live control:** root exclusively owns input. Runner owns the sole QMP connection;
use `companion/qmp_control.py --report .local-build/reports/app-boot-19 ...`.
Never attach a second QMP client or read SPI RXDATA. Fixed seven register reads
are allowlisted. Trace events must remain bounded and disabled afterward. VNC
socket comes from current19 command.json; earlier socket paths are stale. No host
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

1. Finish normal stop19/all7 hashes and run20 with reviewed built emulator2a0e.
   Require actual original lock-state API and visible setup behavior. Candidate
   changes only the missing no-passcode state response; no guest staging needed.
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
