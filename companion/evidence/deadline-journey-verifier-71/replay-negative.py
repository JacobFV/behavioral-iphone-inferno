#!/usr/bin/env python3
"""Synthetic parsed-copy negatives; original run71 files are never modified."""
import argparse,hashlib,importlib.util,json
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--report',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
source=Path(__file__).resolve().parents[2]/'verify-journey.py';sp=importlib.util.spec_from_file_location('v',source);v=importlib.util.module_from_spec(sp);sp.loader.exec_module(v)
rid='c4acb1b93ba848bb8750608bd9ce6a1c';results=[]
for case in ['expired-write','partial','error','missing-clock','mismatched-deadline','wrong-id','wrong-overrun-flag']:
 class Negative(v.Audit):
  def rows(self,name,*args):
   rows=super().rows(name,*args)
   if name=='serial-input-transcript.jsonl':
    r=next(x['value']['response'] for x in rows if x['value'].get('stage')=='after-send' and x['value'].get('response',{}).get('request_id')==rid)
    if case=='expired-write':r['write_begin_monotonic']=r['send_deadline_monotonic'];r['write_end_monotonic']=r['send_deadline_monotonic']
    elif case=='partial':r['bytes_sent']-=1
    elif case=='error':r['error']='synthetic send failure'
    elif case=='missing-clock':del r['write_begin_monotonic']
    elif case=='mismatched-deadline':r['send_deadline_monotonic']+=1
    elif case=='wrong-id':r['request_id']='0'*32
    else:r['write_end_after_deadline']=True
   return rows
 try:Negative(a.report).verify()
 except v.Invalid as e:results.append({'case':case,'status':'rejected','reason':str(e)})
 else:raise AssertionError(case)
with a.output.open('x') as f:json.dump({'scope':'Synthetic in-memory mutations only; no original evidence edits or VM execution','verifier_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'harness_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'results':results},f,indent=2);f.write('\n')
print(json.dumps(results))
