#!/usr/bin/env python3
"""Offline actual82 prefix verification; no runtime calls."""
import argparse,hashlib,importlib.util,json,re
from pathlib import Path
ap=argparse.ArgumentParser();ap.add_argument('--parser',type=Path,required=True);a=ap.parse_args();p=Path(__file__).parent
load=lambda n:json.loads((p/n).read_text())
rows=lambda n:[json.loads(x) for x in (p/n).read_text().splitlines()]
spec=importlib.util.spec_from_file_location('pending',a.parser);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
raw=(p/'guest-errors.log.prefix').read_bytes();parsed=m.parse(raw)
assert parsed['snapshot_count']==parsed['complete_count']==183
assert not parsed['unknown_pc_count'] and not parsed['semantic_violations'] and not parsed['orphan_fragments']
assert parsed['role_counts']=={'null-active':183}
assert all(b['branch_observation']['requested_token']==b['branch_observation']['completed_token']==253 and b['branch_observation']['active_pointer']=='0x0000000000000000' for b in parsed['blocks'])
cmd=load('command.json.prefix');report=load('report.json.prefix');build=load('build-manifest.json.prefix')
assert cmd[cmd.index('-dfilter')+1]=='0xfffffff0096f1c74+4,0xfffffff0096f1c7c+4,0xfffffff0096f1d1c+4'
assert cmd[cmd.index('-d')+1]=='guest_errors'
assert report['binary_sha256']=='0889bfe40c6bbb3e6eb9d493ada2bb86637e1d7acb61e36699e16da2568563f2'
assert report['build_manifest_sha256']==hashlib.sha256((p/'build-manifest.json.prefix').read_bytes()).hexdigest()
slide=re.findall(rb'^info: Kernel Virtual Slide: (0x[0-9a-fA-F]+)\r?$',(p/'stderr.log.prefix').read_bytes(),re.M);assert slide==[b'0x0000000000000000']
j=rows('swapwait-cpu-control.jsonl.prefix');before=[x for x in j if x['stage']=='before-enable'];restored=[x for x in j if x['stage']=='restored'];assert len(before)==len(restored)==1
before=before[0];restored=restored[0];assert before['seconds']==1 and restored['reason']=='deadline'
assert all(before['offset']<=b['start']<b['end']<=restored['offset'] for b in parsed['blocks'])
q=rows('qmp-transcript.jsonl.prefix');messages=[(x,json.loads(x['raw'])) for x in q]
def matched(command,args,reply):
 sent=[x for x,v in messages if x['direction']=='send' and v=={'execute':command,'id':reply['id'],'arguments':args}]
 recv=[x for x,v in messages if x['direction']=='receive' and v==reply]
 assert len(sent)==len(recv)==1 and sent[0]['time']<=recv[0]['time'];return {'request':sent[0],'reply':recv[0]}
checks=[x for x in j if x['stage']=='display-off-check'];assert len(checks)==9 and len({x['event'] for x in checks})==9
proof=[]
for x in checks:
 assert x['response']['return']==[{'name':x['event'],'state':'disabled'}] and x['time']<before['time']
 proof.append(matched('trace-event-get-state',{'name':x['event']},x['response']))
enable=next(x for x in j if x['stage']=='after-enable');disable=next(x for x in j if x['stage']=='after-restore')
proof.append(matched('human-monitor-command',{'command-line':'log cpu,nochain,guest_errors'},enable['response']))
proof.append(matched('human-monitor-command',{'command-line':'log guest_errors'},disable['response']))
display=rows('display-trace-control.jsonl.prefix');stops=[x for x in display if x['stage']=='stop-result'];assert stops[-1]['all_disabled'] and stops[-1]['pending']==[] and stops[-1]['time']<before['time']
serial=(p/'serial.log.prefix').read_bytes();selected=[];off=0
for no,line in enumerate(serial.splitlines(keepends=True),1):
 if (b'8526bf0ac8cb4665a4fce5be9ce240e9' in line or b'INFERNO_UIKIT: tap' in line or b'INFERNO_EVENT_RELAY_READY' in line):selected.append({'line':no,'offset':off,'bytes':len(line),'text':line.decode(errors='replace')})
 off+=len(line)
result={'scope':'Actual82 first failed production pending-branch window; read-only independent prefix audit','parser_sha256':hashlib.sha256(a.parser.read_bytes()).hexdigest(),'binary_sha256':report['binary_sha256'],'build_manifest_sha256':report['build_manifest_sha256'],'runner_sha256':report['runner_sha256'],'control_source_sha256':report['control_source_sha256'],'pins':{'zero_slide':True,'exact_three_filter':True,'default_CPU_off':True,'nine_ADP_disabled_checks':True},'window':{'before':before,'restored':restored,'enable_reply':enable,'restore_reply':disable,'ADP_stop':stops[-1],'all_snapshot_offsets_inside':True},'populations':parsed['distributions'],'counts':{'complete':183,'null_active':183,'active_join':0,'queued_match':0,'unknown':0,'malformed':0},'raw_QMP_matches':proof,'serial_context':selected,'interpretation':'Observed null-active comparison population has requested253 equal completed253, X11zero. This narrows beyond failed76 stationary token/pending returns: it does not support nonnull-active token as the observed pending condition in82. No entry/return or mode/CPU/process pairing is possible across profiles or attempts.','limits':['Exact source-reviewed registers only; X10 ignored at null site.','Absence of active/queued snapshots is not proof no active/queued request existed elsewhere or outside window.','Completed token is a mapped field label, not proof all frontend/display completion succeeded; equality remains a pending comparison in original mode0 mapping.','Mode is unknown at these PCs; do not assign prior76 flags to82.','CPU nochain perturbs execution globally; bounded window can overshoot and counts are snapshots not invocations.','Prefixes captured from live attempt after restore; root owns visual classification, no worker guest action.']}
(p/'audit.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result['counts']))
