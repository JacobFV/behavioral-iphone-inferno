#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Opt-in two-tap sequence for reviewed Finish Setup overlay; no retry."""
import argparse
import hashlib
import importlib.util
import json
import os
import stat
from pathlib import Path
import re
import signal
import subprocess
import sys
import time

from PIL import Image
import qmp_control

HERE = Path(__file__).resolve().parent
SIZE = (832, 1792)
CROP = (0, 100, 832, 1400)  # Entire width; clock and owned debug footer excluded only.


def module(name, filename):
    spec = importlib.util.spec_from_file_location(name, HERE / filename)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


def sha(data):
    return hashlib.sha256(data).hexdigest()


def pixels(path):
    with Image.open(path) as im:
        if im.size != SIZE or im.mode != 'RGB':
            raise ValueError('Require original RGB832x1792 VNC frame; no resize/QMP normalization')
        return im.crop(CROP).tobytes()


def references(path, expected):
    raw = path.read_bytes()
    if sha(raw) != expected:
        raise ValueError('Reference manifest hash mismatch')
    manifest = json.loads(raw)
    if manifest['size'] != list(SIZE) or manifest['crop'] != list(CROP):
        raise ValueError('Unsupported reference crop or dimensions')
    refs = {'overlay': [], 'zero': []}
    for item in manifest['references']:
        p = Path(item['path'])
        if not p.is_absolute():
            p = path.parent / p
        if sha(p.read_bytes()) != item['sha256']:
            raise ValueError('Reference image hash mismatch')
        rgb = pixels(p)
        if sha(rgb) != item['crop_sha256']:
            raise ValueError('Reference RGB hash mismatch')
        refs[item['state']].append(rgb)
    if not all(refs.values()) or any(x in refs['zero'] for x in refs['overlay']):
        raise ValueError('Missing or ambiguous reference states')
    return refs


def classify(path, refs):
    rgb = pixels(path)
    found = [state for state, values in refs.items() if rgb in values]
    return found[0] if len(found) == 1 else 'unknown'


def identity(report, expected_boot):
    b = (report / 'serial.log').read_bytes()
    if len(b) > 64 * 1024 * 1024:
        raise ValueError('Serial evidence exceeds bound')
    lines = [x.rstrip(b'\r') for x in b.split(b'\n')]
    boots = re.findall(rb'^INFERNO_EVENT_RELAY_READY boot=([^ ]+)', b, re.M)
    if boots != [expected_boot.encode()]:
        raise ValueError('Current relay boot mismatch/ambiguity')
    if any(b'INFERNO_UIKIT_PROBE_V1 event=tap ' in x or b'INFERNO_EVENT_RELAY_REJECT' in x for x in lines):
        raise ValueError('Prior tap or rejected identity/event; unsupported initial journey')
    appeared = []
    pids = set()
    for i, line in enumerate(lines):
        m = re.fullmatch(rb'INFERNO_EVENT_RELAY_RAW source=guest-loopback record=INFERNO_EVENT_V1 ([A-Fa-f0-9-]{36}) ([0-9]+) ([0-9]+) ([a-z-]+) ([0-9]+)', line)
        if not m:
            if line.startswith(b'INFERNO_EVENT_RELAY_RAW'):
                raise ValueError('Malformed owned raw event')
            continue
        boot, pid, seq, hook, count = [x.decode() for x in m.groups()]
        pids.add(pid)
        if hook == 'tap':
            raise ValueError('A raw tap already exists')
        if boot != expected_boot:
            raise ValueError('Foreign-boot raw record')
        if hook == 'appeared' and count == '0':
            validation = f'INFERNO_EVENT_RELAY_RECORD boot={boot} pid={pid} sequence={seq} source=guest-loopback claimed_pid_verified=1 peer_pid_authenticated=0'.encode()
            tail = lines[i+1:i+12]
            marker = b'INFERNO_UIKIT_PROBE_V1 event=appeared count=0'
            if tail.count(validation)!=1 or tail.count(marker)!=1 or tail.index(validation)>=tail.index(marker):
                raise ValueError('Appearance lacks ordered matching validation then marker')
            if any(x.startswith(b'INFERNO_EVENT_RELAY_RAW') for x in tail[:tail.index(marker)]):
                raise ValueError('Another raw event interrupts appearance provenance')
            appeared.append({'boot': boot, 'pid': int(pid), 'sequence': int(seq)})
    if len(appeared) != 1 or len(pids) != 1:
        raise ValueError('Require one unambiguous initial owned incarnation')
    return {**appeared[0], 'serial_bytes': len(b), 'serial_sha256': sha(b),
            'scope': 'Original relay identity evidence, not a fresh host query of guest process liveness'}



