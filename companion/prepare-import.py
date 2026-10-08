#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Prepare a pinned owned IPA recovery session; never launch a VM or promote disks."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import plistlib
import stat
import subprocess
import sys
import time
from boot import load_profile
from disk_overlay import validate_tools, load_stopped_overlay

SOURCE = Path(__file__).resolve().parent

def sha(path):
    with Path(path).open('rb') as f:
        return hashlib.file_digest(f,'sha256').hexdigest()

def read_json(path):
    if Path(path).stat().st_size > 16 << 20:
        raise ValueError('JSON exceeds16MiB: '+str(path))
    return json.loads(Path(path).read_bytes())

def pin(record):
    if set(record)!={'path','sha256'}:
        raise ValueError('Expected exact path/sha256 pin')
    path=Path(record['path'])
    if not path.is_absolute() or path.resolve(strict=True)!=path or not stat.S_ISREG(path.lstat().st_mode) or sha(path)!=record['sha256']:
        raise ValueError('Missing, aliased or changed pinned input: '+str(path))
    return path

def artifact(path):
    path=Path(path).resolve(strict=True)
    return {'path':str(path),'sha256':sha(path)}

def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path);value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value);return value

IMPORTER=module('owned_ipa_import',SOURCE/'app-import.py')

def validate_runtime(record):
    expected={'schema','inputs','overlay_tools_root','cache_binding'}
    names={'profile','raw_ramdisk','probe','disk_helper','helper_build','hfsplus','clang','linker','cache','base_report','emulator','emulator_build'}
    if set(record)!=expected or record['schema']!='inferno.local-ipa-runtime.v1' or set(record['inputs'])!=names:
        raise ValueError('Unsupported runtime schema/fields')
    paths={k:pin(v) for k,v in record['inputs'].items()}
    profile,inputs=load_profile(paths['profile'])
    build=read_json(paths['emulator_build'])
    if build.get('binary',{}).get('sha256')!=record['inputs']['emulator']['sha256']:
        raise ValueError('Emulator build does not bind binary')
    helper=read_json(paths['helper_build'])
    if helper.get('outputs',{}).get('inferno-prepare-root',{}).get('sha256')!=record['inputs']['disk_helper']['sha256']:
        raise ValueError('Helper build does not bind prepare-root')
    for name in ('prepare-root.c','imported-app.c','libSystem.tbd','entitlements.plist'):
        values=[v for p,v in helper.get('sources',{}).items() if Path(p).name==name]
        if values!=[sha(SOURCE/'native-probe'/name)]:
            raise ValueError('Preparation helper source differs: '+name)
    binding=record['cache_binding']
    required={'basis','base_report_sha256','cache_sha256','install_profile','install_report','install_serial','cache_readback','raw_ramdisk_preparation','lineage_evidence'}
    if set(binding)!=required or binding['basis']!='reviewed-retained-lineage-not-fresh-guest-export':
        raise ValueError('Explicit reviewed cache lineage binding required')
    if binding['base_report_sha256']!=record['inputs']['base_report']['sha256'] or binding['cache_sha256']!=record['inputs']['cache']['sha256']:
        raise ValueError('Cache binding differs from selected base/cache')
    bpaths={k:pin(binding[k]) for k in ('install_profile','install_report','install_serial','cache_readback','raw_ramdisk_preparation')}
    if not isinstance(binding['lineage_evidence'],list) or not 1<=len(binding['lineage_evidence'])<=32:
        raise ValueError('Concrete retained lineage evidence required')
    for evidence in binding['lineage_evidence']:pin(evidence)
    ip=read_json(bpaths['install_profile']);ir=read_json(bpaths['install_report'])
    raw_preparation=read_json(bpaths['raw_ramdisk_preparation'])
    if raw_preparation.get('source_raw_sha256')!=record['inputs']['raw_ramdisk']['sha256'] or raw_preparation.get('source_profile')!=str(paths['profile']):
        raise ValueError('Raw recovery source binding differs')
    if ip.get('provenance',{}).get('launchd_cache_sha256')!=binding['cache_sha256'] or sha(bpaths['cache_readback'])!=binding['cache_sha256']:
        raise ValueError('Original install profile/readback do not bind cache bytes')
    if ir.get('profile_sha256')!=binding['install_profile']['sha256'] or ir.get('exit_code')!=0:
        raise ValueError('Original cache install report/profile mismatch')
    if bpaths['install_serial']!=bpaths['install_report'].parent/'serial.log':
        raise ValueError('Original install serial must belong to retained report')
    marker=('INFERNO_CACHE_READBACK bytes=%d mismatches=0'%paths['cache'].stat().st_size).encode()
    lines=[x.rstrip(b'\r') for x in bpaths['install_serial'].read_bytes().split(b'\n')]
    if lines.count(marker)!=1 or not any(x.startswith(b'INFERNO_PREP_COMPLETE:') for x in lines):
        raise ValueError('Retained original cache staging raw success absent/ambiguous')
    tool=validate_tools(Path(record['overlay_tools_root']))
    base=load_stopped_overlay(paths['base_report'],tool)
    # Both a recovery child and its installed observation child must fit.
    if len(base['layers'])+1>4:
        raise ValueError('Insufficient recorded overlay depth for recovery and installed child')
    return paths,{'profile_inputs':inputs,'base':base,'overlay_tool':tool,
        'cache_binding_scope':'Reviewed retained lineage selected by caller, references checked. Not independent proof of current guest cache identity; actual new staging readback still required.'}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--ipa',type=Path,required=True);p.add_argument('--runtime',type=Path,required=True)
    p.add_argument('--runtime-sha256',required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();output=None
    try:
        runtime_path=pin({'path':str(a.runtime.absolute()),'sha256':a.runtime_sha256})
        runtime=read_json(runtime_path)
        output=IMPORTER.external_output(a.output)
        paths,verified=validate_runtime(runtime)
        output.mkdir(mode=0o700)
        (output/'INCOMPLETE.json').write_text(json.dumps({'status':'incomplete-do-not-consume','started':time.time()})+'\n')
        commands=[]
        def run(label,args):
            command=[sys.executable,*map(str,args)];start=time.time()
            with (output/(label+'.log')).open('xb') as log:
                result=subprocess.run(command,stdout=log,stderr=subprocess.STDOUT)
            commands.append({'label':label,'argv':command,'started':start,'finished':time.time(),'exit_code':result.returncode,'log':artifact(output/(label+'.log'))})
            (output/'commands.json').write_text(json.dumps(commands,indent=2)+'\n')
            if result.returncode:raise ValueError(label+' failed; retain incomplete output')
        run('import',[SOURCE/'app-import.py','--ipa',a.ipa.resolve(strict=True),'--output',output/'import'])
        manifest_path=output/'import/manifest.json';m=IMPORTER.validate_manifest(manifest_path);manifest_pin=artifact(manifest_path)
        run('launcher',[SOURCE/'app-probe/build-import-launcher.py','--manifest',manifest_path,'--manifest-sha256',manifest_pin['sha256'],'--clang',paths['clang'],'--linker',paths['linker'],'--output',output/'launcher'])
        cache=output/'launchd-cache.plist';job=output/'launcher/org.inferno.app-probe.plist'
        run('cache',[SOURCE/'native-probe/merge-launchd-cache.py','--cache',paths['cache'],'--replace-owned-job',job,'--output',cache])
        original=plistlib.loads(paths['cache'].read_bytes());merged=plistlib.loads(cache.read_bytes());replacement=plistlib.loads(job.read_bytes())
        keys=[k for k,v in original['LaunchDaemons'].items() if v.get('Label')=='org.inferno.app-probe']
        if len(keys)!=1 or replacement.get('Label')!='org.inferno.app-probe':raise ValueError('Expected exactly one existing owned job')
        expected={**original,'LaunchDaemons':{**original['LaunchDaemons'],keys[0]:replacement}}
        if merged!=expected:raise ValueError('Cache merge changed entries beyond selected owned job')
        run('prepare',[SOURCE/'native-probe/prepare.py','--profile',paths['profile'],'--raw-ramdisk',paths['raw_ramdisk'],'--probe',paths['probe'],'--hfsplus',paths['hfsplus'],'--disk-helper',paths['disk_helper'],'--disk-helper-existing','--imported-app-manifest',manifest_path,'--imported-app-manifest-sha256',manifest_pin['sha256'],'--system-launcher',output/'launcher/inferno-launcher','--exec-wrapper',output/'launcher/inferno-exec-launcher','--launchd-cache',cache,'--launchd-cache-sha256',sha(cache),'--output',output/'recovery'])
        prep=output/'recovery';readbacks=[]
        for source,dest in [(paths['probe'],prep/'readback-probe'),(cache,prep/'readback-launchd-cache'),(output/'launcher/inferno-launcher',prep/'readback-system-launcher'),(output/'launcher/inferno-exec-launcher',prep/'readback-exec-wrapper'),(prep/'imported-app.plan',prep/'readback-imported-app.plan')]:
            if sha(source)!=sha(dest):raise ValueError('Prepared HFS readback mismatch: '+str(dest))
            readbacks.append(artifact(dest))
        stage=module('imported_app_plan',SOURCE/'native-probe/imported_app.py');_,_,records,_=stage.validate(manifest_path,manifest_pin['sha256'])
        for i,entry in enumerate(records):
            if entry['type']==2:
                dest=prep/('readback-imported-%04d'%i)
                if dest.stat().st_size!=entry['bytes'] or sha(dest)!=entry['sha256']:raise ValueError('Imported HFS readback mismatch')
                readbacks.append(artifact(dest))
        IMPORTER.validate_manifest(manifest_path)
        for value in runtime['inputs'].values():pin(value)
        if sha(runtime_path)!=a.runtime_sha256:raise ValueError('Runtime changed during preparation')
        # Read-only complete base verification again; no chmod, KEEP writes or overlays.
        after=load_stopped_overlay(paths['base_report'],verified['overlay_tool'])
        if after!=verified['base']:raise ValueError('Base validation changed during host preparation')
        load_profile(prep/'profile.json')
        recover=[sys.executable,str(SOURCE/'boot.py'),'--profile',str(prep/'profile.json'),'--overlay-base-report',str(paths['base_report']),'--overlay-tools-root',runtime['overlay_tools_root'],'--ramdisk-boot','--control-mailbox','--guest-errors','--binary',str(paths['emulator']),'--manifest',str(paths['emulator_build']),'--seconds','1200','--output',str(output/'recovery-run')]
        expected_markers=['INFERNO_EXEC_WRAPPER_READBACK bytes=%d mismatches=0'%(output/'launcher/inferno-exec-launcher').stat().st_size,'INFERNO_SYSTEM_LAUNCHER_READBACK bytes=%d mismatches=0'%(output/'launcher/inferno-launcher').stat().st_size,'INFERNO_IMPORTED_APP_READBACK bundle=%s bytes=%d entries=%d mismatches=0'%(m['bundle']['directory_name'],sum(x['bytes'] for x in m['files']),len(records)),'INFERNO_IMPORTED_APP_FINISH result=0 unmount=0 errno=0','INFERNO_CACHE_READBACK bytes=%d mismatches=0'%cache.stat().st_size,'INFERNO_PREP_COMPLETE: requested preparation operations succeeded']
        sources=[SOURCE/'prepare-import.py',SOURCE/'app-import.py',SOURCE/'app-probe/build-import-launcher.py',SOURCE/'native-probe/merge-launchd-cache.py',SOURCE/'native-probe/prepare.py',SOURCE/'native-probe/imported_app.py',SOURCE/'disk_overlay.py',SOURCE/'boot.py']
        result={'schema':'inferno.prepared-import-session.v1','status':'host-prepared-not-staged','runtime':artifact(runtime_path),'runtime_record':runtime,'verified_runtime':verified,'import_manifest':manifest_pin,'bundle':m['bundle'],'tree_sha256':m['tree_sha256'],'launcher_build':artifact(output/'launcher/build-evidence.json'),'launcher':artifact(output/'launcher/inferno-launcher'),'exec_wrapper':artifact(output/'launcher/inferno-exec-launcher'),'launchd_job':artifact(job),'cache':artifact(cache),'recovery_profile':artifact(prep/'profile.json'),'recovery_ramdisk':artifact(prep/'ramdisk.raw'),'preparation':artifact(prep/'preparation.json'),'readbacks':readbacks,'expected_guest_markers':expected_markers,'recovery_command':recover,'commands':commands,'sources':{str(x.relative_to(SOURCE)):sha(x) for x in sources},'source_revision':subprocess.check_output(['git','-C',str(SOURCE),'rev-parse','HEAD'],text=True).strip(),'limits':['No VM launched, disks modified, base mode changed, or eligibility promoted.','No app execution/launch/presentation success asserted.','Recovery command requires subsequent real raw success and normal stop/retention checks; do not use failed output.','Cache/base relation is explicit reviewed retained provenance, not fresh guest-cache export.','No existing-target overwrite exception, fixture telemetry or generic OPEN automation.']}
        with (output/'session.json').open('x') as f:json.dump(result,f,indent=2);f.write('\n')
        (output/'INCOMPLETE.json').unlink()
        print(json.dumps({'status':result['status'],'session':artifact(output/'session.json')}))
    except Exception as exc:
        if output is not None and output.is_dir():
            (output/'failure.json').write_text(json.dumps({'status':'failed-do-not-consume','type':type(exc).__name__,'error':str(exc)})+'\n')
        p.exit(1,'prepare-import rejected: '+str(exc)+'\n')

if __name__=='__main__':main()
