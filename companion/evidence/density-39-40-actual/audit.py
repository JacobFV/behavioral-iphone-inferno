#!/usr/bin/env python3
"""Independent raw-text recomputation; run inside this evidence directory."""
import hashlib,json,pathlib
P=pathlib.Path(__file__).parent
S=json.loads((P/'summary.json').read_text())
R=[json.loads(x) for x in (P/'samples.jsonl').read_text().splitlines()]
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def stat(raw):
    f=raw[raw.rfind(')')+2:].split()
    return {'pid':int(raw.split(' ',1)[0]),'cpu_ticks':int(f[11])+int(f[12]),'start_ticks':int(f[19]),'threads':int(f[17])}
def kb(raw):
    return {f[0].rstrip(':'):int(f[1])*1024 for line in raw.splitlines() if len(f:=line.split())==3 and f[2]=='kB'}
def psi(raw):
    return {f[0]:dict((k,float(v) if k!='total' else int(v)) for k,v in (x.split('=') for x in f[1:])) for line in raw.splitlines() if (f:=line.split())}
assert len(R)==61 and [r['target_seconds'] for r in R]==list(range(61))
for r in R:
    assert 'error' not in r and len(r['processes'])==2
    for row,ident in zip(r['processes'],S['processes']):
        raw=stat(row['reads']['stat']['raw'])
        assert raw['pid']==ident['pid'] and raw['start_ticks']==ident['start_ticks']
    for read in list(r['host'].values())+[v for p in r['processes'] for v in p['reads'].values()]:
        assert read['error'] is None and len(read['raw'].encode())==read['bytes'] and read['end_ns']>=read['start_ns']
span=(R[-1]['start_ns']-R[0]['start_ns'])/1e9
cpu=[]
for i in range(2):
    first,last=[r['processes'][i] for r in (R[0],R[-1])]
    seconds=(stat(last['reads']['stat']['raw'])['cpu_ticks']-stat(first['reads']['stat']['raw'])['cpu_ticks'])/S['clock_ticks_per_second']
    cpu.append({'pid':first['pid'],'cpu_seconds':seconds,'stat_read_span_seconds':(last['reads']['stat']['start_ns']-first['reads']['stat']['start_ns'])/1e9})
mem=[]
for r in R:
    if all('smaps_rollup' in p['reads'] for p in r['processes']):
        parts=[kb(p['reads']['smaps_rollup']['raw']) for p in r['processes']]
        mem.append({'target_seconds':r['target_seconds'],'rss_sum':sum(x['Rss'] for x in parts),'pss_sum':sum(x['Pss'] for x in parts),'swap_sum':sum(x['Swap'] for x in parts),'swap_pss_sum':sum(x['SwapPss'] for x in parts),'per_pid':parts})
pressure={}
for kind in ('cpu','memory','io'):
    a,b=[r['host']['pressure_'+kind] for r in (R[0],R[-1])]
    dt=(b['start_ns']-a['start_ns'])/1e9
    aa,bb=psi(a['raw']),psi(b['raw'])
    pressure[kind]={name:{'total_delta_us':bb[name]['total']-aa[name]['total'],'stall_percent_of_read_interval':100*(bb[name]['total']-aa[name]['total'])/(dt*1e6),'first_avg10':aa[name]['avg10'],'last_avg10':bb[name]['avg10']} for name in aa}
hostmem=[kb(r['host']['meminfo']['raw']) for r in R]
rawcpu=[[int(x) for x in r['host']['stat']['raw'].splitlines()[0].split()[1:]] for r in (R[0],R[-1])]
deltas=[b-a for a,b in zip(*rawcpu)]
result={'kind':'independent_raw_proc_text_audit','sample_count':len(R),'span_seconds':span,'cpu':cpu,'aggregate_cpu_seconds':sum(x['cpu_seconds'] for x in cpu),'aggregate_cpu_percent_one_core':100*sum(x['cpu_seconds'] for x in cpu)/span,'memory_samples':mem,'peak_rss_sum':max(x['rss_sum'] for x in mem),'peak_pss_sum':max(x['pss_sum'] for x in mem),'max_round_span_seconds':max((r['end_ns']-r['start_ns'])/1e9 for r in R),'max_interprocess_stat_start_skew_seconds':max(abs(r['processes'][1]['reads']['stat']['start_ns']-r['processes'][0]['reads']['stat']['start_ns'])/1e9 for r in R),'round_interval_range_seconds':[min((b['start_ns']-a['start_ns'])/1e9 for a,b in zip(R,R[1:])),max((b['start_ns']-a['start_ns'])/1e9 for a,b in zip(R,R[1:]))],'pressure':pressure,'host_memory_bytes':{'min_available':min(x['MemAvailable'] for x in hostmem),'max_swap_used':max(x['SwapTotal']-x['SwapFree'] for x in hostmem),'first_swap_used':hostmem[0]['SwapTotal']-hostmem[0]['SwapFree'],'last_swap_used':hostmem[-1]['SwapTotal']-hostmem[-1]['SwapFree']},'host_cpu_first_eight_tick_deltas':deltas[:8],'host_cpu_busy_percent_excluding_idle_iowait':100*(sum(deltas[:8])-deltas[3]-deltas[4])/sum(deltas[:8]),'input_hashes':{n:sha(P/n) for n in ('samples.jsonl','summary.json')},'audit_source_sha256':sha(pathlib.Path(__file__))}
assert result['aggregate_cpu_seconds']==S['aggregate_cpu_seconds']
assert result['peak_rss_sum']==S['peak_sampled_rss_sum_bytes'] and result['peak_pss_sum']==S['peak_sampled_pss_sum_bytes']
assert result['max_round_span_seconds']==S['max_sample_read_span_seconds']
result['summary_recomputed_fields_match']=True
result['limits']=['Raw stat CPU and smaps memory independently recomputed; source clock tick rate retained from sampler provenance.','Two emulators only, not all host allocation or maximum density. RSS double counts sharing; PSS apportions shared pages among all sharers.','No VNC/input during window per root; periodic QMP captures30s and startup MT trace900s remained enabled. This is instrumented foreground-idle observation, not an uninstrumented baseline.','Host pressure/activity not attributable solely to these VMs. Swap occupancy does not measure swap traffic; no vmstat swap-in/out counters were sampled.','Sampling is sequential; measured skew retained. Snapshot peak is not continuous peak.','Parent supplied both strict journeys and reviewed counter1; resource samples alone do not establish UIKit correctness.']
(P/'audit.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({k:result[k] for k in ('span_seconds','aggregate_cpu_seconds','aggregate_cpu_percent_one_core','peak_rss_sum','peak_pss_sum','max_interprocess_stat_start_skew_seconds','host_memory_bytes','pressure')}))