def trace_disabled_evidence(report):
    """Conservative sole-runner journal proof; never opens another QMP socket."""
    evidence = {}
    rows = {}
    for name in ('display-trace-control.jsonl', 'qmp-transcript.jsonl'):
        path = report/name
        with path.open('rb') as stream:
            info = os.fstat(stream.fileno())
            if not stat.S_ISREG(info.st_mode) or info.st_size > 32*1024*1024:
                raise ValueError('Trace evidence must be bounded regular files')
            raw = stream.read(info.st_size)
        if not raw or not raw.endswith(b'\n'):
            raise ValueError('Incomplete trace journal prefix')
        rows[name] = [json.loads(x) for x in raw.split(b'\n') if x]
        evidence[name] = {'bytes':len(raw),'sha256':sha(raw),'inode':info.st_ino,'device':info.st_dev}
    journal = rows['display-trace-control.jsonl']
    if journal[-1].get('stage')!='stop-result' or journal[-1].get('all_disabled') is not True or journal[-1].get('pending')!=[]:
        raise ValueError('Runner trace journal does not confirm empty pending state')
    starts = [i for i,x in enumerate(journal) if x.get('stage')=='start']
    if not starts or journal[starts[-1]].get('events')!=list(qmp_control.DISPLAY_TRACE_EVENTS):
        raise ValueError('Missing exact nine-event runner trace lifecycle')
    disables = {}
    for row in journal[starts[-1]+1:]:
        if row.get('stage')=='after-disable':
            disables[row['event']] = row['response']
    if set(disables)!=set(qmp_control.DISPLAY_TRACE_EVENTS) or any('return' not in x or 'error' in x for x in disables.values()):
        raise ValueError('Missing successful runner disable responses')
    states, replies = {}, {}
    for row in rows['qmp-transcript.jsonl']:
        message = json.loads(row['raw'])
        if row['direction']=='send' and message.get('execute')=='trace-event-set-state':
            args = message['arguments']
            if args['name'] in qmp_control.DISPLAY_TRACE_EVENTS:
                states[args['name']] = {'id':message['id'],'enable':args['enable'],'time':row['time']}
        elif row['direction']=='receive' and 'id' in message:
            replies[message['id']] = message
    if set(states)!=set(qmp_control.DISPLAY_TRACE_EVENTS):
        raise ValueError('QMP transcript lacks all nine states')
    for name, state in states.items():
        reply = replies.get(state['id'],{})
        if state['enable'] is not False or reply != disables[name] or 'return' not in reply or 'error' in reply:
            raise ValueError('Latest QMP state not acknowledged disabled and bound to runner journal')
    if list((report/'control').glob('request-*.json')):
        raise ValueError('Concurrent/pending mailbox request; do not start guarded sequence')
    evidence.update(states=states, pending_state=journal[-1], observed_monotonic=time.monotonic(),
                    scope='Retained last-state proof under sole-runner/no concurrent operator controls; upcoming trace-start also rejects pending state')
    return evidence


