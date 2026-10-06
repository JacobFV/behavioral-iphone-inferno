"""Read-only ordered ADP completion audit of actual retained trace logs."""
import pathlib,re,json,hashlib
root=pathlib.Path('/home/brandonin/Documents/behavioral-iphone-inferno');out=pathlib.Path(__file__).parent
sha=lambda b:hashlib.sha256(b).hexdigest()
results=[]
for n in (44,47,49,53,57):
 p=root/f'.local-build/reports/app-boot-{n}/guest-errors.log';data=p.read_bytes();events=[];offset=0
 for lineno,raw in enumerate(data.splitlines(keepends=True),1):
  text=raw.decode().rstrip('\r\n')
  if text.startswith('apple_adp_'):events.append({'line':lineno,'byte_start':offset,'byte_end':offset+len(raw),'sha256':sha(raw),'text':text})
  offset+=len(raw)
 cycles=[];current=None;anomalies=[];ready_before={}
 for row in events:
  t=row['text']
  if t.startswith('apple_adp_output_ready'):
   key=re.search(r'before=(0x\w+)',t)[1];ready_before[key]=ready_before.get(key,0)+1
  if t.startswith('apple_adp_submit'):
   if current is not None:anomalies.append({'reason':'submit before prior processed W1C','current':current,'next':row})
   current={'submit':row}
  elif t.startswith('apple_adp_bh phase=enter'):
   if current is None or 'enter' in current:anomalies.append({'reason':'unpaired/repeated BH entry','row':row})
   else:current['enter']=row
  elif t.startswith('apple_adp_bh phase=exit'):
   if current is None or 'enter' not in current:anomalies.append({'reason':'unpaired BH exit','row':row})
   else:current['exit']=row
  elif t.startswith('apple_adp_irq_write kind=status-w1c') and int(re.search(r'value=(0x\w+)',t)[1],16)&0x100000:
   if current is None or 'exit' not in current:anomalies.append({'reason':'processed W1C without traced draw','row':row})
   else:
    current['processed_w1c']=row
    assert int(re.search(r'before=(0x\w+)',t)[1],16)&0x100000
    assert not int(re.search(r'status=(0x\w+)',t)[1],16)&0x100000
    cycles.append(current);current=None
 assert not anomalies and current is None,(n,anomalies,current)
 results.append({'run':n,'trace_path':str(p),'bytes':len(data),'sha256':sha(data),'cycles':cycles,'cycle_count':len(cycles),'ready_before':ready_before,'anomalies':anomalies,'open_cycle_at_trace_end':current})
 (out/f'run{n}-selected-trace.json').write_text(json.dumps(events,indent=2)+'\n')
sources={}
for name,ranges in {'hw/display/apple_displaypipe_v4.c':[(291,296),(570,611),(646,659),(679,718),(976,995)],'util/async.c':[(72,88),(229,239)],'hw/intc/apple_aic.c':[(135,212),(340,360),(395,423)],'hw/arm/apple-silicon/t8030.c':[(2154,2165)],'hw/display/trace-events':[(228,235)]}.items():
 data=(root/name).read_bytes();lines=data.decode().splitlines();sources[name]={'sha256':sha(data),'excerpts':[{'first_line':a,'last_line':b,'text':'\n'.join(lines[a-1:b])} for a,b in ranges]}
(out/'source-excerpts.json').write_text(json.dumps(sources,indent=2)+'\n')
(out/'audit.json').write_text(json.dumps({'actual_ordered_cycles':results,'source_revision':__import__('subprocess').check_output(['git','-C',str(root),'rev-parse','HEAD'],text=True).strip(),'limits':['Counts cover enabled trace windows only; no claim outside captured windows.','Every cycle contains submit then BH enter/exit then W1C clearing a genuinely set processed bit before next traced submit.','Guest W1C proves register write, not kernel thread/fence/userland notification completion.','Output-ready may coalesce when already set in both failed and healthy runs.','No timestamp per original trace line; ordered byte references are not latency measurements.']},indent=2)+'\n')
print([(r['run'],r['cycle_count']) for r in results])
