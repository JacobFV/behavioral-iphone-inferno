#!/usr/bin/env python3
"""Observe completed original ps absence, then derive one named new-process launch.
SPDX-License-Identifier: AGPL-3.0-or-later
No warm-parser relaxation, process termination, cache clearing or guest input.
"""
import argparse
from fractions import Fraction
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import time

spec=importlib.util.spec_from_file_location('warm_timing',Path(__file__).with_name('warm-timing.py'))
w=importlib.util.module_from_spec(spec);spec.loader.exec_module(w)
require=w.require
EXE='/Applications/InfernoProbe.app/InfernoProbe'
LIMIT=w.initial.LIMIT

def read(path):
    with path.open('rb') as f:data=f.read(LIMIT+1)
    require(len(data)<=LIMIT,f'{path.name} exceeds16MiB bound')
    return data

def identity(path,data):return {'path':str(path.resolve()),'bytes':len(data),'sha256':w.initial.sha(data)}
def structured(data):return [(json.loads(raw),ref) for raw,ref in w.rows(data)]
def only(items,message):
    require(len(items)==1,message);return items[0]

def ps_window(data,seconds,old_pid,after_id):
    rows=list(w.rows(data));begin=only([i for i,(_,r) in enumerate(rows) if r['text']==f'INFERNO_READINESS_BEGIN seconds={seconds}'],'Missing or ambiguous readiness BEGIN')
    ends=[i for i,(_,r) in enumerate(rows) if i>begin and r['text'].startswith(f'INFERNO_READINESS_END seconds={seconds} ')]
    end=only(ends,'Missing or ambiguous readiness END')
    require(rows[end][1]['text']==f'INFERNO_READINESS_END seconds={seconds} status=0 ps_watchdog=600 timed_out=0','ps did not exit normally or timed out')
    require(rows[end][0].endswith(b'\n'),'Incomplete readiness END')
    require(not any(r['text'].startswith('INFERNO_READINESS_BEGIN') for _,r in rows[begin+1:end]),'Overlapping readiness windows')
    header=only([i for i in range(begin+1,end) if rows[i][1]['text'].strip()=='PID  PPID   UID STAT COMM'],'Missing or ambiguous original ps header')
    processes=[]
    for _,ref in rows[header+1:end]:
        text=ref['text']
        if not text.strip():continue
        m=re.fullmatch(r'\s*([0-9]+)\s+([0-9]+)\s+([0-9]+)\s+(\S+)\s+(.+)',text)
        require(m is not None,'Unparsed/non-process output in ps listing; absence inconclusive')
        pid,ppid,uid=map(int,m.groups()[:3]);require(0<pid<=2147483647 and 0<=ppid<=2147483647 and 0<=uid<=4294967295,'Invalid ps numeric field')
        processes.append({'pid':pid,'ppid':ppid,'uid':uid,'state':m[4],'comm':m[5],'reference':ref})
    require(processes and len({x['pid'] for x in processes})==len(processes),'Empty or duplicate-PID ps listing')
    ack=only([r for _,r in rows if r['text'].startswith(f'INFERNO_HID_ACK request_id={after_id} ')],'Missing or ambiguous dismissal acknowledgment')
    matches=[x for x in processes if x['pid']==old_pid or x['comm']==EXE]
    reasons=[]
    if ack['byte_end']>rows[begin][1]['byte_start']:reasons.append('ps snapshot predates dismissal acknowledgment')
    if matches:reasons.append('Old PID or exact owned executable remains present')
    return {'nominal_seconds':seconds,'begin':rows[begin][1],'header':rows[header][1],'end':rows[end][1],'dismiss_ack':ack,'row_count':len(processes),'matching_rows':matches,'process_rows':processes,'rejection_reasons':reasons}

