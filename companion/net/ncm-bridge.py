#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Userspace CDC-NCM bridge, run as root inside the USB companion VM.

Linux's cdc_ncm keeps the link NO-CARRIER because iOS never sends the NCM
NetworkConnection notification, so usbnet moves no frames. This bypasses it:
it claims the iPhone's NCM interfaces with pyusb, selects the data alternate
setting, and copies Ethernet frames between NTB16 transfers and a TAP device.
Then serves the guest a gateway, DNS and NAT on that TAP.

  ncm-bridge.py [--tap ncm0] [--host 192.168.77.1/24]

Prerequisite: the phone is in USB configuration 5 (net/ncm-mode.py set 3).
"""
import argparse, fcntl, os, struct, subprocess, sys, threading, time
import usb.core, usb.util

TUNSETIFF, IFF_TAP, IFF_NO_PI = 0x400454CA, 0x0002, 0x1000


def log(*a):
    print(time.strftime('%T'), *a, flush=True)


def open_tap(name):
    fd = os.open('/dev/net/tun', os.O_RDWR)
    fcntl.ioctl(fd, TUNSETIFF, struct.pack('16sH', name.encode(), IFF_TAP | IFF_NO_PI))
    return fd


def find_ncm(dev):
    cfg = dev.get_active_configuration()
    ctrl = data = None
    for intf in cfg:
        if intf.bInterfaceClass == 0x02 and intf.bInterfaceSubClass == 0x0D:
            ctrl = intf
        if intf.bInterfaceClass == 0x0A and intf.bAlternateSetting == 1:
            data = intf
    if ctrl is None or data is None:
        sys.exit('phone is not in an NCM configuration (active config %d); run ncm-mode.py set 3' % cfg.bConfigurationValue)
    ep_in = next(e.bEndpointAddress for e in data if e.bEndpointAddress & 0x80)
    ep_out = next(e.bEndpointAddress for e in data if not e.bEndpointAddress & 0x80)
    mps = next(e.wMaxPacketSize for e in data if not e.bEndpointAddress & 0x80)
    return cfg, ctrl.bInterfaceNumber, data.bInterfaceNumber, ep_in, ep_out, mps


def parse_ntb16(buf):
    """Yield Ethernet frames from one NTB16 transfer."""
    if len(buf) < 12 or buf[:4] != b'NCMH':
        return
    _, _, _, block_len, ndp = struct.unpack_from('<4sHHHH', buf, 0)
    seen = 0
    while ndp and ndp + 8 <= len(buf) and seen < 16:
        seen += 1
        sig, ndp_len, nxt = struct.unpack_from('<4sHH', buf, ndp)
        if sig[:3] != b'NCM':
            return
        off = ndp + 8
        while off + 4 <= ndp + ndp_len:
            index, length = struct.unpack_from('<HH', buf, off)
            off += 4
            if not index or not length:
                break
            yield bytes(buf[index:index + length])
        ndp = nxt


def build_ntb16(frame, seq, mps):
    # NTH16 (12) | NDP16 at 12: sig, len 16, next 0, (28, len), (0, 0) | datagram at 28
    total = 28 + len(frame)
    pad = 1 if total % mps == 0 else 0  # avoid a transfer that ends on a packet boundary
    total += pad
    nth = struct.pack('<4sHHHH', b'NCMH', 12, seq & 0xFFFF, total, 12)
    ndp = struct.pack('<4sHHHHHH', b'NCM0', 16, 0, 28, len(frame), 0, 0)
    return nth + ndp + frame + b'\0' * pad


def sh(cmd):
    log('$', cmd)
    subprocess.run(cmd, shell=True, check=False)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--tap', default='ncm0')
    ap.add_argument('--host', default='192.168.77.1/24')
    ap.add_argument('--no-nat', action='store_true')
    args = ap.parse_args()

    dev = usb.core.find(idVendor=0x05AC)
    if dev is None:
        sys.exit('no Apple device on the USB bus')
    cfg, ctrl_if, data_if, ep_in, ep_out, mps = find_ncm(dev)
    log('config', cfg.bConfigurationValue, 'ctrl if', ctrl_if, 'data if', data_if,
        'in %#x out %#x mps %d' % (ep_in, ep_out, mps))
    for n in (ctrl_if, data_if):
        if dev.is_kernel_driver_active(n):
            dev.detach_kernel_driver(n)
            log('detached kernel driver from interface', n)
        usb.util.claim_interface(dev, n)
    try:
        p = bytes(dev.ctrl_transfer(0xA1, 0x80, 0, ctrl_if, 28, timeout=2000))
        log('NTB parameters', p.hex())
    except usb.core.USBError as e:
        log('GET_NTB_PARAMETERS failed', e)
    # What a host's NCM driver sends before data flows (Linux cdc_ncm / macOS AppleUSBNCM): NTB16 format,
    # our NTB input size, and an Ethernet packet filter; then the data interface is reset to alternate 0
    # (no endpoints) and back to 1. A device function may hold its data endpoints idle until the filter is set.
    for name, req, value, data in (('SET_NTB_FORMAT(NTB16)', 0x84, 0, None),
                                   ('SET_NTB_INPUT_SIZE', 0x86, 0, struct.pack('<I', 16384)),
                                   ('SET_ETHERNET_PACKET_FILTER', 0x43, 0x001F, None)):
        try:
            dev.ctrl_transfer(0x21, req, value, ctrl_if, data, timeout=2000)
            log(name, 'ok')
        except usb.core.USBError as e:
            log(name, 'failed', e)
    dev.set_interface_altsetting(interface=data_if, alternate_setting=0)
    dev.set_interface_altsetting(interface=data_if, alternate_setting=1)

    tap = open_tap(args.tap)
    sh('ip link set %s up' % args.tap)
    sh('ip addr replace %s dev %s' % (args.host, args.tap))
    if not args.no_nat:
        up = subprocess.run("ip route show default | awk '{print $5; exit}'", shell=True,
                            capture_output=True, text=True).stdout.strip()
        net = args.host.rsplit('.', 1)[0] + '.0/24'
        sh('sysctl -q -w net.ipv4.ip_forward=1')
        sh('iptables -t nat -C POSTROUTING -s %s -o %s -j MASQUERADE 2>/dev/null || '
           'iptables -t nat -A POSTROUTING -s %s -o %s -j MASQUERADE' % (net, up, net, up))
        # Stop an earlier instance by its pid file. Not `pkill -f "dnsmasq.*inferno-ncm"`: that pattern
        # matches this very shell's command line (which names dnsmasq and the pid file), so pkill killed
        # the shell and dnsmasq never started; iOS's DNS queries then met "port 53 unreachable".
        sh('[ -f /run/inferno-ncm-dnsmasq.pid ] && kill $(cat /run/inferno-ncm-dnsmasq.pid) 2>/dev/null; sleep 1')
        sh('dnsmasq --conf-file=/dev/null --pid-file=/run/inferno-ncm-dnsmasq.pid '
           '--listen-address=%s --bind-interfaces --no-resolv --server=8.8.8.8 --server=1.1.1.1 '
           '--dhcp-range=%s.10,%s.50,12h --dhcp-option=3,%s --dhcp-option=6,%s '
           '--log-facility=/var/log/inferno-ncm-dnsmasq.log --log-queries --dhcp-authoritative'
           % (args.host.split('/')[0], args.host.rsplit('.', 1)[0], args.host.rsplit('.', 1)[0],
              args.host.split('/')[0], args.host.split('/')[0]))
        sh('ss -lun | grep -q "%s:53 " && echo DNS-LISTENING || echo DNS-NOT-LISTENING' % args.host.split('/')[0])

    counts = {'rx': 0, 'tx': 0}

    def usb_to_tap():
        while True:
            try:
                buf = dev.read(ep_in, 16384, timeout=0)
            except usb.core.USBTimeoutError:
                continue
            except usb.core.USBError as e:
                log('usb read error', e)
                time.sleep(0.5)
                continue
            for frame in parse_ntb16(bytes(buf)):
                os.write(tap, frame)
                counts['rx'] += 1

    def tap_to_usb():
        seq = 0
        while True:
            frame = os.read(tap, 2048)
            try:
                dev.write(ep_out, build_ntb16(frame, seq, mps), timeout=2000)
                counts['tx'] += 1
            except usb.core.USBError as e:
                log('usb write error', e)
            seq += 1

    for f in (usb_to_tap, tap_to_usb):
        threading.Thread(target=f, daemon=True).start()
    log('bridge up: %s %s <-> iPhone NCM' % (args.tap, args.host))
    while True:
        time.sleep(10)
        log('frames from iPhone %d, to iPhone %d' % (counts['rx'], counts['tx']))


if __name__ == '__main__':
    main()
