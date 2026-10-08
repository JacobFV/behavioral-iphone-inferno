#!/usr/bin/env python3
"""Retained actual raw-content replay, plus explicitly synthetic negative mutations."""
import sys,json,hashlib
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from import_stage import verify_content
main=Path('/home/brandonin/Documents/behavioral-iphone-inferno')
base=main/'.local-build/reports';d=Path('/home/brandonin/.local/share/inferno/app-import/ipa-demo-001')
m=json.loads((d/'imported/manifest.json').read_text())
sizes={'exec_wrapper':67392,'system_launcher':69136,'launchd_cache':596664}
results={}
for name in ('disk-preparation-imported-fixture-1','disk-preparation-imported-fixture-2','disk-preparation-imported-demo-1','disk-preparation-imported-demo-2'):
 raw=(base/name/'serial.log').read_bytes()
 selected=m; selected_sizes=sizes; fixture='fixture' in name
 if fixture:
  selected=json.loads(Path('/home/brandonin/.local/share/inferno/app-import/owned-fixture-final-2/imported/manifest.json').read_text());selected_sizes={}
 try:r=verify_content(raw,selected,selected_sizes,identical_fixture=fixture);accepted=True;error=None
 except ValueError as exc:accepted=False;error=str(exc)
 assert accepted==(name.endswith('demo-2'))
 results[name]={'actual_raw_sha256':hashlib.sha256(raw).hexdigest(),'accepted_content':accepted,'error':error}
raw=(base/'disk-preparation-imported-demo-2/serial.log').read_bytes()
mutations={'duplicate_begin':raw+ b'INFERNO_PREP_BEGIN: disposable /dev/disk0s1 existing=1 roles=0 gigalocker=0\n','wrong_size':raw.replace(b'bytes=71939 entries=3',b'bytes=71938 entries=3'),'missing_complete':raw.replace(b'INFERNO_PREP_COMPLETE',b'ABSENT_COMPLETE'),'late_failure':raw+b'INFERNO_IMPORTED_APP_FINISH result=89 unmount=0 errno=0\n','unexpected_operation':raw+b'INFERNO_KEYBAG_COMPLETE\n','malformed_status':raw+b'INFERNO_PREP_STATUS raw=14\n','unterminated_complete':raw[:raw.index(b'INFERNO_PREP_COMPLETE')]+b'INFERNO_PREP_COMPLETE: requested preparation operations succeeded'}
for name,value in mutations.items():
 try:verify_content(value,m,sizes)
 except ValueError as exc:results['synthetic_'+name]={'rejected':True,'error':str(exc)}
 else:raise AssertionError(name)
# Actual old success was SIGTERM, never pretend it satisfies the new normal-stop contract.
r=json.loads((base/'disk-preparation-imported-demo-2/report.json').read_text())
assert r.get('error') and not r['attempt_completed']
results['demo2_normal_finish']={'accepted':False,'actual_error':r['error'],'attempt_completed':r['attempt_completed'],'scope':'Direct normal-report prerequisite, not synthesized session replay.'}
print(json.dumps(results,indent=2))