def control_request(data,rid,command):
    items=[]
    for item,ref in structured(data):
        request=json.loads(item['raw'])
        if request.get('execute')==command and request.get('arguments',{}).get('request_id')==rid:
            require(w.initial.sha(item['raw'].encode())==item['sha256'],'Control request hash mismatch')
            items.append((request,item,ref))
    return only(items,'Missing or duplicate explicit host request')

def capture(args,result):
    require(re.fullmatch(w.RID,args.after_request_id) is not None,'Invalid after-request-id')
    started=time.time();data=read(args.report/'serial.log');control=read(args.report/'control-transcript.jsonl');captured=time.time()
    window=ps_window(data,args.ps_seconds,args.old_pid,args.after_request_id)
    request,record,ref=control_request(control,args.after_request_id,'guest-hid-gesture')
    require(record['time']<=captured,'Dismissal control timestamp is after capture')
    serial_path=args.output.with_suffix('.serial-prefix.log');control_path=args.output.with_suffix('.control-prefix.jsonl')
    serial_path.write_bytes(data);control_path.write_bytes(control)
    result.update(kind='original_ps_absence_capture',old_pid=args.old_pid,after_request_id=args.after_request_id,read_started_host_epoch=started,captured_host_epoch=captured,serial=identity(serial_path,data),control=identity(control_path,control),window=window,dismissal_control_reference=ref,status='rejected' if window['rejection_reasons'] else 'complete')
    if window['rejection_reasons']:result['reason']='; '.join(window['rejection_reasons'])
    return 2 if window['rejection_reasons'] else 0

def verified_snapshot(manifest,report,old_pid):
    require(manifest['status']=='complete' and manifest['old_pid']==old_pid,'Absence snapshot is rejected or has different old PID')
    captured=manifest['captured_host_epoch'];require(isinstance(captured,(int,float)) and captured>0,'Invalid absence host timestamp')
    retained={}
    for name,current in [('serial','serial.log'),('control','control-transcript.jsonl')]:
        item=manifest[name];data=read(Path(item['path']));require(len(data)==item['bytes'] and w.initial.sha(data)==item['sha256'],'Absence retained snapshot hash mismatch')
        require(read(report/current)[:len(data)]==data,'Absence snapshot is not a prefix of this report');retained[name]=data
    window=ps_window(retained['serial'],manifest['window']['nominal_seconds'],old_pid,manifest['after_request_id'])
    require(not window['rejection_reasons'],'Reparsed absence snapshot failed')
    control_request(retained['control'],manifest['after_request_id'],'guest-hid-gesture')
    return window

