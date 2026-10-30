#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Drive a running guest through a list of apps and record what the screen showed.

Every action goes through the existing tracked entry points: `owned-control`
for taps and swipes (one request each, never retried), `observe --home-button`
for Home, and a chain of no-input `observe --observe-seconds` connections that
capture the private VNC framebuffer at 1 Hz for the video. Nothing here talks to
QMP directly or opens a display.

A plan is JSON: {"apps": [{"name": ..., "steps": [step, ...]}, ...]} where a
step is one of
    {"tap": [x, y]}                      pixels of the captured frame ("panel": [w, h], default 828x1792)
    {"swipe": [x0, y0, x1, y1], "ms": 600}
    {"wait": seconds}
    {"home": true}
Each app starts from Home: the harness presses Home before its first step.
New apps slot in by adding an entry; the harness has no per-app code.

The output records, per action, the request directory and its wall time, so the
frames can be labelled afterwards. It asserts nothing about what an app did:
review the frames.
"""
import argparse
import json
import subprocess
import sys
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RUN = ROOT / 'companion/run'
PANEL = (828, 1792)


def scaled(x, y, panel=PANEL):
    return round(x / panel[0] * 32767), round(y / panel[1] * 32767)


class Recorder(threading.Thread):
    """Back-to-back finite observer connections; each saves 1 Hz frames."""

    def __init__(self, socket, output):
        super().__init__(daemon=True)
        self.socket, self.output, self.stop, self.chunks = socket, output, threading.Event(), 0

    def run(self):
        while not self.stop.is_set():
            target = self.output / ('rec-%04d' % self.chunks)
            self.chunks += 1
            subprocess.run([str(RUN), 'observe', '--socket', str(self.socket), '--output', str(target),
                            '--observe-seconds', '120'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def status_strip(recordings):
    """Digest of the newest recorded frame's status bar (it carries the minute clock)."""
    from PIL import Image
    import hashlib
    frames = sorted(recordings.glob('chunk-*/observed-*.png'), key=lambda p: p.stat().st_mtime)
    # The newest file may still be being written by the recorder: use the newest one that decodes.
    for frame in reversed(frames[-3:]):
        try:
            strip = Image.open(frame).convert('L').crop((0, 0, 300, 80))
        except (OSError, ValueError):
            continue
        return hashlib.sha256(strip.tobytes()).hexdigest()
    return None


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--report', type=Path, required=True, help='Active boot output directory (control mailbox)')
    parser.add_argument('--socket', type=Path, required=True, help='Its private VNC Unix socket')
    parser.add_argument('--plan', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True, help='New directory')
    parser.add_argument('--no-record', action='store_true')
    parser.add_argument('--freeze-dir', type=Path,
                        help='Recorder output to watch: stop with exit 3 when the status-bar clock has not '
                             'changed across two whole apps (the documented compositor freeze)')
    parser.add_argument('--skip', type=int, default=0, help='Start at this app index (resume after a restart)')
    args = parser.parse_args()
    plan = json.loads(args.plan.read_text())
    panel = tuple(plan.get('panel', PANEL))
    args.output.mkdir()
    log = []
    counter = [0]

    def action(kind, make):
        counter[0] += 1
        argv = make(args.output / ('%04d-%s' % (counter[0], kind)))
        started = time.time()
        result = subprocess.run(argv, capture_output=True, text=True)
        log.append({'n': counter[0], 'kind': kind, 'argv': argv, 'started': started, 'finished': time.time(),
                    'exit_code': result.returncode, 'stderr_tail': result.stderr[-400:]})
        (args.output / 'actions.json').write_text(json.dumps(log, indent=1))
        return result.returncode

    recorder = None if args.no_record else Recorder(args.socket, args.output)
    if recorder:
        recorder.start()
    try:
        strips = []
        for index, app in enumerate(plan['apps']):
            if index < args.skip:
                continue
            log.append({'app': app['name'], 'index': index, 'started': time.time()})
            action('home', lambda out: [str(RUN), 'observe', '--socket', str(args.socket), '--home-button', '--output', str(out)])
            time.sleep(app.get('settle', 20))
            for step in app['steps']:
                if 'wait' in step:
                    time.sleep(step['wait'])
                elif 'home' in step:
                    action('home', lambda out: [str(RUN), 'observe', '--socket', str(args.socket), '--home-button', '--output', str(out)])
                elif 'tap' in step:
                    x, y = scaled(*step['tap'], panel)
                    action('tap', lambda out: [str(RUN), 'owned-control', '--report', str(args.report), '--output', str(out),
                                                'tap', str(x), str(y), '--duration-ms', str(step.get('ms', 120))])
                elif 'swipe' in step:
                    x0, y0 = scaled(*step['swipe'][:2], panel); x1, y1 = scaled(*step['swipe'][2:], panel)
                    action('swipe', lambda out: [str(RUN), 'owned-control', '--report', str(args.report), '--output', str(out),
                                                  'swipe', str(x0), str(y0), str(x1), str(y1),
                                                  '--duration-ms', str(step.get('ms', 600))])
                time.sleep(step.get('after', 0))
            log.append({'app_end': app['name'], 'index': index, 'finished': time.time()})
            (args.output / 'actions.json').write_text(json.dumps(log, indent=1))
            if args.freeze_dir:
                strips.append(status_strip(args.freeze_dir))
                if len(strips) >= 3 and strips[-1] is not None and strips[-1] == strips[-3]:
                    log.append({'frozen_after': app['name'], 'index': index, 'time': time.time()})
                    (args.output / 'actions.json').write_text(json.dumps(log, indent=1))
                    print(json.dumps({'frozen_after_index': index}))
                    return 3
    finally:
        if recorder:
            recorder.stop.set()
    print(json.dumps({'output': str(args.output), 'actions': counter[0]}))


if __name__ == '__main__':
    sys.exit(main())
