#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Sample a live runner's host emulator process; not guest app memory or latency."""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import time


def stat_fields(raw):
    # comm can contain spaces and parentheses; fields after the last ')' start3.
    fields = raw[raw.rindex(')') + 2:].split()
    return {'user_ticks': int(fields[11]), 'system_ticks': int(fields[12]),
            'threads': int(fields[17]), 'start_ticks': int(fields[19]),
            'virtual_bytes': int(fields[20]), 'resident_pages': int(fields[21])}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--seconds', type=int, default=60)
    parser.add_argument('--interval', type=float, default=1)
    args = parser.parse_args()
    if not 1 <= args.seconds <= 3600 or not 1 <= args.interval <= 60:
        parser.error('seconds must be1..3600; interval must be1..60')
    report_path = args.report / 'report.json'
    report_bytes = report_path.read_bytes()
    report = json.loads(report_bytes)
    pid = report['pid']
    if not isinstance(pid, int) or pid < 1:
        parser.error('report has no valid emulator pid')
    proc = Path('/proc') / str(pid)
    binary = Path(report['binary']).resolve(strict=True)
    if (proc / 'exe').resolve(strict=True) != binary:
        parser.error('live process executable differs from report')
    with binary.open('rb') as stream:
        actual_hash = hashlib.file_digest(stream, 'sha256').hexdigest()
    if actual_hash != report['binary_sha256']:
        parser.error('live executable hash differs from report')
    identity = stat_fields((proc / 'stat').read_text())['start_ticks']
    args.output.mkdir(parents=True, exist_ok=False)
    tick_rate = os.sysconf('SC_CLK_TCK')
    page_size = os.sysconf('SC_PAGE_SIZE')
    start = time.monotonic()
    samples = []
    error = None
    with (args.output / 'samples.jsonl').open('w') as log:
        while True:
            try:
                raw = (proc / 'stat').read_text()
                parsed = stat_fields(raw)
                if parsed['start_ticks'] != identity:
                    raise RuntimeError('PID identity changed; measurement stopped')
                sample = {'time': time.time(), 'monotonic': time.monotonic(),
                          'proc_stat': raw, 'parsed': parsed,
                          'proc_status': (proc / 'status').read_text(),
                          'proc_io': (proc / 'io').read_text(),
                          'host_cpu': Path('/proc/stat').read_text().splitlines()[0],
                          'host_loadavg': Path('/proc/loadavg').read_text(),
                          'host_meminfo': Path('/proc/meminfo').read_text()}
                samples.append(sample)
                log.write(json.dumps(sample) + '\n')
                log.flush()
            except (OSError, ValueError, RuntimeError) as exc:
                error = str(exc)
                break
            remaining = args.seconds - (time.monotonic() - start)
            if remaining <= 0:
                break
            time.sleep(min(args.interval, remaining))
    result = {'kind': 'host_emulator_process_observation',
              'created_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'source_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'runner_report': str(report_path.resolve()),
              'runner_report_sha256_at_start': hashlib.sha256(report_bytes).hexdigest(),
              'binary_sha256': actual_hash, 'pid': pid, 'start_ticks': identity,
              'clock_ticks_per_second': tick_rate, 'page_size': page_size,
              'host_logical_cpus': os.cpu_count(), 'sample_count': len(samples),
              'requested_seconds': args.seconds, 'interval_seconds': args.interval,
              'error': error,
              'limits': ['Whole emulator process, not guest app RSS or guest CPU.',
                         'This observation is not cold/warm launch timing, reliability or density.',
                         'Host load and software rendering affect results; no cost extrapolation.',
                         'CPU100 percent means one fully occupied host logical CPU.']}
    if len(samples) >= 2:
        first, last = samples[0], samples[-1]
        elapsed = last['monotonic'] - first['monotonic']
        cpu_seconds = sum(last['parsed'][k] - first['parsed'][k]
                          for k in ('user_ticks', 'system_ticks')) / tick_rate
        result.update(observed_seconds=elapsed, process_cpu_seconds=cpu_seconds,
                      process_cpu_percent=100 * cpu_seconds / elapsed,
                      peak_sampled_rss_bytes=max(s['parsed']['resident_pages'] for s in samples) * page_size,
                      first_rss_bytes=first['parsed']['resident_pages'] * page_size,
                      last_rss_bytes=last['parsed']['resident_pages'] * page_size,
                      max_sampled_threads=max(s['parsed']['threads'] for s in samples))
    (args.output / 'summary.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))
    return int(error is not None)


if __name__ == '__main__':
    raise SystemExit(main())
