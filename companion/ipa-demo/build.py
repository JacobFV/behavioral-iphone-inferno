#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Build an owned demo IPA, validate it, and build its fixed launch helpers. No VM actions."""
import argparse, hashlib, importlib.util, json, os, shutil, subprocess, zipfile
from pathlib import Path

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--clang',default='clang')
    p.add_argument('--linker',required=True)
    a=p.parse_args(); source=Path(__file__).resolve().parent; companion=source.parent
    spec=importlib.util.spec_from_file_location('app_import',companion/'app-import.py')
    importer=importlib.util.module_from_spec(spec); spec.loader.exec_module(importer)
    output=importer.external_output(a.output)
    clang=shutil.which(a.clang); linker=shutil.which(a.linker)
    if not clang or not linker: p.error('clang and ld64.lld required')
    clang=os.path.abspath(clang); linker=os.path.abspath(linker)
    output.mkdir(); bundle=output/'Payload'/'ImportedDemo.app'; bundle.mkdir(parents=True)
    commands=[]
    def run(argv):
        commands.append(argv)
        with (output/'build.log').open('ab') as log:
            log.write((json.dumps(argv)+'\n').encode()); log.flush()
            subprocess.run(argv,check=True,stdout=log,stderr=subprocess.STDOUT)
    obj=output/'Main.o'; exe=bundle/'ImportedDemo'
    run([clang,'--target=arm64-apple-ios14','-fobjc-runtime=ios-14.0','-fno-objc-arc','-fno-stack-protector','-ffreestanding','-O2','-Wall','-Wextra','-c',str(source/'Main.m'),'-o',str(obj)])
    cmd=[linker,'-arch','arm64','-platform_version','ios','14.0','14.0','-e','_main','-no_uuid','-adhoc_codesign']
    for lib in ('libSystem','libobjc','Foundation','UIKit'): cmd+=['-needed_library',str(companion/'app-probe/stubs'/f'{lib}.tbd')]
    run(cmd+[str(obj),'-o',str(exe)])
    exe.chmod(0o755)
    for name in ('Info.plist','Message.txt'):
        shutil.copyfile(source/name,bundle/name); (bundle/name).chmod(0o644)
    ipa=output/'ImportedDemo.ipa'
    with zipfile.ZipFile(ipa,'w',compression=zipfile.ZIP_DEFLATED) as archive:
        for file in sorted(bundle.iterdir()):
            info=zipfile.ZipInfo(str(file.relative_to(output)),date_time=(2026,1,1,0,0,0)); info.create_system=3
            info.external_attr=(0o100000 | (0o755 if file==exe else 0o644))<<16
            info.compress_type=zipfile.ZIP_DEFLATED; archive.writestr(info,file.read_bytes())
    importer.import_ipa(ipa,output/'imported')
    manifest=output/'imported/manifest.json'; validated=importer.validate_manifest(manifest)
    run(['python3',str(companion/'app-probe/build-import-launcher.py'),'--manifest',str(manifest),'--manifest-sha256',sha(manifest),'--clang',clang,'--linker',linker,'--output',str(output/'launcher')])
    record={'status':'built-and-import-validated-not-executed','git_revision':subprocess.check_output(['git','-C',str(companion),'rev-parse','HEAD'],text=True).strip(),'commands':commands,'sources':{str(f):sha(f) for f in [source/'Main.m',source/'Info.plist',source/'Message.txt',source/'build.py',companion/'app-probe/UIKitNarrow.h',companion/'app-import.py']},'tools':{tool:{'sha256':sha(Path(tool)),'version':subprocess.check_output([tool,'--version'],text=True).strip()} for tool in (clang,linker)},'ipa':{'path':str(ipa),'sha256':sha(ipa)},'manifest':{'path':str(manifest),'sha256':sha(manifest),'tree_sha256':validated['tree_sha256']},'bundle_files':{f.name:sha(f) for f in sorted(bundle.iterdir())},'limits':['No guest staging, launch, resource display or counter interaction has been executed.','Own LLVM ad-hoc executable, no special entitlements or probe telemetry.','Narrow research fixture, not an Apple SDK or Xcode project build pathway.']}
    (output/'build-evidence.json').write_text(json.dumps(record,indent=2)+'\n')
    print(json.dumps(record,indent=2))
if __name__=='__main__': main()
