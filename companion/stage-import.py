#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Run one explicitly requested imported-app recovery stage; never launch the app."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import signal
import stat
import subprocess
import sys
import time
from import_stage import validate_session, verify_content, verify_stopped, strict_json
from disk_overlay import AUXILIARY_SIZES

SOURCE=Path(__file__).resolve().parent
RECOVERY_SECONDS=1200
STOP_SECONDS=180


def load(name):
    spec=importlib.util.spec_from_file_location(name.replace('-','_'),SOURCE/(name+'.py'))
    mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);return mod

PRESERVE=load('preserve-stopped')
IMPORTER=load('app-import')


def digest(path):
    with Path(path).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def source_inventory():
    """Hash the actual coordinator, validator and runner Python dependencies."""
    names=('stage-import.py','import_stage.py','preserve-stopped.py',
           'disk_overlay.py','app-import.py','boot.py','qmp_control.py',
           'probe_journey.py','headless_refresh.py','boot_milestones.py')
    paths=[SOURCE/name for name in names]
    for path in paths:
        if not path.is_file():raise ValueError('Required coordinator source missing: '+str(path))
    return paths,{str(path):digest(path) for path in paths}


def write_new(path,record):
    with Path(path).open('x') as f:json.dump(record,f,indent=2,allow_nan=False);f.write('\n')


def identity(path):
    s=Path(path).lstat()
    if not stat.S_ISREG(s.st_mode):raise ValueError('Expected regular non-symlink disk: '+str(path))
    return {k:getattr(s,k) for k in ('st_dev','st_ino','st_size','st_mode','st_mtime_ns','st_ctime_ns')}


def no_running_emulator():
    """Readable /proc only, with current-UID inspection failures fatal."""
    found=[];denied=[];uid=os.getuid()
    for p in Path('/proc').iterdir():
        if not p.name.isdigit():continue
        try:
            owner=p.stat().st_uid
            comm=(p/'comm').read_text().strip()
            # The USB companion (usb-companion.py) is a separate Linux guest that the iOS
            # machine attaches to; it never touches iOS disks, so it does not count.
            if comm.startswith('qemu-system') and b'/usb-companion/' not in (p/'cmdline').read_bytes():found.append({'pid':int(p.name),'comm':comm})
        except (FileNotFoundError,ProcessLookupError):continue
        except PermissionError:
            if p.exists() and p.stat().st_uid==uid:raise ValueError('Cannot inspect own-UID process '+p.name)
            denied.append(int(p.name))
    if found:raise ValueError('An emulator is already running: '+json.dumps(found))
    return {'matching_processes':found,'permission_denied_pids':denied,'scope':'Readable /proc comm inventory; no exclusive host lock','time':time.time()}


def owned_group_members(process):
    """List only members of the private session created for our child."""
    expected=getattr(process,'inferno_start_ticks',None)
    if expected is None:raise ValueError('Private session start identity unavailable; refusing group cleanup')
    try:
        leader=Path(f'/proc/{process.pid}/stat').read_text()
        fields=leader[leader.rfind(')')+2:].split()
        if int(fields[19])!=expected:raise ValueError('Private session leader PID was reused')
    except (FileNotFoundError,ProcessLookupError):pass
    members=[]
    for entry in Path('/proc').iterdir():
        if not entry.name.isdigit():continue
        try:
            raw=(entry/'stat').read_text();fields=raw[raw.rfind(')')+2:].split()
            if int(fields[2])==process.pid and int(fields[3])==process.pid:
                members.append(int(entry.name))
        except (FileNotFoundError,ProcessLookupError):continue
        except PermissionError:
            if entry.exists() and entry.stat().st_uid==os.getuid():raise ValueError('Cannot inspect child-session ownership')
    return members


def stop_owned_group(process):
    result={}
    if process.poll() is None:
        process.terminate()
        try:process.wait(timeout=STOP_SECONDS)
        except subprocess.TimeoutExpired:pass
    members=owned_group_members(process)
    if members:
        # The original private session still exists: do not target an arbitrary
        # PID taken from guest/report data. Kill residual owned session members.
        os.killpg(process.pid,signal.SIGKILL)
        result['forced_private_group_kill']=members
    if process.poll() is None:process.wait(timeout=10)
    result['runner_exit_code']=process.returncode
    result['remaining_session_members']=owned_group_members(process)
    return result


def fixed_command(context,report_dir):
    """Never execute arbitrary command fields from session JSON."""
    s=context['session'];i=s['runtime_record']['inputs']
    for filename in ('boot.py','qmp_control.py'):
        if digest(SOURCE/filename)!=s['sources'][filename]:raise ValueError('Current runner/control differs from pinned prepared session')
    return [sys.executable,str(SOURCE/'boot.py'),'--profile',s['recovery_profile']['path'],
            '--overlay-base-report',i['base_report']['path'],'--overlay-tools-root',s['runtime_record']['overlay_tools_root'],
            '--ramdisk-boot','--control-mailbox','--guest-errors','--binary',i['emulator']['path'],
            '--manifest',i['emulator_build']['path'],'--seconds',str(RECOVERY_SECONDS),'--output',str(report_dir)]


