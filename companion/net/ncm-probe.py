#!/usr/bin/env python3
"""Run inside the USB companion (root) with the iPhone in USB configuration 5 (CDC-NCM).
Talks NCM from userspace to see whether the iOS side answers: releases cdc_ncm, selects the data
alternate setting, asks for NTB parameters, then listens on the notification (interrupt) and
data (bulk) endpoints for a while, printing whatever arrives."""
import struct, sys, time
import usb.core, usb.util

d = usb.core.find(idVendor=0x05ac)
cfg = d.get_active_configuration()
print('active config', cfg.bConfigurationValue)
for n in (2, 3):
    if d.is_kernel_driver_active(n):
        d.detach_kernel_driver(n); print('detached kernel driver from interface', n)
usb.util.claim_interface(d, 2); usb.util.claim_interface(d, 3)
# GET_NTB_PARAMETERS (class request 0x80 on the communication interface)
try:
    p = bytes(d.ctrl_transfer(0xA1, 0x80, 0, 2, 28, timeout=2000))
    print('NTB parameters', p.hex(), struct.unpack('<HHIHHHHIHHHH', p[:28]) if len(p) >= 28 else len(p))
except usb.core.USBError as e:
    print('GET_NTB_PARAMETERS failed', e)
d.set_interface_altsetting(interface=3, alternate_setting=1); print('data interface alt 1 selected')
end = time.time() + float(sys.argv[1] if len(sys.argv) > 1 else 60)
while time.time() < end:
    for ep, size in ((0x86, 64), (0x87, 16384)):
        try:
            data = bytes(d.read(ep, size, timeout=1000))
            print(time.strftime('%T'), 'ep %#x %d bytes: %s' % (ep, len(data), data[:96].hex()))
        except usb.core.USBTimeoutError:
            pass
        except usb.core.USBError as e:
            print('ep %#x error %s' % (ep, e)); time.sleep(1)
print('done')
