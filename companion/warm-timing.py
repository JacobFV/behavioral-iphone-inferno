#!/usr/bin/env python3
"""One explicitly named background-to-foreground trial using captured guest ticks.
SPDX-License-Identifier: AGPL-3.0-or-later
This is not native-device performance or a cleared-cache/cold-launch measurement.
"""
import argparse
from fractions import Fraction
import hashlib
import importlib.util
import json
from pathlib import Path
import re

spec = importlib.util.spec_from_file_location('launch_timing', Path(__file__).with_name('launch-timing.py'))
initial = importlib.util.module_from_spec(spec)
spec.loader.exec_module(initial)
require = initial.require
UUID, N = initial.UUID, initial.NUM
RID = r'[0-9a-f]{32}'
OPEN = re.compile(rf'INFERNO_OPEN_TIMING_V1 request_id=({RID}) boot=({UUID}) pid=({N}) request_ticks=({N}) callback_ticks=({N}) numer=({N}) denom=({N}) accepted=([01])')
RAW = re.compile(rf'INFERNO_LIFECYCLE_RELAY_RAW source=guest-loopback record=INFERNO_LIFECYCLE_V1 ({UUID}) ({N}) ({N}) ({N}) ([a-z-]+) ({N}) ({N}) ({N}) ({N})')
VALID = re.compile(rf'INFERNO_LIFECYCLE_RELAY_RECORD boot=({UUID}) pid=({N}) sequence=({N}) generation=({N}) hook=([a-z-]+) main_ticks=({N}) ticks=({N}) numer=({N}) denom=({N}) source=guest-loopback claimed_pid_verified=1 peer_pid_authenticated=0')
IDENTITY = re.compile(rf'INFERNO_EVENT_PROCESS_IDENTITY pid=({N}) query_result=(-?{N}) errno=({N}) uniqueid=({N}) idversion=(-?{N}) source=original-libproc fallback=main-tick-and-pid')

def rows(data):
    offset = 0
    for line, fragment in enumerate(data.split(b'\n'), 1):
        if not fragment and offset == len(data):
            break
        raw = fragment + (b'\n' if offset + len(fragment) < len(data) else b'')
        yield raw, {'line': line, 'byte_start': offset, 'byte_end': offset+len(raw), 'sha256': initial.sha(raw), 'text': raw.rstrip(b'\r\n').decode('utf8', errors='replace')}
        offset += len(raw)

def parse(data, request_id):
    require(re.fullmatch(RID, request_id) is not None, 'request-id must be 32 lowercase hex characters')
    first = initial.parse(data)
    groups = {key: [] for key in ('open', 'raw', 'valid', 'identity')}
    rejects = []
    for raw, ref in rows(data):
        text = ref['text']
        if text.startswith('INFERNO_EVENT_PROCESS_IDENTITY_REJECT '):
            rejects.append(ref)
        for prefix, pattern, key in [('INFERNO_OPEN_TIMING_V1', OPEN, 'open'), ('INFERNO_LIFECYCLE_RELAY_RAW', RAW, 'raw'), ('INFERNO_LIFECYCLE_RELAY_RECORD', VALID, 'valid'), ('INFERNO_EVENT_PROCESS_IDENTITY ', IDENTITY, 'identity')]:
            if text.startswith(prefix):
                match = pattern.fullmatch(text)
                require(raw.endswith(b'\n') and match is not None, f'Malformed or partial {prefix} at byte {ref["byte_start"]}')
                numeric_fields = match.groups()[1:] if key == 'open' else match.groups()
                require(all(len(x) <= 20 for x in numeric_fields if re.fullmatch('-?[0-9]+', x)), 'Oversized numeric field')
                groups[key].append((match.groups(), ref))
    selected = [(x,r) for x,r in groups['open'] if x[0] == request_id]
    require(len(selected) == 1, f'Expected exactly one OPEN timing for named request; found {len(selected)}')
    fields, open_ref = selected[0]
    _, boot, launcher, request, callback, numer, denom, accepted = fields
    launcher, request, callback, numer, denom = map(int, (launcher, request, callback, numer, denom))
    require(accepted == '1', 'Named OPEN callback was not accepted')
    require(0 < launcher <= 2147483647 and 0 < request <= callback <= 2**64-1, 'Invalid OPEN PID/tick range')
    require((boot,numer,denom) == (first['boot_uuid'],first['timebase']['numer'],first['timebase']['denom']), 'OPEN boot/timebase mismatch')
    main = next(x['ticks'] for x in first['hooks'] if x['hook'] == 'main')
    pid = first['app_pid']
    require(request >= main, 'OPEN precedes original app incarnation')
    require(bool(groups['raw']) and len(groups['raw']) == len(groups['valid']) <= 40, 'Missing, partial or oversized lifecycle sequence')
    lifecycle = []; generation = 0; previous = main
    for sequence, (fields, ref) in enumerate(groups['raw'], 1):
        lb, lp, seq, gen, hook, mt, tick, ln, ld = fields
        lp,seq,gen,mt,tick,ln,ld = map(int,(lp,seq,gen,mt,tick,ln,ld))
        require((lb,lp,mt,ln,ld)==(boot,pid,main,numer,denom), 'Mixed lifecycle boot/PID/main-tick/timebase')
        require(seq == sequence and hook in {'active','resign','background','foreground'}, 'Invalid lifecycle sequence/hook')
        require(previous <= tick <= 2**64-1, 'Lifecycle ticks decrease or overflow'); previous = tick
        if hook == 'foreground':
            generation += 1
        require(gen == generation and gen <= 8, 'Lifecycle generation mismatch')
        matches = [(f,r) for f,r in groups['valid'] if f == fields]
        require(len(matches)==1 and matches[0][1]['byte_start']>ref['byte_start'], 'Missing or ambiguous lifecycle validation')
        lifecycle.append({'sequence':seq,'generation':gen,'hook':hook,'ticks':tick,'raw':ref,'validated':matches[0][1]})
    before = [x for x in lifecycle if x['ticks'] < request]
    following = [x for x in lifecycle if x['ticks'] >= request]
    require(bool(before) and before[-1]['hook']=='background', 'App was not demonstrably backgrounded immediately before OPEN; foreground-in-place is not warm resume')
    require(len(following)>=2 and [x['hook'] for x in following[:2]]==['foreground','active'], 'Missing next foreground/active pair or intervening lifecycle event')
    background = before[-1]; foreground, active = following[:2]
    require(foreground['generation']==active['generation']==background['generation']+1, 'Trial generation does not match background-to-foreground transition')
    for other,_ in groups['open']:
        if other[0] != request_id:
            require(not background['ticks'] <= int(other[3]) <= active['ticks'], 'Another OPEN overlaps the named lifecycle interval')
    require(not any(re.search(rf'\bpid={pid}\b',r['text']) for r in rejects), 'Original process-incarnation check rejected the timed PID')
    identities = [(f,r) for f,r in groups['identity'] if int(f[0])==pid]
    require(len(identities)==1, 'Missing or ambiguous original process identity observation')
    identity, identity_ref = identities[0]; query, error, unique, version = map(int,identity[1:])
    require(0<=unique<=2**64-1, 'Invalid process unique ID')
    strong = query==56 and unique!=0 and error==0
    def delta(a,b):
        value=Fraction((b-a)*numer,denom)
        return {'delta_ticks':b-a,'nanoseconds_numerator':value.numerator,'nanoseconds_denominator':value.denominator,'milliseconds_approximate':float(value/1000000)}
    return {'status':'complete','request_id':request_id,'boot_uuid':boot,'app_pid':pid,'main_ticks':main,'generation':foreground['generation'],'timebase':{'numer':numer,'denom':denom},'initial_launch':first,'open':{'launcher_pid':launcher,'request_ticks':request,'callback_ticks':callback,'reference':open_ref},'background':background,'foreground':foreground,'active':active,'process_identity':{'scope':'original-libproc incarnation corroborated' if strong else 'PID/main-tick continuity only; kernel incarnation unavailable','query_result':query,'errno':error,'uniqueid':unique if strong else None,'idversion':version if strong else None,'reference':identity_ref,'no_identity_rejection_observed':True},'intervals':{'background_to_open':delta(background['ticks'],request),'open_to_foreground':delta(request,foreground['ticks']),'open_to_active':delta(request,active['ticks']),'open_to_callback':delta(request,callback)}}

