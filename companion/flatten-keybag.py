#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Flatten one stopped fresh-keybag stage; no guest or filesystem resize."""
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
import keybag_state as KS
from initial_volumes import bounded_record

SOURCE=Path(__file__).resolve().parent
CO=KS.CO
sha=KS.sha

def source_pins():
    pins=KS.sources();pins[str(Path(__file__).resolve())]=sha(Path(__file__))
    return pins

def unchanged(pins):
    KS.SK.unchanged(pins)


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
    parser.add_argument('--keybag-stage', type=Path, required=True); parser.add_argument('--keybag-stage-sha256', required=True)
    parser.add_argument('--overlay-tools-root', type=Path, required=True); parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(); output = None; mask = os.umask(0o077)
    def interrupted(number, frame):
        raise InterruptedError('Signal ' + str(number))
    handlers = {number: signal.signal(number, interrupted) for number in (signal.SIGINT, signal.SIGTERM)}
    try:
        sources = source_pins(); pins = {}; CO.no_running_emulator()
        destination = CO.IMPORTER.external_output(args.output)
        validated=KS.validate(args.keybag_stage,args.keybag_stage_sha256,pins,args.overlay_tools_root)
        stage=validated['manifest'];tool=validated['tool'];before=validated['chain'];before_ids=validated['identities']
        if len(before['layers'])!=3 or before['virtual_size']!=32<<30:
            raise ValueError('Expected fresh-keybag32GiB three-layer chain')
        CO.PRESERVE.descriptor_check([Path(p) for p in before_ids])
        free = shutil.disk_usage(destination.parent).free
        if free < before['virtual_size'] + (2 << 30): raise ValueError('Need full logical raw size plus2GiB free; no resize supported')
        destination.mkdir(mode=0o700); output = destination
        CO.write_new(output / 'INCOMPLETE.json', {'status': 'incomplete-not-runtime-ready'})
        CO.write_new(output / 'preflight.json', {'keybag_stage': {'path': str(args.keybag_stage), 'sha256': args.keybag_stage_sha256}, 'source_sha256': sources, 'evidence_sha256': pins, 'tool': tool, 'source_before': before, 'identities_before': before_ids, 'available_bytes': free, 'logical_bytes': before['virtual_size']})
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
        CO.PRESERVE.descriptor_check([*[Path(p) for p in before_ids], raw])
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
        provenance = {'schema': 'inferno.flattened-keybag-state.v1', 'status': 'flattened-fresh-keybag-not-runtime-ready', 'ipa_runtime_ready': False, 'sep_destination_bytes_verified': False, 'postgrowth_full_data_verified': False, 'keybag_stage': {'path': str(args.keybag_stage), 'sha256': args.keybag_stage_sha256}, 'raw': final, 'allocated_bytes': raw.stat().st_blocks * 512, 'gpt': gpt, 'tool': tool, 'source_before': before, 'source_after': after, 'identities_before': before_ids, 'identities_after': after_ids, 'source_sha256': sources, 'evidence_sha256': pins, 'paired_auxiliary': auxiliary, 'auxiliary_state': str(Path(stage['report']).parent), 'auxiliary_report_sha256': stage['report_sha256'], 'auxiliary_retention_sha256': stage['retention_sha256'], 'future_boot_arguments': ['--root-image', str(raw), '--root-sha256', raw_hash, '--root-overlay', '--auxiliary-state', str(Path(stage['report']).parent)], 'scope': 'Host logical equality/GPT only; fresh original API keybag state preserved with exact paired auxiliaries. No new keybag operation, postgrowth full Data equality, destination SEP byte proof or runtime readiness.'}
        CO.write_new(output / 'flattened-keybag.json', provenance)
        CO.write_new(output / 'KEEP-OVERLAY-BACKING.json', {'backing': final, 'provenance_sha256': sha(output / 'flattened-keybag.json'), 'retirement_prohibited_while_dependent_overlays_exist': True, 'paired_auxiliary_must_be_retained': auxiliary, 'scope': 'Only new raw frozen; all original reports/disks retained unchanged.'})
        (output / 'INCOMPLETE.json').unlink()
        directory = os.open(output, os.O_RDONLY | os.O_DIRECTORY)
        try: os.fsync(directory)
        finally: os.close(directory)
        print(json.dumps({'result': str(output / 'flattened-keybag.json'), 'sha256': sha(output / 'flattened-keybag.json'), 'ipa_runtime_ready': False})); return 0
    except BaseException as exc:
        if output is not None: CO.write_new(output / 'failure.json', {'status': 'failed-not-eligible', 'error': str(exc), 'ipa_runtime_ready': False})
        print('flatten-keybag failed: ' + str(exc), file=sys.stderr); return 1
    finally:
        os.umask(mask)
        for number, handler in handlers.items(): signal.signal(number, handler)


if __name__ == '__main__': raise SystemExit(main())
