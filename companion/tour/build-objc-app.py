#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Build an owned Objective-C/C app on Linux into an IPA, import-validate it and build its launch
helpers. Generalises ipa-demo/build.py to several sources, extra flags and per-app stub overrides.

build-objc-app.py --source DIR --name Exe --output NEW_DIR --clang C --linker LD
  DIR holds Info.plist, sources (*.m, *.c), optional resources/ (copied into the bundle) and
  optional *.tbd stubs that replace the shared ones in app-probe/stubs by file name."""
import argparse, hashlib, importlib.util, json, os, shutil, subprocess, zipfile
from pathlib import Path

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source', type=Path, required=True); p.add_argument('--name', required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--clang', required=True); p.add_argument('--linker', required=True)
    p.add_argument('--cflag', action='append', default=[]); p.add_argument('--lib', action='append', default=[],
                   help='extra stub name (without .tbd) to link, from DIR or app-probe/stubs')
    a = p.parse_args(); src = a.source.resolve(); companion = Path(__file__).resolve().parents[1]
    spec = importlib.util.spec_from_file_location('app_import', companion / 'app-import.py')
    importer = importlib.util.module_from_spec(spec); spec.loader.exec_module(importer)
    out = importer.external_output(a.output); out.mkdir()
    bundle = out / 'Payload' / f'{a.name}.app'; bundle.mkdir(parents=True)
    commands = []
    def run(argv):
        commands.append([str(x) for x in argv])
        with (out / 'build.log').open('ab') as log:
            log.write((json.dumps(commands[-1]) + '\n').encode()); log.flush()
            subprocess.run(argv, check=True, stdout=log, stderr=subprocess.STDOUT)
    objs = []
    for s in sorted(list(src.glob('*.m')) + list(src.glob('*.c'))):
        o = out / (s.stem + '.o'); objs.append(o)
        run([a.clang, '--target=arm64-apple-ios14', '-fobjc-runtime=ios-14.0', '-fno-objc-arc', '-fno-stack-protector',
             '-ffreestanding', '-O2', '-Wall', *a.cflag, '-c', s, '-o', o])
    exe = bundle / a.name
    cmd = [a.linker, '-arch', 'arm64', '-platform_version', 'ios', '14.0', '14.0', '-e', '_main', '-no_uuid', '-adhoc_codesign']
    for lib in ['libSystem', 'libobjc', 'Foundation', 'UIKit', *a.lib]:
        local = src / f'{lib}.tbd'
        cmd += ['-needed_library', local if local.exists() else companion / 'app-probe/stubs' / f'{lib}.tbd']
    run(cmd + objs + ['-o', exe]); exe.chmod(0o755)
    shutil.copyfile(src / 'Info.plist', bundle / 'Info.plist'); (bundle / 'Info.plist').chmod(0o644)
    if (src / 'resources').is_dir():
        for f in sorted((src / 'resources').rglob('*')):
            d = bundle / f.relative_to(src / 'resources')
            if f.is_dir(): d.mkdir(exist_ok=True); d.chmod(0o755)
            else: d.parent.mkdir(parents=True, exist_ok=True); shutil.copyfile(f, d); d.chmod(0o644)
    ipa = out / f'{a.name}.ipa'
    with zipfile.ZipFile(ipa, 'w', compression=zipfile.ZIP_DEFLATED) as z:
        for f in sorted(bundle.rglob('*')):
            if f.is_dir(): continue
            info = zipfile.ZipInfo(str(f.relative_to(out)), date_time=(2026, 1, 1, 0, 0, 0)); info.create_system = 3
            info.external_attr = (0o100000 | (0o755 if f == exe else 0o644)) << 16
            info.compress_type = zipfile.ZIP_DEFLATED; z.writestr(info, f.read_bytes())
    importer.import_ipa(ipa, out / 'imported')
    manifest = out / 'imported/manifest.json'; importer.validate_manifest(manifest)
    record = {'status': 'built-and-import-validated-not-executed', 'app': a.name,
              'git_revision': subprocess.check_output(['git', '-C', str(companion), 'rev-parse', 'HEAD'], text=True).strip(),
              'commands': commands, 'ipa': {'path': str(ipa), 'sha256': sha(ipa)},
              'manifest': {'path': str(manifest), 'sha256': sha(manifest)},
              'sources': {str(f.relative_to(src)): sha(f) for f in sorted(src.rglob('*')) if f.is_file()}}
    (out / 'build-evidence.json').write_text(json.dumps(record, indent=2) + '\n')
    print(json.dumps({'ipa': record['ipa'], 'manifest': record['manifest']}))

if __name__ == '__main__':
    main()
