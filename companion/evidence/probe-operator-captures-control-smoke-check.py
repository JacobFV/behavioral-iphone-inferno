import hashlib,json,socket,subprocess,sys,tempfile,time,uuid
from pathlib import Path
sys.path.insert(0,'/tmp/inferno-qmp-control/companion')
from boot import QMP
from probe_journey import ProbeJourney
from qmp_control import ControlMailbox,write_private
out=Path(__file__).parent
binary=Path('/home/brandonin/Documents/behavioral-iphone-inferno/.local-build/build/qemu-system-aarch64')
with tempfile.TemporaryDirectory(prefix='inferno-before-smoke-') as td:
 endpoint=Path(td)/'qmp.sock'
 cmd=[str(binary),'-machine','virt','-accel','tcg','-cpu','cortex-a57','-m','128M','-S','-nodefaults','-device','VGA,romfile=','-device','virtio-tablet-pci','-display','none','-monitor','none','-serial','none','-qmp',f'unix:{endpoint},server=on,wait=off']
 (out/'command.json').write_text(json.dumps(cmd,indent=2));p=subprocess.Popen(cmd,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL);conn=socket.socket(socket.AF_UNIX);q=None
 try:
  deadline=time.monotonic()+10
  while True:
   try:conn.connect(str(endpoint));break
   except (FileNotFoundError,ConnectionRefusedError):
    if p.poll() is not None or time.monotonic()>deadline:raise RuntimeError('QMP startup')
    time.sleep(.05)
  q=QMP(conn,out);q.receive();q.execute('qmp_capabilities');q.execute('cont')
  journey=ProbeJourney(out);control=ControlMailbox(out,journey=journey);results=[]
  def request(label,args={},command="probe-capture-before"):
   ident=uuid.uuid4().hex;write_private(control.path/f'request-{ident}.json',{'execute':command,'arguments':args,'created':time.time()});control.poll(q);reply=json.loads((control.path/f'reply-{ident}.json').read_text());results.append({'case':label,'reply':reply});return reply
  assert 'rejected' in request('before-appearance')
  assert 'rejected' in request('after-before-appearance',command='probe-capture-after')
  appeared='INFERNO_UIKIT_PROBE_V1 event=appeared count=0\n';tapped='INFERNO_UIKIT_PROBE_V1 event=tap count=1\n'
  (out/'serial.log').write_text(appeared);journey.poll(q,0);journey.poll(q,99)
  assert journey.state=='waiting-for-operator-before-capture' and not journey.report['captures']
  assert 'rejected' in request('extra-argument',{'filename':'not-allowed'})
  (out/'serial.log').write_text(appeared+tapped);assert 'rejected' in request('tap-already-present')
  # Synthetic fixture reset, not a guest log mutation.
  (out/'serial.log').write_text(appeared);assert 'return' in request('operator-reviewed-before')
  assert 'rejected' in request('duplicate-before')
  assert not any(r['request']['execute']=='input-send-event' for r in q.responses)
  assert 'rejected' in request('after-missing-tap',command='probe-capture-after')
  (out/'serial.log').write_text(appeared+tapped);journey.poll(q,100);journey.poll(q,102)
  assert journey.state=='waiting-for-operator-after-capture' and not journey.report['completed'] and 'probe-after' not in journey.report['captures']
  assert 'rejected' in request('after-extra-argument',{'filename':'not-allowed'},command='probe-capture-after')
  assert 'return' in request('operator-reviewed-after',command='probe-capture-after')
  assert 'rejected' in request('duplicate-after',command='probe-capture-after')
  journey.finish()
  legacy_dir=out/'legacy';legacy_dir.mkdir();legacy=ProbeJourney(legacy_dir,hardware_tap=True);(legacy_dir/'serial.log').write_text(appeared)
  legacy.poll(q,0);legacy.poll(q,2);legacy.poll(q,3);(legacy_dir/'serial.log').write_text(appeared+tapped);legacy.poll(q,4);legacy.poll(q,6);legacy.finish()
  assert sum(r['request']['execute']=='input-send-event' for r in q.responses)==2
  result={'kind':'actual image-free QMP and private mailbox with synthetic app markers; no iOS/owned app execution claim','binary_sha256':hashlib.sha256(binary.read_bytes()).hexdigest(),'source_hashes':{n:hashlib.sha256((Path('/tmp/inferno-qmp-control/companion')/n).read_bytes()).hexdigest() for n in ['boot.py','qmp_control.py','probe_journey.py']},'requests':results,'observation_journey':journey.report,'default_input_commands':0,'legacy_explicit_input_commands':2,'quit':q.execute('quit')}
  p.wait(timeout=5);result['exit_code']=p.returncode;assert p.returncode==0;(out/'result.json').write_text(json.dumps(result,indent=2));print(json.dumps({'result':'passed','requests':len(results),'exit':p.returncode}))
 finally:
  if q:q.close()
  conn.close()
  if p.poll() is None:p.terminate();p.wait(timeout=5)
