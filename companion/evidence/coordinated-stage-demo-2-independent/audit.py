#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Read-only actual coordinator evidence audit, without repeating disk hashes."""
import hashlib,importlib.util,json,stat,sys
from pathlib import Path
D=Path('/home/brandonin/.local/share/inferno/app-import/coordinated-stage-demo-2');R=D/'recovery-run';S=Path('/tmp/inferno-stage-import/companion');sys.path.insert(0,str(S))
spec=importlib.util.spec_from_file_location('coordinator',S/'stage-import.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
def read(p):return m.strict_json(p.read_bytes())
sha=m.digest
launch=read(D/'launch.json');session_path=Path(launch['session_path']);session=read(session_path)
assert sha(session_path)==launch['session_sha256']
assert all(sha(Path(p))==h for p,h in launch['source_sha256'].items())
assert not (D/'INCOMPLETE.json').exists() and not (D/'failure.json').exists()
assert launch['command']==m.fixed_command({'session':session},R)
report=m.check_completed_report({'session':session},R/'report.json')
manifest=m.IMPORTER.validate_manifest(session['import_manifest']['path'])
sizes={'exec_wrapper':Path(session['exec_wrapper']['path']).stat().st_size,'system_launcher':Path(session['launcher']['path']).stat().st_size,'launchd_cache':Path(session['cache']['path']).stat().st_size}
serial=(R/'serial.log').read_bytes();raw=m.verify_content(serial,manifest,sizes)
checkpoint=read(D/'content-check.json');assert checkpoint['eligible'] is False and checkpoint['session_sha256']==sha(session_path)
assert hashlib.sha256(serial[:checkpoint['serial_bytes']]).hexdigest()==checkpoint['serial_sha256']
assert m.verify_content(serial[:checkpoint['serial_bytes']],manifest,sizes)['records']==checkpoint['records']
controls=[json.loads(x) for x in (R/'control-transcript.jsonl').read_bytes().splitlines()];assert len(controls)==1
control=controls[0];request=json.loads(control['raw']);assert request['execute']=='finish-observation' and request['arguments']=={}
assert hashlib.sha256(control['raw'].encode()).hexdigest()==control['sha256']
assert checkpoint['captured_time']<request['created']<=control['time']
assert control['response']['return']['finish_requested'] is True
assert read(D/'finish.stdout')==control['response'];assert read(D/'finish-submission.json')['exit_code']==0
qmp=[];offset=0
for line in (R/'qmp-transcript.jsonl').read_bytes().splitlines(keepends=True):
 x=json.loads(line);x.update(byte_offset=offset,byte_length=len(line),message=json.loads(x['raw']));qmp.append(x);offset+=len(line)
quitrows=[x for x in qmp if x['direction']=='send' and x['message'].get('execute')=='quit'];assert len(quitrows)==1 and control['time']<quitrows[0]['time']
shutdown=m.PRESERVE.verify_shutdown(R,report)
freeze=read(D/'freeze-record.json');retention=read(R/'stopped-disk-hashes.json');progress=[json.loads(x) for x in (D/'freeze-progress.jsonl').read_bytes().splitlines()]
assert len(freeze['files'])==len(retention)==len(progress)==7
assert len({x['path'] for x in progress})==7
ancestors=retention['root.qcow2']['backing_chain'];ancestor_ids={(x['device'],x['inode']) for x in ancestors}
checked=[]
for n,e in freeze['files'].items():
 p=Path(e['path']);assert p==R/'disks'/n and not p.is_symlink()
 assert m.identity(p)==e['after'] and e['after']['st_mode']==stat.S_IFREG|0o444
 assert (e['after']['st_dev'],e['after']['st_ino']) not in ancestor_ids
 assert all(e['before'][k]==e['after'][k] for k in ('st_dev','st_ino','st_size','st_mtime_ns'))
 assert e['before']['st_mode'] in (stat.S_IFREG|0o600,stat.S_IFREG|0o644)
 assert retention[n]['sha256']==e['sha256'] and retention[n]['path']==str(p) and retention[n]['bytes']==e['after']['st_size']
 row=next(x for x in progress if x['path']==str(p));assert all(row[k]==e[k] for k in e)
 assert row['time']>max(x['entry']['time'] for x in shutdown['evidence'])
 checked.append({'name':n,'sha256_recorded_by_coordinator_and_retention':e['sha256'],'current_identity':m.identity(p),'freeze_time':row['time']})
for e in ancestors:
 s=Path(e['path']).stat();assert (s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,s.st_ctime_ns,s.st_mode)==(e['device'],e['inode'],e['bytes'],e['mtime_ns'],e['ctime_ns'],stat.S_IFREG|0o444)
keep=read(R/'disks/KEEP-OVERLAY-BACKING.json');assert keep['backing']['path']==retention['root.qcow2']['path'] and keep['backing']['sha256']==retention['root.qcow2']['sha256']
verified=read(D/'verified-stage.json');assert verified['eligible'] is True and verified['session_sha256']==sha(session_path)
assert verified['report_sha256']==sha(R/'report.json') and verified['retention_sha256']==sha(R/'stopped-disk-hashes.json') and verified['content']==raw
runner=read(D/'runner-process.json');assert not Path('/proc/'+str(runner['pid'])).exists() and not Path('/proc/'+str(report['pid'])).exists()
files=['launch.json','runner-process.json','content-check.json','finish-submission.json','finish.stdout','freeze-record.json','freeze-progress.jsonl','verified-stage.json','recovery-run/report.json','recovery-run/serial.log','recovery-run/qmp-transcript.jsonl','recovery-run/control-transcript.jsonl','recovery-run/stopped-disk-hashes.json','recovery-run/stopped-disk-hashes-verification.json']
result={'scope':'Independent raw coordinator audit; no VM, metadata mutation or duplicate namespace/backing hash pass','artifacts':{str(D/n):sha(D/n) for n in files},'source_hashes':launch['source_sha256'],'raw_content':raw,'checkpoint_captured_time':checkpoint['captured_time'],'finish_control':control,'quit':quitrows[0],'shutdown':shutdown,'disks':checked,'retained_ancestors_metadata_unchanged':ancestors,'runner_pid_absent':runner['pid'],'emulator_pid_absent':report['pid'],'eligible':True,'limits':['Disk content hashes are the coordinator/preservation recorded full reads; independently checked metadata and cross-artifact equality, not rehashed here.','No installed-iOS app launch, rendering or compatibility assertion.','Readable process/FD checks are point-in-time, not exclusive global locks.','Guest markers are tied to this fresh run and pinned command/profile; they do not contain a cryptographic session nonce.']}
print(json.dumps(result,indent=2))
