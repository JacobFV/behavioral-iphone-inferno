#!/usr/bin/env python3
"""Host-only parser checks; synthesized blocks are not guest observations."""
import importlib.util,json,pathlib
root=pathlib.Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('pending',root/'pending-branch-result.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
raw=(root/'evidence/swapwait-owned-cpu-validation/attempt-6/guest-errors.log').read_bytes()
old=m.parser.parse(raw,'owned-attempt-6')
assert old['complete_count']==old['snapshot_count'] and not old['unknown_pc_count']
base=old['blocks'][0]['raw_text'].encode()
def block(role,values):
 import re
 fields={'PC':m.PRODUCTION[role],**values}
 return re.sub(rb'(PC|X\d\d)=([0-9a-f]{16})',lambda x:x[1]+b'='+f'{fields.get(x[1].decode(),int(x[2],16)):016x}'.encode(),base)
a=block('null-active',{'X00':293,'X01':292,'X11':0,'X10':999})
b=block('active-join',{'X00':293,'X01':292,'X11':0x4000,'X10':293})
c=block('queued-match',{'X08':0x5000,'X09':293,'X11':293})
r=m.parse(a+b+c)
assert r['complete_count']==3 and not r['semantic_violations']
assert 'active_token_third_read' not in r['blocks'][0]['branch_observation']
assert m.parse(block('null-active',{'X11':1}))['semantic_violations']
assert m.parse(block('queued-match',{'X08':0x5000,'X09':1,'X11':2}))['semantic_violations']
assert m.parse(block('queued-match',{'X08':0,'X09':1,'X11':1}))['semantic_violations']
assert not m.parse(a[:-2])['blocks'][0]['complete']
assert not m.parse(a.replace(b'\n',b'\r',1))['blocks'][0]['complete']
assert m.parse(base)['unknown_pc_count']==1
print(json.dumps({'scope':'host-only replay and explicitly synthetic branch blocks','baseline_actual_snapshots':old['snapshot_count'],'synthetic_three_roles':r['role_counts'],'negative_checks':['null-register','queue-comparison','null-queue-pointer','truncated-EOF','bare-CR','unknown-PC'],'passed':True},indent=2))
