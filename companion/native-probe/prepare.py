#!/usr/bin/env python3
"""Clone a verified raw recovery ramdisk and add owned/nonmutating launch probes."""
import argparse
import hashlib
import json
import plistlib
import shutil
import subprocess
from pathlib import Path

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--profile', required=True, type=Path)
p.add_argument('--raw-ramdisk', required=True, type=Path)
p.add_argument('--probe', required=True, type=Path)
p.add_argument('--hfsplus', required=True, type=Path)
p.add_argument('--disk-helper', type=Path, help='explicitly install disposable-root APFS preparation helper')
p.add_argument('--disk-helper-roles', action='store_true', help='also add xART and Hardware; requires owned helper signed with xart entitlement')
p.add_argument('--disk-helper-existing', action='store_true', help='use existing prepared volumes without adding them again')
p.add_argument('--disk-helper-gigalocker', action='store_true', help='run original seputil initialization on mounted xART')
p.add_argument('--disk-helper-data', action='store_true', help='add Data/Update and copy original var plus Hardware factory path')
p.add_argument('--sep-payload', type=Path, help='explicit original SEP payload to copy unchanged to the boot loader path')
p.add_argument('--sep-sha256', help='required SHA256 of supplied SEP payload')
p.add_argument('--disk-helper-verify-data', action='store_true', help='read-only full guest Data tree bytes, modes, ownership and symlink comparison')
p.add_argument('--disk-helper-keybag', action='store_true', help='load original SEP payload and create system keybag using original MobileKeyBag')
p.add_argument('--hid-input-helper', type=Path, help='owned operator-only virtual touchscreen server; requires readiness launcher')
p.add_argument('--readiness-probe', type=Path, help='owned observation-only system startup helper to stage')
p.add_argument('--launchd-cache', type=Path, help='explicit merged launchd configuration; no signature operation')
p.add_argument('--launchd-cache-sha256', help='required merged configuration SHA256')
p.add_argument('--export-reports', action='store_true', help='read-only bounded crash report export from copied Data')
p.add_argument('--system-launcher',type=Path,help='owned launcher copy for System versus Data execution comparison')
p.add_argument('--system-app-executable',type=Path,help='replace only existing owned /Applications/InfernoProbe.app/InfernoProbe; preserve Info.plist')
p.add_argument('--system-app-dir',type=Path,help='owned two-file InfernoProbe.app bundle to stage under Applications')
p.add_argument('--unlock-helper',type=Path,help='owned single empty-passcode unlock diagnostic for freshly created VM keybag')
p.add_argument('--exec-wrapper',type=Path,help='owned System wrapper to diagnose mobile exec')
p.add_argument('--multitouch-img4', type=Path, help='explicit unsigned format-wrapped original Multitouch payload for existing Preboot FUD directory')
p.add_argument('--multitouch-sha256', help='required SHA256 of supplied IMG4 container')
p.add_argument('--output', required=True, type=Path)
a = p.parse_args()
if a.hid_input_helper and (not a.disk_helper or not a.readiness_probe or not a.hid_input_helper.is_file()):
    p.error('--hid-input-helper requires a regular helper file, disk helper and readiness probe')
if bool(a.multitouch_img4) != bool(a.multitouch_sha256):
    p.error('--multitouch-img4 and --multitouch-sha256 required together')
if a.multitouch_img4 and (not a.disk_helper or not a.disk_helper_existing or not a.multitouch_img4.is_file() or hashlib.sha256(a.multitouch_img4.read_bytes()).hexdigest() != a.multitouch_sha256):
    p.error('Multitouch packaging requires existing volumes, helper, and matching SHA256')
if bool(a.launchd_cache) != bool(a.launchd_cache_sha256):
    p.error('--launchd-cache and --launchd-cache-sha256 required together')
if a.launchd_cache and (not a.disk_helper or not a.launchd_cache.is_file() or hashlib.sha256(a.launchd_cache.read_bytes()).hexdigest() != a.launchd_cache_sha256):
    p.error('merged cache requires helper and matching file hash')
if bool(a.sep_payload) != bool(a.sep_sha256):
    p.error('--sep-payload and --sep-sha256 must be supplied together')
