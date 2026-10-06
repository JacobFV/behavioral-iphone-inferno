# Headless early boot experiment

`companion/run boot --profile /absolute/profile.json --seconds 120` starts the
actual t8030 device with TCG, two CPUs, 4 GiB RAM, simulated SEP and a recovery
ramdisk. This is an early execution experiment, not a completed restore or an
installed iOS system. Direct kernel startup applies upstream kernel patches.
Use `companion/run build --simulated-sep` for this path: upstream builds with
data encryption enabled reject simulated SEP during machine initialization.

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
simulated-SEP messages) in `guest-errors.log`. The duration includes emulator startup,
with up to several additional seconds for QMP capture and graceful shutdown.
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

`--disk-boot --probe-journey` requires the app from `companion/app-probe/` to be
installed and launched separately, with its stderr routed to the serial console.
The runner waits for its exact appearance marker, captures `probe-before.ppm`,
sends one absolute QMP pointer press/release near the large button's center,
requires the `tap count=1` marker, and captures `probe-after.ppm`. It fails if any
required step is absent within the duration. Raw QMP events, image hashes and
marker observations are saved in the normal report. Review both actual images
before accepting a visible counter change; command success alone is insufficient.
This optional flow is implemented but has not yet executed against the UIKit app.
