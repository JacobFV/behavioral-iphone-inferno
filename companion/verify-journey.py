#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Read-only verification of a stopped, operator-observed owned app journey."""
import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

UUID = r'[0-9A-Fa-f]{8}(?:-[0-9A-Fa-f]{4}){3}-[0-9A-Fa-f]{12}'
RAW = re.compile(rf'INFERNO_EVENT_RELAY_RAW source=guest-loopback record=INFERNO_EVENT_V1 ({UUID}) ([1-9][0-9]*) ([1-9][0-9]*) (main|appeared|tap) ([0-9]+)')
VALID = re.compile(rf'INFERNO_EVENT_RELAY_RECORD boot=({UUID}) pid=([1-9][0-9]*) sequence=([1-9][0-9]*) source=guest-loopback claimed_pid_verified=1 peer_pid_authenticated=0')

class Invalid(ValueError):
    pass

def require(condition, message):
    if not condition:
        raise Invalid(message)

def sha(data):
    return hashlib.sha256(data).hexdigest()

def unique(items, message):
    require(len(items) == 1, f'{message}: expected one, got {len(items)}')
    return items[0]

class Audit:
    def __init__(self, report, strict_prefix=None):
        self.strict_prefix = strict_prefix
        self.folder = report.resolve()
        self.sources = {}
        self.data = {}

    def read(self, name, limit=64*1024*1024):
        path = self.folder / name
        require(path.is_file(), f'missing source: {name}')
        require(path.stat().st_size <= limit, f'oversized source: {name}')
        data = path.read_bytes()
        self.sources[name] = {'path': str(path), 'bytes': len(data), 'sha256': sha(data)}
        self.data[name] = data
        return data

    def rows(self, name, structured=False):
        data = self.read(name)
        offset = 0
        result = []
        # LF splitting preserves real serial offsets with CRCRLF console endings.
        for number, line in enumerate(data.split(b'\n'), 1):
            if offset == len(data):
                break
            raw = line + (b'\n' if offset + len(line) < len(data) else b'')
            ref = {'source': name, 'line': number, 'byte_start': offset,
                   'byte_end': offset + len(raw), 'sha256': sha(raw)}
            text = line.rstrip(b'\r').decode('utf-8', errors='strict')
            result.append({'value': json.loads(text) if structured else text, 'reference': ref})
            offset += len(raw)
        return result

    @staticmethod
    def command(row):
        return json.loads(row['value']['raw'])

    def verify(self):
        report = json.loads(self.read('report.json'))
        journey = report.get('probe_journey', {})
        require(journey.get('completed') is True, 'strict journey incomplete')
        require(report.get('exit_code') == 0 and not report.get('error'), 'report is not a normal stopped run')
        require(journey.get('input_mode') == 'operator-observation' and journey.get('automatic_input') is False,
                'requires operator-observation journey')
        controls = self.rows('control-transcript.jsonl', True)
        inputs = self.rows('serial-input-transcript.jsonl', True)
        qmp = self.rows('qmp-transcript.jsonl', True)
        serial = self.rows('serial.log')
        serial_data = self.data['serial.log']
        arrivals = self.rows('event-arrivals/observations.jsonl', True) if (self.folder/'event-arrivals/observations.jsonl').exists() else None
        # This reviewed implementation gates before on appeared-present/tap-absent,
        # and after on tap-present, by reading the actual serial file.
        gate_sha = '1c4cbb542a79b85560433d62726123b99555ad0a47522d5ecd659faf3a04f308'
        require(report.get('probe_journey_source_sha256') == gate_sha, 'unreviewed journey gate source; verifier update required')
        for row in controls:
            v = row['value']
            require(sha(v['raw'].encode()) == v['sha256'], 'control payload hash mismatch')
        def control(name):
            return unique([r for r in controls if self.command(r).get('execute') == name], name)
        before, after = control('probe-capture-before'), control('probe-capture-after')
        for row in [before, after]:
            require(self.command(row).get('arguments') == {}, 'capture arguments must be empty')
        require(before['value'].get('response', {}).get('return', {}).get('state') == 'waiting-for-operator-tap-marker', 'before capture gate not accepted')
        require(after['value'].get('response', {}).get('return', {}).get('state') == 'completed', 'after capture did not complete')
        t0, t1 = before['value']['time'], after['value']['time']
        require(t0 < t1, 'capture command ordering invalid')
        gestures = [r for r in controls if t0 < r['value']['time'] < t1 and self.command(r).get('execute') in ('guest-hid-gesture', 'input-send-event', 'guest-open-app')]
        gesture = unique(gestures, 'intervening explicit app input')
        require(self.command(gesture)['execute'] == 'guest-hid-gesture', 'intervening input is not one HID tap')
        args = self.command(gesture)['arguments']
        require(set(args) == {'kind','x','y','duration_ms','request_id'} and args['kind'] == 'tap', 'requires exact bounded tap fields')
        rid = args['request_id']
        require(re.fullmatch(r'[0-9a-f]{32}', rid) is not None, 'invalid tap ID')
        for key, lo, hi in [('x',0,32767),('y',0,32767),('duration_ms',1,2000)]:
            require(type(args[key]) is int and lo <= args[key] <= hi, f'invalid {key}')
        sent = unique([r for r in inputs if r['value'].get('stage') == 'before-send' and r['value'].get('request_id') == rid], 'tap wire send')
        wire = f"INFERNO_HID_V1 {rid} TAP {args['x']} {args['y']} {args['duration_ms']}\n"
        require(sent['value']['raw'] == wire and sent['value']['sha256'] == sha(wire.encode()), 'tap wire differs from command')
        delivered = unique([r for r in inputs if r['value'].get('stage') == 'after-send' and r['value'].get('response',{}).get('request_id') == rid], 'tap send completion')
        response = delivered['value']['response']
        require(response.get('transmission') == 'written-to-serial-socket' and response.get('bytes_sent') == len(wire), 'incomplete tap transmission')
        require(t0 < sent['value']['time'] <= delivered['value']['time'] < t1, 'tap transmission ordering invalid')
        ack = unique([r for r in serial if re.fullmatch(rf'INFERNO_HID_ACK request_id={rid} attempt_status=0 delivery=unproven timestamp=[0-9]+',r['value'])], 'guest tap attempt acknowledgment')
        prefix_boundary = None
        prefix_manifest = None
        if self.strict_prefix is not None:
            prefix_manifest = json.loads(self.read(str(self.strict_prefix.resolve())))
            prefix_path = Path(prefix_manifest['serial_prefix_path'])
            require(prefix_path.is_absolute(), 'Strict prefix path must be absolute')
            prefix = self.read(str(prefix_path))
            require(len(prefix) == prefix_manifest['serial_prefix_bytes'] and sha(prefix) == prefix_manifest['serial_prefix_sha256'], 'Strict prefix size/hash mismatch')
            require(prefix.endswith(b'\n') and serial_data.startswith(prefix), 'Strict snapshot is not complete-line final serial prefix')
            begin, end = prefix_manifest['read_started_host_epoch'], prefix_manifest['captured_host_epoch']
            require(isinstance(begin,(int,float)) and isinstance(end,(int,float)) and t1 < begin <= end,
                    'Strict prefix was not captured after completed strict control')
            opens = [self.command(r) for r in controls if self.command(r).get('execute') == 'guest-open-app' and r['value']['time'] > t1]
            require(opens and all(end < r['created'] for r in opens), 'Strict prefix must precede every subsequent OPEN creation')
            prefix_boundary = len(prefix)
        records = []
        for row in serial:
            match = RAW.fullmatch(row['value'])
            if match:
                records.append((match.groups(), row))
        # Pair provenance before selecting chronology; later processes are never
        # excluded merely by taking the first matching line.
        candidates = []
        for fields, raw in records:
            event, count = fields[3:]
            if (event, count) not in [('main','0'), ('appeared','0'), ('tap','1')]:
                continue
            boot, pid, sequence = fields[:3]
            valid = unique([r for r in serial if VALID.fullmatch(r['value']) and VALID.fullmatch(r['value']).groups() == fields[:3]], f'{event} validated provenance')
            markers = [r for r in serial if r['value'] == f'INFERNO_UIKIT_PROBE_V1 event={event} count={count}'
                       and valid['reference']['byte_start'] < r['reference']['byte_start'] <= valid['reference']['byte_end'] + 1024]
            marker = unique(markers, f'{event} paired marker')
            require(raw['reference']['byte_end'] <= valid['reference']['byte_start'], f'{event} provenance ordering invalid')
            arrival = None
            if arrivals is not None:
                arrival = unique([r for r in arrivals if r['value']['byte_start'] == marker['reference']['byte_start']], f'{event} marker arrival')
                v = arrival['value']; fragment = serial_data[v['byte_start']:v['byte_end']]
                require(not v['preexisting'] and fragment.endswith(b'\n') and fragment[:-1].hex() == v['raw_hex'], f'{event} arrival raw reference mismatch/preexisting')
                require(sha(fragment[:-1]) == v['sha256'], f'{event} arrival hash mismatch')
            candidates.append({'event':event,'boot':boot,'pid':int(pid),'sequence':int(sequence),'raw':raw,'validated':valid,'marker':marker,'arrival':arrival})
        relevant_markers = [r for r in serial if r['value'] in {
            'INFERNO_UIKIT_PROBE_V1 event=main count=0',
            'INFERNO_UIKIT_PROBE_V1 event=appeared count=0',
            'INFERNO_UIKIT_PROBE_V1 event=tap count=1'}]
        require({r['reference']['byte_start'] for r in relevant_markers} ==
                {c['marker']['reference']['byte_start'] for c in candidates},
                'Unpaired lifecycle marker exists')
        chains = {}
        for event in ['main','appeared','tap']:
            matching = [c for c in candidates if c['event'] == event]
            if arrivals is not None:
                matching = [c for c in matching if
                            (t0 < c['arrival']['value']['observed_time'] < t1 if event == 'tap'
                             else c['arrival']['value']['observed_time'] < t0)]
            elif prefix_boundary is not None:
                matching = [c for c in matching if c['marker']['reference']['byte_end'] <= prefix_boundary]
            chains[event] = unique(matching, f'{event} strict chronology record')
        strict_identity = (chains['main']['boot'], chains['main']['pid'])
        later = [c for c in candidates if all(c is not selected for selected in chains.values())]
        for c in later:
            require((c['arrival']['value']['observed_time'] > t1 if arrivals is not None else
                     prefix_boundary is not None and c['raw']['reference']['byte_start'] >= prefix_boundary),
                    'Additional lifecycle record is not proven after strict capture')
            require(c['boot'] == strict_identity[0] and c['pid'] != strict_identity[1],
                    'Additional lifecycle record has wrong boot or duplicate strict PID')
            require(c['raw']['reference']['byte_start'] > chains['tap']['marker']['reference']['byte_end'],
                    'Additional lifecycle raw record precedes strict tap provenance')
        require(len({c['marker']['reference']['byte_start'] for c in candidates}) == len(candidates),
                'A marker is paired with multiple raw records')
        main, appeared, tap = [chains[k] for k in ['main','appeared','tap']]
        require(main['sequence'] == 1 and main['sequence'] < appeared['sequence'] < tap['sequence'], 'event sequence invalid')
        require(len({(c['boot'],c['pid']) for c in chains.values()}) == 1, 'mixed app identity')
        ready = unique([r for r in serial if r['value'].startswith(f"INFERNO_EVENT_RELAY_READY boot={main['boot']} ") and 'transport=tcp address=127.0.0.1 port=37373 ' in r['value']], 'relay ready')
        require(ready['reference']['byte_start'] < main['raw']['reference']['byte_start'], 'relay not ready before lifecycle')
        if arrivals is not None:
            require(appeared['arrival']['value']['observed_time'] < t0 < sent['value']['time'] < tap['arrival']['value']['observed_time'] < t1, 'host-observed strict chronology invalid')
        def exchange(execute, filename=None):
            req = unique([r for r in qmp if r['value']['direction']=='send' and self.command(r).get('execute')==execute and (filename is None or self.command(r).get('arguments',{}).get('filename')==filename)], f'QMP {execute} request')
            qid=self.command(req)['id']
            reply=unique([r for r in qmp if r['value']['direction']=='receive' and self.command(r).get('id')==qid], f'QMP {execute} reply')
            require(self.command(reply).get('return') == {} and req['reference']['byte_start'] < reply['reference']['byte_start'], f'QMP {execute} failed')
            return {'request':req,'reply':reply}
        captures=[]
        for role, controlrow in [('probe-before',before),('probe-after',after)]:
            data=self.read(role+'.ppm',32*1024*1024);header=re.match(rb'P6\s+(\d+)\s+(\d+)\s+255\s',data)
            require(header is not None, 'invalid PPM header');width,height=map(int,header.groups())
            require(0 < width <= 8192 and 0 < height <= 8192 and len(data)-header.end()==width*height*3, 'invalid PPM dimensions/payload')
            cap=journey.get('captures',{}).get(role,{})
            path=str(self.folder/(role+'.ppm'))
            require(cap.get('path')==path and cap.get('sha256')==sha(data) and cap.get('width')==width and cap.get('height')==height, 'capture metadata mismatch')
            ex=exchange('screendump',path)
            require(controlrow['value']['time'] <= ex['request']['value']['time'] <= ex['reply']['value']['time'], 'capture QMP chronology invalid')
            captures.append({'role':role,'width':width,'height':height,'sha256':sha(data),'qmp':ex})
        if arrivals is not None:
            require(all(c['arrival']['value']['observed_time'] > captures[1]['qmp']['reply']['value']['time'] for c in later),
                    'Additional lifecycle arrived before strict after-capture completed')
        if prefix_manifest is not None:
            require(captures[1]['qmp']['reply']['value']['time'] < prefix_manifest['read_started_host_epoch'],
                    'Strict prefix read started before after-capture QMP completion')
        require(captures[0]['qmp']['reply']['value']['time'] < sent['value']['time'], 'before frame completed after input')
        quit_exchange=exchange('quit')
        require(report.get('quit_response') == self.command(quit_exchange['reply']), 'reported quit response differs from raw QMP reply')
        shutdown=unique([r for r in qmp if r['value']['direction']=='receive' and self.command(r).get('event')=='SHUTDOWN'], 'QMP shutdown event')
        require(self.command(shutdown).get('data') == {'guest':False,'reason':'host-qmp-quit'}, 'shutdown is not host-qmp-quit')
        require(quit_exchange['request']['reference']['byte_start'] < shutdown['reference']['byte_start'], 'shutdown precedes quit request')
        require(captures[1]['qmp']['reply']['value']['time'] < quit_exchange['request']['value']['time'], 'quit precedes after capture')
        finish=[r for r in controls if self.command(r).get('execute')=='finish-run']
        if report.get('probe_run_control',{}).get('keep_running'):
            f=unique(finish,'finish-run');require(self.command(f).get('arguments')=={} and f['value'].get('response',{}).get('return',{}).get('finish_requested') is True,'finish-run not accepted')
            require(t1 < f['value']['time'] < quit_exchange['request']['value']['time'], 'finish-run ordering invalid')
        for name, source in self.sources.items():
            require(sha((self.folder/name).read_bytes()) == source['sha256'], f'source changed during verification: {name}')
        return {'status':'verified','chronology_basis':('raw observer arrival references plus source-gated capture commands' if arrivals is not None else ('source-gated capture plus independently retained serial prefix; no per-marker arrival time' if prefix_manifest is not None else 'source-gated capture commands; independent marker arrival times unavailable')),'reviewed_capture_gate_source_sha256':gate_sha,'boot_uuid':main['boot'],'app_pid':main['pid'],'relay_ready':ready,'events':chains,'strict_prefix_manifest':prefix_manifest,'post_strict_other_process_records':later,'before':before,'tap_command':gesture,'tap_wire':sent,'tap_wire_completion':delivered,'tap_attempt_ack':ack,'after':after,'captures':captures,'finish_run':finish,'quit':quit_exchange,'shutdown':shutdown,'exit_code':0}

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--report',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--strict-prefix',type=Path,help='independently retained completed strict serial prefix manifest');a=p.parse_args()
    if a.output.exists():p.error('output must be a new file')
    audit=Audit(a.report,a.strict_prefix)
    try:
        result=audit.verify();code=0
    except (Invalid,OSError,ValueError,KeyError,TypeError) as exc:
        result={'status':'rejected','reason':str(exc)};code=1
    result.update({'schema':'inferno.strict-journey-verification.v1','report':str(a.report.resolve()),'verifier_sha256':sha(Path(__file__).read_bytes()),'sources':audit.sources,'limits':['Read-only host verification of recorded guest lifecycle, explicit input and QMP captures.','Manual visual review remains separate; PPM hashes do not classify pixels.','Claimed app PID is verified by relay; TCP peer PID remains unauthenticated.','No disk preservation or backing-chain validation performed by this tool.','Host arrival ordering is observational, not intrinsic app latency.']})
    with a.output.open('x') as f:json.dump(result,f,indent=2);f.write('\n')
    print(json.dumps({'status':result['status'],'output':str(a.output),'reason':result.get('reason')}));return code

if __name__=='__main__':sys.exit(main())
