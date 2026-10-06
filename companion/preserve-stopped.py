#!/usr/bin/env python3
"""Verify a normally stopped owned disk set and write a NEW retention manifest.

No VM control, disk writes, freezing, deletion, or source-manifest updates. The
result is a point-in-time observation, not an exclusive lock. Retain all recorded
backing layers. Linux /proc permission gaps are recorded, never called proof of
host-wide descriptor absence.
"""
# SPDX-License-Identifier: AGPL-3.0-or-later
import argparse
import hashlib
import json
from pathlib import Path
import stat
import sys
import time

from disk_overlay import AUXILIARY_SIZES, digest, validate_tools, verify_backing, tool_run


def identity(path):
    value = path.lstat()
    if not stat.S_ISREG(value.st_mode):
        raise ValueError(f'Expected regular non-symlink file: {path}')
    return tuple(getattr(value, key) for key in
                 ('st_dev', 'st_ino', 'st_size', 'st_mtime_ns', 'st_ctime_ns', 'st_mode'))


def bounded_json(path, maximum=16 << 20):
    if identity(path)[2] > maximum:
        raise ValueError(f'JSON exceeds {maximum} bytes: {path}')
    return json.loads(path.read_bytes())


def descriptor_check(paths):
    targets = {identity(path)[:2]: str(path) for path in paths}
    denied = set()
    scanned = 0
    for process in Path('/proc').iterdir():
        if not process.name.isdigit():
            continue
        try:
            descriptors = list((process / 'fd').iterdir())
        except PermissionError:
            denied.add(int(process.name))
            continue
        except (FileNotFoundError, ProcessLookupError):
            continue
        scanned += 1
        for descriptor in descriptors:
            try:
                current = descriptor.stat()
                target = targets.get((current.st_dev, current.st_ino))
                if target:
                    raise ValueError(f'Stopped namespace has an open descriptor: {descriptor} -> {target}')
            except PermissionError:
                denied.add(int(process.name))
            except (FileNotFoundError, ProcessLookupError):
                pass
    return {'scope': 'Readable Linux /proc descriptors only; no exclusive lock or host-wide guarantee.',
            'matching_descriptors': 0, 'processes_scanned': scanned,
            'permission_denied_pids': sorted(denied), 'time': time.time()}


def verify_shutdown(directory, report, failed_attempt=False):
    if report.get('exit_code') != 0:
        raise ValueError('Report must record emulator exit0')
    if report.get('error') and not failed_attempt:
        raise ValueError('Attempt error requires explicit --failed-attempt; default preservation rejects it')
    if report.get('kind') not in ('t8030_direct_root_experiment', 't8030_recovery_ramdisk_experiment'):
        raise ValueError('Expected an owned t8030 boot report')
    pid = report.get('pid')
    if type(pid) is not int or pid <= 0 or Path(f'/proc/{pid}').exists():
        raise ValueError('Reported emulator PID is missing/invalid or still exists (including PID reuse)')
    quit_reply = report.get('quit_response')
    if (not isinstance(quit_reply, dict) or quit_reply.get('return') != {}
            or type(quit_reply.get('id')) is not int):
        raise ValueError('Report lacks a successful QMP quit acknowledgement')
    path = directory / 'qmp-transcript.jsonl'
    if identity(path)[2] > 32 << 20:
        raise ValueError('QMP transcript exceeds bounded32MiB limit')
    data = path.read_bytes()
    sent = acknowledged = shutdown = False
    evidence = []
    for number, line in enumerate(data.splitlines(), 1):
        entry = json.loads(line)
        message = json.loads(entry['raw'])
        relevant = False
        if entry['direction'] == 'send' and message.get('execute') == 'quit' and message.get('id') == quit_reply['id']:
            sent = relevant = True
        if entry['direction'] == 'receive':
            if message == quit_reply:
                acknowledged = relevant = True
            if message.get('event') == 'SHUTDOWN' and message.get('data', {}).get('reason') == 'host-qmp-quit':
                shutdown = relevant = True
        if relevant:
            evidence.append({'line': number, 'entry': entry})
    if not (sent and acknowledged and shutdown):
        raise ValueError('Raw QMP does not establish quit request, matching acknowledgement and host-qmp-quit SHUTDOWN')
    return {'path': str(path), 'sha256': hashlib.sha256(data).hexdigest(), 'evidence': evidence,
            'reported_emulator_pid_absent': pid}


