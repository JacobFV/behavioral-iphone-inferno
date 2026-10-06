#!/usr/bin/env python3
"""Bounded synthetic process-launch log fixture; not a guest execution claim."""
import importlib.util,json,tempfile,time,hashlib
from pathlib import Path
from types import SimpleNamespace
source=Path(__file__).resolve().parents[2]/'process-launch-timing.py';s=importlib.util.spec_from_file_location('process_parser',source);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
h=lambda b:hashlib.sha256(b).hexdigest();boot='11111111-2222-3333-4444-555555555555';rid='1'*32;dismiss='2'*32
with tempfile.TemporaryDirectory() as tmp:
 r=Path(tmp);serial=r/'serial.log';control=r/'control-transcript.jsonl';wire=r/'serial-input-transcript.jsonl'
 lines=[f'INFERNO_TIMING_RELAY_RAW source=guest-loopback record=INFERNO_TIMING_V1 {boot} 266 1 main 50 3 2','INFERNO_EVENT_PROCESS_IDENTITY pid=266 query_result=56 errno=0 uniqueid=266 idversion=1 source=original-libproc fallback=main-tick-and-pid',f'INFERNO_HID_ACK request_id={dismiss} attempt_status=0 delivery=unproven timestamp=90','INFERNO_READINESS_BEGIN seconds=1200','  PID  PPID   UID STAT COMM','  1 0 0 Ss /sbin/launchd','  310 1 0 R /bin/ps','INFERNO_READINESS_END seconds=1200 status=0 ps_watchdog=600 timed_out=0']
 lines.insert(1,f'INFERNO_TIMING_RELAY_RECORD boot={boot} pid=266 sequence=1 hook=main ticks=50 numer=3 denom=2 complete=0 source=guest-loopback claimed_pid_verified=1 peer_pid_authenticated=0')
 prefix=('\r\r\n'.join(lines)+'\r\r\n').encode();serial.write_bytes(prefix)
 def ctl(command,args,when):
  raw=json.dumps({'execute':command,'arguments':args,'created':when})+'\n';return {'time':when+.001,'raw':raw,'sha256':h(raw.encode())}
 control.write_text(json.dumps(ctl('guest-hid-gesture',{'request_id':dismiss,'kind':'swipe'},time.time()-2))+'\n')
 snap=r/'absence.json';result={};assert m.capture(SimpleNamespace(report=r,old_pid=266,ps_seconds=1200,after_request_id=dismiss,output=snap),result)==0;snap.write_text(json.dumps(result))
 now=time.time()+1
 with control.open('a') as f:f.write(json.dumps(ctl('guest-open-app',{'request_id':rid,'boot_uuid':boot},now))+'\n')
 raw=f'INFERNO_OPEN_V1 {rid} {boot}\n';wire.write_text(json.dumps({'time':now+.002,'stage':'before-send','request_id':rid,'raw':raw,'sha256':h(raw.encode())})+'\n')
 new=['INFERNO_EVENT_PROCESS_IDENTITY pid=400 query_result=56 errno=0 uniqueid=400 idversion=2 source=original-libproc fallback=main-tick-and-pid']
 for seq,(hook,tick) in enumerate(zip(['main','launch-delegate','window-request','appeared','active'],[101,102,103,105,108]),1):
  new += [f'INFERNO_TIMING_RELAY_RAW source=guest-loopback record=INFERNO_TIMING_V1 {boot} 400 {seq} {hook} {tick} 3 2',f'INFERNO_TIMING_RELAY_RECORD boot={boot} pid=400 sequence={seq} hook={hook} ticks={tick} numer=3 denom=2 complete={int(seq==5)} source=guest-loopback claimed_pid_verified=1 peer_pid_authenticated=0']
 for seq,hook in enumerate(['main','appeared','active'],1):
  new += [f'INFERNO_EVENT_RELAY_RAW source=guest-loopback record=INFERNO_EVENT_V1 {boot} 400 {seq} {hook} 0',f'INFERNO_EVENT_RELAY_RECORD boot={boot} pid=400 sequence={seq} source=guest-loopback claimed_pid_verified=1 peer_pid_authenticated=0']
 new.append(f'INFERNO_OPEN_TIMING_V1 request_id={rid} boot={boot} pid=399 request_ticks=100 callback_ticks=109 numer=3 denom=2 accepted=1')
 complete=prefix+('\r\r\n'.join(new)+'\r\r\n').encode();serial.write_bytes(complete)
 args=SimpleNamespace(report=r,old_pid=266,new_pid=400,request_id=rid,absence=snap);derived={};assert m.derive(args,derived)==0
 assert derived['intervals']['request_to_main']['nanoseconds_numerator']==3 and derived['intervals']['request_to_main']['nanoseconds_denominator']==2
 cases={'identity_query_denied':complete.replace(b'pid=400 query_result=56 errno=0',b'pid=400 query_result=0 errno=1'),'same_kernel_id':complete.replace(b'uniqueid=400',b'uniqueid=266'),'newmain_before_request':complete.replace(b'400 1 main 101',b'400 1 main 99'),'corrupt_absence_prefix':complete.replace(b'/bin/ps',b'/bin/xx',1)};checks=[]
 for name,data in cases.items():
  serial.write_bytes(data)
  try:m.derive(args,{})
  except ValueError as e:checks.append({'case':name,'rejected':str(e)})
  else:raise AssertionError(name)
 result={'synthetic_only':True,'guest_execution':False,'parser_sha256':h(source.read_bytes()),'exact_request_to_main_ns':'3/2','checks':checks}
 Path(__file__).with_name('synthetic-results.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
