#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Read-only audit of one retained wholly owned baremetal execution."""
import collections,hashlib,importlib.util,json,re
from pathlib import Path
D=Path('/home/brandonin/.local/share/inferno/native-probe/pending-branch-owned-attempt-1')
S=Path('/tmp/inferno-pending-branch-profile/companion')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
report=json.loads((D/'report.json').read_bytes()); data=(D/'guest-errors.log').read_bytes()
spec=importlib.util.spec_from_file_location('pending_parser',S/'pending-branch-result.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
pcs={k:report['symbols'][v] for k,v in m.LABELS.items()};parsed=m.parse(data,pcs,'owned-relocated-fixture-not-production')
assert parsed['snapshot_count']==parsed['complete_count']==3261
assert parsed['role_counts']=={x:1087 for x in pcs}
assert not parsed['semantic_violations'] and not parsed['unknown_pc_count'] and not parsed['orphan_fragments'] and parsed['incomplete_eof_record'] is None
q=[];offset=0
for line in (D/'qmp-transcript.jsonl').read_bytes().splitlines(keepends=True):
 v=json.loads(line);v.update(byte_offset=offset,byte_length=len(line),message=json.loads(v['raw']));q.append(v);offset+=len(line)
sends={x['message']['id']:x for x in q if x['direction']=='send'}
replies={x['message']['id']:x for x in q if x['direction']=='receive' and 'id' in x['message']}
journal=[json.loads(x) for x in (D/'swapwait-cpu-control.jsonl').read_bytes().splitlines()]
checks=[x for x in journal if x['stage']=='display-off-check'];assert len(checks)==27
for x in checks:
 i=x['response']['id'];assert sends[i]['message']['execute']=='trace-event-get-state'
 assert sends[i]['message']['arguments']=={'name':x['event']}
 assert replies[i]['message']==x['response'] and x['response']['return']==[{'name':x['event'],'state':'disabled'}]
starts=[x for x in journal if x['stage']=='before-enable'];ends=[x for x in journal if x['stage']=='restored'];assert len(starts)==len(ends)==3
windows=[]
for index,(start,end,enable,disable) in enumerate(zip(starts,ends,(12,23,34),(13,24,35))):
 for i,mask in ((enable,'log cpu,nochain,guest_errors'),(disable,'log guest_errors')):
  assert sends[i]['message']=={'execute':'human-monitor-command','id':i,'arguments':{'command-line':mask}}
  assert replies[i]['message']=={'return':'','id':i}
 assert sends[enable]['time']<replies[enable]['time']<sends[disable]['time']<replies[disable]['time']
 before=data[0 if index==0 else ends[index-1]['offset']:start['offset']]
 assert b' PC=' not in before and b'pl011_read: Bad offset 0x50' in before
 sample=m.parse(data[start['offset']:end['offset']],pcs,'owned-window-byte-boundary')
 windows.append({'start_offset':start['offset'],'end_offset':end['offset'],'reason':end['reason'],'role_counts':sample['role_counts'],'complete_count':sample['complete_count'],'incomplete_count':sample['snapshot_count']-sample['complete_count'],'enable':sends[enable],'enable_reply':replies[enable],'restore':sends[disable],'restore_reply':replies[disable]})
assert b' PC=' not in data[ends[-1]['offset']:] and b'pl011_read: Bad offset 0x50' in data[ends[-1]['offset']:]
assert sends[36]['message']=={'execute':'quit','id':36} and replies[36]['message']=={'return':{},'id':36}
shutdown=[x for x in q if x['message'].get('event')=='SHUTDOWN'];assert len(shutdown)==1 and shutdown[0]['message']['data']['reason']=='host-qmp-quit'
assert report['final_exit_code']==0
for p,h in report['sources'].items():assert sha(Path(p))==h
result={'scope':'Independent raw replay of wholly owned firmware-free fixture, not iOS or original kernel coverage','artifact_paths_hashes':{str(D/n):sha(D/n) for n in ('report.json','guest-errors.log','qmp-transcript.jsonl','swapwait-cpu-control.jsonl','stderr.log')},'source_hashes':report['sources'],'parser_sha256':sha(S/'pending-branch-result.py'),'base_parser_sha256':parsed['base_parser_sha256'],'actual_command_filter':report['filter'],'mailbox_declared_production_filter':report['request']['return']['filter'],'complete_count':parsed['complete_count'],'role_counts':parsed['role_counts'],'distributions':parsed['distributions'],'disabled_state_queries':len(checks),'windows':windows,'quit':sends[36],'quit_reply':replies[36],'shutdown':shutdown[0],'limits':['Synthetic slide file intentionally exercises gate; not original kernel evidence.','Relocated owned PC coverage supports logging mechanism, not proof original guest PCs are reached.','Returned production filter label differs from deliberately relocated fixture CLI filter; no identity conflation.','Error injection lost only enable reply after actual QMP acknowledged; final restoration visible in raw transcript.','Buffered file offsets bound emitted bytes, not exact guest event times.','No CPU/process/thread pairing, mode attribution or guest memory reads.']}
print(json.dumps(result,indent=2))
