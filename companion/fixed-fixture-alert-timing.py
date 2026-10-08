#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Explicit fixed fixture beta/Setup/counter timing; three inputs at most, no retry."""
import argparse,hashlib,importlib.util,json,math,os,re,stat,sys,time
from pathlib import Path
from PIL import Image
HERE=Path(__file__).resolve().parent
CROP=(0,250,828,1450)
COMMAND_TEMPLATE_SHA='9b4348fc07bd35891c07ee2900eea2847cdb13f92942033131acfbf0c4cef38c'
TEMPLATES={
 'beta':('after-unlock-002/settled.png','33aa5d4dee2047c11cdd427ed400c122108fcbde36882b9befaa7b8772653bee','030fa0c662d6534e2738d71b0a0c2ddd44ad814ee20f354a75b9913038682aac'),
 'setup':('after-beta-close/settled.png','d39b2b5bc77379b94fbb0faed9bd9ce7fbb422df02ef8d8ee6b4837acd9ad9e4','04b54478416ff438debe00f9d5626e9b98f82de1a1fd5d32af91a903e6664339'),
 'zero':('after-setup/settled.png','5849371c145f164b33df103ee78f178af0967a326c404702819f1fc08d70739e','1668dbc41954293f7c1a6e51de71967f4a13f04b929383f93ad04d090881a9bc')}
RUNTIME={'profile_sha256':'7939d609b99b8223863dba0b0af9d181526b420c0023cc9520563fd7e0979ed8','binary_sha256':'0889bfe40c6bbb3e6eb9d493ada2bb86637e1d7acb61e36699e16da2568563f2','build_manifest_sha256':'1c0ca353df0b88956f071503654a9a0a3f1e22346270e89accdfaa911391f096','runner_sha256':'beb55cb892ad246e215a5aa8d1178fc7dcbac6c63adfca6591c9da58606cf097','control_source_sha256':'906716956328980c1a054f1836298471b88acd1db8788c8d18b78b8cbc7c01a2'}
BASE_REPORT_SHA='c54198ab00829fe496f9da3bf4931daf4d76de7ca4bc78cd4c45815887169eea'
BASE_RETENTION_SHA='e196f51a4ed0f4281ae1179aeb7bfa88ed246ec551cc051f65b05c8964d968db'
DEPENDENCIES={'guarded-setup-counter.py':'85263dc31b20a15c5a38fb01c51657b9b2244d6c9bbc77845c1771568a71e436','qmp_control.py':'906716956328980c1a054f1836298471b88acd1db8788c8d18b78b8cbc7c01a2','owned-control.py':'3ca9c6f31839fc8dbee4fbfbaa9c3565d3086b22c6fcaf2238ead072a31d085d','vnc-control.py':'99016edaf5f58ef7a6e2433a03d5a465d46c440053bdcfc2ec06a93124d5d29f'}

DEPENDENCIES['boot.py']=RUNTIME['runner_sha256']
DEPENDENCIES['probe_journey.py']='1c4cbb542a79b85560433d62726123b99555ad0a47522d5ecd659faf3a04f308'

def sha(b):return hashlib.sha256(b).hexdigest()
def read(p,limit=64<<20):
 p=Path(p);s=p.lstat()
 if p.resolve()!=p or not stat.S_ISREG(s.st_mode) or s.st_size>limit:raise ValueError('Unsafe/oversized input: '+str(p))
 return p.read_bytes()
def record(p):return json.loads(read(p))
def rows(p):
 b=read(p)
 if b and not b.endswith(b'\n'):raise ValueError('Incomplete journal prefix')
 return [json.loads(x) for x in b.split(b'\n') if x]
def pixels(p,width):
 with Image.open(p) as im:
  if im.size!=(width,1792) or im.mode!='RGB':raise ValueError('Unexpected original RGB geometry; no normalization')
  return im.crop(CROP).tobytes()
