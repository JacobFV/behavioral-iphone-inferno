#!/usr/bin/env python3
"""Bounded, headless t8030 recovery-ramdisk experiment; not an iOS acceptance test."""
# SPDX-License-Identifier: AGPL-3.0-or-later
import argparse
from contextlib import nullcontext
import datetime
import hashlib
import json
import os
from pathlib import Path
import signal
import socket
import stat
import subprocess
import tempfile
import time
from disk_overlay import DEFAULT_TOOLS, validate_tools, validate_base, create_overlay, verify_backing, load_stopped_overlay, create_recorded_overlay
from probe_journey import ProbeJourney
from headless_refresh import HeadlessRefresh
from boot_milestones import observe as observe_milestones
from qmp_control import ControlMailbox, StartupTouchTrace, SerialGestureTransport, SWAPWAIT_FILTER, SWAPWAIT_PROFILES, SWAPWAIT_KERNEL, SWAPWAIT_BINARY, SWAPWAIT_SOURCE


DISKS = [('root', 32 << 30, 1), ('firmware', 8 << 20, 2),
         ('syscfg', 128 << 10, 3), ('ctrl_bits', 8 << 10, 4),
         ('nvram', 8 << 10, 5), ('effaceable', 4 << 10, 6),
         ('panic_log', 1 << 20, 8)]
BOOT_ARGS = ('debug=0x14e serial=3 wdt=-1 tlto_us=-1 mtxspin=-1 '
             'agm-genuine=1 agm-authentic=1 agm-trusted=1 -vm_compressor_wk_sw')


def digest(path):
    with path.open('rb') as handle:
        return hashlib.file_digest(handle, 'sha256').hexdigest()


def capture_final_frame(qmp, output, report):
    """Best effort on shutdown; never replace the original attempt error."""
    if report.get('framebuffer_captured'):
        return
    frame = output / 'framebuffer.ppm'
    report['final_capture_attempted_at'] = time.time()
    try:
        response = qmp.execute('screendump', {'filename': str(frame)}, timeout=5)
        report['screendump'] = response
        report['framebuffer_captured'] = 'return' in response and frame.is_file()
        if report['framebuffer_captured']:
            report['framebuffer_sha256'] = digest(frame)
        else:
            report['final_capture_error'] = 'QMP screendump failed or produced no file'
    except (Exception, KeyboardInterrupt) as exc:
        report['final_capture_error'] = {'type': type(exc).__name__, 'detail': str(exc)}


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
        if not isinstance(entry, dict) or not {'path', 'sha256'} <= set(entry) or set(entry) - {'path', 'sha256', 'archive_member', 'size'}:
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

    def execute(self, name, arguments=None, timeout=5):
        self.counter += 1
        request = {'execute': name, 'id': self.counter}
        if arguments is not None:
            request['arguments'] = arguments
        line = json.dumps(request) + '\n'
        self.raw.write(json.dumps({'direction': 'send', 'time': time.time(), 'raw': line}) + '\n')
        self.raw.flush()
        self.stream.write(line.encode())
        deadline = time.monotonic() + timeout
        while True:
            self.connection.settimeout(max(.001, deadline - time.monotonic()))
            response = self.receive()
            if response.get('id') == self.counter:
                self.responses.append({'request': request, 'response': response})
                return response


def probe_should_stop(journey, control):
    """Completion preserves the default stop unless explicitly held by the operator."""
    return bool(journey and journey.report['completed'] and
                (control is None or not control.run_control['keep_running'] or
                 control.run_control['finish_requested']))


