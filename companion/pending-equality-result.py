#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Offline independent mode/equality/match/status snapshots; no call pairing."""
import argparse
import collections
import hashlib
import importlib.util
import json
from pathlib import Path

PRODUCTION = {'accepted-mode': 0xfffffff0096f1bc0,
              'token-equality-predicate-true': 0xfffffff0096f1bf4,
              'matching-request-local-false': 0xfffffff0096f1e4c,
              'matching-request-local-true': 0xfffffff0096f1e50,
              'final-return': 0xfffffff0096e219c}
LABELS = dict(zip(PRODUCTION, ('probe_mode','probe_equal','probe_false','probe_true','probe_return')))
BASE = Path(__file__).with_name('evidence') / 'swapwait-cpu-parser/parse.py'
spec = importlib.util.spec_from_file_location('strict_cpu_blocks', BASE)
parser = importlib.util.module_from_spec(spec)
spec.loader.exec_module(parser)


def parse(data, pcs=PRODUCTION, scope='production-fixed-pending-equality'):
    result = parser.parse(data, 'kernel-zero-slide')
    result.update(mode=scope, expected_pcs={k:hex(v) for k,v in pcs.items()})
    roles = collections.Counter(); distributions = collections.Counter(); violations = []
    for block in result['blocks']:
        block.pop('abi_low32', None)
        pc = None if block['pc'] is None else int(block['pc'],16)
        role = next((k for k,v in pcs.items() if pc == v), 'unknown-pc')
        block['role'] = role; roles[role] += 1
        if not block['complete'] or role == 'unknown-pc':
            continue
        w = lambda name: int(block['registers'][name],16) & 0xffffffff
        if role == 'accepted-mode':
            fields = {'mode':w('X08')}; valid = fields['mode'] in (0,1,2)
        elif role == 'token-equality-predicate-true':
            fields = {'requested_token':w('X08'), 'pipeline_bf4_token':w('X09')}
            valid = fields['requested_token'] == fields['pipeline_bf4_token']
        elif role.startswith('matching-request-local-'):
            fields = {'matching_request_local':w('X08')}
            valid = fields['matching_request_local'] == int(role.endswith('-true'))
        else:
            fields = {'status':w('X00')}; valid = True
        if not valid:
            violations.append({'start':block['start'],'role':role,'reason':'Registers violate reviewed site semantics','fields':fields})
        block['observation'] = fields
        distributions[(role,json.dumps(fields,sort_keys=True))] += 1
    result['role_counts'] = dict(roles)
    result['unknown_pc_count'] = roles['unknown-pc']
    result['semantic_violations'] = violations
    result['distributions'] = [{'role':role,'fields':json.loads(fields),'snapshots':n}
                              for (role,fields),n in sorted(distributions.items())]
    result['base_parser_sha256'] = hashlib.sha256(BASE.read_bytes()).hexdigest()
    result['limitations'] = [
        'Independent snapshots, not invocation counts or CPU/process/thread identity; no pairing or count subtraction.',
        'Mode is typed only at accepted-mode; never propagated to other snapshots.',
        'Equality is the positive comparison before its local store, not observed latch lifetime or completion.',
        'pipeline_bf4_token is an offset label, not a done/released/reusable fence predicate.',
        'Matching local may represent active OR queued match; sites are conditional continuation subsets.',
        'Absence of sites is not proof of absent branches; production exact-PC TB coverage requires actual evidence.',
        'Unknown, malformed, truncated blocks and semantic violations retained. Full raw X values preserved.',
        'Zero-slide/build/filter/control and restoration provenance require separate verification; no guest memory reads.'
    ]
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--owned-fixture-report', type=Path)
    a = p.parse_args(); pcs = PRODUCTION; scope = 'production-fixed-pending-equality'
    if a.owned_fixture_report:
        fixture = json.loads(a.owned_fixture_report.read_text())
        pcs = {role:fixture['symbols'][label] for role,label in LABELS.items()}
        if fixture.get('profile') != 'pending-equality' or fixture['filter'] != ','.join(hex(v)+'+4' for v in pcs.values()):
            raise ValueError('Fixture profile/filter differs')
        scope = 'owned-relocated-fixture-not-production'
    result = parse(a.input.read_bytes(),pcs,scope)
    result['input_path'] = str(a.input.resolve())
    with a.output.open('x') as f:
        json.dump(result,f,indent=2); f.write('\n')
    print(json.dumps({k:result[k] for k in ('snapshot_count','complete_count','role_counts','unknown_pc_count','semantic_violations')}))


if __name__ == '__main__':
    main()
