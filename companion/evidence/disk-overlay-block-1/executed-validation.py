from pathlib import Path
import sys,json,subprocess,socket,time,os
sys.path.insert(0,'/tmp/inferno-disk-overlay/companion')
from disk_overlay import *
from boot import QMP
out=Path('/home/brandonin/.local/share/inferno/disk-overlay-validation/run-1');out.mkdir(exist_ok=False)
base=out/'synthetic-base.raw'
with base.open('xb') as f:
 f.truncate(16<<20);f.seek(131072);f.write(bytes([0x11])*4096)
hash_before=digest(base)
try:validate_base(base,hash_before);raise AssertionError('accepted writable base')
except ValueError:pass
base.chmod(0o444)
tool=validate_tools(DEFAULT_TOOLS)
record=create_overlay(out/'root.qcow2',base,hash_before,tool)
binary=Path('/home/brandonin/Documents/behavioral-iphone-inferno/.local-build/build/qemu-system-aarch64')
command=[str(binary),'-machine','none','-accel','tcg','-S','-display','none','-monitor','none','-serial','none','-qmp','unix:'+str(out/'qmp.sock')+',server=on,wait=off','-drive','file='+str(out/'root.qcow2')+',format=qcow2,if=none,id=root']
(out/'command.json').write_text(json.dumps(command,indent=2)+'\n')
stdout=(out/'stdout.log').open('w');stderr=(out/'stderr.log').open('w');p=subprocess.Popen(command,stdout=stdout,stderr=stderr)
s=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM)
for _ in range(100):
 if p.poll() is not None:raise RuntimeError('QEMU exited: '+(out/'stderr.log').read_text())
 try:s.connect(str(out/'qmp.sock'));break
 except (FileNotFoundError,ConnectionRefusedError):time.sleep(.05)
s.settimeout(5);q=QMP(s,out);greeting=q.receive();q.execute('qmp_capabilities')
results=[]
for action in ['read -P 0x11 131072 4096','write -P 0xa5 65536 4096','flush','read -P 0xa5 65536 4096','read -P 0x11 131072 4096']:
 r=q.execute('human-monitor-command',{'command-line':'qemu-io root "'+action+'"'})
 assert 'return' in r and 'error' not in r;results.append({'command':action,'response':r})
q.execute('quit');p.wait(timeout=10);q.close();s.close();stdout.close();stderr.close();assert p.returncode==0
record['backing_after_stop']=verify_backing(record)
# Independent original qemu-io verifies persisted overlay bytes and unchanged base.
env=os.environ.copy();env['LD_LIBRARY_PATH']=str(DEFAULT_TOOLS/'root/usr/lib/aarch64-linux-gnu')
io=DEFAULT_TOOLS/'root/usr/bin/qemu-io'
checks=[]
for path,fmt,cmds in [(out/'root.qcow2','qcow2',['read -P 0xa5 65536 4096','read -P 0x11 131072 4096']),(base,'raw',['read -P 0 65536 4096','read -P 0x11 131072 4096'])]:
 args=[str(io),'-r','-f',fmt]
 for cmd in cmds:args+=['-c',cmd]
 args += [str(path)]
 r=subprocess.run(args,capture_output=True,text=True,env=env);assert r.returncode==0 and 'Pattern verification failed' not in r.stdout+r.stderr
 checks.append({'command':args,'exit_code':r.returncode,'stdout':r.stdout,'stderr':r.stderr})
record.update(kind='firmware_free_qemu_overlay_block_execution',ios_booted=False,app_executed=False,binary=str(binary),binary_sha256=digest(binary),qmp_results=results,persisted_read_checks=checks,qemu_exit_code=p.returncode,base_sha256_before=hash_before,base_sha256_after=digest(base),overlay_allocated_bytes=(out/'root.qcow2').stat().st_blocks*512,overlay_check=json.loads(tool_run(tool,'check','--output=json',out/'root.qcow2')))
assert record['base_sha256_after']==hash_before
(out/'report.json').write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps({'passed':True,'report':str(out/'report.json'),'base_unchanged':True,'overlay_allocated_bytes':record['overlay_allocated_bytes']}))
