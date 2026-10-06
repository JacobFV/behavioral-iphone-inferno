# Linux USB enumeration companion

This bounded ARM64 Linux guest connects Inferno's emulated USB transport to
Linux usbmuxd. It does not run a restore, create tickets or access iCloud.
A running Linux guest is not evidence that the iOS guest reached recovery.

Inputs are the official Ubuntu Noble cloud image, kernel and initrd from
https://cloud-images.ubuntu.com/noble/20260926/ and its `unpacked/` directory.
The tool verifies their SHA256 against the corresponding official HTTPS
manifests, preserves the inputs, and records source URLs and hashes. This is
checksum verification; it does not verify the manifests' detached signatures.
The working QCOW2 is copied with reflink/sparse support. No host mounts or sudo
are required. Host dependencies are Python 3, curl if downloading manually,
OpenSSH ssh-keygen, xorriso and GNU cp.

```sh
python3 companion/usb-companion.py \
  --cache "$HOME/.local/share/inferno/usb-companion/noble-20260926" \
  --prepare-only
python3 companion/usb-companion.py \
  --cache "$HOME/.local/share/inferno/usb-companion/noble-20260926" \
  --binary /absolute/qemu-system-aarch64 \
  --output "$HOME/.local/share/inferno/usb/run1" --seconds 1800
```

Use a new, short output path outside Git. It is private (0700) and contains a
unique disposable SSH key; the guest's password is locked. There is no forwarded
SSH port by default. `--ssh-port PORT` enables loopback-only SSH forwarding
for diagnosis, using `ssh -i OUTPUT/guest-key -p PORT inferno@127.0.0.1`.
A private QMP socket at `OUTPUT/qmp.sock` provides runtime inspection. Networking is QEMU user networking for Ubuntu package installation.
All display output is disabled; serial logs and the report remain in the output.
The current Inferno build enables TCG only. This VM uses two virtual CPUs and
2 GiB RAM by default (`--memory 1G|2G|4G`) and boots the official Linux kernel directly without host EFI files.

NoCloud installs distribution usbmuxd, libimobiledevice-utils and usbutils. Its
script starts usbmuxd, records package versions, and emits
`INFERNO_USB_COMPANION_READY` only after finding the daemon process. It then logs
USB descriptors/device lists every ten seconds. Distro utilities establish a
first enumeration baseline; upstream's full restore instructions require newer,
patched tools and are not implemented here.

Start this guest first. Its USB transport listens at `OUTPUT/usb.sock`; point the
iOS machine's `usb-conn-type=unix,usb-conn-addr=...` there. Both VMs must run
concurrently. A socket alone does not establish daemon or iOS readiness. Check
`serial.log`, `stderr.log`, and `report.json`. USB-device detection and usbmux
visibility are separate milestones; some recovery states will not appear in
`idevice_id -l`. Capture actual USB descriptors and daemon logs before judging
restore-service availability. The bounded process is terminated at the deadline;
its disk and logs are retained for diagnosis. `--disk OLD_OUTPUT/guest.qcow2`
copies a stopped guest disk into a new run to retain already installed packages;
never copy a live writable disk. A new NoCloud instance/key is generated.

To recover an interrupted attempt without changing its cloud-init identity, use
`--resume-from OLD_OUTPUT`. This copies the stopped working disk, seed and
private guest credentials into the new output directory. The old run remains
intact; do not use this option while it is running. Initial 1 GiB execution
reached Ubuntu userland and downloaded apt indices, then became very slow;
run3 retries the same instance with `--memory 4G` and `--ssh-port 22322` for
inspection. This observation does not by itself prove the cause was memory.

Actual run3 reached Linux userland and SSH. Inspection found that cloud-init had
marked the interrupted package module once-per-instance, so it reported `done`
while usbmuxd was absent. Resuming the seed alone does not guarantee retry of
interrupted provisioning. Diagnose with `cloud-init status --long` and
`dpkg-query -W usbmuxd libimobiledevice-utils usbutils`. For this recorded run,
explicitly installing those packages through the private SSH connection, then
running `sudo systemd-run --unit=inferno-enumerate
/usr/local/bin/inferno-enumerate`, completed preparation.

Run3 serial evidence at 2026-10-06 07:36:50 UTC records usbmuxd 1.1.1/libusb
1.0.27 initialization and hotplug registration; the readiness marker and Linux
USB2 root hub enumeration follow at 07:36:52. No Apple device was attached at
that checkpoint. Local raw logs are under
`$HOME/.local/share/inferno/usb/run3/`, including `guest-diagnosis.log`,
`guest-install.log` and `serial.log`. This proves Linux service readiness only.

