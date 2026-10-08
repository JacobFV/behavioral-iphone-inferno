#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Read-only wrapper audit, no VM actions or namespace/backing hash repetition."""
import collections,hashlib,importlib.util,json,sys
from pathlib import Path
D=Path('/home/brandonin/.local/share/inferno/app-import/durable-boot-demo-1');R=D/'boot';S=Path('/home/brandonin/.local/share/inferno/host-runtimes/ipa-release-host-1/source/companion');sys.path.insert(0,str(S))
spec=importlib.util.spec_from_file_location('boot_import',S/'boot-import.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
read=lambda p:json.loads(p.read_bytes());sha=m.coordinator.digest
assert (D/'INCOMPLETE.json').exists() and (D/'failure.json').exists()
assert not (D/'completed-run.json').exists()
l=read(D/'launch.json');done=read(D/'failure.json');report=read(R/'report.json');session=read(Path(l['session']));stage=read(Path(l['stage']))
assert sha(Path(l['session']))==l['session_sha256']==stage['session_sha256']
assert sha(Path(l['stage']))==l['stage_sha256']=='20e76bb692b788f46884914cef71c835a8dbdd24c5c0c79314c73ea4a98c9876'
assert l['session_sha256']=='faaa48f9b2f7a9f8f1b6f705e09c72a59c05c1025c7af7d355ed1a4af35ed044'
assert session['source_revision']=='3f8b2d5623a2ac862eba2899771049c44b197316'
assert Path(session['recovery_command'][1]).parent==S
assert all(sha(S/name)==expected for name,expected in session['sources'].items())
assert all(sha(Path(p))==h for p,h in l['source_sha256'].items())
assert l['command']==m.fixed_command({'session':session},Path(stage['report']),R,1200)
assert l['fresh_stage_verification']['eligible'] is True
for k in ('schema','eligible','session_sha256','report','report_sha256','retention','retention_sha256','content','content_checkpoint_sha256','backing_depth'):
 assert stage[k]==l['fresh_stage_verification'][k]
for record in l['inspected_metadata']:
 assert m.public_snapshot(m.snapshot(record['path'],64<<20))==record
profile_path=Path(session['runtime_record']['inputs']['profile']['path']);assert sha(profile_path)==session['runtime_record']['inputs']['profile']['sha256']
profile=read(profile_path);inputs={k:{'path':str(Path(profile[k]['path']).resolve()),'sha256':profile[k]['sha256'],'bytes':Path(profile[k]['path']).stat().st_size} for k in ('kernel','dtb','trustcache','ramdisk')}
context={'session':session,'verified_runtime':{'profile_inputs':inputs}}
try:
 m.normal_result(R/'report.json',context,Path(stage['report']),l['fresh_stage_verification'])
 raise AssertionError('Forensic report incorrectly accepted as normal')
except ValueError as exc:
 normal_rejection=str(exc)
assert done['app_execution_asserted'] is False and done['status']=='failed-incomplete-do-not-promote'
assert done['cleanup']['runner_exit_code']==1 and done['cleanup']['remaining_session_members']==[]
assert report['attempt_completed'] is False and report['error']=={'type':'KeyboardInterrupt','detail':'Signal 2'} and report['exit_code']==0
shutdown=m.coordinator.PRESERVE.verify_shutdown(R,report,failed_attempt=True)
stop=read(D/'operator-stop.json');assert stop['signal']==2
assert read(R/'command.json')==report['invocation']
qmp=[];offset=0
for raw in (R/'qmp-transcript.jsonl').read_bytes().splitlines(keepends=True):
 e=json.loads(raw);e.update(byte_offset=offset,byte_length=len(raw),message=json.loads(e['raw']));qmp.append(e);offset+=len(raw)
quit_rows=[e for e in qmp if e['direction']=='send' and e['message'].get('execute')=='quit'];assert len(quit_rows)==1
controls=[];offset=0
for raw in (R/'control-transcript.jsonl').read_bytes().splitlines(keepends=True):
 e=json.loads(raw);e.update(byte_offset=offset,byte_length=len(raw),request=json.loads(e['raw']));assert hashlib.sha256(e['raw'].encode()).hexdigest()==e['sha256'];controls.append(e);offset+=len(raw)
finish=[e for e in controls if e['request']['execute']=='finish-observation'];assert len(finish)==0
assert stop['time']<quit_rows[0]['time']
runner=read(D/'runner-process.json');outer=read(D.with_suffix('.launch.json'))
assert stop['pid']==runner['pid']
for pid in (runner['pid'],report['pid'],outer['pid']):assert not Path('/proc/'+str(pid)).exists()
files=['launch.json','runner-process.json','failure.json','INCOMPLETE.json','operator-stop.json','stdout.log','stderr.log','boot/report.json','boot/command.json','boot/profile.json','boot/serial.log','boot/control-transcript.jsonl','boot/qmp-transcript.jsonl']
result={'scope':'Independent actual boot-import wrapper/source/raw-shutdown audit; no VM, disk metadata changes or namespace hashes','artifacts':{str(D/n):sha(D/n) for n in files},'source_sha256':l['source_sha256'],'selected_stage_sha256':l['stage_sha256'],'selected_session_sha256':l['session_sha256'],'fixed_command':l['command'],'actual_profile_inputs':inputs,'generic_report_kind':report['kind'],'failure_result':done,'normal_verifier_rejection':normal_rejection,'raw_shutdown':shutdown,'control_command_counts':dict(collections.Counter(e['request']['execute'] for e in controls)),'operator_finish_count':0,'operator_stop':stop,'quit':quit_rows[0],'absent_pids':{'wrapper':outer['pid'],'runner':runner['pid'],'emulator':report['pid']},'limits':['Failed interaction: root reports counter0 after one ACK. No app callback telemetry; no confirmed display-freeze cause or execution-success assertion.','No namespace/backing content rehash; existing runner pre/postflight and earlier stage verification remain their recorded evidence.','No automatic guest control is introduced by wrapper; operator transcript retained separately.','Host readable-FD/PID observations are point-in-time, not exclusive locks.']}
counter_id='703788b2ec02444dbd48b31236cafdb6'
counter_controls=[e for e in controls if e['request'].get('arguments',{}).get('request_id')==counter_id]
assert len(counter_controls)==1
serial=(R/'serial.log').read_bytes();rows=[];offset=0
for raw in serial.split(b'\n'):
 if counter_id.encode() in raw: rows.append({'byte_offset':offset,'byte_length':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),'text':raw.rstrip(b'\r').decode()})
 offset+=len(raw)+1
assert len([r for r in rows if r['text'].startswith('INFERNO_HID_ACK ') and 'attempt_status=0 delivery=unproven' in r['text']])==1
result['counter_transport']={'control':counter_controls[0],'raw_records':rows,'application_callback_proven':False,'pixel_review':'Separate root evidence; not classified by this audit'}
print(json.dumps(result,indent=2))
