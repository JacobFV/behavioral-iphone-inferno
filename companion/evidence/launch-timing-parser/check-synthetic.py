#!/usr/bin/env python3
"""Small synthetic grammar checks only; no guest performance evidence."""
import importlib.util,json,hashlib
from pathlib import Path
source=Path(__file__).resolve().parents[2]/'launch-timing.py'
spec=importlib.util.spec_from_file_location('timing',source);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
boot='11111111-2222-3333-4444-555555555555';lines=[]
for seq,(hook,ticks) in enumerate(zip(['main','launch-delegate','window-request','appeared','active'],[101,102,103,105,108]),1):
 lines += [f'INFERNO_TIMING_RELAY_RAW source=guest-loopback record=INFERNO_TIMING_V1 {boot} 270 {seq} {hook} {ticks} 3 2',f'INFERNO_TIMING_RELAY_RECORD boot={boot} pid=270 sequence={seq} hook={hook} ticks={ticks} numer=3 denom=2 complete={int(seq==5)} source=guest-loopback claimed_pid_verified=1 peer_pid_authenticated=0']
for seq,hook in enumerate(['main','appeared','active'],1):
 lines += [f'INFERNO_EVENT_RELAY_RAW source=guest-loopback record=INFERNO_EVENT_V1 {boot} 270 {seq} {hook} 0',f'INFERNO_EVENT_RELAY_RECORD boot={boot} pid=270 sequence={seq} source=guest-loopback claimed_pid_verified=1 peer_pid_authenticated=0']
launch=f'INFERNO_LAUNCH_TIMING_V1 boot={boot} pid=210 attempt=1 request_ticks=100 callback_ticks=104 numer=3 denom=2 accepted=1';lines.append(launch)
raw=('\r\r\n'.join(lines)+'\r\r\n').encode();valid=m.parse(raw)
# The actual launcher also emits a timestamp/process-prefixed NSLog copy.
assert m.parse(raw+('2026-10-06 12:00:00 inferno-launcher[210:1] '+launch+'\n').encode())==valid
assert valid['intervals']['request_to_main']['nanoseconds_numerator']==3 and valid['intervals']['request_to_main']['nanoseconds_denominator']==2
for item in valid['hooks']:
 for key in ['raw','validated']:
  r=item[key];assert hashlib.sha256(raw[r['byte_start']:r['byte_end']]).hexdigest()==r['sha256']
cases={'partial_last_line':raw[:-1], 'missing_hook':raw.replace((lines[8]+'\r\r\n').encode(),b''),'duplicate_sequence':raw.replace(b'270 2 launch-delegate',b'270 1 launch-delegate'),'mixed_timebase':raw.replace(b'270 2 launch-delegate 102 3 2',b'270 2 launch-delegate 102 4 2'),'decreasing_ticks':raw.replace(b'270 2 launch-delegate 102',b'270 2 launch-delegate 99'),'unknown_hook':raw.replace(b'launch-delegate',b'unknown-hook'),'missing_provenance':raw.replace((lines[1]+'\r\r\n').encode(),b''),'ambiguous_request':raw+(launch.replace('attempt=1','attempt=2')+'\n').encode(),'request_after_main':raw.replace(b'request_ticks=100',b'request_ticks=102'),'missing_lifecycle':raw.replace((lines[10]+'\r\r\n').encode(),b'')}
results=[]
for name,data in cases.items():
 try:m.parse(data)
 except m.TimingError as exc:results.append({'case':name,'rejected':str(exc)})
 else:raise AssertionError(name+' incorrectly accepted')
result={'synthetic_only':True,'guest_execution':False,'parser_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'positive_fixture_sha256':hashlib.sha256(raw).hexdigest(),'exact_request_to_main_nanoseconds':'3/2','CR_CR_LF_raw_offsets_verified':True,'malformed_cases':results}
Path(__file__).with_name('synthetic-results.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result))
