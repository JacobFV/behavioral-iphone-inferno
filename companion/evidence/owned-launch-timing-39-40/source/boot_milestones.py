"""Conservative observations from retained guest output; never a visual verifier."""
# SPDX-License-Identifier: AGPL-3.0-or-later
import hashlib
from pathlib import Path
import re

UUID = rb'[0-9A-Fa-f-]{36}'
READY = re.compile(rb'INFERNO_EVENT_RELAY_READY boot=(' + UUID + rb') .*transport=tcp address=127\.0\.0\.1 port=37373 .*')
RAW = re.compile(rb'INFERNO_EVENT_RELAY_RAW source=guest-loopback record=INFERNO_EVENT_V1 (' + UUID + rb') ([0-9]+) ([0-9]+) (main|appeared|tap) ([0-9]+)')
VALID = re.compile(rb'INFERNO_EVENT_RELAY_RECORD boot=(' + UUID + rb') pid=([0-9]+) sequence=([0-9]+) source=guest-loopback claimed_pid_verified=1 peer_pid_authenticated=0')


def unestablished():
    return {'state': 'unestablished', 'evidence': []}


def observe(output, report):
    output = Path(output)
    names = ('kernel_serial', 'launchd_userland', 'owned_app_lifecycle', 'strict_owned_journey')
    result = {'schema': 'inferno.boot-observations.v1',
              'scope': 'Retained serial/control observations, not automated visual verification or arbitrary-app compatibility.',
              'ios_booted': None, 'app_executed': None,
              'ios_booted_note': 'Deprecated ambiguous alias; consult granular milestones. Recovery userland is not installed-system readiness.',
              'milestones': {name: unestablished() for name in names}}
    serial = output / 'serial.log'
    try:
        if serial.stat().st_size > 64 * 1024 * 1024:
            raise ValueError('Serial exceeds bounded 64 MiB observation limit')
        data = serial.read_bytes()
    except (OSError, ValueError) as exc:
        result['observation_error'] = str(exc)
        return result
    serial_hash = hashlib.sha256(data).hexdigest()
    result['serial'] = {'path': str(serial), 'sha256': serial_hash, 'bytes': len(data)}
    ready, raw, validated, markers = {}, {}, {}, {}
    offset = 0
    for line_number, line in enumerate(data.splitlines(keepends=True), 1):
        body = line.rstrip(b'\r\n')
        ref = {'path': str(serial), 'sha256': serial_hash, 'byte_start': offset,
               'byte_end': offset + len(line), 'line': line_number,
               'text': body.decode('utf-8', errors='replace')}
        offset += len(line)
        if b'Darwin Kernel Version ' in body or body == b'corecrypto_kext_start called':
            result['milestones']['kernel_serial'] = {'state': 'observed', 'evidence': [ref],
                'scope': 'Original kernel/kext diagnostic text; not boot completion.'}
        if b'com.apple.xpc.launchd[1]' in body and b'Early boot complete. Continuing system boot.' in body:
            result['milestones']['launchd_userland'] = {'state': 'observed', 'evidence': [ref],
                'scope': report.get('kind', 'unspecified guest attempt')}
        match = READY.fullmatch(body)
        if match:
            ready[match[1]] = ref
        match = RAW.fullmatch(body)
        if match:
            boot, pid, sequence, event, count = match.groups()
            raw[(boot, pid, sequence)] = (event, count, ref)
        match = VALID.fullmatch(body)
        if match:
            validated[match.groups()] = ref
        for event, count in ((b'main', b'0'), (b'appeared', b'0'), (b'tap', b'1')):
            if body == b'INFERNO_UIKIT_PROBE_V1 event=' + event + b' count=' + count:
                markers.setdefault(event, []).append(ref)
    chains = []
    for key, (event, count, raw_ref) in raw.items():
        boot, pid, sequence = key
        valid_ref = validated.get(key)
        if boot not in ready or valid_ref is None or ready[boot]['byte_start'] > raw_ref['byte_start']:
            continue
        if valid_ref['byte_start'] < raw_ref['byte_end']:
            continue
        marker = next((ref for ref in markers.get(event, [])
                       if valid_ref['byte_end'] <= ref['byte_start'] < valid_ref['byte_end'] + 1024), None)
        if marker and count == (b'1' if event == b'tap' else b'0'):
            chains.append((boot, pid, int(sequence), event, [raw_ref, valid_ref, marker]))
    main = next((item for item in chains if item[2] == 1 and item[3] == b'main'), None)
    appeared = next((item for item in chains if main and item[:2] == main[:2]
                     and item[2] > main[2] and item[3] == b'appeared'), None)
    if not (main and appeared):
        return result
    result['app_executed'] = True
    result['milestones']['owned_app_lifecycle'] = {
        'state': 'observed', 'scope': 'Owned fixture main and appeared through validated loopback records only.',
        'boot_uuid': main[0].decode(), 'pid': int(main[1]),
        'peer_pid_authenticated': False, 'evidence': [ready[main[0]]] + main[4] + appeared[4]}
    tapped = next((item for item in chains if item[:2] == main[:2]
                   and item[2] > appeared[2] and item[3] == b'tap'), None)
    journey = report.get('probe_journey') or {}
    strict = result['milestones']['strict_owned_journey']
    strict['automated_visual_verification'] = False
    strict['visual_review'] = 'Operator review remains required; frame hashes do not interpret pixels.'
    if not (tapped and journey.get('completed')):
        return result
    mode = journey.get('input_mode')
    if mode == 'operator-observation' and not (journey.get('before_capture_operator_requested')
                                              and journey.get('after_capture_operator_requested')):
        return result
    if mode not in ('operator-observation', 'automatic-hardware-tap'):
        return result
    frames = []
    try:
        for label in ('probe-before', 'probe-after'):
            capture = journey.get('captures', {}).get(label, {})
            path = output / (label + '.ppm')
            if Path(capture.get('path', '')).resolve() != path.resolve():
                raise ValueError('Capture path does not match this report directory')
            with path.open('rb') as stream:
                actual = hashlib.file_digest(stream, 'sha256').hexdigest()
            if actual != capture.get('sha256'):
                raise ValueError('Capture hash mismatch')
            frames.append({'path': str(path), 'sha256': actual, 'role': label})
    except (OSError, ValueError) as exc:
        strict['evidence_error'] = str(exc)
        return result
    strict.update(state='observed', input_mode=mode, evidence=appeared[4] + tapped[4],
                  frames=frames, operator_capture_requests_recorded=(mode == 'operator-observation'))
    return result
