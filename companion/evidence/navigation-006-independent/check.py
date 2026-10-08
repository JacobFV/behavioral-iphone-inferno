#!/usr/bin/env python3
import json,hashlib,zipfile,importlib.util
from pathlib import Path
W=Path('/tmp/inferno-navigation-scroll-fix');R=Path('/home/brandonin/.local/share/inferno/app-import/navigation-demo-006');pins={}
def read(p):
 b=Path(p).read_bytes();pins[str(p)]=hashlib.sha256(b).hexdigest();return b
def js(p):return json.loads(read(p))
def check(p,h):assert hashlib.sha256(read(p)).hexdigest()==h
b=js(R/'build-evidence.json');a=js(W/'companion/navigation-demo/evidence/scroll-revision-006/audit.json');assert b['status']=='built-and-import-validated-not-executed' and b['guest_actions'] is False
for p,h in b['sources'].items():check(p,h)
for t in b['tools'].values():check(t['path'],t['sha256'])
for p,h in a['raw_files'].items():check(p,h)
check(R/'build.log',b['build_log_sha256']);check(b['ipa']['path'],b['ipa']['sha256']);check(b['manifest']['path'],b['manifest']['sha256'])
with zipfile.ZipFile(b['ipa']['path']) as z:
 assert sorted(z.namelist())==a['exact_zip_entries'];assert len(z.namelist())==3
 for n,x in b['bundle_files'].items():
  raw=z.read('Payload/NavigationDemo.app/'+n);assert len(raw)==x['bytes'] and hashlib.sha256(raw).hexdigest()==x['sha256'];check(R/'Payload/NavigationDemo.app'/n,x['sha256'])
spec=importlib.util.spec_from_file_location('sample_import',W/'companion/app-import.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);manifest=m.validate_manifest(Path(b['manifest']['path']));assert len(manifest['files'])==3 and not manifest['directories'] and manifest['tree_sha256']==b['manifest']['tree_sha256']
e=js(R.parent/'navigation-demo-005/import-audit.json');assert len(e['results'])==115 and all(x['export_chain'] for x in e['results'])
for p,h in e['executables'].items():check(p,h);check(str(p).replace('navigation-demo-005','navigation-demo-006'),h)
assert any(x['symbol']=='_OBJC_CLASS_$_UIScrollView' for x in e['results'])
l=js(R/'launcher/build-evidence.json');assert l['manifest_sha256']==b['manifest']['sha256'] and l['target']==manifest['bundle']
for n,h in l['outputs'].items():check(R/'launcher'/n,h)
log=(R/'build.log').read_text();assert all(json.dumps(cmd) in log for cmd in b['commands'])
for p,h in list(pins.items()):assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==h
out={'verdict':'PASS bounded independent source/build/import review; guest behavior untested','pins':pins,'ipa':b['ipa'],'manifest':b['manifest'],'exact_zip_entries':a['exact_zip_entries'],'total_bundle_bytes':sum(x['bytes'] for x in b['bundle_files'].values()),'source_findings':['CatalogScrollView adds no ivars; direct original UIScrollView superclass import is present in sample-local stub and retained export audit.','Override returns BOOL true only for UIButton instances and subclasses, otherwise calls super; explicit cancellation enabled, default delay unchanged.','New selectors use pointer/Class and scalar BOOL ABI consistently with existing narrow declarations; no new struct or ivar layout dependency.','Guide label ends at y390 before option row y405. Height increase plausibly addresses clipping but actual complete text still requires pixel review.','Final producer pins local UIKit stub but packages only executable, Info.plist and Guide.txt; superseded005 preserved.'],'export_scope':'115 retained original export-trie results bound to exact unchanged005/006 app/launcher/wrapper bytes; original multi-GB cache was not rehashed or reaudited. Symbol availability does not prove selector behavior.','limits':['No VM, staging, input, scrolling, text rendering or app execution by this review.','Existing fixed portrait geometry/non-ARC fixture limitations remain; this does not fix or explain system display stalls.']}
Path(__file__).with_name('audit.json').write_text(json.dumps(out,indent=2)+'\n');print(out['verdict'])
