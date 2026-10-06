#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Record and submit one explicit owned-guest action; never retry input."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time
import uuid

import qmp_control


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True, help='New action evidence directory')
    actions = parser.add_subparsers(dest='action', required=True)
    for name, fields in [('tap', ('x', 'y')), ('swipe', ('x0', 'y0', 'x1', 'y1'))]:
        action = actions.add_parser(name)
        for field in fields:
            action.add_argument(field, type=int)
        action.add_argument('--duration-ms', type=int, required=True)
    actions.add_parser('open').add_argument('--boot-uuid', required=True)
    args = parser.parse_args()
    request = {'request_id': uuid.uuid4().hex}
    if args.action == 'open':
        command = 'guest-open-app'
        request['boot_uuid'] = args.boot_uuid
        validator = qmp_control.open_line
    else:
        command = 'guest-hid-gesture'
        fields = ('x', 'y') if args.action == 'tap' else ('x0', 'y0', 'x1', 'y1')
        request.update(kind=args.action, duration_ms=args.duration_ms,
                       **{field: getattr(args, field) for field in fields})
        validator = qmp_control.gesture_line
    try:
        wire = validator(request)
        report = args.report.resolve(strict=True)
        record = json.loads((report / 'report.json').read_text())
        if 'exit_code' in record:
            raise ValueError('Run has already stopped')
        if Path(record['control_mailbox']).resolve() != report / 'control':
            raise ValueError('Report control mailbox does not match its directory')
        qmp_control.private_dir(report / 'control')
        args.output.mkdir(parents=True, mode=0o700, exist_ok=False)
    except (OSError, ValueError, KeyError) as exc:
        parser.error(str(exc))
    output = args.output.resolve()
    (output / 'request.json').write_text(json.dumps(request, indent=2) + '\n')
    script = Path(qmp_control.__file__).resolve()
    argv = [sys.executable, str(script), '--report', str(report), command,
            '--arguments', json.dumps(request)]
    evidence = {'report': str(report), 'command': argv, 'request_id': request['request_id'],
                'expected_serial_wire': wire.decode('ascii'), 'started_time': time.time(),
                'source_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                'control_source_sha256': hashlib.sha256(script.read_bytes()).hexdigest(),
                'scope': 'One explicit host submission; acceptance is not guest delivery or visible response. Never automatically retry an uncertain action.'}
    evidence_path = output / 'submission.json'
    evidence_path.write_text(json.dumps(evidence, indent=2) + '\n')
    try:
        result = subprocess.run(argv, capture_output=True, text=True)
        (output / 'stdout.txt').write_text(result.stdout)
        (output / 'stderr.txt').write_text(result.stderr)
        evidence.update(finished_time=time.time(), exit_code=result.returncode)
    except OSError as exc:
        evidence.update(finished_time=time.time(), error=str(exc), exit_code=1)
    evidence_path.write_text(json.dumps(evidence, indent=2) + '\n')
    print(json.dumps(evidence))
    return evidence['exit_code']


if __name__ == '__main__':
    raise SystemExit(main())
