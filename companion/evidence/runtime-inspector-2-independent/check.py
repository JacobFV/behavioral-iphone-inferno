#!/usr/bin/env python3
"""Independent stopped inspector metadata/raw audit, no disk payload rehash."""
import argparse,hashlib,importlib.util,json,stat
from pathlib import Path

def main():
 p=argparse.ArgumentParser();p.add_argument('--result',type=Path,required=True);p.add_argument('--sha256',required=True);p.add_argument('--parser',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();pins={}
 def sha(raw):return hashlib.sha256(raw).hexdigest()
 def read(path):
  path=Path(path);s=path.stat();assert s.st_size<=64<<20
  b=path.read_bytes();assert path.stat().st_mtime_ns==s.st_mtime_ns and len(b)==s.st_size
  pins[str(path)]={'sha256':sha(b),'bytes':len(b)};return b
 raw=read(a.result);assert sha(raw)==a.sha256;r=json.loads(raw)
 assert r['schema']=='inferno.runtime-inspection.v1' and r['status']=='observed-not-runtime-ready'
 assert r['backing_depth']==4 and r['ipa_runtime_ready'] is False and r['runtime_base_eligible'] is False
 assert not any((a.result.parent/n).exists() for n in ['INCOMPLETE.json','failure.json'])
 for path,h in {**r['source_sha256'],**r['stopped_evidence_sha256']}.items():assert sha(read(path))==h
 report_raw=read(r['report']);assert sha(report_raw)==r['report_sha256'];report=json.loads(report_raw);rd=Path(r['report']).parent
 assert report['attempt_completed'] is True and report['exit_code']==0 and not report.get('error')
 serial=read(rd/'serial.log');spec=importlib.util.spec_from_file_location('inspect_result',a.parser);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
 content,exported=m.verify_content(serial);assert content==r['content'];assert exported==read(r['launchd_export']['path']);assert sha(exported)==r['launchd_export']['sha256']
 checkpoint_path=a.result.parent/'content-check.json';assert sha(read(checkpoint_path))==r['content_checkpoint_sha256']
 checkpoint=json.loads(read(checkpoint_path));assert sha(serial[:checkpoint['serial_bytes']])==checkpoint['serial_sha256']
 controls=[json.loads(x) for x in read(rd/'control-transcript.jsonl').splitlines()]
 assert len(controls)==1 and json.loads(controls[0]['raw'])['execute']=='finish-observation' and controls[0]['response']['return']['finish_requested'] is True
 assert checkpoint['captured_time']<json.loads(controls[0]['raw'])['created']<=controls[0]['time']
 retention_raw=read(r['retention']);assert sha(retention_raw)==r['retention_sha256'];ret=json.loads(retention_raw);assert len(ret)==7
 files={}
 for name,value in ret.items():
  s=Path(value['path']).lstat();assert stat.S_ISREG(s.st_mode) and s.st_size==value['bytes'] and stat.S_IMODE(s.st_mode)==0o444
  files[name]={'path':value['path'],'bytes':s.st_size,'mode':oct(s.st_mode),'device':s.st_dev,'inode':s.st_ino,'recorded_sha256_not_rehashed':value['sha256']}
 q=[json.loads(x) for x in read(rd/'qmp-transcript.jsonl').splitlines()];quits=[]
 for index,row in enumerate(q):
  value=json.loads(row['raw'])
  if row['direction']=='send' and value.get('execute')=='quit':quits.append((index,row,value))
 assert len(quits)==1
 qi,qr,qv=quits[0];assert controls[0]['time']<qr['time'];acks=[row for row in q[qi+1:] if row['direction']=='receive' and json.loads(row['raw']).get('id')==qv['id'] and json.loads(row['raw']).get('return')=={}];assert len(acks)==1
 for path,value in pins.items():assert sha(Path(path).read_bytes())==value['sha256']
 # Exported original configuration and hex-bearing serial deliberately stay external.
 result={'scope':'Independent stopped raw inspector parser, source/metadata and retained-file metadata; no whole-image hash repeated','result':{'path':str(a.result),'sha256':a.sha256},'inputs':pins,'parser':{'path':str(a.parser),'sha256':sha(a.parser.read_bytes())},'raw_content':{**{k:v for k,v in content.items() if k!='records'},'record_count':len(content['records']),'nonexport_records':[row for row in content['records'] if 'text' in row]},'quit':{'request':qr,'ack':acks[0]},'checkpoint_before_sole_finish':{'captured_time':checkpoint['captured_time'],'serial_bytes':checkpoint['serial_bytes'],'serial_sha256':checkpoint['serial_sha256'],'control':controls[0]},'seven_file_metadata':files,'predecessor':r['predecessor'],'limits':['Read-only launchd bytes exported and full dyld digest observed; no .sig identity observation.','Inspector depth4 child is not a runtime base; no renderer patch, install, migration or app execution.','Retained disk hashes are referenced; payloads not independently rehashed.']}
 a.output.write_text(json.dumps(result,indent=2)+'\n');print('PASS independent inspector metadata/raw audit')
if __name__=='__main__':main()