def preserve(report_path, output, failed_attempt=False):
    report_path = report_path.resolve(strict=True)
    if report_path.is_dir():
        report_path /= 'report.json'
    output = output.absolute()
    verification_path = output.with_name(output.stem + '-verification.json')
    if output == verification_path or any(p.exists() or p.is_symlink() for p in (output, verification_path)):
        raise ValueError('Output manifest and verification sidecar must be new files; existing evidence is never overwritten')
    directory = report_path.parent
    report_identity = identity(report_path)
    report_hash = digest(report_path)
    report = bounded_json(report_path)
    shutdown = verify_shutdown(directory, report, failed_attempt)
    entries = report.get('disks')
    if not isinstance(entries, list) or len(entries) != 7:
        raise ValueError('Report must describe exactly seven namespaces')
    root_name = 'root.qcow2' if report.get('root_overlay') else 'root.raw'
    expected = {root_name, *AUXILIARY_SIZES}
    paths = {}
    for entry in entries:
        path = Path(entry['path'])
        if path.name not in expected or path != directory / 'disks' / path.name or path.name in paths:
            raise ValueError('Namespace path must be unique and inside this report disks directory')
        identity(path)
        if entry.get('format', 'raw') != ('qcow2' if path.name == 'root.qcow2' else 'raw'):
            raise ValueError('Reported namespace format mismatch')
        if path.name in AUXILIARY_SIZES and path.stat().st_size != AUXILIARY_SIZES[path.name]:
            raise ValueError('Auxiliary namespace size mismatch')
        if path.name == 'root.raw' and path.stat().st_size != entry.get('bytes'):
            raise ValueError('Raw root size differs from reported allocation')
        paths[path.name] = path
    if set(paths) != expected:
        raise ValueError('Namespace set differs from root plus six known auxiliary namespaces')
    before = {name: identity(path) for name, path in paths.items()}
    fds_before = descriptor_check(paths.values())
    backing = None
    record = report.get('root_overlay')
    if record:
        if bounded_json(directory / 'root-overlay.json') != record or record.get('path') != str(paths[root_name]):
            raise ValueError('Overlay sidecar/path differs from final report')
        if record.get('backing_after_stop', {}).get('unchanged') is not True:
            raise ValueError('Report did not verify unchanged backing at shutdown')
        tools = validate_tools(Path(record['tool']['root']))
        if tools != record['tool']:
            raise ValueError('Recorded overlay tools differ from freshly validated pinned tools')
        backing = verify_backing(record)
        if backing != record['backing_after_stop']:
            raise ValueError('Fresh ancestor verification differs from stopped report')
        layers = backing.get('layers') or [record['backing']]
        info = json.loads(tool_run(tools, 'info', '--output=json', '-f', 'qcow2', paths[root_name]))
        if (info.get('backing-filename') != layers[0]['path']
                or info.get('backing-filename-format') != layers[0]['format']
                or info.get('virtual-size') != next(e['bytes'] for e in entries if e['path'] == str(paths[root_name]))):
            raise ValueError('Actual root overlay header differs from recorded backing/virtual size')
    manifest = {}
    for name, path in sorted(paths.items()):
        entry = {'path': str(path), 'bytes': path.stat().st_size, 'sha256': digest(path),
                 'format': 'qcow2' if name == 'root.qcow2' else 'raw'}
        if name == 'root.qcow2':
            entry.update(standalone=False, backing_chain=backing.get('layers') or [record['backing']])
        if name == root_name and failed_attempt:
            entry['forensic_only'] = True
        manifest[name] = entry
    fds_after = descriptor_check(paths.values())
    if any(identity(path) != before[name] for name, path in paths.items()):
        raise ValueError('Namespace identity changed during verification')
    if identity(report_path) != report_identity or digest(report_path) != report_hash:
        raise ValueError('Source report changed during verification')
    if digest(directory / 'qmp-transcript.jsonl') != shutdown['sha256']:
        raise ValueError('QMP transcript changed during verification')
    if Path(f"/proc/{report['pid']}").exists():
        raise ValueError('Reported emulator PID exists at verification completion')
    verification = {'schema': 'inferno.stopped-retention-verification.v1',
                    'report': str(report_path), 'report_sha256': report_hash,
                    'failed_attempt_opt_in': failed_attempt,
                    'attempt_error': report.get('error'),
                    'attempt_completed': report.get('attempt_completed'),
                    'strict_journey': {key: (report.get('probe_journey') or {}).get(key)
                                       for key in ('state', 'completed')},
                    'outcome_scope': 'Disk retention only; not an attempt-success claim or overlay-base authorization.',
                    'source_sha256': digest(Path(__file__)),
                    'overlay_module_sha256': digest(Path(__file__).with_name('disk_overlay.py')),
                    'shutdown': shutdown, 'fd_before': fds_before, 'fd_after': fds_after,
                    'ancestor_verification': backing, 'namespace_count': len(manifest),
                    'retention': 'Keep each disk and every recorded backing layer. No file was frozen or protected by this tool.',
                    'scope': 'Point-in-time verification; permission gaps and subsequent changes remain possible.'}
    output.parent.mkdir(parents=True, exist_ok=True)
    for path, data in ((output, manifest), (verification_path, verification)):
        with path.open('x') as stream:
            json.dump(data, stream, indent=2)
            stream.write('\n')
    return {'output': str(output), 'manifest_sha256': digest(output),
            'verification': str(verification_path), 'verification_sha256': digest(verification_path),
            'namespace_count': len(manifest)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report', required=True, type=Path, help='Stopped report.json or its directory')
    parser.add_argument('--output', required=True, type=Path,
                        help='New manifest file; also creates NAME-verification.json beside it, never overwrites')
    parser.add_argument('--failed-attempt', action='store_true',
                        help='Retain a recorded failed attempt only if normal QMP shutdown and every disk check still pass')
    args = parser.parse_args()
    try:
        print(json.dumps(preserve(args.report, args.output, args.failed_attempt), indent=2))
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f'preserve-stopped: {exc}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
