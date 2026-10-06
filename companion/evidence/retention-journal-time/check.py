import copy, hashlib, importlib.util, json, pathlib, sys
repo=pathlib.Path(sys.argv[1]); source=repo/'companion/preserve-stopped.py'
sys.path.insert(0,str(repo/'companion'))
spec=importlib.util.spec_from_file_location('preserver',source); module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
folder=pathlib.Path('/home/brandonin/Documents/behavioral-iphone-inferno/.local-build/reports/app-boot-49')
report=json.loads((folder/'report.json').read_text()); original=report['root_overlay']['backing_after_stop']; fresh=json.loads((folder/'ancestor-recheck.json').read_text())
def same(a,b):return module.backing_comparison(a)==module.backing_comparison(b)
checks={}
checks['actual49_new_check_times_allowed']=same(original,fresh)
changed=copy.deepcopy(fresh);changed['metadata_revalidation'][0]['sidecar_sha256']='0'*64
checks['sidecar_hash_change_rejected']=not same(original,changed)
changed=copy.deepcopy(fresh);changed['metadata_revalidation'][0]['actual_verified']['ctime_ns']+=1
checks['attested_identity_change_rejected']=not same(original,changed)
changed=copy.deepcopy(fresh);changed['layers'][0]['sha256']='0'*64
checks['ancestor_content_change_rejected']=not same(original,changed)
legacy=copy.deepcopy(original);legacy.pop('metadata_revalidation');empty=copy.deepcopy(legacy);empty['metadata_revalidation']=[]
checks['legacy_missing_journal_equals_empty']=same(legacy,empty)
checks['legacy_missing_journal_rejects_nonempty']=not same(legacy,fresh)
try:module.backing_comparison({'metadata_revalidation':{}})
except ValueError:checks['malformed_journal_rejected']=True
else:checks['malformed_journal_rejected']=False
assert all(checks.values()),checks
result={'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'report_sha256':hashlib.sha256((folder/'report.json').read_bytes()).hexdigest(),'fresh_recheck_sha256':hashlib.sha256((folder/'ancestor-recheck.json').read_bytes()).hexdigest(),'checks':checks,'original_journal':original['metadata_revalidation'],'fresh_journal':fresh['metadata_revalidation'],'scope':'Comparison only; no disk or historical report mutation. Only per-entry verified_time excluded; every other field remains exact.'}
(repo/'companion/evidence/retention-journal-time/result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(checks,indent=2))
