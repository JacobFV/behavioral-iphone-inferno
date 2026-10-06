#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Observe exactly two live sibling iOS emulators for60s; never launches or controls them."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import time

spec = importlib.util.spec_from_file_location('measure_process', Path(__file__).with_name('measure-process.py'))
reader = importlib.util.module_from_spec(spec)
spec.loader.exec_module(reader)


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def read(path, optional=False):
    start = time.monotonic_ns()
    try:
        raw = path.read_bytes()
        return {'path': str(path), 'start_ns': start, 'end_ns': time.monotonic_ns(),
                'bytes': len(raw), 'raw': raw.decode('utf-8'), 'error': None}
    except OSError as exc:
        if not optional:
            raise
        return {'path': str(path), 'start_ns': start, 'end_ns': time.monotonic_ns(),
                'bytes': 0, 'raw': None, 'error': str(exc)}


def identity(item):
    proc = Path('/proc') / str(item['pid'])
    parsed = reader.stat_fields((proc / 'stat').read_text())
    if parsed['start_ticks'] != item['start_ticks'] or (proc / 'exe').resolve() != Path(item['binary']):
        raise ValueError('live process identity changed')
    return proc


def validate(directory, base):
    directory = directory.resolve(strict=True)
    report_path = directory / 'report.json'
    report = json.loads(report_path.read_bytes())
    pid = report['pid']
    if type(pid) is not int or pid <= 0:
        raise ValueError('invalid emulator PID')
    overlay = report['root_overlay']
    if Path(overlay['backing_report']).resolve() != base:
        raise ValueError('report does not use the explicitly selected frozen base')
    for pathkey, hashkey in [('backing_report', 'backing_report_sha256'), ('stopped_manifest', 'stopped_manifest_sha256')]:
        if digest(Path(overlay[pathkey])) != overlay[hashkey]:
            raise ValueError('frozen base provenance changed')
    dependencies = overlay['dependencies']
    for dep in dependencies:
        st = Path(dep['path']).stat()
        if (st.st_dev, st.st_ino, st.st_size, st.st_mtime_ns) != (dep['device'], dep['inode'], dep['bytes'], dep['mtime_ns']) or st.st_mode & 0o222:
            raise ValueError('backing dependency identity or immutable mode changed')
    command = json.loads((directory / 'command.json').read_text())
    proc = Path('/proc') / str(pid)
    actual = (proc / 'cmdline').read_bytes().rstrip(b'\0').decode().split('\0')
    if actual != command or '-kernel' not in command or 't8030' not in command[command.index('-machine') + 1]:
        raise ValueError('live command does not match recorded guest command')
    binary = Path(report['binary']).resolve(strict=True)
    if (proc / 'exe').resolve(strict=True) != binary or digest(binary) != report['binary_sha256']:
        raise ValueError('executable identity/hash mismatch')
    disks, endpoints = [], [str(Path(report['control_mailbox']).resolve())]
    for i, arg in enumerate(command[:-1]):
        val = command[i + 1]
        if arg == '-drive':
            opts = dict(x.split('=', 1) for x in val.split(',') if '=' in x)
            path = Path(opts['file']).resolve(strict=True)
            if path.parent != directory / 'disks':
                raise ValueError('writable disk is outside isolated report directory')
            st = path.stat()
            disks.append({'path': str(path), 'device': st.st_dev, 'inode': st.st_ino})
        elif arg in ('-vnc', '-qmp'):
            if not val.startswith('unix:'):
                raise ValueError('display/control endpoint is not private Unix socket')
            endpoints.append(val[5:].split(',')[0])
        elif arg == '-chardev' and val.startswith('socket,'):
            opts = dict(x.split('=', 1) for x in val.split(',') if '=' in x)
            endpoints.append(opts['path'])
    if len(disks) != 7 or len(set(endpoints)) != len(endpoints):
        raise ValueError('expected seven independent disks and unique endpoints')
    return {'report': str(report_path), 'report_sha256': digest(report_path), 'pid': pid,
            'binary': str(binary), 'binary_sha256': report['binary_sha256'],
            'start_ticks': reader.stat_fields((proc / 'stat').read_text())['start_ticks'],
            'disks': disks, 'endpoints': endpoints, 'dependencies': dependencies,
            'base_report_sha256': overlay['backing_report_sha256'],
            'base_manifest_sha256': overlay['stopped_manifest_sha256']}


