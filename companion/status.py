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
for path in reports:
    try:
        record = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        continue
    if record.get('binary_sha256') == digest:
        evidence = (path, record)
        break
print('Repository:', root)
print('Branch:', branch, '| HEAD:', head)
changes = subprocess.check_output(['git', '-C', str(root), 'status', '--porcelain'], text=True).strip()
print('Working tree:', 'changes present; commit source before building' if changes else 'clean')
print('Build:', 'present; SHA256 matches build manifest' if build_matches else 'missing or does not match build manifest')
print('Built source:', manifest.get('source_revision', 'none'))
print('Binary:', binary)
if evidence:
    print('Last matching QMP evidence:', 'PASS' if evidence[1].get('passed') else 'FAIL')
    print('Report:', evidence[0])
else:
    print('Matching QMP evidence: none; run companion/run check')
print('iOS boot: NOT YET PERFORMED')
print('App execution: NOT YET PERFORMED')
print('Next session: read NEXT_SESSION.md; continue with the iOS boot profile')
sys.exit(0 if build_matches and evidence and evidence[1].get('passed') else 1)
