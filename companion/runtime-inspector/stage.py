#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""One fixed read-only runtime-cache observation; never a runtime base."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import plistlib
import subprocess
import sys
import time
HERE = Path(__file__).resolve().parent
SOURCE = HERE.parent
sys.path.insert(0, str(SOURCE))
from boot import load_profile
from disk_overlay import load_stopped_overlay
from initial_volumes import bounded_record
from result import verify_content
import keybag_state
import shutil

spec = importlib.util.spec_from_file_location('inspector_coordinator_support', SOURCE / 'stage-import.py')
CO = importlib.util.module_from_spec(spec); spec.loader.exec_module(CO)
sha = CO.digest


def pin(path, expected):
    path = Path(path).absolute()
    if path.resolve(strict=True) != path or not path.is_file() or path.is_symlink() or sha(path) != expected:
        raise ValueError('Missing/aliased/changed pinned artifact: ' + str(path))
    return path


def sources():
    pins = keybag_state.source_pins()
    for path in [*HERE.glob('*.py'), *[HERE / n for n in ('inspect.c', 'sha256.h', 'libSystem.tbd', 'entitlements.plist')],
                 SOURCE / 'native-probe/prepare.py', SOURCE / 'native-probe/imported_app.py']:
        pins[str(path)] = sha(path)
    return pins


def unchanged(pins):
    for path, expected in pins.items():
        if sha(path) != expected:
            raise ValueError('Pinned input/source changed: ' + path)


def validate_inputs(args):
    paths = {}; pins = {}
    for name in ('profile', 'raw_recovery_record', 'keybag_stage', 'helper_build', 'probe', 'hfsplus', 'binary', 'build_manifest'):
        paths[name] = pin(getattr(args, name), getattr(args, name + '_sha256'))
        pins[str(paths[name])] = getattr(args, name + '_sha256')
    prior = keybag_state.validate(paths['keybag_stage'], args.keybag_stage_sha256, pins, tools_root=args.overlay_tools_root)
    profile, inputs = load_profile(paths['profile'])
    # Same supplied recovery/profile/tool inputs as the verified predecessor;
    # only the separately owned helper changes for this read-only observation.
    for name in ('profile', 'raw_recovery_record', 'probe', 'hfsplus', 'binary', 'build_manifest'):
        if prior['preparation_inputs'][name] != paths[name]:
            raise ValueError('Inspector input differs from verified keybag input: ' + name)
    extraction = bounded_record(paths['raw_recovery_record'])
    paths['raw'] = pin(extraction['output']['path'], extraction['output']['sha256'])
    pins[str(paths['raw'])] = extraction['output']['sha256']
    helper = bounded_record(paths['helper_build'])
    if helper.get('status') != 'built-owned-runtime-inspector-only; no guest execution yet':
        raise ValueError('Expected completed owned runtime inspector build')
    for name in ('inspect.c', 'sha256.h', 'libSystem.tbd', 'entitlements.plist'):
        if [h for path,h in helper['sources'].items() if Path(path).name == name] != [sha(HERE / name)]:
            raise ValueError('Inspector source differs: ' + name)
    for path, expected in {**helper['sources'], **helper['producer_sources']}.items():
        pin(path, expected); pins[path] = expected
    if any((paths['helper_build'].parent / name).exists() for name in ('INCOMPLETE.json', 'failure.json')):
        raise ValueError('Helper build failed/incomplete')
    paths['helper'] = pin(paths['helper_build'].parent / 'inferno-runtime-inspector', helper['outputs']['inferno-runtime-inspector']['sha256'])
    pins[str(paths['helper'])] = helper['outputs']['inferno-runtime-inspector']['sha256']
    chain = prior['chain']
    paths['base_report'] = Path(prior['manifest']['report'])
    if len(chain['layers']) != 3:
        raise ValueError('Expected keybag depth3; observation alone consumes final depth4')
    return paths,pins,{'profile_inputs':inputs, 'base':chain,'tool':prior['tool'],
        'base_metadata':{q:CO.identity(q) for q in {x['path'] for x in chain['layers']} | {x['path'] for x in chain['auxiliary'].values()}}}


def check_base_metadata(verified):
    for path, identity in verified['base_metadata'].items():
        if CO.identity(path) != identity:
            raise ValueError('Initial ancestor/paired namespace metadata changed: ' + path)


