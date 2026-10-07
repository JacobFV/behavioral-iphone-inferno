#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Record and submit one explicit owned-guest action; never retry input."""
import argparse
import hashlib
import json
import os
import stat
from pathlib import Path
import subprocess
import sys
import time
import uuid

import qmp_control


def trace_checkpoint(report):
    """Observe only the fixed trace log; never read payload or follow a symlink."""
    path = report / 'guest-errors.log'
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode):
            raise ValueError('Trace checkpoint requires a regular guest-errors.log')
        return {'path': str(path), 'device': info.st_dev, 'inode': info.st_ino,
                'size': info.st_size, 'wall_time': time.time(),
                'monotonic_time': time.monotonic()}
    finally:
        os.close(fd)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True, help='New action evidence directory')
    parser.add_argument('--trace-checkpoints', action='store_true',
                        help='Record file-visible trace log boundaries around this one submission')
    parser.add_argument('--send-deadline-monotonic', type=float, help='Optional HID host send-start cutoff, same-host monotonic, at most15 seconds ahead')
    actions = parser.add_subparsers(dest='action', required=True)
    for name, fields in [('tap', ('x', 'y')), ('swipe', ('x0', 'y0', 'x1', 'y1'))]:
        action = actions.add_parser(name)
        for field in fields:
            action.add_argument(field, type=int)
        action.add_argument('--duration-ms', type=int, required=True)
    actions.add_parser('open').add_argument('--boot-uuid', required=True)
    sample = actions.add_parser('sample')
    sample.add_argument('--boot-uuid', required=True)
    sample.add_argument('--target', choices=('SPRINGBOARD', 'BACKBOARDD'), required=True)
    args = parser.parse_args()
    request = {'request_id': uuid.uuid4().hex}
    if args.action == 'sample':
        command = 'guest-stack-sample'
        request.update(boot_uuid=args.boot_uuid, target=args.target)
        validator = qmp_control.sample_line
    elif args.action == 'open':
        command = 'guest-open-app'
        request['boot_uuid'] = args.boot_uuid
        validator = qmp_control.open_line
    else:
        command = 'guest-hid-gesture'
        fields = ('x', 'y') if args.action == 'tap' else ('x0', 'y0', 'x1', 'y1')
        request.update(kind=args.action, duration_ms=args.duration_ms,
                       **{field: getattr(args, field) for field in fields})
        validator = qmp_control.gesture_line
    if args.send_deadline_monotonic is not None:
        if args.action not in ('tap','swipe'):
            parser.error('Send deadline is restricted to HID gestures')
        request['send_deadline_monotonic'] = args.send_deadline_monotonic
    try:
        wire = validator(request)
        report = args.report.resolve(strict=True)
        record = json.loads((report / 'report.json').read_text())
        if 'exit_code' in record:
            raise ValueError('Run has already stopped')
        if Path(record['control_mailbox']).resolve() != report / 'control':
            raise ValueError('Report control mailbox does not match its directory')
        qmp_control.private_dir(report / 'control')
        if args.action == 'sample':
            qmp_control.sample_capability(report, request)
        if args.trace_checkpoints:
            trace_checkpoint(report)  # Fail preflight before any command submission.
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
    if args.trace_checkpoints:
        evidence['trace_scope'] = ('File-visible guest-errors.log byte boundaries around one CLI subprocess. '
                                   'Buffered trace emission prevents exact device-event times or per-tap draw attribution.')
    evidence_path = output / 'submission.json'
    evidence_path.write_text(json.dumps(evidence, indent=2) + '\n')
    if args.trace_checkpoints:
        try:
            evidence['trace_before'] = trace_checkpoint(report)
        except (OSError, ValueError) as exc:
            evidence.update(error=f'Trace checkpoint failed before submission: {exc}', exit_code=1,
                            submitted=False, finished_time=time.time())
            evidence_path.write_text(json.dumps(evidence, indent=2) + '\n')
            print(json.dumps(evidence))
            return 1
        evidence_path.write_text(json.dumps(evidence, indent=2) + '\n')
    try:
        result = subprocess.run(argv, capture_output=True, text=True)
        if args.trace_checkpoints:
            try:
                evidence['trace_after'] = trace_checkpoint(report)
            except (OSError, ValueError) as exc:
                evidence['trace_after_error'] = str(exc)
        (output / 'stdout.txt').write_text(result.stdout)
        (output / 'stderr.txt').write_text(result.stderr)
        evidence.update(finished_time=time.time(), exit_code=result.returncode)
    except OSError as exc:
        if args.trace_checkpoints:
            try:
                evidence['trace_after'] = trace_checkpoint(report)
            except (OSError, ValueError) as checkpoint_exc:
                evidence['trace_after_error'] = str(checkpoint_exc)
        evidence.update(finished_time=time.time(), error=str(exc), exit_code=1)
    evidence_path.write_text(json.dumps(evidence, indent=2) + '\n')
    print(json.dumps(evidence))
    return evidence['exit_code']


if __name__ == '__main__':
    raise SystemExit(main())
