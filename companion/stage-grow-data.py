#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""One bounded original-API APFS growth stage; never a runtime-ready result."""
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
import struct
import shutil
from boot import load_profile
from disk_overlay import validate_base, validate_tools, load_stopped_overlay
from initial_volumes import bounded_record
from grow_data import verify_content, REQUESTED_BYTES

SOURCE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('initial_coordinator_support', SOURCE / 'stage-import.py')
CO = importlib.util.module_from_spec(spec)
spec.loader.exec_module(CO)
sha = CO.digest
fspec = importlib.util.spec_from_file_location("growth_flatten_support", SOURCE / "flatten-verified-data.py")
FL = importlib.util.module_from_spec(fspec); fspec.loader.exec_module(FL)


def pin(path, expected):
    path = Path(path).absolute()
    if path.resolve(strict=True) != path or not path.is_file() or path.is_symlink() or sha(path) != expected:
        raise ValueError('Missing/aliased/changed pinned artifact: ' + str(path))
    return path


def sources():
    pins = FL.source_pins()
    for path in [SOURCE / 'stage-grow-data.py', SOURCE / 'grow_data.py', SOURCE / 'os-image/grow-gpt4k.py',
                 *[SOURCE / 'native-probe' / n for n in ('prepare.py', 'imported_app.py', 'grow-container.c', 'grow-libSystem.tbd', 'grow-entitlements.plist')]]:
        pins[str(path)] = sha(path)
    return pins


def unchanged(pins):
    for p, expected in pins.items():
        if sha(p) != expected:
            raise ValueError('Pinned input/source changed: ' + p)


