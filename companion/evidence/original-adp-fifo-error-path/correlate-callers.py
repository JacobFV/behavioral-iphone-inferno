#!/usr/bin/env python3
"""Correlate bounded ADP caller records with one attempt's original kernel slide.

No PC correction, PAC stripping, guest action, or Apple implementation copying.
Usage: correlate-callers.py --trace TRACE --stderr STDERR --kernel ORIGINAL --output JSON
"""
import argparse
import collections
import hashlib
import json
from pathlib import Path
import re

KERNEL_SHA256 = '524b91442ad73a225f8b86afbed26642fbc14a821647d972d3c52dfc4c431910'
CALLERS = {
    0xfffffff00975c19c: ('decompression_failure', {0x50184, 0x58184}),
    0xfffffff009746fe8: ('shadow_FIFO_empty', {0x45004}),
    0xfffffff0097453fc: ('interrupt_handler_ready_gate', {0x45004}),
}
EVENT = re.compile(rb'apple_adp_read_caller\b.*?offset=0x([0-9a-fA-F]+) cpu_present=([01]) cpu_index=(-?\d+) aarch64_valid=([01]) pc=0x([0-9a-fA-F]+) lr=0x([0-9a-fA-F]+)(?: x21=0x([0-9a-fA-F]+))?\s*$')
SLIDE = re.compile(rb'Kernel Virtual Slide:\s*(0x[0-9a-fA-F]+)')


def provenance(path, raw):
    return {'path': str(path.resolve()), 'bytes': len(raw),
            'sha256': hashlib.sha256(raw).hexdigest()}


def correlate(raw, slide):
    records, offset = [], 0
    for line_number, line in enumerate(raw.splitlines(keepends=True), 1):
        if b'apple_adp_read_caller' in line:
            match = EVENT.search(line)
            if not match:
                raise ValueError(f'malformed caller event at byte {offset}')
            address, present, index, valid, pc, lr, x21 = match.groups()
            x21 = int(x21, 16) if x21 is not None else None
            address, pc, lr = (int(x, 16) for x in (address, pc, lr))
            present, valid, index = int(present), int(valid), int(index)
            if address not in (0x45004, 0x50184, 0x58184):
                raise ValueError(f'out-of-scope offset at byte {offset}')
            if (not present and (valid or index != -1 or pc or lr)) or (valid and index < 0) or (not valid and (pc or lr or x21)):
                raise ValueError(f'inconsistent CPU validity at byte {offset}')
            normalized = (lr - slide) & ((1 << 64) - 1) if valid else None
            caller, allowed = CALLERS.get(normalized, ('unknown', set()))
            category = 'non_cpu' if not present else 'non_aarch64' if not valid else caller
            if valid and caller != 'unknown' and address not in allowed:
                category = 'known_lr_unexpected_register'
            records.append({'line': line_number, 'byte_offset': offset,
                            'byte_end': offset + len(line), 'raw': line.decode('ascii').rstrip('\r\n'),
                            'offset': hex(address), 'cpu_present': bool(present), 'cpu_index': index,
                            'aarch64_valid': bool(valid), 'exposed_pc': hex(pc), 'raw_lr': hex(lr),
                            'normalized_lr': hex(normalized) if normalized is not None else None,
                            'category': category, 'exposed_x21': hex(x21) if x21 is not None else None,
                            'handler_pending_bit10': bool(x21 & (1 << 10)) if category == 'interrupt_handler_ready_gate' and x21 is not None else None})
        offset += len(line)
    if not records:
        raise ValueError('no caller events; no execution correlation can be claimed')
    return {'records': records, 'counts': dict(collections.Counter(r['category'] for r in records)),
            'total': len(records)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('trace', 'stderr', 'kernel', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error('output already exists; preserve prior evidence')
    raw, stderr = args.trace.read_bytes(), args.stderr.read_bytes()
    with args.kernel.open('rb') as stream:
        kernel_hash = hashlib.file_digest(stream, 'sha256').hexdigest()
    if kernel_hash != KERNEL_SHA256:
        parser.error('original kernel SHA256 does not match audited image')
    slides = SLIDE.findall(stderr)
    if len(slides) != 1:
        parser.error('require exactly one kernel slide record from this attempt')
    slide = int(slides[0], 16)
    try:
        result = correlate(raw, slide)
    except ValueError as exc:
        parser.error(str(exc))
    result.update({'schema': 1, 'trace': provenance(args.trace, raw),
                   'stderr': provenance(args.stderr, stderr),
                   'original_kernel': {'path': str(args.kernel.resolve()), 'sha256': kernel_hash},
                   'kernel_virtual_slide': hex(slide),
                   'limitations': ['Caller supplies trace and stderr from the same attempt; hashes retain that selection, not independent pairing authentication.',
                                   'Exposed PC is not asserted to be the exact MMIO instruction; no CPU restore/synchronization was performed.',
                                   'Only slide subtraction is applied to LR; no guessed PAC stripping or unknown-address coercion.',
                                   'Known LR plus register is static caller correlation, not proof subsequent state gates or userland notification completed.',
                                   'shadow_FIFO_empty caller does not establish its command_mode boolean.',
                                   'x21 bit10 is interpreted only for the exact mapped handler LR/register; older records have unknown x21. Passing this next branch does not prove later completion gates.']})
    args.output.write_text(json.dumps(result, indent=2) + '\n')


if __name__ == '__main__':
    main()
