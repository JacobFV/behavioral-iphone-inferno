#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Boot one freshly reverified imported stage; never assert app execution."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import sys
import time
from import_stage import strict_json, validate_session, verify_stopped

SOURCE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('stage_coordinator', SOURCE / 'stage-import.py')
coordinator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(coordinator)


def snapshot(path, maximum=32 << 20):
    path = Path(path).absolute()
    before = coordinator.identity(path)
    if before['st_size'] > maximum:
        raise ValueError('Metadata exceeds bound: ' + str(path))
    raw = path.read_bytes()
    if coordinator.identity(path) != before:
        raise ValueError('Metadata changed while reading: ' + str(path))
    return {'path': str(path), 'identity': before,
            'sha256': hashlib.sha256(raw).hexdigest(), 'raw': raw}


def public_snapshot(record):
    return {key: value for key, value in record.items() if key != 'raw'}


def unchanged(records):
    for record in records:
        current = snapshot(record['path'], 64 << 20)
        if public_snapshot(current) != public_snapshot(record):
            raise ValueError('Inspected metadata changed: ' + record['path'])


def complete_markers(folder):
    if (folder / 'INCOMPLETE.json').exists() or (folder / 'failure.json').exists():
        raise ValueError('Incomplete/failed coordinator stage is not a boot base')


def source_inventory():
    paths, _ = coordinator.source_inventory()
    paths += [Path(__file__).resolve(), SOURCE / 'run']
    return {str(path): coordinator.digest(path) for path in paths}


def fixed_command(context, report, output, seconds):
    session = context['session']
    inputs = session['runtime_record']['inputs']
    for name in ('boot.py', 'qmp_control.py'):
        if coordinator.digest(SOURCE / name) != session['sources'][name]:
            raise ValueError('Sibling runner/control differs from prepared session; use its reviewed stable host tree')
    return [sys.executable, str(SOURCE / 'boot.py'), '--profile', inputs['profile']['path'],
            '--binary', inputs['emulator']['path'], '--manifest', inputs['emulator_build']['path'],
            '--overlay-tools-root', session['runtime_record']['overlay_tools_root'],
            '--overlay-base-report', str(report), '--disk-boot', '--launchd-unsecure-cache',
            '--control-mailbox', '--guest-hid-serial', '--guest-errors', '--capture-interval', '10',
            '--seconds', str(seconds), '--output', str(output)]


def validate_inputs(stage_path, stage_hash, session_path):
    if not re.fullmatch('[0-9a-f]{64}', stage_hash):
        raise ValueError('Stage SHA256 must be 64 lowercase hexadecimal digits')
    stage_path = Path(stage_path).absolute()
    if stage_path.name != 'verified-stage.json':
        raise ValueError('Use the coordinator verified-stage.json result')
    folder = stage_path.parent
    complete_markers(folder)
    stage_snapshot = snapshot(stage_path)
    if stage_snapshot['sha256'] != stage_hash:
        raise ValueError('Stage SHA256 differs')
    stage = strict_json(stage_snapshot['raw'])
    if stage.get('schema') != 'inferno.verified-import-stage.v1' or stage.get('eligible') is not True:
        raise ValueError('Unsupported stage result; eligibility must still be reverified')
    report = folder / 'recovery-run/report.json'
    retention = report.parent / 'stopped-disk-hashes.json'
    checkpoint = folder / 'content-check.json'
    if stage.get('report') != str(report) or stage.get('retention') != str(retention):
        raise ValueError('Stage report/retention layout differs')
    session_snapshot = snapshot(session_path, 16 << 20)
    if session_snapshot['sha256'] != stage['session_sha256']:
        raise ValueError('Session does not match pinned stage')
    metadata = [stage_snapshot, session_snapshot]
    metadata += [snapshot(path, 64 << 20) for path in (
        report, retention, retention.with_name('stopped-disk-hashes-verification.json'), checkpoint,
        report.parent / 'serial.log', report.parent / 'control-transcript.jsonl',
        report.parent / 'qmp-transcript.jsonl')]
    context = validate_session(session_path, stage['session_sha256'])
    fresh = verify_stopped(context, report, retention, checkpoint)
    for key in ('schema', 'eligible', 'session_sha256', 'report', 'report_sha256',
                'retention', 'retention_sha256', 'content', 'content_checkpoint_sha256', 'backing_depth'):
        if stage.get(key) != fresh.get(key):
            raise ValueError('Fresh stage verification differs: ' + key)
    complete_markers(folder)
    unchanged(metadata)
    return context, report, fresh, metadata