The two-vCPU run3 Linux guest later panicked in `ehci_irq` immediately after
USB attachment. Stderr recorded blocked re-entrant access to EHCI operational
MMIO. `--cpus 1` enables an unchanged-driver experiment to avoid overlapping
vCPU accesses while usb-tcp-remote waits for a response with BQL released.
This is under validation, not a verified fix. The runner now detects a serial
kernel panic and returns failure even if daemon readiness occurred earlier.

`--accel kvm` selects KVM with `-cpu host` for this Linux companion only,
requiring a KVM-enabled binary and usable `/dev/kvm`. TCG remains the default;
this flag does not alter t8030 acceleration.

The one-vCPU EHCI retry (run4) reproduced the same abort: reducing vCPU count
alone does not fix it. EHCI's guarded asynchronous bottom half can overlap a
vCPU MMIO read when the remote USB handler drops BQL while waiting. Controller
selection is exposed as `--controller usb-ehci|qemu-xhci` for isolated experiments;
no upstream reentrancy guard has been disabled.

Run6 booted the same installed Linux disk with one CPU, xHCI and KVM. QMP
`query-kvm` returned `enabled: true, present: true`; raw queries are retained in
`$HOME/.local/share/inferno/usb/run6/kvm-qmp.json`. Actual SSH, Linux kernel logs,
and usbmuxd initialization establish Linux KVM execution and service readiness.
They do not establish iOS KVM support. The guest clock initially reflected its
saved filesystem time until synchronization; use host report times for elapsed
measurements. Controller transport enumeration remains a separate experiment.

The controlled TCG/xHCI attachment (run5 paired with `recovery-usb-3`) stayed
alive but failed descriptor enumeration: Linux logged repeated `device descriptor
read/64` and `read/8` error `-110`, followed by `unable to enumerate USB device`.
`lsusb` retained only root hubs and `idevice_id -l` was empty. Actual guest
commands and kernel logs are in run5 `guest-usb-diagnosis.log`.

Source explains why xHCI is not a drop-in replacement: xHCI sets
`USBPacket.parameter` for control transfers (`hcd-xhci.c:1727`), while the remote
raw-packet handler bypasses USB core's parameter decoding (`core.c:383`) and
does not transmit that field. xHCI's direct SET_ADDRESS callback also reaches
an unset `handle_control` callback on usb-tcp-remote. EHCI remains the documented
controller, with its observed reentrancy failure unresolved. No upstream guard
or driver was modified for these experiments.

The asynchronous remote USB fix plus deferred SET_ADDRESS writeback were actually
verified with Linux KVM/EHCI and iOS TCG at source `7e70337967`. Run8 enumerated
`05ac:12a8`, serial `00008030-1122334455667788`, and usbmuxd connected the device.
The first emulator was shut down with QMP quit; Linux removed the USB device.
A fresh recovery attempt reconnected to the same Linux VM and enumerated as USB
device 003. A second read-only service query returned
`com.apple.mobile.restored`, protocol version 15. Root independently repeated
that query. This proves recovery-service transport, not installation, a full
system boot, application execution or restore completion. EHCI remains the
supported controller for this transport.

`companion/query-restored.py --udid UDID` calls only the documented
[libimobiledevice restored query API](https://github.com/libimobiledevice/libimobiledevice/blob/master/include/libimobiledevice/restore.h),
then frees the client and device. Run it inside the Linux companion where usbmuxd
and libimobiledevice are installed. It reports API return codes and exits nonzero
on an API failure or a service type other than `com.apple.mobile.restored`.
It does not invoke start-restore, reboot, pairing or signature operations.
Use an external timeout to bound an unresponsive transport, for example:

```sh
ssh -i "$RUN/guest-key" -o UserKnownHostsFile="$RUN/known_hosts" \
  -p 22324 inferno@127.0.0.1 \
  'timeout 20 python3 - --udid 00008030-1122334455667788' \
  < companion/query-restored.py
```

The exact committed query source was executed against the reconnected device;
all five API calls returned zero. Its raw output is in run8
`committable-query.log`. Linux KVM queries, build identity and earlier diagnosis
are in the same directory. The matching iOS records are
`.local-build/reports/recovery-usb-async-2/` and
`.local-build/reports/recovery-usb-async-reconnect/`.

The longer reconnect observation was not a completed 300-second boot: restored
waited 120 seconds for a start-restore request, timed out, tore down userspace,
and the guest then panicked `Halt/Restart Timed Out`. The emulator exited with
code zero around 160 seconds; the boot runner correctly marked the attempt
incomplete. The successful read-only service queries occurred before this
shutdown path. No start-restore request was sent to suppress that timeout.
After preserving the logs, Linux run8 shut down through guest `poweroff`; serial
records `reboot: Power down`, and its emulator exited zero. Its stopped installed
QCOW2 is available for reuse. No experimental VM is intentionally left running.