if a.sep_payload and (not a.disk_helper or not a.sep_payload.is_file() or hashlib.sha256(a.sep_payload.read_bytes()).hexdigest() != a.sep_sha256):
    p.error('SEP payload requires disk helper and matching file hash')
if (a.disk_helper_roles or a.disk_helper_existing or a.disk_helper_gigalocker or a.disk_helper_data or a.disk_helper_verify_data or a.disk_helper_keybag or a.readiness_probe or a.export_reports or a.exec_wrapper or a.system_launcher or a.unlock_helper or a.system_app_dir or a.system_app_executable) and not a.disk_helper:
    p.error('--disk-helper-roles requires --disk-helper')
for required in (a.profile, a.raw_ramdisk, a.probe, a.hfsplus):
    if not required.is_file():
        p.error(f'missing input: {required}')
if a.disk_helper and not a.disk_helper.is_file():
    p.error(f'missing helper: {a.disk_helper}')
if a.system_app_dir and (not a.system_app_dir.is_dir() or {p.name for p in a.system_app_dir.iterdir()} != {'InfernoProbe','Info.plist'} or any(not p.is_file() or p.is_symlink() for p in a.system_app_dir.iterdir())):
    p.error('--system-app-dir requires exactly two owned regular files: InfernoProbe and Info.plist')
if a.system_app_executable and (a.system_app_dir or not a.disk_helper_existing or not a.system_app_executable.is_file() or a.system_app_executable.is_symlink()):
    p.error('--system-app-executable requires existing volumes and a regular file; mutually exclusive with --system-app-dir')
a.output.mkdir(parents=True, exist_ok=False)
sha = lambda f: hashlib.sha256(f.read_bytes()).hexdigest()
profile = json.loads(a.profile.read_text())
raw = a.output / 'ramdisk.raw'
shutil.copyfile(a.raw_ramdisk, raw)
log = []
def hfs(*args):
    result = subprocess.run([str(a.hfsplus), str(raw), *map(str, args)], capture_output=True, text=True, check=True)
    log.append({'args': list(map(str, args)), 'stdout': result.stdout, 'stderr': result.stderr})
