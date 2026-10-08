#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""One fresh original SEP/keybag recovery stage; no runtime-readiness claim."""
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
from initial_volumes import bounded_record
from grow_data import verify_content as verify_growth, REQUESTED_BYTES
from sep_keybag import verify_content, SEP_SHA256, SEP_SHA384, SEP_BYTES, SEP_MEMBER
import zipfile

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
    paths += [SOURCE / 'stage-sep-keybag.py', SOURCE / 'sep_keybag.py', SOURCE / 'grow_data.py', SOURCE / 'initial_volumes.py', SOURCE / 'stage-grow-data.py', SOURCE / 'flatten-verified-data.py', SOURCE / 'data_verify.py', SOURCE / 'data_seed.py', SOURCE / 'os-image/grow-gpt4k.py',
              *[SOURCE / 'native-probe' / n for n in ('grow-container.c','grow-libSystem.tbd','grow-entitlements.plist')],
              *[SOURCE / 'native-probe' / n for n in ('prepare.py', 'imported_app.py', 'prepare-root.c', 'imported-app.c', 'libSystem.tbd', 'entitlements.plist')]]
    return {str(p): sha(p) for p in paths}


def unchanged(pins):
    for p, expected in pins.items():
        if sha(p) != expected:
            raise ValueError('Pinned input/source changed: ' + p)


