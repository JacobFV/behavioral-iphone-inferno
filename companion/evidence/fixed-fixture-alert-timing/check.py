# SPDX-License-Identifier: AGPL-3.0-or-later
"""Read-only actual template/submission checks; never send input or start a VM."""
import importlib.util,json,sys,time,argparse
from pathlib import Path
source=Path('/tmp/inferno-initial-volumes-doc-link/companion/fixed-fixture-alert-timing.py');main=Path('/home/brandonin/Documents/behavioral-iphone-inferno/companion');sys.path.insert(0,str(main))
spec=importlib.util.spec_from_file_location('timing_check',source);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
root=main/'evidence/imported-fixture-91-visual';refs=m.templates(root)
assert len(set(refs.values()))==3
qmp=m.pixels(root/'probe-before.png',828);assert qmp==refs['zero']
report=main.parent/'.local-build/reports/app-boot-91'
unlock=m.submission(report,root/'unlock-002/submission.json',{'kind':'swipe','duration_ms':1500,'x0':16384,'y0':32270,'x1':16384,'y1':9145})
ack=m.ack(report,unlock['request_id'])
command=m.record(report/'command.json');private=command[command.index('-vnc')+1][5:].rsplit('/',1)[0]
template=source.parent/'evidence/fixed-fixture-alert-timing/command-template.json'
assert m.sha(m.read(template))==m.COMMAND_TEMPLATE_SHA
assert [x.replace(str(report),'@REPORT@').replace(private,'@PRIVATE@') for x in command]==m.record(template)
# Calling guard on a stopped actual report must reject before any command/output.
m.HERE=main
args=argparse.Namespace(report=report,boot_uuid='unused-stopped-rejection',second_unlock=root/'unlock-002/submission.json',output=Path('/tmp/inferno-fixed-timing-stopped-negative-output'))
assert not args.output.exists()
d=m.Driver(args);d.wall0=time.time();d.mono0=time.monotonic()
try:d.guard()
except ValueError as exc:rejection=str(exc)
else:raise AssertionError('Stopped report accepted')
assert not args.output.exists() and rejection=='Active runtime/source pins differ'
print(json.dumps({'scope':'Actual read-only run91 template/submission replay plus stopped-report rejection; no guest actions or command submission','source_sha256':m.sha(source.read_bytes()),'templates':m.TEMPLATES,'fixed_crop':list(m.CROP),'vnc_dimensions':[832,1792],'qmp_dimensions':[828,1792],'actual_qmp_before_matches_exact_vnc_zero_crop':True,'three_templates_distinct':True,'second_unlock':unlock,'ack_evidence':ack,'stopped_rejection':rejection,'output_not_created':True},indent=2))
