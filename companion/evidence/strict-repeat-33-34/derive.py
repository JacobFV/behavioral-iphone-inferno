#!/usr/bin/env python3
"""Read-only cross-check of strict33/34 raw transcripts, captures and retained disks."""
import argparse,hashlib,json,re,stat
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('repository',type=Path);p.add_argument('--output',type=Path,required=True);a=p.parse_args();root=a.repository.resolve();reports=root/'.local-build/reports';sources={};hashes={}
def filehash(path):
 path=Path(path)
 if str(path) not in hashes:
  before=path.stat();h=hashlib.sha256()
  with path.open('rb') as f:
   for b in iter(lambda:f.read(4*1024*1024),b''):h.update(b)
  after=path.stat();assert (before.st_ino,before.st_size,before.st_mtime_ns)==(after.st_ino,after.st_size,after.st_mtime_ns)
  hashes[str(path)]={'sha256':h.hexdigest(),'bytes':after.st_size}
 return hashes[str(path)]
def reference(path):
 key=str(path.relative_to(root)) if path.is_relative_to(root) else str(path);sources[key]=filehash(path);return key
def load(path):reference(path);return json.loads(path.read_bytes())
def lines(path,structured=False):
 key=reference(path);offset=0;out=[]
 for n,line in enumerate(path.read_bytes().splitlines(keepends=True),1):
  ref={'source':key,'line':n,'byte_start':offset,'byte_end':offset+len(line),'sha256':hashlib.sha256(line).hexdigest()};out.append((json.loads(line) if structured else line.decode(errors='replace').rstrip('\r\n'),ref));offset+=len(line)
 return out
def one(rows,predicate):
 matches=[(x,r) for x,r in rows if predicate(x)];assert len(matches)==1,len(matches);return matches[0]
def evidence(pair):return {'raw':pair[0],'reference':pair[1]}
results=[];common=None
for number in [33,34]:
 folder=reports/f'app-boot-{number}';report=load(folder/'report.json');overlay=load(folder/'root-overlay.json');stopped=load(folder/'stopped-disk-hashes.json')
 controls=lines(folder/'control-transcript.jsonl',True);qmp=lines(folder/'qmp-transcript.jsonl',True);serial=lines(folder/'serial.log');inputs=lines(folder/'serial-input-transcript.jsonl',True)
 counter=load(folder/'counter-tap-request.json');rid=counter['request_id']
 before=one(controls,lambda x:json.loads(x['raw'])['execute']=='probe-capture-before');after=one(controls,lambda x:json.loads(x['raw'])['execute']=='probe-capture-after')
 taps=[(x,r) for x,r in controls if json.loads(x['raw'])['execute']=='guest-hid-gesture' and json.loads(x['raw'])['arguments'].get('kind')=='tap' and json.loads(x['raw'])['arguments'].get('x')==counter['x'] and json.loads(x['raw'])['arguments'].get('y')==counter['y']]
 assert len(taps)==1 and json.loads(taps[0][0]['raw'])['arguments']==counter
 sent=one(inputs,lambda x:x.get('stage')=='before-send' and x.get('request_id')==rid)
 appeared=one(serial,lambda x:x.startswith('INFERNO_UIKIT_PROBE_V1 event=appeared count=0'))
 tapped=one(serial,lambda x:x.startswith('INFERNO_UIKIT_PROBE_V1 event=tap count=1'))
 raw_appeared=one(serial,lambda x:x.startswith('INFERNO_EVENT_RELAY_RAW ') and x.endswith(' appeared 0'))
 raw_tapped=one(serial,lambda x:x.startswith('INFERNO_EVENT_RELAY_RAW ') and x.endswith(' tap 1'))
 boot=raw_tapped[0].split('record=INFERNO_EVENT_V1 ')[1].split()[0];assert boot in raw_appeared[0]
 arrivals=lines(folder/'event-arrivals/observations.jsonl',True)
 ar=one(arrivals,lambda x:x['byte_start']==appeared[1]['byte_start']);tr=one(arrivals,lambda x:x['byte_start']==tapped[1]['byte_start'])
 for x,_ in [ar,tr]:
  assert not x['preexisting'];raw=(folder/'serial.log').read_bytes()[x['byte_start']:x['byte_end']];assert raw[:-1].hex()==x['raw_hex']
 assert ar[0]['observed_time']<before[0]['time']<sent[0]['time']<tr[0]['observed_time']<after[0]['time']
 captures={}
 for label in ['probe-before','probe-after']:
  path=folder/(label+'.ppm');data=path.read_bytes();header=re.match(rb'P6\s+(\d+)\s+(\d+)\s+255\s',data);assert header
  w,h=map(int,header.groups());assert(w,h)==(828,1792) and len(data)-header.end()==w*h*3
  cap=report['probe_journey']['captures'][label];assert filehash(path)['sha256']==cap['sha256']
  request=one(qmp,lambda x:x['direction']=='send' and json.loads(x['raw']).get('execute')=='screendump' and json.loads(x['raw']).get('arguments',{}).get('filename')==str(path));qid=json.loads(request[0]['raw'])['id'];reply=one(qmp,lambda x:x['direction']=='receive' and json.loads(x['raw']).get('id')==qid);assert json.loads(reply[0]['raw']).get('return')=={}
  captures[label]={'path':reference(path),'width':w,'height':h,'sha256':cap['sha256'],'qmp_request':evidence(request),'qmp_reply':evidence(reply)}
 quit_request=one(qmp,lambda x:x['direction']=='send' and json.loads(x['raw']).get('execute')=='quit');qid=json.loads(quit_request[0]['raw'])['id'];quit_reply=one(qmp,lambda x:x['direction']=='receive' and json.loads(x['raw']).get('id')==qid);assert json.loads(quit_reply[0]['raw']).get('return')=={} and report['exit_code']==0 and not report.get('error')
 assert len(stopped)==7
 for name,item in stopped.items():assert filehash(Path(item['path']))=={'sha256':item['sha256'],'bytes':item['bytes']}
 for item in overlay['dependencies']:
  path=Path(item['path']);assert filehash(path)=={'sha256':item['sha256'],'bytes':item['bytes']} and not(path.stat().st_mode&0o222)
 assert overlay['backing_after_stop']['unchanged'] and overlay['backing_after_stop']['layers']==overlay['dependencies']
 for item in report['auxiliary_base']['namespaces'].values():assert filehash(Path(item['path']))=={'sha256':item['sha256'],'bytes':item['bytes']}
 identity={'auxiliary_base':report['auxiliary_base'],'profile_sha256':report['profile_sha256'],'binary_sha256':report['binary_sha256'],'build_source':report['build_manifest']['source_revision'],'runner_sha256':report['runner_sha256'],'journey_source_sha256':report['probe_journey_source_sha256'],'frozen_source_report':overlay['backing_report'],'dependencies':[(x['path'],x['sha256']) for x in overlay['dependencies']]}
 assert filehash(Path(report['binary']))['sha256']==report['binary_sha256']
 if common is None:common=identity
 else:assert identity==common
 results.append({'boot':number,'boot_uuid':boot,'appeared0':evidence(appeared),'tap1':evidence(tapped),'relay_appeared_record':evidence(raw_appeared),'relay_tap_record':evidence(raw_tapped),'before_operator_command':evidence(before),'one_counter_tap_command':evidence(taps[0]),'counter_serial_before_send':evidence(sent),'after_operator_command':evidence(after),'chronology_verified':True,'captures':captures,'quit_request':evidence(quit_request),'quit_reply':evidence(quit_reply),'exit_code':report['exit_code'],'seven_stopped_files_fresh_hashes_match':True,'all_four_readonly_ancestors_fresh_hashes_match':True,'journey_completed':report['probe_journey']['completed'],'generic_placeholders':{k:report[k] for k in ['ios_booted','app_executed']}})
