#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Build owned launch helpers for one validated imported device app.

This neither rebuilds nor signs the imported app. Guest staging and execution
are separate steps; generic apps do not acquire the probe's telemetry protocol.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import plistlib
import shutil
import subprocess


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', required=True, type=Path)
    parser.add_argument('--manifest-sha256', required=True)
    parser.add_argument('--clang', default='clang')
    parser.add_argument('--linker', required=True)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    source = Path(__file__).resolve().parent
    repo = source.parent.parent
    if sha(args.manifest) != args.manifest_sha256:
        parser.error('import manifest SHA256 mismatch')
    spec = importlib.util.spec_from_file_location('inferno_app_import', source.parent / 'app-import.py')
    importer = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(importer)
    manifest = importer.validate_manifest(args.manifest)
    bundle = manifest['bundle']
    output = importer.external_output(args.output)
    clang, linker = shutil.which(args.clang), shutil.which(args.linker)
    if not clang or not linker:
        parser.error('clang and ld64.lld are required')
    clang, linker = os.path.abspath(clang), os.path.abspath(linker)
    output.mkdir(parents=True)
    header = output / 'ImportedAppTarget.h'
    header.write_text('#define INFERNO_MANIFEST_TARGET 1\n' +
                      '#define INFERNO_APP_IDENTIFIER ' + json.dumps(bundle['identifier']) + '\n' +
                      '#define INFERNO_SYSTEM_APP_PATH ' + json.dumps(bundle['guest_path']) + '\n')
    commands = []

    def run(command):
        commands.append(command)
        with (output / 'build.log').open('ab') as log:
            log.write((json.dumps(command) + '\n').encode())
            log.flush()
            subprocess.run(command, check=True, stdout=log, stderr=subprocess.STDOUT)

    for name, extension, executable, libraries, flags in (
        ('DiagnosticLauncher', 'm', 'inferno-launcher',
         ('libSystem', 'libobjc', 'Foundation', 'CoreServices'), ('-fblocks',)),
        ('ExecLauncher', 'c', 'inferno-exec-launcher', ('libSystem',), ())
    ):
        obj = output / (name + '.o')
        run([clang, '--target=arm64-apple-ios14', '-fobjc-runtime=ios-14.0',
             '-fno-objc-arc', '-fno-stack-protector', '-ffreestanding', '-O2',
             '-Wall', '-Wextra', '-include', str(header), *flags,
             '-c', str(source / (name + '.' + extension)), '-o', str(obj)])
        command = [linker, '-arch', 'arm64', '-platform_version', 'ios', '14.0', '14.0',
                   '-e', '_main', '-no_uuid', '-adhoc_codesign']
        for library in libraries:
            command += ['-needed_library', str(source / 'stubs' / (library + '.tbd'))]
        run(command + [str(obj), '-o', str(output / executable)])
    # Replaces only the existing owned job via merge-launchd-cache.py. The
    # wrapper drops to mobile before invoking the manifest-bound launcher.
    job = plistlib.loads((source / 'org.inferno.app-probe-system-app.plist').read_bytes())
    job_path = output / 'org.inferno.app-probe.plist'
    job_path.write_bytes(plistlib.dumps(job))
    # Catch changed input between validation and generated-artifact recording.
    importer.validate_manifest(args.manifest)
    if sha(args.manifest) != args.manifest_sha256:
        raise ValueError('import manifest changed during build')
    record = {
        'status': 'built-not-staged-or-executed',
        'manifest_path': str(args.manifest.resolve()),
        'manifest_sha256': args.manifest_sha256,
        'target': bundle,
        'git_revision': subprocess.check_output(['git', '-C', str(repo), 'rev-parse', 'HEAD'], text=True).strip(),
        'commands': commands,
        'tools': {p: {'sha256': sha(Path(p)), 'version': subprocess.check_output([p, '--version'], text=True).strip()}
                  for p in (clang, linker)},
        'sources': {str(p.relative_to(source)): sha(p) for p in sorted(source.rglob('*')) if p.is_file()},
        'importer_sha256': sha(source.parent / 'app-import.py'),
        'outputs': {p.name: sha(p) for p in (header, job_path, output / 'inferno-launcher', output / 'inferno-exec-launcher')},
        'limits': ['Only owned helpers receive LLVM ad-hoc signatures; imported app bytes are unchanged.',
                   'System-path research VM staging is not normal App Store installation.',
                   'Generic apps need independent original process and pixel evidence; probe telemetry and controlled OPEN are not generalized.'],
    }
    (output / 'build-evidence.json').write_text(json.dumps(record, indent=2) + '\n')
    print(json.dumps(record, indent=2))


if __name__ == '__main__':
    main()
