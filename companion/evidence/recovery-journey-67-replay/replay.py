#!/usr/bin/env python3
"""Read-only real-report replays and explicitly synthetic association negatives."""
import argparse, copy, hashlib, importlib.util, json
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--reports',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
source=Path(__file__).resolve().parents[2]/'verify-journey.py'
spec=importlib.util.spec_from_file_location('verifier',source);v=importlib.util.module_from_spec(spec);spec.loader.exec_module(v)
rid='f657a4fdfee94393a5dd721690eadf30'
results=[]
for run,recovery,expected in [(67,rid,'verified-recovered-journey'),(67,None,'rejected'),(66,None,'verified'),(64,None,'rejected'),(65,rid,'rejected'),(59,None,'verified')]:
    audit=v.Audit(a.reports/f'app-boot-{run}',recovery_open_request=recovery)
    try: result=audit.verify()
    except v.Invalid as e: result={'status':'rejected','reason':str(e)}
    assert result['status']==expected,(run,result)
    results.append({'kind':'actual unchanged report','run':run,'recovery_open_request':recovery,'result':result,'sources':audit.sources})
# Mutate parsed rows only; original files, hashes and historical verifier outputs remain untouched.
for case in ['wrong-wire','wrong-launcher','missing-identity','duplicate-open','prior-appeared','missing-validation','main-before-open','prior-main-after-open','permuted-hooks']:
    class Negative(v.Audit):
        def recovery_selection(self,serial,controls,inputs,candidates,*times):
            serial,controls,inputs,candidates=copy.deepcopy((serial,controls,inputs,candidates))
            if case=='wrong-wire':
                next(r for r in inputs if r['value'].get('request_id')==rid)['value']['raw']='WRONG\n'
            elif case=='wrong-launcher':
                r=next(r for r in serial if r['value'].startswith(f'INFERNO_OPEN_DISPATCHED request_id={rid} '));r['value']=r['value'].replace('child=358','child=360')
            elif case=='missing-identity':
                serial[:]=[r for r in serial if not r['value'].startswith('INFERNO_EVENT_PROCESS_IDENTITY pid=360 ')]
            elif case=='duplicate-open':
                r=copy.deepcopy(next(r for r in serial if r['value'].startswith(f'INFERNO_OPEN_REQUEST request_id={rid} ')));r['value']+=' malformed';serial.append(r)
            elif case=='prior-appeared':
                r=next(r for r in serial if r['value'].startswith('INFERNO_EVENT_RELAY_RAW') and ' 269 1 main 0' in r['value']);r['value']=r['value'].replace('main 0','appeared 0')
            elif case=='missing-validation':
                serial[:]=[r for r in serial if not r['value'].startswith('INFERNO_EVENT_RELAY_RECORD boot=71B7D4EA-E386-402C-9267-FA4A3C458130 pid=360 sequence=2 ')]
            elif case=='prior-main-after-open':
                boundary=next(r for r in serial if r['value'].startswith(f'INFERNO_OPEN_REQUEST request_id={rid} '))['reference']['byte_end']
                c=next(c for c in candidates if c['pid']==269)
                c['marker']['reference']['byte_end']=boundary+1
            elif case=='permuted-hooks':
                for r in serial:
                    if r['value'].startswith(('INFERNO_TIMING_RELAY_RAW','INFERNO_TIMING_RELAY_RECORD')) and (' 360 ' in r['value'] or 'pid=360 ' in r['value']):
                        r['value']=r['value'].replace('launch-delegate','TEMP').replace('window-request','launch-delegate').replace('TEMP','window-request')
            else:
                for r in serial:
                    if r['value'].startswith(f'INFERNO_OPEN_TIMING_V1 request_id={rid} '):r['value']=r['value'].replace('request_ticks=19138500624','request_ticks=19200000000')
            return super().recovery_selection(serial,controls,inputs,candidates,*times)
    try: Negative(a.reports/'app-boot-67',recovery_open_request=rid).verify()
    except v.Invalid as e: results.append({'kind':'synthetic in-memory association mutation','case':case,'status':'rejected','reason':str(e)})
    else: raise AssertionError(f'negative accepted: {case}')
out={'verifier_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'replay_source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'results':results}
with a.output.open('x') as f:json.dump(out,f,indent=2);f.write('\n')
print(json.dumps({'actual_replays':6,'synthetic_rejections':9,'output':str(a.output)}))