def validate_inputs(args):
    paths = {}
    pins = {}
    for name in ('profile', 'raw_recovery_record', 'flattened_data', 'helper_build', 'probe', 'hfsplus', 'binary', 'build_manifest'):
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
    if helper.get('status') != 'built-owned-grow-helper-only; no guest execution yet':
        raise ValueError('Expected actual unchanged growth-helper build record')
    for name in ('grow-container.c', 'grow-libSystem.tbd', 'grow-entitlements.plist'):
        if [v for p, v in helper['sources'].items() if Path(p).name == name] != [sha(SOURCE / 'native-probe' / name)]:
            raise ValueError('Helper source differs: ' + name)
    paths['helper'] = pin(paths['helper_build'].parent / 'inferno-grow', helper['outputs']['inferno-grow']['sha256'])
    pins[str(paths['helper'])] = helper['outputs']['inferno-grow']['sha256']
    if any((paths['helper_build'].parent / n).exists() for n in ('INCOMPLETE.json', 'failure.json')):
        raise ValueError('Helper build remains incomplete')
    build = bounded_record(paths['build_manifest'])
    if build.get('binary', {}).get('sha256') != args.binary_sha256:
        raise ValueError('Emulator manifest does not bind binary')
    flat = bounded_record(paths['flattened_data'])
    if flat.get('schema') != 'inferno.flattened-verified-data.v1' or flat.get('status') != 'flattened-verified-data-not-runtime-ready' or flat.get('ipa_runtime_ready') is not False:
        raise ValueError('Expected verified flattened Data result')
    if any((paths['flattened_data'].parent / n).exists() for n in ('INCOMPLETE.json', 'failure.json')):
        raise ValueError('Flatten remains incomplete/failed')
    unchanged({**flat['source_sha256'], **flat['evidence_sha256']})
    pins.update(flat['source_sha256'])
    pins.update(flat['evidence_sha256'])
    phase = FL.validate_phase(Path(flat['data_verified']['path']), flat['data_verified']['sha256'], 2, pins)
    tools = validate_tools(args.overlay_tools_root)
    chain = load_stopped_overlay(Path(phase['report']), tools)
    if FL.normalized(chain) != FL.normalized(flat['source_after']) or FL.normalized(flat['source_before']) != FL.normalized(flat['source_after']) or FL.identities(chain) != flat['identities_after'] or flat['identities_before'] != flat['identities_after']:
        raise ValueError('Flatten source identities changed')
    paired = {name: value for name, value in chain['auxiliary'].items() if name != 'root.qcow2'}
    if flat['paired_auxiliary'] != paired or flat['auxiliary_state'] != str(Path(phase['report']).parent) or flat['auxiliary_report_sha256'] != phase['report_sha256'] or flat['auxiliary_retention_sha256'] != phase['retention_sha256']:
        raise ValueError('Flatten paired auxiliary provenance differs')
    paths['root'] = Path(flat['raw']['path'])
    raw = validate_base(paths['root'], flat['raw']['sha256'], allow_attestation=False)
    if raw != flat['raw'] or raw['bytes'] != 8 << 30 or FL.gpt_headers(paths['root']) != flat['gpt']:
        raise ValueError('Flattened raw identity/GPT differs')
    if tools != flat['tool']:
        raise ValueError('Flatten tool identity differs')
    folder = paths['flattened_data'].parent
    marker_path = folder / 'KEEP-OVERLAY-BACKING.json'
    pins[str(marker_path)] = sha(marker_path)
    marker = bounded_record(marker_path)
    if marker.get('provenance_sha256') != args.flattened_data_sha256 or marker.get('backing') != raw or marker.get('paired_auxiliary_must_be_retained') != paired or marker.get('retirement_prohibited_while_dependent_overlays_exist') is not True:
        raise ValueError('Flatten KEEP provenance differs')
    original = chain['layers'][0]['path']
    operations = {
        'convert': ['convert', '-f', 'qcow2', '-O', 'raw', '-S', '4k', original, str(paths['root'])],
        'raw-info': ['info', '--output=json', '-f', 'raw', str(paths['root'])],
        'logical-compare': ['compare', '-f', 'qcow2', '-F', 'raw', original, str(paths['root'])],
    }
    previous = 0
    for label, tail in operations.items():
        command_path = folder / (label + '.json')
        pins[str(command_path)] = sha(command_path)
        command = bounded_record(command_path)
        if command.get('argv') != [tools['binary'], *tail] or command.get('exit_code') != 0 or command.get('error') or not previous <= command['started'] <= command['finished']:
            raise ValueError('Flatten actual command record differs: ' + label)
        previous = command['finished']
        for stream in ('stdout', 'stderr'):
            log = folder / (label + '.' + stream)
            pin(log, command[stream + '_sha256']); pins[str(log)] = command[stream + '_sha256']
    if (folder / 'logical-compare.stdout').read_text().strip() != 'Images are identical.':
        raise ValueError('Flatten logical comparison did not report equality')
    info = bounded_record(folder / 'raw-info.stdout')
    if info.get('format') != 'raw' or info.get('virtual-size') != 8 << 30:
        raise ValueError('Flatten original qemu-img geometry differs')
    paths['auxiliary_state'] = Path(flat['auxiliary_state'])
    pins[str(paths['root'])] = flat['raw']['sha256']
    return paths, pins, {'profile_inputs': inputs, 'base': {'layers': [raw], 'auxiliary': paired},
                        'flat': flat, 'tool': tools, 'data_phase': phase,
                        'base_metadata': {q: CO.identity(q) for q in {str(paths['root']), *FL.identities(chain)}}}


def check_base_metadata(verified):
    for path, value in verified['base_metadata'].items():
        if CO.identity(path) != value:
            raise ValueError('Original source/paired namespace metadata changed')


