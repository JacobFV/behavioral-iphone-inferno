#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Read-only wrapper audit, no VM actions or namespace/backing hash repetition."""
import collections,hashlib,importlib.util,json,sys
from pathlib import Path
D=Path('/home/brandonin/.local/share/inferno/app-import/boot-import-demo-1');R=D/'boot';S=Path('/tmp/inferno-boot-import/companion');sys.path.insert(0,str(S))
spec=importlib.util.spec_from_file_location('boot_import',S/'boot-import.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
read=lambda p:json.loads(p.read_bytes());sha=m.coordinator.digest
assert not (D/'INCOMPLETE.json').exists() and not (D/'failure.json').exists()
l=read(D/'launch.json');done=read(D/'completed-run.json');report=read(R/'report.json');session=read(Path(l['session']));stage=read(Path(l['stage']))
assert sha(Path(l['session']))==l['session_sha256']==stage['session_sha256']
assert sha(Path(l['stage']))==l['stage_sha256']
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
fresh=m.normal_result(R/'report.json',context,Path(stage['report']),l['fresh_stage_verification'])
assert fresh==done and done['app_execution_asserted'] is False
assert done['report_sha256']==sha(R/'report.json')
assert read(R/'command.json')==report['invocation']
qmp=[];offset=0
for raw in (R/'qmp-transcript.jsonl').read_bytes().splitlines(keepends=True):
 e=json.loads(raw);e.update(byte_offset=offset,byte_length=len(raw),message=json.loads(e['raw']));qmp.append(e);offset+=len(raw)
quit_rows=[e for e in qmp if e['direction']=='send' and e['message'].get('execute')=='quit'];assert len(quit_rows)==1
controls=[];offset=0
for raw in (R/'control-transcript.jsonl').read_bytes().splitlines(keepends=True):
 e=json.loads(raw);e.update(byte_offset=offset,byte_length=len(raw),request=json.loads(e['raw']));assert hashlib.sha256(e['raw'].encode()).hexdigest()==e['sha256'];controls.append(e);offset+=len(raw)
finish=[e for e in controls if e['request']['execute']=='finish-observation'];assert len(finish)==1
assert finish[0]['request']['arguments']=={} and finish[0]['response']['return']['finish_requested'] is True and finish[0]['time']<quit_rows[0]['time']
runner=read(D/'runner-process.json');outer=read(D.with_suffix('.launch.json'))
for pid in (runner['pid'],report['pid'],outer['pid']):assert not Path('/proc/'+str(pid)).exists()
files=['launch.json','runner-process.json','completed-run.json','stdout.log','stderr.log','boot/report.json','boot/command.json','boot/profile.json','boot/serial.log','boot/control-transcript.jsonl','boot/qmp-transcript.jsonl']
result={'scope':'Independent actual boot-import wrapper/source/raw-shutdown audit; no VM, disk metadata changes or namespace hashes','artifacts':{str(D/n):sha(D/n) for n in files},'source_sha256':l['source_sha256'],'selected_stage_sha256':l['stage_sha256'],'selected_session_sha256':l['session_sha256'],'fixed_command':l['command'],'actual_profile_inputs':inputs,'generic_report_kind':report['kind'],'normal_result':done,'control_command_counts':dict(collections.Counter(e['request']['execute'] for e in controls)),'operator_finish':finish[0],'quit':quit_rows[0],'absent_pids':{'wrapper':outer['pid'],'runner':runner['pid'],'emulator':report['pid']},'limits':['App pixels and input outcome require separate root visual evidence; wrapper explicitly does not assert execution.','No namespace/backing content rehash; existing runner pre/postflight and earlier stage verification remain their recorded evidence.','No automatic guest control is introduced by wrapper; operator transcript retained separately.','Host readable-FD/PID observations are point-in-time, not exclusive locks.']}
print(json.dumps(result,indent=2))
