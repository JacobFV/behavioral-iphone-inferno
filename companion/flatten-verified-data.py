#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Flatten one stopped, raw-log-verified Data stage; no VM or filesystem resize."""
import argparse
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import signal
import stat
import struct
import subprocess
import sys
import time
import zlib
import disk_overlay as OV
from initial_volumes import bounded_record, ORIGINAL_ROOT_SHA, verify_content as initial_content
from data_seed import verify_content as seed_content
from data_verify import verify_content as data_content

SOURCE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('flatten_support', SOURCE / 'stage-import.py')
CO = importlib.util.module_from_spec(spec); spec.loader.exec_module(CO)
sha = CO.digest
PHASES = (
    ('inferno.initial-volumes-stage.v1', 'initial-volumes-prepared', initial_content, 2),
    ('inferno.seeded-data-stage.v1', 'seeded-not-byteverified', seed_content, 3),
    ('inferno.data-verified-stage.v1', 'data-verified', data_content, 4),
)


def pin(path, expected, pins):
    path = Path(path).absolute()
    if path.resolve(strict=True) != path or path.is_symlink() or not path.is_file() or sha(path) != expected:
        raise ValueError('Missing/aliased/changed pinned artifact: ' + str(path))
    pins[str(path)] = expected
    return path


def unchanged(pins):
    for p, expected in pins.items():
        if sha(p) != expected:
            raise ValueError('Pinned source/evidence changed: ' + p)


def source_pins():
    paths, _ = CO.source_inventory()
    paths += [Path(__file__), SOURCE / 'initial_volumes.py', SOURCE / 'data_seed.py', SOURCE / 'data_verify.py',
              *[SOURCE / 'native-probe' / name for name in ('prepare-root.c', 'imported-app.c', 'libSystem.tbd', 'entitlements.plist')]]
    return {str(p.resolve()): sha(p) for p in paths}