def templates(root):
 result={}
 for state,(rel,h,c) in TEMPLATES.items():
  p=root/rel
  if sha(read(p))!=h:raise ValueError('Template file differs')
  rgb=pixels(p,832)
  if sha(rgb)!=c:raise ValueError('Template crop differs')
  result[state]=rgb
 return result

def module(name,path):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def ack(report,rid):
 raw=read(report/'serial.log');matches=[]
 for line in raw.split(b'\n'):
  line=line.rstrip(b'\r')
  if line.startswith(('INFERNO_HID_ACK request_id='+rid+' ').encode()):matches.append(line)
 if len(matches)!=1 or re.search(rb'\battempt_status=0(?:\s|$)',matches[0]) is None:raise ValueError('Missing/duplicate/failed request-specific ACK0')
 return {'serial_bytes':len(raw),'serial_sha256':sha(raw),'ack':matches[0].decode()}

def submission(report,path,expected):
 s=record(path);req=record(path.parent/'request.json');reply=record(path.parent/'stdout.txt')
 if s.get('report')!=str(report) or s.get('exit_code')!=0 or s.get('request_id')!=req.get('request_id') or s.get('source_sha256')!=DEPENDENCIES['owned-control.py'] or s.get('control_source_sha256')!=RUNTIME['control_source_sha256']:raise ValueError('Submission identity/source mismatch')
 if {k:v for k,v in req.items() if k not in ('request_id','send_deadline_monotonic')}!=expected:raise ValueError('Wrong fixed action')
 if not re.fullmatch('[0-9a-f]{32}',req['request_id']):raise ValueError('Invalid request ID')
 started=s['started_time'];finished=s['finished_time']
 if not all(isinstance(x,(int,float)) and math.isfinite(x) for x in (started,finished)) or not started<=finished<=time.time():raise ValueError('Invalid submission timestamps')
 matched=[r for r in rows(report/'control-transcript.jsonl') if json.loads(r['raw']).get('arguments',{}).get('request_id')==req['request_id']]
 if len(matched)!=1:raise ValueError('Missing/duplicate control binding')
 c=matched[0];message=json.loads(c['raw'])
 if message['execute']!='guest-hid-gesture' or message['arguments']!=req or sha(c['raw'].encode())!=c['sha256'] or c['response']!=reply or not started<=message['created']<=c['time']<=finished:raise ValueError('Control response/timing mismatch')
 fields=('x0','y0','x1','y1') if req['kind']=='swipe' else ('x','y')
 wire='INFERNO_HID_V1 '+req['request_id']+' '+req['kind'].upper()+' '+' '.join(str(req[k]) for k in fields)+' '+str(req['duration_ms'])+'\n'
 if s['expected_serial_wire']!=wire:raise ValueError('Submission wire differs from fixed request')
 wire_rows=rows(report/'serial-input-transcript.jsonl')
 before=[r for r in wire_rows if r.get('stage')=='before-send' and r.get('request_id')==req['request_id']]
 after=[r for r in wire_rows if r.get('stage')=='after-send' and r.get('response',{}).get('request_id')==req['request_id']]
 if len(before)!=1 or len(after)!=1 or before[0]['raw']!=wire or sha(wire.encode())!=before[0]['sha256'] or after[0]['response']!=reply:raise ValueError('Serial transport binding mismatch')
 if reply.get('transmission')!='written-to-serial-socket' or reply.get('bytes_sent')!=len(wire.encode()):raise ValueError('Uncertain/partial transmission; no retry')
 return {'request_id':req['request_id'],'started_time':started,'finished_time':finished,'reply':reply,'submission_sha256':sha(read(path)),'submission':str(path)}

