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
SSH port. Networking is QEMU user networking for Ubuntu package installation.
All display output is disabled; serial logs and the report remain in the output.
The current Inferno build enables TCG only. This VM uses two virtual CPUs and
1 GiB RAM and boots the official Linux kernel directly without host EFI files.

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
its disk and logs are retained for diagnosis.