def validate_phase(path, expected, index, pins, seen=None):
    """Replay every phase's pinned raw completion, normal finish and frozen identities."""
    seen = set() if seen is None else seen
    path = pin(path, expected, pins)
    if str(path) in seen:
        raise ValueError('Repeated predecessor')
    seen.add(str(path))
    d = bounded_record(path); schema, status, parser, depth = PHASES[index]
    if d.get('schema') != schema or d.get('status') != status or d.get('ipa_runtime_ready') is not False or d.get('backing_depth') != depth:
        raise ValueError('Wrong preparation phase/depth/readiness')
    if any((path.parent / n).exists() for n in ('INCOMPLETE.json', 'failure.json')):
        raise ValueError('Failed or incomplete stage')
    report_path = pin(d['report'], d['report_sha256'], pins)
    retention = pin(d['retention'], d['retention_sha256'], pins)
    if report_path != path.parent / 'recovery-run/report.json' or retention != report_path.parent / 'stopped-disk-hashes.json':
        raise ValueError('Unexpected report/retention layout')
    for p, digest in d['stopped_evidence_sha256'].items():
        pin(p, digest, pins)
    serial = report_path.parent / 'serial.log'; controls = report_path.parent / 'control-transcript.jsonl'
    qmp = report_path.parent / 'qmp-transcript.jsonl'; checkpoint_path = path.parent / 'content-check.json'; finish = path.parent / 'finish.stdout'
    for required in (serial, controls, qmp, checkpoint_path, finish):
        if str(required) not in d['stopped_evidence_sha256']:
            raise ValueError('Missing raw evidence pin: ' + str(required))
    if serial.stat().st_size > 64 << 20:
        raise ValueError('Raw serial exceeds64MiB')
    raw = serial.read_bytes()
    if parser(raw) != d['content'] or pins[str(checkpoint_path)] != d['content_checkpoint_sha256']:
        raise ValueError('Raw phase content/checkpoint binding differs')
    checkpoint = bounded_record(checkpoint_path)
    if {k: v for k, v in checkpoint.items() if k not in ('captured_time', 'eligible')} != parser(raw[:checkpoint['serial_bytes']]) or checkpoint.get('eligible') is not False:
        raise ValueError('Checkpoint is not exact original prefix')
    submissions = [json.loads(row) for row in controls.read_bytes().splitlines() if row]
    if len(submissions) != 1:
        raise ValueError('Expected one normal finish')
    c = submissions[0]; request = json.loads(c['raw'])
    if request['execute'] != 'finish-observation' or request['arguments'] != {} or hashlib.sha256(c['raw'].encode()).hexdigest() != c['sha256'] or not checkpoint['captured_time'] < request['created'] <= c['time'] or c.get('response', {}).get('return', {}).get('finish_requested') is not True or bounded_record(finish) != c['response']:
        raise ValueError('Finish is not bound to earlier content checkpoint')
    report = bounded_record(report_path)
    for name, key in [('boot.py', 'runner_sha256'), ('qmp_control.py', 'control_source_sha256')]:
        if [h for p, h in d['source_sha256'].items() if Path(p).name == name] != [report[key]]:
            raise ValueError('Producer source/report mismatch')
    for name in (parser.__module__ + '.py', 'prepare-root.c', 'imported-app.c', 'libSystem.tbd', 'entitlements.plist'):
        current = SOURCE / ('native-probe/' + name if name.endswith(('.c', '.tbd', '.plist')) else name)
        if [h for p, h in d['source_sha256'].items() if Path(p).name == name] != [sha(current)]:
            raise ValueError('Observed phase implementation differs: ' + name)
    context = {'session': {'recovery_profile': {'sha256': report['profile_sha256']}, 'sources': {'boot.py': report['runner_sha256'], 'qmp_control.py': report['control_source_sha256']}}}
    CO.check_completed_report(context, report_path)
    frozen_path = path.parent / 'freeze-record.json'
    frozen_hash = sha(frozen_path)
    pin(frozen_path, frozen_hash, pins)
    frozen = bounded_record(frozen_path)
    if sha(frozen_path) != frozen_hash: raise ValueError('Freeze record changed during parsing')
    records = bounded_record(retention)
    if set(records) != {'root.qcow2', *CO.AUXILIARY_SIZES} or set(frozen['files']) != set(records):
        raise ValueError('Expected exactly seven frozen paired namespaces')
    for name, entry in records.items():
        f = frozen['files'][name]
        if entry.get('forensic_only') or f['path'] != entry['path'] or f['sha256'] != entry['sha256'] or CO.identity(entry['path']) != f['after'] or f['after']['st_mode'] != stat.S_IFREG | 0o444:
            raise ValueError('Frozen namespace binding/metadata differs')
    prior = None
    if index:
        prior = validate_phase(d['predecessor']['path'], d['predecessor']['sha256'], index - 1, pins, seen)
        base = report.get('overlay_base_report', {})
        if base.get('report') != prior['report'] or base.get('report_sha256') != prior['report_sha256'] or base.get('stopped_manifest_sha256') != prior['retention_sha256']:
            raise ValueError('Predecessor manifest differs from actual disk lineage')
    return d


def identities(chain):
    paths = {x['path'] for x in chain['layers']} | {x['path'] for x in chain['auxiliary'].values()}
    return {p: CO.identity(p) for p in sorted(paths)}


def normalized(chain):
    result = copy.deepcopy(chain)
    for item in result.get('metadata_revalidation', []):
        item.pop('verified_time', None)
    return result


def gpt_headers(raw):
    size = raw.stat().st_size
    if size % 4096:
        raise ValueError('Raw disk is not 4KiB aligned')
    def header(stream, lba):
        if not 0 < lba < size // 4096:
            raise ValueError('GPT header outside raw disk')
        stream.seek(lba * 4096); block = stream.read(4096)
        if block[:8] != b'EFI PART': raise ValueError('Missing GPT signature')
        length = struct.unpack_from('<I', block, 12)[0]
        if not 92 <= length <= 4096: raise ValueError('Invalid GPT header length')
        crc = struct.unpack_from('<I', block, 16)[0]; h = bytearray(block[:length]); h[16:20] = b'\0' * 4
        if zlib.crc32(h) & 0xffffffff != crc: raise ValueError('GPT header CRC mismatch')
        current, backup = struct.unpack_from('<QQ', block, 24)
        entries, count, entry_size, entry_crc = struct.unpack_from('<QIII', block, 72)
        if current != lba or not 0 < count <= 16384 or not 128 <= entry_size <= 4096 or count * entry_size > 16 << 20 or entries * 4096 + count * entry_size > size:
            raise ValueError('Invalid GPT entry bounds')
        stream.seek(entries * 4096); data = stream.read(count * entry_size)
        if len(data) != count * entry_size or zlib.crc32(data) & 0xffffffff != entry_crc: raise ValueError('GPT entries CRC mismatch')
        return {'lba': lba, 'backup_lba': backup, 'header_crc32': crc, 'entry_count': count, 'entry_size': entry_size, 'entries_crc32': entry_crc, 'entries_sha256': hashlib.sha256(data).hexdigest()}
    with raw.open('rb') as stream:
        a = header(stream, 1); b = header(stream, a['backup_lba'])
    if a['backup_lba'] != size // 4096 - 1 or b['backup_lba'] != 1 or any(a[k] != b[k] for k in ('entry_count', 'entry_size', 'entries_sha256')):
        raise ValueError('Primary/backup GPT differ')
    return {'primary': a, 'backup': b}


