#!/usr/bin/env python3
"""Offline actual84 prefix verification; no runtime calls."""
import argparse,hashlib,importlib.util,json,re
from pathlib import Path
ap=argparse.ArgumentParser();ap.add_argument('--parser',type=Path,required=True);a=ap.parse_args();p=Path(__file__).parent
load=lambda n:json.loads((p/n).read_text())
rows=lambda n:[json.loads(x) for x in (p/n).read_text().splitlines()]
spec=importlib.util.spec_from_file_location('pending',a.parser);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
raw=(p/'guest-errors.log.prefix').read_bytes();parsed=m.parse(raw)
assert parsed['snapshot_count']==parsed['complete_count']==786
assert not parsed['unknown_pc_count'] and not parsed['semantic_violations'] and not parsed['orphan_fragments']
assert parsed['role_counts']=={'accepted-mode':200,'token-equality-predicate-true':192,'matching-request-local-false':191,'matching-request-local-true':4,'final-return':199}
assert all(b['observation']['mode']==0 for b in parsed['blocks'] if b['role']=='accepted-mode')
cmd=load('command.json.prefix');report=load('report.json.prefix');build=load('build-manifest.json.prefix')
assert cmd[cmd.index('-dfilter')+1]=='0xfffffff0096f1bc0+4,0xfffffff0096f1bf4+4,0xfffffff0096f1e4c+4,0xfffffff0096f1e50+4,0xfffffff0096e219c+4'
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

result={'scope':'Actual84 healthy original Clock calibration, separate from preceding strict/warm acceptance; no worker runtime actions',
'parser_sha256':hashlib.sha256(a.parser.read_bytes()).hexdigest(),
'binary_sha256':report['binary_sha256'],'build_manifest_sha256':report['build_manifest_sha256'],
'runner_sha256':report['runner_sha256'],'control_source_sha256':report['control_source_sha256'],
'pins':{'zero_slide':True,'exact_five_filter':True,'default_CPU_off':True,'nine_ADP_disabled_checks':True},
'window':{'before':before,'restored':restored,'enable_reply':enable,'restore_reply':disable,'all_snapshot_offsets_inside':True},
'populations':parsed['distributions'],'counts':parsed['role_counts'],'raw_QMP_matches':proof,
'interpretation':'Actual production PC coverage for allfive sites is established. Frequent token-equality/matchfalse/pending populations occur in this healthy calibration; equality alone does not identify freeze cause. Tokens span468..472 and finalstatus population includes4zero. No per-call conjunction is asserted.',
'limits':['Counts snapshots not invocations, unequal counts retained; no CPU/process/thread attribution or pairing.',
'Mode0 observed at mode site only, not propagated to other blocks.',
'pipeline_bf4_token is neutral offset label, not done/released fence; positive comparison precedes latch store.',
'Matchingfalse/true are conditional continuation subsets, and true cannot distinguish active versus queued.',
'Root owns visual advancing-clock validation; this register audit does not infer pixels from statuses.',
'One globally nochain-perturbed window, no performance/unperturbed scheduling claim.',
'Live prefixes after restore are labeled, not final stopped reports.']}
(p/'audit.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result['counts']))
