import sys,time,json,hashlib
from pathlib import Path
report=Path(sys.argv[1]).resolve();out=report/'event-arrivals';out.mkdir(exist_ok=False)
source=report/'serial.log';initial=source.stat().st_size if source.exists() else 0
meta={'purpose':'Host observations of actual fixed guest log lines, not intrinsic guest latency','initial_bytes':initial,'started_time':time.time(),'poll_seconds':0.05,'limits':'Existing bytes have no arrival timing; new timing includes relay delay and polling. QMP cont and explicit input timestamps remain separate.'}
(out/'context.json').write_text(json.dumps(meta,indent=2)+'\n')
position=0;buffer=b'';offset=0;count=0;deadline=time.monotonic()+3600
patterns=(b'INFERNO_OPEN_',b'INFERNO_LIFECYCLE_RELAY_',b'INFERNO_EVENT_PROCESS_IDENTITY',b'INFERNO_TIMING_RELAY_RAW',b'INFERNO_TIMING_RELAY_RECORD',b'INFERNO_LAUNCH_TIMING_V1',b'INFERNO_LAUNCH_TIMING_ERROR',b'INFERNO_UIKIT_PROBE_V1 event=',b'INFERNO_EVENT_RELAY_RECORD',b'INFERNO_EVENT_RELAY_READY',b'INFERNO_EVENT_RELAY_ERROR',b'INFERNO_HID_ACK',b'event=open-callback',b'Early boot complete')
with (out/'observations.jsonl').open('w') as log:
 while time.monotonic()<deadline and count<512:
  try:
   with source.open('rb') as f:f.seek(position);data=f.read(262144)
  except FileNotFoundError:data=b''
  position+=len(data);buffer+=data;now=time.time();mono=time.monotonic()
  while b'\n' in buffer:
   line,buffer=buffer.split(b'\n',1);end=offset+len(line)+1
   if any(p in line for p in patterns):
    row={'observed_time':now,'monotonic':mono,'byte_start':offset,'byte_end':end,'preexisting':end<=initial,'raw_hex':line.hex(),'text':line.decode('utf8','replace'),'sha256':hashlib.sha256(line).hexdigest()}
    log.write(json.dumps(row)+'\n');log.flush();count+=1
   offset=end
  try:done='exit_code' in json.loads((report/'report.json').read_text())
  except (FileNotFoundError,json.JSONDecodeError):done=False
  if done and not data:break
  time.sleep(0.05)
meta.update(finished_time=time.time(),records=count,last_byte=position)
(out/'context.json').write_text(json.dumps(meta,indent=2)+'\n')
print(json.dumps(meta))
