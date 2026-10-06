#!/usr/bin/env python3
"""Derive guest launch-hook intervals from exact original timing relay logs.
SPDX-License-Identifier: AGPL-3.0-or-later
No host-arrival, native-device, warm-launch or cache-clearing timing claim.
"""
import argparse
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import re

UUID = r'[0-9A-Fa-f]{8}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{12}'
NUM = r'[0-9]+'
HOOKS = {'main', 'launch-delegate', 'window-request', 'appeared', 'active'}
RAW = re.compile(rf'INFERNO_TIMING_RELAY_RAW source=guest-loopback record=INFERNO_TIMING_V1 ({UUID}) ({NUM}) ({NUM}) ([a-z-]+) ({NUM}) ({NUM}) ({NUM})')
VALIDATED = re.compile(rf'INFERNO_TIMING_RELAY_RECORD boot=({UUID}) pid=({NUM}) sequence=({NUM}) hook=([a-z-]+) ticks=({NUM}) numer=({NUM}) denom=({NUM}) complete=([01]) source=guest-loopback claimed_pid_verified=1 peer_pid_authenticated=0')
LAUNCH = re.compile(rf'INFERNO_LAUNCH_TIMING_V1 boot=({UUID}) pid=({NUM}) attempt=({NUM}) request_ticks=({NUM}) callback_ticks=({NUM}) numer=({NUM}) denom=({NUM}) accepted=([01])')
LIFE = re.compile(rf'INFERNO_EVENT_RELAY_RAW source=guest-loopback record=INFERNO_EVENT_V1 ({UUID}) ({NUM}) ({NUM}) ([a-z-]+) ({NUM})')
LIFE_VALIDATED = re.compile(rf'INFERNO_EVENT_RELAY_RECORD boot=({UUID}) pid=({NUM}) sequence=({NUM}) source=guest-loopback claimed_pid_verified=1 peer_pid_authenticated=0')
LIMIT = 16 * 1024 * 1024

class TimingError(ValueError):
    pass

def require(condition, message):
    if not condition:
        raise TimingError(message)

def sha(data):
    return hashlib.sha256(data).hexdigest()

def integer(value, maximum, label):
    require(len(value) <= 20, f'{label} is oversized')
    result = int(value)
    require(0 < result <= maximum, f'{label} is out of range')
    return result

