#!/usr/bin/env python3
"""Recompute traced stall boundary from retained bytes, no guest access."""
import json,pathlib,collections,hashlib
P=pathlib.Path(__file__).parent
b=(P/'guest-errors-prefix.log').read_bytes();s=json.loads((P/'counter-submission.json').read_text());review=json.loads((P/'trace-after-counter-review.json').read_text())['checkpoint'];prov=json.loads((P/'provenance.json').read_text());actual=prov['files']['guest-errors-prefix.log']
for point in (s['trace_before'],s['trace_after'],review):assert (point['device'],point['inode'])==(actual['device'],actual['inode']) and point['size']<=len(b)
j=[json.loads(x) for x in (P/'display-trace-control-prefix.jsonl').read_text().splitlines()];assert j[-1]['all_disabled'] is True
for x in j:
 if 'response' in x:assert 'error' not in x['response']
qmp={}
for line in (P/'qmp-query-trace-excerpt.jsonl').read_text().splitlines():
 row=json.loads(line);data=json.loads(row['raw']);qmp[(row['direction'],data['id'])]=data
for row in j:
 if 'response' not in row:continue
 ident=row['response']['id'];assert qmp[('receive',ident)]==row['response']
 assert qmp[('send',ident)]['arguments']=={'name':row['event'],'enable':row['stage']=='after-enable'}
events=[];offset=0
for line in b.splitlines(keepends=True):
 if line.startswith(b'apple_adp_'):
  f=line.decode().split();events.append({'offset':offset,'name':f[0],'fields':dict(x.split('=',1) for x in f[1:])})
 offset+=len(line)
regions=[]
for label,a,z in [('before_tap_checkpoint',0,s['trace_before']['size']),('CLI_submission',s['trace_before']['size'],s['trace_after']['size']),('after_CLI_through_review',s['trace_after']['size'],review['size']),('after_review_through_retained_deadline',review['size'],len(b))]:
 region=[e for e in events if a<=e['offset']<z];regions.append({'label':label,'start':a,'end':z,'sha256':hashlib.sha256(b[a:z]).hexdigest(),'counts':dict(collections.Counter(x['name'] for x in region))})
assert not any(x['name'] in ('apple_adp_submit','apple_adp_bh','apple_adp_pipe') for x in events if x['offset']>=s['trace_before']['size'])
active=False;draws=[];cycles=0
for e in events:
 f=e['fields']
 if e['name']=='apple_adp_bh':
  if f['phase']=='enter':assert not active;active=True;draws=[]
  else:assert active and draws==[('0','drawn'),('1','disabled')];active=False;cycles+=1
 elif e['name']=='apple_adp_pipe':assert active;draws.append((f['pipe'],f['outcome']))
assert not active
c=json.loads((P/'continuous-capture-report.json').read_text());hashes=[x['sha256'] for x in c['captures']]
a={'trace_events':len(events),'counts':dict(collections.Counter(x['name'] for x in events)),'regions':regions,'complete_preboundary_draw_cycles':cycles,'last_submit_offset':max(x['offset'] for x in events if x['name']=='apple_adp_submit'),'last_bh_exit_offset':max(x['offset'] for x in events if x['name']=='apple_adp_bh' and x['fields']['phase']=='exit'),'window_duration_seconds':j[-1]['time']-j[0]['time'],'all_disabled':True,'continuous_capture_count':len(hashes),'continuous_hashes':sorted(set(hashes)),'event_offsets':events,'interpretation':['Corrected labels show five complete earlier callbacks with GP0 drawn and GP1 disabled.','No submit/BH/pipe trace after before-tap file-visible checkpoint through disabled-window prefix; output-ready events and guest W1C acknowledgments continue. This narrows the boundary upstream of modeled submit, not a scheduled draw BH failing to run.','The guest handles ready interrupts; this does not establish compositor health or explain missing submissions. No IRQ behavior patch justified yet.','Checkpoints bound file visibility, not exact device execution times. Per-event timestamps absent; no exact per-tap presentation latency claim.','Genuine tap1 exists separately; root reviewed stillcounter0 and withheld strictafter. Capture hashes retained; visual interpretation belongs to reviewed image evidence.','VM was live at retention; this is not final-run evidence.']}
(P/'audit.json').write_text(json.dumps(a,indent=2)+'\n');print(json.dumps({k:v for k,v in a.items() if k not in ['event_offsets','interpretation']}))
