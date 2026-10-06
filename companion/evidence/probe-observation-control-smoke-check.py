import sys,socket,time,tempfile,subprocess,json,hashlib
from pathlib import Path
sys.path.insert(0,"/tmp/inferno-qmp-control/companion")
from boot import QMP
from probe_journey import ProbeJourney
out=Path(__file__).parent
binary=Path("/home/brandonin/Documents/behavioral-iphone-inferno/.local-build/build/qemu-system-aarch64")
results=[]
for mode in [False,True]:
 d=out/("legacy-explicit" if mode else "observe-default");d.mkdir(exist_ok=True)
 with tempfile.TemporaryDirectory(prefix="inferno-journey-smoke-") as td:
  endpoint=Path(td)/"qmp.sock"
  cmd=[str(binary),"-machine","virt","-accel","tcg","-cpu","cortex-a57","-m","128M","-S","-nodefaults","-device","VGA,romfile=","-device","virtio-tablet-pci","-display","none","-monitor","none","-serial","none","-qmp",f"unix:{endpoint},server=on,wait=off"]
  (d/"command.json").write_text(json.dumps(cmd,indent=2))
  with (d/"stderr.log").open("wb") as err:
   proc=subprocess.Popen(cmd,stdout=subprocess.DEVNULL,stderr=err)
   conn=socket.socket(socket.AF_UNIX);q=None
   try:
    deadline=time.monotonic()+10
    while not endpoint.exists():
     if proc.poll() is not None:raise RuntimeError("QEMU exited")
     if time.monotonic()>deadline:raise TimeoutError("QMP socket")
     time.sleep(.05)
    while True:
     try:conn.connect(str(endpoint));break
     except ConnectionRefusedError:
      if time.monotonic()>deadline:raise
      time.sleep(.05)
    q=QMP(conn,d);q.receive();q.execute("qmp_capabilities")
    if mode:q.execute("cont")
    journey=ProbeJourney(d,hardware_tap=mode)
    (d/"serial.log").write_text("INFERNO_UIKIT_PROBE_V1 event=appeared count=0\n")
    journey.poll(q,0);journey.poll(q,2)
    if mode:journey.poll(q,3)
    sent=[r["request"]["execute"] for r in q.responses]
    assert sent.count("input-send-event")== (2 if mode else 0),sent
    assert not journey.report["completed"]
    (d/"serial.log").write_text("INFERNO_UIKIT_PROBE_V1 event=appeared count=0\nINFERNO_UIKIT_PROBE_V1 event=tap count=1\n")
    journey.poll(q,4);journey.poll(q,6);journey.finish()
    assert journey.report["completed"]
    result={"mode":journey.report["input_mode"],"input_commands":sent.count("input-send-event"),"synthetic_markers":True,"guest_images":False,"journey_state_test":journey.report,"quit":q.execute("quit")}
    proc.wait(timeout=10);result["exit_code"]=proc.returncode
    (d/"result.json").write_text(json.dumps(result,indent=2));results.append(result)
   finally:
    if q:q.close()
    conn.close()
    if proc.poll() is None:proc.terminate();proc.wait(timeout=10)
summary={"kind":"firmware-free actual QMP with synthetic app markers; no iOS or UIKit claim","binary_sha256":hashlib.sha256(binary.read_bytes()).hexdigest(),"sources":{n:hashlib.sha256((Path("/tmp/inferno-qmp-control/companion")/n).read_bytes()).hexdigest() for n in ["boot.py","probe_journey.py"]},"results":results}
(out/"result.json").write_text(json.dumps(summary,indent=2));print(json.dumps(summary,indent=2))
