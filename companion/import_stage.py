"""Strict owned imported-stage evidence checks. No VM control or preservation writes.
SPDX-License-Identifier: AGPL-3.0-or-later
"""
import hashlib
import json
import re
from pathlib import Path


def digest_bytes(raw):
    return hashlib.sha256(raw).hexdigest()


def strict_json(raw):
    def pairs(items):
        result = {}
        for k, v in items:
            if k in result:
                raise ValueError('Duplicate JSON key: ' + k)
            result[k] = v
        return result
    return json.loads(raw, object_pairs_hook=pairs,
                      parse_constant=lambda value: (_ for _ in ()).throw(ValueError('Nonfinite JSON')))


def verify_content(raw, manifest, artifact_sizes, identical_fixture=False):
    """Pure raw-byte check; caller must separately authenticate manifest/source/session.

    artifact_sizes permits only exec_wrapper/system_launcher/launchd_cache.
    Returned raw references do not authenticate a boot; no nonce exists in this ABI.
    """
    if not isinstance(raw, bytes) or len(raw) > 64 << 20:
        raise ValueError('Serial input must be bounded bytes')
    if set(artifact_sizes) - {'exec_wrapper', 'system_launcher', 'launchd_cache'}:
        raise ValueError('Unknown preparation operation')
    if any(type(v) is not int or v <= 0 for v in artifact_sizes.values()):
        raise ValueError('Invalid artifact size')
    bundle = manifest['bundle']; files = manifest['files']; dirs = manifest['directories']
    name, ident = bundle['directory_name'], bundle['identifier']
    count, total = len(files) + len(dirs), sum(f['bytes'] for f in files)
    if identical_fixture and (name != 'InfernoProbe.app' or ident != 'org.inferno.companion.probe' or len(files) != 2 or dirs):
        raise ValueError('Collision exception is only exact two-file fixture')
    expected = [r'INFERNO_PREP_BEGIN: disposable /dev/disk0s1 existing=1 roles=0 gigalocker=0']
    for key, label in [('exec_wrapper', 'EXEC_WRAPPER'), ('system_launcher', 'SYSTEM_LAUNCHER')]:
        if key in artifact_sizes:
            expected.append(f'INFERNO_{label}_READBACK bytes={artifact_sizes[key]} mismatches=0')
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
                b'INFERNO_CACHE_', b'INFERNO_LAUNCHD_CACHE_', b'INFERNO_PREP_BEGIN', b'INFERNO_PREP_COMPLETE')
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
    return {'content_verified': True, 'serial_bytes': len(raw), 'serial_sha256': digest_bytes(raw),
            'records': references, 'expected_file_bytes': total, 'expected_entries': count,
            'scope': 'Raw stage content only; not stopped eligibility or authenticated boot identity.'}


