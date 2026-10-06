#!/usr/bin/env python3
"""Bounded, headless t8030 recovery-ramdisk experiment; not an iOS acceptance test."""
# SPDX-License-Identifier: AGPL-3.0-or-later
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import signal
import socket
import subprocess
import tempfile
import time


DISKS = [('root', 32 << 30, 1), ('firmware', 8 << 20, 2),
         ('syscfg', 128 << 10, 3), ('ctrl_bits', 8 << 10, 4),
         ('nvram', 8 << 10, 5), ('effaceable', 4 << 10, 6),
         ('panic_log', 1 << 20, 8)]
BOOT_ARGS = ('debug=0x14e serial=3 wdt=-1 tlto_us=-1 mtxspin=-1 '
             'agm-genuine=1 agm-authentic=1 agm-trusted=1 -vm_compressor_wk_sw')


def digest(path):
    with path.open('rb') as handle:
        return hashlib.file_digest(handle, 'sha256').hexdigest()


def load_profile(path):
    profile = json.loads(path.read_text())
    if profile.get('schema') != 'inferno.early-boot.v1':
        raise ValueError('Profile schema must be inferno.early-boot.v1')
    unexpected = set(profile) - {'schema', 'kernel', 'dtb', 'trustcache', 'ramdisk', 'provenance'}
    if unexpected:
        raise ValueError('Unsupported profile fields: ' + ', '.join(sorted(unexpected)))
    inputs = {}
    for name in ('kernel', 'dtb', 'trustcache', 'ramdisk'):
        entry = profile.get(name)
        if not isinstance(entry, dict) or not {'path', 'sha256'} <= set(entry) or set(entry) - {'path', 'sha256', 'archive_member'}:
            raise ValueError(f'{name} requires path and sha256 (optional archive_member)')
        source = Path(entry['path'])
        if not source.is_absolute():
            raise ValueError(f'{name} path must be absolute')
        source = source.resolve(strict=True)
        if not source.is_file() or source.stat().st_size == 0:
            raise ValueError(f'{name} is not a nonempty regular file: {source}')
        actual = digest(source)
        if actual != entry['sha256']:
            raise ValueError(f'{name} SHA256 mismatch: {source}')
        inputs[name] = {'path': str(source), 'sha256': actual, 'bytes': source.stat().st_size}
    return profile, inputs


class QMP:
    def __init__(self, connection, output):
        self.connection = connection
        self.stream = connection.makefile('rwb', buffering=0)
        self.raw = (output / 'qmp-transcript.jsonl').open('w')
        self.responses = []
        self.counter = 0

    def close(self):
        self.stream.close()
        self.raw.close()

    def receive(self):
        line = self.stream.readline(1024 * 1024)
        self.raw.write(json.dumps({'direction': 'receive', 'time': time.time(),
                                   'raw': line.decode('utf-8', errors='replace')}) + '\n')
        self.raw.flush()
        if not line or len(line) >= 1024 * 1024:
            raise RuntimeError('Missing or oversized QMP response')
        return json.loads(line)

    def execute(self, name, arguments=None):
        self.counter += 1
        request = {'execute': name, 'id': self.counter}
        if arguments is not None:
            request['arguments'] = arguments
        line = json.dumps(request) + '\n'
        self.raw.write(json.dumps({'direction': 'send', 'time': time.time(), 'raw': line}) + '\n')
        self.raw.flush()
        self.stream.write(line.encode())
        deadline = time.monotonic() + 5
        while True:
            self.connection.settimeout(max(.001, deadline - time.monotonic()))
            response = self.receive()
            if response.get('id') == self.counter:
                self.responses.append({'request': request, 'response': response})
                return response


