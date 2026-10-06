#!/usr/bin/env python3
"""Firmware-free QEMU monitor socket plumbing, not a guest OPEN or HID test."""
import argparse,hashlib,json,socket,subprocess,sys,tempfile,time
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--binary',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
sys.path.insert(0,str(a.source/'companion'))
from boot import QMP
from qmp_control import ControlMailbox,SerialGestureTransport
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
with tempfile.TemporaryDirectory(prefix='inferno-owned-open-') as tmp:
 endpoint=Path(tmp)/'qmp.sock';serial=Path(tmp)/'serial.sock'
 command=[str(a.binary),'-machine','none','-display','none','-nodefaults','-S','-qmp',f'unix:{endpoint},server=on,wait=off','-chardev',f'socket,id=probe,path={serial},server=on,wait=off,logfile={a.output}/serial.log','-mon','chardev=probe,mode=readline']
 with (a.output/'stderr.log').open('wb') as err:
  proc=subprocess.Popen(command,stdout=subprocess.DEVNULL,stderr=err);qmp=transport=None
  try:
   deadline=time.monotonic()+10
   while not endpoint.exists() or not serial.exists():
    if proc.poll() is not None or time.monotonic()>deadline:raise RuntimeError('startup failure')
    time.sleep(.02)
   conn=socket.socket(socket.AF_UNIX);conn.connect(str(endpoint));qmp=QMP(conn,a.output);qmp.receive();qmp.execute('qmp_capabilities')
   transport=SerialGestureTransport(serial,a.output);transport.connect();box=ControlMailbox(a.output);box.serial_transport=transport;results=[]
   boot='12345678-1234-1234-ABCD-123456789ABC'
   def request(name,args,success):
    before=qmp.counter;client=subprocess.Popen([sys.executable,str(a.source/'companion/qmp_control.py'),'--report',str(a.output),name,'--arguments',json.dumps(args)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True);end=time.monotonic()+8
    while client.poll() is None and time.monotonic()<end:box.poll(qmp);time.sleep(.02)
    if client.poll() is None:client.kill();raise RuntimeError('client timeout')
    out,stderr=client.communicate();assert (client.returncode==0)==success and qmp.counter==before
    results.append({'command':name,'arguments':args,'exit_code':client.returncode,'stdout':out,'stderr':stderr,'qmp_commands_added':0})
   first='1'*32;second='2'*32
   request('guest-open-app',{'request_id':first,'boot_uuid':boot},True)
   request('guest-hid-gesture',{'request_id':first,'kind':'tap','x':1,'y':1,'duration_ms':1},False)
   request('guest-hid-gesture',{'request_id':second,'kind':'tap','x':1,'y':1,'duration_ms':1},True)
   request('guest-open-app',{'request_id':second,'boot_uuid':boot},False)
   request('guest-open-app',{'request_id':'3'*32,'boot_uuid':boot,'path':'/bin/anything'},False)
   request('guest-open-app',{'request_id':'3'*32,'boot_uuid':boot+'\n'},False)
   for n in range(3,10):request('guest-open-app',{'request_id':f'{n:032x}','boot_uuid':boot},True)
   request('guest-open-app',{'request_id':'a'*32,'boot_uuid':boot},False)
   time.sleep(.1);assert transport.open_attempts==8
   raw=(a.output/'serial.log').read_bytes();assert raw.count(b"unknown command: 'INFERNO_OPEN_V1'") == 8
   requests=[json.loads(line) for line in (a.output/'serial-input-transcript.jsonl').read_text().splitlines() if json.loads(line).get('stage')=='before-send'];assert len(requests)==9
   assert requests[0]['raw']==f'INFERNO_OPEN_V1 {first} {boot}\n'
   quit_reply=qmp.execute('quit');assert proc.wait(timeout=5)==0;transport.close();assert not transport.thread.is_alive()
   result={'kind':'actual_firmware_free_owned_open_mailbox_plumbing','ios_boot':False,'guest_open_executed':False,'host_fixture_uuid_only':True,'command':command,'binary_sha256':sha(a.binary),'module_sha256':sha(a.source/'companion/qmp_control.py'),'checks':results,'actual_monitor_unknown_open_commands':8,'actual_serial_attempts':9,'normal_quit':quit_reply,'exit_code':0,'drain_thread_stopped':True,'files':{str(f.relative_to(a.output)):{'sha256':sha(f),'bytes':f.stat().st_size} for f in a.output.rglob('*') if f.is_file()}}
   (a.output/'result.json').write_text(json.dumps(result,indent=2)+'\n')
  finally:
   if proc.poll() is None:proc.terminate();proc.wait(timeout=5)
   if transport:transport.close()
   if qmp:qmp.close();conn.close()
