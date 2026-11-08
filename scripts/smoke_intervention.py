#!/usr/bin/env python3
"""GPU controller regressions and real gate evidence checks; no SR tuning."""
import argparse
from collections import Counter
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from types import SimpleNamespace
import numpy as np
import yaml
TREE=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(TREE),str(TREE/'scripts')]
from report_memory_four_arm import rows,records
from src.recovery_gate import validate_gate_request,current_shadow,select_gate
from src.recovery_agent import save_rgb
from src.qwen_client import QwenClient
from smoke_six_ablation import angle


def probe(folder,out):
    """Fixed perturbations describe sensitivity, not human-labelled accuracy."""
    original=records(folder/'native/recovery/gate_events.jsonl')
    selected=[r for r in original if r['visual_input_valid']][:2]
    assert selected,'No valid real memory input exercised'
    requests=[];descriptions={}
    for j,event in enumerate(selected):
        base=copy.deepcopy(event['gate_request']);base['id']='probe_'+str(j)
        requests += [base,current_shadow(base)]
        descriptions[base['id']]='Actual chronological RGB/action window'
        descriptions[requests[-1]['id']]='Same actions/current RGB; historical images omitted'
        reverse=copy.deepcopy(base);reverse['id']+=':reverse_history'
        for target,source in zip(reverse['images'][:-1],base['images'][-2::-1]):
            target.update(image=source['image'],image_sha256=source['image_sha256'])
        requests.append(reverse);descriptions[reverse['id']]='Stress test: historical pixels reversed, role/time metadata fixed; deliberately not a real chronology'
        blank=copy.deepcopy(base);blank['id']+=':blank'
        for k,item in enumerate(blank['images']):
            blank['images'][k]=save_rgb(item['role'],np.zeros((256,256,3),dtype=np.uint8),out/('blank_%d_%d.png'%(j,k)))
        requests.append(blank);descriptions[blank['id']]='Stress test bypassing runtime blank guard; no navigational decision'
    settings={}
    for name in ('inference_recovery','inference_memory_four_arm','inference_six_ablation','inference_intervention'):
        settings.update(yaml.safe_load((TREE/'src/config'/(name+'.yaml')).read_text())['inference_recovery'])
    client=QwenClient(SimpleNamespace(**settings),out/'worker')
    try:response=client.score(0,requests)
    finally:client.close()
    assert [r['id'] for r in response['results']]==[r['id'] for r in requests]
    assert all(r['valid'] and np.isfinite(r['logits']).all() for r in response['results'])
    verification=json.loads((out/'worker/verification_intervention_gate.json').read_text());assert verification['passed']
    report=dict(inputs=requests,descriptions=descriptions,output=response,verification=verification,
        decisions=[dict(id=r['id'],choice=select_gate(r)[0],reason=select_gate(r)[1]) for r in response['results']],
        purpose='Engineering/evidence-sensitivity probe only; no human labels or positive-SR requirement')
    (out/'probe.json').write_text(json.dumps(report,indent=2)+'\n')
    return dict(token_ids=verification['token_ids'],batch_solo_max_delta=verification['single_batch_max_delta'],
        decisions=report['decisions'],seconds=response['seconds'])


