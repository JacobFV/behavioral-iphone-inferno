#!/usr/bin/env python3
"""Offline actual trace audit: no guest access and no frame-causality inference."""
import pathlib,json,collections
P=pathlib.Path(__file__).parent
lines=(P/'guest-errors-final.log').read_text().splitlines();events=[]
for n,line in enumerate(lines,1):
 if not line.startswith('apple_adp_'):continue
 f=line.split();events.append({'line':n,'name':f[0],'fields':dict(x.split('=',1) for x in f[1:])})
j=[json.loads(x) for x in (P/'display-trace-control.jsonl').read_text().splitlines()]
assert j[-1]['all_disabled'] is True
names={x['event'] for x in j if x['stage']=='after-enable'}
assert len(names)==5 and {x['event'] for x in j if x['stage']=='after-disable'}==names
for x in j:
 if 'response' in x:assert 'return' in x['response'] and 'error' not in x['response']
qmp={}
for l in (P/'qmp-trace-control-excerpt.jsonl').read_text().splitlines():
 d=json.loads(l);q=json.loads(d['raw']);qmp[(d['direction'],q['id'])]=q
for x in j:
 if 'response' not in x:continue
 i=x['response']['id'];assert qmp[('receive',i)]==x['response'];sent=qmp[('send',i)]
 assert sent['execute']=='trace-event-set-state' and sent['arguments']=={'name':x['event'],'enable':x['stage']=='after-enable'}
counts=collections.Counter(e['name'] for e in events);outcomes=collections.Counter();inside=False;draws=[];complete=0
for e in events:
 f=e['fields']
 if e['name']=='apple_adp_bh':
  if f['phase']=='enter':assert not inside;inside=True;draws=[]
  else:assert inside and draws==[('0','drawn'),('0','disabled')];assert int(f['status'],16)&(1<<20);inside=False;complete+=1
 if e['name']=='apple_adp_pipe':
  assert inside;outcomes[(f['pipe'],f['outcome'])]+=1;draws.append((f['pipe'],f['outcome']))
assert not inside
acks=collections.Counter(e['fields']['value'] for e in events if e['name']=='apple_adp_irq_write' and e['fields']['kind']=='status-w1c')
result={'event_counts':dict(counts),'pipe_outcomes':{str(k):v for k,v in outcomes.items()},'complete_bh_sequences':complete,'w1c_masks':dict(acks),'all_submits_scheduled':all(e['fields']['schedule']=='1' for e in events if e['name']=='apple_adp_submit'),'repeat_output_ready_already_pending':sum(bool(int(e['fields']['before'],16)&0x400) for e in events if e['name']=='apple_adp_output_ready'),'window_start_to_all_disabled_seconds':j[-1]['time']-j[0]['time'],'all_five_disabled':True,'event_line_map':events,'interpretation':['Healthy trace reference: each callback has one drawn then one disabled outcome, matching source callorder GP0 then GP1 and distinct controls. No compressed/DMA-failed/no-buffer outcomes.', 'DIAGNOSTIC LABEL DEFECT: original genpipe.index is never initialized, so both calls log pipe=0. GP0/GP1 attribution uses fixed source callorder plus BHcontrols, not raw index; no rendering failure follows from this label defect.','Repeated OUTPUT_READY while already pending is observed; subsequent original W1C acknowledgments are also observed. Repetition alone is not a stuck IRQ.','Trace lines have no per-event timestamps. Sequence within enabled window is known; individual draw cannot be assigned to counter tap host time or claimed as presentation.','Same window includes beta-alert closure, counter interaction and host captures; these affect rendering.','Successful boot43 does not reproduce or fix boot41 display stall. Source adds diagnostic logging only.']}
(P/'audit.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k not in ['event_line_map','interpretation']}))
