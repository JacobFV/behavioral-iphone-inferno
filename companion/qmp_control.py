#!/usr/bin/env python3
"""Private, allowlisted input diagnostics through the boot runner's sole QMP owner."""
# SPDX-License-Identifier: AGPL-3.0-or-later
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import socket
import stat
import threading
import time
import uuid

TRACE_EVENTS = {
    'input_event_btn', 'input_event_abs', 'input_event_sync',
    'apple_mt_spi_host_event', 'apple_mt_spi_enqueue', 'apple_mt_spi_dequeue',
    'apple_mt_spi_tx_drained', 'apple_mt_spi_boot_command', 'apple_mt_spi_control',
}
TOUCH_TRACE_EVENTS = ('apple_mt_spi_host_event', 'apple_mt_spi_enqueue',
                      'apple_mt_spi_dequeue', 'apple_mt_spi_tx_drained',
                      'apple_mt_spi_boot_command', 'apple_mt_spi_control')
# Explicit read-only registers reviewed against the original device models. Never
# include SPI RXDATA (+0x20), which consumes data, or permit arbitrary addresses.
TOUCH_REGISTERS = (0x24a820088, 0x235104000, 0x235104004, 0x235104008,
                   0x23510400c, 0x235104034, 0x23510404c)
# Original N104 DT arm-io ranges[1]=0x200000000 plus disp0 reg[0]=0x30000000.
# Each selected read returns stored state only (apple_displaypipe_v4.c).
# Excludes submit register0x4602c, unimplemented registers and framebuffer/DMA data.
DISPLAY_BASE = 0x230000000
DISPLAY_REGISTERS = (
    ('int_status', 0x45818), ('int_enable', 0x4581c),
    ('version', 0x46020), ('frame_size', 0x4603c),
) + tuple((f'gp{pipe}_{name}', 0x50000 + pipe * 0x8000 + offset)
          for pipe in range(2)
          for name, offset in (('control', 0x4), ('pixel_format', 0x1c),
                               ('data_start', 0x30), ('data_end', 0x40),
                               ('stride', 0x60), ('src_dimensions', 0x70),
                               ('dest_dimensions', 0x80)))
DISPLAY_TRACE_EVENTS = ('apple_adp_submit', 'apple_adp_bh', 'apple_adp_pipe',
                        'apple_adp_output_ready', 'apple_adp_irq_write',
                        'apple_adp_unknown_mmio', 'apple_adp_gp_config_write')
LIMIT = 4096


def gesture_line(args):
    kind = args.get('kind')
    coordinates = ('x', 'y') if kind == 'tap' else ('x0', 'y0', 'x1', 'y1')
    if kind not in ('tap', 'swipe') or set(args) != {'kind', 'request_id', 'duration_ms', *coordinates}:
        raise ValueError('Gesture requires exact tap or swipe fields')
    identifier = args['request_id']
    if not isinstance(identifier, str) or not re.fullmatch('[0-9a-f]{32}', identifier):
        raise ValueError('Gesture request_id must be 32 lowercase hexadecimal characters')
    for field in coordinates:
        if type(args[field]) is not int or not 0 <= args[field] <= 32767:
            raise ValueError('Gesture coordinates must be integers from 0 to 32767')
    if type(args['duration_ms']) is not int or not 1 <= args['duration_ms'] <= 2000:
        raise ValueError('Gesture duration_ms must be an integer from 1 to 2000')
    fields = ['INFERNO_HID_V1', identifier, kind.upper()]
    fields += [str(args[field]) for field in coordinates]
    fields.append(str(args['duration_ms']))
    line = (' '.join(fields) + '\n').encode('ascii')
    if len(line) > 160:
        raise ValueError('Gesture line exceeds 160 bytes')
    return line


