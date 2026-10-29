#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Boot one reverified fresh owned-runtime stage from disk; never assert app execution."""
import contextlib
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
SOURCE = Path(__file__).resolve().parent
sys.path.insert(0, str(SOURCE))
import fresh_runtime_stage as FR
import disk_overlay as OV
import runtime_rebuild as RB
from boot import load_profile
from initial_volumes import bounded_record

CO = FR.CO
RB.install(FR, OV)
INFERNO_HOME = Path(os.environ.get('INFERNO_HOME') or Path.home() / '.local/share/inferno')
DEFAULT_PROFILE = INFERNO_HOME / 'images/ios14b5/verified-profile/profile.json'
SCHEMA = 'inferno.fresh-runtime-stage.v1'
MIN_FREE = 4 << 30
MUST_MATCH_SOURCES = ('boot.py', 'qmp_control.py')


def actual_sha(path):
    """Unwrapped file digest: what is really on disk now."""
    with Path(path).open('rb') as handle:
        return hashlib.file_digest(handle, 'sha256').hexdigest()


def read_stage(path, expected):
    if not re.fullmatch('[0-9a-f]{64}', expected):
        raise ValueError('Stage SHA256 must be 64 lowercase hexadecimal digits')
    path = Path(path).absolute()
    if path.name != 'fresh-runtime.json':
        raise ValueError('Use the fresh-runtime.json result of stage-fresh-runtime.py')
    if not path.is_file() or path.is_symlink():
        raise ValueError('Missing or non-regular fresh-runtime.json: ' + str(path))
    if actual_sha(path) != expected:
        raise ValueError('fresh-runtime.json SHA256 differs from the supplied pin')
    for marker in ('INCOMPLETE.json', 'failure.json'):
        if (path.parent / marker).exists():
            raise ValueError('Fresh stage is incomplete/failed: ' + marker)
    stage = bounded_record(path)
    if (stage.get('schema') != SCHEMA or stage.get('status') != 'owned-runtime-staged-not-booted' or
            stage.get('ipa_runtime_ready') is not False or stage.get('backing_depth') != 3):
        raise ValueError('Unsupported fresh runtime stage record')
    report = path.parent / 'recovery-run/report.json'
    if stage.get('report') != str(report) or stage.get('retention') != str(report.parent / 'stopped-disk-hashes.json'):
        raise ValueError('Fresh stage report/retention layout differs')
    return path, stage, report



def lost_build_context(stage):
    """historical() only for a chain that pins the lost emulator build.

    A chain produced with the recorded rebuild pins the rebuilt hashes on the
    substituted paths; mapping those back to the lost ones would fail its own pins.
    """
    subs = RB.load()['substitutions']
    rebuilt = {e['rebuilt_sha256'] for e in subs.values()}

    def pins_rebuild(value, depth=0):
        # The runs' own reports record the emulator they used; follow report and
        # predecessor links, which is where a stage record keeps that binding.
        if depth > 8:
            return False
        if isinstance(value, dict):
            if any(value.get(p) == e['rebuilt_sha256'] for p, e in subs.items()):
                return True
            if value.get('binary_sha256') in rebuilt or value.get('build_manifest_sha256') in rebuilt:
                return True
            for key in ('report', 'predecessor'):
                link = value.get(key)
                link = link.get('path') if isinstance(link, dict) else link
                if isinstance(link, str) and link.endswith('.json') and Path(link).is_file():
                    if pins_rebuild(json.loads(Path(link).read_text()), depth + 1):
                        return True
            return any(pins_rebuild(v, depth + 1) for v in value.values())
        if isinstance(value, list):
            return any(pins_rebuild(v, depth + 1) for v in value)
        return False
    return contextlib.nullcontext() if pins_rebuild(stage) else RB.historical()


def repin_historical(stage):
    """Re-hash every recorded pin under the recorded historical runtime substitution."""
    pins = {}
    for group in ('source_sha256', 'input_sha256', 'stopped_evidence_sha256'):
        if not isinstance(stage.get(group), dict) or not stage[group]:
            raise ValueError('Stage lacks pin group: ' + group)
        pins.update({p: (h, group) for p, h in stage[group].items()})
    for key in ('report', 'retention'):
        pins[stage[key]] = (stage[key + '_sha256'], key)
    drift = []
    with lost_build_context(stage):
        for path, (recorded, group) in sorted(pins.items()):
            if not re.fullmatch('[0-9a-f]{64}', str(recorded)):
                raise ValueError('Malformed pin for ' + path)
            if Path(path).is_symlink() or not Path(path).is_file():
                raise ValueError('Pinned input missing: ' + path)
            if FR.sha(Path(path)) != recorded:
                if group == 'source_sha256' and Path(path).name not in MUST_MATCH_SOURCES:
                    drift.append(path)  # later host-source edits; recorded, boot-relevant files stay fatal
                    continue
                raise ValueError('Pinned %s differs: %s' % (group, path))
    return drift