assert results[0]['boot_uuid']!=results[1]['boot_uuid']
stage=reports/'disk-preparation-48';profile=load(stage/'profile.json');stage_serial=lines(stage/'serial.log');build=load(root/'companion/evidence/owned-loopback-event-build.json')
components={}
for path,item in build['artifacts'].items():
 if path.endswith('/InfernoProbe') or path.endswith('/inferno-readiness'):
  assert filehash(Path(path))==item;components[path]=item
stageproof=[evidence(one(stage_serial,lambda x:phrase in x)) for phrase in ['INFERNO_APP_EXECUTABLE_READBACK bytes=73680 mismatches=0 info_plist_written=0','INFERNO_READINESS_READBACK bytes=70215 mismatches=0','INFERNO_PREP_COMPLETE:']]
for n in [33,34]:reference(root/f'companion/evidence/owned-loopback-strict-journey-{n}.json')
result={'scope':'Two actual controlled strict journeys from the same frozen48 source; no statistical reliability or intrinsic timing claim.','runs':results,'common_identity':common,'owned_components_fresh_hashes':components,'stage48_actual_guest_readback':stageproof,'stage48_profile_identity':profile['provenance']['system_app_executable'],'limitations':['Capture dimensions and hashes verified from actual PPM bytes and original QMP request/reply; visual counter0/1 reviews are separately retained in the referenced root strict-journey evidence.','Fresh file hashes corroborate recorded stopped manifests and immutable ancestors; no guest disk was mounted or modified.','Identical source components are established through retained component hashes, actual staging readback and identical frozen backing; runtime process images were not dumped.','Generic ios_booted/app_executed=false report fields are conservative placeholders; the separate raw original app markers, QMP images, operator commands and completed strict journey are the execution evidence.','Claimed app PID is verified by the receiver but TCP peer PID is unauthenticated.','Only two controlled runs, including operator-paced unlock/setup/capture; no throughput, density, cold/warm launch, statistical reliability or intrinsic latency inference.'],'sources':sources,'fresh_disk_and_component_hashes':hashes}
a.output.write_text(json.dumps(result,indent=2)+'\n')
