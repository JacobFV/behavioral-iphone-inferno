#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""One original-System role-only recovery stage; never an IPA-ready runtime."""
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
from boot import load_profile
from disk_overlay import validate_base, validate_tools, load_stopped_overlay
from initial_volumes import ORIGINAL_ROOT_SHA, ORIGINAL_APFS_SHA, verify_content, bounded_record

SOURCE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('initial_coordinator_support', SOURCE / 'stage-import.py')
CO = importlib.util.module_from_spec(spec)
spec.loader.exec_module(CO)
sha = CO.digest


def pin(path, expected):
    path = Path(path).absolute()
    if path.resolve(strict=True) != path or not path.is_file() or path.is_symlink() or sha(path) != expected:
        raise ValueError('Missing/aliased/changed pinned artifact: ' + str(path))
    return path


def sources():
    paths, _ = CO.source_inventory()
    paths += [SOURCE / 'stage-initial-volumes.py', SOURCE / 'initial_volumes.py',
              *[SOURCE / 'native-probe' / n for n in ('prepare.py', 'imported_app.py', 'prepare-root.c', 'imported-app.c', 'libSystem.tbd', 'entitlements.plist')]]
    return {str(p): sha(p) for p in paths}


def unchanged(pins):
    for p, expected in pins.items():
        if sha(p) != expected:
            raise ValueError('Pinned input/source changed: ' + p)


def validate_inputs(args):
    paths = {}
    pins = {}
    for name in ('profile', 'raw_recovery_record', 'root_copy_record', 'helper_build', 'probe', 'hfsplus', 'binary', 'build_manifest'):
        path = pin(getattr(args, name), getattr(args, name + '_sha256'))
        paths[name] = path
        pins[str(path)] = getattr(args, name + '_sha256')
    profile, inputs = load_profile(paths['profile'])
    extraction = bounded_record(paths['raw_recovery_record'])
    if extraction.get('schema') != 'inferno.plain-recovery-extraction.v1' or extraction.get('status') != 'extracted-plain-payload-not-booted':
        raise ValueError('Expected completed plain recovery extraction record')
    if extraction['profile'] != {'path': str(paths['profile']), 'sha256': args.profile_sha256} or extraction['source']['sha256'] != profile['ramdisk']['sha256'] or extraction['payload']['type'] != 'rdsk':
        raise ValueError('Recovery/profile binding differs')
    paths['raw'] = pin(extraction['output']['path'], extraction['output']['sha256'])
    pins[str(paths['raw'])] = extraction['output']['sha256']
    if any((paths['raw'].parent / n).exists() for n in ('INCOMPLETE.json', 'failure.json')):
        raise ValueError('Raw extraction remains incomplete')
    helper = bounded_record(paths['helper_build'])
    if helper.get('status') != 'built-owned-preparation-helper-only; no guest execution yet':
        raise ValueError('Expected actual preparation-helper build record')
    for name in ('prepare-root.c', 'imported-app.c', 'libSystem.tbd', 'entitlements.plist'):
        if [v for p, v in helper['sources'].items() if Path(p).name == name] != [sha(SOURCE / 'native-probe' / name)]:
            raise ValueError('Helper source differs: ' + name)
    paths['helper'] = pin(paths['helper_build'].parent / 'inferno-prepare-root', helper['outputs']['inferno-prepare-root']['sha256'])
    pins[str(paths['helper'])] = helper['outputs']['inferno-prepare-root']['sha256']
    if any((paths['helper_build'].parent / n).exists() for n in ('INCOMPLETE.json', 'failure.json')):
        raise ValueError('Helper build remains incomplete')
    build = bounded_record(paths['build_manifest'])
    if build.get('binary', {}).get('sha256') != args.binary_sha256:
        raise ValueError('Emulator manifest does not bind binary')
    copy = bounded_record(paths['root_copy_record'])
    if copy.get('schema') != 'inferno.original-system-copy.v1':
        raise ValueError('Expected explicit new-copy provenance, not modified historical wrapper')
    wrapper_path = pin(copy['wrapper_record']['path'], copy['wrapper_record']['sha256'])
    pins[str(wrapper_path)] = copy['wrapper_record']['sha256']
    wrapper = bounded_record(wrapper_path)
    exact = {'output_sha256': ORIGINAL_ROOT_SHA, 'output_bytes': 8 << 30,
             'apfs_sha256': ORIGINAL_APFS_SHA, 'logical_block_size': 4096,
             'apfs_start_lba': 256, 'apfs_end_lba': 1879058, 'apfs_bytes': 7695577088}
    if any(wrapper.get(k) != v for k, v in exact.items()) or copy['source']['path'] != wrapper['output'] or copy['source']['sha256'] != ORIGINAL_ROOT_SHA or copy['copy']['sha256'] != ORIGINAL_ROOT_SHA:
        raise ValueError('Only exact reproduced original System-only wrapper supported')
    paths['root'] = Path(copy['copy']['path'])
    if not paths['root'].is_absolute() or paths['root'].resolve(strict=True) != paths['root'] or CO.identity(paths['root']) != copy['copy']['identity']:
        raise ValueError('New immutable root copy identity changed')
    if paths['root'].samefile(copy['source']['path']):
        raise ValueError('Copy aliases historical source')
    root = validate_base(paths['root'], ORIGINAL_ROOT_SHA, allow_attestation=False)
    tools = validate_tools(args.overlay_tools_root)
    return paths, pins, {'profile_inputs': inputs, 'base': {'layers': [root], 'auxiliary': {}}, 'tool': tools}


