#!/usr/bin/env python3
"""Turn an unsigned Xcode-built IPA (e.g. from the ios-build-farm repo) into one the importer
accepts: drop PlugIns/ (app extensions), drop files whose names fall outside the importer's
character set (e.g. AppIcon@2x.png), then ad-hoc sign every Mach-O with ldid -S, innermost first
(embedded dylibs and frameworks, then the main executable). Records what it changed.

prepare-swift-ipa.py IN.ipa OUT.ipa --ldid PATH [--entitlements FILE]"""
import argparse, hashlib, json, re, shutil, subprocess, tempfile, zipfile
from pathlib import Path

OK = re.compile(r'[A-Za-z0-9_. @~+-]+')
MAGICS = (b'\xcf\xfa\xed\xfe', b'\xca\xfe\xba\xbe')
# Xcode embeds its test runtime when a scheme builds a test host (JotDemo did); it links
# /Developer private frameworks the importer rightly refuses, and the app never loads it.
TEST_ONLY = re.compile(r'/Frameworks/(XCT[^/]*|XCUnit|XCUIAutomation|Testing)\.framework(/|$)|/Frameworks/libXCTest[^/]*\.dylib$')

def thin_arm64(f):
    """Replace a fat Mach-O (e.g. armv7+arm64 from an old Pods target) with its plain arm64 slice,
    since the importer takes thin ARM64 only. Returns True if the file was fat."""
    import struct
    b = f.read_bytes()
    if b[:4] != b'\xca\xfe\xba\xbe':
        return False
    n = struct.unpack('>I', b[4:8])[0]
    for i in range(n):
        cputype, subtype, off, size, _ = struct.unpack('>iiIII', b[8 + 20 * i:28 + 20 * i])
        if cputype == 0x0100000C and (subtype & 0xFFFFFF) == 0:  # CPU_TYPE_ARM64, ARM64_ALL
            f.write_bytes(b[off:off + size]); return True
    raise SystemExit('%s: fat Mach-O without a plain arm64 slice' % f)

def main():
    a = argparse.ArgumentParser(description=__doc__)
    a.add_argument('ipa', type=Path); a.add_argument('out', type=Path)
    a.add_argument('--ldid', required=True); a.add_argument('--entitlements', type=Path)
    x = a.parse_args()
    dropped, signed = [], []
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        with zipfile.ZipFile(x.ipa) as z:
            for info in z.infolist():
                n = info.filename
                parts = [p for p in n.rstrip('/').split('/') if p]
                if '/PlugIns/' in n or TEST_ONLY.search(n) or any(not OK.fullmatch(p) for p in parts):
                    dropped.append(n); continue
                z.extract(info, tmp)
                mode = (info.external_attr >> 16) & 0o777
                if mode and not n.endswith('/'): (tmp / n).chmod(mode)
        app = next((tmp / 'Payload').glob('*.app'))
        machos = [f for f in app.rglob('*') if f.is_file() and f.read_bytes()[:4] in MAGICS]
        thinned = [str(f.relative_to(tmp)) for f in machos if thin_arm64(f)]
        # innermost first: deepest paths, main executable last
        main_exe = app / __import__('plistlib').loads((app / 'Info.plist').read_bytes())['CFBundleExecutable']
        for f in sorted(machos, key=lambda p: (p == main_exe, -len(p.parts))):
            cmd = [x.ldid, '-S' + (str(x.entitlements) if x.entitlements and f == main_exe else ''), str(f)]
            subprocess.run(cmd, check=True); signed.append(str(f.relative_to(tmp)))
            for sig in f.parent.glob('_CodeSignature'):
                shutil.rmtree(sig)  # stale Xcode signature directory
        x.out.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(x.out, 'w', zipfile.ZIP_DEFLATED) as z:
            for f in sorted(tmp.rglob('*')):
                if f.is_dir(): continue
                info = zipfile.ZipInfo(str(f.relative_to(tmp)), date_time=(2026, 1, 1, 0, 0, 0)); info.create_system = 3
                info.external_attr = (0o100000 | (0o755 if f.read_bytes()[:4] in MAGICS else 0o644)) << 16
                info.compress_type = zipfile.ZIP_DEFLATED; z.writestr(info, f.read_bytes())
    rec = {'input': str(x.ipa), 'input_sha256': hashlib.sha256(x.ipa.read_bytes()).hexdigest(),
           'output': str(x.out), 'output_sha256': hashlib.sha256(x.out.read_bytes()).hexdigest(),
           'dropped': dropped, 'thinned_to_arm64': thinned, 'signed_innermost_first': signed}
    x.out.with_suffix('.prepare.json').write_text(json.dumps(rec, indent=2) + '\n')
    print(json.dumps({'output': rec['output'], 'dropped': len(dropped), 'signed': len(signed)}))

if __name__ == '__main__':
    main()
