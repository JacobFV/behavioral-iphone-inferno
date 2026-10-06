#!/usr/bin/env python3
"""Read retained final serial logs; emit exact offset/hash-backed narrow selections."""
import pathlib,re,json,hashlib,base64,collections
root=pathlib.Path('/home/brandonin/Documents/behavioral-iphone-inferno/.local-build/reports');out=pathlib.Path(__file__).parent
runs=[44,47,45,46,49,50]
gfx=re.compile(rb'(?i)(iomfb|render|display|compositor|fence|windowserver|backboard|quartz)')
warning=re.compile(rb'(?i)(\berror\b|\bfail(?:ed|ure)?\b|\btimeout\b|\bstall(?:ed)?\b|\binvalid\b|\bpanic\b|could not|couldn.t|missing|not found|not supported)')
proc=re.compile(rb'^\s*\d+\s+\d+\s+\d+\s+\S+\s+')
shared=[b'fixed refresh rate only supported on APT devices',b'disable BIC (config init failed)',b'failed to read color accuracy index',b'failed with 0xe00002bc (function-temperature_update)',b'failed with 0xe00002bc (function-link_enable)']
results=[]
for n in runs:
 path=root/f'app-boot-{n}'/'serial.log';data=path.read_bytes();lines=data.splitlines(keepends=False) # overridden below: LF only retains original CR
 rawlines=data.split(b'\n');rows=[];offset=0
 for i,line in enumerate(rawlines):
  raw=line+(b'\n'if i<len(rawlines)-1 else b'');rows.append((i+1,offset,raw));offset+=len(raw)
 tap=next(i for i,r in enumerate(rows)if b'INFERNO_UIKIT_PROBE_V1 event=tap count=1'in r[2]);selected={};warns=[];near=[];postgfx=[];ps=[]
 def keep(i,why):selected.setdefault(i,[]).append(why)
 for i,(line,off,raw)in enumerate(rows):
  if i==tap:keep(i,'actual_tap1_marker')
  eligible=len(raw)<=4096 and not raw.startswith(b'INFERNO_')and not proc.match(raw)and not raw.lstrip().startswith((b'{',b'0x'))
  if eligible and gfx.search(raw)and warning.search(raw):warns.append(i);keep(i,'graphics_warning')
  if eligible and gfx.search(raw)and i>=tap:postgfx.append(i);keep(i,'post_tap_graphics_text')
  if eligible and warning.search(raw)and max(0,tap-80)<=i<tap+150:near.append(i);keep(i,'near_tap_warning')
  if i>=tap and proc.match(raw)and (b'/usr/libexec/backboardd'in raw or b'/System/Library/CoreServices/SpringBoard.app/SpringBoard'in raw):ps.append(i);keep(i,'post_tap_original_service_ps')
 for i in range(max(0,tap-8),min(len(rows),tap+9)):keep(i,'tap_line_context')
 excerpts=[]
 for i,why in sorted(selected.items()):
  line,off,raw=rows[i];excerpts.append({'line':line,'byte_start':off,'byte_end':off+len(raw),'sha256':hashlib.sha256(raw).hexdigest(),'raw_base64':base64.b64encode(raw).decode(),'text':raw.rstrip(b'\n').rstrip(b'\r').decode(errors='replace'),'reasons':why})
 counts={v.decode():sum(v in r[2]for r in rows)for v in shared};assert all(counts.values())
 result={'run':n,'classification':'stalled'if n in[44,47]else'healthy','source':str(path),'source_bytes':len(data),'source_sha256':hashlib.sha256(data).hexdigest(),'tap_line':tap+1,'graphics_warning_lines':[rows[i][0]for i in warns],'post_tap_graphics_text_lines':[rows[i][0]for i in postgfx],'near_tap_warning_lines':[rows[i][0]for i in near],'post_tap_ps_lines':[rows[i][0]for i in ps],'shared_startup_warnings':counts,'excerpts':excerpts};results.append(result)
 assert not postgfx and not near
(out/'comparison.json').write_text(json.dumps({'runs':results,'scope':['LF-only byte offsets preserve CRCRLF and interleaving. All source hashes cover complete retained serial files.','Near means80 preceding/150 following LF records, not elapsed seconds. No uniform timestamps support a timed warning window.','Search skips owned marker lines, process-list lines, JSON/binary-image listing rows and rows over4096bytes. Historical crash-report text may contain library names and is not a current warning.','No matching non-owned graphics text follows tap in these logs. No near-tap general warning match; this does not establish absence from original unified logs or target-private output.','Five concrete IOMFB warnings occur in all six runs before their tap marker, so they do not distinguish the failure.','Failed44/47 have subsequent SpringBoard/backboardd PID/UID ps rows, supporting process presence only, not compositor-thread health.','No behavior change or causal diagnosis follows from this negative serial comparison. Next original target stack comparisons remain appropriate.']},indent=2)+'\n')
print(json.dumps([{k:r[k]for k in ['run','tap_line','post_tap_graphics_text_lines','near_tap_warning_lines','post_tap_ps_lines']}for r in results]))
