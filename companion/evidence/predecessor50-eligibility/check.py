# SPDX-License-Identifier: AGPL-3.0-or-later
"""Read-only current-loader verification; does not create overlays or change modes."""
import hashlib,importlib.util,json,time
from pathlib import Path
ROOT=Path('/home/brandonin/Documents/behavioral-iphone-inferno');D=Path(__file__).resolve().parent
source=ROOT/'companion/disk_overlay.py';spec=importlib.util.spec_from_file_location('overlay',source);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
r=ROOT/'.local-build/reports/disk-preparation-50';record=json.loads((r/'root-overlay.json').read_text());start=time.time()
try: result={'accepted':True,'chain':m.load_stopped_overlay(r/'report.json',record['tool'])}
except Exception as e: result={'accepted':False,'error_type':type(e).__name__,'error':str(e)}
result.update(started=start,finished=time.time(),loader_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),scope='Read-only loader full hashes/headers/FD checks; no new overlay or permission changes.')
(D/'loader-result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k!='chain'}))
