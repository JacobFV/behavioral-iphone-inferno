#!/usr/bin/env python3
"""Explicitly synthetic, firmware-free sample parser checks; no guest execution."""
import hashlib, importlib.util, json, pathlib, subprocess, tempfile
root=pathlib.Path(__file__).resolve().parents[3];tool=root/'companion/sample-result.py';spec=importlib.util.spec_from_file_location('sample_result',tool);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
rid='a'*32;boot='024BD83E-EB10-4666-9C04-687E7C21E9DC';request={'request_id':rid,'boot_uuid':boot,'target':'SPRINGBOARD'}
lines=[f'INFERNO_SAMPLE_REQUEST request_id={rid} boot={boot} target=SPRINGBOARD pid=123 resolve_errno=0 guest_ticks=100',f'INFERNO_SAMPLE_BEGIN request_id={rid} target=SPRINGBOARD pid=123 uid=501 unique=456 idversion=7 output_cap=262144 guest_deadline_seconds=60 original_tool=/usr/sbin/spindump target_signals=0',f'INFERNO_SAMPLE_DATA request_id={rid} offset=0 bytes=5 hex=746573740a',f'INFERNO_SAMPLE_END request_id={rid} boot={boot} target=SPRINGBOARD pid=123 unique=456 idversion=7 bytes=5 chunks=1 eof=1 truncated=0 read_errno=0 output_error=0 reaped=1 raw_status=0 wait_errno=0 killed=0 target_post_match=1 complete=1 guest_ticks=200 pid_reuse_atomicity=unproven']
good=('\r\r\n'.join(lines)+'\r\r\n').encode();cases={'complete-synthetic':good,'missing-end':('\n'.join(lines[:-1])+'\n').encode(),'duplicate-data':good.replace((lines[2]+'\r\r\n').encode(),((lines[2]+'\r\r\n')*2).encode()),'gap':good.replace(b'offset=0',b'offset=1'),'wrong-length':good.replace(b'bytes=5 hex=',b'bytes=6 hex='),'mixed-target':good.replace(b'BEGIN request_id='+rid.encode()+b' target=SPRINGBOARD',b'BEGIN request_id='+rid.encode()+b' target=BACKBOARDD'),'failed-flags':good.replace(b'raw_status=0',b'raw_status=256'),'unterminated-end':good[:-1],'wrong-total':good.replace(b'bytes=5 chunks=1',b'bytes=6 chunks=1')}
cases['child-stop-after-data']=good.replace((lines[3]+'\r\r\n').encode(),f'INFERNO_SAMPLE_CHILD_STOP request_id={rid} reason=guest_deadline child=999 result=0 errno=0 guest_ticks=180\n'.encode())
cases['bad-chunk-no-later-recovery']=good.replace((lines[3]+'\r\r\n').encode(),(f'INFERNO_SAMPLE_DATA request_id={rid} offset=99 bytes=1 hex=61\n'+f'INFERNO_SAMPLE_DATA request_id={rid} offset=5 bytes=1 hex=62\n'+lines[3]+'\n').encode())
checks=[]
for name,data in cases.items():
 result,decoded=m.reconstruct(data,request);assert result['transport_complete']==(name=='complete-synthetic');assert result['output_usefulness']=='not_assessed'
 for record in result['records']:
  ref=record['reference'];assert hashlib.sha256(data[ref['byte_start']:ref['byte_end']]).hexdigest()==ref['sha256']
 if name in ('complete-synthetic','missing-end','unterminated-end','child-stop-after-data','bad-chunk-no-later-recovery'):assert decoded==b'test\n'
 checks.append({'name':name,'input_sha256':hashlib.sha256(data).hexdigest(),'transport_complete':result['transport_complete'],'reason':result.get('incomplete_reason'),'decoded_bytes':len(decoded)})
try:m.check_destination(root/'companion/forbidden-stack-output');raise AssertionError('nonignored Git output accepted')
except ValueError as exc:checks.append({'name':'nonignored-Git-output-rejected','reason':str(exc)})
with tempfile.TemporaryDirectory(prefix='inferno-sample-parser-') as tmp:
 p=pathlib.Path(tmp);(p/'serial.log').write_bytes(good);(p/'request.json').write_text(json.dumps(request));cmd=[str(root/'companion/run'),'sample-result','--serial',str(p/'serial.log'),'--request',str(p/'request.json'),'--output',str(p/'result')];run=subprocess.run(cmd,capture_output=True,text=True);assert run.returncode==0,(run.stdout,run.stderr);assert(p/'result/output.bin').read_bytes()==b'test\n';again=subprocess.run(cmd,capture_output=True,text=True);assert again.returncode==2
 checks.append({'name':'actual-host-CLI-on-explicitly-synthetic-records','exit_code':run.returncode,'stdout':run.stdout,'existing_output_exit':again.returncode})
pathlib.Path(__file__).with_name('execution.json').write_text(json.dumps({'scope':'Host-only synthetic records; no original tool output, guest sample, VM input or launch.','guest_contract_revision':'d2ac5ba0cc','source_sha256':hashlib.sha256(tool.read_bytes()).hexdigest(),'checks':checks},indent=2)+'\n')
