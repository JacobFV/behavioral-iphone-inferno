#!/usr/bin/env python3
"""Host-only protocol checks; fake QMP is not emulator execution."""
import importlib.util,json,pathlib,tempfile,time,hashlib,sys
from unittest.mock import patch
root=pathlib.Path(__file__).resolve().parents[3]
sp=importlib.util.spec_from_file_location('control',root/'companion/qmp_control.py');m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m)
class QMP:
 def __init__(self):self.calls=[];self.reject_disable=False;self.fail_enable=None
 def execute(self,name,args):
  self.calls.append((name,dict(args)))
  if (self.reject_disable and not args['enable']) or (args['enable'] and args['name']==self.fail_enable):return {'error':{'desc':'injected explicit rejection'}}
  return {'return':{}}
checks=[]
for seconds in (0,61,True,1.0,'1'):
 try:m.validate({'execute':'trace-display-window','arguments':{'seconds':seconds},'created':time.time()});raise AssertionError('invalid accepted')
 except ValueError:pass
for args in ({'seconds':1,'event':'anything'},{'enable':True},{}):
 try:m.validate({'execute':'trace-display-window','arguments':args,'created':time.time()});raise AssertionError('extra fields accepted')
 except ValueError:pass
checks.append('bounds/types/exact-fields rejected; no arbitrary trace event API')
with tempfile.TemporaryDirectory() as d:
 w=m.DisplayTraceWindow(pathlib.Path(d));q=QMP()
 with patch.object(m.time,'monotonic',return_value=100):w.start(q,1)
 assert len(q.calls)==5
 try:w.start(q,1);raise AssertionError('overlap accepted')
 except ValueError:pass
 with patch.object(m.time,'monotonic',return_value=100.9):w.poll(q)
 assert len(q.calls)==5
 with patch.object(m.time,'monotonic',return_value=101):w.poll(q)
 assert len(q.calls)==10 and not w.pending
 assert [x[1]['enable'] for x in q.calls]==[True]*5+[False]*5
 checks.append('single deadline and no extension; all5 disabled at deadline')
 w.start(q,60);w.stop(q,'runner cleanup');assert not w.pending
 checks.append('early cleanup disables all5 without second QMP owner')
 w.start(q,1);q.reject_disable=True
 try:w.stop(q,'test rejection');raise AssertionError('disable rejection lost')
 except RuntimeError:pass
 assert len(w.pending)==5;q.reject_disable=False;w.stop(q,'cleanup retry');assert not w.pending
 checks.append('failed disables journaled and retained; successful cleanup clears pending')
 q.fail_enable=m.DISPLAY_TRACE_EVENTS[2]
 try:w.start(q,1);raise AssertionError('enable failure ignored')
 except RuntimeError:pass
 assert not w.pending
 checks.append('partial enable explicit failure rolls back prior enabled events')
 records=[json.loads(x) for x in w.journal.read_text().splitlines()]
 assert any(x.get('stage')=='stop-result' and not x['all_disabled'] for x in records)
 output={'scope':'Host fake-QMP protocol only; no firmware/VM build or execution.','checks':checks,'journal':records,'source_sha256':hashlib.sha256((root/'companion/qmp_control.py').read_bytes()).hexdigest()}
 pathlib.Path(__file__).with_name('result.json').write_text(json.dumps(output,indent=2)+'\n')
sys.path.insert(0,str(root/'scripts'));import tracetool
with (root/'hw/display/trace-events').open() as f:events=tracetool.read_events(f,'hw/display/trace-events')
assert set(m.DISPLAY_TRACE_EVENTS).issubset({e.name for e in events})
print('PASS: fixed protocol/deadline/rollback/cleanup checks; upstream trace-event parser accepted definitions')
