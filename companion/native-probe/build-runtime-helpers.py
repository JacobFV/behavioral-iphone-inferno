#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Build existing owned runtime helpers into NEW external output; no VM."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import plistlib
import re
import subprocess
import time

SOURCE = Path(__file__).resolve().parent
NAMES = (
    'probe.S', 'readiness.c', 'ioreg-touch.c', 'app-event-relay.c', 'app-event-proc.c',
    'unlock-empty.c', 'sample-control.c', 'sample-control.h', 'open-control.c',
    'open-control.h', 'hid-input.c', 'hid-input.h', 'hid-user-device.c',
    'libSystem.tbd', 'IOKit.tbd', 'hid-entitlements.plist', 'unlock-entitlements.plist',
    '../app-probe/EventRecord.h', '../app-probe/LoopbackEvent.h', '../app-probe/OwnedClock.h',
)
BINARIES = ('inferno-probe', 'inferno-readiness', 'inferno-hid-input', 'inferno-unlock-empty')
ENTITLEMENTS = {'inferno-hid-input': 'hid-entitlements.plist',
                'inferno-unlock-empty': 'unlock-entitlements.plist'}


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def write_json(path, value):
    with path.open('x') as stream:
        json.dump(value, stream, indent=2)
        stream.write('\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('clang', 'linker', 'ldid'):
        parser.add_argument('--' + name, type=Path, required=True)
        parser.add_argument('--' + name + '-sha256', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    output = None
    previous_umask = os.umask(0o077)
    try:
        spec = importlib.util.spec_from_file_location('owned_importer', SOURCE.parent / 'app-import.py')
        importer = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(importer)
        destination = importer.external_output(args.output)
        sources = {str(SOURCE / name): sha(SOURCE / name) for name in NAMES}
        implementation = {str(Path(__file__).resolve()): sha(__file__),
                          str(SOURCE.parent / 'app-import.py'): sha(SOURCE.parent / 'app-import.py')}
        revision = subprocess.check_output(['git', '-C', str(SOURCE), 'rev-parse', 'HEAD'], text=True).strip()
        # Require actual committed source, not a revision label for edited bytes.
        check_paths = [*sources, *implementation]
        for path in check_paths:
            subprocess.run(['git', '-C', str(SOURCE), 'ls-files', '--error-unmatch', path],
                           check=True, stdout=subprocess.DEVNULL)
        subprocess.run(['git', '-C', str(SOURCE), 'diff', '--exit-code', 'HEAD', '--', *check_paths], check=True)
        tools = {}
        for name in ('clang', 'linker', 'ldid'):
            invocation = getattr(args, name)
            expected = getattr(args, name + '_sha256')
            if not invocation.is_absolute() or not re.fullmatch('[0-9a-f]{64}', expected):
                raise ValueError('Absolute invocation and lowercase SHA256 required: ' + name)
            resolved = invocation.resolve(strict=True)
            if not resolved.is_file() or not os.access(invocation, os.X_OK) or sha(resolved) != expected:
                raise ValueError('Tool missing/nonexecutable/hash mismatch: ' + name)
            tools[name] = {'invocation': str(invocation), 'resolved': str(resolved), 'sha256': expected}
        if args.linker.name not in ('ld64.lld', 'ld64.lld-18'):
            raise ValueError('Use an explicit ld64.lld Mach-O driver invocation, not resolved lld basename')
        destination.mkdir(mode=0o700)
        output = destination
        write_json(output / 'INCOMPLETE.json', {'status': 'incomplete-do-not-consume', 'started': time.time()})
        commands = []
        readbacks = {}
        def compile_c(name, strict=False, define=None):
            command = [str(args.clang), '--target=arm64-apple-ios14', '-ffreestanding',
                       '-fno-stack-protector', '-fno-builtin', '-O2']
            if strict: command += ['-Wall', '-Wextra', '-Werror']
            if define: command += ['-D' + define]
            commands.append(command + ['-c', str(SOURCE / (name + '.c')), '-o', str(output / (name + '.o'))])
        def link(name, objects, entry='_main', iokit=False):
            command = [str(args.linker), '-arch', 'arm64', '-platform_version', 'ios', '14.0', '14.0',
                       '-e', entry, '-needed_library', str(SOURCE / 'libSystem.tbd'), '-no_uuid', '-adhoc_codesign']
            if iokit: command += ['-needed_library', str(SOURCE / 'IOKit.tbd')]
            commands.append(command + ['-o', str(output / name)] + [str(output / (obj + '.o')) for obj in objects])
        commands.append([str(args.clang), '--target=arm64-apple-ios14', '-c', str(SOURCE / 'probe.S'), '-o', str(output / 'probe.o')])
        link('inferno-probe', ['probe'], entry='_start')
        compile_c('ioreg-touch', strict=True, define='IOREG_TOUCH_LIBRARY')
        for name in ('app-event-relay', 'app-event-proc'): compile_c(name, strict=True)
        compile_c('readiness')
        link('inferno-readiness', ['readiness', 'ioreg-touch', 'app-event-relay', 'app-event-proc'], iokit=True)
        compile_c('unlock-empty')
        link('inferno-unlock-empty', ['unlock-empty'])
        for name in ('sample-control', 'open-control', 'hid-input', 'hid-user-device'): compile_c(name, strict=True)
        link('inferno-hid-input', ['hid-input', 'hid-user-device', 'open-control', 'sample-control'])
        for binary, entitlement in ENTITLEMENTS.items():
            commands.append([str(args.ldid), '-Cadhoc', '-S' + str(SOURCE / entitlement), str(output / binary)])
            readbacks[len(commands)] = binary + '-entitlements.plist'
            commands.append([str(args.ldid), '-e', str(output / binary)])
        records = []
        for index, command in enumerate(commands):
            stdout = output / readbacks.get(index, f'command-{index}.stdout')
            stderr = output / f'command-{index}.stderr'
            started = time.time()
            with stdout.open('xb') as out, stderr.open('xb') as err:
                result = subprocess.run(command, stdout=out, stderr=err, timeout=120, check=False)
            records.append({'argv': command, 'started': started, 'finished': time.time(),
                            'exit_code': result.returncode,
                            'stdout': {'path': str(stdout), 'sha256': sha(stdout)},
                            'stderr': {'path': str(stderr), 'sha256': sha(stderr)}})
            write_json(output / f'command-{index}.json', records[-1])
            if result.returncode:
                raise ValueError('Build command failed: ' + str(index))
        for binary, entitlement in ENTITLEMENTS.items():
            if plistlib.loads((output / (binary + '-entitlements.plist')).read_bytes()) != plistlib.loads((SOURCE / entitlement).read_bytes()):
                raise ValueError('Owned helper entitlement readback mismatch: ' + binary)
        for path, expected in {**sources, **implementation}.items():
            if sha(path) != expected:
                raise ValueError('Source changed during build: ' + path)
        for tool in tools.values():
            if str(Path(tool['invocation']).resolve(strict=True)) != tool['resolved'] or sha(tool['resolved']) != tool['sha256']:
                raise ValueError('Tool changed during build')
        if subprocess.check_output(['git', '-C', str(SOURCE), 'rev-parse', 'HEAD'], text=True).strip() != revision:
            raise ValueError('Source revision changed during build')
        outputs = {name: {'bytes': (output / name).stat().st_size, 'sha256': sha(output / name)}
                   for name in (*BINARIES, *readbacks.values())}
        record = {'status': 'built-owned-runtime-helpers-only; no guest execution yet',
                  'source_revision': revision, 'sources': sources, 'producer_sources': implementation,
                  'commands': commands, 'command_records': records, 'tools': tools, 'outputs': outputs,
                  'signing': 'Only existing owned helpers; LLVM ad-hoc markers and exact existing HID/unlock entitlement dictionaries; no imported or Apple executable signed'}
        write_json(output / 'build.json', record)
        (output / 'INCOMPLETE.json').unlink()
        print(json.dumps({'status': record['status'], 'build': str(output / 'build.json'),
                          'build_sha256': sha(output / 'build.json'), 'helpers': {name: outputs[name] for name in BINARIES}}))
        return 0
    except Exception as exc:
        if output is not None:
            write_json(output / 'failure.json', {'status': 'failed-do-not-consume', 'type': type(exc).__name__, 'error': str(exc)})
        parser.exit(1, str(exc) + '\n')
    finally:
        os.umask(previous_umask)


if __name__ == '__main__':
    raise SystemExit(main())
