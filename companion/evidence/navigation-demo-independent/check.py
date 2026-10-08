#!/usr/bin/env python3
"""Read-only owned sample build/import review. Does not build or execute a guest."""
from pathlib import Path
import json,hashlib,importlib.util,zipfile
W=Path('/tmp/inferno-initial-volumes-doc-link');B=Path('/home/brandonin/.local/share/inferno/app-import');P=B/'navigation-demo-004';pins={}
def sha(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def read(p):
 b=p.read_bytes();pins[str(p)]={'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()};return b
def js(p):return json.loads(read(p))
r=js(P/'build-evidence.json');assert r['status']=='built-and-import-validated-not-executed' and r['guest_actions'] is False and not (P/'INCOMPLETE').exists()
for path,h in r['sources'].items():assert hashlib.sha256(read(Path(path))).hexdigest()==h
for name,t in r['tools'].items():assert sha(Path(t['path']))==t['sha256'] and str(Path(t['path']).resolve())==t['resolved_path']
assert hashlib.sha256(read(P/'build.log')).hexdigest()==r['build_log_sha256']
ipa=Path(r['ipa']['path']);assert sha(ipa)==r['ipa']['sha256'] and ipa.stat().st_size==r['ipa']['bytes']
spec=importlib.util.spec_from_file_location('owned_importer',W/'companion/app-import.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
manifest=m.validate_manifest(Path(r['manifest']['path']));assert sha(Path(r['manifest']['path']))==r['manifest']['sha256'];assert manifest['tree_sha256']==r['manifest']['tree_sha256'];assert manifest['bundle']['identifier']=='org.inferno.companion.navigationdemo'
with zipfile.ZipFile(ipa) as z:
 assert sorted(z.namelist())==['Payload/NavigationDemo.app/Guide.txt','Payload/NavigationDemo.app/Info.plist','Payload/NavigationDemo.app/NavigationDemo']
 for name,item in r['bundle_files'].items():
  data=read(P/'Payload/NavigationDemo.app'/name);assert hashlib.sha256(data).hexdigest()==item['sha256'] and len(data)==item['bytes'] and z.read('Payload/NavigationDemo.app/'+name)==data
launcher=js(P/'launcher/build-evidence.json');assert launcher['manifest_path']==r['manifest']['path'] and launcher['manifest_sha256']==r['manifest']['sha256'] and launcher['target']==manifest['bundle']
for name,h in launcher['outputs'].items():assert hashlib.sha256(read(P/'launcher'/name)).hexdigest()==h
binding=js(P/'prior-export-audit-binding.json')
for rel,x in binding['compared'].items():assert sha(B/'navigation-demo-003'/rel)==sha(P/rel)==x['prior']==x['current']
for name in ['prior_import_audit','prior_dynamic_class_audit']:
 x=binding[name];assert hashlib.sha256(read(Path(x['path']))).hexdigest()==x['sha256']
imports=js(Path(binding['prior_import_audit']['path']));assert len(imports['results'])==110 and all(x['export_chain'] for x in imports['results'])
for path,h in imports['executables'].items():assert sha(Path(path))==h
for n in ['navigation-demo-001','navigation-demo-002']:assert (B/n/'INCOMPLETE').exists()
for p,x in pins.items():assert sha(Path(p))==x['sha256']
result={'verdict':'PASS bounded owned-source and actual host build/import review; no identified execution blocker from declarations','inputs':pins,'source_revision':r['git_revision'],'manifest':r['manifest'],'ipa':r['ipa'],'commands':r['commands'],'tool_records_rehashed':r['tools'],'import_export_audit_binding':'Exact004/003 executables and IPA bytes match; existing actual110-import and3dynamic-class audit reused. Original2GiB cache not rehashed.','abi_review':['Corrected inherited NSObject includes8-byteClass isa; direct delegate _window cannot occupy offset0 under this declaration.','NSInteger/NSUInteger64bit, CGFloatdouble, CGRect32bytes andCGSize16bytes match existing ARM64 sample declarations.','Navigation/push/pop/viewWillAppear/switch/scroll selector argument shapes coherent; dynamic class export existence is not selector execution proof.','UISwitch local interface derivesUIView rather than declaringUIControl; no owned subclass/layout access depends on intermediate framework ivars.'], 'behavior_review':['Twelve tagged buttons in ordinary UIScrollView push detail controllers; bundle Guide.txt loaded with Foundation and explicit failure label.','Switch changes label; Save copies selection/option into process globals and increments count before pop; Back alone leaves saved globals unchanged.','Fixed414-pointportrait geometry and non-ARC retained views/controllers are limited fixture choices; repeated transitions can retain allocations. No persistence or arbitrary app compatibility.'],'limits':['No guest install, original launch, navigation, scroll, switch, resource display or save demonstrated here.','No new grants/network/telemetry or Apple implementation bytes introduced.','Failed001 linkerinvocation and002 umask attempts remain INCOMPLETE; only004 is final host result.']}
Path(__file__).with_name('review.json').write_text(json.dumps(result,indent=2)+'\n');print('PASS actual owned NavigationDemo004 byte/source/tool/import audit')
if __name__=='__main__':pass
