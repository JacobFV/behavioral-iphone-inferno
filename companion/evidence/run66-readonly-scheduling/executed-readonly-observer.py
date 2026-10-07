import pathlib,json,time,os,subprocess,hashlib
m=pathlib.Path('/home/brandonin/Documents/behavioral-iphone-inferno');p=m/'.local-build/reports/app-boot-66';out=p/'host-scheduling-readonly.json';assert not out.exists()
def snap():
 tasks={}
 for t in pathlib.Path('/proc/900988/task').iterdir():
  try:tasks[t.name]={'schedstat':list(map(int,(t/'schedstat').read_text().split())),'wchan':(t/'wchan').read_text().strip()}
  except FileNotFoundError:pass
 s=(p/'serial.log').read_bytes();log=(p/'guest-errors.log').read_bytes()
 return {'time':time.time(),'tasks':tasks,'cpu_pressure':pathlib.Path('/proc/pressure/cpu').read_text(),'loadavg':pathlib.Path('/proc/loadavg').read_text(),'serial_bytes':len(s),'serial_sha256':hashlib.sha256(s).hexdigest(),'gesture_lines':[x.decode(errors='replace') for x in s.splitlines() if b'b9a99f176513477d81ebab0025de31ba' in x],'cpu_PC_log_blocks':log.count(b' PC='),'cpu_window_journal_exists':(p/'swapwait-cpu-control.jsonl').exists()}
a=snap();time.sleep(10);b=snap();duration=b['time']-a['time'];deltas={}
for tid,x in b['tasks'].items():
 if tid in a['tasks']:
  prev=a['tasks'][tid]['schedstat'];cur=x['schedstat'];deltas[tid]={'runtime_seconds':(cur[0]-prev[0])/1e9,'runnable_wait_seconds':(cur[1]-prev[1])/1e9,'timeslices':cur[2]-prev[2]}
r={'scope':'Read-only /proc and existing logs; no guest/QMP/control actions','before':a,'after':b,'duration_seconds':duration,'thread_deltas':deltas,'cpu_affinity':sorted(os.sched_getaffinity(900988)),'cgroup':pathlib.Path('/proc/900988/cgroup').read_text(),'interpretation':'Runnable wait is host scheduler delay, not guest lock wait. It establishes contention during this interval, not sole cause of earlier startup delay.'};out.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({'duration':duration,'thread_deltas':deltas,'serial_growth':b['serial_bytes']-a['serial_bytes'],'cpu_blocks':b['cpu_PC_log_blocks']}))