def open_line(args):
    if set(args) != {'request_id', 'boot_uuid'}:
        raise ValueError('Owned OPEN requires exact request_id and boot_uuid fields')
    identifier, boot = args['request_id'], args['boot_uuid']
    if not isinstance(identifier, str) or not re.fullmatch('[0-9a-f]{32}', identifier):
        raise ValueError('OPEN request_id must be 32 lowercase hexadecimal characters')
    if not isinstance(boot, str) or not re.fullmatch(
            '[0-9A-Fa-f]{8}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{12}', boot):
        raise ValueError('OPEN boot_uuid must be the exact current 36-character boot UUID')
    return f'INFERNO_OPEN_V1 {identifier} {boot}\n'.encode('ascii')


def validate(request):
    if not isinstance(request, dict) or set(request) != {'execute', 'arguments', 'created'}:
        raise ValueError('Expected execute, arguments and created only')
    created = request['created']
    if type(created) not in (int, float) or not 0 <= time.time() - created <= 30:
        raise ValueError('Request must be created within the past 30 seconds')
    name, args = request['execute'], request['arguments']
    if not isinstance(args, dict):
        raise ValueError('Arguments must be an object')
    if name in ('query-mice', 'query-touch-registers', 'query-display-registers', 'probe-status', 'finish-run', 'probe-capture-before', 'probe-capture-after') and args == {}:
        return name, args
    if name == 'trace-display-window':
        if set(args) == {'seconds'} and type(args['seconds']) is int and 1 <= args['seconds'] <= 60:
            return name, args
        raise ValueError('Display trace requires only integer seconds from1 to60')
    if name == 'guest-open-app':
        open_line(args)
        return name, args
    if name == 'guest-hid-gesture':
        gesture_line(args)
        return name, args
    if name in ('trace-event-get-state', 'trace-event-set-state'):
        keys = {'name'} if name.endswith('get-state') else {'name', 'enable'}
        if set(args) == keys and args['name'] in TRACE_EVENTS:
            if 'enable' not in args or type(args['enable']) is bool:
                return name, args
    if name == 'input-send-event' and set(args) == {'events'}:
        events = args['events']
        if not isinstance(events, list) or not 1 <= len(events) <= 8:
            raise ValueError('One to eight pointer events required')
        for event in events:
            if not isinstance(event, dict) or set(event) != {'type', 'data'} or not isinstance(event['data'], dict):
                raise ValueError('Invalid pointer event')
            data = event['data']
            if event['type'] == 'abs' and set(data) == {'axis', 'value'}:
                if data['axis'] in ('x', 'y') and type(data['value']) is int and 0 <= data['value'] <= 32767:
                    continue
            if event['type'] == 'btn' and set(data) == {'button', 'down'}:
                if data['button'] == 'left' and type(data['down']) is bool:
                    continue
            raise ValueError('Only absolute x/y and left-button events are permitted')
        return name, args
    raise ValueError('Command or arguments are outside the input diagnostic allowlist')


def private_dir(path):
    info = path.lstat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) != 0o700:
        raise ValueError('Control directory must be owned by this user with mode 0700')


def read_private(path):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, 'rb') as handle:
        info = os.fstat(handle.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) != 0o600 or info.st_size > LIMIT:
            raise ValueError('Control JSON must be a regular owned mode-0600 file of at most 4096 bytes')
        raw = handle.read(LIMIT + 1)
        if len(raw) > LIMIT:
            raise ValueError('Control JSON exceeded 4096 bytes')
        return raw


def write_private(path, value):
    raw = (json.dumps(value, allow_nan=False) + '\n').encode()
    if len(raw) > LIMIT:
        raise ValueError('Control JSON exceeded 4096 bytes')
    temporary = path.with_suffix('.tmp')
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'wb') as handle:
        handle.write(raw)
    os.replace(temporary, path)