def grow_host(paths, verified, output):
    if shutil.disk_usage(output).free < 34 << 30:
        raise ValueError('Require32GiB logical output plus2GiB reserve')
    original = paths['root']; original_identity = CO.identity(original)
    grown = output / 'grown-root.raw'
    execute([sys.executable, str(SOURCE / 'os-image/grow-gpt4k.py'), '--source', str(original),
             '--source-sha256', verified['flat']['raw']['sha256'], '--output', str(grown)], output, 'grow-gpt', 1200)
    record = bounded_record(grown.with_suffix('.raw.json'))
    if record.get('source') != str(original) or record.get('source_sha256') != verified['flat']['raw']['sha256'] or record.get('output') != str(grown) or record.get('output_bytes') != 32 << 30 or record.get('apfs_resized') is not False or record.get('partition_start_lba') != 256 or record.get('partition_end_lba') != 8388602 or record.get('partition_bytes') != REQUESTED_BYTES or record.get('script_sha256') != sha(SOURCE / 'os-image/grow-gpt4k.py'):
        raise ValueError('Unexpected GPT growth record')
    FL.gpt_headers(grown)
    # Independently compare original APFS extent, not the newly enlarged zero area.
    def extent(path):
        digest = hashlib.sha256(); remaining = 7695577088
        with path.open('rb') as stream:
            stream.seek(1048576)
            while remaining:
                block = stream.read(min(8 << 20, remaining))
                if not block: raise ValueError('Truncated APFS extent')
                digest.update(block); remaining -= len(block)
        return digest.hexdigest()
    if extent(original) != record['original_apfs_sha256'] or extent(grown) != record['original_apfs_sha256'] or sha(original) != verified['flat']['raw']['sha256'] or CO.identity(original) != original_identity or sha(grown) != record['output_sha256']:
        raise ValueError('Original source or preserved APFS extent changed')
    before = CO.identity(grown)
    if grown.is_symlink() or grown.stat().st_nlink != 1 or before['st_mode'] & 0o777 != 0o600:
        raise ValueError('Grown raw is not an exclusive private new file')
    CO.PRESERVE.descriptor_check([grown])
    fd = os.open(grown, os.O_RDWR | os.O_NOFOLLOW)
    try:
        if {k: getattr(os.fstat(fd), k) for k in before} != before: raise ValueError('Grown inode changed before freeze')
        os.fsync(fd); os.fchmod(fd, 0o444)
    finally: os.close(fd)
    frozen = validate_base(grown, record['output_sha256'], allow_attestation=False)
    if any(CO.identity(grown)[k] != before[k] for k in ('st_dev','st_ino','st_size','st_mtime_ns')):
        raise ValueError('Unexpected raw freeze change')
    CO.write_new(output / 'KEEP-OVERLAY-BACKING.json', {'backing': frozen, 'retirement_prohibited_while_dependent_overlays_exist': True})
    CO.write_new(output / 'host-growth.json', {'record': record, 'source_identity_before': original_identity, 'source_identity_after': CO.identity(original), 'new_before_freeze': before, 'backing': frozen})
    paths['root'] = grown
    verified['base']['layers'] = [frozen]
    verified['grown'] = frozen
    return record


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
    for name in ('profile', 'raw-recovery-record', 'flattened-data', 'helper-build', 'probe', 'hfsplus', 'binary', 'build-manifest'):
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
        destination.mkdir(mode=0o700)
        output = destination
        CO.write_new(output / 'INCOMPLETE.json', {'status': 'incomplete-no-phase-promotion', 'ipa_runtime_ready': False})
        host_growth = grow_host(paths, verified, output)
        unchanged({**source_pins, **input_pins})
        check_base_metadata(verified)
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
        if any(prepared_profile['provenance']['helper_flags'].values()):
            raise ValueError('Growth helper must receive no preparation mode flags')
        context = {'session': {'recovery_profile': {'path': str(profile_path), 'sha256': sha(profile_path)},
                               'sources': {'boot.py': source_pins[str(SOURCE / 'boot.py')], 'qmp_control.py': source_pins[str(SOURCE / 'qmp_control.py')]}},
                   'verified_runtime': verified}
        report_dir = output / 'recovery-run'
        command = [sys.executable, str(SOURCE / 'boot.py'), '--profile', str(profile_path), '--root-image', str(paths['root']),
                   '--root-sha256', verified['grown']['sha256'], '--root-overlay', '--overlay-tools-root', str(args.overlay_tools_root),
                   '--auxiliary-state', str(paths['auxiliary_state']), '--ramdisk-boot', '--control-mailbox', '--guest-errors', '--binary', str(paths['binary']),
                   '--manifest', str(paths['build_manifest']), '--seconds', '1200', '--output', str(report_dir)]
        CO.write_new(output / 'launch.json', {'command': command, 'source_sha256': source_pins, 'input_sha256': input_pins,
                    'verified_inputs': verified, 'profile_inputs': profile_inputs, 'readbacks': readbacks,
                    'proc_preflight': preflight, 'scope': 'One original APFS growth recovery; two-file consistency only, not IPA-ready'})
        unchanged({**source_pins, **input_pins})
        CO.no_running_emulator()
        check_base_metadata(verified)
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
                raise ValueError('Runner exited before verified growth phase')
            if serial.exists():
                if serial.stat().st_size > 64 << 20:
                    raise ValueError('Serial exceeds64MiB')
                raw = serial.read_bytes()
                if b'INFERNO_GROW_COMPLETE ' in raw:
                    checkpoint = verify_content(raw)
                    checkpoint.update(captured_time=time.time(), eligible=False)
                    CO.write_new(output / 'content-check.json', checkpoint)
                    break
            time.sleep(1)
        if checkpoint is None:
            raise TimeoutError('Original growth deadline expired')
        execute([sys.executable, str(SOURCE / 'qmp_control.py'), '--report', str(report_dir), 'finish-observation'], output, 'finish', 45)
        if runner.wait(timeout=180) != 0 or CO.owned_group_members(runner):
            raise ValueError('Runner did not exit normally and completely')
        report_path = report_dir / 'report.json'
        stopped_pins = {str(p): sha(p) for p in (report_path, serial, report_dir / 'control-transcript.jsonl',
                        report_dir / 'qmp-transcript.jsonl', output / 'content-check.json', output / 'finish.stdout')}
        report = CO.check_completed_report(context, report_path)
        if report['inputs'] != profile_inputs or report['binary_sha256'] != args.binary_sha256 or report['build_manifest_sha256'] != args.build_manifest_sha256:
            raise ValueError('Stopped runtime input mismatch')
        if report['root_base'] != {'path': str(paths['root']), 'sha256': verified['grown']['sha256'], 'bytes': 32 << 30, 'copied_before_use': False, 'retained_immutable_backing': True}:
            raise ValueError('Unexpected grown root backing')
        auxiliary = report.get('auxiliary_base', {})
        expected_aux = {name.removesuffix('.raw'): {k: item[k] for k in ('path', 'sha256', 'bytes')}
                        for name, item in verified['base']['auxiliary'].items()}
        if auxiliary.get('report') != str(paths['auxiliary_state'] / 'report.json') or auxiliary.get('report_sha256') != verified['data_phase']['report_sha256'] or auxiliary.get('namespaces') != expected_aux or auxiliary.get('copied_before_use') is not True:
            raise ValueError('Original six paired auxiliary states differ')
        check_base_metadata(verified)
        final_serial = serial.read_bytes()
        if hashlib.sha256(final_serial[:checkpoint['serial_bytes']]).hexdigest() != checkpoint['serial_sha256']:
            raise ValueError('Final serial does not preserve exact pre-finish checkpoint prefix')
        content = verify_content(final_serial)
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
        check_base_metadata(verified)
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
        if len(chain['layers']) != 2: raise ValueError('Growth must produce raw-backed depth2')
        CO.write_new(output / 'grown-data.json', {'schema': 'inferno.grown-data-stage.v1',
                     'status': 'grown-not-runtime-ready', 'ipa_runtime_ready': False,
                     'report': str(report_path), 'report_sha256': stopped_pins[str(report_path)],
                     'retention': str(retention), 'retention_sha256': stopped_pins[str(retention)],
                     'content': content, 'content_checkpoint_sha256': stopped_pins[str(output / 'content-check.json')],
                     'backing_depth': len(chain['layers']), 'source_sha256': source_pins, 'stopped_evidence_sha256': stopped_pins,
                     'predecessor': {'path': str(paths['flattened_data']), 'sha256': args.flattened_data_sha256},
                     'host_growth': host_growth, 'scope': 'Original resize and two System fingerprints only; no postgrowth whole-Data equality or runtime readiness'})
        (output / 'INCOMPLETE.json').unlink()
        print(json.dumps({'result': str(output / 'grown-data.json'), 'sha256': sha(output / 'grown-data.json'), 'ipa_runtime_ready': False}))
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
        print('grow-data failed: ' + str(exc), file=sys.stderr)
        return 1
    finally:
        os.umask(previous_umask)
        for log in logs:
            log.close()


if __name__ == '__main__':
    raise SystemExit(main())
