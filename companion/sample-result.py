#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Reconstruct one explicitly identified guest SAMPLE result without submitting input."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess

ID = r'[0-9a-f]{32}'
UUID = r'[0-9A-Fa-f]{8}(?:-[0-9A-Fa-f]{4}){3}-[0-9A-Fa-f]{12}'
TARGET = r'(?:SPRINGBOARD|BACKBOARDD)'
SCHEMAS = {
    'REQUEST': [('request_id', ID), ('boot', UUID), ('target', TARGET), ('pid', r'-?\d+'),
                ('resolve_errno', r'\d+'), ('guest_ticks', r'\d+')],
    'BEGIN': [('request_id', ID), ('target', TARGET), ('pid', r'\d+'), ('uid', '501'),
              ('unique', r'\d+'), ('idversion', r'-?\d+'), ('output_cap', '262144'),
              ('guest_deadline_seconds', '60'), ('original_tool', '/usr/sbin/spindump'), ('target_signals', '0')],
    'DATA': [('request_id', ID), ('offset', r'\d+'), ('bytes', r'\d+'), ('hex', r'[0-9a-f]+')],
    'END': [('request_id', ID), ('boot', UUID), ('target', TARGET), ('pid', r'\d+'),
            ('unique', r'\d+'), ('idversion', r'-?\d+'), ('bytes', r'\d+'), ('chunks', r'\d+'),
            ('eof', '[01]'), ('truncated', '[01]'), ('read_errno', r'\d+'),
            ('output_error', '[01]'), ('reaped', '[01]'), ('raw_status', r'-?\d+'),
            ('wait_errno', r'\d+'), ('killed', '[01]'), ('target_post_match', '[01]'),
            ('complete', '[01]'), ('guest_ticks', r'\d+'), ('pid_reuse_atomicity', 'unproven')],
}
PATTERNS = {kind: re.compile('INFERNO_SAMPLE_' + kind + ' ' + ' '.join(
    re.escape(key) + '=(?P<' + key + '>' + expression + ')' for key, expression in fields))
    for kind, fields in SCHEMAS.items()}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def reconstruct(data, request):
    records = []
    decoded = bytearray()
    result = {'transport_complete': False, 'output_usefulness': 'not_assessed', 'records': records}
    try:
        offset = 0
        for line in data.split(b'\n'):
            if offset == len(data):
                break
            terminated = offset + len(line) < len(data)
            raw = line + (b'\n' if terminated else b'')
            text = line.rstrip(b'\r').decode('ascii', errors='replace')
            ref = {'byte_start': offset, 'byte_end': offset + len(raw), 'sha256': sha(raw), 'text': text}
            offset += len(raw)
            if 'INFERNO_SAMPLE_' not in text or ('request_id=' + request['request_id']) not in text:
                continue
            records.append({'reference': ref})
            if not terminated:
                records[-1]['invalid'] = 'selected record lacks physical LF terminator'
            matches = [(kind, pattern.fullmatch(text)) for kind, pattern in PATTERNS.items()]
            matches = [(kind, match) for kind, match in matches if match]
            if len(matches) != 1:
                records[-1]['invalid'] = 'selected record malformed, prefixed or failure/stop record'
                continue
            kind, match = matches[0]
            fields = match.groupdict()
            require(fields['request_id'] == request['request_id'], 'request identity differs')
            records[-1].update(kind=kind, fields=fields)
        require(len(records) >= 2, 'missing REQUEST or BEGIN')
        require([r.get('kind') for r in records[:2]] == ['REQUEST','BEGIN'] and
                not any(r.get('invalid') for r in records[:2]), 'missing, malformed or duplicate initial REQUEST/BEGIN')
        req, begin = [records[i]['fields'] for i in (0, 1)]
        for fields in (req, begin):
            require(fields['target'] == request['target'], 'mixed target')
        require(req['boot'] == request['boot_uuid'], 'mixed boot UUID')
        require(int(req['pid']) > 0 and req['pid'] == begin['pid'], 'invalid or mixed target PID')
        require(int(begin['unique']) > 0, 'invalid target incarnation')
        end = None
        chunk_count = 0
        for index, record in enumerate(records[2:], 2):
            require(not record.get('invalid'), record.get('invalid', 'invalid record'))
            kind, fields = record['kind'], record['fields']
            if kind == 'END':
                require(index == len(records)-1, 'duplicate or additional selected record after END')
                end = fields
                break
            require(kind == 'DATA', 'duplicate, missing or out-of-order record')
            chunk = bytes.fromhex(fields['hex'])
            require(1 <= int(fields['bytes']) <= 256 and len(chunk) == int(fields['bytes']), 'DATA decoded length invalid')
            require(int(fields['offset']) == len(decoded), 'DATA offsets are not contiguous')
            require(len(decoded) + len(chunk) <= 262144, 'output exceeds 256KiB cap')
            decoded.extend(chunk)
            chunk_count += 1
        require(end is not None, 'missing END; retaining validated contiguous DATA prefix')
        require(end['target'] == request['target'] and end['boot'] == request['boot_uuid'], 'mixed END boot/target')
        require(end['pid'] == begin['pid'] and begin['unique'] == end['unique'] and
                begin['idversion'] == end['idversion'], 'END target incarnation differs')
        require(int(end['guest_ticks']) >= int(req['guest_ticks']), 'guest ticks reversed')
        require(int(end['bytes']) == len(decoded) and int(end['chunks']) == chunk_count, 'END byte/chunk totals differ')
        expected = {'eof':'1', 'truncated':'0', 'read_errno':'0', 'output_error':'0',
                    'reaped':'1', 'raw_status':'0', 'wait_errno':'0', 'killed':'0',
                    'target_post_match':'1', 'complete':'1'}
        require(all(end[k] == v for k, v in expected.items()), 'END reports incomplete, failed or truncated sample')
        result.update(transport_complete=True, target_pid=int(begin['pid']),
                      target_unique=int(begin['unique']), target_idversion=int(begin['idversion']))
    except (ValueError, KeyError) as exc:
        result['incomplete_reason'] = str(exc)
    result['decoded_bytes'] = len(decoded)
    result['decoded_sha256'] = sha(decoded)
    return result, bytes(decoded)


