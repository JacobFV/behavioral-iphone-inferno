# SPDX-License-Identifier: AGPL-3.0-or-later
"""Read-only typed validation of a normally stopped fresh keybag preparation."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import plistlib
from initial_volumes import bounded_record
from disk_overlay import DEFAULT_TOOLS, load_stopped_overlay, validate_tools
from sep_keybag import verify_content, SEP_SHA256

SOURCE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('keybag_state_producer',SOURCE/'stage-sep-keybag.py')
SK=importlib.util.module_from_spec(spec);spec.loader.exec_module(SK)
CO=SK.CO;sha=SK.sha


def pin(path, expected, pins):
    path=SK.pin(path,expected);pins[str(path)]=expected;return path


def inspected(path,pins):
    path=Path(path);expected=sha(path);pin(path,expected,pins);value=bounded_record(path)
    if sha(path)!=expected:raise ValueError('Metadata changed during inspection: '+str(path))
    return value


def sources():
    result=SK.sources();result[str(Path(__file__).resolve())]=sha(Path(__file__));return result


def source_pins():
    """Snapshot shared validator and its reviewed producer dependencies."""
    return sources()


def validate(path, expected, pins, tools_root=DEFAULT_TOOLS):
    """Return manifest, exact chain and recovered validated inputs; never launch/mutate."""
    path=pin(path,expected,pins);stage=bounded_record(path)
    if stage.get('schema')!='inferno.sep-keybag-stage.v1' or stage.get('status')!='fresh-keybag-created-not-runtime-ready' or stage.get('backing_depth')!=3 or any(stage.get(k) is not False for k in ('ipa_runtime_ready','sep_destination_bytes_verified','postgrowth_full_data_verified')):
        raise ValueError('Expected exact fresh keybag stage, not runtime or observation result')
    if any((path.parent/n).exists() for n in ('INCOMPLETE.json','failure.json')):raise ValueError('Keybag stage incomplete/failed')
    report_path=pin(stage['report'],stage['report_sha256'],pins);retention=pin(stage['retention'],stage['retention_sha256'],pins)
    if report_path!=path.parent/'recovery-run/report.json' or retention!=report_path.parent/'stopped-disk-hashes.json':raise ValueError('Keybag output layout differs')
    for p,h in stage['stopped_evidence_sha256'].items():pin(p,h,pins)
    serial=report_path.parent/'serial.log';checkpoint_path=path.parent/'content-check.json';controls_path=report_path.parent/'control-transcript.jsonl';finish=path.parent/'finish.stdout'
    for p in (serial,checkpoint_path,controls_path,finish,report_path.parent/'qmp-transcript.jsonl'):
        if str(p) not in stage['stopped_evidence_sha256']:raise ValueError('Missing keybag raw proof pin')
    if serial.stat().st_size>64<<20:raise ValueError('Keybag serial exceeds64MiB')
    raw=serial.read_bytes();checkpoint=bounded_record(checkpoint_path)
    if verify_content(raw)!=stage['content'] or sha(checkpoint_path)!=stage['content_checkpoint_sha256'] or {k:v for k,v in checkpoint.items() if k not in ('captured_time','eligible')}!=verify_content(raw[:checkpoint['serial_bytes']]) or checkpoint.get('eligible') is not False:raise ValueError('Keybag raw/prefix differs')
    controls=[json.loads(x) for x in controls_path.read_bytes().splitlines() if x]
    if len(controls)!=1:raise ValueError('Expected sole normal keybag finish')
    c=controls[0];request=json.loads(c['raw'])
    if request['execute']!='finish-observation' or request['arguments']!={} or hashlib.sha256(c['raw'].encode()).hexdigest()!=c['sha256'] or not checkpoint['captured_time']<request['created']<=c['time'] or c.get('response',{}).get('return',{}).get('finish_requested') is not True or bounded_record(finish)!=c['response']:raise ValueError('Keybag finish lacks exact checkpoint binding')
    report=bounded_record(report_path)
    for name,key in [('boot.py','runner_sha256'),('qmp_control.py','control_source_sha256')]:
        if [h for p,h in stage['source_sha256'].items() if Path(p).name==name]!=[report[key]]:raise ValueError('Producer source/report differs')
    for name in ('sep_keybag.py','stage-sep-keybag.py','prepare-root.c','imported-app.c','libSystem.tbd','entitlements.plist'):
        current=SOURCE/('native-probe/'+name if name.endswith(('.c','.tbd','.plist')) else name)
        if [h for p,h in stage['source_sha256'].items() if Path(p).name==name]!=[sha(current)]:raise ValueError('Reviewed keybag implementation differs: '+name)
    CO.check_completed_report({'session':{'recovery_profile':{'sha256':report['profile_sha256']},'sources':{'boot.py':report['runner_sha256'],'qmp_control.py':report['control_source_sha256']}}},report_path)
    frozen=inspected(path.parent/'freeze-record.json',pins);records=bounded_record(retention)
    if set(records)!={'root.qcow2',*CO.AUXILIARY_SIZES} or set(frozen['files'])!=set(records):raise ValueError('Keybag seven namespaces missing')
    for name,entry in records.items():
        f=frozen['files'][name]
        if entry.get('forensic_only') or entry['path']!=f['path'] or entry['sha256']!=f['sha256'] or CO.identity(entry['path'])!=f['after']:raise ValueError('Keybag frozen identity differs')
    # Recover only declarative input references from the actual prepare command.
    # None of these records is executed; existing producer validation checks them.
    launch=inspected(path.parent/'launch.json',pins);prepare=inspected(path.parent/'prepare.json',pins)
    argv=prepare['argv'];values={};switches=[];i=2
    if prepare.get('exit_code')!=0 or prepare.get('error') or Path(argv[1]).name!='prepare.py':raise ValueError('Original preparation did not succeed')
    while i<len(argv):
        key=argv[i]
        if key in ('--disk-helper-existing','--disk-helper-keybag'):
            if key in switches:raise ValueError('Duplicate preparation switch')
            switches.append(key);i+=1
        else:
            if not key.startswith('--') or key in values or i+1>=len(argv):raise ValueError('Malformed preparation argument')
            values[key]=argv[i+1];i+=2
    if set(switches)!={'--disk-helper-existing','--disk-helper-keybag'} or set(values)!={'--profile','--raw-ramdisk','--probe','--hfsplus','--disk-helper','--sep-payload','--sep-sha256','--output'} or values['--output']!=str(path.parent/'recovery') or values['--sep-sha256']!=SEP_SHA256:raise ValueError('Unexpected keybag preparation flags')
    input_pins=launch['input_sha256'];metadata=[]
    for p,h in input_pins.items():
        if Path(p).suffix=='.json':metadata.append((pin(p,h,pins),h,bounded_record(p)))
    def one(predicate):
        selected=[(p,h) for p,h,d in metadata if predicate(d)]
        if len(selected)!=1:raise ValueError('Ambiguous typed producer input')
        return selected[0]
    typed={'raw_recovery_record':one(lambda d:d.get('schema')=='inferno.plain-recovery-extraction.v1'),
           'helper_build':one(lambda d:d.get('status')=='built-owned-preparation-helper-only; no guest execution yet'),
           'sep_record':one(lambda d:d.get('component')=='SEP' and d.get('sha256')==SEP_SHA256)}
    args={'overlay_tools_root':Path(tools_root),'grown_stage':Path(stage['predecessor']['path']),'grown_stage_sha256':stage['predecessor']['sha256']}
    for name,option in [('profile','--profile'),('probe','--probe'),('hfsplus','--hfsplus'),('sep_payload','--sep-payload')]:
        args[name]=Path(values[option]);args[name+'_sha256']=input_pins[values[option]]
    for name,(p,h) in typed.items():args[name]=p;args[name+'_sha256']=h
    for name,key in [('binary','binary'),('build_manifest','build_manifest_path')]:args[name]=Path(report[key]);args[name+'_sha256']=input_pins[report[key]]
    _,prior_pins,prior=SK.validate_inputs(argparse.Namespace(**args));pins.update(prior_pins)
    if values['--disk-helper']!=str(args['helper_build'].parent/'inferno-prepare-root') or values['--raw-ramdisk']!=bounded_record(args['raw_recovery_record'])['output']['path']:raise ValueError('Actual helper/raw input differs')
    prepared_profile=path.parent/'recovery/profile.json';pin(prepared_profile,report['profile_sha256'],pins)
    _, prepared_inputs=SK.load_profile(prepared_profile)
    if prepared_inputs!=report['inputs']:raise ValueError('Prepared runtime profile inputs differ')
    if report.get('binary_sha256')!=args['binary_sha256'] or report.get('build_manifest_sha256')!=args['build_manifest_sha256']:raise ValueError('Runtime binary or manifest differs from pinned preparation inputs')
    job_path=path.parent/'readback-job';pin(job_path,launch['readbacks']['job']['sha256'],pins)
    if plistlib.loads(job_path.read_bytes())!={'Label':'org.inferno.probe.prepare-root','ProgramArguments':['/usr/bin/inferno-prepare-root','--disposable-root-copy','--existing-volumes','--copy-sep','--create-keybag'],'RunAtLoad':True,'StandardOutPath':'/dev/console','StandardErrorPath':'/dev/console','UserName':'root'}:raise ValueError('Actual keybag job differs')
    for name in ('helper','probe','sep'):
        p=path.parent/('readback-'+name);pin(p,launch['readbacks'][name]['sha256'],pins)
        expected_hash=sha(Path(values['--disk-helper'])) if name=='helper' else args['probe_sha256'] if name=='probe' else SEP_SHA256
        if pins[str(p)]!=expected_hash:raise ValueError('Actual HFS input readback differs')
    tools=validate_tools(Path(tools_root));chain=load_stopped_overlay(report_path,tools)
    expected_base={k:prior['base'][k] for k in ('report','report_sha256','stopped_manifest','stopped_manifest_sha256')}
    aux=report.get('auxiliary_base',{})
    if report.get('overlay_base_report')!=expected_base or chain['layers'][1:]!=prior['base']['layers'] or len(chain['layers'])!=3 or chain['virtual_size']!=32<<30 or aux.get('report')!=prior['base']['report'] or aux.get('report_sha256')!=prior['base']['report_sha256'] or aux.get('copied_before_use') is not True or aux.get('namespaces')!={k.removesuffix('.raw'):v for k,v in prior['base']['auxiliary'].items() if k!='root.qcow2'}:raise ValueError('Keybag predecessor or paired-state link differs')
    for entry in frozen['files'].values():
        if CO.identity(entry['path'])!=entry['after']:raise ValueError('Keybag metadata changed during validation')
    SK.check_base_metadata(prior);SK.unchanged(pins)
    identities={p:CO.identity(p) for p in {x['path'] for x in chain['layers']}|{x['path'] for x in chain['auxiliary'].values()}}
    return {'manifest':stage,'chain':chain,'tool':tools,'identities':identities,'preparation_inputs':args,'predecessor_validation':prior}
