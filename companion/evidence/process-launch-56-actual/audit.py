"""Independent raw-line, snapshot and integer-clock audit; no guest actions."""
import json,pathlib,re,hashlib,shutil
from fractions import Fraction
src=pathlib.Path('/home/brandonin/Documents/behavioral-iphone-inferno/.local-build/reports/app-boot-56');out=pathlib.Path(__file__).parent
sha=lambda x:hashlib.sha256(x).hexdigest()
files=['serial.log','control-transcript.jsonl','serial-input-transcript.jsonl','process-absence-600.json','process-absence-600.serial-prefix.log','process-absence-600.control-prefix.jsonl','strict-completed-prefix.json','strict-completed.serial-prefix.log','report.json','new-process-timing.json','new-process-view/report.json']
manifest={}
for name in files:
 data=(src/name).read_bytes(); target=out/('retained-'+name.replace('/','-'));target.write_bytes(data);manifest[name]={'path':str(src/name),'bytes':len(data),'sha256':sha(data),'retained':target.name}
data=(src/'serial.log').read_bytes();lines=[];offset=0
for raw in data.splitlines(keepends=True):
 text=raw.rstrip(b'\r\n').decode();lines.append((text,{'byte_start':offset,'byte_end':offset+len(raw),'sha256':sha(raw),'text':text}));offset+=len(raw)
def one(pattern):
 matches=[(re.fullmatch(pattern,t),ref) for t,ref in lines if re.fullmatch(pattern,t)];assert len(matches)==1,(pattern,len(matches));return matches[0]
boot='02034EC7-A855-43F7-927E-070ECEBC70B4';rid='7f06261169f8480896cf96522609f600'
open_match,open_ref=one(r'INFERNO_OPEN_TIMING_V1 request_id='+rid+r' boot='+boot+r' pid=\d+ request_ticks=(\d+) callback_ticks=(\d+) numer=(\d+) denom=(\d+) accepted=1')
request,callback,numer,denom=map(int,open_match.groups())
hooks={}
for t,ref in lines:
 m=re.fullmatch(r'INFERNO_TIMING_RELAY_RAW source=guest-loopback record=INFERNO_TIMING_V1 '+boot+r' 375 (\d+) (\S+) (\d+) (\d+) (\d+)',t)
 if m:
  seq,hook,tick,n,d=m.groups();assert (int(n),int(d))==(numer,denom);assert hook not in hooks;hooks[hook]={'sequence':int(seq),'ticks':int(tick),'reference':ref}
assert set(hooks)=={'main','launch-delegate','window-request','appeared','active'}
assert sorted(x['sequence'] for x in hooks.values())==[1,2,3,4,5]
ordered=sorted(hooks.values(),key=lambda x:x['sequence']);assert [x['ticks'] for x in ordered]==sorted(x['ticks'] for x in ordered)
identities={}
for pid in [261,375]:
 m,ref=one(r'INFERNO_EVENT_PROCESS_IDENTITY pid='+str(pid)+r' query_result=56 errno=0 uniqueid=(\d+) idversion=(\d+) source=original-libproc fallback=main-tick-and-pid');identities[pid]={'uniqueid':int(m[1]),'idversion':int(m[2]),'reference':ref}
assert identities[261]['uniqueid']!=identities[375]['uniqueid']
prefix=(src/'process-absence-600.serial-prefix.log').read_bytes();assert data.startswith(prefix)
text=prefix.decode();begin=text.index('INFERNO_READINESS_BEGIN seconds=600');end=text.index('INFERNO_READINESS_END seconds=600 status=0 ps_watchdog=600 timed_out=0',begin)
block=text[begin:end];table=block[block.index('PID  PPID   UID STAT COMM'):].splitlines()[1:];rows=[]
for line in table:
 if not line.strip():continue
 m=re.fullmatch(r'\s*(\d+)\s+(\d+)\s+(\d+)\s+(\S+)\s+(.+)',line.strip());assert m,line;rows.append(m.groups())
assert len(rows)==174 and len({r[0] for r in rows})==174
assert not any(r[0]=='261' or r[4]=='/Applications/InfernoProbe.app/InfernoProbe' for r in rows)
absence=json.loads((src/'process-absence-600.json').read_bytes());controls=[json.loads(x) for x in (src/'control-transcript.jsonl').read_text().splitlines()];named=[r for r in controls if json.loads(r['raw']).get('arguments',{}).get('request_id')==rid];assert len(named)==1
assert absence['captured_host_epoch']<json.loads(named[0]['raw'])['created']<=named[0]['time']
intervals={}
for name,a,b in [('open_to_main',request,hooks['main']['ticks']),('main_to_active',hooks['main']['ticks'],hooks['active']['ticks']),('main_to_appeared',hooks['main']['ticks'],hooks['appeared']['ticks']),('open_to_active',request,hooks['active']['ticks']),('open_to_callback',request,callback)]:
 value=Fraction((b-a)*numer,denom);assert value>=0;intervals[name]={'delta_ticks':b-a,'ns_numerator':value.numerator,'ns_denominator':value.denominator,'milliseconds':float(value/1000000)}
result={'scope':'Independent actual raw clock/incarnation/complete ps parsing, not parser assertions alone','source_files':manifest,'boot_uuid':boot,'old_pid':261,'new_pid':375,'identities':identities,'absence_clean_rows':len(rows),'absence_captured_time':absence['captured_host_epoch'],'open_created_time':json.loads(named[0]['raw'])['created'],'open_control_time':named[0]['time'],'open_reference':open_ref,'hooks':hooks,'timebase':{'numer':numer,'denom':denom},'intervals':intervals,'limits':['Single ps snapshot, not continuous absence or proof of termination cause.','Fresh process, not cleared cache or cold device.','Guest lifecycle ticks are not frame presentation timestamps.','Root separately reviewed new-process-view/observed-0010.png counter0; no second tap.','Strict prefix is an independent actual host checkpoint, not per-marker arrival observation.']}
(out/'audit.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(intervals))
