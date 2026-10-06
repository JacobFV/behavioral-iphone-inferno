# Headless early boot experiment

`companion/run boot --profile /absolute/profile.json --seconds 120` starts the
actual t8030 device with TCG, two CPUs, 4 GiB RAM, simulated SEP and a recovery
ramdisk. This is an early execution experiment, not a completed restore or an
installed iOS system. Direct kernel startup applies upstream kernel patches.
Use `companion/run build --simulated-sep` for this path: upstream builds with
data encryption enabled reject simulated SEP during machine initialization.

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

Each input may also include `archive_member` for archive provenance. All four
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
from upstream's full restore example. No USB companion is connected: its address
is an absent socket in the attempt's private temporary directory.

There are no display windows or TCP listeners. VNC and QMP use private Unix
sockets; serial output goes to a file. The duration includes emulator startup,
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
