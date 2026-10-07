#!/usr/bin/env python3
"""Exercise actual private mailbox files; no emulator or guest is involved."""
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import time
from types import SimpleNamespace

repo = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(repo / 'companion'))
import qmp_control as q


class NoQMP:
    def execute(self, *args):
        raise AssertionError('Termination request must not execute QMP inside mailbox poll')


results = []
with tempfile.TemporaryDirectory(prefix='inferno-finish-observation-') as temporary:
    for index, (completed, command, accepted) in enumerate([
        (None, 'finish-observation', True),
        (False, 'finish-observation', False),
        (True, 'finish-observation', False),
        (None, 'finish-run', False),
        (False, 'finish-run', False),
        (True, 'finish-run', True),
    ]):
        output = Path(temporary) / str(index)
        output.mkdir(mode=0o700)
        journey = None if completed is None else SimpleNamespace(report={'completed': completed})
        mailbox = q.ControlMailbox(output, journey=journey, keep_running=journey is not None)
        name = 'request-' + ('%032x' % index) + '.json'
        q.write_private(mailbox.path / name, {'execute': command, 'arguments': {}, 'created': time.time()})
        mailbox.poll(NoQMP())
        response = json.loads((mailbox.path / name.replace('request-', 'reply-')).read_text())
        assert ('return' in response) == accepted
        assert mailbox.run_control['finish_requested'] == accepted
        results.append({'probe_completed': completed, 'command': command, 'response': response})
print(json.dumps({'scope': __doc__, 'control_sha256': hashlib.sha256((repo / 'companion/qmp_control.py').read_bytes()).hexdigest(), 'cases': results}, indent=2))
