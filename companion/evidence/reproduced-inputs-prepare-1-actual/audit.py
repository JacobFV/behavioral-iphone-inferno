# SPDX-License-Identifier: AGPL-3.0-or-later
"""Read-only verification of retained host preparation; no VM or disk mutation."""
import hashlib,json,pathlib,subprocess,sys
p=pathlib.Path(sys.argv[1]); out=pathlib.Path(sys.argv[2])
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
s=json.loads((p/'session.json').read_text()); source=pathlib.Path(s['recovery_command'][1]).parent
assert s['status']=='host-prepared-not-staged'
assert not (p/'INCOMPLETE.json').exists() and not (p/'failure.json').exists()
assert subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD']).decode().strip()==s['source_revision']
assert not subprocess.check_output(['git','-C',str(source),'status','--porcelain=v1','--untracked-files=all'])
for name,h in s['sources'].items(): assert sha(source/name)==h
m=json.loads(pathlib.Path(s['import_manifest']['path']).read_text()); runtime=s['runtime_record']
pairs=[(pathlib.Path(runtime['inputs']['probe']['path']),p/'recovery/readback-probe'),(pathlib.Path(s['cache']['path']),p/'recovery/readback-launchd-cache'),(pathlib.Path(s['launcher']['path']),p/'recovery/readback-system-launcher'),(pathlib.Path(s['exec_wrapper']['path']),p/'recovery/readback-exec-wrapper'),(p/'recovery/imported-app.plan',p/'recovery/readback-imported-app.plan')]
for i,row in enumerate(m['files']):pairs.append((p/'import'/m['bundle']['relative_path']/row['path'],p/('recovery/readback-imported-%04d'%i)))
checks=[]
for a,b in pairs:
 assert a.read_bytes()==b.read_bytes();checks.append({'source':str(a),'readback':str(b),'bytes':b.stat().st_size,'sha256':sha(b)})
for r in s['readbacks']:assert sha(pathlib.Path(r['path']))==r['sha256']
for c in s['commands']:assert c['exit_code']==0 and sha(pathlib.Path(c['log']['path']))==c['log']['sha256']
result={'session_path':str(p/'session.json'),'session_sha256':sha(p/'session.json'),'status':s['status'],'source':str(source),'source_revision':s['source_revision'],'source_pins_verified':len(s['sources']),'commands':s['commands'],'readback_comparisons':checks,'ramdisk_sha256':sha(pathlib.Path(s['recovery_ramdisk']['path'])),'limits':['Host preparation only; no recovery or installed VM executed.','Runtime validator ran normally inside preparation; this audit does not repeat full backing-disk hashes.','Existing sessions/source trees untouched; new session pins persistent source.']}
with out.open('x') as f:json.dump(result,f,indent=2);f.write('\n')
