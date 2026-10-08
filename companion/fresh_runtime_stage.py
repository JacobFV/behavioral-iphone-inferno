# SPDX-License-Identifier: AGPL-3.0-or-later
"""Typed fresh owned-runtime staging proof; no guest execution on import."""
import argparse
import hashlib
import json
from pathlib import Path
import plistlib
import re
import cache_patch_stage as CP
from initial_volumes import bounded_record
SOURCE=Path(__file__).resolve().parent
KS=CP.KS;CO=CP.CO;sha=CP.sha
F=CP.module('fresh_runtime_artifact_producer',SOURCE/'prepare-fresh-runtime.py')
IA=CP.module('fresh_runtime_import_plan',SOURCE/'native-probe/imported_app.py')

def digest_bytes(raw):return hashlib.sha256(raw).hexdigest()

def sources():
    pins=CP.sources()
    for p in (SOURCE/'fresh_runtime_stage.py',SOURCE/'stage-fresh-runtime.py',SOURCE/'prepare-fresh-runtime.py',SOURCE/'native-probe/merge-launchd-cache.py'):
        pins[str(p)]=sha(p)
    return pins

def verify_content(raw, manifest, artifact_sizes, identical_fixture=False):
    """Pure raw-byte check; caller must separately authenticate manifest/source/session.

    artifact_sizes requires the exact six owned runtime installation categories.
    Returned raw references do not authenticate a boot; no nonce exists in this ABI.
    """
    if not isinstance(raw, bytes) or len(raw) > 64 << 20:
        raise ValueError('Serial input must be bounded bytes')
    if set(artifact_sizes) - {'exec_wrapper', 'system_launcher', 'launchd_cache', 'hid_input', 'readiness', 'unlock_helper'}:
        raise ValueError('Unknown preparation operation')
    if any(type(v) is not int or v <= 0 for v in artifact_sizes.values()):
        raise ValueError('Invalid artifact size')
    if set(artifact_sizes)!={'exec_wrapper','system_launcher','launchd_cache','hid_input','readiness','unlock_helper'} or identical_fixture:raise ValueError('Require exact fresh operations; no collision exception')
    bundle = manifest['bundle']; files = manifest['files']; dirs = manifest['directories']
    name, ident = bundle['directory_name'], bundle['identifier']
    count, total = len(files) + len(dirs), sum(f['bytes'] for f in files)
    if identical_fixture and (name != 'InfernoProbe.app' or ident != 'org.inferno.companion.probe' or len(files) != 2 or dirs):
        raise ValueError('Collision exception is only exact two-file fixture')
    expected = [r'INFERNO_PREP_BEGIN: disposable /dev/disk0s1 existing=1 roles=0 gigalocker=0']
    expected += [f'INFERNO_HID_INPUT_READBACK bytes={artifact_sizes["hid_input"]} mismatches=0', 'INFERNO_HID_INPUT_INSTALLED: operator-only virtual device; no automatic gestures', f'INFERNO_READINESS_READBACK bytes={artifact_sizes["readiness"]} mismatches=0', 'INFERNO_READINESS_INSTALLED']
    for key, label in [('exec_wrapper', 'EXEC_WRAPPER'), ('system_launcher', 'SYSTEM_LAUNCHER')]:
        if key in artifact_sizes:
            expected.append(f'INFERNO_{label}_READBACK bytes={artifact_sizes[key]} mismatches=0')
    expected.append(f'INFERNO_UNLOCK_HELPER_READBACK bytes={artifact_sizes["unlock_helper"]} mismatches=0')
    expected += [f'INFERNO_IMPORTED_APP_PLAN bundle={re.escape(name)} identifier={re.escape(ident)} entries={count} bytes={total} identical_fixture={int(identical_fixture)}',
                 r'INFERNO_IMPORTED_APP_PARENT stat=0 errno=0 (?:mode=40775 uid=0 gid=80|mode=40755 uid=0 gid=0) nlink=[1-9][0-9]* path_result=0']
    if identical_fixture:
        expected.append('INFERNO_IMPORTED_APP_IDENTICAL_COLLISION_ACCEPTED')
    else:
        for rel in ['', *sorted(dirs, key=lambda x:(x.count('/'), x))]:
            target = '/mnt1' + bundle['guest_path'] + ('/' + rel if rel else '')
            expected += [r'INFERNO_IMPORTED_APP_DIR_METADATA_BEFORE target=' + re.escape(target) + r' source_stat=0 source_mode=40755 source_uid=0 source_gid=0 target_stat=0 target_mode=40[0-7]{3} target_uid=0 target_gid=[0-9]+',
                         r'INFERNO_IMPORTED_APP_DIR_METADATA_AFTER target=' + re.escape(target) + r' copy=0 copy_errno=0 stat=0 mode=40755 uid=0 gid=0']
    expected += [f'INFERNO_IMPORTED_APP_READBACK bundle={re.escape(name)} bytes={total} entries={count} mismatches=0',
                 'INFERNO_IMPORTED_APP_FINISH result=0 unmount=0 errno=0']
    if 'launchd_cache' in artifact_sizes:
        expected += [f'INFERNO_CACHE_READBACK bytes={artifact_sizes["launchd_cache"]} mismatches=0',
                     'INFERNO_LAUNCHD_CACHE_INSTALLED: explicit configuration only; signature unchanged']
    expected.append('INFERNO_PREP_COMPLETE: requested preparation operations succeeded')
    relevant = (b'INFERNO_IMPORTED_APP_', b'INFERNO_EXEC_WRAPPER_', b'INFERNO_SYSTEM_LAUNCHER_',
                b'INFERNO_HID_INPUT_', b'INFERNO_READINESS_', b'INFERNO_UNLOCK_HELPER_', b'INFERNO_CACHE_', b'INFERNO_LAUNCHD_CACHE_', b'INFERNO_PREP_BEGIN', b'INFERNO_PREP_COMPLETE')
    references = []; index = 0; offset = 0
    for physical in raw.split(b'\n'):
        complete = offset + len(physical) < len(raw)
        line = physical.rstrip(b'\r')
        if b'INFERNO_TREE_MISMATCH' in line or b'INFERNO_PREP_MISSING' in line or b'INFERNO_PREP_COPY_FAILED' in line or b'INFERNO_PREP_MKDIR_FAILED' in line:
            raise ValueError('Actual preparation failure at byte ' + str(offset))
        if b'INFERNO_PREP_STATUS' in line and not re.fullmatch(rb'INFERNO_PREP_STATUS raw=0', line):
            raise ValueError('Nonzero/malformed preparation child status')
        if any(prefix in line for prefix in relevant):
            if not complete or index >= len(expected) or not re.fullmatch(expected[index].encode('ascii'), line):
                raise ValueError(f'Unexpected/duplicate/malformed stage record at byte {offset}, expected index {index}')
            references.append({'byte_start': offset, 'byte_end': offset+len(physical)+1,
                               'sha256': digest_bytes(physical+b'\n'), 'text': line.decode('ascii')})
            index += 1
        # Full owned-prefix inventory: the narrow route permits only scanner/mount
        # diagnostics besides the milestones. Original kernel lines may interleave
        # before PREP_EXEC; retain offset, but never use these as success proof.
        owned = re.search(rb'INFERNO_[A-Z0-9_]+', line)
        if owned and not any(p in line for p in relevant):
            rest=line[owned.start():]
            auxiliary=(rb'INFERNO_OWNED_NATIVE_PROBE_V1: executed arm64 Darwin syscalls',
                       rb'INFERNO_PREP_DEVICE [a-zA-Z0-9]+ type=[0-9]+',
                       rb'INFERNO_PREP_EXEC /sbin/mount_apfs -o (?:ro|rw) /dev/disk0s1s[1-6] /mnt1',
                       rb'INFERNO_PREP_STATUS raw=0',
                       rb'INFERNO_PREP_VOLUME /dev/disk0s1s[1-6] name=[A-Za-z0-9._-]+',
                       rb'INFERNO_TREE_PROGRESS entries=[1-9][0-9]*000 bytes=[0-9]+ mismatches=0')
            if not complete or not any(re.fullmatch(pattern,rest) for pattern in auxiliary):
                raise ValueError('Unknown/malformed owned preparation record at byte '+str(offset))
        offset += len(physical)+1
    if index != len(expected):
        raise ValueError(f'Incomplete stage: {index}/{len(expected)} records')
    for i,row in enumerate(references):
        if re.match(r'INFERNO_(?:HID_INPUT|READINESS|EXEC_WRAPPER|SYSTEM_LAUNCHER|UNLOCK_HELPER|IMPORTED_APP|CACHE)_READBACK ',row['text']):
            end=references[i+1]['byte_start']
            tail=raw[row['byte_end']:end]
            if b"unmounting volume 'AzulSeed18A5351d.N104N841DeveloperOS'" not in tail or b'(numMountedAPFSVolumes 0)' not in tail:raise ValueError('Missing clean original unmount after '+row['text'].split()[0])
    return {'schema':'inferno.fresh-runtime-content.v1','ipa_runtime_ready':False,'content_verified': True, 'serial_bytes': len(raw), 'serial_sha256': digest_bytes(raw),
            'records': references, 'expected_file_bytes': total, 'expected_entries': count,
            'scope': 'Raw stage content only; not stopped eligibility or authenticated boot identity.'}