class DisplayTraceWindow:
    """Disabled by default; exact event set, sole-owner deadline and cleanup."""
    def __init__(self, output):
        self.journal = output / 'display-trace-control.jsonl'
        self.pending = []
        self.deadline = None

    def record(self, **fields):
        fd = os.open(self.journal, os.O_WRONLY | os.O_APPEND | os.O_CREAT | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, 'a') as log:
            log.write(json.dumps({'time': time.time(), 'monotonic_ns': time.monotonic_ns(), **fields}) + '\n')

    def start(self, qmp, seconds):
        if self.pending:
            raise ValueError('Display trace already active or cleanup incomplete; cannot extend/restart')
        self.deadline = time.monotonic() + seconds
        self.record(stage='start', seconds=seconds, events=list(DISPLAY_TRACE_EVENTS))
        try:
            for name in DISPLAY_TRACE_EVENTS:
                # Retain an uncertain enable for mandatory cleanup if execute raises.
                self.pending.append(name)
                self.record(stage='before-enable', event=name)
                response = qmp.execute('trace-event-set-state', {'name': name, 'enable': True})
                self.record(stage='after-enable', event=name, response=response)
                if 'error' in response:
                    self.pending.remove(name)  # explicit rejection, not an uncertain send
                    raise RuntimeError(f'Display trace event unavailable: {name}: {response}')
        except Exception:
            self.deadline = time.monotonic()
            self.stop(qmp, 'start failed')
            raise
        return {'seconds': seconds, 'events': list(DISPLAY_TRACE_EVENTS),
                'scope': 'Opt-in diagnostic tracing; deadline checked by sole runner poll; no guest behavior changes.'}

    def stop(self, qmp, reason):
        if not self.pending:
            return
        self.record(stage='stop', reason=reason, pending=list(self.pending))
        for name in list(self.pending):
            self.record(stage='before-disable', event=name)
            try:
                response = qmp.execute('trace-event-set-state', {'name': name, 'enable': False})
                self.record(stage='after-disable', event=name, response=response)
                if 'error' not in response:
                    self.pending.remove(name)
            except Exception as exc:
                self.record(stage='disable-error', event=name, error=str(exc))
        self.record(stage='stop-result', reason=reason, all_disabled=not self.pending,
                    pending=list(self.pending))
        if self.pending:
            raise RuntimeError('Display trace cleanup incomplete: ' + ','.join(self.pending))

    def poll(self, qmp):
        if self.pending and time.monotonic() >= self.deadline:
            self.stop(qmp, 'deadline')


class ControlMailbox:
    def __init__(self, output, journey=None, keep_running=False):
        self.path = output / 'control'
        self.path.mkdir(mode=0o700)
        self.journal = output / 'control-transcript.jsonl'
        self.journal.touch(mode=0o600, exist_ok=False)
        self.serial_transport = None
        self.journey = journey
        self.run_control = {'keep_running': keep_running, 'finish_requested': False}
        self.display_trace = DisplayTraceWindow(output)

    def close(self, qmp):
        # Runner calls before quit; propagate cleanup error for its report, not a retry loop.
        self.display_trace.stop(qmp, 'runner cleanup')

    def poll(self, qmp):
        self.display_trace.poll(qmp)
        private_dir(self.path)
        for path in sorted(self.path.glob('request-*.json'))[:4]:
            if not re.fullmatch(r'request-[0-9a-f]{32}\.json', path.name):
                continue
            record = {'time': time.time(), 'request_file': path.name}
            try:
                raw = read_private(path)
                record.update(raw=raw.decode('utf-8', errors='replace'), sha256=hashlib.sha256(raw).hexdigest())
                request = json.loads(raw)
                name, args = validate(request)
                if name == 'trace-display-window':
                    response = {'return': self.display_trace.start(qmp, args['seconds'])}
                elif name == 'probe-status':
                    if self.journey is None:
                        raise ValueError('This boot did not enable --probe-journey')
                    response = {'return': {**self.journey.report, **self.run_control}}
                    encoded = json.dumps(response, allow_nan=False) + '\n'
                    if len(encoded.encode()) > LIMIT:
                        raise ValueError('Probe status exceeded 4096 bytes')
                    response = json.loads(encoded)
                elif name == 'finish-run':
                    if not self.run_control['keep_running'] or self.journey is None:
                        raise ValueError('finish-run requires --probe-keep-running')
                    if not self.journey.report['completed']:
                        raise ValueError('finish-run requires a completed probe journey')
                    self.run_control['finish_requested'] = True
                    response = {'return': dict(self.run_control)}
                elif name in ('probe-capture-before', 'probe-capture-after'):
                    if self.journey is None:
                        raise ValueError('This boot did not enable --probe-journey')
                    capture = (self.journey.operator_capture_before if name == 'probe-capture-before'
                               else self.journey.operator_capture_after)
                    response = {'return': capture(qmp)}
                elif name == 'guest-open-app':
                    if self.serial_transport is None:
                        raise ValueError('This boot did not enable --guest-hid-serial')
                    response = self.serial_transport.transmit_open(args)
                elif name == 'guest-hid-gesture':
                    if self.serial_transport is None:
                        raise ValueError('This boot did not enable --guest-hid-serial')
                    response = self.serial_transport.transmit(args)
                elif name == 'query-display-registers':
                    started = time.monotonic_ns()
                    response = {'registers': [
                        {'name': label, 'address': hex(DISPLAY_BASE + offset),
                         'response': qmp.execute('human-monitor-command', {
                             'command-line': f'xp /1wx 0x{DISPLAY_BASE + offset:x}'})}
                        for label, offset in DISPLAY_REGISTERS],
                        'start_monotonic_ns': started,
                        'end_monotonic_ns': time.monotonic_ns(),
                        'scope': 'Fixed nonconsuming ADP reads; sequential, not atomic; no framebuffer contents.'}
                elif name == 'query-touch-registers':
                    response = {'registers': [
                        {'address': hex(address), 'response': qmp.execute(
                            'human-monitor-command', {'command-line': f'xp /1wx 0x{address:x}'})}
                        for address in TOUCH_REGISTERS]}
                else:
                    response = qmp.execute(name, args)
                record['response'] = response
            except (OSError, ValueError, TypeError, KeyError, RuntimeError) as exc:
                response = {'rejected': str(exc)}
                record['response'] = response
            with self.journal.open('a') as journal:
                journal.write(json.dumps(record) + '\n')
            write_private(self.path / path.name.replace('request-', 'reply-', 1), response)
            path.unlink()


