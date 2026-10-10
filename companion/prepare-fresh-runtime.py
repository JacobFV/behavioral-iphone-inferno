#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Prepare small fresh-runtime artifacts; never launch, stage, or promote disks."""
import argparse
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import plistlib
import stat
import subprocess
import sys

SOURCE = Path(__file__).resolve().parent
POLICY = ('com.apple.voicemail.vmd', 'com.apple.CommCenter',
          'com.apple.CommCenterMobileHelper', 'com.apple.CommCenterRootHelper', 'com.apple.locationd')
INPUTS = {'inspection', 'keybag_stage', 'runtime_build', 'prepare_build', 'app_manifest', 'launcher_build'}

def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value

IMPORTER = module('fresh_app_import', SOURCE / 'app-import.py')
INSPECTOR = module('fresh_inspector_result', SOURCE / 'runtime-inspector/result.py')

def identity(s):
    return (s.st_dev, s.st_ino, s.st_mode, s.st_size, s.st_mtime_ns, s.st_ctime_ns)

def read(path, maximum=64 << 20):
    path = Path(path)
    before = path.lstat()
    if not path.is_absolute() or path.resolve(strict=True) != path or not stat.S_ISREG(before.st_mode) or before.st_size > maximum:
        raise ValueError('Noncanonical, nonregular or oversized input: ' + str(path))
    with path.open('rb') as stream:
        if identity(os.fstat(stream.fileno())) != identity(before):
            raise ValueError('Input changed before open')
        raw = stream.read(maximum + 1)
        if identity(os.fstat(stream.fileno())) != identity(before):
            raise ValueError('Input changed during read')
    if len(raw) != before.st_size or identity(path.lstat()) != identity(before):
        raise ValueError('Input changed after read')
    return raw

def digest(raw):
    return hashlib.sha256(raw).hexdigest()

