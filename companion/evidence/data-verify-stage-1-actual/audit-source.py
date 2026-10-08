import pathlib,json,hashlib,sys,shutil,stat
sys.path.insert(0,'/tmp/inferno-data-verify-stage/companion');import data_verify
p=pathlib.Path('/home/brandonin/.local/share/inferno/app-import/data-verify-stage-1')
o=pathlib.Path('/tmp/inferno-initial-volumes-doc-link/companion/evidence/data-verify-stage-1-actual')
def digest(f):return hashlib.sha256(f.read_bytes()).hexdigest()
def pin(f):return {'path':str(f),'sha256':digest(f),'bytes':f.stat().st_size}
def read(n):return json.loads((p/n).read_text())
r=read('recovery-run/report.json');result=read('data-verified.json');f=read('freeze-record.json');c=read('content-check.json');raw=(p/'recovery-run/serial.log').read_bytes();v=data_verify.verify_content(raw)
assert r['attempt_completed'] and not r.get('error') and r['exit_code']==0
assert hashlib.sha256(raw[:c['serial_bytes']]).hexdigest()==c['serial_sha256']
assert not (p/'INCOMPLETE.json').exists() and not (p/'failure.json').exists()
for path,h in {**result['source_sha256'],**result['stopped_evidence_sha256']}.items():assert digest(pathlib.Path(path))==h
identities={}
for name,x in f['files'].items():
 s=(p/'recovery-run/disks'/name).stat();i={k:getattr(s,k) for k in x['after']};assert i==x['after'];assert stat.S_IMODE(s.st_mode)==0o444 and s.st_nlink==1;identities[name]=i
pids=[163843,164030,r['pid']];assert all(not pathlib.Path('/proc',str(i)).exists() for i in pids)
o.mkdir()
for n in ['data-verified.json','content-check.json','freeze-record.json','finish.json','finish.stdout','runner-process.json','recovery-run/report.json','recovery-run/control-transcript.jsonl','recovery-run/qmp-transcript.jsonl','recovery-run/stopped-disk-hashes.json']:
 shutil.copyfile(p/n,o/n.replace('/','--'))
x={'status':'actual read-only Data tree verification passed','ipa_runtime_ready':False,'result':pin(p/'data-verified.json'),'serial':pin(p/'recovery-run/serial.log'),'raw_content_replayed':v,'pid_absent':{str(i):True for i in pids},'current_frozen_identity_matches':identities,'limits':['Compares bytes/mode/uid/gid/symlink targets/missing and extra entries; not xattrs/ACLs/timestamps/compression encoding.','No keybag/cache/setup/app readiness.','No duplicate disk hashing during packaging; original coordinator retention and backing verification retained.','Readable /proc descriptor inspection is not a host-wide exclusive lock.','Four layers including raw; flatten verified tuple before further child stages.']}
(o/'audit.json').write_text(json.dumps(x,indent=2)+'\n');shutil.copyfile(pathlib.Path(str(p)+'-launch.json'),o/'operator-launch.json')
(o/'README.md').write_text('Actual separate read-only Data verification completed: original System var and Data tree equality, clean unmounts, one normal coordinator finish, all seven new-file freezing and retention. Raw content replay, source/metadata hashes and current frozen identities match. IPA readiness remains false and depth4 requires flattening before further stages. No further VM or flatten was launched.\n')
print(json.dumps({'result':pin(p/'data-verified.json'),'tree':v['tree'],'depth':result['backing_depth'],'pids':pids}))