def execute(command, output, label, timeout):
    started = time.time()
    with (output / (label + '.stdout')).open('xb') as out, (output / (label + '.stderr')).open('xb') as err:
        process = subprocess.run(command, stdout=out, stderr=err, timeout=timeout)
    record = {'argv': command, 'started': started, 'finished': time.time(), 'exit_code': process.returncode,
              'stdout_sha256': sha(output / (label + '.stdout')), 'stderr_sha256': sha(output / (label + '.stderr'))}
    CO.write_new(output / (label + '.json'), record)
    if process.returncode:
        raise ValueError(label + ' failed; no retry')
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('profile', 'raw-recovery-record', 'root-copy-record', 'helper-build', 'probe', 'hfsplus', 'binary', 'build-manifest'):
        parser.add_argument('--' + name, type=Path, required=True)
        parser.add_argument('--' + name + '-sha256', required=True)
    parser.add_argument('--overlay-tools-root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    output = None
    runner = None
    logs = []
    try:
        source_pins = sources()
        destination = CO.IMPORTER.external_output(args.output)
        preflight = CO.no_running_emulator()
        paths, input_pins, verified = validate_inputs(args)
        destination.mkdir(mode=0o700)
        output = destination
        CO.write_new(output / 'INCOMPLETE.json', {'status': 'incomplete-no-phase-promotion', 'ipa_runtime_ready': False})
        prepared = output / 'recovery'
        command = [sys.executable, str(SOURCE / 'native-probe/prepare.py'), '--profile', str(paths['profile']),
                   '--raw-ramdisk', str(paths['raw']), '--probe', str(paths['probe']), '--hfsplus', str(paths['hfsplus']),
                   '--disk-helper', str(paths['helper']), '--disk-helper-roles', '--output', str(prepared)]
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
        if job != {'Label': 'org.inferno.probe.prepare-root', 'ProgramArguments': ['/usr/bin/inferno-prepare-root', '--disposable-root-copy', '--role-volumes'], 'RunAtLoad': True, 'StandardOutPath': '/dev/console', 'StandardErrorPath': '/dev/console', 'UserName': 'root'}:
            raise ValueError('Unexpected preparation job fields/operations')
        profile_path = prepared / 'profile.json'
        _, profile_inputs = load_profile(profile_path)
        context = {'session': {'recovery_profile': {'path': str(profile_path), 'sha256': sha(profile_path)},
                               'sources': {'boot.py': source_pins[str(SOURCE / 'boot.py')], 'qmp_control.py': source_pins[str(SOURCE / 'qmp_control.py')]}},
                   'verified_runtime': verified}
        report_dir = output / 'recovery-run'
        command = [sys.executable, str(SOURCE / 'boot.py'), '--profile', str(profile_path), '--root-image', str(paths['root']),
                   '--root-sha256', ORIGINAL_ROOT_SHA, '--root-overlay', '--overlay-tools-root', str(args.overlay_tools_root),
                   '--ramdisk-boot', '--control-mailbox', '--guest-errors', '--binary', str(paths['binary']),
                   '--manifest', str(paths['build_manifest']), '--seconds', '1200', '--output', str(report_dir)]
        CO.write_new(output / 'launch.json', {'command': command, 'source_sha256': source_pins, 'input_sha256': input_pins,
                    'verified_inputs': verified, 'profile_inputs': profile_inputs, 'readbacks': readbacks,
                    'proc_preflight': preflight, 'scope': 'One role-only recovery; not IPA-ready'})
        unchanged({**source_pins, **input_pins})
        CO.no_running_emulator()
        if CO.identity(paths['root']) != bounded_record(paths['root_copy_record'])['copy']['identity']:
            raise ValueError('Root metadata changed before launch')
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
                raise ValueError('Runner exited before verified role phase')
            if serial.exists():
                if serial.stat().st_size > 64 << 20:
                    raise ValueError('Serial exceeds64MiB')
                raw = serial.read_bytes()
                if b'INFERNO_PREP_COMPLETE:' in raw:
                    checkpoint = verify_content(raw)
                    checkpoint.update(captured_time=time.time(), eligible=False)
                    CO.write_new(output / 'content-check.json', checkpoint)
                    break
            time.sleep(1)
        if checkpoint is None:
            raise TimeoutError('Role preparation deadline expired')
        execute([sys.executable, str(SOURCE / 'qmp_control.py'), '--report', str(report_dir), 'finish-observation'], output, 'finish', 45)
        if runner.wait(timeout=180) != 0 or CO.owned_group_members(runner):
            raise ValueError('Runner did not exit normally and completely')
        report_path = report_dir / 'report.json'
        report = CO.check_completed_report(context, report_path)
        if report['inputs'] != profile_inputs or report['binary_sha256'] != args.binary_sha256 or report['build_manifest_sha256'] != args.build_manifest_sha256:
            raise ValueError('Stopped runtime input mismatch')
        if report.get('auxiliary_base') or report['root_base'] != {'path': str(paths['root']), 'sha256': ORIGINAL_ROOT_SHA, 'bytes': 8 << 30, 'copied_before_use': False, 'retained_immutable_backing': True}:
            raise ValueError('Unexpected inherited disks')
        content = verify_content(serial.read_bytes())
        controls = [json.loads(line) for line in (report_dir / 'control-transcript.jsonl').read_bytes().split(b'\n') if line]
        if len(controls) != 1:
            raise ValueError('Unexpected control submissions')
        control = controls[0]
        request = json.loads(control['raw'])
        if request['execute'] != 'finish-observation' or request['arguments'] != {} or hashlib.sha256(control['raw'].encode()).hexdigest() != control['sha256'] or not checkpoint['captured_time'] < request['created'] <= control['time']:
            raise ValueError('Finish does not follow content checkpoint')
        if control['response']['return'].get('finish_requested') is not True or bounded_record(output / 'finish.stdout') != control['response']:
            raise ValueError('Finish response mismatch')
        unchanged({**source_pins, **input_pins})
        frozen = CO.freeze_new_disks(report_path, report, context, output)
        retention = report_dir / 'stopped-disk-hashes.json'
        CO.PRESERVE.preserve(report_path, retention, False)
        records = bounded_record(retention)
        for name, value in frozen['files'].items():
            if records[name]['sha256'] != value['sha256'] or CO.identity(value['path']) != value['after']:
                raise ValueError('Frozen new namespace changed')
        # Existing overlay loader independently checks the normal stopped seven-file
        # layout, exact current identities and immutable raw backing dependency.
        chain = load_stopped_overlay(report_path, verified['tool'])
        unchanged({**source_pins, **input_pins})
        CO.write_new(output / 'initial-volumes.json', {'schema': 'inferno.initial-volumes-stage.v1',
                     'status': 'initial-volumes-prepared', 'ipa_runtime_ready': False,
                     'report': str(report_path), 'report_sha256': sha(report_path),
                     'retention': str(retention), 'retention_sha256': sha(retention),
                     'content': content, 'content_checkpoint_sha256': sha(output / 'content-check.json'),
                     'backing_depth': len(chain['layers']), 'source_sha256': source_pins,
                     'scope': 'Only Preboot/xART/Hardware and original firmware copy; no Data/keybag/cache/setup/app readiness'})
        (output / 'INCOMPLETE.json').unlink()
        print(json.dumps({'result': str(output / 'initial-volumes.json'), 'sha256': sha(output / 'initial-volumes.json'), 'ipa_runtime_ready': False}))
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
        print('initial-volumes failed: ' + str(exc), file=sys.stderr)
        return 1
    finally:
        for log in logs:
            log.close()


if __name__ == '__main__':
    raise SystemExit(main())
