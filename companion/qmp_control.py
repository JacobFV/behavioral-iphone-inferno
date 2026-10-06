#!/usr/bin/env python3
"""Private, allowlisted input diagnostics through the boot runner's sole QMP owner."""
# SPDX-License-Identifier: AGPL-3.0-or-later
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat
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
LIMIT = 4096


def validate(request):
    if not isinstance(request, dict) or set(request) != {'execute', 'arguments', 'created'}:
        raise ValueError('Expected execute, arguments and created only')
    created = request['created']
    if type(created) not in (int, float) or not 0 <= time.time() - created <= 30:
        raise ValueError('Request must be created within the past 30 seconds')
    name, args = request['execute'], request['arguments']
    if not isinstance(args, dict):
        raise ValueError('Arguments must be an object')
    if name in ('query-mice', 'query-touch-registers') and args == {}:
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


class ControlMailbox:
    def __init__(self, output):
        self.path = output / 'control'
        self.path.mkdir(mode=0o700)
        self.journal = output / 'control-transcript.jsonl'
        self.journal.touch(mode=0o600, exist_ok=False)

    def poll(self, qmp):
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
                if name == 'query-touch-registers':
                    response = {'registers': [
                        {'address': hex(address), 'response': qmp.execute(
                            'human-monitor-command', {'command-line': f'xp /1wx 0x{address:x}'})}
                        for address in TOUCH_REGISTERS]}
                else:
                    response = qmp.execute(name, args)
                record['response'] = response
            except (OSError, ValueError, TypeError, KeyError) as exc:
                response = {'rejected': str(exc)}
                record['response'] = response
            with self.journal.open('a') as journal:
                journal.write(json.dumps(record) + '\n')
            write_private(self.path / path.name.replace('request-', 'reply-', 1), response)
            path.unlink()


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
    parser.add_argument('command', choices=['query-mice', 'query-touch-registers', 'trace-event-get-state', 'trace-event-set-state', 'input-send-event'])
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