def _load(name, directory=None):
    import importlib.util
    path = (Path(directory)/ (name+'.py')) if directory else Path(__file__).with_name(name + '.py')
    spec = importlib.util.spec_from_file_location(name.replace('-', '_'), path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


def _pin(record, maximum=None):
    import stat
    path = Path(record['path'])
    before = path.lstat()
    identity=lambda st:(st.st_dev,st.st_ino,st.st_mode,st.st_size,st.st_mtime_ns,st.st_ctime_ns)
    if not path.is_absolute() or not stat.S_ISREG(before.st_mode) or (maximum and before.st_size > maximum):
        raise ValueError('Invalid pinned regular file: ' + str(path))
    import hashlib
    with path.open('rb') as f:
        found = hashlib.file_digest(f, 'sha256').hexdigest()
    if found != record['sha256'] or identity(path.lstat()) != identity(before):
        raise ValueError('Pinned source changed: ' + str(path))
    return path


def validate_session(path, sha256):
    """Validate prepared-import-session v1, returning raw checker inputs and pins."""
    import plistlib
    path = _pin({'path': str(Path(path).absolute()), 'sha256': sha256}, 16 << 20)
    s = strict_json(path.read_bytes())
    if s['schema'] != 'inferno.prepared-import-session.v1' or s['status'] != 'host-prepared-not-staged':
        raise ValueError('Unsupported session')
    if (path.parent/'INCOMPLETE.json').exists() or (path.parent/'failure.json').exists():
        raise ValueError('Incomplete/failed host session')
    pinned = {key: _pin(s[key]) for key in ('runtime','import_manifest','launcher_build','cache','recovery_profile','recovery_ramdisk','preparation')}
    runtime = strict_json(pinned['runtime'].read_bytes())
    if runtime != s['runtime_record']:
        raise ValueError('Runtime record differs')
    for value in runtime['inputs'].values():
        _pin(value)
    source_root=Path(s['recovery_command'][1]).parent
    for relative, expected_hash in s['sources'].items():
        if Path(relative).is_absolute() or '..' in Path(relative).parts:raise ValueError('Invalid source pin path')
        _pin({'path':str(source_root/relative),'sha256':expected_hash})
    runtime_validator=_load('prepare-import',source_root)
    _,verified_runtime=runtime_validator.validate_runtime(runtime)
    manifest = _load('app-import').validate_manifest(pinned['import_manifest'])
    if manifest['bundle'] != s['bundle'] or manifest['tree_sha256'] != s['tree_sha256']:
        raise ValueError('Manifest target differs')
    profile = strict_json(pinned['recovery_profile'].read_bytes()); prov=profile['provenance']
    if profile['ramdisk']['sha256'] != s['recovery_ramdisk']['sha256'] or Path(profile['ramdisk']['path']) != pinned['recovery_ramdisk']:
        raise ValueError('Profile ramdisk differs')
    if prov['imported_app']['manifest_sha256'] != s['import_manifest']['sha256'] or prov['imported_app']['allow_identical_fixture_tree_sha256'] is not None:
        raise ValueError('Only fresh imported sessions supported')
    build = strict_json(pinned['launcher_build'].read_bytes())
    if build['manifest_sha256'] != s['import_manifest']['sha256'] or build['target'] != s['bundle']:
        raise ValueError('Launcher target differs')
    artifacts={}
    for key, filename, profile_key in [('exec_wrapper','inferno-exec-launcher','exec_wrapper_sha256'),('system_launcher','inferno-launcher','system_launcher_sha256')]:
        record={'path':str(pinned['launcher_build'].parent/filename),'sha256':build['outputs'][filename]}
        artifact=_pin(record)
        if s['launcher' if key=='system_launcher' else key] != record:raise ValueError('Explicit launcher artifact pin differs')
        if prov[profile_key] != record['sha256']: raise ValueError('Profile helper differs')
        artifacts[key]=artifact.stat().st_size
    if prov['launchd_cache_sha256'] != s['cache']['sha256'] :
        raise ValueError('Cache/helper profile binding differs')
    _pin(s['launchd_job'])
    if s['launchd_job']['sha256'] != build['outputs']['org.inferno.app-probe.plist']:raise ValueError('Launch job differs')
    artifacts['launchd_cache']=pinned['cache'].stat().st_size
    job_path=pinned['recovery_profile'].parent/'org.inferno.probe.prepare-root.plist'
    job=plistlib.loads(job_path.read_bytes())
    expected=['/usr/bin/inferno-prepare-root','--disposable-root-copy','--existing-volumes','--install-cache','--install-exec-wrapper','--install-system-launcher','--install-imported-app']
    if job.get('ProgramArguments') != expected or job.get('UserName') != 'root' or job.get('RunAtLoad') is not True:
        raise ValueError('Unknown or changed preparation operations')
    # The HFS generation transcript must record installing this exact job. Current
    # session pins also bind the ramdisk bytes, so this is not a mutable argv hint.
    prep=strict_json(pinned['preparation'].read_bytes())
    operations=prep['operations']
    if prep['disk_helper_sha256'] != runtime['inputs']['disk_helper']['sha256']:
        raise ValueError('Preparation helper hash differs')
    if not any(x['args'][:2]==['add',str(job_path)] for x in operations):
        raise ValueError('Preparation job installation absent')
    return {'session':s,'verified_runtime':verified_runtime,'manifest':manifest,'artifact_sizes':artifacts,'session_path':str(path),'session_sha256':sha256,
            'pinned':{key:str(value) for key,value in pinned.items()}}


def verify_stopped(context, report_path, retention_path, content_check_path):
    """Read-only eligibility verification after ordinary preserve-stopped exists."""
    from disk_overlay import load_stopped_overlay, validate_tools, MAX_OVERLAY_DEPTH
    report_path=Path(report_path).absolute()
    stable_paths=[report_path,report_path.parent/'control-transcript.jsonl',report_path.parent/'qmp-transcript.jsonl',Path(retention_path).absolute(),Path(retention_path).absolute().with_name(Path(retention_path).stem+'-verification.json'),Path(content_check_path)]
    stable_bytes={str(p):p.read_bytes() for p in stable_paths}
    stable_hashes={p:digest_bytes(raw) for p,raw in stable_bytes.items()}
    report=strict_json(stable_bytes[str(report_path)]); s=context['session']
    if report.get('kind')!='t8030_recovery_ramdisk_experiment' or report.get('attempt_completed') is not True or report.get('error') or report.get('exit_code')!=0:
        raise ValueError('Recovery did not complete normally')
    if report.get('profile_sha256')!=s['recovery_profile']['sha256'] or Path(report['profile_path'])!=Path(s['recovery_profile']['path']):
        raise ValueError('Actual recovery profile differs')
    if report.get('runner_sha256')!=s['sources']['boot.py'] or report.get('control_source_sha256')!=s['sources']['qmp_control.py']:
        raise ValueError('Actual runner/control source differs')
    from boot import load_profile
    _,profile_inputs=load_profile(Path(s['recovery_profile']['path']))
    if report.get('inputs')!=profile_inputs:raise ValueError('Actual profile input dictionary differs')
    if report.get('probe_journey') or report.get('observation_run_control',{}).get('finish_requested') is not True:
        raise ValueError('Explicit normal finish-observation required')
    base=s['runtime_record']['inputs']['base_report']; actualbase=report.get('overlay_base_report',{})
    if actualbase.get('report_sha256')!=base['sha256'] or actualbase.get('report')!=base['path']:
        raise ValueError('Actual recovery base differs')
    inputs=s['runtime_record']['inputs']
    if report.get('binary_sha256')!=inputs['emulator']['sha256'] or report.get('build_manifest_sha256')!=inputs['emulator_build']['sha256']:
        raise ValueError('Runtime binary/build differs')
    argv=report['invocation']
    if argv.count('-initrd')!=1 or argv[argv.index('-initrd')+1]!=s['recovery_ramdisk']['path'] or argv.count('-serial')!=1 or argv[argv.index('-serial')+1]!='file:'+str(report_path.parent/'serial.log'):
        raise ValueError('Actual ramdisk/sole serial path differs')
    raw=(report_path.parent/'serial.log').read_bytes()
    content=verify_content(raw,context['manifest'],context['artifact_sizes'])
    checkpoint=strict_json(stable_bytes[str(Path(content_check_path))])
    n=checkpoint.get('serial_bytes')
    if (checkpoint.get('session_sha256')!=context['session_sha256'] or checkpoint.get('content_verified') is not True
            or type(n) is not int or n<=0 or n>len(raw) or digest_bytes(raw[:n])!=checkpoint.get('serial_sha256')):
        raise ValueError('Pre-finish content checkpoint differs from final serial prefix')
    verify_content(raw[:n],context['manifest'],context['artifact_sizes'])
    control_raw=stable_bytes[str(report_path.parent/'control-transcript.jsonl')]
    if not control_raw.endswith(b'\n') or len(control_raw)>32<<20:raise ValueError('Incomplete/oversize control journal')
    finishes=[]
    for line in control_raw.split(b'\n')[:-1]:
        entry=strict_json(line); request=strict_json(entry['raw'])
        if digest_bytes(entry['raw'].encode())!=entry['sha256']:raise ValueError('Control raw hash differs')
        if request.get('execute')=='finish-observation':
            if request.get('arguments')!={} or entry.get('response',{}).get('return',{}).get('finish_requested') is not True:
                raise ValueError('Finish request failed')
            finishes.append((entry,request))
    if len(finishes)!=1:raise ValueError('Exactly one successful explicit finish required')
    finish,request=finishes[0]
    if not (checkpoint['read_started_time']<=checkpoint['captured_time']<request['created']<=finish['time']):
        raise ValueError('Complete content not observed before finish request')
    # Reuse original shutdown checker without its write-producing preserve API.
    preserve=_load('preserve-stopped'); shutdown=preserve.verify_shutdown(report_path.parent,report)
    qmp_raw=stable_bytes[str(report_path.parent/'qmp-transcript.jsonl')]
    if not qmp_raw.endswith(b'\n'):raise ValueError('Truncated QMP journal')
    quit_sends=[];quit_acks=[];shutdowns=[]
    for i,line in enumerate(qmp_raw.split(b'\n')[:-1]):
        e=strict_json(line);msg=strict_json(e['raw'])
        if e['direction']=='send' and msg.get('execute')=='quit':quit_sends.append((i,e,msg))
        if e['direction']=='receive' and msg==report['quit_response']:quit_acks.append((i,e,msg))
        if e['direction']=='receive' and msg.get('event')=='SHUTDOWN' and msg.get('data',{}).get('reason')=='host-qmp-quit':shutdowns.append((i,e,msg))
    if len(quit_sends)!=1 or len(quit_acks)!=1 or len(shutdowns)!=1:raise ValueError('Ambiguous QMP shutdown')
    qi,qe,qm=quit_sends[0]
    if qm.get('id')!=report['quit_response']['id'] or qi>=quit_acks[0][0] or qi>=shutdowns[0][0] or qe['time']<finish['time']:
        raise ValueError('QMP shutdown does not follow normal finish')
    retention_path=Path(retention_path).absolute(); side=retention_path.with_name(retention_path.stem+'-verification.json')
    if retention_path!=report_path.parent/'stopped-disk-hashes.json':raise ValueError('Use standard stopped manifest bound by overlay loader')
    retention=strict_json(stable_bytes[str(retention_path)]); verification=strict_json(stable_bytes[str(side)])
    expected_paths={x['path'] for x in report['disks']}
    if {x['path'] for x in retention.values()}!=expected_paths:raise ValueError('Retention paths differ from actual namespaces')
    if verification.get('failed_attempt_opt_in') is not False or verification.get('report_sha256')!=digest_bytes(report_path.read_bytes()) or verification.get('attempt_error') or verification.get('attempt_completed') is not True:
        raise ValueError('Default successful stopped preservation required')
    if len(retention)!=7:raise ValueError('Exactly seven stopped namespaces required')
    for value in retention.values():
        if value.get('forensic_only'):raise ValueError('Forensic namespace not eligible')
        _pin(value)
    tool=validate_tools(Path(s['runtime_record']['overlay_tools_root']))
    backing=load_stopped_overlay(report_path,tool)
    if len(backing['layers'])>=MAX_OVERLAY_DEPTH:raise ValueError('No remaining depth for installed-app boot')
    descriptors=preserve.descriptor_check([Path(x['path']) for x in retention.values()])
    if Path('/proc').joinpath(str(report['pid'])).exists():raise ValueError('Emulator PID exists after hashing')
    # Revalidate all mutable input dependencies once more after potentially long hashes.
    validate_session(context['session_path'],context['session_sha256'])
    if digest_bytes((report_path.parent/'serial.log').read_bytes())!=content['serial_sha256']:
        raise ValueError('Serial changed during verification')
    if any(digest_bytes(Path(p).read_bytes())!=h for p,h in stable_hashes.items()):raise ValueError('Inspected metadata changed during verification')
    return {'schema':'inferno.verified-import-stage.v1','eligible':True,'session_sha256':context['session_sha256'],
            'report':str(report_path),'report_sha256':stable_hashes[str(report_path)],
            'retention':str(retention_path),'retention_sha256':stable_hashes[str(retention_path)],
            'content':content,'shutdown':shutdown,'descriptor_check':descriptors,'content_checkpoint_sha256':stable_hashes[str(Path(content_check_path))],'backing_depth':len(backing['layers']),
            'scope':'Stage eligibility only, not app launch. Point-in-time source/process evidence; no exclusive lock or nonce-authenticated serial.'}
