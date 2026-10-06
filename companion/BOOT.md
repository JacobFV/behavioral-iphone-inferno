# Headless iOS execution

The current installed iOS14 beta5 path has completed setup, launched original
Clock, and run the owned UIKit counter through two consecutive strict journeys
(boots33/34). Each retained actual lifecycle/tap records, reviewed counter0→1,
both QMP screenshots, normal emulator exit0 and unchanged backing ancestors.
See `evidence/owned-loopback-strict-journey-33.json` and the corresponding34 record.
`NEXT_SESSION.md` identifies the active run, frozen image state and exact binaries.

The command below without `--disk-boot` starts the earlier recovery experiment:
`companion/run boot --profile /absolute/profile.json --seconds 120`.
It uses the actual t8030 device with TCG, two CPUs,4GiB RAM, simulatedSEP and a
recovery ramdisk. A recovery boot is distinct from the proven installed-iOS path.
Direct kernel startup applies upstream patches. Use
`companion/run build --simulated-sep` for this path: upstream builds with data
encryption enabled reject simulatedSEP during machine initialization.

Prepare the documented iPhone 11 iOS 14.0 beta 5 (18A5351d) inputs from a local
IPSW downloaded from the Apple URL in upstream's File Setup guide:

```sh
companion/run prepare --ipsw /absolute/iPhone11,8,iPhone12,1_14.0_18A5351d_Restore.ipsw \
  --output /absolute/outside-repository/ios14b5-profile
companion/run boot --profile /absolute/outside-repository/ios14b5-profile/profile.json
```

Preparation checks the device/build and selects the n104ap research erase
identity in BuildManifest.plist. It records the full archive and component hashes,
and extracts only the kernel, device tree, restore trustcache and restore ramdisk.
It does not create tickets or process SEP firmware. The URL is recorded as the
documented acquisition location; a local file's hash does not itself prove origin.

The profile must live outside tracked source and use this schema:

```json
{
  "schema": "inferno.early-boot.v1",
  "kernel": {"path": "/absolute/kernelcache", "sha256": "64 hex digits"},
  "dtb": {"path": "/absolute/DeviceTree.im4p", "sha256": "64 hex digits"},
  "trustcache": {"path": "/absolute/ramdisk.trustcache", "sha256": "64 hex digits"},
  "ramdisk": {"path": "/absolute/ramdisk.dmg", "sha256": "64 hex digits"},
  "provenance": {"description": "Record official source, build and preparation"}
}
```

Each input may also include `archive_member` and `size` for archive provenance. All four
files must be nonempty regular files with matching SHA256 before the emulator
starts. Unknown profile settings are rejected. This profile does not accept SEP
firmware, SEP ROM, tickets, arbitrary flags or existing writable disks.
`--binary`, `--manifest` and `--output` override the local build defaults. The
binary must match the recorded build-manifest SHA256. Output must be a new path.

