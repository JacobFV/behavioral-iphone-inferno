# SPDX-License-Identifier: AGPL-3.0-or-later
"""Fixed renderer cache patch proof and typed predecessor validation."""
import hashlib
import importlib.util
import json
from pathlib import Path
import plistlib
import re
import struct
import keybag_state as KS
import disk_overlay as OV
from initial_volumes import bounded_record
SOURCE=Path(__file__).resolve().parent
CO=KS.CO;sha=KS.sha
ORIGINAL='59fdf288034e947c39b087b7c405ed149de3fea9f8af4a5ae2611fa03d4081e1'
PATCHED='af1001abe5b075afd337bf110562746c3e006e9d93951e163fc5daae062aeab8'
PLAN='c20a73ee8aa777ea36595cf60fb1ed86b9fc4a3bad42645a34045536ab01b079'
REVISION='3008aaaa0909824a71ee3040c9edc58703c250f5'
BYTES=2052489216

def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
FL=module('cache_flatten_support',SOURCE/'flatten-keybag.py')
IR=module('cache_inspection_result',SOURCE/'runtime-inspector/result.py')

def sources():
    pins=FL.source_pins()
    for path in [SOURCE/'cache_patch_stage.py',SOURCE/'stage-cache-patch.py',SOURCE/'runtime-inspector/result.py',SOURCE/'runtime-inspector/stage.py',*[SOURCE/'fs-patches'/n for n in ('make-plan.py','prepare.py','build-cache-helper.py','cache-patch.c','libSystem.tbd','entitlements.plist')]]:pins[str(path)]=sha(path)
    return pins

def verify_content(raw):
    if not isinstance(raw,bytes) or len(raw)>64<<20:raise ValueError('Serial bound/type')
    records=[];offset=0
    for line in raw.split(b'\n'):
        value=line.rstrip(b'\r')
        if b'INFERNO_CACHE_' in value:
            if value.count(b'INFERNO_CACHE_')!=1 or offset+len(line)>=len(raw):raise ValueError('Ambiguous/truncated cache record')
            pos=value.index(b'INFERNO_CACHE_');records.append({'text':value[pos:].decode('ascii'),'byte_start':offset+pos,'byte_end':offset+len(value),'sha256':hashlib.sha256(value[pos:]).hexdigest()})
        elif b'INFERNO_' in value and b'INFERNO_OWNED_NATIVE_PROBE_V1: executed arm64 Darwin syscalls' not in value:raise ValueError('Unexpected owned guest operation')
        if b'panic(cpu' in value:raise ValueError('Guest panic')
        offset+=len(line)+1
    text=[r['text'] for r in records]
    expected=['INFERNO_CACHE_BEGIN fixed_path=/mnt1/System/Library/Caches/com.apple.dyld/dyld_shared_cache_arm64e','INFERNO_CACHE_MOUNT status=0','INFERNO_CACHE_SHA256 before '+ORIGINAL,'INFERNO_CACHE_VALIDATED bytes=2052489216 records=45','INFERNO_CACHE_SHA256 after '+PATCHED]
    if len(text)!=7 or text[:5]!=expected or not re.fullmatch(r'INFERNO_CACHE_UNMOUNT status=0 errno=-?[0-9]+',text[5]) or text[6]!='INFERNO_CACHE_RESULT status=0':raise ValueError('Missing/extra/failed cache patch records')
    tail=raw[records[4]['byte_end']:records[5]['byte_start']]
    if b"unmounting volume 'AzulSeed18A5351d.N104N841DeveloperOS'" not in tail or b'(numMountedAPFSVolumes 0)' not in tail:raise ValueError('Missing original clean unmount')
    return {'schema':'inferno.cache-patch-content.v1','content_verified':True,'ipa_runtime_ready':False,'serial_bytes':len(raw),'serial_sha256':hashlib.sha256(raw).hexdigest(),'records':records,'original_sha256':ORIGINAL,'patched_sha256':PATCHED,'file_bytes':BYTES,'patch_records':45,'replacement_bytes':180,'scope':'Whole original/patched guest hashes and unchanged helper write/fsync/readback path, clean unmount. No installed runtime proof.'}

