#!/usr/bin/env python3
import json,hashlib,importlib.util,stat
from pathlib import Path
R=Path('/home/brandonin/.local/share/inferno/app-import/navigation-stage-2');P=R.parent/'navigation-prepare-2';S=Path('/home/brandonin/.local/share/inferno/host-runtimes/ipa-release-host-1/source/companion');pins={}
def read(p):
 b=p.read_bytes();pins[str(p)]=hashlib.sha256(b).hexdigest();return b
def js(p):return json.loads(read(p))
s=js(P/'session.json');v=js(R/'verified-stage.json');r=js(R/'recovery-run/report.json');c=js(R/'content-check.json');f=js(R/'freeze-record.json');ret=js(R/'recovery-run/stopped-disk-hashes.json');rv=js(R/'recovery-run/stopped-disk-hashes-verification.json');proc=js(R/'runner-process.json')
assert v['eligible'] and v['backing_depth']==3 and v['session_sha256']==pins[str(P/'session.json')]=='a4b188240030f60954ef0682f3257e13028df4c8f5f6ee4069f9b3c6043ca46b'
assert not (R/'INCOMPLETE.json').exists() and not (R/'failure.json').exists()
for key,path in [('report_sha256',R/'recovery-run/report.json'),('retention_sha256',R/'recovery-run/stopped-disk-hashes.json'),('content_checkpoint_sha256',R/'content-check.json')]:assert v[key]==pins[str(path)]
for name,h in s['sources'].items():assert hashlib.sha256(read(S/name)).hexdigest()==h
assert r['runner_sha256']==s['sources']['boot.py'] and r['control_source_sha256']==s['sources']['qmp_control.py']
assert r['profile_sha256']==s['recovery_profile']['sha256'];assert r['attempt_completed'] and r['exit_code']==0 and not r.get('error')
assert rv['failed_attempt_opt_in'] is False and rv['attempt_completed'] and rv['report_sha256']==v['report_sha256']
for pid in [int(proc['proc_stat'].split(') ',1)[1].split()[1]),proc['pid'],r['pid']]:assert not Path('/proc',str(pid)).exists()
raw=read(R/'recovery-run/serial.log');assert hashlib.sha256(raw[:c['serial_bytes']]).hexdigest()==c['serial_sha256']
m=js(Path(s['import_manifest']['path']));spec=importlib.util.spec_from_file_location('raw_stage',S/'import_stage.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
parsed=mod.verify_content(raw,m,{'exec_wrapper':Path(s['exec_wrapper']['path']).stat().st_size,'system_launcher':Path(s['launcher']['path']).stat().st_size,'launchd_cache':Path(s['cache']['path']).stat().st_size})
assert parsed==v['content'];assert parsed['expected_file_bytes']==74518 and parsed['expected_entries']==3
ctl=[json.loads(x) for x in read(R/'recovery-run/control-transcript.jsonl').splitlines()];assert len(ctl)==1;request=json.loads(ctl[0]['raw']);assert request['execute']=='finish-observation' and c['captured_time']<request['created']<=ctl[0]['time']
q=[json.loads(x) for x in read(R/'recovery-run/qmp-transcript.jsonl').splitlines()];quitrows=[x for x in q if x['direction']=='send' and json.loads(x['raw']).get('execute')=='quit'];assert len(quitrows)==1;quitrow=quitrows[0];qid=json.loads(quitrow['raw'])['id'];acks=[x for x in q if x['direction']=='receive' and json.loads(x['raw']).get('id')==qid];assert len(acks)==1 and json.loads(acks[0]['raw'])['return']=={} and ctl[0]['time']<quitrow['time']<acks[0]['time']
assert len(ret)==len(f['files'])==7
for name,item in f['files'].items():
 p=Path(item['path']);st=p.lstat();assert p.parent==R/'recovery-run/disks' and not p.is_symlink() and stat.S_ISREG(st.st_mode) and stat.S_IMODE(st.st_mode)==0o444 and st.st_nlink==1
 for k,val in item['after'].items():assert getattr(st,k)==val
 assert ret[name]['sha256']==item['sha256'] and ret[name]['bytes']==st.st_size
for layer in ret['root.qcow2']['backing_chain']:
 st=Path(layer['path']).lstat()
 for k,attr in [('device','st_dev'),('inode','st_ino'),('bytes','st_size'),('mtime_ns','st_mtime_ns'),('ctime_ns','st_ctime_ns')]:assert layer[k]==getattr(st,attr)
 assert stat.S_IMODE(st.st_mode)==0o444
assert len(ret['root.qcow2']['backing_chain'])==2
keep=js(R/'recovery-run/disks/KEEP-OVERLAY-BACKING.json');assert keep['backing']['sha256']==ret['root.qcow2']['sha256'] and keep['retirement_prohibited_while_dependent_overlays_exist']
a=[str(S/'run'),'boot-import','--stage',str(R/'verified-stage.json'),'--stage-sha256',pins[str(R/'verified-stage.json')],'--session',str(P/'session.json'),'--output',str(R.parent/'navigation-boot-2'),'--seconds','1200']
for p,h in pins.items():assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==h
out={'verdict':'PASS independent actual raw staging and stopped metadata audit','pins':pins,'records':parsed['records'],'checkpoint_captured':c['captured_time'],'sole_finish':ctl[0],'quit':quitrow,'quit_ack':acks[0],'elapsed_seconds':r['elapsed_seconds'],'retention':ret,'reviewed_boot_argv_unexecuted':a,'limits':['No disk payload hashes repeated; current identity/mode and retained producer full-hash relationships checked.','Raw helper records and normal shutdown prove this staging operation; not installed app launch, navigation or reliability.','Serial ABI has no authenticated per-operation nonce; source/session/report/raw ordering provide retained provenance.']}
Path(__file__).with_name('audit.json').write_text(json.dumps(out,indent=2)+'\n');print(out['verdict'])
