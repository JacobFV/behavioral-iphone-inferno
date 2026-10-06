#!/usr/bin/env python3
"""Prepare/run a private ARM64 Linux USB enumeration companion; never restore."""
# SPDX-License-Identifier: AGPL-3.0-or-later
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import time
import urllib.request

BASE = 'https://cloud-images.ubuntu.com/noble/20260926/'
FILES = {'noble-server-cloudimg-arm64.img': '',
         'noble-server-cloudimg-arm64-vmlinuz-generic': 'unpacked/',
         'noble-server-cloudimg-arm64-initrd-generic': 'unpacked/'}


def sha(path):
    with path.open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def prepare(cache):
    cache.mkdir(parents=True, exist_ok=True, mode=0o700)
    records = {}
    for name, section in FILES.items():
        manifest = cache / (('unpacked-' if section else '') + 'SHA256SUMS')
        if not manifest.exists():
            urllib.request.urlretrieve(BASE + section + 'SHA256SUMS', manifest)
        hashes = {line.split(maxsplit=1)[1].lstrip('*'): line.split()[0]
                  for line in manifest.read_text().splitlines() if line.strip()}
        expected = hashes[name]
        target = cache / name
        if not target.exists():
            temporary = target.with_suffix(target.suffix + '.partial')
            urllib.request.urlretrieve(BASE + section + name, temporary)
            if sha(temporary) != expected:
                raise ValueError(f'Checksum mismatch: {name}')
            temporary.rename(target)
        if sha(target) != expected:
            raise ValueError(f'Checksum mismatch: {target}')
        records[name] = {'url': BASE + section + name, 'sha256': expected,
                         'bytes': target.stat().st_size}
    (cache / 'inputs.json').write_text(json.dumps(records, indent=2) + '\n')
    return records