def finish_proof(folder,stage,pins):
    report=KS.pin(stage['report'],stage['report_sha256'],pins);retention=KS.pin(stage['retention'],stage['retention_sha256'],pins)
    if report!=folder/'recovery-run/report.json' or retention!=report.parent/'stopped-disk-hashes.json':raise ValueError('Inspection layout differs')
    for p,h in stage['stopped_evidence_sha256'].items():KS.pin(p,h,pins)
    for p in (report.parent/'serial.log',report.parent/'control-transcript.jsonl',report.parent/'qmp-transcript.jsonl',folder/'content-check.json',folder/'finish.stdout'):
        if str(p) not in stage['stopped_evidence_sha256']:raise ValueError('Inspection raw proof absent')
    raw=(report.parent/'serial.log').read_bytes();content,export=IR.verify_content(raw)
    checkpoint=bounded_record(folder/'content-check.json')
    prior,_=IR.verify_content(raw[:checkpoint['serial_bytes']])
    if content!=stage['content'] or {k:v for k,v in checkpoint.items() if k not in ('captured_time','eligible')}!=prior or checkpoint.get('eligible') is not False or sha(folder/'content-check.json')!=stage['content_checkpoint_sha256']:raise ValueError('Inspection prefix/content differs')
    controls=[json.loads(x) for x in (report.parent/'control-transcript.jsonl').read_bytes().splitlines() if x]
    if len(controls)!=1:raise ValueError('Inspection control count differs')
    c=controls[0];req=json.loads(c['raw'])
    if req['execute']!='finish-observation' or req['arguments']!={} or hashlib.sha256(c['raw'].encode()).hexdigest()!=c['sha256'] or not checkpoint['captured_time']<req['created']<=c['time'] or c.get('response',{}).get('return',{}).get('finish_requested') is not True or bounded_record(folder/'finish.stdout')!=c['response']:raise ValueError('Inspection finish binding differs')
    r=bounded_record(report)
    for name,key in [('boot.py','runner_sha256'),('qmp_control.py','control_source_sha256')]:
        if [h for p,h in stage['source_sha256'].items() if Path(p).name==name]!=[r[key]]:raise ValueError('Inspection source/report mismatch')
    CO.check_completed_report({'session':{'recovery_profile':{'sha256':r['profile_sha256']},'sources':{'boot.py':r['runner_sha256'],'qmp_control.py':r['control_source_sha256']}}},report)
    frozen=KS.inspected(folder/'freeze-record.json',pins);entries=bounded_record(retention)
    if set(entries)!=set(frozen['files']) or set(entries)!={'root.qcow2',*CO.AUXILIARY_SIZES}:raise ValueError('Inspection seven files absent')
    for name,e in entries.items():
        f=frozen['files'][name]
        if e.get('forensic_only') or e['path']!=f['path'] or e['sha256']!=f['sha256'] or CO.identity(e['path'])!=f['after']:raise ValueError('Inspection frozen identity differs')
    exported=KS.pin(stage['launchd_export']['path'],stage['launchd_export']['sha256'],pins)
    if exported!=folder/'launchd.plist' or exported.read_bytes()!=export:raise ValueError('Inspection export differs')
    return r,report

def validate_flatten(path,expected,pins,tools_root):
    path=KS.pin(path,expected,pins);flat=bounded_record(path)
    if flat.get('schema')!='inferno.flattened-keybag-state.v1' or flat.get('status')!='flattened-fresh-keybag-not-runtime-ready' or any(flat.get(k) is not False for k in ('ipa_runtime_ready','sep_destination_bytes_verified','postgrowth_full_data_verified')):raise ValueError('Expected typed flattened keybag result')
    if any((path.parent/n).exists() for n in ('INCOMPLETE.json','failure.json')):raise ValueError('Flatten incomplete/failed')
    KS.SK.unchanged({**flat['source_sha256'],**flat['evidence_sha256']});pins.update(flat['source_sha256']);pins.update(flat['evidence_sha256'])
    prior=KS.validate(Path(flat['keybag_stage']['path']),flat['keybag_stage']['sha256'],pins,tools_root)
    chain=prior['chain'];tool=prior['tool']
    if FL.normalized(chain)!=FL.normalized(flat['source_after']) or FL.normalized(flat['source_before'])!=FL.normalized(flat['source_after']) or FL.identities(chain)!=flat['identities_after'] or flat['identities_before']!=flat['identities_after']:raise ValueError('Flatten original chain changed')
    paired={k:v for k,v in chain['auxiliary'].items() if k!='root.qcow2'}
    stage=prior['manifest']
    if flat['paired_auxiliary']!=paired or flat['auxiliary_state']!=str(Path(stage['report']).parent) or flat['auxiliary_report_sha256']!=stage['report_sha256'] or flat['auxiliary_retention_sha256']!=stage['retention_sha256']:raise ValueError('Flatten paired state differs')
    raw=OV.validate_base(Path(flat['raw']['path']),flat['raw']['sha256'],allow_attestation=False)
    if raw!=flat['raw'] or raw['bytes']!=32<<30 or FL.gpt_headers(Path(raw['path']))!=flat['gpt'] or tool!=flat['tool']:raise ValueError('Flatten raw/GPT/tool differs')
    keep=KS.inspected(path.parent/'KEEP-OVERLAY-BACKING.json',pins)
    if keep.get('backing')!=raw or keep.get('provenance_sha256')!=expected or keep.get('paired_auxiliary_must_be_retained')!=paired or keep.get('retirement_prohibited_while_dependent_overlays_exist') is not True:raise ValueError('Flatten KEEP differs')
    operations={'convert':['convert','-f','qcow2','-O','raw','-S','4k',chain['layers'][0]['path'],raw['path']],'raw-info':['info','--output=json','-f','raw',raw['path']],'logical-compare':['compare','-f','qcow2','-F','raw',chain['layers'][0]['path'],raw['path']]};previous=0
    for name,tail in operations.items():
        r=KS.inspected(path.parent/(name+'.json'),pins)
        if r['argv']!=[tool['binary'],*tail] or r['exit_code']!=0 or r.get('error') or not previous<=r['started']<=r['finished']:raise ValueError('Flatten command proof differs')
        previous=r['finished']
        for stream in ('stdout','stderr'):KS.pin(path.parent/(name+'.'+stream),r[stream+'_sha256'],pins)
    info=bounded_record(path.parent/'raw-info.stdout')
    if info['format']!='raw' or info['virtual-size']!=32<<30:raise ValueError('Flatten actual raw info differs')
    return flat,prior

