#!/usr/bin/env python3
"""Synthetic grammar/ordering fixtures only, not guest execution evidence."""
import hashlib,importlib.util,json
from pathlib import Path
source=Path(__file__).resolve().parents[2]/'warm-timing.py';s=importlib.util.spec_from_file_location('warm',source);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
b='11111111-2222-3333-4444-555555555555';rid='1'*32;lines=[]
lines.append('INFERNO_EVENT_PROCESS_IDENTITY pid=270 query_result=56 errno=0 uniqueid=999 idversion=1 source=original-libproc fallback=main-tick-and-pid')
for seq,(hook,tick) in enumerate(zip(['main','launch-delegate','window-request','appeared','active'],[101,102,103,105,108]),1):
 lines += [f'INFERNO_TIMING_RELAY_RAW source=guest-loopback record=INFERNO_TIMING_V1 {b} 270 {seq} {hook} {tick} 3 2',f'INFERNO_TIMING_RELAY_RECORD boot={b} pid=270 sequence={seq} hook={hook} ticks={tick} numer=3 denom=2 complete={int(seq==5)} source=guest-loopback claimed_pid_verified=1 peer_pid_authenticated=0']
for seq,hook in enumerate(['main','appeared','active'],1):
 lines += [f'INFERNO_EVENT_RELAY_RAW source=guest-loopback record=INFERNO_EVENT_V1 {b} 270 {seq} {hook} 0',f'INFERNO_EVENT_RELAY_RECORD boot={b} pid=270 sequence={seq} source=guest-loopback claimed_pid_verified=1 peer_pid_authenticated=0']
lines.append(f'INFERNO_LAUNCH_TIMING_V1 boot={b} pid=210 attempt=1 request_ticks=100 callback_ticks=104 numer=3 denom=2 accepted=1')
for seq,(hook,gen,tick) in enumerate([('active',0,108),('resign',0,140),('background',0,150),('foreground',1,210),('active',1,220)],1):
 lines += [f'INFERNO_LIFECYCLE_RELAY_RAW source=guest-loopback record=INFERNO_LIFECYCLE_V1 {b} 270 {seq} {gen} {hook} 101 {tick} 3 2',f'INFERNO_LIFECYCLE_RELAY_RECORD boot={b} pid=270 sequence={seq} generation={gen} hook={hook} main_ticks=101 ticks={tick} numer=3 denom=2 source=guest-loopback claimed_pid_verified=1 peer_pid_authenticated=0']
opening=f'INFERNO_OPEN_TIMING_V1 request_id={rid} boot={b} pid=300 request_ticks=200 callback_ticks=205 numer=3 denom=2 accepted=1';lines += [opening,'2026-10-06 12:00:00 inferno-launcher[300:1] '+opening]
raw=('\r\r\n'.join(lines)+'\r\r\n').encode();ok=m.parse(raw,rid)
assert ok['intervals']['open_to_active']['nanoseconds_numerator']==30 and ok['process_identity']['uniqueid']==999
fallback=m.parse(raw.replace(b'query_result=56 errno=0 uniqueid=999',b'query_result=0 errno=1 uniqueid=0'),rid);assert fallback['process_identity']['uniqueid'] is None
cases={'foreground_in_place':raw.replace(b'background',b'active'),'generation_mismatch':raw.replace(b'270 4 1 foreground',b'270 4 0 foreground'),'mixed_main_tick':raw.replace(b'foreground 101 210',b'foreground 102 210'),'duplicate_named_open':raw+(opening+'\n').encode(),'rejected_callback':raw.replace(b'callback_ticks=205 numer=3 denom=2 accepted=1',b'callback_ticks=205 numer=3 denom=2 accepted=0'),'identity_rejected':raw+b'INFERNO_EVENT_PROCESS_IDENTITY_REJECT pid=270 query_result=0 errno=1 uniqueid=0 idversion=0\n','missing_active':raw.replace((lines[-4]+'\r\r\n').encode(),b'')}
results=[]
for name,data in cases.items():
 try:m.parse(data,rid)
 except ValueError as e:results.append({'case':name,'rejected':str(e)})
 else:raise AssertionError(name)
result={'synthetic_only':True,'guest_execution':False,'parser_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'fixture_sha256':hashlib.sha256(raw).hexdigest(),'exact_open_to_active_ns':30,'denied_identity_explicit_fallback':fallback['process_identity']['scope'],'prefixed_NSLog_ignored':True,'malformed_cases':results}
Path(__file__).with_name('synthetic-results.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
