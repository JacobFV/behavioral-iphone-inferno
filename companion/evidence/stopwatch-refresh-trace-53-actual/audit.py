#!/usr/bin/env python3
"""Recompute actual refresh cadence from raw bounded trace and QMP records."""
import pathlib,json,hashlib,collections
p=pathlib.Path(__file__).parent
for n,v in json.loads((p/'provenance.json').read_text())['files'].items():
 b=(p/n).read_bytes();assert len(b)==v['size']and hashlib.sha256(b).hexdigest()==v['sha256']
cps=[json.loads((p/n).read_text())['checkpoint']for n in ['trace-refresh-no-vnc-start.json','trace-refresh-no-vnc-end.json','trace-refresh-connected-end.json']];assert len({(c['device'],c['inode'])for c in cps})==1
b=(p/'guest-errors-prefix.log').read_bytes();assert len(b)==cps[-1]['size'];events=[];off=0
for l in b.splitlines(keepends=True):
 if l.startswith(b'apple_adp_'):
  f=l.decode().split();events.append((off,f[0],dict(x.split('=',1)for x in f[1:])))
 off+=len(l)
j=[json.loads(l)for l in(p/'display-trace-control-window.jsonl').read_text().splitlines()];assert j[-1]['all_disabled']and len(j[0]['events'])==7;q={};captures=[]
for l in(p/'qmp-window-excerpt.jsonl').read_text().splitlines():
 r=json.loads(l);x=json.loads(r['raw']);q[(r['direction'],x['id'])]=(r,x)
 if x.get('execute')=='screendump':captures.append({'time':r['time'],'id':x['id'],'filename':x['arguments']['filename']})
for r in j:
 if 'response'not in r:continue
 i=r['response']['id'];assert 'error'not in r['response']and q[('receive',i)][1]==r['response'];assert q[('send',i)][1]['arguments']=={'name':r['event'],'enable':r['stage']=='after-enable'}
regions=[]
for name,a,z in [('no_VNC',cps[0],cps[1]),('connected_checkpoint_interval',cps[1],cps[2])]:
 es=[e for e in events if a['size']<=e[0]<z['size']];c=collections.Counter(e[1]for e in es);active=False;cycles=0;out=[]
 for o,n,f in es:
  if n=='apple_adp_bh':
   if f['phase']=='enter':assert not active;active=True;out=[]
   else:assert active and out==[('0','drawn'),('1','disabled')];active=False;cycles+=1
  if n=='apple_adp_pipe':assert active;out.append((f['pipe'],f['outcome']))
 assert not active
 regions.append({'name':name,'bytes':[a['size'],z['size']],'host_checkpoint_seconds':z['monotonic_time']-a['monotonic_time'],'counts':dict(c),'complete_draw_cycles':cycles,'ordered_handshake_events':[e for e in es if e[1]in('apple_adp_output_ready','apple_adp_irq_write','apple_adp_submit','apple_adp_bh','apple_adp_pipe')]if name=='no_VNC'else[]})
assert regions[0]['complete_draw_cycles']==2 and regions[1]['complete_draw_cycles']==27
no_vnc_captures=[r for r in captures if cps[0]['wall_time']<=r['time']<=cps[1]['wall_time']];assert len(no_vnc_captures)==2
for r in captures:assert 'error'not in q[('receive',r['id'])][1]
v=json.loads((p/'connected-capture-report.json').read_text());assert not v['pointer_events']and not v['home_button_events'];inputs=[json.loads(l)for l in(p/'serial-input-transcript.jsonl').read_text().splitlines()];assert not any(cps[0]['wall_time']<=r['time']<=cps[-1]['wall_time']for r in inputs)
result={'regions':regions,'no_VNC_QMP_captures':no_vnc_captures,'all_window_QMP_captures':captures,'window_seconds':j[-1]['time']-j[0]['time'],'connected_first_requested_time':v['captures'][0]['requested_time'],'connected_first_received_time':v['captures'][0]['received_time'],'first_received_through_trace_stop_seconds':j[-1]['time']-v['captures'][0]['received_time'],'trace_disabled_time':j[-1]['time'],'connected_capture_count':len(v['captures']),'input_commands_during_checkpoint_intervals':0,'interpretation':['No-VNC53.874406s interval has two refresh-ready/ack/submit/draw/frameprocessed-ack sequences and exactly two periodic QMP captures. This agrees with refresh-driven rendering cadence; individual trace events lack timestamps, so correspondence is source-supported inference rather than event-time pairing.','After connection27complete draws and29ready events are visible. Only about6.09seconds from first received VNC frame to deadline are traced, not the full24.42second checkpoint interval or full15second observation. No cross-condition frame-rate benchmark is computed.','Trace stops midway through connected observation. Last captured stopwatch digits reflect untraced later updates; screenshots are not presentation-time samples.','There are no intervening serial input commands or VNC pointer/Home events in these retained intervals. Earlier explicit stopwatch resume establishes workload; connection itself changes refresh stimulation.','Unlike earlier stuck41/44/47, both no-viewer and connected53 windows have normal submit/draw responses. This supports capture-cadence explanation for stopwatch pictures, not a fix for no-submission failures or proof of guest monotonic-clock rate.']}
(p/'audit.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items()if k not in('regions','interpretation','all_window_QMP_captures')}));print([(r['name'],r['complete_draw_cycles'],r['host_checkpoint_seconds'])for r in regions])
