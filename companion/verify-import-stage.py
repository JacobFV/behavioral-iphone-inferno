#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Verify raw imported-stage content or normally stopped stage eligibility. Never controls a VM."""
import argparse,json,time
from pathlib import Path
from import_stage import validate_session,verify_content,verify_stopped

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--session',required=True,type=Path);p.add_argument('--session-sha256',required=True)
    p.add_argument('--serial',type=Path,help='Content-only check before finish; no eligibility')
    p.add_argument('--report',type=Path);p.add_argument('--retention',type=Path);p.add_argument('--content-check',type=Path)
    p.add_argument('--output',required=True,type=Path)
    a=p.parse_args()
    if bool(a.serial)==bool(a.report) or bool(a.report)!=bool(a.retention) or bool(a.report)!=bool(a.content_check):p.error('Choose serial-only or report plus retention')
    if a.output.exists() or a.output.is_symlink():p.error('Output must be new')
    try:
        c=validate_session(a.session,a.session_sha256)
        started=time.time()
        raw=a.serial.read_bytes() if a.serial else None
        captured=time.time()
        result=verify_content(raw,c['manifest'],c['artifact_sizes']) if a.serial else verify_stopped(c,a.report,a.retention,a.content_check)
        if a.serial:result.update(session_sha256=c['session_sha256'],eligible=False,read_started_time=started,captured_time=captured)
        with a.output.open('x') as f:json.dump(result,f,indent=2);f.write('\n')
        print(json.dumps({'output':str(a.output),'eligible':result.get('eligible',False),'content_verified':result.get('content_verified',result.get('content',{}).get('content_verified'))}))
    except (ValueError,OSError,KeyError,TypeError) as e:p.exit(1,'verify-import-stage rejected: '+str(e)+'\n')
if __name__=='__main__':main()
