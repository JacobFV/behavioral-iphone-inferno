"""make_cuts2.py SPEC.json OUT.json : cut list for imported-app sessions (try-app.sh runs), for build_tour.py.

SPEC.json: {"sections": [{"kind": "card", ...} | {"kind": "session", "session": NAME, "kicker": ..., "label": ...,
                          "caption": ..., "seconds": 9}]}
For a session, the clip starts after bring-up (the newest bring-* action directory) and runs to the end of the
recording; frames are subsampled evenly so the clip lasts about `seconds`, and the speed-up it states is the
real ratio of recorded time to screen time. Frames are never edited, only chosen.
"""
import glob, json, os, statistics, sys

A = os.path.expanduser('~/.local/share/inferno/app-import')
FPS = 30
spec = json.load(open(sys.argv[1]))
out = []
for sec in spec['sections']:
    if sec['kind'] != 'session':
        out.append(sec); continue
    B = '%s/session-%s' % (A, sec['session'])
    caps = []
    for r in sorted(glob.glob(B + '/rec/chunk-*/report.json')):
        try: caps += [(c['time'], c['path']) for c in json.load(open(r)).get('captures', []) if os.path.exists(c['path'])]
        except Exception: pass
    caps.sort()
    ready = max([os.path.getmtime(d) for d in glob.glob(B + '/bring-*')] or [caps[0][0] if caps else 0])
    caps = [c for c in caps if c[0] >= ready + sec.get('skip', 0)]
    if sec.get('until'): caps = [c for c in caps if c[0] <= ready + sec['until']]
    if len(caps) < 2:
        print('skip (no frames after bring-up):', sec['session']); continue
    span = caps[-1][0] - caps[0][0]
    want = max(2, round(sec.get('seconds', 9) * FPS / 3))   # each shown frame held >= 3 video frames
    step = max(1, -(-len(caps) // want))                     # ceil: never longer than asked
    pick = caps[::step]
    interval = span / max(1, len(pick) - 1)                  # recorded seconds per shown frame
    speed = interval * FPS / 3                               # 3 video frames per shown frame
    speed = max(1, round(speed))
    out.append({'kind': 'clip', 'kicker': sec.get('kicker', 'APP'), 'label': sec['label'], 'caption': sec.get('caption', ''),
                'frames': [list(c) for c in pick], 'speed': speed, 'interval': round(interval, 3)})
    print('%-28s %4d frames  span %5.0fs  speed %dx' % (sec['session'], len(pick), span, speed))
json.dump({'sections': out}, open(sys.argv[2], 'w'))
