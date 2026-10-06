"""Actual host action interval audit; no VM actions or filesystem-time inference."""
import json,pathlib,hashlib,re
root=pathlib.Path('/home/brandonin/Documents/behavioral-iphone-inferno/.local-build/reports');out=pathlib.Path(__file__).parent
sha=lambda b:hashlib.sha256(b).hexdigest()
results=[]
def rows(p):
 data=p.read_bytes(); offset=0;result=[]
 for n,raw in enumerate(data.splitlines(keepends=True),1):
  result.append({'value':json.loads(raw),'reference':{'path':str(p),'line':n,'byte_start':offset,'byte_end':offset+len(raw),'sha256':sha(raw),'raw':raw.decode()}});offset+=len(raw)
 return result,{'path':str(p),'bytes':len(data),'sha256':sha(data)}
def only(xs):assert len(xs)==1,len(xs);return xs[0]
for n in [41,44,47,45,46,49,50,54,58,59,60,61]:
 p=root/f'app-boot-{n}';item={'run':n,'observed_group':'stalled' if n in [41,44,47] else 'healthy','sources':{},'missing':[]}
 try:
  controls,item['sources']['control']=rows(p/'control-transcript.jsonl');wire,item['sources']['wire']=rows(p/'serial-input-transcript.jsonl');qmp,item['sources']['qmp']=rows(p/'qmp-transcript.jsonl')
  for x in controls:x['command']=json.loads(x['value']['raw'])
  before=only([x for x in controls if x['command'].get('execute')=='probe-capture-before'])
  taps=[x for x in controls if x['command'].get('execute')=='guest-hid-gesture' and x['command'].get('arguments',{}).get('kind')=='tap']
  close=only([x for x in taps if x['value']['time']<before['value']['time'] and x['command']['arguments'].get('x')==16384 and x['command']['arguments'].get('y')==18560])
  counter=only([x for x in taps if x['value']['time']>before['value']['time'] and x['command']['arguments'].get('x')==16384 and x['command']['arguments'].get('y')==20316])
  qreq=only([x for x in qmp if x['value']['direction']=='send' and json.loads(x['value']['raw']).get('execute')=='screendump' and json.loads(x['value']['raw']).get('arguments',{}).get('filename')==str(p/'probe-before.ppm')]);qid=json.loads(qreq['value']['raw'])['id'];qreply=only([x for x in qmp if x['value']['direction']=='receive' and json.loads(x['value']['raw']).get('id')==qid]);assert json.loads(qreply['value']['raw']).get('return')=={}
  sends={}
  for name,x in [('close',close),('counter',counter)]:
   rid=x['command']['arguments']['request_id'];r=only([r for r in wire if r['value'].get('stage')=='before-send' and r['value'].get('request_id')==rid]);assert sha(r['value']['raw'].encode())==r['value']['sha256'];sends[name]=r
  item['records']={'close_control':close,'before_control':before,'counter_control':counter,'close_wire':sends['close'],'counter_wire':sends['counter'],'before_qmp_request':qreq,'before_qmp_reply':qreply}
  cs=sends['close']['value']['time'];ts=sends['counter']['value']['time'];bt=before['value']['time'];qt=qreply['value']['time']
  item['seconds']={'close_wire_to_counter_wire':ts-cs,'close_wire_to_before_control':bt-cs,'before_control_to_counter_wire':ts-bt,'before_qmp_request_to_reply':qt-qreq['value']['time'],'before_qmp_reply_to_counter_wire':ts-qt}
  item['geometry']={key:x['command']['arguments'] for key,x in [('close',close),('counter',counter)]}
  serial=(p/'serial.log').read_bytes();item['sources']['serial']={'path':str(p/'serial.log'),'bytes':len(serial),'sha256':sha(serial)};acks=[];offset=0
  for raw in serial.splitlines(keepends=True):
   text=raw.rstrip(b'\r\n').decode()
   if any(text.startswith('INFERNO_HID_ACK request_id='+x['command']['arguments']['request_id']+' ') for x in [close,counter]):acks.append({'byte_start':offset,'byte_end':offset+len(raw),'sha256':sha(raw),'text':text})
   offset+=len(raw)
  assert len(acks)==2;item['guest_acknowledgments']=acks
 except (OSError,AssertionError,KeyError) as e:item['missing'].append(str(e))
 results.append(item)
summary={}
for metric in ['close_wire_to_counter_wire','before_control_to_counter_wire','before_qmp_reply_to_counter_wire']:
 summary[metric]={group:{'min':min(x['seconds'][metric] for x in results if x['observed_group']==group and not x['missing']),'max':max(x['seconds'][metric] for x in results if x['observed_group']==group and not x['missing'])} for group in ['stalled','healthy']}
(out/'audit.json').write_text(json.dumps({'runs':results,'ranges_seconds':summary,'limits':['Close label comes from prior operator-reviewed action context; coordinates alone do not prove what pixels were present.','Host control/send/QMP timestamps are not guest delivery or animation completion timestamps.','Recorded ACK is attempt completion, not pixel acceptance.','Selected runs differ in observer cadence/helper/emulator/host scheduling, not randomized controlled groups.','No filesystem modification times are used.']},indent=2)+'\n')
print(json.dumps(summary,indent=2))
for x in results: print(x['run'],x.get('seconds'),x['missing'])
