#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Capture/touch a private QEMU Unix VNC socket without opening a display.

Narrow RFB3.8 client, RFC6143: None security, raw true-color frames, pointer input
and one fixed F6 Home/Menu button. No TCP listener, clipboard, arbitrary keyboard,
or host display integration.
"""
import argparse
import hashlib
import json
from pathlib import Path
import socket
import signal
import struct
import time
from PIL import Image


class ObserverStop(Exception):
    pass


def write_report(path, report):
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(report, indent=2)+"\n")
    temporary.replace(path)


class Client:
    def __init__(self, endpoint, report, status_path=None):
        self.report = report
        self.status_path = status_path
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.settimeout(15)
        self.sock.connect(str(endpoint))
        banner = self.read(12)
        if banner != b'RFB 003.008\n':
            raise ValueError(f'Expected QEMU RFB3.8: {banner!r}')
        self.sock.sendall(banner)
        security = self.read(self.read(1)[0])
        if 1 not in security:
            raise ValueError('Private socket does not offer None security')
        self.sock.sendall(b'\x01')
        if self.read(4) != bytes(4):
            raise ValueError('VNC security handshake failed')
        self.sock.sendall(b'\x01')  # Shared client; preserve other connections.
        header = self.read(24)
        self.width, self.height = struct.unpack('>HH', header[:4])
        length = struct.unpack('>I', header[20:24])[0]
        if length > 4096 or not 0 < self.width*self.height <= 16000000:
            raise ValueError('Unsupported framebuffer dimensions/name')
        name = self.read(length).decode(errors='replace')
        report['server'] = {'banner': banner.decode().strip(), 'name': name,
                            'width': self.width, 'height': self.height}
        pf = struct.pack('>BBBBHHHBBBxxx', 32, 24, 0, 1, 255, 255, 255, 16, 8, 0)
        self.sock.sendall(b'\x00\x00\x00\x00' + pf)
        self.sock.sendall(struct.pack('>BBHi', 2, 0, 1, 0))
        report['connection_established_time'] = time.time()
        report['connection_established_monotonic'] = time.monotonic()
        if self.status_path:
            write_report(self.status_path, report)

    def read(self, size):
        data = bytearray()
        while len(data) < size:
            part = self.sock.recv(min(size-len(data), 1024*1024))
            if not part:
                raise EOFError('VNC socket closed')
            data.extend(part)
        return bytes(data)

    def capture(self, path):
        requested = time.time()
        requested_mono = time.monotonic()
        self.sock.sendall(struct.pack('>BBHHHH', 3, 0, 0, 0, self.width, self.height))
        canvas = Image.new('RGB', (self.width, self.height))
        coverage = bytearray(self.width*self.height)
        deadline = time.monotonic()+15
        while time.monotonic() < deadline:
            kind = self.read(1)[0]
            if kind == 2:  # Bell has no payload.
                continue
            if kind == 3:
                length = struct.unpack('>xxxI', self.read(7))[0]
                if length > 1024*1024:
                    raise ValueError('Oversized server text')
                self.read(length)
                continue
            if kind != 0:
                raise ValueError(f'Unexpected server message {kind}')
            count = struct.unpack('>xH', self.read(3))[0]
            for _ in range(count):
                x, y, width, height, encoding = struct.unpack('>HHHHi', self.read(12))
                if encoding != 0 or x+width > self.width or y+height > self.height:
                    raise ValueError('Unexpected encoding or rectangle bounds')
                if not width or not height:
                    continue
                pixels = self.read(width*height*4)
                canvas.paste(Image.frombytes('RGB', (width, height), pixels, 'raw', 'BGRX'), (x,y))
                for row in range(y,y+height):
                    start=row*self.width+x
                    coverage[start:start+width]=b'\x01'*width
            if all(coverage):
                received = time.time()
                received_mono = time.monotonic()
                canvas.save(path)
                self.report['captures'].append({'path': str(path),
                    'sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'time': time.time(),
                    'requested_time': requested, 'received_time': received,
                    'request_to_receive_seconds': received_mono-requested_mono})
                if len(self.report['captures']) == 1:
                    self.report['first_frame_received_time'] = received
                    if self.status_path:
                        write_report(self.status_path, self.report)
                return
        raise TimeoutError('Incomplete VNC framebuffer')

    def pointer(self, x, y, down):
        if not 0 <= x < self.width or not 0 <= y < self.height:
            raise ValueError('Pointer outside framebuffer')
        packet = struct.pack('>BBHH', 5, int(down), x, y)
        self.sock.sendall(packet)
        self.report['pointer_events'].append({'x': x, 'y': y, 'down': bool(down),
                                             'wire_hex': packet.hex(), 'time': time.time()})

    def home_button(self, down):
        # QEMU buttons.c maps F6 to SMC_HID_BUTTON_MENU; this is not an app hook.
        packet = struct.pack('>BBxxI', 4, int(down), 0xffc3)
        event = {'key': 'F6', 'keysym': 0xffc3, 'down': bool(down),
                 'wire_hex': packet.hex(), 'time': time.time(),
                 'transmission': 'unknown-or-partial', 'ui_acceptance': 'unproven'}
        self.report['home_button_events'].append(event)
        self.sock.sendall(packet)
        event['transmission'] = 'written-to-vnc-socket'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--socket', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    actions=parser.add_mutually_exclusive_group()
    actions.add_argument('--tap', nargs=2, type=int, metavar=('X','Y'))
    actions.add_argument('--swipe', nargs=4, type=int, metavar=('X0','Y0','X1','Y1'))
    actions.add_argument('--home-button', action='store_true',
                         help='one fixed 150ms F6 press/release through emulator SMC Menu')
    actions.add_argument('--app-switcher', action='store_true',
                         help='two fixed 150ms F6 presses with a 100ms gap')
    parser.add_argument('--hold-seconds', type=float, default=None,
                        help='stationary press before release or swipe (0..10 seconds)')
    parser.add_argument('--swipe-seconds', type=float, default=.5,
                        help='duration of the 20-step swipe (0.1..10 seconds)')
    parser.add_argument('--settle-seconds', type=float, default=1,
                        help='wait before a second capture, including observation-only (0..10 seconds)')
    parser.add_argument('--observe-seconds', type=float, default=0,
                        help='keep observation-only connection active, capture at 1Hz (0..300 seconds)')
    parser.add_argument("--runner-observer", action="store_true",
                        help="owned finite no-input child with graceful SIGTERM and status reporting")
    args=parser.parse_args()
    if (args.home_button or args.app_switcher) and args.hold_seconds is not None:
        parser.error('Home button actions use fixed 150ms presses')
    has_input = bool(args.tap or args.swipe or args.home_button or args.app_switcher)
    if not 0 <= args.observe_seconds <= 300 or (args.observe_seconds and has_input):
        parser.error('--observe-seconds must be finite within 0..300 and cannot accompany input')
    if args.runner_observer and (has_input or not args.observe_seconds):
        parser.error("--runner-observer requires positive observation duration and no input")
    hold=args.hold_seconds if args.hold_seconds is not None else (0 if args.swipe else .15)
    if not (0 <= hold <= 10 and .1 <= args.swipe_seconds <= 10 and 0 <= args.settle_seconds <= 10):
        parser.error('timings must be finite and within their documented bounds')
    if not args.socket.is_absolute() or not args.socket.is_socket():
        parser.error('expected existing absolute private Unix socket')
    args.output.mkdir(parents=True, exist_ok=False)
    report={'kind':'headless_unix_vnc_observation', 'socket':str(args.socket),
            'captures':[], 'pointer_events':[], 'home_button_events':[], 'completed':False,
            'timing_seconds':{'hold':hold, 'swipe':args.swipe_seconds, 'settle':args.settle_seconds},
            'observation_seconds':args.observe_seconds,
            'capture_limit':'Frame receipt is not guest presentation time; display refresh can stimulate guest rendering.',
            'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    client=None
    previous_handlers={}
    if args.runner_observer:
        def stop_observer(signum, frame):
            raise ObserverStop(f"signal {signum}")
        for sig in (signal.SIGTERM, signal.SIGINT):
            previous_handlers[sig]=signal.signal(sig, stop_observer)
    try:
        client=Client(args.socket,report,args.output/"report.json" if args.runner_observer else None)
        client.capture(args.output/'before.png')
        if not has_input:
            deadline = time.monotonic()+args.observe_seconds
            time.sleep(args.settle_seconds)
            client.capture(args.output/'settled.png')
            sequence = 0
            while time.monotonic() < deadline:
                time.sleep(min(1, max(0, deadline-time.monotonic())))
                sequence += 1
                client.capture(args.output/f'observed-{sequence:04d}.png')
        if args.home_button or args.app_switcher:
            client.home_button(True)
            time.sleep(.15)
            client.home_button(False)
            if args.app_switcher:
                time.sleep(.1)
                client.home_button(True)
                time.sleep(.15)
                client.home_button(False)
            time.sleep(args.settle_seconds)
            client.capture(args.output/'after.png')
        if args.tap or args.swipe:
            x,y=(args.tap or args.swipe)[:2]
            points=[(x,y)] + ([tuple(args.swipe[2:])] if args.swipe else [])
            if any(not 0 <= px < client.width or not 0 <= py < client.height for px,py in points):
                raise ValueError('Pointer outside framebuffer')
            client.pointer(x,y,True)
            if hold:
                time.sleep(hold)
            if args.swipe:
                target_x,target_y=args.swipe[2:]
                for step in range(1,21):
                    time.sleep(args.swipe_seconds/20)
                    client.pointer(round(x+(target_x-x)*step/20),round(y+(target_y-y)*step/20),True)
                x,y=target_x,target_y
            client.pointer(x,y,False)
            time.sleep(args.settle_seconds)
            client.capture(args.output/'after.png')
        report['completed']=True
    except ObserverStop as error:
        report["stop_requested"] = True
        report["stop_reason"] = str(error)
    except Exception as error:
        report['error']={'type':type(error).__name__,'message':str(error)}
    finally:
        for sig, handler in previous_handlers.items():
            signal.signal(sig, handler)
        if client:
            if report['home_button_events'] and report['home_button_events'][-1]['down']:
                try:
                    client.home_button(False)
                except OSError:
                    pass
            if report['pointer_events'] and report['pointer_events'][-1]['down']:
                event=report['pointer_events'][-1]
                try:
                    client.pointer(event['x'],event['y'],False)
                except OSError:
                    pass
            client.sock.close()
            report["connection_closed_time"] = time.time()
            report["connection_closed_monotonic"] = time.monotonic()
        write_report(args.output/"report.json", report)
    print(json.dumps(report))
    return 0 if report['completed'] or report.get('stop_requested') else 1


if __name__ == '__main__':
    raise SystemExit(main())