def derive(args,result):
    require(re.fullmatch(w.RID,args.request_id) is not None,'Invalid request-id')
    require(args.old_pid!=args.new_pid and 0<args.new_pid<=2147483647,'Expected distinct explicit old/new PIDs')
    snapshot_bytes=read(args.absence);snapshot=json.loads(snapshot_bytes);window=verified_snapshot(snapshot,args.report,args.old_pid)
    data=read(args.report/'serial.log');source_rows=list(w.rows(data));result['serial']=identity(args.report/'serial.log',data)
    groups={'timing':[],'validated':[],'open':[],'identity':[],'events':[],'event_validated':[]}
    specs=[('INFERNO_TIMING_RELAY_RAW',w.initial.RAW,'timing'),('INFERNO_TIMING_RELAY_RECORD',w.initial.VALIDATED,'validated'),('INFERNO_OPEN_TIMING_V1',w.OPEN,'open'),('INFERNO_EVENT_PROCESS_IDENTITY ',w.IDENTITY,'identity'),('INFERNO_EVENT_RELAY_RAW',w.initial.LIFE,'events'),('INFERNO_EVENT_RELAY_RECORD',w.initial.LIFE_VALIDATED,'event_validated')]
    for raw,ref in source_rows:
        for prefix,pattern,key in specs:
            if ref['text'].startswith(prefix):
                m=pattern.fullmatch(ref['text']);require(raw.endswith(b'\n') and m is not None,f'Malformed {prefix}')
                groups[key].append((m.groups(),ref))
    fields,opened=only([(f,r) for f,r in groups['open'] if f[0]==args.request_id],'Missing or duplicate named OPEN timing')
    rid,boot,launcher,req,callback,numer,denom,accepted=fields;req,callback,numer,denom=map(int,(req,callback,numer,denom))
    require(accepted=='1' and 0<req<=callback<=2**64-1 and 0<numer<=2**32-1 and 0<denom<=2**32-1,'Named OPEN rejected or invalid clock')
    selected=[(f,r) for f,r in groups['timing'] if f[1]==str(args.new_pid)];require(len(selected)==5,'New PID must have exactly five timing hooks')
    require(len([f for f,_ in groups['validated'] if f[1]==str(args.new_pid)])==5,'Ambiguous validated new timing record count')
    hooks={};previous=req
    for seq,(f,ref) in enumerate(selected,1):
        b,p,s,hook,t,n,d=f;t,n,d=map(int,(t,n,d))
        require((b,n,d)==(boot,numer,denom) and int(s)==seq and hook in w.initial.HOOKS and hook not in hooks,'Mixed or duplicate new-process timing sequence')
        require(seq!=1 or hook=='main','First new hook is not main');require(previous<=t<=2**64-1,'New hook precedes request or decreases');previous=t
        vf,vr=only([(v,r) for v,r in groups['validated'] if v[:7]==f],'Missing or duplicate validated new hook')
        require(int(vf[7])==(seq==5) and vr['byte_start']>ref['byte_start'],'Invalid new-hook provenance/complete flag')
        hooks[hook]={'ticks':t,'raw':ref,'validated':vr}
    require(set(hooks)==w.initial.HOOKS,'Incomplete new hook set')
    old_mains=[(f,r) for f,r in groups['timing'] if f[1]==str(args.old_pid) and f[3]=='main']
    old,old_ref=only(old_mains,'Missing or ambiguous old main hook')
    only([(v,r) for v,r in groups['validated'] if v[:7]==old], 'Missing or duplicate validated old main hook')
    require(old[0]==boot and (int(old[5]),int(old[6]))==(numer,denom) and int(old[4])<hooks['main']['ticks'] and old_ref['byte_end']<=window['begin']['byte_start'],'Old process identity does not precede absence')
    identities={}
    for pid in [args.old_pid,args.new_pid]:
        f,ref=only([(f,r) for f,r in groups['identity'] if f[0]==str(pid)],'Missing or ambiguous process incarnation')
        require(int(f[1])==56 and int(f[2])==0 and 0<int(f[3])<=2**64-1,'Strong classification requires original successful nonzero kernel incarnation')
        require(not any(r['text'].startswith('INFERNO_EVENT_PROCESS_IDENTITY_REJECT ') and re.search(rf'\bpid={pid}\b',r['text']) for _,r in source_rows),'Incarnation rejection observed')
        identities[str(pid)]={'uniqueid':int(f[3]),'idversion':int(f[4]),'reference':ref}
    require(identities[str(args.old_pid)]['uniqueid']!=identities[str(args.new_pid)]['uniqueid'],'Kernel incarnation is not distinct')
    life=[]
    for hook in ['main','appeared','active']:
        f,ref=only([(f,r) for f,r in groups['events'] if f[0]==boot and f[1]==str(args.new_pid) and f[3:]==(hook,'0')],'Missing or ambiguous new lifecycle hook')
        _,vr=only([(v,r) for v,r in groups['event_validated'] if v==f[:3]],'Missing validated new lifecycle hook');life.append({'hook':hook,'raw':ref,'validated':vr})
    host=read(args.report/'control-transcript.jsonl');request,record,cref=control_request(host,args.request_id,'guest-open-app')
    require(request['arguments']=={'request_id':args.request_id,'boot_uuid':boot},'Host OPEN boot/fields mismatch')
    require(snapshot['captured_host_epoch']<request['created']<=record['time'],'Absence was not captured before named OPEN creation')
    wire=read(args.report/'serial-input-transcript.jsonl');sent,sref=only([(x,r) for x,r in structured(wire) if x.get('stage')=='before-send' and x.get('request_id')==args.request_id],'Missing or duplicate named serial OPEN')
    require(sent['raw']==f'INFERNO_OPEN_V1 {args.request_id} {boot}\n' and w.initial.sha(sent['raw'].encode())==sent['sha256'] and record['time']<=sent['time'],'Serial OPEN mismatch/order failure')
    for x,_ in structured(host):
        request2=json.loads(x['raw'])
        if request2.get('execute')=='guest-open-app' and request2.get('arguments',{}).get('request_id')!=args.request_id:
            require(not snapshot['captured_host_epoch']<=request2['created']<=record['time'],'Other OPEN between absence and selected request')
    for f,_ in groups['open']:
        if f[0]!=args.request_id:require(not req<=int(f[3])<=hooks['active']['ticks'],'Overlapping guest OPEN request')
    def delta(a,b):
        value=Fraction((b-a)*numer,denom);return {'delta_ticks':b-a,'nanoseconds_numerator':value.numerator,'nanoseconds_denominator':value.denominator,'milliseconds_approximate':float(value/1000000)}
    result.update(kind='process_launch_after_observed_absence',status='complete',boot_uuid=boot,old_pid=args.old_pid,new_pid=args.new_pid,request_id=args.request_id,absence_manifest=identity(args.absence,snapshot_bytes),absence_window=window,process_identities=identities,timebase={'numer':numer,'denom':denom},request_ticks=req,callback_ticks=callback,new_hooks=hooks,new_lifecycle=life,open_reference=opened,host_control_reference=cref,host_serial_reference=sref,host_sources={'control':identity(args.report/'control-transcript.jsonl',host),'serial_input':identity(args.report/'serial-input-transcript.jsonl',wire)},intervals={'request_to_main':delta(req,hooks['main']['ticks']),'main_to_appeared':delta(hooks['main']['ticks'],hooks['appeared']['ticks']),'main_to_active':delta(hooks['main']['ticks'],hooks['active']['ticks']),'request_to_active':delta(req,hooks['active']['ticks']),'request_to_callback':delta(req,callback)})
    return 0