def memory(raw):
    fields = {}
    for line in raw.splitlines():
        parts = line.split()
        if len(parts) == 3 and parts[2] == 'kB':
            fields[parts[0].rstrip(':')] = int(parts[1]) * 1024
    if not all(key in fields for key in ('Rss', 'Pss')):
        raise ValueError('required smaps_rollup Rss/Pss missing')
    return fields


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report', action='append', type=Path, required=True)
    parser.add_argument('--base-report', type=Path, required=True, help='frozen50 report.json shared by both children')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if len(args.report) != 2 or args.report[0].resolve() == args.report[1].resolve():
        parser.error('exactly two distinct live reports are required')
    try:
        items = [validate(p, args.base_report.resolve(strict=True)) for p in args.report]
        if items[0]['pid'] == items[1]['pid'] or items[0]['binary_sha256'] != items[1]['binary_sha256']:
            raise ValueError('distinct PIDs with identical executable hashes required')
        if items[0]['dependencies'] != items[1]['dependencies']:
            raise ValueError('backing chain provenance differs')
        if set(items[0]['endpoints']) & set(items[1]['endpoints']):
            raise ValueError('shared control/display endpoint')
        disksets = [{(x['device'], x['inode']) for x in item['disks']} for item in items]
        if len(disksets[0]) != 7 or len(disksets[1]) != 7 or disksets[0] & disksets[1]:
            raise ValueError('writable disks share an inode')
    except (OSError, ValueError, KeyError, IndexError) as exc:
        parser.error(str(exc))
    args.output.mkdir(parents=True, exist_ok=False)
    result = {'kind': 'two_host_emulator_observation', 'source_sha256': digest(Path(__file__)),
              'reader_sha256': digest(Path(reader.__file__)), 'processes': items,
              'requested_seconds': 60, 'stat_interval_seconds': 1, 'memory_interval_seconds': 5,
              'clock_ticks_per_second': os.sysconf('SC_CLK_TCK'), 'host_logical_cpus': os.cpu_count(),
              'limits': ['Whole emulator processes, not guest app memory.', 'PSS sum excludes other host allocations; RSS counts shared pages repeatedly.',
                         'Sequential read timestamps expose non-atomic sampling; no maximum density or cost claim.',
                         'Guest journey and workload correctness require separate actual execution evidence.']}
    samples, error = [], None
    start, own_cpu = time.monotonic_ns(), time.process_time_ns()
    target = 0
    with (args.output / 'samples.jsonl').open('w') as log:
        while target <= 60:
            time.sleep(max(0, (start + target * 1_000_000_000 - time.monotonic_ns()) / 1e9))
            sample = {'target_seconds': target, 'wall_time': time.time(), 'start_ns': time.monotonic_ns(), 'processes': [], 'host': {}}
            try:
                for item in items:
                    proc = identity(item)
                    row = {'pid': item['pid'], 'reads': {name: read(proc / name) for name in ('stat', 'status', 'io')}}
                    sample['processes'].append(row)
                    row['parsed'] = reader.stat_fields(row['reads']['stat']['raw'])
                    if target % 5 == 0 or target == 60:
                        row['reads']['smaps_rollup'] = read(proc / 'smaps_rollup')
                        row['memory_bytes'] = memory(row['reads']['smaps_rollup']['raw'])
                    identity(item)
                for name in ('stat', 'meminfo', 'loadavg'):
                    sample['host'][name] = read(Path('/proc') / name)
                for name in ('cpu', 'memory', 'io'):
                    sample['host']['pressure_' + name] = read(Path('/proc/pressure') / name, optional=True)
            except (OSError, ValueError) as exc:
                error = str(exc)
                sample['error'] = error
            sample['end_ns'] = time.monotonic_ns()
            samples.append(sample)
            log.write(json.dumps(sample) + '\n'); log.flush()
            if error or target == 60:
                break
            target = min(60, max(target + 1, int((time.monotonic_ns() - start) / 1e9) + 1))
    result.update(error=error, sample_count=len(samples), sampler_cpu_seconds=(time.process_time_ns()-own_cpu)/1e9)
    valid = [s for s in samples if 'error' not in s]
    if len(valid) >= 2:
        first, last = valid[0], valid[-1]
        elapsed = (last['start_ns'] - first['start_ns']) / 1e9
        cpu = []
        for a, b in zip(first['processes'], last['processes']):
            seconds = sum(b['parsed'][k]-a['parsed'][k] for k in ('user_ticks','system_ticks')) / result['clock_ticks_per_second']
            cpu.append({'pid': a['pid'], 'cpu_seconds': seconds, 'stat_read_span_seconds': (b['reads']['stat']['start_ns']-a['reads']['stat']['start_ns'])/1e9})
        mem = [s for s in valid if all('memory_bytes' in p for p in s['processes'])]
        result.update(observed_seconds=elapsed, cpu=cpu, aggregate_cpu_seconds=sum(p['cpu_seconds'] for p in cpu),
                      aggregate_cpu_percent_one_core=100*sum(p['cpu_seconds'] for p in cpu)/elapsed,
                      max_sample_read_span_seconds=max((s['end_ns']-s['start_ns'])/1e9 for s in valid),
                      memory_sample_count=len(mem),
                      peak_sampled_rss_sum_bytes=max((sum(p['memory_bytes']['Rss'] for p in s['processes']) for s in mem), default=None),
                      peak_sampled_pss_sum_bytes=max((sum(p['memory_bytes']['Pss'] for p in s['processes']) for s in mem), default=None))
    result['complete'] = error is None and len(valid) >= 2 and valid[-1]['target_seconds'] == 60
    (args.output / 'summary.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result))
    return 0 if result['complete'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
