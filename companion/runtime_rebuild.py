# SPDX-License-Identifier: AGPL-3.0-or-later
"""Explicit, recorded substitution of the lost pinned emulator build.

Historical stage records pin the original emulator binary and build manifest by
path and SHA256. Those bytes were lost with .local-build. The clean rebuild of
the same committed source is not byte-identical. Consumers that revalidate the
historical records may treat exactly the recorded path/hash pairs as satisfied
by the recorded rebuild, and only inside historical(). New executions record
and expect the actual rebuilt hashes; nothing here rewrites an old record.
"""
import contextlib
import hashlib
import importlib.machinery
import json
from pathlib import Path
import types

SOURCE = Path(__file__).resolve().parent
RECORD = SOURCE / 'evidence/runtime-rebuild-1/substitution.json'
RECORD_SHA256 = 'cac4c9ce52ecd681255355caac253f4218c09a0b74aa6be48f261a869a90d6f8'
_active = [0]


def _digest(path):
    with Path(path).open('rb') as f: return hashlib.file_digest(f, 'sha256').hexdigest()


def load():
    """Validate the tracked record against current files; return a summary."""
    if RECORD.is_symlink() or _digest(RECORD) != RECORD_SHA256: raise ValueError('Runtime substitution record changed')
    record = json.loads(RECORD.read_text())
    for key in ('rebuild_driver', 'rebuild_log', 'original_manifest_evidence', 'rebuilt_manifest_evidence', 'smoke'):
        if _digest(SOURCE.parent / record[key]['path']) != record[key]['sha256']: raise ValueError('Runtime substitution evidence changed: ' + key)
    old = json.loads((SOURCE.parent / record['original_manifest_evidence']['path']).read_text())
    new = json.loads((SOURCE.parent / record['rebuilt_manifest_evidence']['path']).read_text())
    if {k: v for k, v in old.items() if k != 'binary'} != {k: v for k, v in new.items() if k != 'binary'} or old['binary']['path'] != new['binary']['path']:
        raise ValueError('Rebuilt manifest differs beyond binary bytes')
    subs = record['substitutions']
    if set(subs) != {new['binary']['path'], str(Path(new['binary']['path']).parent.parent / 'build-manifest.json')}: raise ValueError('Unexpected substitution paths')
    for path, entry in subs.items():
        p = Path(path)
        if p.is_symlink() or p.resolve(strict=True) != p or _digest(p) != entry['rebuilt_sha256']: raise ValueError('Current rebuilt runtime differs from record: ' + path)
    if subs[new['binary']['path']]['rebuilt_sha256'] != new['binary']['sha256'] or subs[new['binary']['path']]['pinned_sha256'] != old['binary']['sha256']: raise ValueError('Binary substitution differs from manifests')
    if _digest(SOURCE.parent / record['rebuilt_manifest_evidence']['path']) != subs[str(Path(new['binary']['path']).parent.parent / 'build-manifest.json')]['rebuilt_sha256']: raise ValueError('Manifest substitution differs from retained copy')
    return {'record': str(RECORD), 'record_sha256': RECORD_SHA256, 'source_sha256': _digest(Path(__file__)), 'substitutions': subs}


def current(path, pinned):
    """Map a historical pin of a substituted path to the hash new runs must use."""
    entry = load()['substitutions'].get(str(Path(path).absolute()))
    return entry['rebuilt_sha256'] if entry and entry['pinned_sha256'] == pinned else pinned


def _companion_modules(root):
    seen = {}; queue = [root]
    while queue:
        module = queue.pop()
        if id(module) in seen: continue
        seen[id(module)] = module
        for value in vars(module).values():
            if isinstance(value, types.ModuleType) and str(getattr(value, '__file__', '') or '').startswith(str(SOURCE) + '/'): queue.append(value)
    return list(seen.values())


def _wrap(original, subs):
    def historical_sha(path):
        actual = original(path)
        if not isinstance(path, (str, Path)): return actual
        entry = subs.get(str(Path(path).absolute()))
        return entry['pinned_sha256'] if _active[0] and entry and actual == entry['rebuilt_sha256'] else actual
    historical_sha.inferno_runtime_substitution = original
    return historical_sha


def _wrap_record(original, subs, retained):
    # The pinned manifest bytes survive in tracked evidence; historical reads use them.
    def historical_record(path):
        if _active[0] and isinstance(path, (str, Path)) and str(Path(path).absolute()) in retained:
            entry = subs[str(Path(path).absolute())]; copy = retained[str(Path(path).absolute())]
            if _digest(path) == entry['rebuilt_sha256'] and _digest(copy) == entry['pinned_sha256']: return original(copy)
        return original(path)
    historical_record.inferno_runtime_substitution = original
    return historical_record


def install(*roots):
    """Wrap hash/record helpers of all loaded companion modules; inert until historical()."""
    summary = load(); subs = summary['substitutions']; record = json.loads(RECORD.read_text())
    manifest = [p for p in subs if p.endswith('/build-manifest.json')][0]
    retained = {manifest: SOURCE.parent / record['original_manifest_evidence']['path']}
    def wrap_module(module):
        for name, wrapper in (('sha', lambda v: _wrap(v, subs)), ('digest', lambda v: _wrap(v, subs)), ('bounded_record', lambda v: _wrap_record(v, subs, retained))):
            value = getattr(module, name, None)
            if callable(value) and not hasattr(value, 'inferno_runtime_substitution') and getattr(value, '__code__', None) is not None and value.__code__.co_argcount == 1:
                setattr(module, name, wrapper(value))
    for module in {id(m): m for r in roots for m in _companion_modules(r)}.values(): wrap_module(module)
    # Producers load predecessor validators lazily by file path; wrap those too.
    loader = importlib.machinery.SourceFileLoader
    if not hasattr(loader.exec_module, 'inferno_runtime_substitution'):
        original = loader.exec_module
        def exec_module(self, module):
            original(self, module)
            if str(getattr(module, '__file__', '') or '').startswith(str(SOURCE) + '/'): wrap_module(module)
        exec_module.inferno_runtime_substitution = original
        loader.exec_module = exec_module


@contextlib.contextmanager
def historical():
    load(); _active[0] += 1
    try: yield
    finally: _active[0] -= 1