class Driver:
 def __init__(self,args):
  self.created=False;self.host_identity=None;self.args=args;self.report=args.report.resolve(strict=True);self.output=args.output.absolute();self.G=module('fixed_guard_support',HERE/'guarded-setup-counter.py');self.refs=templates(HERE/'evidence/imported-fixture-91-visual');self.allowed=[];self.log={'complete':False,'actions':[],'observations':[],'scope':'Three explicit fixed actions at most; no retry, strict-after, finish, Home, OPEN, CPU or sample.'};self.count=0
  for n,h in DEPENDENCIES.items():
   if sha(read(HERE/n))!=h:raise ValueError('Source dependency mismatch: '+n)
  self.source_pins={str(HERE/n):h for n,h in DEPENDENCIES.items()};self.source_pins[str(Path(__file__).resolve())]=sha(read(Path(__file__).resolve()))
  importer=module('fixed_importer',HERE/'app-import.py');self.source_pins[str(HERE/'app-import.py')]=sha(read(HERE/'app-import.py'));self.output=importer.external_output(self.output)
 def save(self):
  (self.output/'sequence.json').write_text(json.dumps(self.log,indent=2)+'\n')
 def run_command(self,argv,name,timeout):
  self.log['actions'].append({'argv':argv,'started_time':time.time()});self.save()
  with (self.output/(name+'.stdout')).open('xb') as o,(self.output/(name+'.stderr')).open('xb') as e:r=self.G.bounded_subprocess(argv,o,e,timeout)
  if r:raise ValueError('Subprocess failed/uncertain; never retry')
  return self.output/(name+'.stdout')
 def command(self,name,timeout=4):
  self.count+=1;p=self.run_command([sys.executable,str(HERE/'qmp_control.py'),'--report',str(self.report),name,'--arguments','{}'],f'control-{self.count}',timeout);value=record(p)
  if 'error' in value or 'rejected' in value:raise ValueError('Control failed')
  return value
 def guard(self):
  for p,h in self.source_pins.items():
   if sha(read(p))!=h:raise ValueError('Driver dependency changed')
  v=record(self.report/'report.json')
  if 'exit_code' in v or v.get('error') or any(v.get(k)!=x for k,x in RUNTIME.items()):raise ValueError('Active runtime/source pins differ')
  base=v.get('overlay_base_report',{})
  if base.get('report_sha256')!=BASE_REPORT_SHA or base.get('stopped_manifest_sha256')!=BASE_RETENTION_SHA or v.get('root_base'):raise ValueError('Wrong fixture base')
  if sha(read(Path(base['report'])))!=BASE_REPORT_SHA or sha(read(Path(base['stopped_manifest'])))!=BASE_RETENTION_SHA:raise ValueError('Fixture metadata pins changed')
  command=record(self.report/'command.json');proc=Path('/proc')/str(v['pid'])
  if [x.decode() for x in (proc/'cmdline').read_bytes().split(b'\0') if x]!=command or (proc/'exe').resolve()!=Path(command[0]).resolve():raise ValueError('Emulator identity differs')
  procstat=(proc/'stat').read_text();ticks=int(procstat[procstat.rfind(')')+2:].split()[19]);st=(proc/'exe').stat()
  host={'pid':v['pid'],'start_ticks':ticks,'binary_metadata':{k:getattr(st,k) for k in ('st_dev','st_ino','st_size','st_mtime_ns','st_ctime_ns')}}
  if self.host_identity is None:
   if st.st_size>256<<20:raise ValueError('Unexpected executable size')
   with (proc/'exe').open('rb') as executable:
    if hashlib.file_digest(executable,'sha256').hexdigest()!=RUNTIME['binary_sha256']:raise ValueError('Actual emulator executable hash differs')
   self.host_identity=host;self.log['host_identity']=host
  elif self.host_identity!=host:raise ValueError('Host process/binary identity changed')
  if '-d' not in command or command[command.index('-d')+1]!='guest_errors':raise ValueError('Unexpected CPU logging mode')
  endpoint=command[command.index('-vnc')+1];qmp=command[command.index('-qmp')+1].split(',')[0]
  if not endpoint.startswith('unix:') or not qmp.startswith('unix:'):raise ValueError('Private Unix surfaces required')
  self.socket=Path(endpoint[5:]);parent=self.socket.parent;s=parent.stat()
  if self.socket.name!='vnc.sock' or Path(qmp[5:]).parent!=parent or parent.resolve()!=parent or stat.S_IMODE(s.st_mode)!=0o700 or s.st_uid!=os.getuid() or self.socket.resolve()!=self.socket or not stat.S_ISSOCK(self.socket.lstat().st_mode) or self.socket.lstat().st_uid!=os.getuid():raise ValueError('Unowned/aliased socket namespace')
  template=HERE/'evidence/fixed-fixture-alert-timing/command-template.json'
  if sha(read(template))!=COMMAND_TEMPLATE_SHA or [x.replace(str(self.report),'@REPORT@').replace(str(parent),'@PRIVATE@') for x in command]!=record(template):raise ValueError('Exact normalized run91 startup command differs')
  self.log['diagnostic_off_basis']={'kind':'Pinned binary/source default-disabled plus exact startup command and no subsequent ADP enable/HMP; not nine runtime query replies','command_template_sha256':COMMAND_TEMPLATE_SHA}
  if Path(v['control_mailbox']).resolve()!=self.report/'control' or list((self.report/'control').glob('request-*.json')):raise ValueError('Pending/mismatched mailbox')
  controls=rows(self.report/'control-transcript.jsonl')
  for c in controls:
   msg=json.loads(c['raw']);name=msg['execute']
   if name not in ('probe-status','probe-capture-before','guest-hid-gesture'):raise ValueError('Unexpected diagnostic/concurrent command: '+name)
   if name=='guest-hid-gesture' and msg['arguments']['request_id'] not in self.allowed:raise ValueError('Concurrent/unapproved gesture')
  states={};responses={}
  for q in rows(self.report/'qmp-transcript.jsonl'):
   msg=json.loads(q['raw'])
   if q['direction']=='send':
    if msg.get('execute')=='human-monitor-command':raise ValueError('HMP diagnostic observed')
    if msg.get('execute')=='trace-event-set-state' and msg['arguments']['name'] in self.G.qmp_control.DISPLAY_TRACE_EVENTS:
     if msg['arguments']['enable'] is not False:raise ValueError('ADP enable observed')
     states[msg['arguments']['name']]=(False,msg['id'])
   elif 'id' in msg:responses[msg['id']]=msg
  if any(on is not False or 'return' not in responses.get(i,{}) for on,i in states.values()):raise ValueError('Diagnostics not acknowledged OFF')
  ident=self.G.identity(self.report,self.args.boot_uuid)
  if hasattr(self,'identity') and ident['pid']!=self.identity['pid']:raise ValueError('Owned app incarnation changed')
  self.identity=ident
  if abs((time.time()-self.wall0)-(time.monotonic()-self.mono0))>.05:raise ValueError('Host clock drift')
 def observe(self,name,seconds=0,timeout=3):
  dest=self.output/name
  self.run_command([sys.executable,str(HERE/'vnc-control.py'),'--socket',str(self.socket),'--output',str(dest),'--settle-seconds','0','--observe-seconds',str(seconds)],name,timeout)
  r=record(dest/'report.json')
  if not r.get('completed') or r.get('pointer_events') or r.get('home_button_events'):raise ValueError('Observation incomplete/unexpected input')
  p=dest/'settled.png';entry={'path':str(p),'sha256':sha(read(p)),'time':time.time()}
  captures=r.get('captures',[])
  if not captures:raise ValueError('Missing actual capture records')
  final=captures[-1];final_path=Path(final['path'])
  if final_path.parent!=dest or sha(read(final_path))!=final['sha256']:raise ValueError('Final observation capture binding differs')
  entry['final_capture']=final;entry['observer_report_sha256']=sha(read(dest/'report.json'));entry['scope']='File capture times; no automatic visual classification'
  self.log['observations'].append(entry);self.save();return p
 def wait_until(self,wall):
  while time.time()<wall:
   if abs((time.time()-self.wall0)-(time.monotonic()-self.mono0))>.05:raise ValueError('Clock drift')
   time.sleep(max(0,min(.05,wall-time.time())))
 def run(self):
  self.wall0=time.time();self.mono0=time.monotonic()
  initial=submission(self.report,self.args.second_unlock.resolve(strict=True),{'kind':'swipe','duration_ms':1500,'x0':16384,'y0':32270,'x1':16384,'y1':9145})
  wires=[r for r in rows(self.report/'serial-input-transcript.jsonl') if r.get('stage')=='before-send']
  if len(wires)!=2 or wires[-1]['request_id']!=initial['request_id'] or any(r['operation']!='HID' or not re.fullmatch(r'INFERNO_HID_V1 [0-9a-f]{32} SWIPE 16384 32270 16384 9145 1500\n',r['raw']) for r in wires):raise ValueError('Require exactly two fixed unlocks, no earlier action')
  self.allowed=[r['request_id'] for r in wires];ack(self.report,initial['request_id']);self.guard()
  if time.time()>initial['started_time']+39:raise TimeoutError('Too late for first observation/deadline')
  self.output.mkdir(mode=0o700);self.created=True;self.log.update(source_sha256=self.source_pins,root_review_commit='5ad7a300e6',crop=list(CROP),initial_unlock=initial,identity=self.identity);self.save()
  status=self.command('probe-status')['return']
  if status['state']!='waiting-for-operator-before-capture' or status.get('automatic_input'):raise ValueError('Before-capture gate already consumed')
  prior=initial
  for state,delay,x,y in [('beta',43,16384,18560),('setup',18,11028,18432),('zero',13,16384,20316)]:
   target=prior['started_time']+delay;self.wait_until(target-4);self.guard();ack(self.report,prior['request_id'])
   if time.time()>target:raise TimeoutError('Late pre-action validation')
   p=self.observe('before-'+state,timeout=min(3,max(.1,target-time.time())))
   if pixels(p,832)!=self.refs[state]:raise ValueError('Exact state mismatch; no input')
   if state=='zero':
    capture=self.command('probe-capture-before',timeout=min(3,max(.1,target-time.time())))['return']['capture'];q=Path(capture['path'])
    if q!=self.report/'probe-before.ppm' or sha(read(q))!=capture['sha256'] or pixels(q,828)!=self.refs['zero']:raise ValueError('Strict-before QMP crop differs from reviewed zero')
    self.log['strict_before']=capture
   self.guard();ack(self.report,prior['request_id']);self.wait_until(target)
   if time.time()>target+.5:raise TimeoutError('Deadline missed; no late input')
   cutoff=self.mono0+(target+.5-self.wall0);name='tap-'+state
   argv=[sys.executable,str(HERE/'owned-control.py'),'--report',str(self.report),'--output',str(self.output/name),'--send-deadline-monotonic',str(cutoff),'tap',str(x),str(y),'--duration-ms','150']
   self.run_command(argv,name,4)
   sent=submission(self.report,self.output/name/'submission.json',{'kind':'tap','duration_ms':150,'x':x,'y':y});self.allowed.append(sent['request_id'])
   if not target<=sent['started_time']<=target+.5 or sent['reply'].get('send_deadline_monotonic')!=cutoff or sent['reply']['write_begin_monotonic']>=cutoff:raise TimeoutError('Actual submission/send missed bound; never retry')
   self.log.setdefault('timed_actions',[]).append({'state':state,'target_wall':target,'delay_seconds':delay,**sent});self.save();prior=sent
  self.observe('after-counter',seconds=25,timeout=29);self.log['counter_ack']=ack(self.report,prior['request_id']);self.log['complete']=True;self.log['visual_review_required']=True;self.save()

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--report',type=Path,required=True);p.add_argument('--boot-uuid',required=True);p.add_argument('--second-unlock',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();d=None;old=os.umask(0o077)
 try:d=Driver(a);d.run();return 0
 except BaseException as e:
  if d is not None and d.created:d.log['error']=str(e);d.save()
  print('Fixed sequence aborted; no retry: '+str(e),file=sys.stderr);return 1
 finally:os.umask(old)
if __name__=='__main__':raise SystemExit(main())