def check_destination(path):
    """Require an external directory or a destination ignored by its worktree."""
    path = path.resolve()
    parent = path.parent
    require(parent.is_dir(), 'Output parent directory must already exist')
    probe = subprocess.run(['git', '-C', str(parent), 'rev-parse', '--show-toplevel'],
                           capture_output=True, text=True)
    if probe.returncode:
        require(probe.returncode == 128 and 'not a git repository' in probe.stderr,
                'Could not establish output Git status')
        return 'outside-worktree'
    root = Path(probe.stdout.strip()).resolve()
    for candidate in (path, path/'output.bin', path/'result.json'):
        result = subprocess.run(['git', '-C', str(root), 'check-ignore', '--quiet', '--', str(candidate)],
                                capture_output=True)
        require(result.returncode == 0, 'Output destination must be outside Git or actually ignored')
    return 'ignored-by-worktree'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--serial', type=Path, required=True)
    parser.add_argument('--request', type=Path, required=True, help='Exact owned-control request.json (ID, boot UUID, target)')
    parser.add_argument('--output', type=Path, required=True, help='New ignored or outside-Git directory for result.json and output.bin')
    args = parser.parse_args()
    try:
        require(not args.output.exists(), 'Output directory must be new')
        destination_scope = check_destination(args.output)
        request_bytes = args.request.read_bytes()
        request = json.loads(request_bytes)
        require(isinstance(request, dict) and set(request) == {'request_id','boot_uuid','target'}, 'Request requires exact request_id, boot_uuid and target')
        for key, pattern in [('request_id', ID), ('boot_uuid', UUID), ('target', TARGET)]:
            require(isinstance(request[key], str) and re.fullmatch(pattern, request[key]) is not None, f'invalid {key}')
        with args.serial.open('rb') as stream:
            data = stream.read(64*1024*1024+1)
        require(len(data) <= 64*1024*1024, 'serial exceeds 64MiB bound')
        result, decoded = reconstruct(data, request)
        result.update(schema='inferno.sample-result.v1', request=request, output_destination=destination_scope,
                      serial={'path':str(args.serial.resolve()), 'bytes':len(data), 'sha256':sha(data),
                              'scope':'bytes read; a live serial log may grow later'},
                      request_source={'path':str(args.request.resolve()), 'sha256':sha(request_bytes)},
                      parser_sha256=sha(Path(__file__).read_bytes()),
                      limits=['No command submitted or guest action performed.',
                              'A complete transport does not prove useful stacks; review original tool output and errors.',
                              'Target incarnation checks do not atomically prevent PID reuse inside the original tool.',
                              'stdout/stderr are merged in pipe write order; sampling perturbs scheduling.',
                              'Incomplete output.bin is only the validated contiguous DATA prefix, if any.'])
        args.output.mkdir(mode=0o700)
        with (args.output/'output.bin').open('xb') as stream:
            stream.write(decoded)
        with (args.output/'result.json').open('x') as stream:
            json.dump(result, stream, indent=2); stream.write('\n')
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    print(json.dumps({'output':str(args.output), 'transport_complete':result['transport_complete'],
                      'output_usefulness':result['output_usefulness'], 'reason':result.get('incomplete_reason')}))
    return 0 if result['transport_complete'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
