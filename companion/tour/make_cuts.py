"""make_cuts.py SEGMENTS.json OUT.json : choose one clean segment per app and write the video cut list.

Segments come from segments.py (recorded frames inside each app's tour window).
A segment is skipped if a freeze was detected during or right after it. Later
passes win over earlier ones. Captions are written from what the frames show.
"""
import glob, json, os, sys

A = '/home/brandonin/.local/share/inferno/app-import'
segs = json.load(open(sys.argv[1]))

CAPTION = {
    'Settings': 'Settings, then into General.',
    'Clock': 'World Clock (Cupertino and New York), Alarm, a running Stopwatch with a lap, then Timer.',
    'Calendar': 'First launch: "What\'s New in Calendar".',
    'Photos': 'First launch: "What\'s New in Photos".',
    'Notes': '"Welcome to Notes", dismissed: the Notes list, then a new, empty note.',
    'Weather': 'Weather draws its Cupertino page; with no network there is no forecast.',
    'Books': '"Get Started", then Reading Now, which says it is offline.',
    'Health': '"Welcome to the New Health App", then "Set up Health Details".',
    'Wallet': 'Wallet: boarding passes and tickets, no cards.',
    'Home': '"Welcome to Home"; continuing fails to add a home without an iCloud account.',
    'TV': '"Welcome to Apple TV".',
    'News': '"Welcome to Apple News"; it reports no internet connection.',
    'Mail': '"Welcome to Mail" with the account providers.',
    'App Store': 'The App Store asks for a network connection; this emulated phone has none.',
    'Safari': 'Safari\'s start page with Favorites.',
    'Messages': 'Messages: an empty conversation list.',
    'Music': '"What\'s New in Apple Music".',
    'Phone': 'The Phone keypad.',
    'FaceTime': 'FaceTime asks for an Apple ID.',
    'Maps': 'Maps quits back to the Home screen on launch.',
    'Stocks': 'Stocks quits back to the Home screen on launch.',
}
# Apps whose best take is from a specific boot (a later take tapped while another screen was up).
PREFER = {'Calendar': 'tour-boot-3'}
ORDER = ['Settings', 'Clock', 'Calendar', 'Photos', 'Notes', 'Weather', 'Books', 'Health', 'Wallet', 'Home',
         'TV', 'News', 'Mail', 'App Store', 'Safari', 'Messages', 'Music', 'Phone', 'FaceTime', 'Maps', 'Stocks']
SKIP_IN_VIDEO = set(json.loads(os.environ.get('SKIP_APPS', '[]')))

best = {}
for s in segs:
    if s.get('tainted') or len(s['frames']) < 8:
        continue
    key = s['app']
    if key in PREFER and not s['boot'].endswith(PREFER[key]):
        continue
    # otherwise later boots/passes are appended later; prefer them
    best[key] = s

sections = [
    {'kind': 'card', 'seconds': 4, 'title': 'Real iOS on Linux: an app tour',
     'body': 'An emulated iPhone 11 running Apple\'s own iOS 14, set up from a fresh image on an ARM Linux server and driven only by virtual touches. Every phone frame below was captured from the emulator.'},
]
setup = sorted(glob.glob(A + '/fresh-boot-r6/boot/frames/*.ppm'))
if setup:
    sections.append({'kind': 'clip', 'kicker': 'FRESH DEVICE', 'label': 'Setup Assistant, from Hello',
                     'caption': 'Language, region, no Wi-Fi, no passcode, terms, then "Welcome to iPhone". About 25 gestures, 1-3 minutes per screen in pure CPU emulation.',
                     'frames': [[0, p] for p in setup[60:]], 'speed': 60, 'interval': 10})
demo = []
for r in sorted(glob.glob(A + '/tour-boot-1/rec/chunk-*/report.json'))[:6]:
    try:
        demo += [[c['time'], c['path']] for c in json.load(open(r))['captures'] if os.path.exists(c['path'])]
    except Exception:
        pass
# From the unlock swipe to just after the Home press (times from the action records).
demo = [c for c in demo if 1793274425 <= c[0] <= 1793274610]
if demo:
    sections.append({'kind': 'clip', 'kicker': 'BUILT ON LINUX', 'label': 'Lock screen, unlock, an imported app',
                     'caption': 'After setup the device restarts to the lock screen. An app compiled on Linux and installed as an IPA opens; two taps take its counter from 0 to 2.',
                     'frames': sorted(demo), 'speed': 8})
ran = []
for name in ORDER:
    if name not in best or name in SKIP_IN_VIDEO:
        continue
    fr = best[name]['frames']
    if len(fr) > 30:
        fr = fr[17:]  # drop the Home press and settle before the icon tap
    speed = max(3, round(len(fr) / 9))
    sections.append({'kind': 'clip', 'kicker': 'APPLE APP', 'label': name, 'caption': CAPTION.get(name, ''),
                     'frames': fr, 'speed': speed})
    ran.append(name)
sections.append({'kind': 'card', 'seconds': 6, 'kicker': 'WHAT RAN', 'title': '%d stock apps on a fresh device' % sum(1 for n in ran if n not in ('Maps', 'Stocks')),
                 'body': ', '.join(n for n in ran if n not in ('Maps', 'Stocks')) + '. Maps and Stocks quit on launch; Reminders and Podcasts launched but showed blank pages. Not shown: App Store apps, which are encrypted and are not decrypted, by design. Known open issue: the display intermittently freezes; the tour restarts the device and resumes.'})
json.dump({'sections': sections, 'apps': ran}, open(sys.argv[2], 'w'))
print(len(sections), 'sections;', ', '.join(ran))
