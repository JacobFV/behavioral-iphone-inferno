#!/usr/bin/env python3
"""Offline AArch64 CPU snapshots; no invocation, pairing or identity inference."""
import argparse
import collections
import hashlib
import json
import pathlib
import re

PCS = {
    'kernel-zero-slide': (0xfffffff0096df690, 0xfffffff0096e219c),
    'owned-attempt-6': (0x40200024, 0x4020000c),
}
TOKEN = re.compile(rb'(?<!\S)(PC|X\d{2}|SP)=([0-9a-fA-F]{16})(?!\S)')
START = re.compile(rb'^\s*PC=')
FRAGMENT = re.compile(rb'^\s*(?:X\d{2}=|SP=|PSTATE=)')


def parse(data, mode):
    entry, final = PCS[mode]
    lines, pos = [], 0
    for line in data.splitlines(keepends=True):
        lines.append((pos, line))
        pos += len(line)
    blocks, orphans, active = [], [], []

    def finish(reason):
        nonlocal active
        if not active:
            return
        raw = b''.join(x[1] for x in active)
        pairs = TOKEN.findall(raw)
        counts = collections.Counter(k.decode() for k, _ in pairs)
        values = {k.decode(): int(v, 16) for k, v in pairs}
        required = ['PC'] + [f'X{i:02d}' for i in range(31)] + ['SP']
        errors = []
        if any(counts[k] != 1 for k in required) or set(counts) != set(required):
            errors.append('missing, duplicate or unexpected register')
        # Verify exact line layout emitted by aarch64_cpu_dump_state, not just tokens.
        names = [['PC', 'X00', 'X01']] + [[f'X{i:02d}' for i in range(n, n+3)] for n in range(2, 29, 3)] + [['X29', 'X30', 'SP']]
        if len(active) != 12:
            errors.append('incomplete or unexpected line count')
        for i, keys in enumerate(names):
            if i >= len(active):
                break
            pattern = rb'\s*' + rb'\s+'.join(k.encode()+rb'=[0-9a-fA-F]{16}' for k in keys) + rb'\s*'
            if re.fullmatch(pattern, active[i][1]) is None:
                errors.append(f'malformed register line {i}')
        if not re.fullmatch(rb'PSTATE=[0-9a-fA-F]{8}[^\r\n]*\r?\n', active[-1][1]):
            errors.append('missing or unterminated PSTATE footer')
        pc = values.get('PC')
        role = 'entry' if pc == entry else 'final-return' if pc == final else 'unknown-pc'
        item = {'start': active[0][0], 'end': active[-1][0]+len(active[-1][1]),
                'raw_sha256': hashlib.sha256(raw).hexdigest(), 'raw_text': raw.decode('ascii', 'backslashreplace'),
                'termination': reason, 'errors': errors, 'complete': not errors,
                'pc': None if pc is None else f'0x{pc:016x}', 'role': role,
                'registers': {k: f'0x{v:016x}' for k, v in values.items()}}
        if not errors and role == 'entry':
            item['abi_low32'] = {name: values[reg] & 0xffffffff for name, reg in [('token','X01'),('flags','X02'),('third','X03')]}
        elif not errors and role == 'final-return':
            item['abi_low32'] = {'status': values['X00'] & 0xffffffff}
        blocks.append(item)
        active = []

    for offset, line in lines:
        if START.match(line):
            finish('next PC before footer')
            active = [(offset, line)]
        elif active:
            if FRAGMENT.match(line):
                active.append((offset, line))
                if line.startswith(b'PSTATE='):
                    finish('PSTATE footer')
            else:
                active.append((offset, line))
                finish('interrupted by non-CPU line (retained)')
        elif FRAGMENT.match(line):
            orphans.append({'start': offset, 'end': offset+len(line), 'raw_text': line.decode('ascii','backslashreplace')})
    finish('end of input')
    distribution = collections.Counter()
    for b in blocks:
        if b['complete'] and 'abi_low32' in b:
            distribution[(b['role'], json.dumps(b['abi_low32'], sort_keys=True))] += 1
    return {'schema': 1, 'mode': mode, 'input_bytes': len(data), 'input_sha256': hashlib.sha256(data).hexdigest(),
            'expected_pcs': {'entry': hex(entry), 'final-return': hex(final)},
            'snapshot_count': len(blocks), 'complete_count': sum(b['complete'] for b in blocks),
            'exact_pc_counts': dict(collections.Counter(b['pc'] for b in blocks)),
            'unknown_pc_count': sum(b['role']=='unknown-pc' for b in blocks),
            'orphan_fragments': orphans,
            'distributions': [{'role': k[0], 'abi_low32': json.loads(k[1]), 'snapshots': n} for k,n in sorted(distribution.items())],
            'blocks': blocks,
            'limitations': ['Counts are snapshots, not invocations; no CPU, process or thread attribution and no entry/return pairing.',
                            'Kernel interpretation requires independently verified same-attempt zero kernel slide and pinned original ABI. This parser does not establish either.',
                            'Exact observed PC is required for ABI interpretation; unknown PCs and malformed/truncated blocks are retained.',
                            'Raw offsets refer to supplied bytes. Logging windows, filter provenance and mask restoration require separate control evidence.']}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--input', required=True, type=pathlib.Path)
    ap.add_argument('--mode', required=True, choices=PCS)
    ap.add_argument('--output', required=True, type=pathlib.Path)
    args = ap.parse_args()
    result = parse(args.input.read_bytes(), args.mode)
    result['input_path'] = str(args.input.resolve())
    with args.output.open('x') as f:
        json.dump(result, f, indent=2)
        f.write('\n')

if __name__ == '__main__':
    main()