class SerialGestureTransport:
    """Own and continuously drain a private serial socket; never interpret UI success."""
    def __init__(self, path, output):
        self.path = path
        self.connection = None
        self.thread = None
        self.stopping = threading.Event()
        self.seen = set()
        self.open_attempts = 0
        self.report = {'endpoint': str(path), 'connected': False, 'drained_bytes': 0,
                       'transmissions': [], 'automatic_replay': False}
        self.journal = output / 'serial-input-transcript.jsonl'
        self.journal.touch(mode=0o600, exist_ok=False)

    def connect(self):
        private_dir(self.path.parent)
        info = self.path.lstat()
        if not stat.S_ISSOCK(info.st_mode) or info.st_uid != os.getuid():
            raise ValueError('Serial endpoint must be an owned Unix socket')
        self.path.chmod(0o600)
        self.connection = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.connection.settimeout(1)
        self.connection.connect(str(self.path))
        self.report.update(connected=True, connected_time=time.time())
        self.thread = threading.Thread(target=self._drain, name='inferno-serial-drain', daemon=True)
        self.thread.start()

    def _drain(self):
        while not self.stopping.is_set():
            try:
                data = self.connection.recv(65536)
                if not data:
                    self.report['peer_closed'] = True
                    return
                # QEMU's logfile retains the exact output. Draining prevents its
                # UART write_all path from stalling on a full socket buffer.
                self.report['drained_bytes'] += len(data)
            except socket.timeout:
                continue
            except OSError as exc:
                if not self.stopping.is_set():
                    self.report['drain_error'] = str(exc)
                return

    def _record(self, record):
        with self.journal.open('a') as journal:
            journal.write(json.dumps(record) + '\n')

    def transmit(self, args):
        return self._transmit(gesture_line(args), args['request_id'], 'HID')

    def transmit_open(self, args):
        return self._transmit(open_line(args), args['request_id'], 'OPEN')

    def _transmit(self, line, identifier, operation):
        if identifier in self.seen:
            raise ValueError('Duplicate serial request ID; never replay a possibly transmitted request')
        if not self.report['connected'] or self.stopping.is_set() or not self.thread.is_alive():
            raise ValueError('Serial transport is not connected and draining')
        if operation == 'OPEN':
            if self.open_attempts >= 8:
                raise ValueError('At most eight explicit OPEN attempts are allowed per run')
            self.open_attempts += 1
        self.seen.add(identifier)
        attempt = {'time': time.time(), 'stage': 'before-send', 'request_id': identifier, 'operation': operation,
                   'raw': line.decode('ascii'), 'sha256': hashlib.sha256(line).hexdigest()}
        self._record(attempt)
        result = {'request_id': identifier, 'guest_acknowledgment': 'not checked',
                  'ui_acceptance': 'not observed by transport'}
        try:
            self.connection.sendall(line)
            result.update(transmission='written-to-serial-socket', bytes_sent=len(line))
        except OSError as exc:
            result.update(transmission='unknown-or-partial', error=str(exc), replay_allowed=False)
        self._record({'time': time.time(), 'stage': 'after-send', 'response': result})
        self.report['transmissions'].append(result)
        return result

    def close(self):
        self.stopping.set()
        if self.connection:
            try:
                self.connection.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            self.connection.close()
        if self.thread:
            self.thread.join(timeout=2)
            self.report['drain_thread_stopped'] = not self.thread.is_alive()
        self.report['closed_time'] = time.time()