def run_tool(tool, output, label, args, timeout=1200):
    command = [tool['binary'], *map(str, args)]
    env = os.environ.copy(); env['LD_LIBRARY_PATH'] = str(Path(tool['root']) / 'root/usr/lib/aarch64-linux-gnu')
    process = None; error = None; cleanup = {}; started = time.time()
    with (output / (label + '.stdout')).open('xb') as out, (output / (label + '.stderr')).open('xb') as err:
        try:
            process = subprocess.Popen(command, stdout=out, stderr=err, stdin=subprocess.DEVNULL, env=env, start_new_session=True)
            proc = Path(f'/proc/{process.pid}/stat').read_text(); process.inferno_start_ticks = int(proc[proc.rfind(')') + 2:].split()[19])
            if process.wait(timeout=timeout) != 0 or CO.owned_group_members(process): raise ValueError(label + ' failed or left owned processes')
        except BaseException as exc:
            error = exc
            if process is not None: cleanup = CO.stop_owned_group(process)
    CO.write_new(output / (label + '.json'), {'argv': command, 'LD_LIBRARY_PATH': env['LD_LIBRARY_PATH'], 'started': started, 'finished': time.time(), 'exit_code': process.returncode if process else None, 'error': str(error) if error else None, 'cleanup': cleanup, 'stdout_sha256': sha(output / (label + '.stdout')), 'stderr_sha256': sha(output / (label + '.stderr'))})
    if error: raise error


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-verified', type=Path, required=True); parser.add_argument('--data-verified-sha256', required=True)
    parser.add_argument('--overlay-tools-root', type=Path, required=True); parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(); output = None; mask = os.umask(0o077)
    def interrupted(number, frame):
        raise InterruptedError('Signal ' + str(number))
    handlers = {number: signal.signal(number, interrupted) for number in (signal.SIGINT, signal.SIGTERM)}
    try:
        sources = source_pins(); pins = {}; CO.no_running_emulator()
        destination = CO.IMPORTER.external_output(args.output)
        stage = validate_phase(args.data_verified, args.data_verified_sha256, 2, pins)
        tool = OV.validate_tools(args.overlay_tools_root)
        before = OV.load_stopped_overlay(Path(stage['report']), tool); before_ids = identities(before)
        if len(before['layers']) != 4 or before['virtual_size'] != 8 << 30 or before['layers'][-1]['sha256'] != ORIGINAL_ROOT_SHA:
            raise ValueError('Expected verified original 8GiB four-layer chain')
        CO.PRESERVE.descriptor_check(before_ids)
        free = shutil.disk_usage(destination.parent).free
        if free < before['virtual_size'] + (2 << 30): raise ValueError('Need full logical raw size plus2GiB free; no resize supported')
        destination.mkdir(mode=0o700); output = destination
        CO.write_new(output / 'INCOMPLETE.json', {'status': 'incomplete-not-runtime-ready'})
        CO.write_new(output / 'preflight.json', {'data_verified': {'path': str(args.data_verified), 'sha256': args.data_verified_sha256}, 'source_sha256': sources, 'evidence_sha256': pins, 'tool': tool, 'source_before': before, 'identities_before': before_ids, 'available_bytes': free, 'logical_bytes': before['virtual_size']})
        unchanged({**sources, **pins}); CO.no_running_emulator()
        if identities(before) != before_ids: raise ValueError('Source metadata changed before conversion')
        raw = output / 'root.raw'; original = Path(before['layers'][0]['path'])
        run_tool(tool, output, 'convert', ['convert', '-f', 'qcow2', '-O', 'raw', '-S', '4k', original, raw])
        if raw.is_symlink() or raw.stat().st_nlink != 1 or raw.stat().st_size != before['virtual_size']: raise ValueError('Unexpected new raw layout')
        run_tool(tool, output, 'raw-info', ['info', '--output=json', '-f', 'raw', raw], 60)
        info = bounded_record(output / 'raw-info.stdout')
        if info['format'] != 'raw' or info['virtual-size'] != before['virtual_size']: raise ValueError('Raw virtual size changed')
        gpt = gpt_headers(raw); raw_hash = sha(raw)
        run_tool(tool, output, 'logical-compare', ['compare', '-f', 'qcow2', '-F', 'raw', original, raw])
        after = OV.load_stopped_overlay(Path(stage['report']), tool); after_ids = identities(after)
        if normalized(before) != normalized(after) or before_ids != after_ids or sha(raw) != raw_hash: raise ValueError('Source or new raw changed during logical comparison')
        unchanged({**sources, **pins})
        if OV.validate_tools(args.overlay_tools_root) != tool: raise ValueError('Pinned qemu-img tool changed')
        CO.PRESERVE.descriptor_check([*before_ids, raw])
        raw_before = CO.identity(raw)
        fd = os.open(raw, os.O_RDWR | os.O_NOFOLLOW)
        try:
            if {k: getattr(os.fstat(fd), k) for k in raw_before} != raw_before: raise ValueError('New raw replaced before freeze')
            os.fsync(fd); os.fchmod(fd, 0o444); os.fsync(fd)
        finally: os.close(fd)
        final = OV.validate_base(raw, raw_hash, allow_attestation=False)
        if any(CO.identity(raw)[k] != raw_before[k] for k in ('st_dev', 'st_ino', 'st_size', 'st_mtime_ns')): raise ValueError('Unexpected new raw freeze identity change')
        unchanged({**sources, **pins})
        if OV.validate_tools(args.overlay_tools_root) != tool: raise ValueError('Pinned qemu-img tool changed during final raw validation')
        if identities(before) != before_ids: raise ValueError('Source metadata changed at publication')
        auxiliary = {name: entry for name, entry in before['auxiliary'].items() if name != 'root.qcow2'}
        provenance = {'schema': 'inferno.flattened-verified-data.v1', 'status': 'flattened-verified-data-not-runtime-ready', 'ipa_runtime_ready': False, 'data_verified': {'path': str(args.data_verified), 'sha256': args.data_verified_sha256}, 'raw': final, 'allocated_bytes': raw.stat().st_blocks * 512, 'gpt': gpt, 'tool': tool, 'source_before': before, 'source_after': after, 'identities_before': before_ids, 'identities_after': after_ids, 'source_sha256': sources, 'evidence_sha256': pins, 'paired_auxiliary': auxiliary, 'auxiliary_state': str(Path(stage['report']).parent), 'auxiliary_report_sha256': stage['report_sha256'], 'auxiliary_retention_sha256': stage['retention_sha256'], 'future_boot_arguments': ['--root-image', str(raw), '--root-sha256', raw_hash, '--root-overlay', '--auxiliary-state', str(Path(stage['report']).parent)], 'scope': 'Host logical equality and GPT validation only; original verified Data comparison scope retained. No growth, APFS resize, guest execution, keybag or runtime readiness.'}
        CO.write_new(output / 'flattened-data.json', provenance)
        CO.write_new(output / 'KEEP-OVERLAY-BACKING.json', {'backing': final, 'provenance_sha256': sha(output / 'flattened-data.json'), 'retirement_prohibited_while_dependent_overlays_exist': True, 'paired_auxiliary_must_be_retained': auxiliary, 'scope': 'Only new raw frozen; all original reports/disks retained unchanged.'})
        (output / 'INCOMPLETE.json').unlink()
        directory = os.open(output, os.O_RDONLY | os.O_DIRECTORY)
        try: os.fsync(directory)
        finally: os.close(directory)
        print(json.dumps({'result': str(output / 'flattened-data.json'), 'sha256': sha(output / 'flattened-data.json'), 'ipa_runtime_ready': False})); return 0
    except BaseException as exc:
        if output is not None: CO.write_new(output / 'failure.json', {'status': 'failed-not-eligible', 'error': str(exc), 'ipa_runtime_ready': False})
        print('flatten-verified-data failed: ' + str(exc), file=sys.stderr); return 1
    finally:
        os.umask(mask)
        for number, handler in handlers.items(): signal.signal(number, handler)


if __name__ == '__main__': raise SystemExit(main())