def parse(data):
    require(len(data) <= LIMIT, 'Serial log exceeds 16 MiB parser bound')
    groups = {key: [] for key in ('timing', 'validated', 'launcher', 'lifecycle', 'lifecycle_validated')}
    patterns = [('INFERNO_TIMING_RELAY_RAW', RAW, 'timing'),
                ('INFERNO_TIMING_RELAY_RECORD', VALIDATED, 'validated'),
                ('INFERNO_LAUNCH_TIMING_V1', LAUNCH, 'launcher'),
                ('INFERNO_EVENT_RELAY_RAW', LIFE, 'lifecycle'),
                ('INFERNO_EVENT_RELAY_RECORD', LIFE_VALIDATED, 'lifecycle_validated')]
    offset = 0
    for line_number, fragment in enumerate(data.split(b'\n'), 1):
        if not fragment and offset == len(data):
            break
        raw = fragment + (b'\n' if offset + len(fragment) < len(data) else b'')
        text = raw.rstrip(b'\r\n').decode('utf-8', errors='replace')
        for prefix, pattern, key in patterns:
            if not text.startswith(prefix):
                continue
            require(raw.endswith(b'\n'), f'Incomplete {prefix} line at byte {offset}')
            match = pattern.fullmatch(text)
            require(match is not None, f'Malformed {prefix} line at byte {offset}')
            groups[key].append({'fields': match.groups(), 'reference': {
                'line': line_number, 'byte_start': offset, 'byte_end': offset + len(raw),
                'sha256': sha(raw), 'text': text}})
        offset += len(raw)
    require(len(groups['timing']) == 5, f'Expected one complete five-hook sequence; found {len(groups["timing"])} timing records')
    require(len(groups['validated']) == 5, 'Expected exactly five validated timing provenance records')
    ticks = {}; records = []; identity = None; previous = 0
    for expected, item in enumerate(groups['timing'], 1):
        boot, pid, sequence, hook, tick, numer, denom = item['fields']
        pid = integer(pid, 2147483647, 'app PID'); sequence = integer(sequence, 5, 'sequence')
        tick = integer(tick, 2**64-1, 'ticks'); numer = integer(numer, 2**32-1, 'numer'); denom = integer(denom, 2**32-1, 'denom')
        require(sequence == expected, 'Timing sequence must be unique and consecutive in serial order')
        require(hook in HOOKS and hook not in ticks, 'Unknown or duplicate hook')
        require(expected != 1 or hook == 'main', 'First hook must be main')
        current = (boot, pid, numer, denom)
        if identity is None:
            identity = current
        require(current == identity, 'Mixed timing boot, app PID or timebase')
        require(tick >= previous, 'Hook ticks decrease'); previous = tick; ticks[hook] = tick
        matches = [entry for entry in groups['validated'] if entry['fields'][:7] == item['fields']]
        require(len(matches) == 1, 'Missing or ambiguous validated timing provenance')
        validated = matches[0]
        require(int(validated['fields'][7]) == (expected == 5), 'Inconsistent complete flag')
        require(validated['reference']['byte_start'] > item['reference']['byte_start'], 'Timing validation precedes raw record')
        records.append({'hook': hook, 'sequence': sequence, 'ticks': tick, 'raw': item['reference'], 'validated': validated['reference']})
    require(set(ticks) == HOOKS, 'Required timing hooks missing')
    boot, app_pid, numer, denom = identity
    accepted = []; launcher_keys = set(); rejected = []
    for entry in groups['launcher']:
        lb, lp, attempt, request, callback, ln, ld, ok = entry['fields']
        lp = integer(lp, 2147483647, 'launcher PID'); attempt = integer(attempt, 30, 'attempt')
        request = integer(request, 2**64-1, 'request ticks'); callback = integer(callback, 2**64-1, 'callback ticks')
        ln = integer(ln, 2**32-1, 'launcher numer'); ld = integer(ld, 2**32-1, 'launcher denom')
        require((lb, ln, ld) == (boot, numer, denom), 'Mixed launcher boot or timebase')
        require((lp, attempt) not in launcher_keys, 'Duplicate launcher attempt'); launcher_keys.add((lp, attempt))
        require(callback >= request, 'Launcher callback precedes request')
        item = {'launcher_pid': lp, 'attempt': attempt, 'request_ticks': request, 'callback_ticks': callback, 'reference': entry['reference']}
        (accepted if ok == '1' else rejected).append(item)
    require(len(accepted) == 1, f'Expected one unambiguous accepted launcher request; found {len(accepted)}')
    launcher = accepted[0]
    require(launcher['request_ticks'] <= ticks['main'], 'Accepted request occurs after main; cannot attribute launch')
    require(all(x['request_ticks'] < launcher['request_ticks'] for x in rejected), 'Additional launcher request after accepted request is ambiguous')
    lifecycle = []
    for hook in ('main', 'appeared', 'active'):
        matches = [x for x in groups['lifecycle'] if x['fields'][0] == boot and x['fields'][1] == str(app_pid) and x['fields'][3] == hook and x['fields'][4] == '0']
        require(bool(matches), f'Missing actual lifecycle {hook} for timed app PID')
        entry = matches[0]
        matches = [x for x in groups['lifecycle_validated'] if x['fields'] == entry['fields'][:3]]
        require(len(matches) == 1, f'Missing or ambiguous lifecycle provenance for {hook}')
        lifecycle.append({'hook': hook, 'raw': entry['reference'], 'validated': matches[0]['reference']})
    def interval(start, end):
        require(end >= start, 'Negative derived interval')
        ns = Fraction((end-start)*numer, denom)
        return {'delta_ticks': end-start, 'nanoseconds_numerator': ns.numerator,
                'nanoseconds_denominator': ns.denominator, 'milliseconds_approximate': float(ns/1000000)}
    return {'status': 'complete', 'boot_uuid': boot, 'app_pid': app_pid,
            'timebase': {'numer': numer, 'denom': denom}, 'hooks': records,
            'accepted_launcher': launcher, 'earlier_rejected_launcher_requests': rejected,
            'validated_lifecycle': lifecycle, 'intervals': {
                'request_to_main': interval(launcher['request_ticks'], ticks['main']),
                'main_to_appeared': interval(ticks['main'], ticks['appeared']),
                'main_to_active': interval(ticks['main'], ticks['active']),
                'request_to_callback': interval(launcher['request_ticks'], launcher['callback_ticks']),
                'request_to_active': interval(launcher['request_ticks'], ticks['active'])}}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(); source = args.report / 'serial.log'
    result = {'kind': 'owned_guest_launch_hook_timing', 'parser_sha256': sha(Path(__file__).read_bytes()),
              'limits': ['Guest emulated mach_absolute_time intervals, not native-device performance.',
                         'First observed owned app launch only; no warm/cleared-cache classification.',
                         'Host log arrival times are not substituted for captured hook ticks.',
                         'Relay verifies claimed app PID/UID/executable, not TCP peer authentication.',
                         'Launcher acknowledgement is not visual rendering completion.']}
    try:
        with source.open('rb') as stream:
            data = stream.read(LIMIT + 1)
        result['serial'] = {'path': str(source.resolve()), 'bytes_read': len(data), 'sha256': sha(data),
                            'hash_scope': 'full log' if len(data) <= LIMIT else 'bounded prefix only'}
        result.update(parse(data))
        code = 0
    except (OSError, TimingError) as exc:
        result.update(status='rejected', reason=str(exc)); code = 2
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'status': result['status'], 'output': str(args.output), 'reason': result.get('reason')}))
    return code

if __name__ == '__main__':
    raise SystemExit(main())
