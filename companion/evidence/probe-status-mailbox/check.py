#!/usr/bin/env python3
"""Actual empty-QEMU mailbox plumbing; simulated host state is not iOS evidence."""
import argparse, hashlib, importlib.util, json, socket, subprocess, sys, tempfile, time
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--runtime',type=Path,required=True);p.add_argument('--binary',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
a.output.mkdir(parents=True,exist_ok=False)
sys.path.insert(0,str(a.runtime/'companion'))
from boot import QMP
from probe_journey import ProbeJourney
spec=importlib.util.spec_from_file_location('candidate_control',a.source/'companion/qmp_control.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
with tempfile.TemporaryDirectory(prefix='inferno-probe-status-') as temp:
 endpoint=Path(temp)/'qmp.sock'
 command=[str(a.binary),'-machine','none','-display','none','-nodefaults','-S','-qmp',f'unix:{endpoint},server=on,wait=off']
 with (a.output/'stderr.log').open('wb') as err:
  proc=subprocess.Popen(command,stdout=subprocess.DEVNULL,stderr=err)
  qmp=None
  try:
   deadline=time.monotonic()+10
   while not endpoint.exists():
    if time.monotonic()>deadline or proc.poll() is not None:raise RuntimeError('QMP startup failed')
    time.sleep(.02)
   conn=socket.socket(socket.AF_UNIX);conn.connect(str(endpoint));qmp=QMP(conn,a.output);qmp.receive();qmp.execute('qmp_capabilities')
   journey=ProbeJourney(a.output);box=module.ControlMailbox(a.output,journey);results=[]
   def request(label,arguments):
    before=json.dumps(journey.report,sort_keys=True);commands=qmp.counter
    client=subprocess.Popen([sys.executable,str(a.source/'companion/qmp_control.py'),'--report',str(a.output),'probe-status','--arguments',json.dumps(arguments)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
    end=time.monotonic()+8
    while client.poll() is None and time.monotonic()<end:box.poll(qmp);time.sleep(.02)
    if client.poll() is None:client.kill();raise RuntimeError('client deadline')
    stdout,stderr=client.communicate();assert qmp.counter==commands and json.dumps(journey.report,sort_keys=True)==before
    result={'label':label,'exit_code':client.returncode,'stdout':stdout,'stderr':stderr,'qmp_commands_added':qmp.counter-commands,'journey_unchanged':True};results.append(result);return result
   first=request('initial_live_state',{});assert 'waiting-for-app' in first['stdout']
   # Feed an explicitly synthetic host fixture into the real observation object.
   (a.output/'serial.log').write_text('INFERNO_UIKIT_PROBE_V1 event=appeared count=0\n')
   journey.poll(qmp,time.monotonic())
   second=request('host_fixture_transition_live_state',{});assert 'waiting-for-operator-before-capture' in second['stdout']
   bad=request('nonempty_arguments_rejected',{'unused':True});assert bad['exit_code']!=0
   box.journey=None
   missing=request('disabled_journey_rejected',{});assert 'did not enable' in missing['stdout']
   box.journey=journey;journey.report['oversized_fixture']='x'*4096
   oversized=request('oversized_response_rejected',{});assert 'exceeded 4096' in oversized['stdout'];del journey.report['oversized_fixture']
   qmp.execute('query-status');qmp.execute('quit');exit_code=proc.wait(timeout=5);assert exit_code==0
   files={str(f.relative_to(a.output)):{'sha256':sha(f),'bytes':f.stat().st_size} for f in a.output.rglob('*') if f.is_file()}
   result={'kind':'actual_firmware_free_probe_status_mailbox_check','ios_boot':False,'guest_app_execution':False,'synthetic_host_marker':True,'source_module_sha256':sha(a.source/'companion/qmp_control.py'),'runtime_probe_journey_sha256':sha(a.runtime/'companion/probe_journey.py'),'binary_sha256':sha(a.binary),'command':command,'checks':results,'exit_code':exit_code,'files':files}
   (a.output/'result.json').write_text(json.dumps(result,indent=2)+'\n')
  finally:
   if proc.poll() is None:proc.terminate();proc.wait(timeout=5)
   if qmp:qmp.close();conn.close()