def check_completed_report(context,report_path):
    s=context['session'];r=strict_json(report_path.read_bytes())
    if r.get('attempt_completed') is not True or r.get('error') or r.get('exit_code')!=0 or r.get('kind')!='t8030_recovery_ramdisk_experiment':
        raise ValueError('Recovery did not complete normally')
    if r.get('profile_sha256')!=s['recovery_profile']['sha256'] or r.get('runner_sha256')!=s['sources']['boot.py'] or r.get('control_source_sha256')!=s['sources']['qmp_control.py']:
        raise ValueError('Stopped runner/profile/source mismatch')
    if r.get('observation_run_control',{}).get('finish_requested') is not True or r.get('probe_journey'):
        raise ValueError('Normal non-journey finish missing')
    PRESERVE.verify_shutdown(report_path.parent,r)
    return r


def freeze_new_disks(report_path,report,context,output):
    """Freeze only seven new files under this coordinator's fresh report directory."""
    folder=report_path.parent/'disks';expected={'root.qcow2',*AUXILIARY_SIZES}
    if folder.is_symlink() or {p.name for p in folder.iterdir()}!=expected:
        raise ValueError('New disk directory must contain exactly seven files before freeze')
    declared={Path(x['path']).name:Path(x['path']) for x in report['disks']}
    if len(report['disks'])!=7 or set(declared)!=expected or any(p!=folder/n for n,p in declared.items()):
        raise ValueError('Report namespaces are not exact new output paths')
    inherited={(x['device'],x['inode']) for x in context['verified_runtime']['base']['layers']}
    for entry in context['verified_runtime']['base']['auxiliary'].values():
        st=Path(entry['path']).stat();inherited.add((st.st_dev,st.st_ino))
    before={n:identity(p) for n,p in declared.items()}
    for n,v in before.items():
        if v['st_mode'] not in (stat.S_IFREG|0o600,stat.S_IFREG|0o644) or (v['st_dev'],v['st_ino']) in inherited or declared[n].stat().st_nlink!=1:
            raise ValueError('Only new singly linked writable namespaces may be frozen: '+n)
        if n in AUXILIARY_SIZES and v['st_size']!=AUXILIARY_SIZES[n]:raise ValueError('Namespace size mismatch')
    fd_before=PRESERVE.descriptor_check(declared.values())
    hashes={n:digest(p) for n,p in declared.items()}
    if any(identity(p)!=before[n] for n,p in declared.items()):raise ValueError('New disks changed during pre-freeze hashes')
    fd_after_hash=PRESERVE.descriptor_check(declared.values())
    record={'scope':'Only newly allocated current report seven files; ancestors never chmod','fd_before':fd_before,'fd_after_hash':fd_after_hash,'files':{}}
    journal=output/'freeze-progress.jsonl'
    for n,p in sorted(declared.items()):
        if identity(p)!=before[n]:raise ValueError('Disk identity changed immediately before freeze: '+n)
        PRESERVE.descriptor_check([p])
        # Descriptor chmod avoids replacing the path between lstat and chmod.
        fd=os.open(p,os.O_RDONLY|os.O_NOFOLLOW)
        try:
            opened=os.fstat(fd)
            if {k:getattr(opened,k) for k in before[n]}!=before[n]:raise ValueError('Freeze descriptor identity differs')
            os.fchmod(fd,0o444)
            frozen=os.fstat(fd)
        finally:os.close(fd)
        after={k:getattr(frozen,k) for k in before[n]}
        if any(after[k]!=before[n][k] for k in ('st_dev','st_ino','st_size','st_mtime_ns')) or after['st_mode']!=(stat.S_IFREG|0o444) or identity(p)!=after:
            raise ValueError('Unexpected metadata change during freeze')
        value={'path':str(p),'sha256':hashes[n],'before':before[n],'after':after}
        record['files'][n]=value
        with journal.open('a') as f:f.write(json.dumps({'time':time.time(),**value})+'\n');f.flush();os.fsync(f.fileno())
    root=record['files']['root.qcow2'];v=root['after']
    write_new(folder/'KEEP-OVERLAY-BACKING.json',{'backing':{'path':root['path'],'sha256':root['sha256'],'bytes':v['st_size'],'device':v['st_dev'],'inode':v['st_ino'],'mtime_ns':v['st_mtime_ns'],'ctime_ns':v['st_ctime_ns'],'mode':'0o444'},'retirement_prohibited_while_dependent_overlays_exist':True,'scope':'New successful recovery stage only; no ancestor metadata changed'})
    write_new(output/'freeze-record.json',record)
    return record


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--session',type=Path,required=True);parser.add_argument('--session-sha256',required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();output=None;process=None;finish_started=False;logs=[]
    try:
        source_paths,sources=source_inventory()
        context=validate_session(args.session,args.session_sha256)
        output=IMPORTER.external_output(args.output)
        proc_check=no_running_emulator()
        command=fixed_command(context,output/'recovery-run')
        output.mkdir(mode=0o700)
        write_new(output/'INCOMPLETE.json',{'status':'incomplete-do-not-consume','session_sha256':args.session_sha256,'started':time.time()})
        write_new(output/'launch.json',{'command':command,'session_path':str(args.session.absolute()),'session_sha256':args.session_sha256,'proc_preflight':proc_check,'source_sha256':sources,'scope':'One explicit recovery attempt only; no app launch or automatic retry'})
        # Recheck immediately before launch; this remains a point-in-time guard.
        no_running_emulator()
        if {str(p):digest(p) for p in source_paths}!=sources:raise ValueError('Coordinator dependencies changed before launch')
        for name in ('stdout.log','stderr.log'):logs.append((output/name).open('xb'))
        process=subprocess.Popen(command,stdout=logs[0],stderr=logs[1],start_new_session=True)
        runner_stat=Path(f'/proc/{process.pid}/stat').read_text()
        process.inferno_start_ticks=int(runner_stat[runner_stat.rfind(')')+2:].split()[19])
        write_new(output/'runner-process.json',{'pid':process.pid,'command':command,'proc_stat':runner_stat,'start_ticks':process.inferno_start_ticks,'started':time.time()})
        deadline=time.monotonic()+RECOVERY_SECONDS
        report_dir=output/'recovery-run';serial=report_dir/'serial.log';checkpoint=None
        while time.monotonic()<deadline:
            if process.poll() is not None:raise ValueError('Runner exited before verified preparation')
            if serial.exists():
                if serial.stat().st_size>64<<20:raise ValueError('Recovery serial exceeds bound')
                started=time.time();raw=serial.read_bytes();captured=time.time()
                if b'INFERNO_PREP_COMPLETE:' in raw:
                    checkpoint=verify_content(raw,context['manifest'],context['artifact_sizes'])
                    checkpoint.update(session_sha256=args.session_sha256,eligible=False,read_started_time=started,captured_time=captured)
                    write_new(output/'content-check.json',checkpoint)
                    break
                if b'INFERNO_TREE_MISMATCH' in raw or b'INFERNO_IMPORTED_APP_FINISH result=' in raw and b'INFERNO_IMPORTED_APP_FINISH result=0 unmount=0 errno=0' not in raw:
                    raise ValueError('Recovery reported preparation failure')
            time.sleep(1)
        if checkpoint is None:raise TimeoutError('Recovery preparation deadline expired')
        # Exactly one submission. A lost response is uncertain and never retried.
        finish_started=True
        finish_command=[sys.executable,str(SOURCE/'qmp_control.py'),'--report',str(report_dir),'finish-observation']
        with (output/'finish.stdout').open('xb') as out,(output/'finish.stderr').open('xb') as err:
            finish=subprocess.run(finish_command,stdout=out,stderr=err,timeout=45)
        write_new(output/'finish-submission.json',{'command':finish_command,'exit_code':finish.returncode,'automatic_retry':False})
        if finish.returncode:raise ValueError('finish-observation response failed/uncertain')
        if process.wait(timeout=STOP_SECONDS)!=0:raise ValueError('Recovery runner returned failure')
        if Path(f'/proc/{process.pid}').exists() or owned_group_members(process):raise ValueError('Runner or its private session still exists')
        report_path=report_dir/'report.json';report=check_completed_report(context,report_path)
        # Raw content must still be successful after all serial output flushed.
        verify_content(serial.read_bytes(),context['manifest'],context['artifact_sizes'])
        if {str(p):digest(p) for p in source_paths}!=sources:raise ValueError('Coordinator dependencies changed before freeze')
        frozen=freeze_new_disks(report_path,report,context,output)
        retention=report_dir/'stopped-disk-hashes.json'
        PRESERVE.preserve(report_path,retention,False)
        retained=strict_json(retention.read_bytes())
        for name,entry in frozen['files'].items():
            if retained[name]['sha256']!=entry['sha256'] or identity(entry['path'])!=entry['after']:raise ValueError('Frozen namespace changed before retention')
        verified=verify_stopped(context,report_path,retention,output/'content-check.json')
        if {str(p):digest(p) for p in source_paths}!=sources:raise ValueError('Coordinator dependencies changed during execution')
        write_new(output/'verified-stage.json',verified)
        (output/'INCOMPLETE.json').unlink()
        print(json.dumps({'stage':str(output/'verified-stage.json'),'sha256':digest(output/'verified-stage.json'),'eligible':True,'scope':'Recovery staging only; no app execution claim'}))
        return 0
    except BaseException as exc:
        cleanup={}
        if process is not None:
            try:cleanup=stop_owned_group(process)
            except Exception as stop_error:cleanup={'error':str(stop_error),'owned_runner_pid':process.pid}
        if output is not None and output.is_dir():
            write_new(output/'failure.json',{'status':'failed-forensic-only-do-not-consume','type':type(exc).__name__,'error':str(exc),'finish_submission_started':finish_started,'cleanup':cleanup,'scope':'No eligibility promotion; partial freezes/attempt files retained'})
        print('stage-import failed: '+str(exc),file=sys.stderr)
        return 1
    finally:
        for log in logs:log.close()

if __name__=='__main__':raise SystemExit(main())
