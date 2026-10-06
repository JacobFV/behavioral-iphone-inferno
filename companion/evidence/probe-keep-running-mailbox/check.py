#!/usr/bin/env python3
"""Actual empty-QEMU control lifecycle with explicit host-only completion fixtures."""
import argparse,hashlib,importlib.util,json,socket,subprocess,sys,tempfile,time
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--binary',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
sys.path.insert(0,str(a.source/'companion'))
from boot import QMP,probe_should_stop
from qmp_control import ControlMailbox
from probe_journey import ProbeJourney
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
results=[]
with tempfile.TemporaryDirectory(prefix='inferno-keep-running-') as temp:
 endpoint=Path(temp)/'qmp.sock';command=[str(a.binary),'-machine','none','-display','none','-nodefaults','-S','-qmp',f'unix:{endpoint},server=on,wait=off']
 with (a.output/'stderr.log').open('wb') as stderr:
  proc=subprocess.Popen(command,stdout=subprocess.DEVNULL,stderr=stderr);qmp=None
  try:
   deadline=time.monotonic()+10
   while not endpoint.exists():
    if time.monotonic()>deadline or proc.poll() is not None:raise RuntimeError('QMP startup failed')
    time.sleep(.02)
   conn=socket.socket(socket.AF_UNIX);conn.connect(str(endpoint));qmp=QMP(conn,a.output);qmp.receive();qmp.execute('qmp_capabilities')
   journey=ProbeJourney(a.output);box=ControlMailbox(a.output,journey=journey)
   def request(command,args='{}'):
    commands=qmp.counter;before=json.dumps(journey.report,sort_keys=True)
    client=subprocess.Popen([sys.executable,str(a.source/'companion/qmp_control.py'),'--report',str(a.output),command,'--arguments',args],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
    end=time.monotonic()+8
    while client.poll() is None and time.monotonic()<end:box.poll(qmp);time.sleep(.02)
    if client.poll() is None:client.kill();raise RuntimeError('client timed out')
    out,err=client.communicate();assert qmp.counter==commands and json.dumps(journey.report,sort_keys=True)==before
    result={'command':command,'arguments':args,'exit_code':client.returncode,'stdout':out,'stderr':err,'qmp_commands_added':0,'journey_unchanged':True};results.append(result);return result
   assert request('finish-run')['exit_code']==1
   assert not probe_should_stop(journey,box)
   journey.report['completed']=True;journey.report['state']='completed' # host fixture, not guest markers
   assert probe_should_stop(journey,box);results.append({'default_completed_stop':True})
   box.run_control['keep_running']=True;journey.report['completed']=False
   assert request('finish-run')['exit_code']==1 and not box.run_control['finish_requested']
   journey.report['completed']=True
   status=request('probe-status');assert json.loads(status['stdout'])['return']['keep_running']
   assert request('finish-run','{"extra":true}')['exit_code']==1
   start=time.monotonic();iterations=0
   while time.monotonic()-start<.15:
    assert not probe_should_stop(journey,box) and proc.poll() is None;iterations+=1;time.sleep(.02)
   results.append({'completed_opt_in_remained_alive':True,'host_loop_iterations':iterations,'duration_deadline_reached_without_finish':True})
   assert request('finish-run')['exit_code']==0 and probe_should_stop(journey,box)
   qmp.execute('query-status');quit_reply=qmp.execute('quit');exit_code=proc.wait(timeout=5);assert exit_code==0
   files={str(f.relative_to(a.output)):{'sha256':sha(f),'bytes':f.stat().st_size} for f in a.output.rglob('*') if f.is_file()}
   result={'kind':'actual_firmware_free_keep_running_mailbox_lifecycle','ios_boot':False,'guest_markers_injected':False,'host_completion_fixture':True,'binary_sha256':sha(a.binary),'source_sha256':{n:sha(a.source/'companion'/n) for n in ['boot.py','qmp_control.py']},'command':command,'checks':results,'normal_qmp_quit':quit_reply,'exit_code':exit_code,'files':files}
   (a.output/'result.json').write_text(json.dumps(result,indent=2)+'\n')
  finally:
   if proc.poll() is None:proc.terminate();proc.wait(timeout=5)
   if qmp:qmp.close();conn.close()
