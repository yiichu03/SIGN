#!/usr/bin/env python3
"""Original A image replay, all six E1 mappings, E2, and CPU E3. No SR claims."""
import argparse
from collections import Counter
import csv
import json
import os
from pathlib import Path
import sys
import time
from types import SimpleNamespace
import numpy as np
TREE=Path(__file__).resolve().parents[1];sys.path.insert(0,str(TREE))
from src.qwen_client import QwenClient
from src.recovery_agent import select_agent
from src.recovery_options import PERMUTATIONS, balanced_option_map


def write(path,value):path.write_text(json.dumps(value,indent=2,allow_nan=False)+'\n')


def main():
    p=argparse.ArgumentParser();p.add_argument('--batch',type=Path,required=True);a=p.parse_args();b=a.batch.resolve()
    assert os.environ.get('PBS_JOBID') and os.environ.get('PYTHONHASHSEED')=='0'
    out=b/'offline';out.mkdir(exist_ok=False);started=time.perf_counter()
    original=json.loads((b/'original_A_decisions.json').read_text());requests=[];metadata={}
    for r in original:
        idx=r['index'];base=r['request'];assigned=balanced_option_map(idx,100)
        for arm,permutation in [('A_replay',None),('E2',None)]+[('E1',k) for k in range(6)]:
            row=dict(base,id=arm+':'+str(idx)+':'+str(permutation),images=list(base['images']))
            if arm=='E2':row.update(task='no_goal_arbitration',images=row['images'][1:])
            if arm=='E1':
                mapping=dict(zip('ABC',PERMUTATIONS[permutation]));context=json.loads(base['context']);context['option_to_action']=mapping
                row.update(task='balanced_arbitration',option_map=mapping,context=json.dumps(context))
            requests.append(row);metadata[row['id']]=dict(arm=arm,original_index=idx,original_event=r['id'],episode=r['episode'],
                step=r['step'],permutation=permutation,assigned_online_mapping=arm=='E1' and row['option_map']==assigned)
    cfg=SimpleNamespace(request_timeout=600,startup_timeout=600,python_executable=str(TREE.parent/'envs/qwen35/bin/python'),
        model_dir=str(TREE.parent/'models/Qwen3.5-2B'),prompt='scripts/prompts/recovery_agent.txt',feedback_prompt='scripts/prompts/recovery_feedback.txt',
        worker_script='scripts/recovery_worker.py',verify_first_batch=True,candidate_affordance=True,candidate_protocol='agent')
    client=QwenClient(cfg,out/'worker');records=[];max_error=0.;worker_seconds=0.
    try:
        # Each transport request remains small; real inference batches are <=2.
        for n in range(0,len(requests),16):
            selected=requests[n:n+16];response=client.score(n//16,selected);worker_seconds+=response['seconds']
            assert [r['id'] for r in response['results']]==[r['id'] for r in selected]
            for request,value in zip(selected,response['results']):
                meta=metadata[request['id']];old=original[meta['original_index']]
                choice,reason=select_agent(value)
                # Low candidate mass or ties are legitimate safe KEEP decisions,
                # not a reason to discard a potentially negative ablation result.
                if not value.get('valid') or reason=='invalid_model_evidence':
                    raise RuntimeError('Offline scoring invalid evidence: '+str((meta,reason)))
                error=float(np.max(np.abs(np.asarray(value['probabilities'])-old['value']['probabilities']))) if meta['arm']=='A_replay' else None
                if error is not None:max_error=max(max_error,error)
                record=dict(meta,id=request['id'],choice=choice,reason=reason,original_choice=old['selected'],changed=choice!=old['selected'],
                    option_map=request.get('option_map'),value=value,probability_replay_error=error,request=request)
                records.append(record)
            print('Offline scored',min(n+16,len(requests)),'/',len(requests),flush=True)
    finally:client.close()
    for old in original:
        choice,reason=select_agent(old['value'],minimum=.5,margin=.1)
        records.append(dict(arm='E3',id='E3:'+str(old['index']),original_index=old['index'],original_event=old['id'],episode=old['episode'],
            step=old['step'],choice=choice,reason=reason,original_choice=old['selected'],changed=choice!=old['selected'],
            value=old['value'],source='original frozen logits; no new model call'))
    summary={}
    for arm in ['A_replay','E1','E2','E3']:
        group=[r for r in records if r['arm']==arm]
        chosen=[r for r in group if arm!='E1' or r['assigned_online_mapping']]
        summary[arm]=dict(scored=len(group),online_schedule_rows=len(chosen),choices=dict(Counter(r['choice'] for r in chosen)),
            reasons=dict(Counter(r['reason'] for r in chosen)),changed_from_original=sum(r['changed'] for r in chosen))
    per_event=[len({r['choice'] for r in records if r['arm']=='E1' and r['original_index']==i}) for i in range(155)]
    e1=[r for r in records if r['arm']=='E1']
    summary['E1']['all_six_mapping_consistent_events']=sum(x==1 for x in per_event)
    summary['E1']['raw_token_argmax_all_permutations']=dict(Counter('ABC'[int(np.argmax(r['value']['probabilities']))] for r in e1))
    summary['E1']['semantic_choices_all_permutations']=dict(Counter(r['choice'] for r in e1))
    summary.update(passed=max_error<=1e-4,original_A_probability_max_abs_error=max_error,seconds=time.perf_counter()-started,
        worker_seconds=worker_seconds,source_commit=json.loads((b/'source_manifest.json').read_text())['commit'],
        interpretation='Reused155 original arbitration inputs, not independent performance data; no SR inference; thresholds/mappings not tuned.')
    write(out/'records.json',records);write(out/'summary.json',summary)
    with (out/'decisions.csv').open('w',newline='') as f:
        fields=['arm','id','original_event','episode','step','permutation','assigned_online_mapping','choice','reason','original_choice','changed','option_map','p_left','p_right','p_keep','raw_probabilities','raw_logits','candidate_mass','prompt_version','probability_replay_error']
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
        for r in records:
            row={k:r.get(k) for k in fields};v=r['value'];probs=v.get('action_probabilities',v['probabilities'])
            row.update(p_left=probs[0],p_right=probs[1],p_keep=probs[2],raw_probabilities=v['probabilities'],raw_logits=v['logits'],
                candidate_mass=v['candidate_mass'],prompt_version=v['prompt_version']);w.writerow(row)
    if not summary['passed']:raise RuntimeError('Original A probability reproduction failed')


if __name__=='__main__':main()