def normal_result(report_path, context, base_report, verified):
    report = strict_json(report_path.read_bytes())
    session = context['session']
    inputs = session['runtime_record']['inputs']
    if (report.get('attempt_completed') is not True or report.get('error') or
            report.get('exit_code') != 0 or report.get('kind') != 't8030_direct_root_experiment'):
        raise ValueError('Installed attempt did not finish normally')
    for key, expected in (
        ('profile_path', inputs['profile']['path']), ('profile_sha256', inputs['profile']['sha256']),
        ('binary_sha256', inputs['emulator']['sha256']), ('build_manifest_sha256', inputs['emulator_build']['sha256']),
        ('runner_sha256', session['sources']['boot.py']), ('control_source_sha256', session['sources']['qmp_control.py'])):
        if report.get(key) != expected:
            raise ValueError('Installed report input/source differs: ' + key)
    if report.get('inputs') != context['verified_runtime']['profile_inputs']:
        raise ValueError('Installed report profile input dictionary differs')
    if '-initrd' in report.get('invocation', []):
        raise ValueError('Installed attempt unexpectedly used a recovery initrd')
    actual_base = report.get('overlay_base_report', {})
    if (actual_base.get('report') != str(base_report) or
            actual_base.get('report_sha256') != verified['report_sha256'] or
            actual_base.get('stopped_manifest_sha256') != verified['retention_sha256']):
        raise ValueError('Installed report used a different verified stage')
    if report.get('probe_journey'):
        raise ValueError('Unexpected fixture journey on generic imported app')
    shutdown = coordinator.PRESERVE.verify_shutdown(report_path.parent, report)
    return {'status': 'normal-installed-attempt-no-app-success-assertion',
            'report': str(report_path), 'report_sha256': coordinator.digest(report_path),
            'shutdown': shutdown, 'app_execution_asserted': False,
            'scope': 'Normal runner completion only; app launch, pixels and preservation remain separate.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stage', type=Path, required=True)
    parser.add_argument('--stage-sha256', required=True)
    parser.add_argument('--session', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--seconds', type=int, default=1200)
    args = parser.parse_args()
    if not 1 <= args.seconds <= 3600:
        parser.error('--seconds must be 1..3600')
    output = process = None
    handles = []
    try:
        sources = source_inventory()
        context, base_report, verified, metadata = validate_inputs(args.stage, args.stage_sha256, args.session)
        output = coordinator.IMPORTER.external_output(args.output)
        command = fixed_command(context, base_report, output / 'boot', args.seconds)
        proc_check = coordinator.no_running_emulator()
        output.mkdir(mode=0o700)
        coordinator.write_new(output / 'INCOMPLETE.json', {'status': 'incomplete-attempt', 'started': time.time()})
        coordinator.write_new(output / 'launch.json', {
            'command': command, 'stage': str(args.stage.absolute()), 'stage_sha256': args.stage_sha256,
            'session': str(args.session.absolute()), 'session_sha256': context['session_sha256'],
            'source_sha256': sources, 'inspected_metadata': [public_snapshot(x) for x in metadata],
            'fresh_stage_verification': verified, 'proc_preflight': proc_check,
            'scope': 'One explicit installed attempt; no automatic gestures, retries or app success assertion'})
        complete_markers(args.stage.absolute().parent)
        unchanged(metadata)
        if source_inventory() != sources:
            raise ValueError('Host source changed before launch')
        coordinator.no_running_emulator()
        for name in ('stdout.log', 'stderr.log'):
            handles.append((output / name).open('xb'))
        process = subprocess.Popen(command, stdout=handles[0], stderr=handles[1], start_new_session=True)
        runner_stat = Path(f'/proc/{process.pid}/stat').read_text()
        process.inferno_start_ticks = int(runner_stat[runner_stat.rfind(')') + 2:].split()[19])
        coordinator.write_new(output / 'runner-process.json', {
            'pid': process.pid, 'start_ticks': process.inferno_start_ticks,
            'proc_stat': runner_stat, 'command': command, 'started': time.time()})
        if process.wait(timeout=args.seconds + 300) != 0:
            raise ValueError('Installed runner returned failure')
        if Path(f'/proc/{process.pid}').exists() or coordinator.owned_group_members(process):
            raise ValueError('Owned runner/session remains alive')
        result = normal_result(output / 'boot/report.json', context, base_report, verified)
        complete_markers(args.stage.absolute().parent)
        unchanged(metadata)
        if source_inventory() != sources:
            raise ValueError('Host source changed during attempt')
        coordinator.write_new(output / 'completed-run.json', result)
        (output / 'INCOMPLETE.json').unlink()
        print(json.dumps({'completed_run': str(output / 'completed-run.json'),
                          'sha256': coordinator.digest(output / 'completed-run.json'),
                          'app_execution_asserted': False}))
        return 0
    except BaseException as exc:
        cleanup = {}
        if process is not None:
            try:
                cleanup = coordinator.stop_owned_group(process)
            except Exception as stop_error:
                cleanup = {'error': str(stop_error), 'owned_runner_pid': process.pid}
        if output is not None and output.is_dir():
            coordinator.write_new(output / 'failure.json', {
                'status': 'failed-incomplete-do-not-promote', 'type': type(exc).__name__,
                'error': str(exc), 'cleanup': cleanup, 'app_execution_asserted': False})
        print('boot-import failed: ' + str(exc), file=sys.stderr)
        return 1
    finally:
        for handle in handles:
            handle.close()


if __name__ == '__main__':
    raise SystemExit(main())
