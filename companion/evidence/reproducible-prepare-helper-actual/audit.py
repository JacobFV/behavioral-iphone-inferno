# SPDX-License-Identifier: AGPL-3.0-or-later
"""Read-only actual artifact/schema checks; not full runtime or guest validation."""
import hashlib,json,pathlib,plistlib,sys
out=pathlib.Path(sys.argv[1]);old=pathlib.Path(sys.argv[2]);source=pathlib.Path(sys.argv[3])
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
b=json.loads((out/'build.json').read_text());h=json.loads((old/'build.json').read_text())
assert not (out/'INCOMPLETE.json').exists() and not (out/'failure.json').exists()
for name in ('prepare-root.c','imported-app.c','libSystem.tbd','entitlements.plist'):
 values=[v for p,v in b['sources'].items() if pathlib.Path(p).name==name]
 assert values==[sha(source/name)]
assert b['outputs']['inferno-prepare-root']['sha256']==sha(out/'inferno-prepare-root')
assert b['outputs']['inferno-prepare-root']['bytes']==(out/'inferno-prepare-root').stat().st_size
assert (out/'inferno-prepare-root').read_bytes()==(old/'inferno-prepare-root').read_bytes()
assert b['outputs']['inferno-prepare-root']==h['outputs']['inferno-prepare-root']
assert plistlib.loads((out/'helper-entitlements.plist').read_bytes())==plistlib.loads((source/'entitlements.plist').read_bytes())
for r in b['command_records']:
 assert r['exit_code']==0
 for k in ('stdout','stderr'):assert sha(pathlib.Path(r[k]['path']))==r[k]['sha256']
for p,v in b['producer_sources'].items():assert sha(pathlib.Path(p))==v
print(json.dumps({'scope':'Actual helper bytes, entitlement readback and exact helper gates from prepare-import.validate_runtime; no full runtime rehash/guest execution','build_sha256':sha(out/'build.json'),'historical_build_sha256':sha(old/'build.json'),'helper':b['outputs']['inferno-prepare-root'],'byte_identical_to_helper60':True,'entitlement_dictionary_matches':True,'four_consumer_source_pins_match':True,'all_commands_exit_zero':True,'producer_sources':b['producer_sources']},indent=2))