def execute(command, output, label, timeout):
    started = time.time()
    process = None
    failure = None
    cleanup = {}
    with (output / (label + '.stdout')).open('xb') as out, (output / (label + '.stderr')).open('xb') as err:
        try:
            process = subprocess.Popen(command, stdout=out, stderr=err, start_new_session=True)
            value = Path(f'/proc/{process.pid}/stat').read_text()
            process.inferno_start_ticks = int(value[value.rfind(')') + 2:].split()[19])
            process.wait(timeout=timeout)
            if process.returncode or CO.owned_group_members(process):
                raise ValueError(label + ' failed or left child-session members')
        except BaseException as exc:
            failure = exc
            if process is not None:
                cleanup = CO.stop_owned_group(process)
    record = {'argv': command, 'started': started, 'finished': time.time(),
              'exit_code': process.returncode if process else None, 'cleanup': cleanup,
              'error': str(failure) if failure else None,
              'stdout_sha256': sha(output / (label + '.stdout')), 'stderr_sha256': sha(output / (label + '.stderr'))}
    CO.write_new(output / (label + '.json'), record)
    if failure is not None:
        raise failure
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('profile', 'raw-recovery-record', 'keybag-stage', 'helper-build', 'probe', 'hfsplus', 'binary', 'build-manifest'):
        parser.add_argument('--' + name, type=Path, required=True)
        parser.add_argument('--' + name + '-sha256', required=True)
    parser.add_argument('--overlay-tools-root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    output = None
    runner = None
    logs = []
    # Fresh namespaces must be private regardless of the invoking shell umask.
    # Child preparation/boot processes inherit this; never chmod existing inputs.
    previous_umask = os.umask(0o077)
    try:
        source_pins = sources()
        destination = CO.IMPORTER.external_output(args.output)
        preflight = CO.no_running_emulator()
        paths, input_pins, verified = validate_inputs(args)
        if shutil.disk_usage(destination.parent).free < 2 << 30:
            raise ValueError('Require2GiB free for sparse observation, recovery and logs')
        destination.mkdir(mode=0o700)
        output = destination
        CO.write_new(output / 'INCOMPLETE.json', {'status': 'incomplete-no-phase-promotion', 'ipa_runtime_ready': False})
        prepared = output / 'recovery'
        command = [sys.executable, str(SOURCE / 'native-probe/prepare.py'), '--profile', str(paths['profile']),
                   '--raw-ramdisk', str(paths['raw']), '--probe', str(paths['probe']), '--hfsplus', str(paths['hfsplus']),
                   '--disk-helper', str(paths['helper']), '--output', str(prepared)]
        execute(command, output, 'prepare', 180)
        readbacks = {}
        for name, guest, expected in [('helper', '/usr/bin/inferno-prepare-root', paths['helper']),
                                     ('probe', '/usr/bin/inferno-probe', paths['probe']),
                                     ('job', '/System/Library/LaunchDaemons/org.inferno.probe.prepare-root.plist', prepared / 'org.inferno.probe.prepare-root.plist')]:
            target = output / ('readback-' + name)
            execute([str(paths['hfsplus']), str(prepared / 'ramdisk.raw'), 'extract', guest, str(target)], output, 'extract-' + name, 60)
            if sha(target) != sha(expected):
                raise ValueError('HFS readback mismatch: ' + name)
            readbacks[name] = {'path': str(target), 'sha256': sha(target)}
        job = plistlib.loads((output / 'readback-job').read_bytes())
        if job != {'Label': 'org.inferno.probe.prepare-root', 'ProgramArguments': ['/usr/bin/inferno-prepare-root', '--disposable-root-copy'], 'RunAtLoad': True, 'StandardOutPath': '/dev/console', 'StandardErrorPath': '/dev/console', 'UserName': 'root'}:
            raise ValueError('Unexpected preparation job fields/operations')
        profile_path = prepared / 'profile.json'
        prepared_profile, profile_inputs = load_profile(profile_path)
        flags = prepared_profile['provenance']['helper_flags']
        expected_flags = {key: False
                          for key in ('disk_helper_roles', 'disk_helper_existing', 'disk_helper_gigalocker',
                                      'disk_helper_data', 'disk_helper_verify_data', 'disk_helper_keybag', 'export_reports')}
        if flags != expected_flags:
            raise ValueError('Prepared profile helper operations differ')
        context = {'session': {'recovery_profile': {'path': str(profile_path), 'sha256': sha(profile_path)},
                               'sources': {'boot.py': source_pins[str(SOURCE / 'boot.py')], 'qmp_control.py': source_pins[str(SOURCE / 'qmp_control.py')]}},
                   'verified_runtime': verified}
        report_dir = output / 'recovery-run'
        command = [sys.executable, str(SOURCE / 'boot.py'), '--profile', str(profile_path), '--overlay-base-report', str(paths['base_report']), '--overlay-tools-root', str(args.overlay_tools_root),
                   '--ramdisk-boot', '--control-mailbox', '--guest-errors', '--binary', str(paths['binary']),
                   '--manifest', str(paths['build_manifest']), '--seconds', '1200', '--output', str(report_dir)]
        CO.write_new(output / 'launch.json', {'command': command, 'source_sha256': source_pins, 'input_sha256': input_pins,
                    'verified_inputs': verified, 'profile_inputs': profile_inputs, 'readbacks': readbacks,
                    'proc_preflight': preflight, 'scope': 'Fixed read-only System cache observation; not a runtime base'})
        unchanged({**source_pins, **input_pins})
        CO.no_running_emulator()
        check_base_metadata(verified)
        if shutil.disk_usage(output).free < 2 << 30:
            raise ValueError('Require2GiB free immediately before recovery')
        for name in ('stdout.log', 'stderr.log'):
            logs.append((output / name).open('xb'))
        runner = subprocess.Popen(command, stdout=logs[0], stderr=logs[1], start_new_session=True)
        procstat = Path(f'/proc/{runner.pid}/stat').read_text()
        runner.inferno_start_ticks = int(procstat[procstat.rfind(')') + 2:].split()[19])
        CO.write_new(output / 'runner-process.json', {'pid': runner.pid, 'start_ticks': runner.inferno_start_ticks, 'command': command, 'proc_stat': procstat})
        serial = report_dir / 'serial.log'
        deadline = time.monotonic() + 1200
        checkpoint = None
        while time.monotonic() < deadline:
            if runner.poll() is not None:
                raise ValueError('Runner exited before verified cache observation')
            if serial.exists():
                if serial.stat().st_size > 64 << 20:
                    raise ValueError('Serial exceeds64MiB')
                raw = serial.read_bytes()
                if b'INFERNO_INSPECT_RESULT status=' in raw:
                    checkpoint, exported = verify_content(raw)
                    with (output / 'launchd.plist').open('xb') as stream:
                        stream.write(exported); stream.flush(); os.fsync(stream.fileno())
                    checkpoint.update(captured_time=time.time(), eligible=False)
                    CO.write_new(output / 'content-check.json', checkpoint)
                    break
            time.sleep(1)
        if checkpoint is None:
            raise TimeoutError('Cache observation deadline expired')
        execute([sys.executable, str(SOURCE / 'qmp_control.py'), '--report', str(report_dir), 'finish-observation'], output, 'finish', 45)
        if runner.wait(timeout=180) != 0 or CO.owned_group_members(runner):
            raise ValueError('Runner did not exit normally and completely')
        report_path = report_dir / 'report.json'
        stopped_pins = {str(p): sha(p) for p in (report_path, serial, report_dir / 'control-transcript.jsonl',
                        report_dir / 'qmp-transcript.jsonl', output / 'content-check.json', output / 'finish.stdout')}
        report = CO.check_completed_report(context, report_path)
        if report['inputs'] != profile_inputs or report['binary_sha256'] != args.binary_sha256 or report['build_manifest_sha256'] != args.build_manifest_sha256:
            raise ValueError('Stopped runtime input mismatch')
        expected_base = {k: verified['base'][k] for k in ('report', 'report_sha256', 'stopped_manifest', 'stopped_manifest_sha256')}
        if report.get('overlay_base_report') != expected_base or report.get('root_base'):
            raise ValueError('Unexpected root lineage')
        inherited = report.get('auxiliary_base', {})
        if inherited.get('report') != str(paths['base_report']) or inherited.get('report_sha256') != verified['base']['report_sha256'] or inherited.get('copied_before_use') is not True:
            raise ValueError('Paired auxiliary lineage differs')
        expected_aux = {k.removesuffix('.raw'): v for k, v in verified['base']['auxiliary'].items() if k != 'root.qcow2'}
        if inherited.get('namespaces') != expected_aux:
            raise ValueError('Paired auxiliary namespace identities differ')
        check_base_metadata(verified)
        final_serial = serial.read_bytes()
        if hashlib.sha256(final_serial[:checkpoint['serial_bytes']]).hexdigest() != checkpoint['serial_sha256']:
            raise ValueError('Final serial does not preserve exact pre-finish checkpoint prefix')
        content, final_export = verify_content(final_serial)
        if final_export != (output / 'launchd.plist').read_bytes():
            raise ValueError('Final export differs from prefinish reconstruction')
        stopped_pins[str(output / 'launchd.plist')] = content['launchd']['sha256']
        controls = [json.loads(line) for line in (report_dir / 'control-transcript.jsonl').read_bytes().split(b'\n') if line]
        if len(controls) != 1:
            raise ValueError('Unexpected control submissions')
        control = controls[0]
        request = json.loads(control['raw'])
        if request['execute'] != 'finish-observation' or request['arguments'] != {} or hashlib.sha256(control['raw'].encode()).hexdigest() != control['sha256'] or not checkpoint['captured_time'] < request['created'] <= control['time']:
            raise ValueError('Finish does not follow content checkpoint')
        if control['response']['return'].get('finish_requested') is not True or bounded_record(output / 'finish.stdout') != control['response']:
            raise ValueError('Finish response mismatch')
        unchanged({**source_pins, **input_pins, **stopped_pins})
        frozen = CO.freeze_new_disks(report_path, report, context, output)
        retention = report_dir / 'stopped-disk-hashes.json'
        CO.PRESERVE.preserve(report_path, retention, False)
        stopped_pins[str(retention)] = sha(retention)
        records = bounded_record(retention)
        for name, value in frozen['files'].items():
            if records[name]['sha256'] != value['sha256'] or CO.identity(value['path']) != value['after']:
                raise ValueError('Frozen new namespace changed')
        # Existing overlay loader independently checks the normal stopped seven-file
        # layout, exact current identities and immutable raw backing dependency.
        chain = load_stopped_overlay(report_path, verified['tool'])
        unchanged({**source_pins, **input_pins, **stopped_pins})
        check_base_metadata(verified)
        if len(chain['layers']) != 4:
            raise ValueError('Observation must retain exactly four layers; never use it as a runtime base')
        CO.write_new(output / 'runtime-inspection.json', {'schema': 'inferno.runtime-inspection.v1',
                     'status': 'observed-not-runtime-ready', 'runtime_base_eligible': False, 'ipa_runtime_ready': False,
                     'launchd_export': {'path': str(output / 'launchd.plist'), 'sha256': content['launchd']['sha256']},
                     'report': str(report_path), 'report_sha256': stopped_pins[str(report_path)],
                     'retention': str(retention), 'retention_sha256': stopped_pins[str(retention)],
                     'content': content, 'content_checkpoint_sha256': stopped_pins[str(output / 'content-check.json')],
                     'backing_depth': len(chain['layers']), 'source_sha256': source_pins, 'stopped_evidence_sha256': stopped_pins,
                     'predecessor': {'path': str(paths['keybag_stage']), 'sha256': args.keybag_stage_sha256},
                     'scope': 'Fixed System RO launchd export and dyld fullSHA observation only. No cache patch, installation or IPA readiness. This child is not a runtime base.'})
        (output / 'INCOMPLETE.json').unlink()
        print(json.dumps({'result': str(output / 'runtime-inspection.json'), 'sha256': sha(output / 'runtime-inspection.json'), 'ipa_runtime_ready': False}))
        return 0
    except BaseException as exc:
        cleanup = {}
        if runner is not None:
            try:
                cleanup = CO.stop_owned_group(runner)
            except Exception as error:
                cleanup = {'error': str(error), 'owned_runner_pid': runner.pid}
        if output is not None and output.is_dir():
            CO.write_new(output / 'failure.json', {'status': 'failed-forensic-only', 'error': str(exc), 'cleanup': cleanup, 'ipa_runtime_ready': False})
        print('runtime-inspector failed: ' + str(exc), file=sys.stderr)
        return 1
    finally:
        os.umask(previous_umask)
        for log in logs:
            log.close()


if __name__ == '__main__':
    raise SystemExit(main())