class StartupTouchTrace:
    """Six explicit touch tracepoints with a bounded automatic disable deadline."""
    def __init__(self, seconds=180):
        if type(seconds) is not int or not 1 <= seconds <= 1800:
            raise ValueError('Touch trace seconds must be an integer from 1 to 1800')
        self.seconds = seconds
        self.report = {'limit_seconds': seconds, 'events': list(TOUCH_TRACE_EVENTS),
                       'enable_results': [], 'disable_results': []}
        self.active = []
        self.deadline = None

    def start(self, qmp):
        self.deadline = time.monotonic() + self.seconds
        self.report.update(start_time=time.time(), deadline_time=time.time() + self.seconds)
        for name in TOUCH_TRACE_EVENTS:
            result = qmp.execute('trace-event-set-state', {'name': name, 'enable': True})
            self.report['enable_results'].append({'name': name, 'response': result})
            if 'error' in result:
                raise RuntimeError(f'Touch startup trace unavailable: {name}: {result}')
            self.active.append(name)

    def poll(self, qmp):
        if self.active and time.monotonic() >= self.deadline:
            self.stop(qmp, f'{self.seconds}-second deadline')

    def stop(self, qmp, reason):
        if not self.active:
            return
        for name in list(self.active):
            result = qmp.execute('trace-event-set-state', {'name': name, 'enable': False})
            self.report['disable_results'].append({'name': name, 'response': result})
            if 'error' not in result:
                self.active.remove(name)
        self.report.update(stop_time=time.time(), stop_reason=reason,
                           all_disabled=not self.active)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report', type=Path, required=True, help='Active boot output directory with --control-mailbox')
    parser.add_argument('command', choices=['probe-status', 'finish-run', 'probe-capture-before', 'probe-capture-after', 'query-mice', 'query-touch-registers', 'query-display-registers', 'trace-display-window', 'trace-event-get-state', 'trace-event-set-state', 'input-send-event', 'guest-hid-gesture', 'guest-open-app'])
    parser.add_argument('--arguments', default='{}', help='Allowlisted QMP arguments as JSON')
    args = parser.parse_args()
    directory = args.report.resolve(strict=True) / 'control'
    private_dir(directory)
    request = {'execute': args.command, 'arguments': json.loads(args.arguments), 'created': time.time()}
    validate(request)
    token = uuid.uuid4().hex
    write_private(directory / ('request-' + token + '.json'), request)
    reply = directory / ('reply-' + token + '.json')
    deadline = time.monotonic() + 35
    while time.monotonic() < deadline:
        if reply.exists():
            response = json.loads(read_private(reply))
            print(json.dumps(response))
            return 1 if ('error' in response or 'rejected' in response or
                         any('error' in x['response'] for x in response.get('registers', []))) else 0
        time.sleep(.1)
    raise SystemExit('No reply within 35 seconds; retained request may expire without execution')


if __name__ == '__main__':
    raise SystemExit(main())