def json_bytes(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError('Duplicate JSON key')
            result[key] = value
        return result
    def constant(value):
        raise ValueError('Nonfinite JSON')
    return json.loads(raw, object_pairs_hook=pairs, parse_constant=constant)

def pin(record, pins):
    if set(record) != {'path', 'sha256'}:
        raise ValueError('Expected exact path/sha256 pin')
    path = Path(record['path'])
    raw = read(path)
    if digest(raw) != record['sha256']:
        raise ValueError('Pin mismatch: ' + str(path))
    pins[str(path)] = record['sha256']
    return path, raw

def checked_map(values, pins):
    for path, sha in values.items():
        pin({'path': path, 'sha256': sha}, pins)

def historical_importer(build, source_path, sha):
    """Authenticate a reviewed build's superseded importer producer from Git.

    Only the in-checkout app-import.py producer qualifies: its bytes must equal
    the pin at the build's own recorded source revision, which must be an
    ancestor of HEAD. The current importer is pinned separately by its
    current hash; the old hash is never recorded as the current file.
    """
    path = Path(source_path).resolve(strict=True)
    importer = SOURCE / 'app-import.py'
    if path != importer or source_path not in build['producer_sources'] or digest(read(path)) == sha:
        return None
    revision = build.get('source_revision')
    if not isinstance(revision, str) or len(revision) != 40 or any(c not in '0123456789abcdef' for c in revision):
        raise ValueError('Historical importer needs an exact recorded source revision')
    repo = SOURCE.parent
    git = ['git', '-C', str(repo)]
    if subprocess.run(git + ['merge-base', '--is-ancestor', revision, 'HEAD'], timeout=30).returncode != 0:
        raise ValueError('Historical importer revision is not an ancestor of HEAD')
    relative = importer.relative_to(repo).as_posix()
    blob = subprocess.run(git + ['cat-file', 'blob', revision + ':' + relative], check=True, capture_output=True, timeout=30).stdout
    if digest(blob) != sha:
        raise ValueError('Historical importer differs from recorded build revision: ' + str(path))
    return {'path': str(path), 'pinned_sha256': sha, 'source_revision': revision, 'git_object': revision + ':' + relative,
            'git_blob_sha256': digest(blob), 'current_sha256': digest(read(path)),
            'scope': 'Producer provenance of an existing reviewed build only; current importer pinned at its current hash.'}

def build_outputs(path, build, names, pins, historical=None):
    if (path.parent / 'INCOMPLETE.json').exists() or (path.parent / 'failure.json').exists():
        raise ValueError('Incomplete build')
    # Legacy reviewed producers recorded ../app-probe headers lexically.
    # Resolve those source references, preserving their original spelling in the
    # pinned build manifest; output/input artifacts still require canonical paths.
    for source_path, sha in {**build['sources'], **build['producer_sources']}.items():
        superseded = historical_importer(build, source_path, sha)
        if superseded is not None:
            if historical is not None:
                historical.append(superseded)
            continue
        pin({'path': str(Path(source_path).resolve(strict=True)), 'sha256': sha}, pins)
    for row in build['command_records']:
        for channel in ('stdout', 'stderr'):
            pin(row[channel], pins)
    if not build['command_records'] or any(row['exit_code'] != 0 for row in build['command_records']):
        raise ValueError('Failed or absent build commands')
    result = {}
    for name in names:
        item = build['outputs'][name]
        output, raw = pin({'path': str(path.parent / name), 'sha256': item['sha256']}, pins)
        if len(raw) != item['bytes']:
            raise ValueError('Build output length mismatch')
        result[name] = str(output)
    return result

def merge(original, jobs):
    """Exact first insertion: no replacement, exactly five original policy edits."""
    result = copy.deepcopy(original)
    daemons = result['LaunchDaemons']
    if any(v.get('Label', '').startswith('org.inferno.') for v in daemons.values()):
        raise ValueError('Fresh original cache already contains owned jobs')
    for label in POLICY:
        matches = [job for job in daemons.values() if job.get('Label') == label]
        if len(matches) != 1:
            raise ValueError('Original policy label missing or ambiguous: ' + label)
        matches[0]['Disabled'] = True
    for filename, job in jobs.items():
        key = '/System/Library/LaunchDaemons/' + filename
        if key in daemons or any(v.get('Label') == job['Label'] for v in daemons.values()):
            raise ValueError('Owned job collision')
        daemons[key] = copy.deepcopy(job)
    return result

def prepare(config_path, expected, output):
    pins = {}
    _, raw = pin({'path': str(config_path), 'sha256': expected}, pins)
    config = json_bytes(raw)
    if set(config) != {'schema', 'inputs', 'policy'} or config['schema'] != 'inferno.fresh-runtime-artifact-input.v1' or set(config['inputs']) != INPUTS:
        raise ValueError('Unsupported artifact input contract')
    if config['policy'] != 'disable-five-unsupported-services':
        raise ValueError('Explicit five-service policy required')
    paths, records = {}, {}
    for name, value in config['inputs'].items():
        paths[name], raw = pin(value, pins)
        records[name] = json_bytes(raw)
    inspection = records['inspection']
    if (inspection.get('schema'), inspection.get('status'), inspection.get('backing_depth')) != ('inferno.runtime-inspection.v1', 'observed-not-runtime-ready', 4) or inspection.get('ipa_runtime_ready') is not False or inspection.get('runtime_base_eligible') is not False:
        raise ValueError('Expected fresh read-only inspector result')
    if inspection['predecessor'] != config['inputs']['keybag_stage']:
        raise ValueError('Inspector/keybag predecessor mismatch')
    for name in ('inspection', 'keybag_stage'):
        if any((paths[name].parent / marker).exists() for marker in ('INCOMPLETE.json', 'failure.json')):
            raise ValueError('Failed/incomplete predecessor')
    checked_map(inspection['source_sha256'], pins)
    checked_map(inspection['stopped_evidence_sha256'], pins)
    report_path, report_raw = pin({'path': inspection['report'], 'sha256': inspection['report_sha256']}, pins)
    report = json_bytes(report_raw)
    if report.get('exit_code') != 0 or report.get('error') or report.get('attempt_completed') is not True:
        raise ValueError('Inspector did not stop normally')
    serial = read(report_path.parent / 'serial.log')
    pins[str(report_path.parent / 'serial.log')] = digest(serial)
    content, launchd = INSPECTOR.verify_content(serial)
    if content != inspection['content']:
        raise ValueError('Inspector content does not match actual raw serial')
    _, exported = pin(inspection['launchd_export'], pins)
    if exported != launchd:
        raise ValueError('Fresh export differs from raw inspector bytes')
    pin({'path': inspection['retention'], 'sha256': inspection['retention_sha256']}, pins)
    pin({'path': str(paths['inspection'].parent / 'content-check.json'), 'sha256': inspection['content_checkpoint_sha256']}, pins)
    approved = {
        'runtime_build': ('aa7ba5975fe5436ebb6bfbd7f922817e3b7b4e0c4b2250756ca2824547ddcf35', 'built-owned-runtime-helpers-only; no guest execution yet'),
        'prepare_build': ('3cb1656f3978bfdcca7e3da80d7f8091f524c1b7593bb64a42a7a2a47f34e532', 'built-owned-preparation-helper-only; no guest execution yet'),
    }
    for name, (approved_sha, status) in approved.items():
        if config['inputs'][name]['sha256'] != approved_sha or records[name].get('status') != status:
            raise ValueError('First fresh preparation requires exact independently reviewed owned build: ' + name)
    superseded = []
    helpers = build_outputs(paths['runtime_build'], records['runtime_build'], ('inferno-probe', 'inferno-readiness', 'inferno-hid-input', 'inferno-unlock-empty'), pins, superseded)
    for binary, entitlement in (('inferno-hid-input', 'hid-entitlements.plist'), ('inferno-unlock-empty', 'unlock-entitlements.plist')):
        name = binary + '-entitlements.plist'
        readback = records['runtime_build']['outputs'][name]
        _, raw = pin({'path': str(paths['runtime_build'].parent / name), 'sha256': readback['sha256']}, pins)
        source = SOURCE / 'native-probe' / entitlement
        source_raw = read(source); pins[str(source)] = digest(source_raw)
        if len(raw) != readback['bytes'] or plistlib.loads(raw) != plistlib.loads(source_raw):
            raise ValueError('Runtime helper entitlement readback mismatch')
    prep = build_outputs(paths['prepare_build'], records['prepare_build'], ('inferno-prepare-root',), pins, superseded)
    entitlement = records['prepare_build']['outputs']['helper-entitlements.plist']
    _, raw = pin({'path': str(paths['prepare_build'].parent / 'helper-entitlements.plist'), 'sha256': entitlement['sha256']}, pins)
    source = SOURCE / 'native-probe/entitlements.plist'
    source_raw = read(source); pins[str(source)] = digest(source_raw)
    if len(raw) != entitlement['bytes'] or plistlib.loads(raw) != plistlib.loads(source_raw):
        raise ValueError('Preparation helper entitlement readback mismatch')
    app = IMPORTER.validate_manifest(paths['app_manifest'])
    if (app['bundle']['identifier'], app['bundle']['guest_path']) != ('org.inferno.companion.ipademo', '/Applications/ImportedDemo.app'):
        raise ValueError('First fresh journey is pinned to the owned imported demo')
    launcher = records['launcher_build']
    if launcher['status'] != 'built-not-staged-or-executed' or launcher['manifest_path'] != str(paths['app_manifest']) or launcher['manifest_sha256'] != config['inputs']['app_manifest']['sha256'] or launcher['target'] != app['bundle']:
        raise ValueError('Launcher does not bind this validated app')
    app_source = SOURCE / 'app-probe'
    for relative, sha in launcher['sources'].items():
        candidate = app_source / relative
        if not candidate.resolve().is_relative_to(app_source):
            raise ValueError('Launcher source escapes owned source directory')
        pin({'path': str(candidate), 'sha256': sha}, pins)
    pin({'path': str(SOURCE / 'app-import.py'), 'sha256': launcher['importer_sha256']}, pins)
    launch_outputs = {}
    for name in ('inferno-launcher', 'inferno-exec-launcher', 'org.inferno.app-probe.plist', 'ImportedAppTarget.h'):
        target, data = pin({'path': str(paths['launcher_build'].parent / name), 'sha256': launcher['outputs'][name]}, pins)
        launch_outputs[name] = str(target)
    job = plistlib.loads(read(Path(launch_outputs['org.inferno.app-probe.plist'])))
    template = app_source / 'org.inferno.app-probe-system-app.plist'
    template_raw = read(template); pins[str(template)] = digest(template_raw)
    if job != plistlib.loads(template_raw):
        raise ValueError('App launch job differs from reviewed fixed mobile wrapper job')
    jobs = {'org.inferno.app-probe.plist': job}
    for label, program, keep in (('readiness', 'inferno-readiness', None), ('unlock-empty', 'inferno-unlock-empty', False)):
        job = {'Label': 'org.inferno.' + label, 'ProgramArguments': ['/usr/bin/' + program], 'RunAtLoad': True, 'UserName': 'root', 'StandardOutPath': '/dev/console', 'StandardErrorPath': '/dev/console'}
        if keep is not None: job['KeepAlive'] = keep
        jobs[job['Label'] + '.plist'] = job
    merged = plistlib.dumps(merge(plistlib.loads(launchd), jobs), fmt=plistlib.FMT_BINARY, sort_keys=False)
    for own in (Path(__file__).resolve(), SOURCE / 'app-import.py', SOURCE / 'runtime-inspector/result.py', SOURCE / 'native-probe/merge-launchd-cache.py'):
        pins[str(own)] = digest(read(own))
    output = IMPORTER.external_output(output)
    output.mkdir(parents=True)
    (output / 'INCOMPLETE.json').write_text('{"status":"preparing-artifacts"}\n')
    try:
        for filename, job in jobs.items():
            (output / filename).write_bytes(plistlib.dumps(job))
        command = [sys.executable, str(SOURCE / 'native-probe/merge-launchd-cache.py'), '--cache', inspection['launchd_export']['path'], '--disable-unsupported-services', '--output', str(output / 'launchd.plist')]
        for filename in jobs:
            command += ['--job', str(output / filename)]
        with (output / 'merge.stdout').open('xb') as stdout, (output / 'merge.stderr').open('xb') as stderr:
            subprocess.run(command, check=True, stdout=stdout, stderr=stderr, timeout=30)
        actual_merged = read(output / 'launchd.plist')
        # Binary plist object-table references need not serialize identically.
        # Compare the entire decoded tree, then bind the actual merger bytes.
        if plistlib.loads(actual_merged) != plistlib.loads(merged):
            raise ValueError('Existing merger differs from independent exact merge')
        merged = actual_merged
        IMPORTER.validate_manifest(paths['app_manifest'])
        checked_map(dict(pins), {})
        args = ['--disk-helper-existing', '--readiness-probe', helpers['inferno-readiness'], '--hid-input-helper', helpers['inferno-hid-input'], '--unlock-helper', helpers['inferno-unlock-empty'], '--disk-helper', prep['inferno-prepare-root'], '--system-launcher', launch_outputs['inferno-launcher'], '--exec-wrapper', launch_outputs['inferno-exec-launcher'], '--imported-app-manifest', str(paths['app_manifest']), '--imported-app-manifest-sha256', config['inputs']['app_manifest']['sha256'], '--launchd-cache', str(output / 'launchd.plist'), '--launchd-cache-sha256', digest(merged)]
        result = {'schema': 'inferno.fresh-runtime-artifacts.v1', 'status': 'host-prepared-not-staged', 'ipa_runtime_ready': False, 'inputs': config['inputs'], 'input_source_sha256': pins, 'historical_producer_sources': superseded, 'merge_command': command, 'policy': {'disabled_original_labels': list(POLICY), 'original_signature_modified': False, 'signature_scope': 'Original signature not read or written', 'fresh_insertion': True}, 'jobs': sorted(jobs), 'outputs': {p.name: {'path': str(p), 'sha256': digest(read(p))} for p in sorted(output.iterdir()) if p.name != 'INCOMPLETE.json'}, 'prepare_arguments_fragment': args, 'scope': 'Small artifact preparation only. No disk eligibility validation, renderer success, ramdisk construction, guest staging, migration, first unlock or launch. Require separately verified renderer stage from same keybag before constructing a recovery session. No signature file is supplied or modified.'}
        (output / 'fresh-runtime-artifacts.json').write_text(json.dumps(result, indent=2) + '\n')
        (output / 'INCOMPLETE.json').unlink()
        return result
    except BaseException as exc:
        (output / 'failure.json').write_text(json.dumps({'error': str(exc), 'ipa_runtime_ready': False}) + '\n')
        raise

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--input-sha256', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    old = os.umask(0o077)
    try:
        result = prepare(args.input, args.input_sha256, args.output)
        print(json.dumps({'status': result['status'], 'ipa_runtime_ready': False}))
    finally:
        os.umask(old)

if __name__ == '__main__':
    main()