def main():
    repo = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profile', type=Path, required=True)
    parser.add_argument('--touch-trace-startup', action='store_true',
                        help='trace six touch-model events before cont; disable after a bounded interval')
    parser.add_argument('--touch-trace-seconds', type=int,
                        help='startup trace limit from 1 to 1800 seconds; default 180; requires --touch-trace-startup')
    parser.add_argument('--control-mailbox', action='store_true',
                        help='enable private allowlisted pointer/input-trace requests via qmp_control.py')
    parser.add_argument('--guest-hid-serial', action='store_true',
                        help='optional private serial gesture transport; requires --control-mailbox')
    parser.add_argument('--binary', type=Path, default=repo / '.local-build/build/qemu-system-aarch64')
    parser.add_argument('--manifest', type=Path)
    parser.add_argument('--seconds', type=float, default=120)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--swapwait-cpu-profile', choices=tuple(SWAPWAIT_PROFILES), default='baseline', help='fixed CPU sites; pending-branch requires explicit diagnostic opt-in')
    parser.add_argument('--swapwait-cpu-diagnostic', action='store_true', help='opt in to fixed kernel SwapWait GPR windows; requires pinned inputs, mailbox and guest-errors')
    parser.add_argument('--guest-errors', action='store_true',
                        help='record QEMU guest-error diagnostics in guest-errors.log')
    parser.add_argument('--launchd-unsecure-cache', action='store_true',
                        help='use original loader support for an edited launchd configuration on a disposable disk')
    parser.add_argument('--probe-journey', action='store_true',
                        help='observe owned UIKit appearance/operator tap markers and capture before/after; sends no input')
    parser.add_argument('--probe-keep-running', action='store_true',
                        help='keep completed observation alive until duration or finish-run; requires journey and mailbox')
    parser.add_argument('--probe-hardware-tap', action='store_true',
                        help='explicitly allow legacy QMP hardware tap; requires --probe-journey, not guest-HID serial')
    parser.add_argument('--headless-refresh-seconds', type=int, default=0,
                        help='opt-in runner-owned no-input VNC observer for 1..300 seconds after cont; 0 disables')
    parser.add_argument('--capture-interval', type=float, default=0,
                        help='save periodic headless framebuffers; zero disables, otherwise at least 5 seconds')
    parser.add_argument('--usb-socket', type=Path,
                        help='existing local Unix socket of a running isolated USB companion')
    parser.add_argument('--root-image', type=Path,
                        help='raw 4096-sector GPT base; privately copied by default')
    parser.add_argument('--overlay-base-report', type=Path,
                        help='opt-in child overlay from a normally stopped owned overlay report; copies its six auxiliaries')
    parser.add_argument('--root-overlay', action='store_true',
                        help='opt-in qcow2 root over retained read-only raw base; six auxiliary disks stay copied raw')
    parser.add_argument('--overlay-tools-root', type=Path, default=DEFAULT_TOOLS,
                        help='pinned tools directory created by disk_overlay.py bootstrap')
    parser.add_argument('--root-sha256', help='required expected SHA256 of --root-image')
    parser.add_argument('--auxiliary-state', type=Path,
                        help='stopped boot report directory whose six auxiliary namespaces are copied')
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument('--disk-boot', action='store_true',
                        help='experimental direct root boot instead of recovery ramdisk')
    modes.add_argument('--ramdisk-boot', action='store_true',
                       help='boot rd=md0 without recovery reformat arguments; keeps NVMe visible')
    modes.add_argument('--recovery-preserve-disk', action='store_true',
                       help='recovery environment with explicit nand-enable-reformat=0')
    args = parser.parse_args()
    if args.probe_keep_running and (not args.probe_journey or not args.control_mailbox or args.probe_hardware_tap):
        parser.error('--probe-keep-running requires --probe-journey and --control-mailbox, and excludes --probe-hardware-tap')
    if args.guest_hid_serial and not args.control_mailbox:
        parser.error('--guest-hid-serial requires --control-mailbox')
    if args.touch_trace_seconds is not None:
        if not args.touch_trace_startup:
            parser.error('--touch-trace-seconds requires --touch-trace-startup')
        if not 1 <= args.touch_trace_seconds <= 1800:
            parser.error('--touch-trace-seconds must be between 1 and 1800')
    if args.probe_journey and not args.disk_boot:
        parser.error('--probe-journey requires --disk-boot')
    if args.probe_hardware_tap and not args.probe_journey:
        parser.error('--probe-hardware-tap requires --probe-journey')
    if args.probe_journey and not args.probe_hardware_tap and not args.control_mailbox:
        parser.error('Observation --probe-journey requires --control-mailbox for operator before capture')
    if args.probe_hardware_tap and args.guest_hid_serial:
        parser.error('--probe-hardware-tap cannot be combined with --guest-hid-serial')
    if args.launchd_unsecure_cache and not args.disk_boot:
        parser.error('--launchd-unsecure-cache requires --disk-boot')
    if args.overlay_base_report and (args.root_image or args.root_sha256 or args.root_overlay or args.auxiliary_state):
        parser.error('--overlay-base-report excludes raw root arguments, --root-overlay and --auxiliary-state')
    if args.auxiliary_state and not args.root_image:
        parser.error('--auxiliary-state requires an explicit --root-image and hash')
    if not 1 <= args.seconds <= 86400:
        parser.error('--seconds must be between 1 and 86400')
    if not 0 <= args.headless_refresh_seconds <= 300:
        parser.error("--headless-refresh-seconds must be 0..300")
    if args.capture_interval != 0 and not 5 <= args.capture_interval <= 86400:
        parser.error('--capture-interval must be zero or between 5 and 86400 seconds')
    # Complete validation before allocating disks or launching the emulator.
    auxiliary = {}
    overlay_tool = None
    overlay_chain = None
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
        if args.swapwait_cpu_profile != 'baseline' and not args.swapwait_cpu_diagnostic:
            raise ValueError('CPU profile requires --swapwait-cpu-diagnostic')
        if args.swapwait_cpu_diagnostic:
            if not (args.control_mailbox and args.guest_errors and args.disk_boot):
                raise ValueError('SwapWait diagnostic requires mailbox, guest-errors and disk boot')
            if inputs['kernel']['sha256'] != SWAPWAIT_KERNEL or binary_hash != SWAPWAIT_BINARY or manifest['source_revision'] != SWAPWAIT_SOURCE:
                raise ValueError('SwapWait diagnostic requires exact reviewed kernel and binary/source pins')
        usb_socket = args.usb_socket.resolve(strict=True) if args.usb_socket else None
        if usb_socket and not stat.S_ISSOCK(usb_socket.stat().st_mode):
            raise ValueError('--usb-socket must name an existing Unix socket')
        if bool(args.root_image) != bool(args.root_sha256):
            raise ValueError('--root-image and --root-sha256 must be supplied together')
        if args.root_overlay and not args.root_image:
            raise ValueError('--root-overlay requires --root-image and --root-sha256')
        if args.disk_boot and not (args.root_image or args.overlay_base_report):
            raise ValueError('--disk-boot requires --root-image or --overlay-base-report')
        root_image = args.root_image.resolve(strict=True) if args.root_image else None
        if root_image:
            if not root_image.is_file() or (not args.root_overlay and digest(root_image) != args.root_sha256):
                raise ValueError('Root image missing or SHA256 mismatch')
            with root_image.open('rb') as stream:
                stream.seek(4096)
                if stream.read(8) != b'EFI PART':
                    raise ValueError('Root image must have GPT with 4096-byte sectors (NVMe geometry)')
        if args.root_overlay:
            validate_base(root_image, args.root_sha256)
            overlay_tool = validate_tools(args.overlay_tools_root)
        if args.overlay_base_report:
            overlay_tool = validate_tools(args.overlay_tools_root)
            overlay_chain = load_stopped_overlay(args.overlay_base_report, overlay_tool)
            state_report_path = Path(overlay_chain['report'])
            for name, size, _ in DISKS[1:]:
                auxiliary[name] = overlay_chain['auxiliary'][name + '.raw']
        if args.auxiliary_state:
            state_dir = args.auxiliary_state.resolve(strict=True)
            state_report_path = state_dir / 'report.json'
            state_report = json.loads(state_report_path.read_text())
            if not isinstance(state_report, dict):
                raise ValueError('Auxiliary source report must be a JSON object')
            if not isinstance(state_report.get('exit_code'), int):
                raise ValueError('Auxiliary source report must record a stopped emulator exit code')
            if state_report.get('kind') not in ('t8030_recovery_ramdisk_experiment', 't8030_direct_root_experiment'):
                raise ValueError('Auxiliary source must be a t8030 boot report')
            for name, size, _ in DISKS[1:]:
                source = (state_dir / 'disks' / (name + '.raw')).resolve(strict=True)
                if not source.is_file() or source.stat().st_size != size:
                    raise ValueError(f'Auxiliary namespace {name} has unexpected size')
                auxiliary[name] = {'path': str(source), 'sha256': digest(source), 'bytes': size}
    except (OSError, ValueError, KeyError, TypeError) as exc:
        parser.error(str(exc))
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
    output = (args.output or repo / '.local-build/reports' / ('boot-' + stamp)).resolve()
    output.mkdir(parents=True, exist_ok=False, mode=0o700)
    report = {'kind': ('t8030_direct_root_experiment' if args.disk_boot else 't8030_recovery_ramdisk_experiment'), 'attempt_completed': False,
              'ios_booted': None, 'app_executed': None,
              'milestones': {name: {'state': 'unestablished', 'evidence': []} for name in
                             ('kernel_serial', 'launchd_userland', 'owned_app_lifecycle', 'strict_owned_journey')},
              'milestone_source_sha256': digest(Path(__file__).with_name('boot_milestones.py')),
              'milestone_note': 'QMP running and framebuffer captures alone do not establish iOS boot.',
              'profile_path': str(profile_path), 'profile_sha256': digest(profile_path),
              'inputs': inputs, 'binary': str(binary), 'binary_sha256': binary_hash,
              'build_manifest_path': str(manifest_path), 'build_manifest_sha256': digest(manifest_path),
              'build_manifest': manifest, 'runner_sha256': digest(Path(__file__)),
              'companion_revision': subprocess.check_output(['git', '-C', str(repo), 'rev-parse', 'HEAD'], text=True).strip(),
              'duration_limit_seconds': args.seconds, 'disks': [], 'observations': []}
    if root_image:
        report['root_base'] = {'path': str(root_image), 'sha256': args.root_sha256,
                               'bytes': root_image.stat().st_size, 'copied_before_use': not args.root_overlay,
                               'retained_immutable_backing': args.root_overlay}
    if overlay_chain:
        report['overlay_base_report'] = {key: overlay_chain[key] for key in
                                         ('report', 'report_sha256', 'stopped_manifest', 'stopped_manifest_sha256')}
    if auxiliary:
        report['auxiliary_base'] = {'report': str(state_report_path),
                                    'report_sha256': digest(state_report_path),
                                    'namespaces': auxiliary, 'copied_before_use': True}
    (output / 'profile.json').write_text(json.dumps(profile, indent=2) + '\n')
    (output / 'build-manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    journey = ProbeJourney(output, hardware_tap=args.probe_hardware_tap) if args.probe_journey else None
    if journey:
        report['probe_journey'] = journey.report
        report['probe_journey_source_sha256'] = digest(Path(__file__).with_name('probe_journey.py'))
    control = ControlMailbox(output, journey=journey, keep_running=args.probe_keep_running, swapwait_cpu=args.swapwait_cpu_diagnostic, swapwait_profile=args.swapwait_cpu_profile) if args.control_mailbox else None
    if control:
        if control.swapwait_cpu:
            report['swapwait_cpu_observation'] = control.swapwait_cpu.report
        report['control_mailbox'] = str(control.path)
        if journey:
            report['probe_run_control'] = control.run_control
        else:
            report['observation_run_control'] = control.run_control
        report['control_source_sha256'] = digest(Path(__file__).with_name('qmp_control.py'))
    touch_trace = StartupTouchTrace(args.touch_trace_seconds if args.touch_trace_seconds is not None else 180) if args.touch_trace_startup else None
    if touch_trace:
        report['touch_startup_trace'] = touch_trace.report
        report['control_source_sha256'] = digest(Path(__file__).with_name('qmp_control.py'))
    refresh = HeadlessRefresh(output, args.headless_refresh_seconds) if args.headless_refresh_seconds else None
    if refresh:
        report["headless_refresh"] = refresh.report
    process = qmp = connection = None
    serial_transport = None
    started = time.monotonic()
    previous_handlers = {}
    def interrupted(signum, frame):
        raise KeyboardInterrupt(f'Signal {signum}')
    try:
        for sig in (signal.SIGTERM, signal.SIGINT):
            previous_handlers[sig] = signal.signal(sig, interrupted)
        with tempfile.TemporaryDirectory(prefix='inferno-boot-') as tmp, \
                (output / 'stderr.log').open('wb') as stderr, \
                (output / 'stdout.log').open('wb') as stdout, \
                (refresh if refresh else nullcontext()):
            endpoint = str(Path(tmp) / 'qmp.sock')
            usb_address = str(usb_socket or Path(tmp) / 'absent-usb.sock').replace(',', ',,')
            command = [str(binary), '-machine', 't8030,kaslr-off=true,usb-conn-type=unix,usb-conn-addr=' + usb_address + ',trustcache=' + inputs['trustcache']['path'].replace(',', ',,'),
                       '-accel', 'tcg', '-smp', '2', '-m', '4G', '-S',
                       '-kernel', inputs['kernel']['path'], '-dtb', inputs['dtb']['path'],
                       '-initrd', inputs['ramdisk']['path'], '-append', BOOT_ARGS,
                       '-display', 'none', '-vnc', 'unix:' + str(Path(tmp) / 'vnc.sock'),
                       '-monitor', 'none', '-serial', 'file:' + str(output / 'serial.log'),
                       '-qmp', 'unix:' + endpoint + ',server=on,wait=off', '-no-reboot']
            if args.guest_hid_serial:
                serial_path = Path(tmp) / 'gesture-serial.sock'
                serial_transport = SerialGestureTransport(serial_path, output)
                report['serial_transport'] = serial_transport.report
                report['control_source_sha256'] = digest(Path(__file__).with_name('qmp_control.py'))
                serial_index = command.index('-serial')
                command[serial_index:serial_index + 2] = [
                    '-chardev', 'socket,id=gesture-serial,path=' + str(serial_path).replace(',', ',,') +
                    ',server=on,wait=off,logfile=' + str(output / 'serial.log').replace(',', ',,') +
                    ',logappend=off,logtimestamp=off', '-serial', 'chardev:gesture-serial']
            if args.swapwait_cpu_diagnostic:
                command += ['-dfilter', SWAPWAIT_PROFILES[args.swapwait_cpu_profile]]
                report['swapwait_cpu_diagnostic'] = {'profile': args.swapwait_cpu_profile, 'filter': SWAPWAIT_PROFILES[args.swapwait_cpu_profile], 'initial_mask': 'guest_errors', 'automatic_enable': False}
            if args.guest_errors:
                command += ['-d', 'guest_errors', '-D', str(output / 'guest-errors.log')]
            if args.touch_trace_startup and not args.guest_errors:
                command += ['-D', str(output / 'touch-trace.log')]
            if args.disk_boot or args.ramdisk_boot:
                command[2] += ',boot-mode=exit_recovery'
            if args.ramdisk_boot:
                command[command.index('-append') + 1] = 'rd=md0 ' + BOOT_ARGS
            if args.recovery_preserve_disk:
                command[command.index('-append') + 1] = 'nand-enable-reformat=0 ' + BOOT_ARGS
            if args.disk_boot:
                index = command.index('-initrd')
                del command[index:index + 2]
            if args.launchd_unsecure_cache:
                command[command.index('-append') + 1] += ' launchd_unsecure_cache=1'
                report['launchd_unsecure_cache'] = True
            disk_dir = output / 'disks'
            disk_dir.mkdir()
            for nsid, (name, size, nstype) in enumerate(DISKS, 1):
                use_overlay = name == 'root' and bool(args.root_overlay or overlay_chain)
                disk_format = 'qcow2' if use_overlay else 'raw'
                disk = disk_dir / (name + ('.qcow2' if use_overlay else '.raw'))
                if use_overlay:
                    if overlay_chain:
                        report['root_overlay'] = create_recorded_overlay(disk, Path(overlay_chain['report']), overlay_tool)
                        if (report['root_overlay']['backing_report_sha256'] != overlay_chain['report_sha256'] or
                                report['root_overlay']['stopped_manifest_sha256'] != overlay_chain['stopped_manifest_sha256']):
                            raise ValueError('Overlay source report changed after initial validation')
                    else:
                        report['root_overlay'] = create_overlay(disk, root_image, args.root_sha256, overlay_tool)
                    (output / 'root-overlay.json').write_text(json.dumps(report['root_overlay'], indent=2) + '\n')
                    size = report['root_overlay']['image_info']['virtual-size']
                elif name == 'root' and root_image:
                    subprocess.run(['cp', '--reflink=auto', '--sparse=always', '--',
                                    str(root_image), str(disk)], check=True)
                    size = disk.stat().st_size
                elif name in auxiliary:
                    # Reserve only a new private destination; cp otherwise inherits
                    # a frozen source's read-only mode and QEMU cannot open it.
                    with disk.open('xb'):
                        pass
                    subprocess.run(['cp', '--reflink=auto', '--sparse=always', '--',
                                    auxiliary[name]['path'], str(disk)], check=True)
                    if digest(disk) != auxiliary[name]['sha256']:
                        raise ValueError(f'Auxiliary namespace {name} changed during copy')
                    disk.chmod(0o600)
                else:
                    with disk.open('xb') as handle:
                        handle.truncate(size)
                initial = 'private copy of hash-verified root base' if name == 'root' and root_image else 'fresh sparse zero-filled raw'
                if use_overlay:
                    initial = 'private qcow2 overlay over retained hash-verified read-only backing'
                if name in auxiliary:
                    initial = 'private copy of recorded auxiliary namespace'
                report['disks'].append({'path': str(disk), 'initial_state': initial,
                                        'bytes': size, 'format': disk_format, 'nsid': nsid, 'nstype': nstype})
                if name in auxiliary:
                    report['disks'][-1]['private_copy_mode'] = oct(disk.stat().st_mode & 0o777)
                device = 'apple-nvram' if name == 'nvram' else 'nvme-ns'
                device_id = ',id=nvram' if name == 'nvram' else ''
                command += ['-drive', f'file={str(disk).replace(",", ",,")},format={disk_format},if=none,id={name}',
                            '-device', f'{device},drive={name},bus=nvme-bus.0,nsid={nsid},nstype={nstype}{device_id},logical_block_size=4096,physical_block_size=4096']
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
            for name in ('qmp_capabilities', 'query-status', 'query-cpus-fast', 'query-mice'):
                response = qmp.execute(name, timeout=max(.1, min(30, deadline - time.monotonic())))
                if 'error' in response:
                    raise RuntimeError(f'QMP {name} failed: {response["error"]}')
            if serial_transport:
                serial_transport.connect()
                control.serial_transport = serial_transport
            if touch_trace:
                touch_trace.start(qmp)
                (output / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
            continued = qmp.execute('cont')
            if 'error' in continued:
                raise RuntimeError(f'QMP cont failed: {continued}')
            if refresh:
                refresh.start(Path(tmp) / 'vnc.sock')
            next_capture = time.monotonic() + args.capture_interval
            if args.capture_interval:
                (output / 'frames').mkdir()
                report['periodic_captures'] = []
            while time.monotonic() < deadline and process.poll() is None:
                if refresh:
                    refresh.poll()
                    if refresh.report.get("error"):
                        raise RuntimeError("Headless refresh failed: " + refresh.report["error"])
                if touch_trace:
                    touch_trace.poll(qmp)
                if control:
                    control.poll(qmp)
                    if journey is None and control.run_control['finish_requested']:
                        break
                if args.capture_interval and time.monotonic() >= next_capture:
                    captures = report['periodic_captures']
                    frame = output / 'frames' / f'{len(captures):04d}.ppm'
                    captured = qmp.execute('screendump', {'filename': str(frame)})
                    if 'error' in captured or not frame.is_file():
                        raise RuntimeError(f'Periodic framebuffer capture failed: {captured}')
                    captures.append({'elapsed_seconds': round(time.monotonic() - started, 3),
                                     'path': str(frame), 'sha256': digest(frame)})
                    next_capture = time.monotonic() + args.capture_interval
                if journey:
                    journey.poll(qmp, time.monotonic())
                    if probe_should_stop(journey, control):
                        break
                time.sleep(min(.2, max(0, deadline - time.monotonic())))
            if process.poll() is not None:
                raise RuntimeError('Emulator exited during boot attempt; see serial.log and stderr.log')
            if journey:
                journey.finish()
            for name in ('query-status', 'query-cpus-fast'):
                report['observations'].append(qmp.execute(name))
            screenshot = qmp.execute('screendump', {'filename': str(output / 'framebuffer.ppm')})
            report['screendump'] = screenshot
            report['framebuffer_captured'] = 'return' in screenshot and (output / 'framebuffer.ppm').is_file()
            if report['framebuffer_captured']:
                report['framebuffer_sha256'] = digest(output / 'framebuffer.ppm')
            report['attempt_completed'] = True
        if refresh and (refresh.report.get('error') or refresh.report.get('cleanup_errors')
                        or refresh.report.get('cleanup_error')):
            report['attempt_completed'] = False
            raise RuntimeError('Headless refresh failed; see headless_refresh lifecycle diagnostics')
    except (Exception, KeyboardInterrupt) as exc:
        report['error'] = {'type': type(exc).__name__, 'detail': str(exc)}
    finally:
        if process is not None and process.poll() is None:
            try:
                if qmp:
                    if control:
                        try:
                            control.close(qmp)
                        except Exception as exc:
                            report['display_trace_cleanup_error'] = str(exc)  # legacy aggregate key
                            report['control_cleanup_error'] = str(exc)
                            if control.swapwait_cpu and control.swapwait_cpu.pending:
                                report['swapwait_cpu_cleanup_error'] = str(exc)
                    if touch_trace:
                        try:
                            touch_trace.stop(qmp, 'runner cleanup')
                        except Exception as exc:
                            report['touch_trace_cleanup_error'] = str(exc)
                    capture_final_frame(qmp, output, report)
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
        if serial_transport:
            serial_transport.close()
        if connection:
            connection.close()
        if process:
            report['exit_code'] = process.returncode
        for sig, handler in previous_handlers.items():
            signal.signal(sig, handler)
        if report.get('root_overlay'):
            try:
                report['root_overlay']['backing_after_stop'] = verify_backing(report['root_overlay'])
            except Exception as exc:
                report['root_overlay']['backing_after_stop'] = {'unchanged': False, 'error': str(exc)}
                report['attempt_completed'] = False
                report.setdefault('error', {'type': type(exc).__name__, 'detail': str(exc)})
            (output / 'root-overlay.json').write_text(json.dumps(report['root_overlay'], indent=2) + '\n')
        report['elapsed_seconds'] = round(time.monotonic() - started, 6)
        serial = output / 'serial.log'
        report['serial_bytes'] = serial.stat().st_size if serial.exists() else 0
        report['observed_milestones'] = observe_milestones(output, report)
        for key in ('ios_booted', 'app_executed', 'milestones'):
            report[key] = report['observed_milestones'][key]
        (output / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'attempt_completed': report['attempt_completed'], 'ios_booted': report['ios_booted'],
                      'app_executed': report['app_executed'],
                      'milestones': {key: value['state'] for key, value in report['milestones'].items()},
                      'report': str(output / 'report.json')}))
    return 0 if report['attempt_completed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
