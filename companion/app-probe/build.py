#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Build an owned ARM64 UIKit probe without an Apple SDK."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def signature(path):
    data = path.read_bytes()
    magic, cpu, _, filetype, ncmds, _, _, _ = struct.unpack_from('<8I', data)
    if (magic, cpu, filetype) != (0xfeedfacf, 0x100000c, 2):
        raise ValueError('Expected ARM64 Mach-O executable')
    offset = 32
    for _ in range(ncmds):
        cmd, size = struct.unpack_from('<II', data, offset)
        if cmd == 0x1d:
            start, length = struct.unpack_from('<II', data, offset + 8)
            blob = data[start:start + length]
            kind, _, count = struct.unpack_from('>III', blob)
            if kind != 0xfade0cc0:
                raise ValueError('Expected signature superblob')
            for index in range(count):
                slot, position = struct.unpack_from('>II', blob, 12 + index * 8)
                if slot == 0:
                    kind, cd_length, version, flags = struct.unpack_from('>IIII', blob, position)
                    if kind != 0xfade0c02 or not flags & 2:
                        raise ValueError('Expected own ad-hoc CodeDirectory')
                    return {'flags': flags, 'version': version, 'code_directory_sha256':
                            hashlib.sha256(blob[position:position + cd_length]).hexdigest()}
        offset += size
    raise ValueError('No ad-hoc CodeDirectory found')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--clang', default='clang')
    parser.add_argument('--linker', required=True)
    parser.add_argument('--output', required=True, type=Path,
                        help='Fresh directory outside the repository')
    args = parser.parse_args()
    source = Path(__file__).resolve().parent
    repo = source.parent.parent
    output = args.output.resolve()
    if output.is_relative_to(repo):
        parser.error('--output must be outside the repository')
    if output.exists():
        parser.error('--output must be a fresh directory')
    # Keep the linker invocation basename: lld selects its driver from argv[0].
    clang = shutil.which(args.clang)
    linker = shutil.which(args.linker)
    if not clang or not linker:
        parser.error('clang and ld64.lld must be installed or supplied by absolute path')
    clang, linker = os.path.abspath(clang), os.path.abspath(linker)
    output.mkdir(parents=True)
    bundle = output / 'InfernoProbe.app'
    bundle.mkdir()
    commands = []

    def run(argv):
        commands.append(argv)
        with (output / 'build.log').open('ab') as log:
            log.write((json.dumps(argv) + '\n').encode())
            log.flush()
            subprocess.run(argv, check=True, stdout=log, stderr=subprocess.STDOUT)

    def build(name, executable, libraries):
        obj = output / (name + '.o')
        run([clang, '--target=arm64-apple-ios14', '-fobjc-runtime=ios-14.0',
             '-fno-objc-arc', '-fno-stack-protector', '-ffreestanding', '-O2',
             '-Wall', '-Wextra', '-c', str(source / (name + '.m')), '-o', str(obj)])
        command = [linker, '-arch', 'arm64', '-platform_version', 'ios', '14.0', '14.0',
                   '-e', '_main', '-no_uuid', '-adhoc_codesign']
        for library in libraries:
            command += ['-needed_library', str(source / 'stubs' / (library + '.tbd'))]
        run(command + [str(obj), '-o', str(executable)])

    build('Main', bundle / 'InfernoProbe', ('libSystem', 'libobjc', 'Foundation', 'UIKit'))
    build('Launcher', output / 'inferno-launcher', ('libSystem', 'libobjc', 'Foundation', 'CoreServices'))
    shutil.copyfile(source / 'Info.plist', bundle / 'Info.plist')
    shutil.copyfile(source / 'org.inferno.app-probe.plist', output / 'org.inferno.app-probe.plist')
    evidence = {
        'status': 'built; guest installation and execution untested',
        'git_revision': subprocess.check_output(['git', '-C', str(repo), 'rev-parse', 'HEAD'], text=True).strip(),
        'commands': commands,
        'tools': {path: {'resolved': str(Path(path).resolve()), 'sha256': sha(path),
                         'version': subprocess.check_output([path, '--version'], text=True).strip()}
                  for path in (clang, linker)},
        'sources': {str(path.relative_to(source)): sha(path) for path in sorted(source.rglob('*')) if path.is_file()},
        'bundle': {path.name: sha(path) for path in sorted(bundle.iterdir())},
        'launcher_sha256': sha(output / 'inferno-launcher'),
        'signing': {'method': 'LLVM ad-hoc; no certificate or Apple identity',
                    'app': signature(bundle / 'InfernoProbe'),
                    'launcher': signature(output / 'inferno-launcher')},
    }
    (output / 'build-evidence.json').write_text(json.dumps(evidence, indent=2) + '\n')
    print(bundle)


if __name__ == '__main__':
    main()
