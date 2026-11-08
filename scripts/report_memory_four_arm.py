#!/usr/bin/env python3
"""Paired reporting only; never rewrites producer results or claims VLM causality."""
import argparse
import csv
import json
from pathlib import Path
import sys
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.recovery_affordance import decision_prefix_audit


def rows(folder):
    result={}
    for path in sorted((folder/'episodes').glob('*.jsonl')):
        for line in path.read_text().splitlines():
            r=json.loads(line);key=(r['scene_id'],r['episode_id'])
            if key in result:raise RuntimeError('Duplicate episode')
            result[key]=r
    return result

def records(path):return [json.loads(l) for l in path.read_text().splitlines()] if path.exists() else []

def main():
    p=argparse.ArgumentParser();p.add_argument('--batch',type=Path,required=True);p.add_argument('--split',default='full',choices=['full','smoke'])
    p.add_argument('--reference',default='rule');p.add_argument('--arms',nargs='+',default=['A','B','C','D']);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
    base_folder=a.batch/(a.split+'_'+a.reference);base=rows(base_folder);summaries={};paired=[]
    for arm in a.arms:
        folder=a.batch/(a.split+'_'+arm);data=rows(folder);assert data.keys()==base.keys()
        events=records(folder/'native/recovery/events.jsonl');feedback=records(folder/'native/recovery/feedback.jsonl')
        episode_stats=records(folder/'native/recovery/episodes.jsonl');case=[]
        for key,r in data.items():
            ref=base[key];assert r['goal_sha256']==ref['goal_sha256'] and r['start_position']==ref['start_position']
            ev=[e for e in events if tuple(e['episode'])==key]
            fb=[e for e in feedback if tuple(e['episode'])==key and 'choice' in e]
            changes=[e['decision_step'] for e in ev if e['model'].get('source')=='vlm' and
                (e['model'].get('memory_changed_decision') if a.reference=='A' and arm.startswith(('C','D')) else e['model'].get('differs_from_rule'))]
            changes += [e['step'] for e in fb if e.get('reason')=='model_argmax' and e['choice']=='return']
            name=Path(key[0]).stem+'_'+key[1]+'.npz'
            with np.load(base_folder/'audit_traces'/name,allow_pickle=False) as ref_trace,np.load(folder/'audit_traces'/name,allow_pickle=False) as actual:
                first,prefix=decision_prefix_audit(ref_trace['commands'],ref_trace['poses'],actual['commands'],actual['poses'],changes)
            rescue=r['success']>ref['success'];harm=r['success']<ref['success']
            entry=dict(arm=arm,reference=a.reference,scene_id=key[0],episode_id=key[1],reference_sr=ref['success'],sr=r['success'],
                reference_spl=ref['spl'],spl=r['spl'],rescue=rescue,harm=harm,first_action_difference=first,
                model_decision_changes=len(changes),prefix_supported_model_action_difference=prefix,
                memory_appearance_hits=sum(sum(x['match']['valid'] for x in e.get('memory_retrieval',[])) for e in ev),
                memory_prompt_entries=sum(e.get('memory_prompt_count',0) for e in ev),
                memory_changed_decisions=sum(e['model'].get('memory_changed_decision',False) for e in ev),
                verified_memory_changed_decisions=sum(e['model'].get('memory_changed_decision',False) and any(x['match']['valid'] for x in e.get('memory_retrieval',[])) for e in ev),
                human_cause='',human_notes='')
            case.append(entry);paired.append(entry)
        result=json.loads((folder/'result.json').read_text())
        summaries[arm]=dict(metrics=result,rescues=sum(x['rescue'] for x in case),harms=sum(x['harm'] for x in case),
            prefix_supported_rescues=sum(x['rescue'] and x['prefix_supported_model_action_difference'] for x in case),
            prefix_supported_harms=sum(x['harm'] and x['prefix_supported_model_action_difference'] for x in case),
            success_changes_without_model_decision=sum((x['rescue'] or x['harm']) and not x['model_decision_changes'] for x in case),
            actual_action_changed_episodes=sum(x['first_action_difference'] is not None for x in case),
            memory_stats={k:sum(x.get(k,0) for x in case) for k in ['memory_appearance_hits','memory_prompt_entries','memory_changed_decisions','verified_memory_changed_decisions']},
            episode_memory_writes=sum(x.get('memory_stats',{}).get('writes',0) for x in episode_stats))
    with (a.output/'paired.csv').open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(paired[0]));writer.writeheader();writer.writerows(paired)
    (a.output/'summary.json').write_text(json.dumps(dict(reference=a.reference,split=a.split,arms=summaries,
        attribution='SR/SPL changes without actual model decisions are not VLM gains. Prefix support is necessary evidence, not a causal proof. Retrieval matches are appearance checks, not human true locations. Memory changes use an unexecuted no-memory shadow readout; run A comparisons separately.'),indent=2)+'\n')

if __name__=='__main__':main()
