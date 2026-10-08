#!/usr/bin/env python3
"""Host-only parser checks using explicitly synthetic register substitutions."""
import importlib.util,json,pathlib,re
root=pathlib.Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('equality',root/'pending-equality-result.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
raw=(root/'evidence/swapwait-owned-cpu-validation/attempt-6/guest-errors.log').read_bytes()
old=m.parser.parse(raw,'owned-attempt-6');assert old['complete_count']==old['snapshot_count']==922
base=old['blocks'][0]['raw_text'].encode()
def block(role,values):
 fields={'PC':m.PRODUCTION[role],**values}
 return re.sub(rb'(PC|X\d\d)=([0-9a-f]{16})',lambda x:x[1]+b'='+f'{fields.get(x[1].decode(),int(x[2],16)):016x}'.encode(),base)
roles=list(m.PRODUCTION)
valid=[block(roles[0],{'X08':0}),block(roles[1],{'X08':253,'X09':253}),block(roles[2],{'X08':0}),block(roles[3],{'X08':1}),block(roles[4],{'X00':0xe00002d5})]
r=m.parse(b''.join(valid));assert r['complete_count']==5 and not r['semantic_violations']
for role,values in [(roles[0],{'X08':3}),(roles[1],{'X08':1,'X09':2}),(roles[2],{'X08':1}),(roles[3],{'X08':0})]:assert m.parse(block(role,values))['semantic_violations']
assert not m.parse(valid[0][:-2])['blocks'][0]['complete']
assert not m.parse(valid[0].replace(b'\n',b'\r',1))['blocks'][0]['complete']
assert m.parse(base)['unknown_pc_count']==1
print(json.dumps({'scope':'Host-only actual baseline replay and synthetic predicate tests, no VM','baseline_snapshots':922,'valid_roles':r['role_counts'],'negative_cases':7,'passed':True},indent=2))
