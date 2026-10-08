import importlib.util,sys,json,hashlib,time
from pathlib import Path
root=Path('/tmp/inferno-stage-import/companion');sys.path.insert(0,str(root))
spec=importlib.util.spec_from_file_location('stage_import',root/'stage-import.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
session=Path('/home/brandonin/.local/share/inferno/app-import/prepare-session-demo-2/session.json')
started=time.time();c=m.validate_session(session,m.digest(session));report=session.parent/'recovery-run/report.json'
r=m.check_completed_report(c,report)
result={'scope':'Read-only replay; no coordinator VM launch, chmod or preservation invocation','sources':{str(root/n):m.digest(root/n) for n in ('stage-import.py','import_stage.py')},'session_sha256':m.digest(session),'report_sha256':m.digest(report),'fixed_command':m.fixed_command(c,Path('/tmp/EXAMPLE-NEW-stage/recovery-run')),'actual_runtime_base_layers':c['verified_runtime']['base']['layers'],'normal_report_check':True,'verified_stopped':m.verify_stopped(c,report,report.parent/'stopped-disk-hashes.json',session.parent/'content-check.json'),'negative_reports':[]}
for name in ('disk-preparation-imported-fixture-1','disk-preparation-imported-demo-1'):
 p=Path('/home/brandonin/Documents/behavioral-iphone-inferno/.local-build/reports')/name/'report.json'
 if not p.exists():continue
 try:m.check_completed_report(c,p);out={'rejected':False}
 except Exception as e:out={'rejected':True,'error':str(e)}
 result['negative_reports'].append({'path':str(p),'sha256':m.digest(p),**out})
result['elapsed_seconds']=time.time()-started
Path('/tmp/stage-import-readonly-review/result.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'normal_report_check':True,'stopped_eligible':result['verified_stopped']['eligible'],'negative_reports':result['negative_reports'],'elapsed':result['elapsed_seconds']}))
