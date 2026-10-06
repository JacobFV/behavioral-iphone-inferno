#!/usr/bin/env python3
"""Execute a firmware-free headless QMP smoke; never implies iOS boot."""
# SPDX-License-Identifier: AGPL-3.0-or-later
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import platform
import socket
import subprocess
import tempfile
import time


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--binary', required=True, type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    binary = args.binary.resolve(strict=True)
    repo = Path(__file__).resolve().parents[1]
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
    output = args.output or repo / '.local-build' / 'reports' / ('smoke-' + stamp)
    output.mkdir(parents=True, exist_ok=False)
    report = {'kind': 'firmware_free_qmp_control_plane', 'passed': False,
              'ios_booted': False, 'app_executed': False,
              'binary': str(binary), 'binary_sha256': hashlib.file_digest(binary.open('rb'), 'sha256').hexdigest(),
              'host': {'system': platform.system(), 'architecture': platform.machine(),
                       'page_size': os.sysconf('SC_PAGE_SIZE')},
              'upstream': json.loads((repo / 'companion/upstream.json').read_text()),
              'companion_revision': subprocess.check_output(['git', '-C', str(repo), 'rev-parse', 'HEAD'], text=True).strip(),
              'commands': []}
    process = None
    started = time.monotonic()
    try:
        with tempfile.TemporaryDirectory(prefix='inferno-qmp-') as tmp, (output / 'stderr.log').open('wb') as stderr:
            endpoint = str(Path(tmp) / 'qmp.sock')
            command = [str(binary), '-machine', 'none', '-accel', 'tcg', '-S',
                       '-display', 'none', '-nodefaults', '-monitor', 'none', '-serial', 'none',
                       '-qmp', 'unix:' + endpoint + ',server=on,wait=off']
            report['invocation'] = command
            process = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=stderr)
            deadline = started + 30
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as connection:
                while True:
                    if process.poll() is not None:
                        raise RuntimeError('Emulator exited before QMP connection; see stderr.log')
                    try:
                        connection.connect(endpoint)
                        break
                    except (FileNotFoundError, ConnectionRefusedError):
                        if time.monotonic() >= deadline:
                            raise TimeoutError('QMP socket did not become ready within 30 seconds')
                        time.sleep(.025)
                connection.settimeout(10)
                with connection.makefile('rwb', buffering=0) as stream:
                    def receive():
                        line = stream.readline(1024 * 1024)
                        if not line or len(line) >= 1024 * 1024:
                            raise RuntimeError('Missing or oversized QMP response')
                        return json.loads(line)
                    report['greeting'] = receive()
                    if 'QMP' not in report['greeting']:
                        raise RuntimeError('Missing QMP greeting')
                    def execute(name):
                        request = {'execute': name, 'id': name}
                        stream.write((json.dumps(request) + '\n').encode())
                        for _ in range(100):
                            response = receive()
                            if response.get('id') == name:
                                report['commands'].append({'request': request, 'response': response})
                                if 'error' in response:
                                    raise RuntimeError('QMP command failed: ' + name)
                                return response['return']
                        raise RuntimeError('Too many unrelated QMP events')
                    execute('qmp_capabilities')
                    report['version'] = execute('query-version')
                    machines = execute('query-machines')
                    report['apple_machine_present'] = any(m.get('name') == 't8030' for m in machines)
                    if not report['apple_machine_present']:
                        raise RuntimeError('Built executable does not list the t8030 machine')
                    status = execute('query-status')
                    if status.get('running'):
                        raise RuntimeError('Smoke must remain stopped, with no guest running')
                    cpus = execute('query-cpus-fast')
                    if cpus:
                        raise RuntimeError('Image-free none smoke unexpectedly created guest CPUs')
                    execute('quit')
            code = process.wait(timeout=10)
            if code:
                raise RuntimeError('Emulator returned exit code ' + str(code))
            report['exit_code'] = code
            report['passed'] = True
    except Exception as exc:
        report['error'] = {'type': type(exc).__name__, 'detail': str(exc)}
    finally:
        if process is not None and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
        report['control_plane_elapsed_seconds'] = round(time.monotonic() - started, 6)
        (output / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'passed': report['passed'], 'kind': report['kind'], 'report': str(output / 'report.json')}))
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