def validate_renderer(path,expected,pins,tools_root):
    path=KS.pin(path,expected,pins);stage=bounded_record(path)
    if stage.get('schema')!='inferno.renderer-cache-stage.v1' or stage.get('status')!='renderer-patched-not-runtime-ready' or stage.get('ipa_runtime_ready') is not False or stage.get('backing_depth')!=2:raise ValueError('Expected completed renderer stage depth2')
    if any((path.parent/n).exists() for n in ('INCOMPLETE.json','failure.json')):raise ValueError('Renderer incomplete/failed')
    for p,h in {**stage['source_sha256'],**stage['input_sha256'],**stage['stopped_evidence_sha256']}.items():KS.pin(p,h,pins)
    for name in ('stage-cache-patch.py','cache_patch_stage.py'):
        if [h for p,h in stage['source_sha256'].items() if Path(p).name==name]!=[sha(SOURCE/name)]:raise ValueError('Renderer source differs')
    launch=KS.inspected(path.parent/'launch.json',pins);make=KS.inspected(path.parent/'make-plan.json',pins)
    argv=make['argv'];wanted=['--original','--patched','--sidecar','--output','--original-sha256','--patched-sha256','--patcher-revision']
    if make.get('exit_code')!=0 or make.get('error') or Path(argv[1]).name!='make-plan.py' or argv[2::2]!=wanted:raise ValueError('Actual renderer plan invocation differs')
    values=dict(zip(argv[2::2],argv[3::2]))
    builds=[]
    for p,h in stage['input_sha256'].items():
        if Path(p).suffix=='.json':
            d=bounded_record(p)
            if d.get('status')=='built-owned-cache-helper-only; no guest execution yet':builds.append((p,h))
    if len(builds)!=1:raise ValueError('Renderer helper build ambiguous')
    args={'flattened_keybag':Path(stage['predecessor']['path']),'flattened_keybag_sha256':stage['predecessor']['sha256'],'inspection':Path(stage['inspection']['path']),'inspection_sha256':stage['inspection']['sha256'],'helper_build':Path(builds[0][0]),'helper_build_sha256':builds[0][1],'overlay_tools_root':Path(tools_root)}
    for name,key in [('original_cache','--original'),('patched_cache','--patched'),('sidecar','--sidecar')]:args[name]=Path(values[key]);args[name+'_sha256']=stage['input_sha256'][values[key]]
    paths,prior_pins,verified=CP.validate_inputs(argparse.Namespace(**args));pins.update(prior_pins)
    plan=KS.pin(stage['plan']['path'],stage['plan']['sha256'],pins);plan_record=KS.inspected(Path(stage['plan']['record']),pins)
    if stage['plan']['sha256']!=CP.PLAN or plan_record['plan_sha256']!=CP.PLAN or sha(Path(stage['plan']['record']))!=stage['plan']['record_sha256'] or values['--output']!=str(plan) or values['--original-sha256']!=CP.ORIGINAL or values['--patched-sha256']!=CP.PATCHED or values['--patcher-revision']!=CP.REVISION:raise ValueError('Renderer plan binding differs')
    rp=KS.pin(stage['report'],stage['report_sha256'],pins);ret=KS.pin(stage['retention'],stage['retention_sha256'],pins)
    if rp!=path.parent/'recovery-run/report.json' or ret!=rp.parent/'stopped-disk-hashes.json':raise ValueError('Renderer output layout differs')
    for p in (rp.parent/'serial.log',rp.parent/'control-transcript.jsonl',rp.parent/'qmp-transcript.jsonl',path.parent/'content-check.json',path.parent/'finish.stdout'):
        if str(p) not in stage['stopped_evidence_sha256']:raise ValueError('Missing renderer raw proof')
    raw=(rp.parent/'serial.log').read_bytes();content=CP.verify_content(raw);checkpoint=bounded_record(path.parent/'content-check.json')
    if content!=stage['content'] or {k:v for k,v in checkpoint.items() if k not in ('captured_time','eligible')}!=CP.verify_content(raw[:checkpoint['serial_bytes']]) or checkpoint.get('eligible') is not False or sha(path.parent/'content-check.json')!=stage['content_checkpoint_sha256']:raise ValueError('Renderer checkpoint differs')
    controls=[json.loads(x) for x in (rp.parent/'control-transcript.jsonl').read_bytes().splitlines() if x]
    if len(controls)!=1:raise ValueError('Renderer control count differs')
    c=controls[0];request=json.loads(c['raw'])
    if request['execute']!='finish-observation' or request['arguments']!={} or digest_bytes(c['raw'].encode())!=c['sha256'] or not checkpoint['captured_time']<request['created']<=c['time'] or c.get('response',{}).get('return',{}).get('finish_requested') is not True or bounded_record(path.parent/'finish.stdout')!=c['response']:raise ValueError('Renderer finish binding differs')
    r=bounded_record(rp)
    for name,key in [('boot.py','runner_sha256'),('qmp_control.py','control_source_sha256')]:
        if [h for p,h in stage['source_sha256'].items() if Path(p).name==name]!=[r[key]]:raise ValueError('Renderer source report mismatch')
    profile=KS.pin(path.parent/'recovery/profile.json',r['profile_sha256'],pins);_,inputs=KS.SK.load_profile(profile)
    if inputs!=r['inputs'] or r['binary_sha256']!=verified['runtime_inputs']['binary_sha256'] or r['build_manifest_sha256']!=verified['runtime_inputs']['build_manifest_sha256']:raise ValueError('Renderer runtime input mismatch')
    for name,expected_hash in [('helper',sha(paths['helper'])),('probe',sha(paths['probe'])),('plan',CP.PLAN),('digests',digest_bytes(bytes.fromhex(CP.ORIGINAL+CP.PATCHED)))]:
        p=KS.pin(path.parent/('readback-'+name),launch['readbacks'][name]['sha256'],pins)
        if pins[str(p)]!=expected_hash:raise ValueError('Renderer HFS readback differs')
    job=KS.pin(path.parent/'readback-job',launch['readbacks']['job']['sha256'],pins)
    if plistlib.loads(job.read_bytes())!={'Label':'org.inferno.probe.prepare-root','ProgramArguments':['/usr/bin/inferno-prepare-root','--disposable-root-copy'],'RunAtLoad':True,'StandardOutPath':'/dev/console','StandardErrorPath':'/dev/console','UserName':'root'}:raise ValueError('Renderer HFS job differs')
    CO.check_completed_report({'session':{'recovery_profile':{'sha256':r['profile_sha256']},'sources':{'boot.py':r['runner_sha256'],'qmp_control.py':r['control_source_sha256']}}},rp)
    frozen=KS.inspected(path.parent/'freeze-record.json',pins);entries=bounded_record(ret)
    if set(entries)!=set(frozen['files']) or set(entries)!={'root.qcow2',*CO.AUXILIARY_SIZES}:raise ValueError('Renderer7namespace mismatch')
    for name,e in entries.items():
        f=frozen['files'][name]
        if e.get('forensic_only') or e['path']!=f['path'] or e['sha256']!=f['sha256'] or CO.identity(e['path'])!=f['after']:raise ValueError('Renderer frozen identity differs')
    chain=CP.OV.load_stopped_overlay(rp,verified['tool'])
    if len(chain['layers'])!=2 or chain['layers'][-1]!=verified['flat']['raw']:raise ValueError('Renderer actual raw backing differs')
    aux=r.get('auxiliary_base',{});expected_aux={k.removesuffix('.raw'):{field:v[field] for field in ('path','bytes','sha256')} for k,v in verified['flat']['paired_auxiliary'].items()}
    if aux.get('report')!=verified['keybag']['report'] or aux.get('report_sha256')!=verified['keybag']['report_sha256'] or aux.get('namespaces')!=expected_aux or aux.get('copied_before_use') is not True:raise ValueError('Renderer paired keybag inputs differ')
    return stage,chain,verified