def bounded_subprocess(argv, stdout, stderr, timeout):
    # Own a new process group: owned-control may itself spawn the mailbox CLI.
    child = subprocess.Popen(argv, stdout=stdout, stderr=stderr, start_new_session=True)
    try:
        return child.wait(timeout=timeout)
    except BaseException:
        try:
            os.killpg(child.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        try:
            child.wait(timeout=1)
        except subprocess.TimeoutExpired:
            pass
        # Even if the group leader exited, a mailbox grandchild may remain.
        try:
            os.killpg(child.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        child.wait(timeout=2)
        raise


class Sequence:
    def __init__(self, args):
        self.args = args
        self.report = args.report.resolve(strict=True)
        args.output.mkdir(mode=0o700, parents=True, exist_ok=False)
        self.out = args.output.resolve()
        self.log = {'started_wall': time.time(), 'started_monotonic': time.monotonic(),
                    'actions': [], 'captures': [], 'complete': False, 'scope': 'Two explicit taps at most; no replay, CPU, Home, OPEN, strict-after or finish.'}
        self.log['source_hashes'] = {n: sha((HERE/n).read_bytes()) for n in ('guarded-setup-counter.py','owned-control.py','qmp_control.py','vnc-control.py','probe_journey.py')}
        self.log['references_sha256'] = args.references_sha256
        self.client = None
        self.number = 0
        self.save()

    def save(self):
        (self.out / 'sequence.json').write_text(json.dumps(self.log, indent=2)+'\n')

    def command(self, name, arguments=None, timeout=6):
        # Existing mailbox client remains sole QMP owner. Killing a timed-out CLI
        # never retracts its possibly submitted request: abort, never retry.
        self.number += 1
        prefix = self.out / f'control-{self.number:02d}-{name}'
        argv = [sys.executable, str(HERE/'qmp_control.py'), '--report', str(self.report), name,
                '--arguments', json.dumps(arguments or {})]
        self.log['actions'].append({'command': argv, 'started_monotonic': time.monotonic()})
        self.save()
        with prefix.with_suffix('.stdout').open('wb') as stdout, prefix.with_suffix('.stderr').open('wb') as stderr:
            result = bounded_subprocess(argv, stdout, stderr, timeout)
        if result:
            raise ValueError('Control rejected; sequence aborted')
        answer = json.loads(prefix.with_suffix('.stdout').read_text())
        if 'error' in answer or 'rejected' in answer:
            raise ValueError('Control failed; sequence aborted')
        return answer

    def capture(self, label):
        p = self.out / (label+'.png')
        self.client.capture(p)
        self.save()
        return p

    def tap(self, name, x, y, deadline):
        argv = [sys.executable, str(HERE/'owned-control.py'), '--report', str(self.report),
                '--output', str(self.out/name), '--trace-checkpoints', '--send-deadline-monotonic', str(deadline), 'tap', str(x), str(y), '--duration-ms', '150']
        start = {'wall': time.time(), 'monotonic': time.monotonic()}
        self.log['actions'].append({'command': argv, 'anchor': start})
        self.save()
        with (self.out/(name+'.stdout')).open('wb') as stdout, (self.out/(name+'.stderr')).open('wb') as stderr:
            result = bounded_subprocess(argv, stdout, stderr, 4)
        if result:
            raise ValueError('Tap uncertain/rejected; do not retry')
        req = json.loads((self.out/name/'request.json').read_text())
        reply = json.loads((self.out/name/'stdout.txt').read_text())
        if reply.get('transmission') != 'written-to-serial-socket' or reply.get('request_id') != req['request_id']:
            raise ValueError('Tap transport uncertain; do not retry')
        entries = [json.loads(x) for x in (self.report/'serial-input-transcript.jsonl').read_text().splitlines()]
        sent = [x for x in entries if x.get('stage')=='before-send' and x.get('request_id')==req['request_id']]
        if len(sent) != 1:
            raise ValueError('Missing exact transmission timestamp')
        now_mono, now_wall = time.monotonic(), time.time()
        if abs((now_wall-start['wall'])-(now_mono-start['monotonic'])) > .05:
            raise ValueError('Host clock changed; timing untrustworthy')
        estimate = reply['write_begin_monotonic']
        if reply.get('send_deadline_monotonic') != deadline or estimate >= deadline:
            raise ValueError('Receiver did not confirm timely write start')
        if not start['monotonic'] <= estimate <= now_mono:
            raise ValueError('Transmission time outside local command bracket')
        return {'request_id': req['request_id'], 'send_wall': sent[0]['time'],
                'send_begin_monotonic': estimate, 'send_end_monotonic': reply['write_end_monotonic'],
                'send_deadline_monotonic': deadline, 'write_end_after_deadline': reply['write_end_after_deadline'],
                'clock_crosscheck_tolerance_seconds': .05}

    def ack(self, request_id):
        b = (self.report/'serial.log').read_bytes()
        pat = rb'^INFERNO_HID_ACK request_id=' + request_id.encode() + rb'[^\n]*'
        found = re.findall(pat, b, re.M)
        if len(found)>1:
            raise ValueError('Duplicate ACK')
        if found and re.search(rb'\battempt_status=0(?:\s|$)', found[0]) is None:
            raise ValueError('Guest rejected gesture')
        return bool(found)

    def run(self):
        refs = references(self.args.references.resolve(), self.args.references_sha256)
        current = json.loads((self.report/'report.json').read_text())
        if 'exit_code' in current or Path(current['control_mailbox']).resolve()!=self.report/'control':
            raise ValueError('Require active matching report/mailbox')
        cmd = json.loads((self.report/'command.json').read_text())
        proc = Path('/proc') / str(current['pid'])
        actual_cmd = [x.decode() for x in (proc/'cmdline').read_bytes().split(b'\0') if x]
        if actual_cmd != cmd or (proc/'exe').resolve() != Path(cmd[0]).resolve():
            raise ValueError('Active report PID does not own exact recorded emulator command')
        self.log['host_process_stat'] = (proc/'stat').read_text()
        endpoint = cmd[cmd.index('-vnc')+1]
        if not endpoint.startswith('unix:'):
            raise ValueError('Require private Unix VNC')
        socket_path = Path(endpoint[5:])
        qmp_endpoint = cmd[cmd.index('-qmp')+1].split(',')[0]
        if not qmp_endpoint.startswith('unix:') or Path(qmp_endpoint[5:]).parent != socket_path.parent or socket_path.name != 'vnc.sock':
            raise ValueError('VNC/QMP endpoints do not share recorded private namespace')
        parent = socket_path.parent
        if parent.resolve()!=parent or socket_path.resolve()!=socket_path:
            raise ValueError('Socket namespace aliases not permitted')
        parent_stat, socket_stat = parent.lstat(), socket_path.lstat()
        if not stat.S_ISDIR(parent_stat.st_mode) or stat.S_IMODE(parent_stat.st_mode)!=0o700 or parent_stat.st_uid!=os.getuid() or not stat.S_ISSOCK(socket_stat.st_mode) or socket_stat.st_uid!=os.getuid():
            raise ValueError('Socket/parent is not private and owned')
        self.log['endpoint'] = {'path':str(socket_path),'device':socket_stat.st_dev,'inode':socket_stat.st_ino,'host_pid':current['pid']}
        self.log['identity_before'] = identity(self.report, self.args.boot_uuid)
        status = self.command('probe-status')['return']
        if status['state']!='waiting-for-operator-before-capture' or status.get('automatic_input'):
            raise ValueError('Require unused operator probe-before gate')
        vnc = module('guarded_vnc', 'vnc-control.py')
        self.client = vnc.Client(Path(endpoint[5:]), self.log)
        if classify(self.capture('overlay-initial'), refs)!='overlay':
            raise ValueError('Initial frame differs from reviewed Finish Setup overlay')
        if len(qmp_control.DISPLAY_TRACE_EVENTS)!=9:
            raise ValueError('Unsupported trace tuple')
        self.log['all_traces_disabled_evidence'] = trace_disabled_evidence(self.report)
        self.save()
        self.log['trace_start_command_monotonic'] = time.monotonic()
        trace_reply = self.command('trace-display-window', {'seconds':60})
        if trace_reply.get('return',{}).get('seconds') != 60 or trace_reply['return'].get('events') != list(qmp_control.DISPLAY_TRACE_EVENTS):
            raise ValueError('Unexpected trace window response; no input')
        self.log['trace_reply'] = trace_reply
        # Existing runner guarantees finite deadline and CPU-window exclusion.
        trace_deadline = self.log['trace_start_command_monotonic'] + 60
        if classify(self.capture('overlay-pre-input'),refs)!='overlay':
            raise ValueError('Overlay changed before Not Now')
        if identity(self.report,self.args.boot_uuid)['pid'] != self.log['identity_before']['pid']:
            raise ValueError('Owned process changed before Not Now')
        if trace_deadline-time.monotonic()<50:
            raise TimeoutError('Trace coverage consumed before Not Now')
        notnow = self.tap('not-now',11028,18432,time.monotonic()+3)
        self.log['not_now'] = notnow
        target = notnow['send_begin_monotonic'] + self.args.delay_seconds
        self.log['counter_target_monotonic'] = target
        self.save()
        self.log['settling_observations'] = []
        for i in range(100):
            if time.monotonic() >= target-1:
                raise TimeoutError('Zero-frame/ACK gate missed target; no counter tap')
            state = classify(self.capture(f'poll-{i:03d}'),refs)
            self.log['settling_observations'].append({'frame':f'poll-{i:03d}.png','classification':state,'monotonic':time.monotonic()})
            self.log['settling_unknown_count'] = sum(x['classification']=='unknown' for x in self.log['settling_observations'])
            self.save()
            # Waiting is input-free: unknown animation may settle, but never
            # authorizes an action. Initial/final exact-match gates stay strict.
            if time.monotonic() >= target-1:
                raise TimeoutError('Settling frame arrived too late; no counter tap')
            if state=='zero' and self.ack(notnow['request_id']):
                break
            time.sleep(.1)
        else:
            raise TimeoutError('No matched zero frame')
        self.log['identity_before_counter'] = identity(self.report,self.args.boot_uuid)
        if self.log['identity_before_counter']['pid']!=self.log['identity_before']['pid']:
            raise ValueError('Owned process changed')
        self.log['probe_before'] = self.command('probe-capture-before',timeout=max(.1,target-time.monotonic()))
        # QMP828 capture is retained as-is; NEVER compared/resized to VNC832.
        if self.log['probe_before'].get('return',{}).get('state')!='waiting-for-operator-tap-marker':
            raise ValueError('Probe before gate failed')
        while time.monotonic()<target-.4:
            time.sleep(min(.05,target-.4-time.monotonic()))
        if classify(self.capture('zero-pre-counter'),refs)!='zero':
            raise ValueError('Zero frame changed before counter')
        if time.monotonic()>target+.5 or trace_deadline-time.monotonic()<35:
            raise TimeoutError('Missed counter target or insufficient trace coverage; no counter tap')
        while time.monotonic()<target:
            time.sleep(min(.01,target-time.monotonic()))
        if identity(self.report,self.args.boot_uuid)['pid'] != self.log['identity_before']['pid']:
            raise ValueError('Owned identity changed immediately before counter')
        if time.monotonic()>target+.5 or trace_deadline-time.monotonic()<35:
            raise TimeoutError('Final deadline check failed; no counter tap')
        self.log['counter'] = self.tap('counter',16384,20316,target+.5)
        self.save()
        self.log['actual_send_interval_seconds'] = self.log['counter']['send_begin_monotonic']-notnow['send_begin_monotonic']
        self.log['target_met_at_transmission'] = abs(self.log['actual_send_interval_seconds']-self.args.delay_seconds)<=.5
        end=time.monotonic()+30
        for i in range(100):
            if time.monotonic()>=end:break
            self.capture(f'after-{i:03d}')
            time.sleep(.5)
        self.log['counter_ack_observed'] = self.ack(self.log['counter']['request_id'])
        self.log['end_checkpoint'] = module('guarded_owned','owned-control.py').trace_checkpoint(self.report)
        self.log['complete'] = self.log['counter_ack_observed'] and self.log['target_met_at_transmission']
        self.log['trace_coverage_conservative_end'] = trace_deadline
        self.log['observation_finished_within_trace_deadline'] = time.monotonic() <= trace_deadline
        self.log['visual_outcome'] = 'Unasserted; root reviews retained full frames'
        if not self.log['observation_finished_within_trace_deadline']:
            self.log['complete'] = False
        if not self.log['complete']:
            raise ValueError('ACK, actual send deadline or trace coverage incomplete; no retry')


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--references',type=Path,required=True)
    ap.add_argument('--references-sha256',required=True)
    sub=ap.add_subparsers(dest='mode',required=True)
    replay=sub.add_parser('replay');replay.add_argument('frames',type=Path,nargs='+')
    run=sub.add_parser('execute-reviewed');run.add_argument('--report',type=Path,required=True);run.add_argument('--output',type=Path,required=True);run.add_argument('--boot-uuid',required=True);run.add_argument('--delay-seconds',type=float,default=10)
    args=ap.parse_args()
    if args.mode=='replay':
        refs=references(args.references.resolve(),args.references_sha256)
        print(json.dumps([{'path':str(p),'sha256':sha(p.read_bytes()),'state':classify(p,refs)} for p in args.frames],indent=2));return 0
    if not 8<=args.delay_seconds<=12 or not re.fullmatch(r'[A-Fa-f0-9-]{36}',args.boot_uuid):
        ap.error('Require bounded8..12s target and explicit boot UUID')
    seq=Sequence(args)
    try:seq.run()
    except Exception as exc:
        seq.log['error']=f'{type(exc).__name__}: {exc}'
        return 1
    finally:
        if seq.client:seq.client.sock.close()
        seq.log['finished_wall']=time.time();seq.log['finished_monotonic']=time.monotonic();seq.save()
    return 0


if __name__=='__main__':
    raise SystemExit(main())
