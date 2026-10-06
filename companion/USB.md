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
