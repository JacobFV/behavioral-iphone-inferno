import hashlib,json,os,signal,socket,subprocess,sys,tempfile,time
from pathlib import Path
sys.path.insert(0,'/tmp/inferno-qmp-control/companion')
from boot import QMP,capture_final_frame
from probe_journey import ProbeJourney
out=Path(__file__).parent
binary=Path('/home/brandonin/Documents/behavioral-iphone-inferno/.local-build/build/qemu-system-aarch64')
results=[]
for case in ('incomplete-journey','sigterm','no-display-capture-error'):
 d=out/case;d.mkdir(exist_ok=True)
 with tempfile.TemporaryDirectory(prefix='inferno-final-capture-') as td:
  endpoint=Path(td)/'qmp.sock'
  cmd=[str(binary),'-machine','virt','-accel','tcg','-cpu','cortex-a57','-m','128M','-S','-nodefaults','-display','none','-monitor','none','-serial','none','-qmp',f'unix:{endpoint},server=on,wait=off']
  if case!='no-display-capture-error':cmd+=['-device','VGA,romfile=']
  (d/'command.json').write_text(json.dumps(cmd,indent=2))
  with (d/'stderr.log').open('wb') as err:
   proc=subprocess.Popen(cmd,stdout=subprocess.DEVNULL,stderr=err);conn=socket.socket(socket.AF_UNIX);q=None;report={}
   try:
    deadline=time.monotonic()+10
    while True:
     try:conn.connect(str(endpoint));break
     except (FileNotFoundError,ConnectionRefusedError):
      if proc.poll() is not None or time.monotonic()>deadline:raise RuntimeError('QMP startup')
      time.sleep(.05)
    q=QMP(conn,d);q.receive();q.execute('qmp_capabilities')
    try:
     if case=='sigterm':
      def interrupted(signum,frame):raise KeyboardInterrupt('actual SIGTERM')
      old=signal.signal(signal.SIGTERM,interrupted)
      try:os.kill(os.getpid(),signal.SIGTERM)
      finally:signal.signal(signal.SIGTERM,old)
     else:ProbeJourney(d).finish()
    except (Exception,KeyboardInterrupt) as exc:report['error']={'type':type(exc).__name__,'detail':str(exc)}
    finally:
     original=dict(report['error']);capture_final_frame(q,d,report)
     assert report['error']==original
     report['quit_response']=q.execute('quit');proc.wait(timeout=5);report['exit_code']=proc.returncode
    assert report['exit_code']==0 and 'return' in report['quit_response']
    assert report['framebuffer_captured']==(case!='no-display-capture-error')
    if case=='no-display-capture-error':assert report['final_capture_error']
    (d/'report.json').write_text(json.dumps(report,indent=2));results.append({'case':case,**report})
   finally:
    if q:q.close()
    conn.close()
    if proc.poll() is None:proc.terminate();proc.wait(timeout=5)
summary={'kind':'actual firmware-free QMP cleanup capture; no iOS or app execution claim','binary_sha256':hashlib.sha256(binary.read_bytes()).hexdigest(),'boot_source_sha256':hashlib.sha256(Path('/tmp/inferno-qmp-control/companion/boot.py').read_bytes()).hexdigest(),'results':results}
(out/'result.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary,indent=2))