def validate_artifacts(path,expected,renderer,verified,pins):
    path=KS.pin(path,expected,pins);a=bounded_record(path)
    if a.get('schema')!='inferno.fresh-runtime-artifacts.v1' or a.get('status')!='host-prepared-not-staged' or a.get('ipa_runtime_ready') is not False or set(a['inputs'])!=F.INPUTS:raise ValueError('Expected fresh small artifact result')
    if any((path.parent/n).exists() for n in ('INCOMPLETE.json','failure.json')):raise ValueError('Artifacts incomplete/failed')
    if a['inputs']['inspection']!=renderer['inspection'] or a['inputs']['keybag_stage']!=verified['flat']['keybag_stage']:raise ValueError('Artifact/renderer keybag or inspection differs')
    for p,h in a['input_source_sha256'].items():KS.pin(p,h,pins)
    if [h for p,h in a['input_source_sha256'].items() if Path(p).name=='prepare-fresh-runtime.py']!=[sha(SOURCE/'prepare-fresh-runtime.py')]:raise ValueError('Artifact producer source differs')
    paths={};records={}
    for name,e in a['inputs'].items():paths[name]=KS.pin(e['path'],e['sha256'],pins);records[name]=bounded_record(paths[name])
    approved={'runtime_build':('aa7ba5975fe5436ebb6bfbd7f922817e3b7b4e0c4b2250756ca2824547ddcf35','built-owned-runtime-helpers-only; no guest execution yet'),'prepare_build':('3cb1656f3978bfdcca7e3da80d7f8091f524c1b7593bb64a42a7a2a47f34e532','built-owned-preparation-helper-only; no guest execution yet')}
    for name,(h,status) in approved.items():
        if a['inputs'][name]['sha256']!=h or records[name].get('status')!=status:raise ValueError('Reviewed helper build differs')
    runtime=F.build_outputs(paths['runtime_build'],records['runtime_build'],('inferno-probe','inferno-readiness','inferno-hid-input','inferno-unlock-empty'),pins)
    prep=F.build_outputs(paths['prepare_build'],records['prepare_build'],('inferno-prepare-root',),pins)
    for name,build,source in [('inferno-hid-input-entitlements.plist','runtime_build','hid-entitlements.plist'),('inferno-unlock-empty-entitlements.plist','runtime_build','unlock-entitlements.plist'),('helper-entitlements.plist','prepare_build','entitlements.plist')]:
        h=records[build]['outputs'][name]['sha256'];p=KS.pin(paths[build].parent/name,h,pins)
        if plistlib.loads(p.read_bytes())!=plistlib.loads((SOURCE/'native-probe'/source).read_bytes()):raise ValueError('Owned helper grants differ')
    manifest=F.IMPORTER.validate_manifest(paths['app_manifest']);IA.validate(paths['app_manifest'],a['inputs']['app_manifest']['sha256'])
    if (manifest['bundle']['identifier'],manifest['bundle']['guest_path'])!=('org.inferno.companion.ipademo','/Applications/ImportedDemo.app'):raise ValueError('First fresh app differs')
    launcher=records['launcher_build']
    if launcher.get('status')!='built-not-staged-or-executed' or launcher['manifest_path']!=str(paths['app_manifest']) or launcher['manifest_sha256']!=a['inputs']['app_manifest']['sha256'] or launcher['target']!=manifest['bundle']:raise ValueError('Launcher target differs')
    launch={}
    for name in ('inferno-launcher','inferno-exec-launcher','org.inferno.app-probe.plist','ImportedAppTarget.h'):launch[name]=str(KS.pin(paths['launcher_build'].parent/name,launcher['outputs'][name],pins))
    for relative,h in launcher['sources'].items():
        p=SOURCE/'app-probe'/relative
        if not p.resolve().is_relative_to(SOURCE/'app-probe'):raise ValueError('Launcher source escape')
        KS.pin(p,h,pins)
    if launcher['importer_sha256']!=sha(SOURCE/'app-import.py'):raise ValueError('Launcher importer differs')
    appjob=plistlib.loads(Path(launch['org.inferno.app-probe.plist']).read_bytes())
    if appjob!=plistlib.loads((SOURCE/'app-probe/org.inferno.app-probe-system-app.plist').read_bytes()):raise ValueError('Wrapper job differs')
    jobs={'org.inferno.app-probe.plist':appjob}
    for label,program,keep in [('readiness','inferno-readiness',None),('unlock-empty','inferno-unlock-empty',False)]:
        job={'Label':'org.inferno.'+label,'ProgramArguments':['/usr/bin/'+program],'RunAtLoad':True,'UserName':'root','StandardOutPath':'/dev/console','StandardErrorPath':'/dev/console'}
        if keep is not None:job['KeepAlive']=keep
        jobs[job['Label']+'.plist']=job
    for name,e in a['outputs'].items():
        if Path(e['path'])!=path.parent/name:raise ValueError('Artifact output escaped')
        KS.pin(e['path'],e['sha256'],pins)
    if set(a['outputs'])!={*jobs,'launchd.plist','merge.stdout','merge.stderr'} or a['jobs']!=sorted(jobs):raise ValueError('Artifact output inventory differs')
    for name,job in jobs.items():
        if plistlib.loads((path.parent/name).read_bytes())!=job:raise ValueError('Artifact job bytes differ')
    original=plistlib.loads(Path(records['inspection']['launchd_export']['path']).read_bytes())
    merged=plistlib.dumps(F.merge(original,jobs),fmt=plistlib.FMT_BINARY,sort_keys=False)
    if (path.parent/'launchd.plist').read_bytes()!=merged:raise ValueError('Fresh exact cache merge differs')
    merge=a['merge_command'];merge_tail=['--cache',records['inspection']['launchd_export']['path'],'--disable-unsupported-services','--output',str(path.parent/'launchd.plist')]
    for name in jobs:merge_tail+=['--job',str(path.parent/name)]
    if len(merge)<2 or Path(merge[1]).name!='merge-launchd-cache.py' or sha(Path(merge[1]))!=sha(SOURCE/'native-probe/merge-launchd-cache.py') or merge[2:]!=merge_tail:raise ValueError('Artifact merge command differs')
    if a['policy']!={'disabled_original_labels':list(F.POLICY),'original_signature_modified':False,'signature_scope':'Original signature not read or written','fresh_insertion':True}:raise ValueError('Fresh policy differs')
    fragment=['--disk-helper-existing','--readiness-probe',runtime['inferno-readiness'],'--hid-input-helper',runtime['inferno-hid-input'],'--unlock-helper',runtime['inferno-unlock-empty'],'--disk-helper',prep['inferno-prepare-root'],'--system-launcher',launch['inferno-launcher'],'--exec-wrapper',launch['inferno-exec-launcher'],'--imported-app-manifest',str(paths['app_manifest']),'--imported-app-manifest-sha256',a['inputs']['app_manifest']['sha256'],'--launchd-cache',str(path.parent/'launchd.plist'),'--launchd-cache-sha256',digest_bytes(merged)]
    if a['prepare_arguments_fragment']!=fragment:raise ValueError('Unsafe or unexpected preparation fragment')
    sizes={'hid_input':Path(runtime['inferno-hid-input']).stat().st_size,'readiness':Path(runtime['inferno-readiness']).stat().st_size+(path.parent/'org.inferno.readiness.plist').stat().st_size,'unlock_helper':Path(runtime['inferno-unlock-empty']).stat().st_size,'exec_wrapper':Path(launch['inferno-exec-launcher']).stat().st_size,'system_launcher':Path(launch['inferno-launcher']).stat().st_size,'launchd_cache':len(merged)}
    readbacks={'helper':('/usr/bin/inferno-prepare-root',prep['inferno-prepare-root']),'probe':('/usr/bin/inferno-probe',runtime['inferno-probe']),'readiness':('/usr/share/inferno-readiness',runtime['inferno-readiness']),'readiness-job':('/usr/share/org.inferno.readiness.plist',str(path.parent/'org.inferno.readiness.plist')),'hid':('/usr/share/inferno-hid-input',runtime['inferno-hid-input']),'unlock':('/usr/share/inferno-unlock-empty',runtime['inferno-unlock-empty']),'wrapper':('/usr/share/inferno-exec-launcher',launch['inferno-exec-launcher']),'launcher':('/usr/share/inferno-system-launcher',launch['inferno-launcher']),'cache':('/usr/share/inferno-launchd-cache.plist',str(path.parent/'launchd.plist'))}
    return a,manifest,sizes,readbacks,fragment,paths

def validate_inputs(args):
    pins={};stage,chain,prior=validate_renderer(args.renderer_stage,args.renderer_stage_sha256,pins,args.overlay_tools_root)
    a,manifest,sizes,readbacks,fragment,artifact_paths=validate_artifacts(args.artifacts,args.artifacts_sha256,stage,prior,pins)
    paths={name:Path(prior['runtime_inputs'][name]) for name in ('profile','raw_recovery_record','hfsplus','binary','build_manifest')}
    paths['probe']=Path(readbacks['probe'][1]);paths['base_report']=Path(stage['report'])
    extraction=bounded_record(paths['raw_recovery_record']);paths['raw']=KS.pin(extraction['output']['path'],extraction['output']['sha256'],pins)
    paths.update(artifact_paths)
    metadata={**prior['base_metadata'],**CP.FL.identities(chain)}
    KS.SK.unchanged(pins)
    return paths,pins,{'base':chain,'tool':prior['tool'],'base_metadata':metadata,'runtime_inputs':prior['runtime_inputs'],'renderer':stage,'artifacts':a,'manifest':manifest,'artifact_sizes':sizes,'readbacks':readbacks,'fragment':fragment}