def validate_inputs(args):
    names=('flattened_keybag','inspection','helper_build','original_cache','patched_cache','sidecar')
    if Path(args.sidecar).stat().st_size>1<<20:raise ValueError('Original-byte sidecar exceeds1MiB')
    pins={};paths={n:KS.pin(getattr(args,n),getattr(args,n+'_sha256'),pins) for n in names}
    flat,prior=validate_flatten(paths['flattened_keybag'],args.flattened_keybag_sha256,pins,args.overlay_tools_root)
    inspection=bounded_record(paths['inspection'])
    if inspection.get('schema')!='inferno.runtime-inspection.v1' or inspection.get('status')!='observed-not-runtime-ready' or inspection.get('runtime_base_eligible') is not False or inspection.get('ipa_runtime_ready') is not False or inspection.get('backing_depth')!=4 or inspection.get('predecessor')!=flat['keybag_stage']:raise ValueError('Inspection is not same-keybag observation')
    if any((paths['inspection'].parent/n).exists() for n in ('INCOMPLETE.json','failure.json')):raise ValueError('Inspection failed/incomplete')
    for p,h in inspection['source_sha256'].items():KS.pin(p,h,pins)
    for name in ('stage.py','result.py','inspect.c','sha256.h','libSystem.tbd','entitlements.plist'):
        matches=[h for p,h in inspection['source_sha256'].items() if Path(p).parent.name=='runtime-inspector' and Path(p).name==name]
        if matches!=[sha(SOURCE/'runtime-inspector'/name)]:raise ValueError('Inspector reviewed source differs')
    r,rp=finish_proof(paths['inspection'].parent,inspection,pins)
    profile=KS.pin(paths['inspection'].parent/'recovery/profile.json',r['profile_sha256'],pins)
    _,actual_inputs=KS.SK.load_profile(profile)
    if actual_inputs!=r['inputs'] or r['binary_sha256']!=prior['preparation_inputs']['binary_sha256'] or r['build_manifest_sha256']!=prior['preparation_inputs']['build_manifest_sha256']:raise ValueError('Inspection actual runtime inputs differ')
    launch=KS.inspected(paths['inspection'].parent/'launch.json',pins)
    builds=[]
    for p,h in launch['input_sha256'].items():
        if Path(p).suffix=='.json':
            record=bounded_record(KS.pin(p,h,pins))
            if record.get('status')=='built-owned-runtime-inspector-only; no guest execution yet':builds.append((Path(p),record))
    if len(builds)!=1:raise ValueError('Missing unique inspector helper build')
    build_path,build=builds[0]
    for name in ('inspect.c','sha256.h','libSystem.tbd','entitlements.plist'):
        if [h for p,h in build['sources'].items() if Path(p).name==name]!=[sha(SOURCE/'runtime-inspector'/name)]:raise ValueError('Inspector helper build source differs')
    helper=KS.pin(build_path.parent/'inferno-runtime-inspector',build['outputs']['inferno-runtime-inspector']['sha256'],pins)
    for name,expected_hash in [('helper',pins[str(helper)]),('probe',prior['preparation_inputs']['probe_sha256'])]:
        actual=KS.pin(paths['inspection'].parent/('readback-'+name),launch['readbacks'][name]['sha256'],pins)
        if pins[str(actual)]!=expected_hash:raise ValueError('Inspector HFS executable readback differs')
    job=KS.pin(paths['inspection'].parent/'readback-job',launch['readbacks']['job']['sha256'],pins)
    if plistlib.loads(job.read_bytes())!={'Label':'org.inferno.probe.prepare-root','ProgramArguments':['/usr/bin/inferno-prepare-root','--disposable-root-copy'],'RunAtLoad':True,'StandardOutPath':'/dev/console','StandardErrorPath':'/dev/console','UserName':'root'}:raise ValueError('Inspector HFS job differs')
    observed=OV.load_stopped_overlay(rp,prior['tool']);base=prior['chain']
    if len(observed['layers'])!=4 or observed['layers'][1:]!=base['layers'] or r.get('overlay_base_report')!={k:base[k] for k in ('report','report_sha256','stopped_manifest','stopped_manifest_sha256')}:raise ValueError('Inspector predecessor lineage differs')
    aux=r.get('auxiliary_base',{})
    if aux.get('report')!=base['report'] or aux.get('report_sha256')!=base['report_sha256'] or aux.get('copied_before_use') is not True or aux.get('namespaces')!={k.removesuffix('.raw'):v for k,v in base['auxiliary'].items() if k!='root.qcow2'}:raise ValueError('Inspector paired input differs')
    if inspection['content']['dyld']['sha256']!=ORIGINAL or args.original_cache_sha256!=ORIGINAL or args.patched_cache_sha256!=PATCHED or paths['original_cache'].stat().st_size!=BYTES or paths['patched_cache'].stat().st_size!=BYTES:raise ValueError('Exact original renderer cache binding differs')
    build=bounded_record(paths['helper_build']);folder=paths['helper_build'].parent
    if build.get('status')!='built-owned-cache-helper-only; no guest execution yet' or any((folder/n).exists() for n in ('INCOMPLETE.json','failure.json')):raise ValueError('Cache helper build not complete')
    for p,h in {**build['sources'],**build['producer_sources']}.items():KS.pin(p,h,pins)
    for name in ('cache-patch.c','libSystem.tbd','entitlements.plist'):
        if [h for p,h in build['sources'].items() if Path(p).name==name]!=[sha(SOURCE/'fs-patches'/name)]:raise ValueError('Cache helper source differs')
    if build['outputs']['inferno-cache-patch']!={'bytes':68416,'sha256':'13cd534f238d6fc47ec70351479034a6b97262e0984588c0948625478d2edb8c'}:raise ValueError('Reviewed reproducible cache helper differs')
    paths['helper']=KS.pin(folder/'inferno-cache-patch',build['outputs']['inferno-cache-patch']['sha256'],pins)
    ent=KS.pin(folder/'helper-entitlements.plist',build['outputs']['helper-entitlements.plist']['sha256'],pins)
    if plistlib.loads(ent.read_bytes())!=plistlib.loads((SOURCE/'fs-patches/entitlements.plist').read_bytes()):raise ValueError('Helper grants differ')
    for c in build['command_records']:
        if c['exit_code']!=0:raise ValueError('Failed helper build command')
        for stream in ('stdout','stderr'):KS.pin(c[stream]['path'],c[stream]['sha256'],pins)
    paths.update({n:prior['preparation_inputs'][n] for n in ('profile','raw_recovery_record','probe','hfsplus','binary','build_manifest')})
    extraction=bounded_record(paths['raw_recovery_record']);paths['raw']=KS.pin(extraction['output']['path'],extraction['output']['sha256'],pins)
    paths['root']=Path(flat['raw']['path']);paths['auxiliary_state']=Path(flat['auxiliary_state'])
    metadata={**prior['identities'],**FL.identities(observed),str(paths['root']):CO.identity(paths['root'])}
    KS.SK.unchanged(pins)
    # CO.freeze_new_disks uses base.layers only as a protected inode inventory.
    # This includes the flattened raw AND retained historical layers; it is not
    # the boot backing chain, which is independently checked as depth2 afterward.
    return paths,pins,{'base_scope':'Protected inode inventory only, not actual ancestry; actual output chain must be raw plus new overlay (depth2).','flat':flat,'keybag':prior['manifest'],'base':{**base,'layers':[flat['raw'],*base['layers']]},'tool':prior['tool'],'base_metadata':metadata,'runtime_inputs':{k:str(v) for k,v in prior['preparation_inputs'].items()}}
