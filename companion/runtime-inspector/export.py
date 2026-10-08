#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Reconstruct a completed fixed launchd export into NEW external output; no VM."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
from result import verify_content

HERE = Path(__file__).resolve().parent

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--serial', type=Path, required=True)
    parser.add_argument('--serial-sha256', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    previous = os.umask(0o077)
    try:
        spec = importlib.util.spec_from_file_location('inspector_importer', HERE.parent / 'app-import.py')
        importer = importlib.util.module_from_spec(spec); spec.loader.exec_module(importer)
        output = importer.external_output(args.output)
        source_pins = {str(p): hashlib.sha256(p.read_bytes()).hexdigest()
                       for p in (HERE / 'export.py', HERE / 'result.py', HERE.parent / 'app-import.py')}
        source = args.serial.resolve(strict=True)
        if source != args.serial.absolute() or not source.is_file() or source.stat().st_size > 64 << 20:
            raise ValueError('Missing/aliased/oversized serial')
        raw = source.read_bytes()
        if hashlib.sha256(raw).hexdigest() != args.serial_sha256:
            raise ValueError('Serial hash mismatch')
        content, exported = verify_content(raw)
        if any(hashlib.sha256(Path(p).read_bytes()).hexdigest() != h for p,h in source_pins.items()):
            raise ValueError('Reconstruction source changed')
        if source.read_bytes() != raw:
            raise ValueError('Serial changed during reconstruction')
        output.mkdir(mode=0o700)
        with (output / 'launchd.plist').open('xb') as stream:
            stream.write(exported); stream.flush(); os.fsync(stream.fileno())
        record = {'schema': 'inferno.runtime-cache-export.v1', 'serial': str(source),
                  'content': content, 'output': str(output / 'launchd.plist'),
                  'runtime_base_eligible': False, 'ipa_runtime_ready': False,
                  'sources': source_pins}
        with (output / 'export.json').open('x') as stream:
            json.dump(record, stream, indent=2); stream.write('\n')
        print(json.dumps({'export': str(output / 'export.json'), 'launchd_sha256': content['launchd']['sha256']}))
        return 0
    except Exception as exc:
        parser.exit(1, str(exc) + '\n')
    finally:
        os.umask(previous)

if __name__ == '__main__':
    raise SystemExit(main())
