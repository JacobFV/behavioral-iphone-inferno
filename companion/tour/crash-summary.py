#!/usr/bin/env python3
"""crash-summary.py FILE APP... : from a crash-lane text (INFERNO_APP_CRASH blocks copied off the
serial console), print each named app's first crash report: exception, termination reason and the
crashed thread's top frames, with images named. Blocks whose path doesn't name the app are skipped."""
import re, sys

text = open(sys.argv[1], errors='replace').read()
for app in sys.argv[2:]:
    blocks = re.findall(r'INFERNO_APP_CRASH_BEGIN (\S+)\n(.*?)INFERNO_APP_CRASH_END', text, re.S)
    own = [(p, b) for p, b in blocks if app.lower().replace(' ', '') in p.lower().replace(' ', '')]
    if not own:
        print(f'== {app}: no crash report of its own'); continue
    path, body = own[0]
    print(f'== {app}: {path.split("/")[-1]} ({len(own)} report blocks)')
    for key in ('Exception Type:', 'Exception Subtype:', 'Exception Codes:', 'Termination Reason:',
                'Termination Description:', 'Application Specific Information:', 'Crashed Thread:'):
        m = re.search(re.escape(key) + r'(.*)', body)
        if m: print('  ', key, m.group(1).strip()[:160])
    m = re.search(r'Application Specific Information:\n(.*?)\n\n', body, re.S)
    if m: print('   ', m.group(1).strip().replace('\n', ' | ')[:300])
    m = re.search(r'Thread \d+ Crashed:[^\n]*\n', body)
    if m:
        frames = [l for l in body[m.end():].splitlines()[:40] if re.match(r'\s*\d+\s+\S', l)][:14]
        for line in frames: print('    ', re.sub(r'\s+', ' ', line.strip())[:110])
