# SPDX-License-Identifier: AGPL-3.0-or-later
"""Read-only small-file audit; full Apple export and disk bytes remain external."""
import hashlib,importlib.util,json,os
from pathlib import Path
base=Path('/home/brandonin/.local/share/inferno/app-import/runtime-inspection-stage-2')
source=Path('/tmp/inferno-runtime-inspector-framing/companion/runtime-inspector/result.py')
spec=importlib.util.spec_from_file_location('actual_inspector_result',source);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
result_path=base/'runtime-inspection.json';v=json.loads(result_path.read_bytes());raw=(base/'recovery-run/serial.log').read_bytes()
content,export=m.verify_content(raw)
assert content==v['content'] and export==(base/'launchd.plist').read_bytes()
assert v['status']=='observed-not-runtime-ready' and v['runtime_base_eligible'] is False and v['ipa_runtime_ready'] is False and v['backing_depth']==4
assert not any((base/n).exists() for n in ['INCOMPLETE.json','failure.json'])
report=json.loads((base/'recovery-run/report.json').read_bytes());assert report['attempt_completed'] is True and report.get('error') is None and report['exit_code']==0
checkpoint=json.loads((base/'content-check.json').read_bytes());assert hashlib.sha256(raw[:checkpoint['serial_bytes']]).hexdigest()==checkpoint['serial_sha256']
controls=[json.loads(x) for x in (base/'recovery-run/control-transcript.jsonl').read_bytes().split(b'\n') if x];assert len(controls)==1
control=controls[0];request=json.loads(control['raw']);assert request['execute']=='finish-observation' and request['arguments']=={} and checkpoint['captured_time']<request['created']<=control['time']
assert hashlib.sha256(control['raw'].encode()).hexdigest()==control['sha256'] and control['response']['return']['finish_requested'] is True
qmp=[json.loads(x) for x in (base/'recovery-run/qmp-transcript.jsonl').read_bytes().split(b'\n') if x]
quit_rows=[x for x in qmp if json.loads(x['raw']).get('execute')=='quit'];assert len(quit_rows)==1
quit_message=json.loads(quit_rows[0]['raw']);assert report['quit_response']=={'return':{},'id':quit_message['id']}
assert any(json.loads(x['raw'])==report['quit_response'] for x in qmp)
assert any(json.loads(x['raw']).get('data',{}).get('reason')=='host-qmp-quit' for x in qmp)
frozen=json.loads((base/'freeze-record.json').read_bytes());retention=json.loads((base/'recovery-run/stopped-disk-hashes.json').read_bytes());assert len(frozen['files'])==len(retention)==7
for name,entry in frozen['files'].items():
 st=Path(entry['path']).stat();assert {k:getattr(st,k) for k in entry['after']}==entry['after']
 assert st.st_mode&0o777==0o444 and retention[name]['sha256']==entry['sha256']
assert all(not Path('/proc/'+str(pid)).exists() for pid in [1132078,1146660,1154792])
paths=[result_path,source,base/'content-check.json',base/'freeze-record.json',base/'launch.json',base/'runner-process.json',base/'finish.json',base/'finish.stdout',base/'launchd.plist',base/'recovery-run/serial.log',base/'recovery-run/report.json',base/'recovery-run/control-transcript.jsonl',base/'recovery-run/qmp-transcript.jsonl',base/'recovery-run/stopped-disk-hashes.json',base/'recovery-run/stopped-disk-hashes-verification.json']
summary={'scope':'Actual corrected inspector recovery; observation only, not a runtime base or IPA execution. No full disk hashes repeated in this metadata audit. Full serial/export stay external.',
 'artifacts':{str(p):{'sha256':sha(p),'bytes':p.stat().st_size} for p in paths},'launchd':content['launchd'],'launchd_jobs':content['launchd_jobs'],'dyld':content['dyld'],
 'nonexport_markers':[r for r in content['records'] if 'text' in r],
 'data_record_count':sum('text' not in r for r in content['records']),
 'checkpoint_time':checkpoint['captured_time'],'finish_request_time':request['created'],'finish_response_time':control['time'],'qmp_shutdown_records':qmp[-3:],
 'report_result':{k:report.get(k) for k in ['attempt_completed','error','exit_code','quit_response']},
 'all_seven_frozen_metadata_matches':True,'all_processes_absent':True,'backing_depth':4,'runtime_base_eligible':False,'ipa_runtime_ready':False}
print(json.dumps(summary,indent=2))
