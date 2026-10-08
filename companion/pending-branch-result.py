#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Parse fixed pending-branch GPR snapshots offline; never pair calls or read guest memory."""
import argparse,collections,hashlib,importlib.util,json
from pathlib import Path
PRODUCTION={'null-active':0xfffffff0096f1c74,'active-join':0xfffffff0096f1c7c,'queued-match':0xfffffff0096f1d1c}
LABELS={'null-active':'probe_null','active-join':'probe_active','queued-match':'probe_queued'}
BASE=Path(__file__).with_name('evidence')/'swapwait-cpu-parser/parse.py'
spec=importlib.util.spec_from_file_location('strict_cpu_blocks',BASE)
parser=importlib.util.module_from_spec(spec);spec.loader.exec_module(parser)

def parse(data,pcs=PRODUCTION,scope='production-fixed-pending-branch'):
    result=parser.parse(data,'kernel-zero-slide')
    result.update(mode=scope,expected_pcs={k:hex(v) for k,v in pcs.items()})
    distribution=collections.Counter();roles=collections.Counter();violations=[]
    for block in result['blocks']:
        block.pop('abi_low32',None)
        role=next((key for key,value in pcs.items() if block['pc'] is not None and int(block['pc'],16)==value), 'unknown-pc')
        block['role']=role;roles[role]+=1
        if not block['complete'] or role=='unknown-pc':continue
        regs={k:int(v,16) for k,v in block['registers'].items()};w=lambda k:regs[k]&0xffffffff
        fields={'mode':'unknown'}
        if role=='null-active':
            fields.update(requested_token=w('X00'),completed_token=w('X01'),active_pointer=block['registers']['X11'])
            if regs['X11']!=0:violations.append({'start':block['start'],'reason':'null-site X11 is not zero'})
            fields['null_branch_register_valid']=regs['X11']==0
        elif role=='active-join':
            fields.update(requested_token=w('X00'),completed_token=w('X01'),active_pointer_second_read=block['registers']['X11'])
            if regs['X11']:
                fields['active_token_third_read']=w('X10');fields['active_token_equals_requested']=w('X10')==w('X00')
            else:fields['active_token_third_read']=None
            fields['requested_equals_completed']=w('X00')==w('X01')
        else:
            fields.update(queue_pointer=block['registers']['X08'],queued_token=w('X09'),requested_token=w('X11'),tokens_equal=w('X09')==w('X11'))
            if not fields['tokens_equal']:violations.append({'start':block['start'],'reason':'queued-site W09 differs from W11'})
        block['branch_observation']=fields
        distribution[(role,json.dumps(fields,sort_keys=True))]+=1
    result['role_counts']=dict(roles);result['unknown_pc_count']=roles['unknown-pc'];result['semantic_violations']=violations
    result['distributions']=[{'role':role,'fields':json.loads(fields),'snapshots':count} for (role,fields),count in sorted(distribution.items())]
    result['base_parser_sha256']=hashlib.sha256(BASE.read_bytes()).hexdigest()
    result['limitations']=['Counts are independent snapshots, never invocation counts, CPU/process/thread identity or paired calls.',
      'Production interpretation requires independently validated original kernel/build/zero slide and actual exact-PC TB coverage.',
      'Modes0/1/2 can reach these sites; no captured mode or flags assumed.',
      'Active pointer is second field read, token comes from a third pointer read; coherent GPR dump is not atomic memory state.',
      'At null-active ignore X10. At active-join with X11zero token is unknown, never infer previous X10 value.',
      'Positive queued-match observation identifies equal comparison only; absence is not proof no queued match.',
      'No pointer is dereferenced; unknown/malformed/truncated blocks and semantic inconsistencies remain explicit.']
    return result

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--input',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--owned-fixture-report',type=Path,help='Only for relocated owned baremetal fixture, never original kernel attribution')
    a=p.parse_args();pcs=PRODUCTION;scope='production-fixed-pending-branch'
    if a.owned_fixture_report:
        fixture=json.loads(a.owned_fixture_report.read_text());pcs={key:fixture['symbols'][label] for key,label in LABELS.items()};scope='owned-relocated-fixture-not-production'
        if fixture.get('profile')!='pending-branch' or fixture['filter']!=','.join(hex(v)+'+4' for v in pcs.values()):raise ValueError('Fixture profile/filter differs')
    r=parse(a.input.read_bytes(),pcs,scope);r['input_path']=str(a.input.resolve())
    with a.output.open('x') as f:json.dump(r,f,indent=2);f.write('\n')
    print(json.dumps({key:r[key] for key in ('snapshot_count','complete_count','role_counts','unknown_pc_count','semantic_violations')}))
if __name__=='__main__':main()