hfs('add', a.probe, '/usr/bin/inferno-probe')
hfs('chmod', '755', '/usr/bin/inferno-probe')
jobs = [('native', ['/usr/bin/inferno-probe']), ('asr-help', ['/usr/sbin/asr', '--help']), ('apfs-help', ['/sbin/newfs_apfs', '-h'])]
if a.disk_helper:
    # Dedicated preparation does not run a restore transaction or its timeout.
    hfs('mv', '/System/Library/LaunchDaemons/com.apple.restored_external.plist', '/usr/share/com.apple.restored_external.plist.disabled')
    hfs('add', a.disk_helper, '/usr/bin/inferno-prepare-root')
    hfs('chmod', '755', '/usr/bin/inferno-prepare-root')
    if a.multitouch_img4:
        hfs('add', a.multitouch_img4, '/usr/share/inferno-multitouch.img4')
        hfs('chmod', '644', '/usr/share/inferno-multitouch.img4')
        hfs('extract', '/usr/share/inferno-multitouch.img4', a.output / 'readback-multitouch.img4')
        assert sha(a.output / 'readback-multitouch.img4') == a.multitouch_sha256
    if a.sep_payload:
        hfs('add', a.sep_payload, '/usr/share/inferno-sep-payload')
        hfs('chmod', '644', '/usr/share/inferno-sep-payload')
        hfs('extract', '/usr/share/inferno-sep-payload', a.output / 'readback-sep')
        assert sha(a.output / 'readback-sep') == a.sep_sha256
    if a.system_launcher:
        hfs('add', a.system_launcher, '/usr/share/inferno-system-launcher')
        hfs('chmod', '755', '/usr/share/inferno-system-launcher')
        hfs('extract', '/usr/share/inferno-system-launcher', a.output / 'readback-system-launcher')
        assert sha(a.output / 'readback-system-launcher') == sha(a.system_launcher)
    if a.system_app_executable:
        hfs('add', a.system_app_executable, '/usr/share/inferno-app-executable')
        hfs('chmod', '755', '/usr/share/inferno-app-executable')
        hfs('extract', '/usr/share/inferno-app-executable', a.output / 'readback-app-executable')
        assert sha(a.output / 'readback-app-executable') == sha(a.system_app_executable)
    if a.system_app_dir:
        hfs('mkdir', '/usr/share/InfernoProbe.app')
        hfs('chmod', '755', '/usr/share/InfernoProbe.app')
        for name,mode in (('InfernoProbe','755'),('Info.plist','644')):
            hfs('add', a.system_app_dir/name, '/usr/share/InfernoProbe.app/'+name)
            hfs('chmod', mode, '/usr/share/InfernoProbe.app/'+name)
            hfs('extract', '/usr/share/InfernoProbe.app/'+name, a.output/('readback-app-'+name))
            assert sha(a.output/('readback-app-'+name)) == sha(a.system_app_dir/name)
    if a.unlock_helper:
        hfs('add', a.unlock_helper, '/usr/share/inferno-unlock-empty')
        hfs('chmod', '755', '/usr/share/inferno-unlock-empty')
        hfs('extract', '/usr/share/inferno-unlock-empty', a.output / 'readback-unlock-helper')
        assert sha(a.output / 'readback-unlock-helper') == sha(a.unlock_helper)
    if a.exec_wrapper:
        hfs('add', a.exec_wrapper, '/usr/share/inferno-exec-launcher')
        hfs('chmod', '755', '/usr/share/inferno-exec-launcher')
        hfs('extract', '/usr/share/inferno-exec-launcher', a.output / 'readback-exec-wrapper')
        assert sha(a.output / 'readback-exec-wrapper') == sha(a.exec_wrapper)
    if a.launchd_cache:
        hfs('add', a.launchd_cache, '/usr/share/inferno-launchd-cache.plist')
        hfs('chmod', '644', '/usr/share/inferno-launchd-cache.plist')
        hfs('extract', '/usr/share/inferno-launchd-cache.plist', a.output / 'readback-launchd-cache')
        assert sha(a.output / 'readback-launchd-cache') == a.launchd_cache_sha256
    if a.hid_input_helper:
        hfs('add', a.hid_input_helper, '/usr/share/inferno-hid-input')
        hfs('chmod', '755', '/usr/share/inferno-hid-input')
        hfs('extract', '/usr/share/inferno-hid-input', a.output / 'readback-hid-input')
        assert sha(a.output / 'readback-hid-input') == sha(a.hid_input_helper)
    if a.readiness_probe:
        hfs('add', a.readiness_probe, '/usr/share/inferno-readiness')
        hfs('chmod', '755', '/usr/share/inferno-readiness')
        readiness_job = a.output / 'org.inferno.readiness.plist'
        readiness_job.write_bytes(plistlib.dumps({'Label': 'org.inferno.readiness', 'ProgramArguments': ['/usr/bin/inferno-readiness'], 'RunAtLoad': True, 'StandardOutPath': '/dev/console', 'StandardErrorPath': '/dev/console', 'UserName': 'root'}))
        hfs('add', readiness_job, '/usr/share/org.inferno.readiness.plist')
        hfs('chmod', '644', '/usr/share/org.inferno.readiness.plist')
    jobs.append(('prepare-root', ['/usr/bin/inferno-prepare-root', '--disposable-root-copy'] + (['--role-volumes'] if a.disk_helper_roles else []) + (['--existing-volumes'] if a.disk_helper_existing else []) + (['--init-gigalocker'] if a.disk_helper_gigalocker else []) + (['--seed-data'] if a.disk_helper_data else []) + (['--copy-sep'] if a.sep_payload else []) + (['--verify-data'] if a.disk_helper_verify_data else []) + (['--create-keybag'] if a.disk_helper_keybag else []) + (['--install-readiness'] if a.readiness_probe else []) + (['--install-cache'] if a.launchd_cache else []) + (['--export-reports'] if a.export_reports else []) + (['--install-exec-wrapper'] if a.exec_wrapper else []) + (['--install-system-launcher'] if a.system_launcher else []) + (['--install-unlock-helper'] if a.unlock_helper else []) + (['--install-system-app'] if a.system_app_dir else []) + (['--replace-system-app-executable'] if a.system_app_executable else []) + (['--install-multitouch'] if a.multitouch_img4 else []) + (['--install-hid-input'] if a.hid_input_helper else [])))
