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
print('Full iOS / SpringBoard boot: NOT YET ESTABLISHED')
print('UIKit app journey: NOT YET ESTABLISHED (owned recovery native probe has executed)')
print('Boot instructions: companion/BOOT.md; execution notes: PROGRESS.md')
sys.exit(0 if build_matches and evidence and evidence[1].get('passed') else 1)
