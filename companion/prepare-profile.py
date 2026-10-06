#!/usr/bin/env python3
"""Extract the documented iPhone 11 early-boot inputs from a local Apple IPSW."""
# SPDX-License-Identifier: AGPL-3.0-or-later
import argparse
import datetime
import hashlib
import json
from pathlib import Path
import plistlib
import shutil
import zipfile

SOURCE_URL = ('https://updates.cdn-apple.com/2020SummerSeed/fullrestores/001-35886/'
              '5FE9BE2E-17F8-41C8-96BB-B76E2B225888/'
              'iPhone11,8,iPhone12,1_14.0_18A5351d_Restore.ipsw')
COMPONENTS = {'kernel': 'KernelCache', 'dtb': 'DeviceTree',
              'trustcache': 'RestoreTrustCache', 'ramdisk': 'RestoreRamDisk'}


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ipsw', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path,
                        help='new directory outside the repository')
    args = parser.parse_args()
    repo = Path(__file__).resolve().parents[1]
    ipsw = args.ipsw.resolve(strict=True)
    output = args.output.resolve()
    if output.is_relative_to(repo) or ipsw.is_relative_to(repo):
        parser.error('IPSW and extracted inputs must be outside the repository')
    if output.exists():
        parser.error('output already exists; choose a new directory')
    with zipfile.ZipFile(ipsw) as archive:
        manifest_bytes = archive.read('BuildManifest.plist')
        manifest = plistlib.loads(manifest_bytes)
        if (manifest.get('ProductBuildVersion') != '18A5351d'
                or manifest.get('ProductVersion') != '14.0'
                or 'iPhone12,1' not in manifest.get('SupportedProductTypes', [])):
            parser.error('this profile requires iPhone12,1 iOS 14.0 build 18A5351d')
        identities = [identity for identity in manifest['BuildIdentities']
                      if identity['Info'].get('DeviceClass') == 'n104ap'
                      and identity['Info'].get('Variant') ==
                      'Research Developer Erase Install (IPSW)']
        if len(identities) != 1:
            parser.error('expected one n104ap research erase identity')
        identity = identities[0]
        members = {key: identity['Manifest'][component]['Info']['Path']
                   for key, component in COMPONENTS.items()}
        for member in members.values():
            info = archive.getinfo(member)
            if info.is_dir() or info.flag_bits & 1:
                parser.error('component must be an unencrypted ZIP file member')
        # Create only after all required members and the device identity exist.
        output.mkdir(parents=True, mode=0o700)
        profile = {'schema': 'inferno.early-boot.v1', 'provenance': {
            'source_url': SOURCE_URL,
            'source_url_note': 'documented acquisition URL; hash identifies the supplied local archive',
            'ipsw_path': str(ipsw), 'ipsw_sha256': digest(ipsw),
            'ipsw_size': ipsw.stat().st_size,
            'manifest_sha256': hashlib.sha256(manifest_bytes).hexdigest(),
            'prepared_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'device': 'iPhone12,1', 'board': 'n104ap', 'build': '18A5351d',
            'variant': identity['Info']['Variant'],
            'preparation': 'ZIP extraction only; no ticket, SEP firmware, keys, or binary edits'}}
        (output / 'BuildManifest.plist').write_bytes(manifest_bytes)
        for key, member in members.items():
            path = output / (key + '-' + Path(member).name)
            with archive.open(member) as source, path.open('xb') as target:
                shutil.copyfileobj(source, target)
            profile[key] = {'path': str(path), 'sha256': digest(path),
                            'archive_member': member, 'size': path.stat().st_size}
        profile_path = output / 'profile.json'
        profile_path.write_text(json.dumps(profile, indent=2) + '\n')
        print(profile_path)


if __name__ == '__main__':
    main()