def main():
    p=argparse.ArgumentParser();p.add_argument('--batch',type=Path,required=True);a=p.parse_args();b=a.batch.resolve()
    assert os.environ.get('PBS_JOBID') and os.environ.get('PYTHONHASHSEED')=='0'
    out=b/'checks';out.mkdir(exist_ok=False);started=time.perf_counter()
    for arm in ['native','off','rule','A','P1','P2','P3','P4']:
        env=dict(os.environ)
        if arm=='native':env['RECOVERY_NATIVE_REFERENCE']='1'
        cmd=[sys.executable,str(TREE/'scripts/evaluate_recovery.py'),'--batch',str(b),'--run',str(out/('smoke_'+arm)),
            '--split','smoke','--mode','off','--arm','off' if arm=='native' else arm]
        with (out/(arm+'.log')).open('w') as log:subprocess.run(cmd,env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
        print('GPU engineering complete',arm,flush=True)
    refs=json.loads((b/'references.json').read_text())
    fields=['success','spl','view_match','navigation_reward','collisions','steps','pose_trace_sha256','actual_actions_sha256']
    for name,left,right in [('native_off',out/'smoke_native',out/'smoke_off'),
            ('A',Path(refs['smoke_A']),out/'smoke_A'),('rule',Path(refs['smoke_rule']),out/'smoke_rule')]:
        l,r=rows(left),rows(right);assert set(l)==set(r),(name,'tasks')
        for key in l:
            for field in fields:assert l[key][field]==r[key][field],(name,key,field)
    checks={}
    for arm in ['P1','P2','P3','P4']:
        d=out/('smoke_'+arm);result=json.loads((d/'result.json').read_text())
        events=records(d/'native/recovery/events.jsonl');gates=records(d/'native/recovery/gate_events.jsonl')
        assert result['harness']['technical_errors']==0
        if arm in ('P1','P2'):
            assert events and not gates and not result['harness']['worker_started']
            assert all(r['choice']==('A' if arm=='P1' else 'C') for r in events)
        else:
            assert gates and result['harness']['worker_started']
            for g in gates:
                request=g['gate_request'];validate_gate_request(request)
                assert len(request['images'])==(1 if arm=='P3' else 4)
                assert g['attempt']<=2 and g['step']==json.loads(request['context'])['current_step']
                if arm=='P4' and g['visual_input_valid']:
                    assert g['shadow_request']==current_shadow(request) and g['shadow_model'] is not None
                    assert g['shadow_model']['prompt_version']==g['gate_model']['prompt_version']
                name=Path(g['episode'][0]).stem+'_'+g['episode'][1]+'.npz'
                with np.load(d/'audit_traces'/name,allow_pickle=False) as trace:
                    c=json.loads(request['context']);window=trace['commands'][c['window_start_step']:g['step']]
                    np.testing.assert_array_equal(window,np.array([x['normalized_action'] for x in c['actual_executed_actions']],dtype=np.float32))
                    if g['start_scan']:np.testing.assert_array_equal(trace['commands'][g['step']],[-1,1])
        pose_checks=[]
        for e in events:
            assert e['decision_step']-e['step']==24
            name=Path(e['episode'][0]).stem+'_'+e['episode'][1]+'.npz'
            with np.load(d/'audit_traces'/name,allow_pickle=False) as trace:
                s=e['step'];poses=trace['poses']
                np.testing.assert_array_equal(trace['commands'][s:s+24],np.array([[-1,1]]*6+[[-1,-1]]*12+[[-1,1]]*6,np.float32))
                left,right,returned=[angle(poses[s,3:],poses[s+i,3:]) for i in (6,18,24)]
                assert abs(left-90)<.05 and abs(right-90)<.05 and returned<.05
                pose_checks.append(dict(id=e['id'],left=left,right=right,returned=returned))
            if arm=='P2':assert 'planned_actions' not in e
            elif e['choice']!='C':assert len(e['planned_actions'])==14
        checks[arm]=dict(metrics=result,scan_pose_checks=pose_checks,gate_count=len(gates),
            gate_choices=dict(Counter(g['gate_choice'] for g in gates)),
            history_changed_choice=sum(g['history_changed_choice'] for g in gates),
            history_changed_intervention=sum(g['history_changed_intervention'] for g in gates))
    probe_dir=out/'input_probe';probe_dir.mkdir();probe_summary=probe(out/'smoke_P4',probe_dir)
    summary=dict(passed=True,engineering_only=True,source_commit=json.loads((b/'source_manifest.json').read_text())['commit'],
        seconds=time.perf_counter()-started,native_off_exact=True,old_A_exact=True,old_rule_exact=True,
        arms=checks,input_probe=probe_summary,gate='Technical checks only. No tuning/selecting by smoke SR.')
    (out/'check_summary.json').write_text(json.dumps(summary,indent=2)+'\n')


if __name__=='__main__':main()