for name, args in jobs:
    label = 'org.inferno.probe.' + name
    local = a.output / (label + '.plist')
    local.write_bytes(plistlib.dumps({'Label': label, 'ProgramArguments': args, 'RunAtLoad': True, 'StandardOutPath': '/dev/console', 'StandardErrorPath': '/dev/console', 'UserName': 'root'}))
    destination = '/System/Library/LaunchDaemons/' + local.name
    hfs('add', local, destination)
    hfs('chmod', '644', destination)
hfs('ls', '/System/Library/LaunchDaemons')
hfs('extract', '/usr/bin/inferno-probe', a.output / 'readback-probe')
assert sha(a.output / 'readback-probe') == sha(a.probe)
profile['ramdisk'] = {'path': str(raw.resolve()), 'size': raw.stat().st_size, 'sha256': sha(raw)}
steps = ['Cloned decoded HFSX recovery ramdisk', 'added owned ad-hoc marker and diagnostic launchd jobs']
if a.disk_helper:
    steps += ['moved the original restored_external launchd plist outside LaunchDaemons', 'added owned disk preparation helper and explicit launch arguments']
if a.sep_payload:
    steps += ['added supplied SEP payload byte-for-byte after SHA256 and readback verification']
profile['provenance']['preparation'] = '; '.join(steps) + '. Original source image and Apple executable bytes unchanged; cloned ramdisk configuration changed.'
profile['provenance']['helper_flags'] = {key: getattr(a, key) for key in ('disk_helper_roles', 'disk_helper_existing', 'disk_helper_gigalocker', 'disk_helper_data', 'disk_helper_verify_data', 'disk_helper_keybag', 'export_reports')}
profile['provenance']['multitouch_img4_sha256'] = a.multitouch_sha256
profile['provenance']['multitouch_scope'] = 'Explicit unsigned container to existing Preboot zero-hash firmware/FUD; no manifest or signature added' if a.multitouch_img4 else None
profile['provenance']['sep_payload_sha256'] = a.sep_sha256
profile['provenance']['system_app_executable'] = {'path': str(a.system_app_executable), 'sha256': sha(a.system_app_executable), 'target': '/Applications/InfernoProbe.app/InfernoProbe', 'scope': 'existing owned executable only; no Info.plist or registration changes'} if a.system_app_executable else None
profile['provenance']['system_app_files'] = {p.name:sha(p) for p in a.system_app_dir.iterdir()} if a.system_app_dir else None
profile['provenance']['unlock_helper_sha256'] = sha(a.unlock_helper) if a.unlock_helper else None
profile['provenance']['system_launcher_sha256'] = sha(a.system_launcher) if a.system_launcher else None
profile['provenance']['exec_wrapper_sha256'] = sha(a.exec_wrapper) if a.exec_wrapper else None
profile['provenance']['launchd_cache_sha256'] = a.launchd_cache_sha256
profile['provenance']['hid_input_helper_sha256'] = sha(a.hid_input_helper) if a.hid_input_helper else None
profile['provenance']['readiness_sha256'] = sha(a.readiness_probe) if a.readiness_probe else None
(a.output / 'profile.json').write_text(json.dumps(profile, indent=2) + '\n')
(a.output / 'preparation.json').write_text(json.dumps({'source_profile': str(a.profile), 'source_raw_sha256': sha(a.raw_ramdisk), 'probe_sha256': sha(a.probe), 'sep_payload_sha256': a.sep_sha256, 'disk_helper_sha256': sha(a.disk_helper) if a.disk_helper else None, 'hfsplus_sha256': sha(a.hfsplus), 'output_ramdisk_sha256': sha(raw), 'operations': log}, indent=2) + '\n')
print(a.output / 'profile.json')