def validate_inputs(args):
    paths = {}
    pins = {}
    for name in ('profile', 'raw_recovery_record', 'grown_stage', 'helper_build', 'probe', 'hfsplus', 'binary', 'build_manifest', 'sep_payload', 'sep_record'):
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
    sep = bounded_record(paths['sep_record'])
    if sep.get('output') != str(paths['sep_payload']) or args.sep_payload_sha256 != SEP_SHA256 or paths['sep_payload'].stat().st_size != SEP_BYTES or sep.get('sha256') != SEP_SHA256 or sep.get('sha384') != SEP_SHA384 or sep.get('archive_member') != SEP_MEMBER or sep.get('transformations') != 'ZIP extraction only; no decryption, ticket, signature, or payload edits':
        raise ValueError('Only exact unchanged official SEP input is supported')
    archive = Path(profile['provenance']['ipsw_path'])
    if str(archive) != sep.get('source_archive') or sha(archive) != profile['provenance']['ipsw_sha256']:
        raise ValueError('SEP archive/profile differs')
    pins[str(archive)] = profile['provenance']['ipsw_sha256']
    with zipfile.ZipFile(archive) as zipped:
        item = zipped.getinfo(SEP_MEMBER)
        if item.file_size != SEP_BYTES or item.flag_bits & 1: raise ValueError('SEP ZIP member size/encryption differs')
        h = hashlib.sha256(); h384 = hashlib.sha384()
        with zipped.open(item) as stream:
            while block := stream.read(1 << 20): h.update(block); h384.update(block)
        if h.hexdigest() != SEP_SHA256 or h384.hexdigest() != SEP_SHA384: raise ValueError('SEP member digest differs')
        manifest_info = zipped.getinfo('BuildManifest.plist')
        if manifest_info.file_size > 16 << 20: raise ValueError('Oversized BuildManifest')
        manifest_raw = zipped.read(manifest_info)
        if hashlib.sha256(manifest_raw).hexdigest() != profile['provenance']['manifest_sha256']: raise ValueError('BuildManifest profile binding differs')
        manifest = plistlib.loads(manifest_raw)
        matches = [i['Manifest']['SEP'] for i in manifest['BuildIdentities'] if i.get('Info', {}).get('DeviceClass') == 'n104ap' and i.get('Info', {}).get('Variant') == 'Research Developer Erase Install (IPSW)']
        if len(matches) != 1 or matches[0]['Info']['Path'] != SEP_MEMBER or matches[0]['Digest'].hex() != SEP_SHA384: raise ValueError('Exact SEP BuildIdentity digest missing')
    stage_path = paths['grown_stage']; stage = bounded_record(stage_path)
    if stage.get('schema') != 'inferno.grown-data-stage.v1' or stage.get('status') != 'grown-not-runtime-ready' or stage.get('ipa_runtime_ready') is not False or stage.get('backing_depth') != 2:
        raise ValueError('Expected successful grown-data depth2 stage')
    if any((stage_path.parent / n).exists() for n in ('INCOMPLETE.json','failure.json')): raise ValueError('Growth stage incomplete/failed')
    paths['base_report'] = pin(stage['report'],stage['report_sha256'])
    retention = pin(stage['retention'],stage['retention_sha256'])
    if paths['base_report'] != stage_path.parent/'recovery-run/report.json' or retention != paths['base_report'].parent/'stopped-disk-hashes.json': raise ValueError('Growth output layout differs')
    for p, expected in stage['stopped_evidence_sha256'].items(): pin(p,expected); pins[p]=expected
    pins[str(paths['base_report'])]=stage['report_sha256'];pins[str(retention)]=stage['retention_sha256']
    serial=paths['base_report'].parent/'serial.log';checkpoint_path=stage_path.parent/'content-check.json';controls_path=paths['base_report'].parent/'control-transcript.jsonl';finish=stage_path.parent/'finish.stdout'
    for p in (serial,checkpoint_path,controls_path,finish,paths['base_report'].parent/'qmp-transcript.jsonl'):
        if str(p) not in stage['stopped_evidence_sha256']: raise ValueError('Missing growth raw evidence pin')
    if serial.stat().st_size>64<<20: raise ValueError('Growth serial too large')
    raw=serial.read_bytes();checkpoint=bounded_record(checkpoint_path)
    if verify_growth(raw)!=stage['content'] or sha(checkpoint_path)!=stage['content_checkpoint_sha256'] or {k:v for k,v in checkpoint.items() if k not in ('captured_time','eligible')}!=verify_growth(raw[:checkpoint['serial_bytes']]) or checkpoint.get('eligible') is not False: raise ValueError('Growth raw/checkpoint differs')
    controls=[json.loads(x) for x in controls_path.read_bytes().splitlines() if x]
    if len(controls)!=1: raise ValueError('Expected sole growth finish')
    c=controls[0];request=json.loads(c['raw'])
    if request['execute']!='finish-observation' or request['arguments']!={} or hashlib.sha256(c['raw'].encode()).hexdigest()!=c['sha256'] or not checkpoint['captured_time']<request['created']<=c['time'] or c['response']['return'].get('finish_requested') is not True or bounded_record(finish)!=c['response']: raise ValueError('Growth finish not bound to raw checkpoint')
    report=bounded_record(paths['base_report'])
    for filename,key in [('boot.py','runner_sha256'),('qmp_control.py','control_source_sha256')]:
        if [h for p,h in stage['source_sha256'].items() if Path(p).name==filename]!=[report[key]]: raise ValueError('Growth source/report differs')
    for filename in ('grow_data.py','grow-container.c','grow-libSystem.tbd','grow-entitlements.plist'):
        current=SOURCE/('native-probe/'+filename if filename!='grow_data.py' else filename)
        if [h for p,h in stage['source_sha256'].items() if Path(p).name==filename]!=[sha(current)]: raise ValueError('Growth implementation differs')
    CO.check_completed_report({'session':{'recovery_profile':{'sha256':report['profile_sha256']},'sources':{'boot.py':report['runner_sha256'],'qmp_control.py':report['control_source_sha256']}}},paths['base_report'])
    freeze_path=stage_path.parent/'freeze-record.json';pins[str(freeze_path)]=sha(freeze_path);freeze=bounded_record(freeze_path);unchanged({str(freeze_path):pins[str(freeze_path)]})
    records=bounded_record(retention)
    if set(records)!={'root.qcow2',*CO.AUXILIARY_SIZES} or set(freeze['files'])!=set(records): raise ValueError('Growth paired seven missing')
    for name,entry in records.items():
        f=freeze['files'][name]
        if entry.get('forensic_only') or f['path']!=entry['path'] or f['sha256']!=entry['sha256'] or CO.identity(entry['path'])!=f['after']: raise ValueError('Growth frozen namespace differs')
    tools=validate_tools(args.overlay_tools_root);chain=load_stopped_overlay(paths['base_report'],tools)
    host=stage['host_growth']
    if len(chain['layers'])!=2 or chain['virtual_size']!=32<<30 or chain['layers'][-1]['sha256']!=host['output_sha256'] or host['partition_bytes']!=REQUESTED_BYTES or host['apfs_resized'] is not False: raise ValueError('Growth raw wrapper/chain differs')
    # Reuse the reviewed predecessor validator with original growth-helper inputs,
    # never rebuild or execute that helper. It validates flatten/raw comparison,
    # old read-only Data evidence, immutable source identities and paired auxiliaries.
    gs=importlib.util.spec_from_file_location('keybag_growth_support',SOURCE/'stage-grow-data.py');growth=importlib.util.module_from_spec(gs);gs.loader.exec_module(growth)
    launch_path=stage_path.parent/'launch.json';pins[str(launch_path)]=sha(launch_path);launch=bounded_record(launch_path)
    original_builds=[]
    for path,digest in launch['input_sha256'].items():
        if Path(path).name=='build.json':
            record=bounded_record(pin(path,digest))
            if record.get('status')=='built-owned-grow-helper-only; no guest execution yet':original_builds.append((path,digest))
    if len(original_builds)!=1: raise ValueError('Ambiguous original growth helper build')
    inherited=argparse.Namespace(**vars(args));inherited.helper_build=Path(original_builds[0][0]);inherited.helper_build_sha256=original_builds[0][1];inherited.flattened_data=Path(stage['predecessor']['path']);inherited.flattened_data_sha256=stage['predecessor']['sha256']
    _,prior_pins,prior=growth.validate_inputs(inherited);pins.update(prior_pins)
    if host['source']!=prior['flat']['raw']['path'] or host['source_sha256']!=prior['flat']['raw']['sha256'] or report.get('auxiliary_base',{}).get('report')!=str(Path(prior['flat']['auxiliary_state'])/'report.json') or report['auxiliary_base']['namespaces']!={k.removesuffix('.raw'):v for k,v in prior['base']['auxiliary'].items()}: raise ValueError('Growth predecessor/paired state differs')
    for item in freeze['files'].values():
        if CO.identity(item['path'])!=item['after']:raise ValueError('Growth metadata changed during validation')
    return paths,pins,{'profile_inputs':inputs,'base':chain,'tool':tools,'base_metadata':{p:CO.identity(p) for p in {x['path'] for x in chain['layers']}|{x['path'] for x in chain['auxiliary'].values()}|set(prior['base_metadata'])}}


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
    for name in ('profile', 'raw-recovery-record', 'grown-stage', 'helper-build', 'probe', 'hfsplus', 'binary', 'build-manifest', 'sep-payload', 'sep-record'):
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
        prepared = output / 'recovery'
        command = [sys.executable, str(SOURCE / 'native-probe/prepare.py'), '--profile', str(paths['profile']),
                   '--raw-ramdisk', str(paths['raw']), '--probe', str(paths['probe']), '--hfsplus', str(paths['hfsplus']),
                   '--disk-helper', str(paths['helper']), '--disk-helper-existing', '--disk-helper-keybag', '--sep-payload', str(paths['sep_payload']), '--sep-sha256', SEP_SHA256, '--output', str(prepared)]
        execute(command, output, 'prepare', 180)
        readbacks = {}
        for name, guest, expected in [('helper', '/usr/bin/inferno-prepare-root', paths['helper']),
                                     ('probe', '/usr/bin/inferno-probe', paths['probe']),
                                     ('sep', '/usr/share/inferno-sep-payload', paths['sep_payload']),
                                     ('job', '/System/Library/LaunchDaemons/org.inferno.probe.prepare-root.plist', prepared / 'org.inferno.probe.prepare-root.plist')]:
            target = output / ('readback-' + name)
            execute([str(paths['hfsplus']), str(prepared / 'ramdisk.raw'), 'extract', guest, str(target)], output, 'extract-' + name, 60)
            if sha(target) != sha(expected):
                raise ValueError('HFS readback mismatch: ' + name)
            readbacks[name] = {'path': str(target), 'sha256': sha(target)}
        job = plistlib.loads((output / 'readback-job').read_bytes())
        if job != {'Label': 'org.inferno.probe.prepare-root', 'ProgramArguments': ['/usr/bin/inferno-prepare-root', '--disposable-root-copy', '--existing-volumes', '--copy-sep', '--create-keybag'], 'RunAtLoad': True, 'StandardOutPath': '/dev/console', 'StandardErrorPath': '/dev/console', 'UserName': 'root'}:
            raise ValueError('Unexpected preparation job fields/operations')
        profile_path = prepared / 'profile.json'
        prepared_profile, profile_inputs = load_profile(profile_path)
        flags = prepared_profile['provenance']['helper_flags']
        if {k for k,v in flags.items() if v} != {'disk_helper_existing','disk_helper_keybag'} or prepared_profile['provenance']['sep_payload_sha256'] != SEP_SHA256:
            raise ValueError('Unexpected prepared profile SEP/helper flags')
        context = {'session': {'recovery_profile': {'path': str(profile_path), 'sha256': sha(profile_path)},
                               'sources': {'boot.py': source_pins[str(SOURCE / 'boot.py')], 'qmp_control.py': source_pins[str(SOURCE / 'qmp_control.py')]}},
                   'verified_runtime': verified}
        report_dir = output / 'recovery-run'
        command = [sys.executable, str(SOURCE / 'boot.py'), '--profile', str(profile_path), '--overlay-base-report', str(paths['base_report']), '--overlay-tools-root', str(args.overlay_tools_root),
                   '--ramdisk-boot', '--control-mailbox', '--guest-errors', '--binary', str(paths['binary']),
                   '--manifest', str(paths['build_manifest']), '--seconds', '1200', '--output', str(report_dir)]
        CO.write_new(output / 'launch.json', {'command': command, 'source_sha256': source_pins, 'input_sha256': input_pins,
                    'verified_inputs': verified, 'profile_inputs': profile_inputs, 'readbacks': readbacks,
                    'proc_preflight': preflight, 'scope': 'One fresh original SEP/keybag recovery; no destination SEP byte or runtime proof'})
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
                raise ValueError('Runner exited before verified fresh SEP/keybag path')
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
            raise TimeoutError('SEP/keybag deadline expired')
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
        if len(chain['layers']) != 3:
            raise ValueError('Keybag output must retain exactly three layers')
        CO.write_new(output / 'sep-keybag.json', {'schema': 'inferno.sep-keybag-stage.v1',
                     'status': 'fresh-keybag-created-not-runtime-ready', 'ipa_runtime_ready': False,
                     'sep_destination_bytes_verified': False, 'postgrowth_full_data_verified': False,
                     'report': str(report_path), 'report_sha256': stopped_pins[str(report_path)],
                     'retention': str(retention), 'retention_sha256': stopped_pins[str(retention)],
                     'content': content, 'content_checkpoint_sha256': stopped_pins[str(output / 'content-check.json')],
                     'backing_depth': len(chain['layers']), 'source_sha256': source_pins, 'stopped_evidence_sha256': stopped_pins,
                     'predecessor': {'path': str(paths['grown_stage']), 'sha256': args.grown_stage_sha256},
                     'scope': 'Fresh original simulated-SEP/effaceable/MobileKeyBag path only; no destination SEP byte comparison, postgrowth whole Data verification or runtime readiness'})
        (output / 'INCOMPLETE.json').unlink()
        print(json.dumps({'result': str(output / 'sep-keybag.json'), 'sha256': sha(output / 'sep-keybag.json'), 'ipa_runtime_ready': False}))
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
        print('sep-keybag failed: ' + str(exc), file=sys.stderr)
        return 1
    finally:
        os.umask(previous_umask)
        for log in logs:
            log.close()


if __name__ == '__main__':
    raise SystemExit(main())