def check_runtime(stage, report):
    """Expectations for the new run use the actual rebuilt hashes (RB.current)."""
    substitution = RB.load()
    recorded = stage.get('runtime_substitution', {})
    if recorded.get('record_sha256') != substitution['record_sha256'] or recorded.get('substitutions') != substitution['substitutions']:
        raise ValueError('Stage runtime substitution differs from the tracked rebuild record')
    actual = {p: actual_sha(p) for p in substitution['substitutions']}
    if stage.get('runtime_actual_sha256') != actual:
        raise ValueError('Runtime actual hashes differ from those recorded by the stage')
    binary, manifest = report.get('binary'), report.get('build_manifest_path')
    for path, key in ((binary, 'binary_sha256'), (manifest, 'build_manifest_sha256')):
        entry = substitution['substitutions'].get(str(path))
        if entry is None:
            raise ValueError('Report runtime path is not a recorded substituted input: ' + str(path))
        if RB.current(path, entry['pinned_sha256']) != entry['rebuilt_sha256'] or actual[str(path)] != entry['rebuilt_sha256']:
            raise ValueError('Current runtime differs from expectation: ' + str(path))
        if report.get(key) != entry['rebuilt_sha256']:
            raise ValueError('Fresh report did not run the rebuilt runtime: ' + key)
    return Path(binary), Path(manifest), substitution, actual


def validate(args):
    path, stage, report_path = read_stage(args.stage, args.stage_sha256)
    drift = repin_historical(stage)
    if actual_sha(report_path) != stage['report_sha256']:
        raise ValueError('Fresh report changed')
    report = bounded_record(report_path)
    if report.get('kind') != 't8030_recovery_ramdisk_experiment':
        raise ValueError('Stage report is not the owned recovery run')
    binary, manifest, substitution, actual = check_runtime(stage, report)
    for name, key in (('boot.py', 'runner_sha256'), ('qmp_control.py', 'control_source_sha256')):
        if actual_sha(SOURCE / name) != report.get(key):
            raise ValueError('Sibling %s differs from the staged run; use its reviewed host tree' % name)
    with lost_build_context(stage):
        context = {'session': {'recovery_profile': {'sha256': report['profile_sha256']},
                               'sources': {'boot.py': report['runner_sha256'],
                                           'qmp_control.py': report['control_source_sha256']}}}
        CO.check_completed_report(context, report_path)
        tool = OV.validate_tools(args.overlay_tools_root)
        chain = OV.load_stopped_overlay(report_path, tool)
    if len(chain['layers']) != 3:
        raise ValueError('Fresh stage must retain exactly three layers, found %d' % len(chain['layers']))
    profile = args.profile.expanduser().absolute()
    if not profile.is_file():
        raise ValueError('Missing verified profile: ' + str(profile))
    _, profile_inputs = load_profile(profile)
    return {'path': path, 'stage': stage, 'report_path': report_path, 'report': report,
            'binary': binary, 'manifest': manifest, 'substitution': substitution, 'actual': actual,
            'chain': {k: chain[k] for k in ('layers',) if k in chain}, 'profile': profile,
            'profile_inputs': profile_inputs, 'source_drift': drift, 'tool_root': args.overlay_tools_root.resolve()}


def command_for(v, output, seconds):
    return [sys.executable, str(SOURCE / 'boot.py'), '--profile', str(v['profile']),
            '--binary', str(v['binary']), '--manifest', str(v['manifest']),
            '--overlay-tools-root', str(v['tool_root']),
            '--overlay-base-report', str(v['report_path']), '--disk-boot', '--launchd-unsecure-cache',
            '--control-mailbox', '--guest-hid-serial', '--guest-errors', '--capture-interval', '10',
            '--seconds', str(seconds), '--output', str(output)]


def preflight(parent):
    found = CO.no_running_emulator()
    free = shutil.disk_usage(parent).free
    if free < MIN_FREE:
        raise ValueError('Require at least 4GiB free at %s; have %d bytes' % (parent, free))
    return found


