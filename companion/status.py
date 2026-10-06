#!/usr/bin/env python3
"""Inspect setup readiness; saved QMP evidence is never an iOS-boot verdict."""
# SPDX-License-Identifier: AGPL-3.0-or-later
import hashlib
import json
from pathlib import Path
import subprocess
import sys

root = Path(__file__).resolve().parents[1]
binary = root / '.local-build/build/qemu-system-aarch64'
manifest_path = root / '.local-build/build-manifest.json'
manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
head = subprocess.check_output(['git', '-C', str(root), 'rev-parse', '--short', 'HEAD'], text=True).strip()
branch = subprocess.check_output(['git', '-C', str(root), 'branch', '--show-current'], text=True).strip()
digest = None
if binary.is_file():
    with binary.open('rb') as handle:
        digest = hashlib.file_digest(handle, 'sha256').hexdigest()
build_matches = bool(digest and manifest.get('binary', {}).get('sha256') == digest)
reports = sorted((root / '.local-build/reports').glob('*/report.json'), key=lambda p: p.stat().st_mtime, reverse=True)
evidence = None
boot_evidence = {}
for path in reports:
    try:
        record = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        continue
    if record.get('kind') in ('t8030_recovery_ramdisk_experiment', 't8030_direct_root_experiment'):
        boot_evidence.setdefault(record['kind'], (path, record))
    if (record.get('binary_sha256') == digest
            and record.get('kind') == 'firmware_free_qmp_control_plane' and evidence is None):
        evidence = (path, record)
print('Repository:', root)
print('Branch:', branch, '| HEAD:', head)
changes = subprocess.check_output(['git', '-C', str(root), 'status', '--porcelain'], text=True).strip()
print('Working tree:', 'changes present; commit source before building' if changes else 'clean')
print('Build:', 'present; SHA256 matches build manifest' if build_matches else 'missing or does not match build manifest')
print('Built source:', manifest.get('source_revision', 'none'))
print('SEP build mode:', manifest.get('sep_mode', 'not recorded (initial build used encrypted emulated SEP)'))
print('Binary:', binary)
if evidence:
    print('Last matching QMP evidence:', 'PASS' if evidence[1].get('passed') else 'FAIL')
    print('Report:', evidence[0])
else:
    print('Matching QMP evidence: none; run companion/run check')
for kind, (path, record) in boot_evidence.items():
    print('Latest', kind + ':', path)
    print('Attempt binary matches current build:', record.get('binary_sha256') == digest)
    print('Attempt error:', record.get('error', 'none reported; inspect raw logs'))
direct = boot_evidence.get('t8030_direct_root_experiment')
if direct:
    path, record = direct
    journey = record.get('probe_journey', {})
    print('Latest owned-app journey state:', journey.get('state', 'not enabled'))
    if 'exit_code' not in record:
        print('Live journey: initial report may be stale; query probe-status through the mailbox')
    elif journey.get('completed'):
        try:
            serial = (path.parent / 'serial.log').read_bytes()
            if not all(marker in serial for marker in (
                    b'INFERNO_UIKIT_PROBE_V1 event=appeared count=0',
                    b'INFERNO_UIKIT_PROBE_V1 event=tap count=1')):
                raise ValueError('required actual guest markers missing')
            for label in ('probe-before', 'probe-after'):
                capture = journey['captures'][label]
                frame = path.parent / (label + '.ppm')
                if hashlib.sha256(frame.read_bytes()).hexdigest() != capture['sha256']:
                    raise ValueError(label + ' frame hash mismatch')
            if record.get('error') or record.get('exit_code') != 0:
                raise ValueError('run did not exit cleanly')
            print('Saved strict UIKit journey: COMPLETE; actual markers and both frame hashes verified')
            print('Visual review and input provenance: inspect the report and control transcript')
        except (OSError, KeyError, TypeError, ValueError) as exc:
            print('Saved strict UIKit journey: evidence verification failed:', exc)
    else:
        print('Latest strict UIKit journey: incomplete or not enabled; see prior retained attempts')
else:
    print('Saved installed-iOS execution report: none')
print('Recovery/QMP-only evidence does not establish an installed-iOS or app journey')
print('Boot instructions: companion/BOOT.md; execution notes: PROGRESS.md')
sys.exit(0 if build_matches and evidence and evidence[1].get('passed') else 1)