The runner follows the namespace sizes and types from upstream
[File Setup](https://chefkiss.dev/guides/inferno/file-setup/) and the kernel,
device-tree, trustcache and ramdisk wiring in
[Running & Restoring](https://chefkiss.dev/guides/inferno/running-restoring/).
Each attempt creates seven fresh sparse raw namespaces: root 32 GiB, firmware
8 MiB, syscfg 128 KiB, ctrl_bits 8 KiB, nvram 8 KiB, effaceable 4 KiB and panic_log
1 MiB. Empty NVRAM takes upstream's recovery path. The simulated SEP choice is
from `hw/arm/apple-silicon/t8030.c` when no SEP firmware/ROM is provided; it differs
from upstream's full restore example. By default no USB companion is connected. Supply `--usb-socket` with an existing
private Unix socket from the isolated Linux companion to test attachment. See
[USB.md](USB.md) for the current transport failures and execution evidence.

For a prepared root disk, supply `--root-image /absolute/root.raw` and its expected
`--root-sha256`. The runner validates its 4096-byte GPT and copies it into the
attempt directory before guest writes; the source is never attached writable.
The copy retains the source size instead of the default 32GiB blank namespace.
Use `--auxiliary-state /absolute/stopped-attempt` to copy its six other namespaces
alongside the explicit root image. The prior report must record emulator exit;
the runner records each actual source hash and verifies each private copy before
launch. This preserves this VM's initialized effaceable/NVRAM state between runs.
Without this option auxiliary namespaces start fresh. Pair the state from the
same stopped preparation with its root image; a root-only copy is insufficient
once preparation starts writing auxiliary storage.
Choose one boot mode:

- Default recovery passes `-restore rd=md0`; the guest currently exposes a dummy
  NVMe disk, unsuitable for preparing a supplied APFS image.
- `--ramdisk-boot` retains the ramdisk but exits recovery boot mode and passes
  `rd=md0`. This executed the owned disk helper against real NVMe namespaces.
- `--disk-boot` omits the initrd and exits recovery boot mode. Use the firmware's
  StaticTrustCache in the profile for the full System image. This has reached
  Darwin Bootstrapper, but installed iOS boot completion remains unproven.
- `--recovery-preserve-disk` explicitly disables the recovery reformat argument.
  Actual execution still exposed a dummy disk; it did not solve disk preparation.

See [native-probe/README.md](native-probe/README.md) for the owned helper and
[os-image/README.md](os-image/README.md) for original System image preparation.

There are no display windows or TCP listeners. VNC and QMP use private Unix
sockets; serial output goes to a file. `--guest-errors` additionally records emulator device diagnostics (including
simulated-SEP messages) in `guest-errors.log`. `--capture-interval 30` saves
intermediate framebuffer images under `frames/`, with elapsed times and hashes
in the report. The duration includes emulator startup, with up to several
additional seconds for QMP capture and graceful shutdown.
Shutdown falls back to termination and kill if QMP is unavailable. The output
retains disks, serial/stdout/stderr logs, raw QMP JSON lines (including asynchronous
events), command argv, profile and build-manifest copies, identity hashes,
status/CPU queries and a PPM screendump when available. Temporary sockets disappear
after the run. The source revision is the manifest's `source_revision`; the
runner's current Git revision and file hash are separately recorded.

A zero exit status means the bounded attempt stayed alive and reached the end of
its observation interval. It does not certify guest boot. Inspect raw serial logs
and the framebuffer before describing any milestone. A QMP running state means
virtual CPUs are scheduled; it proves neither recovery readiness nor iOS boot,
app launch, screenshot correctness or performance. Blank disks cannot provide an
installed iOS application journey.

The first real 30-second attempt (2026-10-06) used the original build. It decoded
the iOS 14 kernel and applied upstream patches, then exited with `Simulated SEP
cannot be used with data encryption at the moment.` QMP sent its greeting but
reset before capability negotiation; serial output was empty. This is execution
evidence of an initialization failure, not guest kernel execution. Local raw
evidence: `.local-build/reports/first-t8030-boot/`.

## Owned app interaction experiment

`--disk-boot --probe-journey --control-mailbox` requires the app from `companion/app-probe/` to be
installed and launched separately, with its stderr routed to the serial console.
The runner waits for its exact appearance marker and the operator's explicit
`probe-capture-before` request after live visual review, captures `probe-before.ppm`,
waits for an operator-produced `tap count=1` marker, and captures
`probe-after.ppm`. It sends no input by default and fails if any
required step is absent within the duration. Raw QMP events, image hashes and
marker observations are saved in the normal report. Review both actual images
before accepting a visible counter change; command success alone is insufficient.
This optional flow is implemented but has not yet executed against the UIKit app.
The legacy automatic QMP press/release additionally requires the explicit
`--probe-hardware-tap` flag, which is incompatible with `--guest-hid-serial`.
Use observation mode for the current operator-controlled virtual HID route.

## Explicit owned launchd configuration

`--disk-boot --launchd-unsecure-cache` appends the original loader's supported
`launchd_unsecure_cache=1` argument. Use it with the disposable System configuration
produced by `native-probe/merge-launchd-cache.py`: that file preserves original
jobs and adds explicit `org.inferno.*` jobs. The existing `.sig` is unchanged; no
signature is generated. This mode is opt-in, recorded in the invocation/report,
and rejected for recovery boots. Actual execution must show the original loader's
“Using unsecure cache” message and owned job output before claiming job loading.

## Headless interaction during a long boot

`python3 companion/vnc-control.py --socket /absolute/private/vnc.sock --output /fresh/output`
captures the running guest without another QMP connection or a host window. Read
the socket from the attempt's recorded `-vnc unix:...` argument. The narrow
[RFB3.8 client](https://www.rfc-editor.org/rfc/rfc6143.html) uses Pillow and supports
`--tap X Y` or `--swipe X0 Y0 X1 Y1` after reviewing the current screenshot. It
records before/after PNGs, hashes and exact pointer packets. It accepts only an
existing Unix socket. Capture was actually verified against app-boot-3; pointer
input remains unverified until a visible guest response is observed. QEMU VNC
reported832x1792 while QMP reports828x1792; retain that surface-width distinction.

Observation-only now retains `before.png`, waits `--settle-seconds` on the same
connection, then saves `settled.png`. Optional `--observe-seconds 30` keeps the
connection active with additional captures for up to300seconds; it cannot be
combined with input. Each capture records request, receive and save times.
A first full VNC framebuffer can precede new rendering; display refresh can also
stimulate guest rendering. Keep observation active across a launch when examining
visual arrival, and do not interpret lifecycle clocks as presentation times.

For installed iOS Home navigation, `--home-button` sends a single fixed150ms
F6 press/release over that private VNC socket. The existing emulator maps F6 to
SMC Menu; actual37 showed original SMC button6 notifications, app background,
and visible SpringBoard Home. Exact RFB packets, timestamps and before/after
captures are recorded. This does not establish touch edge-swipe support: two
such swipes in37 had no effect. Arbitrary keyboard input is not exposed.

For a retained strict journey followed by warm measurements, start the boot with
`--probe-journey --control-mailbox --guest-hid-serial --probe-keep-running` in
addition to its verified image/profile arguments. After reviewed0→1 and both
strictcaptures, the VM remains live. Review Home and actual appbackground before
sending a fresh explicit `guest-open-app` request with the current boot UUID.
The guest opens only the owned bundle; there is no automatic input or retry.

```sh
python3 companion/qmp_control.py --report /absolute/attempt guest-open-app \
  --arguments '{"request_id":"NEW32LOWERCASEHEX","boot_uuid":"EXACT-CURRENT-GUEST-BOOT-UUID"}'
python3 companion/warm-timing.py --report /absolute/attempt \
  --request-id NEW32LOWERCASEHEX --output /fresh/trial.json
python3 companion/qmp_control.py --report /absolute/attempt finish-run
```

Replace both placeholders with actual values. The parser requires same-incarnation
background→OPEN→foreground/active raw guest clocks and validated records; review
the returned app separately. Successful callbacks alone are not UI evidence.
`finish-run` uses normal QMP cleanup and is accepted only after strict completion
when keepalive was enabled. Three actual37 cycles retained counter1 and original
process identity; individual intervals are in `evidence/warm-timing-37-actual`.

Shutdown cleanup makes a bounded, best-effort final framebuffer capture before
QMP quit when the normal completion path did not capture one, including an
interrupted or incomplete strict journey. Capture failures are recorded separately
and do not replace the original attempt error or prevent shutdown. A saved frame
is evidence of its pixels only; it does not establish an app milestone.

In observation mode the operator also reviews visible counter1 and sends
`probe-capture-after` after the genuine tap1 marker. The runner does not
automatically capture or quit on a marker that might precede rendering.

## Opt-in raw-backed root overlays

The default remains a private raw root copy. `--root-overlay` instead creates
`disks/root.qcow2` over the hash-verified `--root-image` raw base; all six auxiliary
namespaces remain independent raw copies. Bootstrap the pinned Ubuntu24.04 arm64
`qemu-img` tools outside Git with:

```sh
python3 companion/disk_overlay.py bootstrap
```

An alternate external directory can be selected with `--tools-root` for bootstrap
and `--overlay-tools-root` for boot. Package URLs, SHA256 hashes and extracted-file
hashes are recorded and checked. The existing emulator executable is unchanged.

The source must be a stopped, retained raw image with every write mode bit cleared.
The runner refuses writable bases and unrecorded qcow2 inputs; it never changes
file permissions itself. After verifying and freezing a selected base, place an explicit
`KEEP-OVERLAY-BACKING.json` marker in its `disks/` directory before launching a
dependent boot. Record the raw base path/hash and intended dependent attempt in
that marker, then update it with the actual attempt's overlay/report path. The
previous retirement procedure requires exactly seven raw files, so this extra
marker deliberately makes that guard reject the protected directory. Do not remove
the marker or retire the backing file while any dependent overlay is retained.

`root-overlay.json` and the normal report record the immutable backing path,
full hash, file identity, qcow2 format, tool provenance and dependency warning.
An overlay is **not standalone**: retain its base at that exact absolute path.
Do not use `root.qcow2` as the next `--root-image`. For a retained, normally
stopped owned overlay, use `--overlay-base-report /absolute/report.json` instead
of raw-root and auxiliary arguments. It validates the recorded quit and all
stopped hashes, follows only recorded immutable ancestors, and copies the six
auxiliary namespaces from that same report. Up to four qcow2 layers are allowed.
Every source layer must already have all write mode bits cleared and no open
writable descriptors. Reports, retention markers and every backing layer must
remain at their recorded paths. Flattening/export is not implemented. Permission bits and hashes provide an operational contract,
not protection against a privileged process replacing the file. The base is
verified before creation and again after the emulator stops; changes fail the
attempt. Reported `elapsed_seconds` includes postflight backing verification and
therefore is not a pure guest-runtime or boot-latency measurement.

The actual [synthetic block run](evidence/disk-overlay-block-1/provenance.json)
used the existing QEMU binary with `-machine none`, wrote/read an overlay pattern,
read unchanged bytes through from its backing file, independently verified the
persisted bytes, passed `qemu-img check`, and preserved the full backing SHA256.
Only 331,776 bytes were allocated for that 16 MiB synthetic case. This proves block
behavior, not an iOS boot or performance improvement. For planned boot27, the
stopped stage43 raw root must remain protected together with the boot27 overlay;
that actual iOS run and its measured disk growth are separate evidence.

### Evidence-backed report milestones

New reports keep deprecated `ios_booted` null: recovery userspace and a usable
installed system are different milestones. `milestones` records kernel/kext
serial output, launchd userspace, the owned fixture lifecycle, and the strict
journey as `observed` or `unestablished`. Final observations include raw serial
SHA-256, byte ranges and marker text. `app_executed` becomes true only for matching
current-boot owned main/appeared raw loopback records, their validation records
and emitted UIKit markers; otherwise it is null. This is scoped to the owned
fixture. The TCP peer PID is not authenticated.

Strict observation additionally requires the completed journey, genuine tap1
chain, expected capture paths, both actual frame hashes and the operator capture
gates when applicable. It does not interpret image pixels or claim automated
visual verification; operator review remains required. QMP operation or a blank
frame alone establishes none of these guest milestones. Old reports are not
rewritten. The reporter source hash is recorded alongside the runner hash.