def run(args):
    inputs = prepare(args.cache)
    output = args.output.resolve()
    if ',' in str(output):
        raise ValueError('Output path must not contain commas')
    output.mkdir(parents=True, exist_ok=False, mode=0o700)
    binary = args.binary.resolve(strict=True)
    endpoint = output / 'usb.sock'
    if len(str(endpoint).encode()) > 100:
        raise ValueError('Output path too long for private Unix socket (maximum 91 bytes)')
    subprocess.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-f', str(output / 'guest-key')], check=True)
    key = (output / 'guest-key.pub').read_text().strip()
    seed = output / 'seed'
    seed.mkdir(mode=0o700)
    (seed / 'meta-data').write_text('instance-id: inferno-usb-' + str(time.time_ns()) + '\nlocal-hostname: inferno-usb\n')
    config = {'users': [{'name': 'inferno', 'sudo': 'ALL=(ALL) NOPASSWD:ALL',
                        'shell': '/bin/bash', 'lock_passwd': True,
                        'ssh_authorized_keys': [key]}],
              'package_update': True, 'packages': ['usbutils', 'usbmuxd', 'libimobiledevice-utils'],
              'write_files': [{'path': '/usr/local/bin/inferno-enumerate', 'permissions': '0755',
                              'content': '#!/bin/sh\nexec > /dev/ttyAMA0 2>&1\n'
                                         'systemctl stop usbmuxd || true\n'
                                         'usbmuxd -f -v &\n'
                                         'sleep 2\n'
                                         'pgrep -x usbmuxd || exit 1\n'
                                         'echo INFERNO_USB_COMPANION_READY\n'
                                         'dpkg-query -W usbmuxd libimobiledevice-utils usbutils\n'
                                         'while true; do date -u; lsusb; idevice_id -l; sleep 10; done\n'}],
              'runcmd': [['sh', '-c', '/usr/local/bin/inferno-enumerate &']]}
    (seed / 'user-data').write_text('#cloud-config\n' + json.dumps(config, indent=2) + '\n')
    (seed / 'network-config').write_text('version: 2\nethernets:\n  eth0:\n    match:\n      name: "en*"\n    dhcp4: true\n')
    with (output / 'prepare.log').open('wb') as log:
        subprocess.run(['xorriso', '-as', 'mkisofs', '-quiet', '-V', 'cidata', '-J', '-r',
                        '-o', str(output / 'seed.iso'), str(seed)], stdout=log, stderr=log, check=True)
    subprocess.run(['cp', '--reflink=auto', '--sparse=always',
                    str(args.cache / 'noble-server-cloudimg-arm64.img'), str(output / 'guest.qcow2')], check=True)
    command = [str(binary), '-M', 'virt', '-accel', 'tcg', '-cpu', 'max', '-smp', '2', '-m', '1G',
               '-kernel', str(args.cache / 'noble-server-cloudimg-arm64-vmlinuz-generic'),
               '-initrd', str(args.cache / 'noble-server-cloudimg-arm64-initrd-generic'),
               '-append', 'root=LABEL=cloudimg-rootfs rw console=ttyAMA0',
               '-drive', f'if=none,id=os,file={output}/guest.qcow2,format=qcow2',
               '-device', 'virtio-blk-pci,drive=os',
               '-drive', f'if=none,id=seed,file={output}/seed.iso,format=raw,readonly=on',
               '-device', 'virtio-blk-pci,drive=seed',
               '-netdev', 'user,id=net0', '-device', 'virtio-net-pci,netdev=net0,romfile=',
               '-device', 'usb-ehci,id=ehci', '-device',
               'usb-tcp-remote,bus=ehci.0,conn-type=unix,conn-addr=' + str(endpoint),
               '-display', 'none', '-monitor', 'none', '-serial', 'file:' + str(output / 'serial.log')]
    report = {'kind': 'linux_usb_enumeration_companion', 'inputs': inputs,
              'binary': str(binary), 'binary_sha256': sha(binary), 'runner_sha256': sha(Path(__file__)), 'command': command,
              'usb_socket': str(endpoint), 'guest_ready': False, 'ios_booted': False,
              'restore_attempted': False, 'started_utc': datetime.datetime.now(datetime.timezone.utc).isoformat()}
    (output / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    process = None
    def interrupted(signum, frame):
        raise KeyboardInterrupt(f'Signal {signum}')
    old = {s: signal.signal(s, interrupted) for s in (signal.SIGINT, signal.SIGTERM)}
    try:
        with (output / 'stderr.log').open('wb') as err, (output / 'stdout.log').open('wb') as out:
            process = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=out, stderr=err)
            report['pid'] = process.pid
            (output / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
            deadline = time.monotonic() + args.seconds
            while process.poll() is None and time.monotonic() < deadline:
                serial = output / 'serial.log'
                if not report['guest_ready'] and serial.exists() and b'INFERNO_USB_COMPANION_READY' in serial.read_bytes():
                    report['guest_ready'] = True
                    (output / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
                    print(json.dumps({'guest_ready': True, 'usb_socket': str(endpoint)}), flush=True)
                time.sleep(1)
    except KeyboardInterrupt as exc:
        report['interrupted'] = str(exc)
    finally:
        if process and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
        for sig, handler in old.items():
            signal.signal(sig, handler)
        report['exit_code'] = process.returncode if process else None
        report['ended_utc'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        (output / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'report': str(output / 'report.json'), 'guest_ready': report['guest_ready']}))
    return 0 if report['guest_ready'] else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cache', type=Path, required=True)
    parser.add_argument('--prepare-only', action='store_true')
    parser.add_argument('--binary', type=Path)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--seconds', type=int, default=1800)
    args = parser.parse_args()
    args.cache = args.cache.resolve()
    if args.prepare_only:
        print(json.dumps(prepare(args.cache), indent=2))
        return 0
    if not args.binary or not args.output or args.seconds < 1:
        parser.error('run requires --binary, --output, and positive --seconds')
    return run(args)


if __name__ == '__main__':
    raise SystemExit(main())
