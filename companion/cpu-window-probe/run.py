#!/usr/bin/env python3
"""Actual owned baremetal TB/GPR logging check; never an iOS claim."""
import argparse,pathlib,subprocess,socket,time,json,sys,hashlib,tempfile,uuid,re,shutil
ap=argparse.ArgumentParser();ap.add_argument('--binary',type=pathlib.Path,required=True);ap.add_argument('--output',type=pathlib.Path,required=True);a=ap.parse_args();o=a.output.resolve();o.mkdir(exist_ok=False);repo=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(repo));from boot import QMP
from qmp_control import ControlMailbox,write_private,read_private
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
src=pathlib.Path(__file__).with_name('loop.S');commands=[['as','-o',str(o/'loop.o'),str(src)],['ld','-Ttext=0x40200000','-e','_start','-o',str(o/'loop.elf'),str(o/'loop.o')]]
for c in commands:subprocess.run(c,check=True,capture_output=True)
nm=subprocess.check_output(['nm',str(o/'loop.elf')],text=True);syms={s[2]:int(s[0],16) for l in nm.splitlines() if len(s:=l.split())==3};pcs=[syms['probe_entry'],syms['probe_return']];filt=','.join(hex(x)+'+4' for x in pcs)
# Synthetic fixture solely exercises production slide gate; virt does not report an Apple kernel slide.
(o/'stderr.log').write_text('OWNED HARNESS SLIDE FIXTURE, NOT GUEST KERNEL EVIDENCE\ninfo: Kernel Virtual Slide: 0x0000000000000000\n')
r={'scope':'Wholly owned baremetal loop, synthetic filter and explicitly labeled slide fixture; no iOS/kernel capture claim.','binary_sha256':sha(a.binary),'sources':{str(p):sha(p) for p in [src,pathlib.Path(__file__),repo/'qmp_control.py',repo/'boot.py']},'build_commands':commands,'symbols':syms,'filter':filt,'checks':{}}
p=q=box=conn=None
try:
 with tempfile.TemporaryDirectory(prefix='inferno-owned-cpu-') as tmp:
  endpoint=tmp+'/qmp.sock';cmd=[str(a.binary),'-machine','virt','-cpu','cortex-a57','-accel','tcg','-smp','1','-m','128M','-display','none','-monitor','none','-serial','none','-nic','none','-S','-device','loader,file='+str(o/'loop.elf')+',cpu-num=0','-d','guest_errors','-D',str(o/'guest-errors.log'),'-dfilter',filt,'-qmp','unix:'+endpoint+',server=on,wait=off'];r['command']=cmd
  with (o/'emulator-stderr.log').open('wb') as err:
   p=subprocess.Popen(cmd,stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=err)
   deadline=time.monotonic()+10
   while not pathlib.Path(endpoint).exists():
    assert p.poll() is None and time.monotonic()<deadline;time.sleep(.02)
   conn=socket.socket(socket.AF_UNIX);conn.connect(endpoint);q=QMP(conn,o);r['greeting']=q.receive();q.execute('qmp_capabilities');box=ControlMailbox(o,swapwait_cpu=True);q.execute('cont');time.sleep(.15)
   def log():return (o/'guest-errors.log').read_text()
   before=log();assert ' PC=' not in before and 'pl011_read: Bad offset 0x50' in before;r['checks']['default_cpu_off_guest_errors_on']=True
   def request(seconds):
    token=uuid.uuid4().hex;write_private(box.path/('request-'+token+'.json'),{'execute':'swapwait-cpu-window','arguments':{'seconds':seconds},'created':time.time()});box.poll(q);v=json.loads(read_private(box.path/('reply-'+token+'.json')));assert 'return' in v,v;return v
   r['request']=request(1)
   while box.swapwait_cpu.pending:box.poll(q);time.sleep(.01)
   text=log();blocks=re.findall(r' PC=([0-9a-f]+)(.*?PSTATE=[^\n]*\n)',text,re.S);assert blocks
   found=set()
   for pc,block in blocks:
    pc=int(pc,16);assert pc in pcs;regs={k:int(v,16) for k,v in re.findall(r'(X\d\d)=([0-9a-f]+)',block)};assert len(regs)==31
    if pc==pcs[0]:assert regs['X01']==0x1234 and regs['X02']==0x56
    if pc==pcs[1]:assert regs['X00']==0x789
    found.add(pc)
   assert found==set(pcs);r['checks']['known_entry_and_return_exact_PCs']=True;r['checks']['only_filtered_PCs']=True;r['block_count']=len(blocks)
   time.sleep(.1);start=len(log());time.sleep(.15);tail=log()[start:];assert ' PC=' not in tail and 'pl011_read: Bad offset 0x50' in tail;r['checks']['deadline_restore_cpu_off_guest_errors_on']=True
   r['early_request']=request(3);time.sleep(.05);box.close(q);time.sleep(.1);start=len(log());time.sleep(.15);tail=log()[start:];assert ' PC=' not in tail and 'pl011_read: Bad offset 0x50' in tail;r['checks']['early_cleanup_restore']=True
   class UncertainEnable:
    def execute(self, name, args=None):
     reply=q.execute(name,args)
     if args=={'command-line':'log cpu,nochain,guest_errors'}:raise TimeoutError('owned harness simulates lost response after actual enable')
     return reply
   try:box.swapwait_cpu.start(UncertainEnable(),1)
   except TimeoutError:pass
   else:raise AssertionError('uncertain enable did not raise')
   assert not box.swapwait_cpu.pending
   time.sleep(.1);start=len(log());time.sleep(.15);tail=log()[start:];assert ' PC=' not in tail and 'pl011_read: Bad offset 0x50' in tail;r['checks']['uncertain_actual_enable_restored']=True
   r['quit']=q.execute('quit');p.wait(timeout=5);r['exit_code']=p.returncode;assert p.returncode==0;r['passed']=True
except BaseException as exc:r['error']={'type':type(exc).__name__,'detail':str(exc)};raise
finally:
 if p and p.poll() is None:
  try:
   if box:box.close(q)
   if q:q.execute('quit')
   p.wait(timeout=5)
  except BaseException:p.terminate();p.wait(timeout=5)
 if q:q.close()
 if conn:conn.close()
 r['final_exit_code']=p.returncode if p else None;(o/'report.json').write_text(json.dumps(r,indent=2)+'\n')
print(json.dumps({'passed':r.get('passed'),'output':str(o)}))
