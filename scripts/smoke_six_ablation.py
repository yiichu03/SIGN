#!/usr/bin/env python3
"""Real GPU engineering regressions, not a performance selection gate."""
import argparse
from collections import Counter
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import numpy as np
TREE=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(TREE/'scripts'))
from report_memory_four_arm import rows, records


def angle(a,b):
    a=np.asarray(a,dtype=float);b=np.asarray(b,dtype=float)
    cosine=abs(np.dot(a,b)/(np.linalg.norm(a)*np.linalg.norm(b)))
    return float(np.degrees(2*np.arccos(np.clip(cosine,0,1))))


def main():
    p=argparse.ArgumentParser();p.add_argument('--batch',type=Path,required=True);a=p.parse_args();b=a.batch.resolve()
    assert os.environ.get('PBS_JOBID') and os.environ.get('PYTHONHASHSEED')=='0'
    out=b/'checks';out.mkdir(exist_ok=False);started=time.perf_counter()
    assert json.loads((b/'offline/summary.json').read_text())['passed']
    for arm in ['native','off','A','E1','E2','E3','E4','E5','E6']:
        env=dict(os.environ)
        if arm=='native':env['RECOVERY_NATIVE_REFERENCE']='1'
        command=[sys.executable,str(TREE/'scripts/evaluate_recovery.py'),'--batch',str(b),'--run',str(out/('smoke_'+arm)),
            '--split','smoke','--mode','off','--arm','off' if arm=='native' else arm]
        with (out/(arm+'.log')).open('w') as log:subprocess.run(command,env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
        print('GPU smoke finished',arm,flush=True)
    keys=['success','spl','view_match','navigation_reward','collisions','steps','pose_trace_sha256','actual_actions_sha256']
    comparisons=[('native_off',out/'smoke_native',out/'smoke_off'),
        ('original_A_regression',Path(json.loads((b/'six_references.json').read_text())['smoke_A']),out/'smoke_A')]
    for name,left,right in comparisons:
        l,r=rows(left),rows(right);assert set(l)==set(r),(name,'keys')
        for key in l:
            for field in keys:assert l[key][field]==r[key][field],(name,key,field,l[key][field],r[key][field])
    checks={}
    for arm in ['A','E1','E2','E3','E4','E5','E6']:
        folder=out/('smoke_'+arm);result=json.loads((folder/'result.json').read_text());events=records(folder/'native/recovery/events.jsonl')
        assert events and result['harness']['technical_errors']==0,(arm,'No real exercised decision or worker failure')
        evidence=[]
        for e in events:
            if not e.get('active_survey'):continue
            k=4 if arm=='E5' else 6;assert e['commanded_view_yaw']==15*k and e['survey_command_steps']==4*k
            assert e['decision_step']-e['step']==4*k
            request=e['request'];roles=[x['role'] for x in request['images']]
            assert roles==(['CURRENT','LEFT','RIGHT'] if arm=='E2' else ['GOAL','CURRENT','LEFT','RIGHT'])
            if arm=='E1':assert request['task']=='balanced_arbitration' and e['model']['raw']['action_probabilities'] is not None
            if arm=='E3':assert e['model']['confidence_gate']==dict(min_probability=.5,min_margin=.1)
            if e['choice'] in ('A','B'):
                fwd=4 if arm=='E4' else 8
                expected=[[-1.,1. if e['choice']=='A' else -1.]]*k+[[np.float32(.6).item(),0.]]*fwd
                assert e['planned_actions']==expected,(arm,'planned recovery')
            name=Path(e['episode'][0]).stem+'_'+e['episode'][1]+'.npz'
            with np.load(folder/'audit_traces'/name,allow_pickle=False) as trace:
                commands=trace['commands'];poses=trace['poses'];start=e['step'];end=e['decision_step']
                assert np.array_equal(commands[start:end],np.array([[-1,1]]*k+[[-1,-1]]*(2*k)+[[-1,1]]*k,dtype=np.float32))
                left=angle(poses[start,3:],poses[start+k,3:]);right=angle(poses[start,3:],poses[start+3*k,3:]);returned=angle(poses[start,3:],poses[end,3:])
                assert abs(left-15*k)<.05 and abs(right-15*k)<.05 and returned<.05,(arm,left,right,returned)
                assert np.max(np.abs(poses[start:end+1,:3]-poses[start,:3]))<1e-5
                recovery_angle=None
                if e['choice'] in ('A','B') and len(commands)>=end+k and np.array_equal(commands[end:end+k],np.array(e['planned_actions'][:k],dtype=np.float32)):
                    recovery_angle=angle(poses[end,3:],poses[end+k,3:]);assert abs(recovery_angle-15*k)<.05
                evidence.append(dict(event=e['id'],left_yaw_abs=left,right_yaw_abs=right,returned_yaw_abs=returned,recovery_yaw_abs=recovery_angle))
        checks[arm]=dict(metrics=result,events=len(events),choices=dict(Counter(e['model']['semantic_choice'] for e in events)),
            scan_and_recovery_pose_checks=evidence)
    summary=dict(passed=True,engineering_only=True,seconds=time.perf_counter()-started,native_off_exact=True,original_A_exact=True,
        source_commit=json.loads((b/'source_manifest.json').read_text())['commit'],arms=checks,
        gate='Technical only; no small-subset positive SR requirement. Existing checkpoint and training untouched.')
    (out/'check_summary.json').write_text(json.dumps(summary,indent=2,allow_nan=False)+'\n')


if __name__=='__main__':main()
