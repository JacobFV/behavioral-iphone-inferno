#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""One actual CLI import followed by unchanged shared validation under umask077."""
import argparse,hashlib,importlib.util,json,os,stat,subprocess,sys
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--importer',type=Path,required=True);p.add_argument('--ipa',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--expect',choices=['rejected','accepted'],required=True);a=p.parse_args()
a.output.mkdir(mode=0o700)
h=lambda x:hashlib.sha256(x.read_bytes()).hexdigest()
source_before=h(a.importer);old=os.umask(0o077)
try:
 cmd=[sys.executable,str(a.importer),'--ipa',str(a.ipa),'--output',str(a.output/'imported')]
 with (a.output/'stdout.log').open('xb')as out,(a.output/'stderr.log').open('xb')as err:r=subprocess.run(cmd,stdout=out,stderr=err,check=False)
 spec=importlib.util.spec_from_file_location('mode_importer',a.importer);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
 path=a.output/'imported/manifest.json';status='accepted';error=None
 try:validated=m.validate_manifest(path)
 except ValueError as exc:status='rejected';error=str(exc)
 observed=os.umask(0o077);assert observed==0o077
 assert r.returncode==0 and status==a.expect and source_before==h(a.importer)
 manifest=json.loads(path.read_text());target=path.parent/manifest['bundle']['relative_path']
 result={'scope':'Actual CLI then shared read-only validator; no guest actions','argv':cmd,'exit_code':r.returncode,'source':{'path':str(a.importer),'sha256':source_before},'ipa':{'path':str(a.ipa),'sha256':h(a.ipa)},'stdout_sha256':h(a.output/'stdout.log'),'stderr_sha256':h(a.output/'stderr.log'),'manifest_sha256':h(path),'validator':status,'error':error,'bundle_mode':oct(stat.S_IMODE(target.stat().st_mode)),'caller_umask_after':'077','input_bytes_preserved':all(h(target/f['path'])==f['sha256']for f in manifest['files'])}
 (a.output/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
finally:os.umask(old)
