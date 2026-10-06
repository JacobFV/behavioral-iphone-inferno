import pathlib,time,re,json,hashlib
r=pathlib.Path('/home/brandonin/Documents/behavioral-iphone-inferno/.local-build/reports/app-boot-38');o=pathlib.Path('/tmp/inferno-disk-overlay-chain/companion/evidence/process-absence-38');deadline=time.monotonic()+1000
begin_marker=b'INFERNO_READINESS_BEGIN seconds=1200';end_marker=b'INFERNO_READINESS_END seconds=1200 status=0 ps_watchdog=600 timed_out=0';ack=b'INFERNO_HID_ACK request_id=10e2b4b73dcd406f8ca3229fe11ec032 '
h=lambda b:hashlib.sha256(b).hexdigest()
while time.monotonic()<deadline:
 started=time.time();data=(r/'serial.log').read_bytes();observed=time.time();start=data.find(begin_marker);end=data.find(end_marker,start if start>=0 else 0)
 if start>=0 and end>=0 and data.find(b'\n',end)>=0:
  end=data.index(b'\n',end)+1;block=data[start:end];header=b'  PID  PPID   UID STAT COMM';hp=block.find(header);assert hp>=0 and block.count(header)==1
  table=block[block.index(b'\n',hp)+1:block.index(end_marker)];rows=[];bad=[]
  for raw in table.split(b'\n'):
   text=raw.rstrip(b'\r').decode(errors='replace')
   if not text.strip():continue
   match=re.fullmatch(r'\s*(\d+)\s+(\d+)\s+(\d+)\s+(\S+)\s+(.+)',text)
   if match:rows.append({'pid':int(match[1]),'ppid':int(match[2]),'uid':int(match[3]),'state':match[4],'comm':match[5]})
   else:bad.append(text)
  ackpos=data.find(ack);assert 0<=ackpos<start
  matches=[x for x in rows if x['pid']==266 or x['comm']=='/Applications/InfernoProbe.app/InfernoProbe']
  clean=not bad and len(rows)>0 and len({x['pid'] for x in rows})==len(rows)
  o.mkdir(exist_ok=False);(o/'serial-prefix.log').write_bytes(data);(o/'ps-block.log').write_bytes(block)
  controls=(r/'control-transcript.jsonl').read_bytes();(o/'control-prefix.jsonl').write_bytes(controls)
  result={'kind':'actual_completed_original_ps_observation','read_started_host_epoch':started,'captured_host_epoch':observed,'nominal_seconds':1200,'serial_prefix':{'path':str(r/'serial.log'),'bytes':len(data),'sha256':h(data)},'block':{'byte_start':start,'byte_end':end,'sha256':h(block),'header_byte_start':start+hp},'dismiss_ack_byte_start':ackpos,'complete_successful_ps':clean,'row_count':len(rows),'unparsed_lines':bad,'old_pid':266,'owned_executable':'/Applications/InfernoProbe.app/InfernoProbe','matching_rows':matches,'absence_observed':clean and not matches,'rows':rows,'control_prefix_sha256':h(controls),'limit':'One completed original ps enumeration after dismissal; not continuous nonexistence or termination cause. Must precede named OPEN host creation for new-process attribution.'}
  (o/'observation.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:result[k] for k in ['captured_host_epoch','complete_successful_ps','row_count','matching_rows','absence_observed']}),flush=True);break
 if 'exit_code' in json.loads((r/'report.json').read_text()):raise RuntimeError('Guest stopped before target1200 snapshot')
 time.sleep(2)
else:raise RuntimeError('Bounded observer deadline exceeded')