def main():
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='mode',required=True)
    for name in ['capture-absence','derive']:
        s=sub.add_parser(name);s.add_argument('--report',type=Path,required=True);s.add_argument('--old-pid',type=int,required=True);s.add_argument('--output',type=Path,required=True)
        if name=='capture-absence':s.add_argument('--ps-seconds',type=int,required=True);s.add_argument('--after-request-id',required=True)
        else:s.add_argument('--new-pid',type=int,required=True);s.add_argument('--request-id',required=True);s.add_argument('--absence',type=Path,required=True)
    args=p.parse_args();result={'source_sha256':{n:w.initial.sha(Path(__file__).with_name(n).read_bytes()) for n in ['process-launch-timing.py','warm-timing.py','launch-timing.py']},'limits':['One completed ps enumeration proves observed absence, not continuous absence or termination cause.','Host capture chronology is separate from guest clock intervals.','Strong classification requires original kernel process identities; no fallback is promoted to strong.','No cold-cache, native-device, statistical reliability or intrinsic presentation claim.','Visual AppSwitcher dismissal and returned app state require separate review.']}
    try:code=capture(args,result) if args.mode=='capture-absence' else derive(args,result)
    except (OSError,ValueError,TypeError,KeyError) as e:result.update(status='rejected',reason=str(e));code=2
    args.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'status':result['status'],'reason':result.get('reason'),'output':str(args.output)}));return code

if __name__=='__main__':raise SystemExit(main())