def host_match(report, result):
    paths=[report/'control-transcript.jsonl',report/'serial-input-transcript.jsonl']
    if not all(p.exists() for p in paths):
        return {'scope':'host request transcripts unavailable; no host ordering or transport claim'}
    parsed=[]; sources={}
    for path in paths:
        data=path.read_bytes();sources[str(path)]={'sha256':initial.sha(data),'bytes':len(data)}
        parsed.append([(json.loads(raw),ref) for raw,ref in rows(data)])
    rid=result['request_id'];boot=result['boot_uuid']
    controls=[(x,r) for x,r in parsed[0] if json.loads(x['raw']).get('execute')=='guest-open-app' and json.loads(x['raw']).get('arguments',{}).get('request_id')==rid]
    require(len(controls)==1,'Missing or duplicate named host OPEN request')
    control,cref=controls[0];args=json.loads(control['raw'])['arguments']
    require(args=={'request_id':rid,'boot_uuid':boot},'Host OPEN boot/fields mismatch')
    sends=[(x,r) for x,r in parsed[1] if x.get('stage')=='before-send' and x.get('request_id')==rid]
    require(len(sends)==1,'Missing or duplicate serial OPEN send')
    send,sref=sends[0];require(send['raw']==f'INFERNO_OPEN_V1 {rid} {boot}\n','Host serial wire mismatch')
    require(initial.sha(send['raw'].encode())==send['sha256'],'Host serial wire hash mismatch')
    require(control['time']<=send['time'],'Host control/send order mismatch')
    return {'scope':'exact named explicit host request and serial wire matched; not an intrinsic guest timing source','sources':sources,'control':cref,'serial_before_send':sref}

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--report',type=Path,required=True);p.add_argument('--request-id',required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    result={'kind':'owned_guest_background_resume_timing','source_sha256':{n:initial.sha(Path(__file__).with_name(n).read_bytes()) for n in ['warm-timing.py','launch-timing.py']},'limits':['Guest-emulated captured clock, not native-device timing.','No cold/cleared-cache claim; genuine background followed by named OPEN and foreground/active is required.','Host arrivals never replace guest ticks.','Visual Home/app continuity must be reviewed separately.','TCP peer PID is not authenticated.']}
    try:
        with (a.report/'serial.log').open('rb') as f:data=f.read(initial.LIMIT+1)
        require(len(data)<=initial.LIMIT,'Serial exceeds16MiB bound')
        result['serial']={'path':str((a.report/'serial.log').resolve()),'bytes':len(data),'sha256':initial.sha(data)}
        result.update(parse(data,a.request_id));result['host_request']=host_match(a.report,result);code=0
    except (OSError,ValueError,KeyError,TypeError) as exc:result.update(status='rejected',reason=str(exc));code=2
    a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'status':result['status'],'reason':result.get('reason'),'output':str(a.output)}));return code

if __name__=='__main__':raise SystemExit(main())
