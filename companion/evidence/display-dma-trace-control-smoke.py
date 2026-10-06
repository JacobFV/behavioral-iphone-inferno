#!/usr/bin/env python3
"""Actual firmware-free QMP/mailbox trace cleanup check, never a guest/display test."""
# SPDX-License-Identifier: AGPL-3.0-or-later
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import uuid


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('repo', 'binary', 'manifest', 'output'):
        parser.add_argument('--' + name, required=True, type=Path)
    args = parser.parse_args()
    repo, binary, manifest = (p.resolve(strict=True) for p in (args.repo, args.binary, args.manifest))
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    sys.path.insert(0, str(repo / 'companion'))
    from boot import QMP
    from qmp_control import ControlMailbox, DISPLAY_TRACE_EVENTS, write_private, read_private
    result = {'scope': 'Firmware-free machine none control-plane execution only; no iOS boot, trace emission, display or app claim.',
              'binary_sha256': sha(binary), 'manifest_sha256': sha(manifest),
              'script_sha256': sha(Path(__file__)),
              'boot_source_sha256': sha(repo / 'companion/boot.py'),
              'control_source_sha256': sha(repo / 'companion/qmp_control.py'),
              'events': list(DISPLAY_TRACE_EVENTS), 'checks': {}}
    shutil.copyfile(manifest, output / 'build-manifest.json')
    qmp = connection = mailbox = process = None
    with tempfile.TemporaryDirectory(prefix='inferno-trace-smoke-') as temporary:
        endpoint = str(Path(temporary) / 'qmp.sock')
        command = [str(binary), '-machine', 'none', '-accel', 'tcg', '-m', '128M',
                   '-display', 'none', '-monitor', 'none', '-serial', 'none', '-S',
                   '-qmp', 'unix:' + endpoint + ',server=on,wait=off']
        result['command'] = command
        try:
            with (output / 'stderr.log').open('xb') as stderr:
                process = subprocess.Popen(command, stdin=subprocess.DEVNULL,
                                           stdout=subprocess.DEVNULL, stderr=stderr)
                deadline = time.monotonic() + 10
                while not Path(endpoint).exists():
                    if process.poll() is not None or time.monotonic() > deadline:
                        raise RuntimeError('QMP endpoint did not become ready')
                    time.sleep(.02)
                connection = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                connection.settimeout(5)
                connection.connect(endpoint)
                qmp = QMP(connection, output)
                result['greeting'] = qmp.receive()
                assert 'return' in qmp.execute('qmp_capabilities')
                mailbox = ControlMailbox(output)

                def states(label, expected):
                    observations = {}
                    for name in DISPLAY_TRACE_EVENTS:
                        reply = qmp.execute('trace-event-get-state', {'name': name})
                        rows = reply.get('return', [])
                        assert len(rows) == 1 and rows[0]['name'] == name and rows[0]['state'] == expected, reply
                        observations[name] = reply
                    result['checks'][label] = observations

                def request_window(seconds):
                    token = uuid.uuid4().hex
                    write_private(mailbox.path / ('request-' + token + '.json'),
                                  {'execute': 'trace-display-window', 'arguments': {'seconds': seconds},
                                   'created': time.time()})
                    mailbox.poll(qmp)
                    reply = json.loads(read_private(mailbox.path / ('reply-' + token + '.json')))
                    assert 'return' in reply, reply
                    return reply

                states('default_off', 'disabled')
                result['ten_second_request'] = request_window(10)
                states('explicitly_enabled', 'enabled')
                limit = time.monotonic() + 12
                while mailbox.display_trace.pending and time.monotonic() < limit:
                    time.sleep(.02)
                    mailbox.poll(qmp)
                assert not mailbox.display_trace.pending
                states('deadline_disabled', 'disabled')
                result['early_close_request'] = request_window(10)
                states('second_window_enabled', 'enabled')
                mailbox.close(qmp)
                states('early_cleanup_disabled', 'disabled')
                result['control_plane_checks_passed'] = True
        except Exception as exc:
            result['error'] = {'type': type(exc).__name__, 'detail': str(exc)}
        finally:
            if qmp:
                try:
                    if mailbox:
                        mailbox.close(qmp)
                    result['quit_response'] = qmp.execute('quit')
                except Exception as exc:
                    result['cleanup_error'] = str(exc)
            if process:
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.terminate()
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait()
                result['exit_code'] = process.returncode
            if qmp:
                qmp.close()
            if connection:
                connection.close()
    result['retained_raw'] = {name: sha(output / name) for name in
                              ('qmp-transcript.jsonl', 'control-transcript.jsonl', 'display-trace-control.jsonl')
                              if (output / name).exists()}
    (output / 'report.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'output': str(output), 'checks_passed': result.get('control_plane_checks_passed', False),
                      'exit_code': result.get('exit_code'), 'error': result.get('error')}))
    return 0 if result.get('control_plane_checks_passed') and result.get('exit_code') == 0 and not result.get('cleanup_error') else 1


if __name__ == '__main__':
    raise SystemExit(main())
