# SPDX-License-Identifier: AGPL-3.0-or-later
"""Opt-in finite no-input VNC observer, separate from the sole QMP owner."""
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import time


class HeadlessRefresh:
    def __init__(self, output, seconds):
        if type(seconds) is not int or not 1 <= seconds <= 300:
            raise ValueError('headless refresh seconds must be an integer 1..300')
        self.output = Path(output) / 'headless-refresh'
        self.output.mkdir()
        self.seconds = seconds
        self.child = None
        self.handles = []
        self.last_sample = -1.0
        self.identity = None
        self.finished = False
        self.report = {'kind': 'opt-in-active-headless-refresh', 'requested_seconds': seconds,
                       'automatic_input': False, 'auto_restart': False, 'state': 'not-started',
                       'clock_ticks_per_second': os.sysconf('SC_CLK_TCK'),
                       'page_size': os.sysconf('SC_PAGE_SIZE'),
                       'coverage_complete_for_whole_boot': False,
                       'limits': ['VNC refresh stimulates guest display work; not passive observation.',
                                  'Observer CPU/RSS below is separate from emulator resources.',
                                  'CPU is sampled delta, not exact child lifetime CPU; RSS peak is sampled.',
                                  'No claim to fix earlier missing display submissions.',
                                  'Coverage starts at actual connection and ends on disconnect/exit; not guest presentation.']}

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        try:
            self.close()
        except Exception as error:
            self.report["cleanup_error"] = f"{type(error).__name__}: {error}"
        return False

    def save(self):
        temp = self.output / 'lifecycle.json.tmp'
        temp.write_text(json.dumps(self.report, indent=2) + '\n')
        temp.replace(self.output / 'lifecycle.json')

    def start(self, endpoint):
        endpoint = Path(endpoint)
        parent = endpoint.parent.stat()
        if not endpoint.is_absolute() or not stat.S_ISSOCK(endpoint.stat().st_mode):
            raise ValueError('expected fixed private Unix VNC socket')
        if parent.st_uid != os.getuid() or parent.st_mode & 0o077:
            raise ValueError('VNC socket directory is not private to runner UID')
        script = Path(__file__).with_name('vnc-control.py')
        command = [sys.executable, str(script), '--socket', str(endpoint), '--output',
                   str(self.output / 'observer'), '--observe-seconds', str(self.seconds),
                   '--runner-observer', '--settle-seconds', '0']
        self.report.update(command=command, socket=str(endpoint),
                           script_sha256=hashlib.sha256(script.read_bytes()).hexdigest(),
                           lifecycle_source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                           spawn_time=time.time(), spawn_monotonic=time.monotonic())
        try:
            self.handles = [(self.output / n).open('wb') for n in ('stdout.log', 'stderr.log')]
            self.child = subprocess.Popen(command, stdin=subprocess.DEVNULL,
                                          stdout=self.handles[0], stderr=self.handles[1])
            self.report.update(pid=self.child.pid, state='starting')
            self.poll()
        except Exception as exc:
            self.report.update(state='failed', error=f'{type(exc).__name__}: {exc}')
            self.save()
            raise

    def sample(self):
        if self.child is None or time.monotonic() - self.last_sample < 1:
            return
        self.last_sample = time.monotonic()
        try:
            raw = (Path('/proc') / str(self.child.pid) / 'stat').read_text()
            fields = raw[raw.rindex(')') + 2:].split()
            start, cpu, rss = int(fields[19]), int(fields[11]) + int(fields[12]), int(fields[21]) * os.sysconf('SC_PAGE_SIZE')
            if self.identity is None:
                self.identity = start
                self.report['start_ticks'] = start
            if start != self.identity:
                raise RuntimeError('observer PID start identity changed')
            row = {'time': time.time(), 'monotonic': time.monotonic(), 'proc_stat': raw,
                   'start_ticks': start, 'cpu_ticks': cpu, 'rss_bytes': rss}
            with (self.output / 'resources.jsonl').open('a') as stream:
                stream.write(json.dumps(row) + '\n')
            self.report['resource_last'] = row
            self.report.setdefault('resource_first', row)
            self.report['rss_peak_bytes'] = max(rss, self.report.get('rss_peak_bytes', 0))
            self.report['cpu_observed_seconds'] = (cpu-self.report['resource_first']['cpu_ticks']) / os.sysconf('SC_CLK_TCK')
        except OSError as exc:
            self.report['resource_unavailable'] = str(exc)
        except (ValueError, IndexError, RuntimeError) as exc:
            self.report['resource_error'] = str(exc)

    def read_observer(self):
        path = self.output / 'observer' / 'report.json'
        if not path.exists():
            return
        try:
            raw = path.read_bytes()
            if len(raw) > 1024*1024:
                raise ValueError('oversized observer report')
            data = json.loads(raw)
            if data.get('pointer_events') or data.get('home_button_events'):
                raise ValueError('observer unexpectedly reports input')
            self.report['observer_report'] = data
            self.report['observer_report_sha256'] = hashlib.sha256(raw).hexdigest()
            connected = data.get('connection_established_time')
            if connected is not None:
                self.report['connection_established_time'] = connected
                self.report['first_frame_received_time'] = data.get('first_frame_received_time')
            if data.get('connection_closed_time') is not None:
                self.report['connection_closed_time'] = data['connection_closed_time']
            self.report['requested_phase_completed'] = bool(data.get('completed'))
        except (ValueError, OSError) as exc:
            self.report['observer_report_error'] = str(exc)

    def poll(self):
        if self.child is None or self.finished:
            return
        self.sample()
        self.read_observer()
        code = self.child.poll()
        if code is None and time.monotonic() - self.report["spawn_monotonic"] > self.seconds + 30:
            self.report["error"] = "observer exceeded requested duration plus 30s startup/IO allowance"
        if code is not None:
            # Re-read after observed exit: the child may publish its final report
            # between the initial read and poll().
            self.read_observer()
            self.finished = True
            self.report.update(exit_code=code, exit_observed_time=time.time(), state='ended')
            data = self.report.get('observer_report', {})
            if code or not (data.get('completed') or data.get('stop_requested')):
                self.report.update(state='failed', error='observer exited without complete or controlled-stop report')
            self.report['coverage_active'] = False
            for handle in self.handles:
                handle.close()
            self.handles = []
        else:
            self.report['coverage_active'] = bool(self.report.get('first_frame_received_time')) and not self.report.get('connection_closed_time')
            if self.report['coverage_active']:
                self.report['state'] = 'observing'
        self.save()

    def close(self):
        """Bounded child-only shutdown, independent of report persistence success."""
        def retain_error(phase, exc):
            self.report.setdefault('cleanup_errors', []).append(
                {'phase': phase, 'error': f'{type(exc).__name__}: {exc}'})
        try:
            self.poll()
        except Exception as exc:
            retain_error('pre-stop-observation', exc)
        # Never let observation/report I/O failure skip owned-child cleanup.
        if self.child is not None:
            try:
                if self.child.poll() is None:
                    self.report['stop_requested_time'] = time.time()
                    self.child.terminate()
                    try:
                        self.child.wait(timeout=3)
                    except subprocess.TimeoutExpired:
                        self.report['forced_kill'] = True
                        self.child.kill()
                        self.child.wait(timeout=3)
                self.report['cleanup_child_exit_code'] = self.child.poll()
            except Exception as exc:
                retain_error('child-stop-reap', exc)
            try:
                self.poll()
            except Exception as exc:
                retain_error('post-stop-observation', exc)
            if not self.report.get('connection_closed_time'):
                self.report['coverage_end_unconfirmed'] = True
        for handle in self.handles:
            try:
                handle.close()
            except Exception as exc:
                retain_error('log-close', exc)
        self.handles = []
        try:
            self.save()
        except Exception as exc:
            # Retained in the runner's in-memory report if its final write works.
            retain_error('final-report-save', exc)