def main():
    repo = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profile', type=Path, required=True)
    parser.add_argument('--binary', type=Path, default=repo / '.local-build/build/qemu-system-aarch64')
    parser.add_argument('--manifest', type=Path)
    parser.add_argument('--seconds', type=float, default=120)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    if not 1 <= args.seconds <= 86400:
        parser.error('--seconds must be between 1 and 86400')
    # Complete validation before allocating disks or launching the emulator.
    try:
        profile_path = args.profile.resolve(strict=True)
        profile, inputs = load_profile(profile_path)
        binary = args.binary.resolve(strict=True)
        if not os.access(binary, os.X_OK):
            raise ValueError(f'Binary is not executable: {binary}')
        binary_hash = digest(binary)
        manifest_path = (args.manifest or binary.parent.parent / 'build-manifest.json').resolve(strict=True)
        manifest = json.loads(manifest_path.read_text())
        if manifest['binary']['sha256'] != binary_hash:
            raise ValueError('Binary SHA256 does not match build manifest')
    except (OSError, ValueError, KeyError, TypeError) as exc:
        parser.error(str(exc))
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
    output = (args.output or repo / '.local-build/reports' / ('boot-' + stamp)).resolve()
    output.mkdir(parents=True, exist_ok=False, mode=0o700)
    report = {'kind': 't8030_recovery_ramdisk_experiment', 'attempt_completed': False,
              'ios_booted': False, 'app_executed': False,
              'milestone_note': 'QMP running and framebuffer captures alone do not establish iOS boot.',
              'profile_path': str(profile_path), 'profile_sha256': digest(profile_path),
              'inputs': inputs, 'binary': str(binary), 'binary_sha256': binary_hash,
              'build_manifest_path': str(manifest_path), 'build_manifest_sha256': digest(manifest_path),
              'build_manifest': manifest, 'runner_sha256': digest(Path(__file__)),
              'companion_revision': subprocess.check_output(['git', '-C', str(repo), 'rev-parse', 'HEAD'], text=True).strip(),
              'duration_limit_seconds': args.seconds, 'disks': [], 'observations': []}
    (output / 'profile.json').write_text(json.dumps(profile, indent=2) + '\n')
    (output / 'build-manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    process = qmp = connection = None
    started = time.monotonic()
    previous_handlers = {}
    def interrupted(signum, frame):
        raise KeyboardInterrupt(f'Signal {signum}')
    try:
        for sig in (signal.SIGTERM, signal.SIGINT):
            previous_handlers[sig] = signal.signal(sig, interrupted)
        with tempfile.TemporaryDirectory(prefix='inferno-boot-') as tmp, \
                (output / 'stderr.log').open('wb') as stderr, \
                (output / 'stdout.log').open('wb') as stdout:
            endpoint = str(Path(tmp) / 'qmp.sock')
            command = [str(binary), '-machine', 't8030,kaslr-off=true,usb-conn-type=unix,usb-conn-addr=' + str(Path(tmp) / 'absent-usb.sock') + ',trustcache=' + inputs['trustcache']['path'].replace(',', ',,'),
                       '-accel', 'tcg', '-smp', '2', '-m', '4G', '-S',
                       '-kernel', inputs['kernel']['path'], '-dtb', inputs['dtb']['path'],
                       '-initrd', inputs['ramdisk']['path'], '-append', BOOT_ARGS,
                       '-display', 'none', '-vnc', 'unix:' + str(Path(tmp) / 'vnc.sock'),
                       '-monitor', 'none', '-serial', 'file:' + str(output / 'serial.log'),
                       '-qmp', 'unix:' + endpoint + ',server=on,wait=off', '-no-reboot']
            disk_dir = output / 'disks'
            disk_dir.mkdir()
            for nsid, (name, size, nstype) in enumerate(DISKS, 1):
                disk = disk_dir / (name + '.raw')
                with disk.open('xb') as handle:
                    handle.truncate(size)
                report['disks'].append({'path': str(disk), 'initial_state': 'fresh sparse zero-filled raw',
                                        'bytes': size, 'nsid': nsid, 'nstype': nstype})
                device = 'apple-nvram' if name == 'nvram' else 'nvme-ns'
                command += ['-drive', f'file={str(disk).replace(",", ",,")},format=raw,if=none,id={name}',
                            '-device', f'{device},drive={name},bus=nvme-bus.0,nsid={nsid},nstype={nstype},logical_block_size=4096,physical_block_size=4096']
            report['invocation'] = command
            (output / 'command.json').write_text(json.dumps(command, indent=2) + '\n')
            # Persist identity even if the host interrupts this experiment.
            (output / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
            started = time.monotonic()
            deadline = started + args.seconds
            process = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=stdout, stderr=stderr)
            report['pid'] = process.pid
            connection = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            while True:
                if process.poll() is not None:
                    raise RuntimeError('Emulator exited before QMP connection; see stderr.log')
                try:
                    connection.connect(endpoint)
                    break
                except (FileNotFoundError, ConnectionRefusedError):
                    if time.monotonic() >= min(deadline, started + 30):
                        raise TimeoutError('QMP initialization deadline reached')
                    time.sleep(.05)
            connection.settimeout(5)
            qmp = QMP(connection, output)
            report['greeting'] = qmp.receive()
            if 'QMP' not in report['greeting']:
                raise RuntimeError('Missing QMP greeting')
            for name in ('qmp_capabilities', 'query-status', 'query-cpus-fast', 'cont'):
                response = qmp.execute(name)
                if 'error' in response:
                    raise RuntimeError(f'QMP {name} failed: {response["error"]}')
            while time.monotonic() < deadline and process.poll() is None:
                time.sleep(min(.2, max(0, deadline - time.monotonic())))
            if process.poll() is not None:
                raise RuntimeError('Emulator exited during boot attempt; see serial.log and stderr.log')
            for name in ('query-status', 'query-cpus-fast'):
                report['observations'].append(qmp.execute(name))
            screenshot = qmp.execute('screendump', {'filename': str(output / 'framebuffer.ppm')})
            report['screendump'] = screenshot
            report['framebuffer_captured'] = 'return' in screenshot and (output / 'framebuffer.ppm').is_file()
            if report['framebuffer_captured']:
                report['framebuffer_sha256'] = digest(output / 'framebuffer.ppm')
            report['attempt_completed'] = True
    except (Exception, KeyboardInterrupt) as exc:
        report['error'] = {'type': type(exc).__name__, 'detail': str(exc)}
    finally:
        if process is not None and process.poll() is None:
            try:
                if qmp:
                    report['quit_response'] = qmp.execute('quit')
                process.wait(timeout=5)
            except (Exception, KeyboardInterrupt):
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
        if qmp:
            report['qmp_commands'] = qmp.responses
            qmp.close()
        if connection:
            connection.close()
        if process:
            report['exit_code'] = process.returncode
        for sig, handler in previous_handlers.items():
            signal.signal(sig, handler)
        report['elapsed_seconds'] = round(time.monotonic() - started, 6)
        serial = output / 'serial.log'
        report['serial_bytes'] = serial.stat().st_size if serial.exists() else 0
        (output / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'attempt_completed': report['attempt_completed'], 'ios_booted': False,
                      'report': str(output / 'report.json')}))
    return 0 if report['attempt_completed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
