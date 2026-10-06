#!/usr/bin/env python3
"""Read the restored service type/version through local libimobiledevice/usbmuxd."""
# SPDX-License-Identifier: AGPL-3.0-or-later
import argparse
import ctypes as C
import ctypes.util
import json


def query(udid):
    report = {'udid': udid, 'operation': 'restored_query_type',
              'restore_started': False, 'api_results': {}}
    library = ctypes.util.find_library('imobiledevice-1.0')
    if not library:
        raise RuntimeError('libimobiledevice-1.0 is not installed')
    lib = C.CDLL(library)
    signatures = {
        'idevice_new': [C.POINTER(C.c_void_p), C.c_char_p],
        'idevice_free': [C.c_void_p],
        'restored_client_new': [C.c_void_p, C.POINTER(C.c_void_p), C.c_char_p],
        'restored_client_free': [C.c_void_p],
        'restored_query_type': [C.c_void_p, C.POINTER(C.c_char_p), C.POINTER(C.c_uint64)],
    }
    for name, arguments in signatures.items():
        function = getattr(lib, name)
        function.argtypes = arguments
        function.restype = C.c_int
    libc = C.CDLL(None)
    libc.free.argtypes = [C.c_void_p]
    libc.free.restype = None
    device = C.c_void_p()
    client = C.c_void_p()
    kind = C.c_char_p()
    version = C.c_uint64()
    try:
        result = lib.idevice_new(C.byref(device), udid.encode())
        report['api_results']['idevice_new'] = result
        if result:
            return report
        result = lib.restored_client_new(device, C.byref(client), b'inferno-readonly-query')
        report['api_results']['restored_client_new'] = result
        if result:
            return report
        result = lib.restored_query_type(client, C.byref(kind), C.byref(version))
        report['api_results']['restored_query_type'] = result
        if not result:
            report['type'] = kind.value.decode() if kind.value else None
            report['version'] = version.value
    finally:
        if kind:
            libc.free(C.cast(kind, C.c_void_p))
        if client:
            report['api_results']['restored_client_free'] = lib.restored_client_free(client)
        if device:
            report['api_results']['idevice_free'] = lib.idevice_free(device)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--udid', required=True, help='exact identifier reported by idevice_id -l')
    args = parser.parse_args()
    try:
        report = query(args.udid)
        passed = (report.get('type') == 'com.apple.mobile.restored' and
                  all(value == 0 for value in report['api_results'].values()))
        report['passed'] = passed
    except (OSError, RuntimeError, AttributeError, UnicodeError) as exc:
        report = {'passed': False, 'operation': 'restored_query_type', 'error': str(exc)}
        passed = False
    print(json.dumps(report, sort_keys=True))
    return 0 if passed else 1


if __name__ == '__main__':
    raise SystemExit(main())
