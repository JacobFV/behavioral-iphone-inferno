#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Build/import the owned navigation IPA and fixed launch helpers. No guest actions."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile

TOOL_HASHES = {
    'clang': '6d99f6207153b8b2063ace5d2a6177debaf6a6b6f31649e03afac07b98ba0b4d',
    'linker': 'f8835e48488195c65fb3dcb946053284ddf6b1369922893785209a9073c4e57b',
}

def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--clang', required=True)
    parser.add_argument('--linker', required=True)
    args = parser.parse_args()
    source = Path(__file__).resolve().parent
    companion = source.parent
    tools = {}
    for name in TOOL_HASHES:
        found = shutil.which(getattr(args, name))
        if not found:
            parser.error('Missing tool: ' + name)
        # Preserve ld64.lld's invocation basename: the same binary selects its
        # object-format driver from argv[0]. Hashing still follows the symlink.
        tools[name] = os.path.abspath(found)
        if sha(tools[name]) != TOOL_HASHES[name]:
            parser.error('Tool differs from reviewed LLVM18 build: ' + name)
    paths = [source / name for name in ('build.py', 'Main.m', 'NavigationNarrow.h', 'Info.plist', 'Guide.txt', 'UIKit.tbd')]
    paths += [companion / 'app-import.py']
    paths += [companion / 'app-probe' / name for name in (
        'build-import-launcher.py', 'UIKitNarrow.h', 'LaunchServicesNarrow.h',
        'DiagnosticLauncher.m', 'Launcher.m', 'EventRecord.h', 'OwnedClock.h',
        'ExecLauncher.c', 'AppTarget.h',
        'org.inferno.app-probe-system-app.plist')]
    paths += sorted((companion / 'app-probe/stubs').glob('*.tbd'))
    pins = {str(path): sha(path) for path in paths}
    spec = importlib.util.spec_from_file_location('navigation_importer', companion / 'app-import.py')
    importer = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(importer)
    output = importer.external_output(args.output)
    old_umask = os.umask(0o077)
    try:
        output.mkdir(mode=0o700)
        (output / 'INCOMPLETE').write_text('Host build/import only; not an execution result.\n')
        commands = []
        def run(argv):
            commands.append(argv)
            with (output / 'build.log').open('ab') as log:
                log.write((json.dumps(argv) + '\n').encode()); log.flush()
                subprocess.run(argv, check=True, stdout=log, stderr=subprocess.STDOUT)
        bundle = output / 'Payload/NavigationDemo.app'
        bundle.mkdir(parents=True)
        obj = output / 'Main.o'
        executable = bundle / 'NavigationDemo'
        run([tools['clang'], '--target=arm64-apple-ios14', '-fobjc-runtime=ios-14.0',
             '-fno-objc-arc', '-fno-stack-protector', '-ffreestanding', '-O2',
             '-Wall', '-Wextra', '-Werror', '-c', str(source / 'Main.m'), '-o', str(obj)])
        command = [tools['linker'], '-arch', 'arm64', '-platform_version', 'ios', '14.0', '14.0',
                   '-e', '_main', '-no_uuid', '-adhoc_codesign']
        for library in ('libSystem', 'libobjc', 'Foundation', 'UIKit'):
            stub = source / 'UIKit.tbd' if library == 'UIKit' else companion / 'app-probe/stubs' / (library + '.tbd')
            command += ['-needed_library', str(stub)]
        run(command + [str(obj), '-o', str(executable)])
        executable.chmod(0o755)
        for name in ('Info.plist', 'Guide.txt'):
            shutil.copyfile(source / name, bundle / name)
            (bundle / name).chmod(0o644)
        ipa = output / 'NavigationDemo.ipa'
        with zipfile.ZipFile(ipa, 'x', compression=zipfile.ZIP_DEFLATED) as archive:
            for file in sorted(bundle.iterdir()):
                entry = zipfile.ZipInfo(str(file.relative_to(output)), date_time=(2026, 1, 1, 0, 0, 0))
                entry.create_system = 3
                entry.external_attr = (0o100000 | (0o755 if file == executable else 0o644)) << 16
                entry.compress_type = zipfile.ZIP_DEFLATED
                archive.writestr(entry, file.read_bytes())
        # The unchanged importer creates validated 0755 bundle directories via
        # mkdir; allow those bits inside our already-private 0700 output root.
        os.umask(0o022)
        try:
            importer.import_ipa(ipa, output / 'imported')
        finally:
            os.umask(0o077)
        manifest_path = output / 'imported/manifest.json'
        manifest = importer.validate_manifest(manifest_path)
        run([sys.executable, str(companion / 'app-probe/build-import-launcher.py'),
             '--manifest', str(manifest_path), '--manifest-sha256', sha(manifest_path),
             '--clang', tools['clang'], '--linker', tools['linker'], '--output', str(output / 'launcher')])
        if pins != {path: sha(path) for path in pins} or any(sha(tools[name]) != value for name, value in TOOL_HASHES.items()):
            raise ValueError('Source/tool drift; output remains incomplete')
        result = {
            'status': 'built-and-import-validated-not-executed',
            'guest_actions': False, 'commands': commands, 'sources': pins,
            'git_revision': subprocess.check_output(['git', '-C', str(source), 'rev-parse', 'HEAD'], text=True).strip(),
            'tools': {name: {'path': path, 'resolved_path': str(Path(path).resolve(strict=True)), 'sha256': sha(path), 'version': subprocess.check_output([path, '--version'], text=True).strip()} for name, path in tools.items()},
            'ipa': {'path': str(ipa), 'sha256': sha(ipa), 'bytes': ipa.stat().st_size},
            'manifest': {'path': str(manifest_path), 'sha256': sha(manifest_path), 'tree_sha256': manifest['tree_sha256']},
            'bundle_files': {f.name: {'sha256': sha(f), 'bytes': f.stat().st_size} for f in sorted(bundle.iterdir())},
            'build_log_sha256': sha(output / 'build.log'),
            'limitations': ['UIKit dynamic class existence and selectors require guest validation.',
                            'No guest staging, launch, navigation, scrolling, switch, save, or resource display asserted.',
                            'Fixed portrait research fixture, not arbitrary IPA or Linux Xcode compatibility.'],
        }
        with (output / 'build-evidence.json').open('x') as stream:
            json.dump(result, stream, indent=2); stream.write('\n')
        (output / 'INCOMPLETE').unlink()
        print(json.dumps(result, indent=2))
    finally:
        os.umask(old_umask)

if __name__ == '__main__':
    main()
