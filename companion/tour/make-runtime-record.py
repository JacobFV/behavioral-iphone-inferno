#!/usr/bin/env python3
"""Write an inferno.local-ipa-runtime.v1 record that binds prepare-import to a setup-complete
base made by the fresh chain (stage-fresh-runtime + boot-fresh), so owned apps can be staged
onto it with prepare-import / stage-import / boot-import.

make-runtime-record.py --fresh-stage A/fresh-r6 --artifacts A/art-r6 --base A/fresh-boot-r6/boot/report.json
    --clang PATH --linker PATH --output runtime.json
Every other input is taken from ~/inferno-chain/env.sh conventions ($I, $N, repo .local-build)."""
import argparse, hashlib, json
from pathlib import Path

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def pin(p):
    p = Path(p).resolve(strict=True)
    return {'path': str(p), 'sha256': sha(p)}

def main():
    a = argparse.ArgumentParser(description=__doc__)
    a.add_argument('--fresh-stage', type=Path, required=True)
    a.add_argument('--artifacts', type=Path, required=True)
    a.add_argument('--base', type=Path, required=True)
    a.add_argument('--clang', type=Path, required=True)
    a.add_argument('--linker', type=Path, required=True)
    a.add_argument('--inferno-home', type=Path, default=Path.home() / '.local/share/inferno')
    a.add_argument('--repo', type=Path, default=Path(__file__).resolve().parents[2])
    a.add_argument('--output', type=Path, required=True)
    x = a.parse_args()
    I = x.inferno_home / 'images/ios14b5'; N = x.inferno_home / 'native-probe'; F = x.fresh_stage
    prep = json.loads((F / 'recovery/preparation.json').read_text())
    raw = I / 'raw-recovery-r2/ramdisk-payload.raw'
    if sha(raw) != prep['source_raw_sha256']:
        raise SystemExit('raw ramdisk does not match the fresh stage preparation')
    helper_build = N / 'reproducible-helper-build-r2/build.json'
    hb = json.loads(helper_build.read_text())
    disk_helper = Path(hb['outputs']['inferno-prepare-root']['path']) if 'path' in hb['outputs']['inferno-prepare-root'] else N / 'reproducible-helper-build-r2/inferno-prepare-root'
    cache = x.artifacts / 'launchd.plist'
    inputs = {
        'profile': pin(I / 'profile/profile.json'), 'raw_ramdisk': pin(raw),
        'probe': pin(N / 'runtime-helpers-r2/inferno-probe'), 'disk_helper': pin(disk_helper),
        'helper_build': pin(helper_build), 'hfsplus': pin(N / 'tools/hfsplus'),
        'clang': pin(x.clang), 'linker': pin(x.linker), 'cache': pin(cache), 'base_report': pin(x.base),
        'emulator': pin(x.repo / '.local-build/build/qemu-system-aarch64'),
        'emulator_build': pin(x.repo / '.local-build/build-manifest.json'),
    }
    record = {
        'schema': 'inferno.local-ipa-runtime.v1', 'inputs': inputs,
        'overlay_tools_root': str((x.inferno_home / 'disk-overlay-tools').resolve()),
        'tool_invocations': {'clang': str(x.clang.absolute()), 'linker': str(x.linker.absolute())},
        'cache_binding': {
            'basis': 'reviewed-retained-lineage-not-fresh-guest-export',
            'base_report_sha256': inputs['base_report']['sha256'], 'cache_sha256': inputs['cache']['sha256'],
            'install_profile': pin(F / 'recovery-run/profile.json'), 'install_report': pin(F / 'recovery-run/report.json'),
            'install_serial': pin(F / 'recovery-run/serial.log'), 'cache_readback': pin(F / 'readback-cache'),
            'raw_ramdisk_preparation': pin(F / 'recovery/preparation.json'),
            'lineage_evidence': [pin(F / 'fresh-runtime.json'), pin(x.artifacts / 'fresh-runtime-artifacts.json')],
        },
    }
    with x.output.open('x') as f:
        json.dump(record, f, indent=2); f.write('\n')
    print(x.output, sha(x.output))

if __name__ == '__main__':
    main()
