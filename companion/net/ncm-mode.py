#!/usr/bin/env python3
"""Run inside the USB companion (root): read and set the emulated iPhone's USB "mode" so iOS
exposes its CDC-NCM (reverse tethering) interface, then select the configuration that has it.

Same vendor requests usbmuxd sends for USBMUXD_DEFAULT_DEVICE_MODE (usbmuxd src/usb.c):
  GET_MODE: bmRequestType 0xC0, bRequest 0x45, wValue 0, wIndex 0, wLength 4
  SET_MODE: bmRequestType 0xC0, bRequest 0x52, wValue 0, wIndex MODE, wLength 1
Modes: 1 initial, 2 Valeria, 3 CDC-NCM, 4 USB Ethernet + CDC-NCM, 5 CDC-NCM direct.

ncm-mode.py [get|set MODE|configs|select N]"""
import sys, time
import usb.core

APPLE = 0x05ac

def dev():
    d = usb.core.find(idVendor=APPLE)
    if d is None:
        raise SystemExit('no Apple USB device')
    return d

def configs(d):
    for c in d:
        ifs = [(i.bInterfaceNumber, i.bAlternateSetting, i.bInterfaceClass, i.bInterfaceSubClass, i.bInterfaceProtocol) for i in c]
        print('config', c.bConfigurationValue, 'interfaces (num,alt,class,sub,proto):', ifs)

def main(argv):
    cmd = argv[1] if len(argv) > 1 else 'get'
    d = dev()
    print('device %04x:%04x serial=%s active-config=%s' % (d.idVendor, d.idProduct, usb.util.get_string(d, d.iSerialNumber), d.get_active_configuration().bConfigurationValue))
    if cmd == 'get':
        print('mode bytes', list(d.ctrl_transfer(0xC0, 0x45, 0, 0, 4, timeout=2000)))
    elif cmd == 'set':
        print('set result', list(d.ctrl_transfer(0xC0, 0x52, 0, int(argv[2]), 1, timeout=2000)))
    elif cmd == 'configs':
        configs(d)
    elif cmd == 'select':
        for i in d.get_active_configuration():
            if d.is_kernel_driver_active(i.bInterfaceNumber):
                d.detach_kernel_driver(i.bInterfaceNumber)
        d.set_configuration(int(argv[2])); time.sleep(1)
        print('active config now', d.get_active_configuration().bConfigurationValue)

if __name__ == '__main__':
    main(sys.argv)
