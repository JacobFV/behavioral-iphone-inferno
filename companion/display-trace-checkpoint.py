#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Record a read-only, file-visible boundary in a report's fixed display trace log."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True, help='New checkpoint JSON file')
    args = parser.parse_args()
    try:
        if args.output.exists():
            raise ValueError('Output must be a new file')
        report = args.report.resolve(strict=True)
        raw_report = (report / 'report.json').read_bytes()
        json.loads(raw_report)  # Live and stopped reports are both eligible.
        helper = Path(__file__).resolve().with_name('owned-control.py')
        spec = importlib.util.spec_from_file_location('inferno_owned_control', helper)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        checkpoint = module.trace_checkpoint(report)
        result = {
            'schema': 'inferno.display-trace-checkpoint.v1',
            'report': str(report),
            'report_sha256': hashlib.sha256(raw_report).hexdigest(),
            'helper_path': str(helper),
            'helper_sha256': hashlib.sha256(helper.read_bytes()).hexdigest(),
            'source_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'checkpoint': checkpoint,
            'scope': ('Read-only file-visible guest-errors.log boundary. No QMP or guest input. '
                      'Buffered trace emission prevents exact device-event times or per-tap draw attribution. '
                      'The report hash describes bytes read before the checkpoint; a live report may change.')}
        with args.output.open('x') as stream:
            json.dump(result, stream, indent=2)
            stream.write('\n')
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    print(json.dumps({'output': str(args.output), 'checkpoint': checkpoint}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