def normal_result(run_report_path, v):
    report_path = Path(run_report_path)
    before = actual_sha(report_path)
    report = bounded_record(report_path)
    if (report.get('attempt_completed') is not True or report.get('error') or report.get('exit_code') != 0 or
            report.get('kind') != 't8030_direct_root_experiment'):
        raise ValueError('Installed attempt did not finish normally')
    for key, expected in (('profile_path', str(v['profile'])), ('profile_sha256', actual_sha(v['profile'])),
                          ('binary_sha256', RB.current(v['binary'], v['report']['binary_sha256'])),
                          ('build_manifest_sha256', RB.current(v['manifest'], v['report']['build_manifest_sha256'])),
                          ('runner_sha256', actual_sha(SOURCE / 'boot.py')),
                          ('control_source_sha256', actual_sha(SOURCE / 'qmp_control.py'))):
        if report.get(key) != expected:
            raise ValueError('Installed report input/source differs: ' + key)
    if report.get('inputs') != v['profile_inputs']:
        raise ValueError('Installed report profile input dictionary differs')
    if '-initrd' in report.get('invocation', []):
        raise ValueError('Installed attempt unexpectedly used a recovery initrd')
    base = report.get('overlay_base_report', {})
    if (base.get('report') != str(v['report_path']) or base.get('report_sha256') != v['stage']['report_sha256'] or
            base.get('stopped_manifest_sha256') != v['stage']['retention_sha256']):
        raise ValueError('Installed report used a different fresh stage')
    if report.get('probe_journey'):
        raise ValueError('Unexpected fixture journey on generic fresh runtime')
    shutdown = CO.PRESERVE.verify_shutdown(report_path.parent, report)
    if actual_sha(report_path) != before:
        raise ValueError('Report changed during verification')
    return {'status': 'normal-installed-attempt-no-app-success-assertion', 'report': str(report_path),
            'report_sha256': before, 'shutdown': shutdown, 'app_execution_asserted': False,
            'scope': 'Normal runner completion only; migration, unlock, app launch, pixels and preservation remain separate.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stage', type=Path, required=True, help='fresh-runtime.json from stage-fresh-runtime.py')
    parser.add_argument('--stage-sha256', required=True)
    parser.add_argument('--overlay-tools-root', type=Path, default=OV.DEFAULT_TOOLS)
    parser.add_argument('--profile', type=Path, default=DEFAULT_PROFILE)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--seconds', type=int, default=1200)
    parser.add_argument('--dry-run', action='store_true', help='validate and print argv; launch nothing')
    args = parser.parse_args()
    if not 1 <= args.seconds <= 7000:
        parser.error('--seconds must be 1..7000')
    output = process = None
    handles = []
    previous_umask = os.umask(0o077)
    try:
        destination = CO.IMPORTER.external_output(args.output)
        v = validate(args)
        command = command_for(v, destination / 'boot', args.seconds)
        if '-initrd' in command or '--ramdisk-boot' in command:
            raise ValueError('Refusing initrd/ramdisk boot')
        proc_check = preflight(destination.parent)
        if args.dry_run:
            print(json.dumps({'dry_run': True, 'validated': True, 'argv': command, 'layers': len(v['chain']['layers']),
                              'source_drift': v['source_drift'], 'launched': False}, indent=2))
            return 0
        output = destination
        output.mkdir(mode=0o700)
        CO.write_new(output / 'INCOMPLETE.json', {'status': 'incomplete-attempt', 'started': time.time()})
        CO.write_new(output / 'launch.json', {
            'command': command, 'stage': str(v['path']), 'stage_sha256': args.stage_sha256,
            'runtime_substitution': v['substitution'], 'runtime_actual_sha256': v['actual'],
            'source_drift': v['source_drift'], 'proc_preflight': proc_check,
            'scope': 'One explicit installed attempt; no automatic gestures, retries or app success assertion'})
        preflight(destination.parent)
        for name in ('stdout.log', 'stderr.log'):
            handles.append((output / name).open('xb'))
        process = subprocess.Popen(command, stdout=handles[0], stderr=handles[1], start_new_session=True)
        stat = Path(f'/proc/{process.pid}/stat').read_text()
        process.inferno_start_ticks = int(stat[stat.rfind(')') + 2:].split()[19])
        CO.write_new(output / 'runner-process.json', {'pid': process.pid, 'start_ticks': process.inferno_start_ticks,
                                                      'proc_stat': stat, 'command': command, 'started': time.time()})
        if process.wait(timeout=args.seconds + 300) != 0:
            raise ValueError('Installed runner returned failure')
        if Path(f'/proc/{process.pid}').exists() or CO.owned_group_members(process):
            raise ValueError('Owned runner/session remains alive')
        result = normal_result(output / 'boot/report.json', v)
        CO.write_new(output / 'completed-run.json', result)
        (output / 'INCOMPLETE.json').unlink()
        print(json.dumps({'completed_run': str(output / 'completed-run.json'),
                          'sha256': actual_sha(output / 'completed-run.json'), 'app_execution_asserted': False}))
        return 0
    except BaseException as exc:
        cleanup = {}
        if process is not None:
            try:
                cleanup = CO.stop_owned_group(process)
            except Exception as stop_error:
                cleanup = {'error': str(stop_error), 'owned_runner_pid': process.pid}
        if output is not None and output.is_dir():
            CO.write_new(output / 'failure.json', {'status': 'failed-incomplete-do-not-promote', 'type': type(exc).__name__,
                                                  'error': str(exc), 'cleanup': cleanup, 'app_execution_asserted': False})
        print('boot-fresh failed: ' + str(exc), file=sys.stderr)
        return 1
    finally:
        os.umask(previous_umask)
        for handle in handles:
            handle.close()


if __name__ == '__main__':
    raise SystemExit(main())
