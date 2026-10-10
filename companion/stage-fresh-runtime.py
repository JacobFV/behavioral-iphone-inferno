#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Install exact fresh owned-runtime artifacts on a verified renderer child."""
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
SOURCE = Path(__file__).resolve().parent
from boot import load_profile
from disk_overlay import load_stopped_overlay
from initial_volumes import bounded_record
from fresh_runtime_stage import verify_content, validate_inputs, sources
import fresh_runtime_stage as FR
import runtime_rebuild as RB
import shutil
CO=FR.CO;sha=FR.sha
RB.install(FR)
unchanged=FR.KS.SK.unchanged


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
    for name in ('renderer-stage','artifacts'):
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
    # Historical pins of the lost emulator build are satisfied only by the
    # recorded rebuild; this run's own report records the actual rebuilt hashes.
    historical = RB.historical(); historical.__enter__()
    try:
        substitution = RB.load()
        source_pins = sources(); source_pins[str(Path(RB.__file__).resolve())] = sha(Path(RB.__file__))
        destination = CO.IMPORTER.external_output(args.output)
        preflight = CO.no_running_emulator()
        paths, input_pins, verified = validate_inputs(args)
        if shutil.disk_usage(destination.parent).free < 4 << 30:
            raise ValueError('Require4GiB free for sparse runtime clone, recovery and logs')
        destination.mkdir(mode=0o700)
        output = destination
        CO.write_new(output / 'INCOMPLETE.json', {'status': 'incomplete-no-phase-promotion', 'ipa_runtime_ready': False})
        prepared = output / 'recovery'
        command=[sys.executable,str(SOURCE/'native-probe/prepare.py'),'--profile',str(paths['profile']),'--raw-ramdisk',str(paths['raw']),'--probe',str(paths['probe']),'--hfsplus',str(paths['hfsplus']),*verified['fragment'],'--output',str(prepared)]
        execute(command,output,'prepare',180)
        readbacks={}
        expected_readbacks={**verified['readbacks'],'job':('/System/Library/LaunchDaemons/org.inferno.probe.prepare-root.plist',str(prepared/'org.inferno.probe.prepare-root.plist'))}
        manifest=verified['manifest']
        for index,item in enumerate(manifest['files']):
            expected_readbacks['app-'+str(index)]=('/usr/share/inferno-imported-app/'+item['path'],str(paths['app_manifest'].parent/manifest['bundle']['relative_path']/item['path']))
        _,_,_,plan_bytes=FR.IA.validate(paths['app_manifest'],verified['artifacts']['inputs']['app_manifest']['sha256'])
        if (prepared/'imported-app.plan').read_bytes()!=plan_bytes:raise ValueError('Imported generated plan differs')
        expected_readbacks['import-plan']=('/usr/share/inferno-imported-app.plan',str(prepared/'imported-app.plan'))
        for name,(guest,expected) in expected_readbacks.items():
            target=output/('readback-'+name)
            execute([str(paths['hfsplus']),str(prepared/'ramdisk.raw'),'extract',guest,str(target)],output,'extract-'+name,60)
            if sha(target)!=sha(Path(expected)):raise ValueError('HFS readback mismatch: '+name)
            readbacks[name]={'path':str(target),'sha256':sha(target),'bytes':target.stat().st_size}
        sizes={'hid_input':readbacks['hid']['bytes'],'readiness':readbacks['readiness']['bytes']+readbacks['readiness-job']['bytes'],'unlock_helper':readbacks['unlock']['bytes'],'exec_wrapper':readbacks['wrapper']['bytes'],'system_launcher':readbacks['launcher']['bytes'],'launchd_cache':readbacks['cache']['bytes']}
        if sizes!=verified['artifact_sizes']:raise ValueError('Actual HFS readback sizes differ from pinned artifacts')
        job = plistlib.loads((output / 'readback-job').read_bytes())
        if job != {'Label': 'org.inferno.probe.prepare-root', 'ProgramArguments': ['/usr/bin/inferno-prepare-root','--disposable-root-copy','--existing-volumes','--install-readiness','--install-cache','--install-exec-wrapper','--install-system-launcher','--install-unlock-helper','--install-imported-app','--install-hid-input'], 'RunAtLoad': True, 'StandardOutPath': '/dev/console', 'StandardErrorPath': '/dev/console', 'UserName': 'root'}:
            raise ValueError('Unexpected preparation job fields/operations')
        profile_path = prepared / 'profile.json'
        prepared_profile, profile_inputs = load_profile(profile_path)
        flags = prepared_profile['provenance']['helper_flags']
        expected_flags = {key: key=='disk_helper_existing'
                          for key in ('disk_helper_roles', 'disk_helper_existing', 'disk_helper_gigalocker',
                                      'disk_helper_data', 'disk_helper_verify_data', 'disk_helper_keybag', 'export_reports')}
        if flags != expected_flags:
            raise ValueError('Prepared profile helper operations differ')
        imported=prepared_profile['provenance']['imported_app']
        if imported['manifest_sha256']!=verified['artifacts']['inputs']['app_manifest']['sha256'] or imported['tree_sha256']!=manifest['tree_sha256'] or imported['guest_path']!=manifest['bundle']['guest_path'] or imported.get('allow_identical_fixture_tree_sha256') is not None:raise ValueError('Prepared imported target differs')
        if prepared_profile['provenance'].get('sep_payload_sha256') or prepared_profile['provenance'].get('multitouch_img4_sha256') or prepared_profile['provenance'].get('system_app_executable'):raise ValueError('Unexpected extra preparation mutation')
        context = {'session': {'recovery_profile': {'path': str(profile_path), 'sha256': sha(profile_path)},
                               'sources': {'boot.py': source_pins[str(SOURCE / 'boot.py')], 'qmp_control.py': source_pins[str(SOURCE / 'qmp_control.py')]}},
                   'verified_runtime': verified}
        report_dir = output / 'recovery-run'
        command = [sys.executable, str(SOURCE / 'boot.py'), '--profile', str(profile_path), '--overlay-base-report',str(paths['base_report']), '--overlay-tools-root', str(args.overlay_tools_root),
                   '--ramdisk-boot', '--control-mailbox', '--guest-errors', '--binary', str(paths['binary']),
                   '--manifest', str(paths['build_manifest']), '--seconds', '1200', '--output', str(report_dir)]
        CO.write_new(output / 'launch.json', {'command': command, 'source_sha256': source_pins, 'input_sha256': input_pins,
                    'verified_inputs': verified, 'profile_inputs': profile_inputs, 'readbacks': readbacks,
                    'proc_preflight': preflight, 'scope': 'Owned runtime/app/cache installation only; not runtime ready'})
        unchanged({**source_pins, **input_pins})
        FR.F.IMPORTER.validate_manifest(paths['app_manifest'])
        CO.no_running_emulator()
        check_base_metadata(verified)
        if shutil.disk_usage(output).free < 4 << 30:
            raise ValueError('Require4GiB free immediately before recovery')
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
                raise ValueError('Runner exited before verified owned runtime preparation')
            if serial.exists():
                if serial.stat().st_size > 64 << 20:
                    raise ValueError('Serial exceeds64MiB')
                raw = serial.read_bytes()
                if b'INFERNO_PREP_COMPLETE:' in raw:
                    checkpoint = verify_content(raw,manifest,sizes)
                    checkpoint.update(captured_time=time.time(), eligible=False)
                    CO.write_new(output / 'content-check.json', checkpoint)
                    break
            time.sleep(1)
        if checkpoint is None:
            raise TimeoutError('Fresh runtime deadline expired')
        execute([sys.executable, str(SOURCE / 'qmp_control.py'), '--report', str(report_dir), 'finish-observation'], output, 'finish', 45)
        if runner.wait(timeout=180) != 0 or CO.owned_group_members(runner):
            raise ValueError('Runner did not exit normally and completely')
        report_path = report_dir / 'report.json'
        stopped_pins = {str(p): sha(p) for p in (report_path, serial, report_dir / 'control-transcript.jsonl',
                        report_dir / 'qmp-transcript.jsonl', output / 'content-check.json', output / 'finish.stdout')}
        report = CO.check_completed_report(context, report_path)
        runtime = verified['runtime_inputs']
        if report['inputs'] != profile_inputs or report['binary_sha256'] != RB.current(runtime['binary'], runtime['binary_sha256']) or report['build_manifest_sha256'] != RB.current(runtime['build_manifest'], runtime['build_manifest_sha256']):
            raise ValueError('Stopped runtime input mismatch')
        expected_base={k:verified['base'][k] for k in ('report','report_sha256','stopped_manifest','stopped_manifest_sha256')}
        if report.get('overlay_base_report')!=expected_base or report.get('root_base'):raise ValueError('Unexpected renderer root lineage')
        inherited=report.get('auxiliary_base',{})
        if inherited.get('report')!=verified['base']['report'] or inherited.get('report_sha256')!=verified['base']['report_sha256'] or inherited.get('copied_before_use') is not True:raise ValueError('Renderer paired lineage differs')
        expected_aux={k.removesuffix('.raw'):v for k,v in verified['base']['auxiliary'].items() if k!='root.qcow2'}
        if inherited.get('namespaces')!=expected_aux:raise ValueError('Renderer exact six paired namespaces differ')
        check_base_metadata(verified)
        final_serial = serial.read_bytes()
        if hashlib.sha256(final_serial[:checkpoint['serial_bytes']]).hexdigest() != checkpoint['serial_sha256']:
            raise ValueError('Final serial does not preserve exact pre-finish checkpoint prefix')
        content = verify_content(final_serial,manifest,sizes)
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
            raise ValueError('Owned runtime stage must retain exactly three layers')
        FR.F.IMPORTER.validate_manifest(paths['app_manifest'])
        unchanged({**source_pins, **input_pins, **stopped_pins})
        check_base_metadata(verified)
        CO.write_new(output/'fresh-runtime.json',{'schema':'inferno.fresh-runtime-stage.v1','status':'owned-runtime-staged-not-booted','ipa_runtime_ready':False,
                     'report':str(report_path),'report_sha256':stopped_pins[str(report_path)],'retention':str(retention),'retention_sha256':stopped_pins[str(retention)],
                     'content':content,'content_checkpoint_sha256':stopped_pins[str(output/'content-check.json')],'backing_depth':len(chain['layers']),
                     'source_sha256':source_pins,'input_sha256':input_pins,'stopped_evidence_sha256':stopped_pins,
                     'predecessor':{'path':str(args.renderer_stage),'sha256':args.renderer_stage_sha256},'artifacts':{'path':str(args.artifacts),'sha256':args.artifacts_sha256},'runtime_substitution':substitution,
                     'scope':'Exact owned helper/app/launchd configuration copies read back and normally unmounted. No keybag initialization or Data seeding repeated. No installed boot, migration, unlock or app interaction proof.'})
        (output / 'INCOMPLETE.json').unlink()
        print(json.dumps({'result': str(output / 'fresh-runtime.json'), 'sha256': sha(output / 'fresh-runtime.json'), 'ipa_runtime_ready': False}))
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
        print('stage-fresh-runtime failed: ' + str(exc), file=sys.stderr)
        return 1
    finally:
        historical.__exit__(None, None, None)
        os.umask(previous_umask)
        for log in logs:
            log.close()


if __name__ == '__main__':
    raise SystemExit(main())
