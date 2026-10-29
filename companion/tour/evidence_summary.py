"""evidence_summary.py OUT.json : small, reviewable record of the second-host fresh setup and app tour."""
import glob, hashlib, json, os, re, sys

A = '/home/brandonin/.local/share/inferno/app-import'
H = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
out = {'schema': 'inferno.app-tour-summary.v1', 'host_machine_id_prefix': open('/etc/machine-id').read()[:8],
       'chain': {}, 'setup_boot': {}, 'tour_boots': []}
for name in ['iv-r6', 'seed-r6', 'verify-r6', 'flatd-r6', 'grow-r6', 'kb-r6', 'flatk-r6', 'insp-r6', 'cache-r6', 'art-r6', 'fresh-r6']:
    js = [p for p in glob.glob(f'{A}/{name}/*.json') if os.path.basename(p) not in ('INCOMPLETE.json', 'failure.json')]
    main = [p for p in js if re.search(r'(initial-volumes|seeded-data|data-verified|flattened-data|grown-data|sep-keybag|flattened-keybag|runtime-inspection|renderer-cache|fresh-runtime-artifacts|fresh-runtime)\.json$', p)]
    if main:
        d = json.load(open(main[0]))
        out['chain'][name] = {'result': os.path.basename(main[0]), 'sha256': H(main[0]), 'status': d.get('status')}
b = f'{A}/fresh-boot-r6'
serial = open(b + '/boot/serial.log', 'rb').read()
out['setup_boot'] = {'completed_run_sha256': H(b + '/completed-run.json'),
                     'hid_ready': re.findall(rb'INFERNO_HID_READY[^\n]*', serial)[:1][0].decode(),
                     'hid_acks': serial.count(b'INFERNO_HID_ACK'),
                     'observed': 'Hello -> language -> United States -> Quick Start (manual) -> Wi-Fi skipped -> Data & Privacy -> no passcode -> no transfer -> Terms -> Express Settings -> Software Update -> iMessage later -> Siri later -> Screen Time later -> App Analytics declined -> Appearance -> Display Zoom -> "Welcome to iPhone"; ended with finish-observation',
                     'stopped_retention_sha256': H(b + '/boot/stopped-disk-hashes.json')}
for B in sorted(glob.glob(f'{A}/tour-boot-*'), key=lambda p: int(p.rsplit('-', 1)[1])):
    rec = {'boot': os.path.basename(B), 'apps_completed': [], 'freeze_after': [], 'hid_acks': 0}
    try:
        rec['hid_acks'] = open(B + '/serial.log', 'rb').read().count(b'INFERNO_HID_ACK')
    except OSError:
        pass
    for t in sorted(glob.glob(B + '/tour-*/actions.json')):
        a = json.load(open(t))
        rec['apps_completed'] += [x['app_end'] for x in a if 'app_end' in x]
        rec['freeze_after'] += [x['frozen_after'] for x in a if 'frozen_after' in x]
    rec['frames_recorded'] = len(glob.glob(B + '/rec/chunk-*/observed-*.png'))
    out['tour_boots'].append(rec)
json.dump(out, open(sys.argv[1], 'w'), indent=1)
print(json.dumps({k: (len(v) if isinstance(v, (list, dict)) else v) for k, v in out.items()}))
