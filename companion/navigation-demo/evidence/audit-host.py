#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Reuse the existing original-cache export audit, then inspect three dynamic class exports."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--build',required=True,type=Path)
p.add_argument('--cache',required=True,type=Path)
p.add_argument('--objdump',required=True)
a=p.parse_args()
source=Path(__file__).resolve().parents[2]/'app-probe/audit-imports.py'
out=a.build/'import-audit.json'
classes=a.build/'dynamic-classes-audit.json'
if out.exists() or classes.exists():raise ValueError('Fresh audit outputs required')
raw=source.read_bytes()
# Execute the unmodified sibling script in a retained namespace so its exact
# export-trie resolver (not a second parser) also checks dynamically named classes.
sys.argv=[str(source),'--cache',str(a.cache),'--objdump',a.objdump,'--output',str(out),
          str(a.build/'Payload/NavigationDemo.app/NavigationDemo'),
          str(a.build/'launcher/inferno-launcher'),str(a.build/'launcher/inferno-exec-launcher')]
namespace={'__name__':'__main__','__file__':str(source)}
try:exec(compile(raw,str(source),'exec'),namespace)
except SystemExit as result:
    if result.code!=0:raise
results={name:namespace['resolve']('/System/Library/Frameworks/UIKit.framework/UIKit','_OBJC_CLASS_$_'+name)
         for name in ('UINavigationController','UIScrollView','UISwitch')}
if not all(results.values()):raise ValueError('Missing original UIKit class export')
if source.read_bytes()!=raw:raise ValueError('Audit source changed')
classes.write_text(json.dumps({'source':str(source),'source_sha256':hashlib.sha256(raw).hexdigest(),
  'cache_sha256':namespace['report']['cache_sha256'],'dynamic_class_export_chains':results,
  'scope':'Exports exist in supplied original cache; selector ABI, initialization and UI behavior remain unexecuted.'},indent=2)+'\n')
