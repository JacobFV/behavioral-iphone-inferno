#!/usr/bin/env python3
"""Read-only failed-inspector audit; never export/reconstruct Apple config bytes."""
import hashlib,importlib.util,json,re
from pathlib import Path
R=Path('/home/brandonin/.local/share/inferno/app-import/runtime-inspection-stage-1')
S=Path('/tmp/inferno-runtime-inspector/companion/runtime-inspector/result.py')
def sha(raw):return hashlib.sha256(raw).hexdigest()
pins={}
def read(p):
 b=p.read_bytes();pins[str(p)]={'sha256':sha(b),'bytes':len(b)};return b
raw=read(R/'recovery-run/serial.log');rows=[];offset=0;malformed=[];nonexport=[]
for line in raw.splitlines(keepends=True):
 clean=line.rstrip(b'\r\n');i=clean.find(b'INFERNO_INSPECT_')
 if i>=0:
  value=clean[i:]
  if value.startswith(b'INFERNO_INSPECT_DATA '):
   if not re.fullmatch(rb'INFERNO_INSPECT_DATA name=launchd offset=[0-9]+ bytes=[0-9]+ hex=[0-9a-f]+',value):
    header=value.split(b'hex=',1)[0].decode('ascii');malformed.append({'byte_start':offset+i,'byte_end':offset+len(clean),'line_sha256':sha(value),'owned_header':header,'contains_asr_help_word':any(w in value for w in [b'--',b'asr',b'restore',b'source',b'target'])})
  else:nonexport.append({'byte_start':offset+i,'text':value.decode('ascii')})
 offset+=len(line)
assert len(malformed)==5
spec=importlib.util.spec_from_file_location('inspector',S);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
try:m.verify_content(raw)
except ValueError as e:rejection=str(e)
else:raise AssertionError('Contaminated raw accepted')
assert rejection=='Malformed export chunk'
f=json.loads(read(R/'failure.json'));report=json.loads(read(R/'recovery-run/report.json'))
assert f['status']=='failed-forensic-only' and f['cleanup']['remaining_session_members']==[]
assert report['attempt_completed'] is False and report['error']['detail']=='Signal 15' and report['exit_code']==0
q=[json.loads(x) for x in read(R/'recovery-run/qmp-transcript.jsonl').splitlines()];quit_rows=[]
for i,row in enumerate(q):
 value=json.loads(row['raw'])
 if value.get('execute')=='quit' or value.get('id')==7:quit_rows.append({'line':i+1,**row})
assert len(quit_rows)==2 and json.loads(quit_rows[-1]['raw']).get('return')=={}
ret=json.loads(read(R/'recovery-run/failed-stopped-disk-hashes.json'));verification=json.loads(read(R/'recovery-run/failed-stopped-disk-hashes-verification.json'))
assert len(ret)==7 and verification['failed_attempt_opt_in'] is True and verification['attempt_completed'] is False
files={}
for name,row in ret.items():
 st=Path(row['path']).lstat();assert st.st_size==row['bytes'];files[name]={'path':row['path'],'size':st.st_size,'mode':oct(st.st_mode),'device':st.st_dev,'inode':st.st_ino,'recorded_sha256_not_rehashed':row['sha256']}
for pid in (1032152,1042481,1048889):
 assert not (Path('/proc')/str(pid)).exists()
assert not (R/'runtime-inspection.json').exists() and not (R/'launchd.plist').exists() and (R/'INCOMPLETE.json').exists()
for p,pin in pins.items():assert sha(Path(p).read_bytes())==pin['sha256']
result={'scope':'Independent failed export framing/parser/cleanup and seven-file metadata audit; no image rehash, Apple configuration reconstruction, or successful inspection claim','inputs':pins,'parser_source':{'path':str(S),'sha256':sha(S.read_bytes())},'malformed_chunks':malformed,'nonexport_markers':nonexport,'actual_parser_rejection':rejection,'quit_ack':quit_rows,'report_outcome':{'attempt_completed':False,'error':report['error'],'emulator_exit_code':report['exit_code']},'seven_file_metadata':files,'pids_absent':[1032152,1042481,1048889],'limits':['Guest hash and unmount records exist, but five malformed export records prevent reconstruction.','Coordinator signal cleanup and QMP quit0 are not a normal successful inspection finish.','Forensic retention hashes are referenced; this independent audit did not reread disk payloads.','No eligible manifest or exported launchd file exists.']}
Path(__file__).with_name('audit.json').write_text(json.dumps(result,indent=2)+'\n')
print('PASS: failure preserved, malformed export rejected, metadata and cleanup corroborated')
