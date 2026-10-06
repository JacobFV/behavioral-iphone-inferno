"""Read-only actual-report verification plus deliberate in-memory corruptions."""
import importlib.util,json,pathlib
root=pathlib.Path(__file__).resolve().parents[2]
s=importlib.util.spec_from_file_location('verify',root/'verify-journey.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
reports=pathlib.Path('/home/brandonin/Documents/behavioral-iphone-inferno/.local-build/reports')
results=[]
for number in (38,55,41,44,47):
 a=m.Audit(reports/f'app-boot-{number}')
 try:r=a.verify();status='verified';reason=None
 except m.Invalid as e:status='rejected';reason=str(e)
 assert status==('verified' if number in (38,55) else 'rejected')
 results.append({'report':number,'status':status,'reason':reason,'sources':a.sources})
class Corrupt(m.Audit):
 def rows(self,name,structured=False):
  rows=super().rows(name,structured)
  if name=='serial.log':
   raw=[r for r in rows if r['value'].startswith('INFERNO_EVENT_RELAY_RAW') and r['value'].endswith(' main 0')]
   assert len(raw)==2
   if self.mode=='missing-raw': rows.remove(raw[1])
   elif self.mode=='wrong-pid':raw[1]['value']=raw[1]['value'].replace(' 492 ',' 493 ')
   elif self.mode=='duplicate-raw':rows.append(dict(raw[0]))
   elif self.mode=='duplicate-marker':
    x=next(r for r in rows if r['value']=='INFERNO_UIKIT_PROBE_V1 event=main count=0');y={'value':x['value'],'reference':dict(x['reference'])};y['reference']['byte_start']+=1;rows.append(y)
  elif name=='event-arrivals/observations.jsonl' and self.mode=='late-record-before-capture':
   matches=[r for r in rows if bytes.fromhex(r['value'].get('raw_hex','')).rstrip(b'\r')==b'INFERNO_UIKIT_PROBE_V1 event=main count=0'];assert len(matches)==2
   matches[1]['value']['observed_time']=matches[0]['value']['observed_time']
  return rows
for mode in ['missing-raw','wrong-pid','duplicate-raw','duplicate-marker','late-record-before-capture']:
 a=Corrupt(reports/'app-boot-38');a.mode=mode
 try:a.verify()
 except m.Invalid as e:results.append({'in_memory_corruption':mode,'status':'rejected','reason':str(e)})
 else:raise AssertionError(mode)
print(json.dumps({'scope':'No report mutation or guest action; actual raw files plus explicitly synthetic in-memory corruptions','results':results},indent=2))
