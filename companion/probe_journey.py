"""Narrow QMP interaction with companion/app-probe; screenshots need review."""
# SPDX-License-Identifier: AGPL-3.0-or-later
import hashlib


class ProbeJourney:
    def __init__(self, output, hardware_tap=False):
        self.output = output
        self.hardware_tap = hardware_tap
        self.state = 'waiting-for-app'
        self.ready_at = None
        self.report = {'state': self.state, 'completed': False,
                       'input_mode': 'automatic-hardware-tap' if hardware_tap else 'operator-observation',
                       'automatic_input': hardware_tap,
                       'visual_review_required': True, 'captures': {}}

    def command(self, qmp, name, arguments=None):
        result = qmp.execute(name, arguments)
        if 'error' in result:
            raise RuntimeError(f'Probe journey QMP {name}: {result["error"]}')
        return result

    def capture(self, qmp, label):
        path = self.output / (label + '.ppm')
        self.command(qmp, 'screendump', {'filename': str(path)})
        with path.open('rb') as stream:
            tokens = []
            while len(tokens) < 4:
                line = stream.readline()
                if not line:
                    raise ValueError('Incomplete probe framebuffer header')
                tokens.extend(line.split(b'#', 1)[0].split())
            if tokens[0] != b'P6' or tokens[3] != b'255':
                raise ValueError('Expected an 8-bit P6 probe framebuffer')
            width, height = int(tokens[1]), int(tokens[2])
            if width <= 0 or height <= 0:
                raise ValueError('Invalid probe framebuffer dimensions')
        self.report['captures'][label] = {
            'path': str(path), 'width': width, 'height': height,
            'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}

    def operator_capture_before(self, qmp):
        """Capture only after the operator has reviewed the visible app at zero."""
        if self.hardware_tap or self.state != 'waiting-for-operator-before-capture':
            raise ValueError('Probe is not awaiting an operator before capture')
        serial = (self.output / 'serial.log').read_bytes()
        if b'INFERNO_UIKIT_PROBE_V1 event=appeared count=0' not in serial:
            raise ValueError('Owned app appearance marker is missing')
        if b'INFERNO_UIKIT_PROBE_V1 event=tap count=1' in serial:
            raise ValueError('Tap marker already observed; before capture is too late')
        self.report['input_devices'] = self.command(qmp, 'query-mice')
        self.capture(qmp, 'probe-before')
        self.state = 'waiting-for-operator-tap-marker'
        self.report['state'] = self.state
        self.report['before_capture_operator_requested'] = True
        return {'state': self.state, 'capture': self.report['captures']['probe-before']}

    def operator_capture_after(self, qmp):
        """Complete only after the operator has reviewed the visible counter at one."""
        if self.hardware_tap or self.state != 'waiting-for-operator-after-capture':
            raise ValueError('Probe is not awaiting an operator after capture')
        serial = (self.output / 'serial.log').read_bytes()
        if b'INFERNO_UIKIT_PROBE_V1 event=tap count=1' not in serial:
            raise ValueError('Owned app tap marker is missing')
        if 'probe-before' not in self.report['captures']:
            raise ValueError('Owned app before capture is missing')
        self.capture(qmp, 'probe-after')
        self.state = 'completed'
        self.report['state'] = self.state
        self.report['completed'] = True
        self.report['after_capture_operator_requested'] = True
        return {'state': self.state, 'capture': self.report['captures']['probe-after']}

    def poll(self, qmp, now):
        serial_path = self.output / 'serial.log'
        serial = serial_path.read_bytes() if serial_path.exists() else b''
        appeared = b'INFERNO_UIKIT_PROBE_V1 event=appeared count=0'
        tapped = b'INFERNO_UIKIT_PROBE_V1 event=tap count=1'
        if self.state == 'waiting-for-app' and appeared in serial:
            self.report['appearance_marker_observed'] = True
            self.state = ('waiting-for-first-frame' if self.hardware_tap
                          else 'waiting-for-operator-before-capture')
            self.ready_at = now + 1
        elif self.state == 'waiting-for-first-frame' and now >= self.ready_at:
            self.report['input_devices'] = self.command(qmp, 'query-mice')
            self.capture(qmp, 'probe-before')
            # Main.m lays out a large central button starting at 58% height.
            # This is a probe-specific target, subject to actual image review.
            x, y = round(32767 * .5), round(32767 * .62)
            self.report['tap'] = {'absolute_x': x, 'absolute_y': y,
                                  'target_fraction': [.5, .62]}
            self.command(qmp, 'input-send-event', {'events': [
                {'type': 'abs', 'data': {'axis': 'x', 'value': x}},
                {'type': 'abs', 'data': {'axis': 'y', 'value': y}},
                {'type': 'btn', 'data': {'button': 'left', 'down': True}}]})
            self.state = 'pressed'
            self.ready_at = now + .15
        elif self.state == 'pressed' and now >= self.ready_at:
            self.command(qmp, 'input-send-event', {'events': [
                {'type': 'btn', 'data': {'button': 'left', 'down': False}}]})
            self.state = 'waiting-for-tap-marker'
        elif self.state in ('waiting-for-tap-marker', 'waiting-for-operator-tap-marker') and tapped in serial:
            self.report['tap_marker_observed'] = True
            self.state = ('waiting-for-updated-frame' if self.hardware_tap
                          else 'waiting-for-operator-after-capture')
            self.ready_at = now + 1
        elif self.state == 'waiting-for-updated-frame' and now >= self.ready_at:
            self.capture(qmp, 'probe-after')
            self.state = 'completed'
            self.report['completed'] = True
        self.report['state'] = self.state

    def finish(self):
        if not self.report['completed']:
            raise RuntimeError(f'Owned app journey incomplete: {self.state}')
