# SPDX-License-Identifier: AGPL-3.0-or-later
"""Recompute immutable run59 trace-prefix observations; no runtime operations."""
import collections, hashlib, json, re
from pathlib import Path
D=Path(__file__).resolve().parent
h=lambda b:hashlib.sha256(b).hexdigest()
b=(D/'guest-errors.prefix.log').read_bytes()
assert len(b)==300868
before=json.loads((D/'before.json').read_text())['checkpoint']; after=json.loads((D/'after.json').read_text())['checkpoint']
assert before['size']==4594 and before['inode']==after['inode'] and before['device']==after['device']
rows=[];off=0
for line in b.splitlines(keepends=True):
 if off>=4594 and line.startswith(b'apple_adp_'):
  s=line.decode().strip(); name=s.split()[0]; fields=dict(re.findall(r'(\w+)=([^ ]+)',s))
  rows.append(dict(offset=off,length=len(line),sha256=h(line),event=name,fields=fields))
 off+=len(line)
c=collections.Counter(r['event'] for r in rows)
reads=[r for r in rows if r['event']=='apple_adp_status_read'];writes=[r for r in rows if r['event']=='apple_adp_irq_write' and r['fields']['kind']=='status-w1c']
assert len(reads)==len(writes)==71
pairs=[]
for r,w in zip(reads,writes):
 assert r['offset']<w['offset']
 between=[x for x in rows if r['offset']<x['offset']<w['offset']]
 assert not any(x['event']=='apple_adp_status_read' for x in between)
 rv=int(r['fields']['value'],16); wf=w['fields']; value=int(wf['value'],16); pre=int(wf['before'],16); post=int(wf['status'],16)
 assert rv==value and post==(pre&~value)
 pairs.append(dict(read=r['offset'],write=w['offset'],value=hex(rv),before=hex(pre),after=hex(post),intervening=collections.Counter(x['event'] for x in between)))
unknown=[r for r in rows if r['event']=='apple_adp_unknown_mmio' and r['fields']['block']=='main' and r['fields']['offset']=='0x45004']
assert all(r['fields']['write']=='0' and r['fields']['value']=='0x0' for r in unknown)
# Classify each unknown read by the nearest status-read offsets, without claiming causality.
correlations=[dict(offset=x['offset'],previous_status=next((r['offset'] for r in reversed(reads) if r['offset']<x['offset']),None),next_status=next((r['offset'] for r in reads if r['offset']>x['offset']),None)) for x in unknown]
q=[json.loads(x) for x in (D/'qmp.prefix.jsonl').read_text().splitlines()]
commands=[dict(time=x['time'],**json.loads(x['raw'])) for x in q if x['direction']=='send']
assert not any(x['execute'] in ['human-monitor-command','input-send-event','send-key'] for x in commands)
ct=[json.loads(x) for x in (D/'control.prefix.jsonl').read_text().splitlines()]
assert [json.loads(x['raw'])['execute'] for x in ct]==['trace-display-window']
assert not (D/'serial-input.prefix.jsonl').read_bytes()
j=[json.loads(x) for x in (D/'trace-control.prefix.jsonl').read_text().splitlines()]
en=[x for x in j if x['stage']=='after-enable'];dis=[x for x in j if x['stage']=='after-disable']
assert len(en)==len(dis)==8 and {x['event'] for x in en}=={x['event'] for x in dis}
for x in en+dis:
 assert x['response']['return']=={}
 assert any(y['direction']=='receive' and json.loads(y['raw'])==x['response'] for y in q)
view=json.loads((D/'view-report.json').read_text())
result=dict(scope='File-visible immutable prefix; no per-event timestamps, guest frame completion, causality, or performance claim.',prefix_sha256=h(b),range=[4594,300868],bytes=300868-4594,checkpoint_wall_seconds=after['wall_time']-before['wall_time'],event_counts=c,status_values=collections.Counter(r['fields']['value'] for r in reads),pairs=pairs,unknown_45004=correlations,unknown_45004_count=len(unknown),trace_enabled=[x['time'] for x in en],trace_disabled=[x['time'] for x in dis],qmp_commands=commands,view_connection=[view['connection_established_time'],view['connection_closed_time']],limits=['Status reads can originate from debug/HMP too; retained sole-owner QMP/control prefix contains no such request. This is provenance, not an intrinsic CPU-origin tag.','Continuous VNC refresh was active; buffered stderr boundaries do not establish event timing or display presentation.','Parent reviewed final observed-0008 as lockscreen; visual interpretation is separate from numeric trace audit.'])
(D/'result.json').write_text(json.dumps(result,indent=2)+'\n')
(D/'event-index.json').write_text(json.dumps(rows,indent=2)+'\n')
print(json.dumps({k:result[k] for k in ['bytes','event_counts','status_values','unknown_45004_count']},indent=2))
