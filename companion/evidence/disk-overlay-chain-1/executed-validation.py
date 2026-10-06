from pathlib import Path
import argparse,sys,json,subprocess,socket,time,os,hashlib
p=argparse.ArgumentParser();p.add_argument('--companion-dir',type=Path,required=True);p.add_argument('--binary',type=Path,required=True);p.add_argument('--output',type=Path,required=True);args=p.parse_args()
sys.path.insert(0,str(args.companion_dir));from disk_overlay import *
from boot import QMP
out=args.output.resolve();out.mkdir(exist_ok=False);tool=validate_tools(DEFAULT_TOOLS)
base_dir=out/'raw/disks';base_dir.mkdir(parents=True);base=base_dir/'root.raw'
with base.open('xb') as f:f.truncate(16<<20);f.seek(196608);f.write(bytes([0x11])*4096)
base.chmod(0o444);base_hash=digest(base)
def execute(directory,record,operations):
 path=Path(record['path']);command=[str(args.binary),'-machine','none','-accel','tcg','-S','-display','none','-monitor','none','-serial','none','-qmp','unix:'+str(directory/'qmp.sock')+',server=on,wait=off','-drive','file='+str(path)+',format=qcow2,if=none,id=root']
 (directory/'command.json').write_text(json.dumps(command,indent=2)+'\n');stdout=(directory/'stdout.log').open('w');stderr=(directory/'stderr.log').open('w');proc=subprocess.Popen(command,stdout=stdout,stderr=stderr)
 conn=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM)
 for _ in range(100):
  if proc.poll() is not None:raise RuntimeError((directory/'stderr.log').read_text())
  try:conn.connect(str(directory/'qmp.sock'));break
  except (FileNotFoundError,ConnectionRefusedError):time.sleep(.05)
 conn.settimeout(5);q=QMP(conn,directory);q.receive();q.execute('qmp_capabilities')
 for op in operations:
  result=q.execute('human-monitor-command',{'command-line':'qemu-io root "'+op+'"'});assert 'return'in result
 quit_response=q.execute('quit');proc.wait(timeout=10);q.close();conn.close();stdout.close();stderr.close();assert proc.returncode==0
 assert 'Pattern verification failed' not in (directory/'stdout.log').read_text()+(directory/'stderr.log').read_text()
 record['backing_after_stop']=verify_backing(record)
 report={'kind':'firmware_free_qemu_overlay_block_execution','exit_code':proc.returncode,'quit_response':quit_response,'root_overlay':record,'binary':str(args.binary),'binary_sha256':digest(args.binary),'ios_booted':False,'app_executed':False}
 (directory/'root-overlay.json').write_text(json.dumps(record,indent=2)+'\n');(directory/'report.json').write_text(json.dumps(report,indent=2)+'\n')
 path.chmod(0o444)
 manifest={}
 for image in (directory/'disks').iterdir():
  if image.suffix not in ('.raw','.qcow2'):continue
  manifest[image.name]={'path':str(image),'bytes':image.stat().st_size,'sha256':digest(image)}
 (directory/'stopped-disk-hashes.json').write_text(json.dumps(manifest,indent=2)+'\n')
 return report
one=out/'one';(one/'disks').mkdir(parents=True)
for name,size in AUXILIARY_SIZES.items():
 with (one/'disks'/name).open('xb') as f:f.truncate(size)
r1=create_overlay(one/'disks/root.qcow2',base,base_hash,tool)
execute(one,r1,['write -P 0xa5 65536 4096','write -P 0xa5 131072 4096','flush','read -P 0xa5 65536 4096','read -P 0x11 196608 4096'])
layer1_hash=digest(one/'disks/root.qcow2')
chain=load_stopped_overlay(one/'report.json',tool)
two=out/'two';(two/'disks').mkdir(parents=True)
for name in AUXILIARY_SIZES:
 subprocess.run(['cp','--sparse=always','--',str(one/'disks'/name),str(two/'disks'/name)],check=True)
r2=create_recorded_overlay(two/'disks/root.qcow2',one/'report.json',tool)
execute(two,r2,['read -P 0xa5 65536 4096','write -P 0xb6 65536 4096','flush','read -P 0xb6 65536 4096','read -P 0xa5 131072 4096','read -P 0x11 196608 4096'])
assert digest(base)==base_hash and digest(one/'disks/root.qcow2')==layer1_hash
# Exercise the next-stage reader recursively, proving this stopped second layer is usable.
loaded=load_stopped_overlay(two/'report.json',tool);assert len(loaded['layers'])==3
checks=[];env=os.environ.copy();env['LD_LIBRARY_PATH']=str(DEFAULT_TOOLS/'root/usr/lib/aarch64-linux-gnu');io=DEFAULT_TOOLS/'root/usr/bin/qemu-io'
for image,fmt,commands in [(two/'disks/root.qcow2','qcow2',['read -P 0xb6 65536 4096','read -P 0xa5 131072 4096','read -P 0x11 196608 4096']),(one/'disks/root.qcow2','qcow2',['read -P 0xa5 65536 4096']),(base,'raw',['read -P 0 65536 4096','read -P 0x11 196608 4096'])]:
 cmd=[str(io),'-r','-f',fmt]
 for c in commands:cmd+=['-c',c]
 cmd+=[str(image)];r=subprocess.run(cmd,capture_output=True,text=True,env=env);assert r.returncode==0 and 'Pattern verification failed'not in r.stdout+r.stderr
 checks.append({'command':cmd,'stdout':r.stdout,'stderr':r.stderr,'exit_code':r.returncode})
rejects={}
for name,action in [('wrong-base-hash',lambda:validate_base(base,'0'*64)),('report-cycle',lambda:load_stopped_overlay(one/'report.json',tool,(str(one/'report.json'),))),('depth-limit',lambda:load_stopped_overlay(one/'report.json',tool,('a','b','c','d')))]:
 try:action();raise AssertionError('guard accepted '+name)
 except ValueError as e:rejects[name]=str(e)
fixture=out/'writable-handle-fixture.raw';fixture.write_bytes(b'owned synthetic fixture');writer=os.open(fixture,os.O_RDWR);fixture.chmod(0o444)
try:
 try:validate_base(fixture,digest(fixture));raise AssertionError('accepted preexisting writer')
 except ValueError as e:rejects['preexisting-writable-fd']=str(e)
finally:os.close(writer)
bad=out/'missing-quit';bad.mkdir();(bad/'report.json').write_text(json.dumps({'kind':'firmware_free_qemu_overlay_block_execution','exit_code':0}))
try:load_stopped_overlay(bad/'report.json',tool);raise AssertionError('accepted missing quit')
except ValueError as e:rejects['missing-quit-ack']=str(e)
summary={'kind':'actual_firmware_free_two_overlay_chain_execution','ios_booted':False,'source_sha256':digest(args.companion_dir/'disk_overlay.py'),'binary_sha256':digest(args.binary),'base_before_after_sha256':base_hash,'layer1_before_after_sha256':layer1_hash,'independent_reads':checks,'rejection_checks':rejects,'two_stopped_chain_layers':loaded['layers'],'qcow_checks':[json.loads(tool_run(tool,'check','--output=json',str(d/'disks/root.qcow2'))) for d in (one,two)],'overlay_allocated_bytes':[(d/'disks/root.qcow2').stat().st_blocks*512 for d in (one,two)]}
(out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps({'passed':True,'summary':str(out/'summary.json')}))
