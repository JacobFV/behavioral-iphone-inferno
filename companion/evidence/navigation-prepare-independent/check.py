#!/usr/bin/env python3
"""Audit actual host preparation only; no disk ancestry hashes or guest actions."""
import json,hashlib,plistlib,importlib.util
from pathlib import Path
P=Path('/home/brandonin/.local/share/inferno/app-import/navigation-prepare-1');S=Path('/home/brandonin/.local/share/inferno/host-runtimes/ipa-release-host-1/source/companion');pins={}
def sha(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def read(p):
 b=p.read_bytes();pins[str(p)]={'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()};return b
def js(p):return json.loads(read(p))
def pin(x):
 p=Path(x['path']);assert sha(p)==x['sha256'];return p
session=js(P/'session.json');assert pins[str(P/'session.json')]['sha256']=='54551a25f5b0865b1169bc7eba15afa99b694c7e614edbfc54aa6da4a224c27d'
assert session['status']=='host-prepared-not-staged' and session['schema']=='inferno.prepared-import-session.v1';assert not (P/'INCOMPLETE.json').exists() and not (P/'failure.json').exists() and not Path('/proc/1315347').exists()
for n,h in session['sources'].items():assert hashlib.sha256(read(S/n)).hexdigest()==h
runtime=js(pin(session['runtime']));assert runtime==session['runtime_record'] and session['runtime']['sha256']=='52a1297061096d0d0a8936127e58e3e69f5629415514580a057971e5aca5ee76'
for name in ['import_manifest','launcher_build','launcher','exec_wrapper','launchd_job','cache','recovery_profile','preparation']:pin(session[name])
# New ramdisk is a host build artifact, not an ancestor disk. Its recorded hash
# is checked once here to bind the retained extraction bytes to this artifact.
ramdisk=pin(session['recovery_ramdisk'])
spec=importlib.util.spec_from_file_location('nav_import',S/'app-import.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);manifest=m.validate_manifest(Path(session['import_manifest']['path']))
assert manifest['bundle']==session['bundle'] and manifest['tree_sha256']==session['tree_sha256'] and manifest['bundle']['identifier']=='org.inferno.companion.navigationdemo'
for c in session['commands']:
 assert c['exit_code']==0 and c['started']<=c['finished'];assert hashlib.sha256(read(Path(c['log']['path']))).hexdigest()==c['log']['sha256']
assert [c['label'] for c in session['commands']]==['import','launcher','cache','prepare']
assert all(a['finished']<=b['started'] for a,b in zip(session['commands'],session['commands'][1:]))
original=plistlib.loads(read(Path(runtime['inputs']['cache']['path'])));merged=plistlib.loads(read(Path(session['cache']['path'])));job=plistlib.loads(read(Path(session['launchd_job']['path'])));keys=[k for k,v in original['LaunchDaemons'].items() if v.get('Label')=='org.inferno.app-probe'];assert len(keys)==1
expected={**original,'LaunchDaemons':{**original['LaunchDaemons'],keys[0]:job}};assert merged==expected
cache_command=session['commands'][2]['argv'];assert '--replace-owned-job' in cache_command and '--job' not in cache_command and '--disable-unsupported-services' not in cache_command
l=js(Path(session['launcher_build']['path']));assert l['manifest_sha256']==session['import_manifest']['sha256'] and l['target']==manifest['bundle']
for n,h in l['outputs'].items():assert sha(P/'launcher'/n)==h
for row in session['readbacks']:pin(row)
for source,dest in [(Path(runtime['inputs']['probe']['path']),'readback-probe'),(Path(session['cache']['path']),'readback-launchd-cache'),(Path(session['launcher']['path']),'readback-system-launcher'),(Path(session['exec_wrapper']['path']),'readback-exec-wrapper'),(P/'recovery/imported-app.plan','readback-imported-app.plan')]:assert sha(source)==sha(P/'recovery'/dest)
# Importer's fixed plan ordering is sorted manifest entries for this flat3file app.
assert not manifest['directories']
for i,item in enumerate(sorted(manifest['files'],key=lambda x:x['path'])):
 b=read(P/'recovery'/('readback-imported-%04d'%i));assert len(b)==item['bytes'] and hashlib.sha256(b).hexdigest()==item['sha256']
prepared=js(P/'recovery/preparation.json');assert prepared['output_ramdisk_sha256']==session['recovery_ramdisk']['sha256'] and prepared['disk_helper_sha256']==runtime['inputs']['disk_helper']['sha256']
profile=js(P/'recovery/profile.json');assert profile['provenance']['helper_flags']=={'disk_helper_roles':False,'disk_helper_existing':True,'disk_helper_gigalocker':False,'disk_helper_data':False,'disk_helper_verify_data':False,'disk_helper_keybag':False,'export_reports':False}
flags=session['commands'][3]['argv'];assert '--imported-app-manifest' in flags and '--allow-identical-fixture-tree-sha256' not in flags and '--system-app-dir' not in flags
assert len(session['readbacks'])==8
for p,x in pins.items():assert sha(Path(p))==x['sha256']
result={'verdict':'PASS actual host preparation and retained readback audit; not guest staging','session':session['runtime']|{'session_path':str(P/'session.json'),'session_sha256':sha(P/'session.json')},'inputs':pins,'bundle':session['bundle'],'tree_sha256':session['tree_sha256'],'readbacks':session['readbacks'],'expected_guest_markers_not_yet_observed':session['expected_guest_markers'],'recovery_command_unexecuted':session['recovery_command'],'actual_commands':session['commands'],'new_ramdisk_hash_checked':session['recovery_ramdisk'],'cache_scope':'Entire decoded tree matches original with only exact existing org.inferno.app-probe replacement; existing cache lineage is retained provenance, not a fresh original guest export.','limits':['No ancestor image payloads rehashed; referenced base verification is producer evidence, not a new independent full-chain audit.','Eight retained HFS readbacks match exact owned/provided source bytes; original HFS commands/logs and final ramdisk digest retained.','No guest copies, utility unmounts, normal guest shutdown, frozen new disks, launch or interaction claimed.']}
Path(__file__).with_name('audit.json').write_text(json.dumps(result,indent=2)+'\n');print('PASS independent NavigationDemo host preparation')
