#!/usr/bin/env python3
"""Independent paired audit against preserved A and matched-scan rule results."""
import argparse
from collections import Counter
import csv
import json
from pathlib import Path
import sys
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.recovery_affordance import decision_prefix_audit
from report_memory_four_arm import rows,records


def main():
    p=argparse.ArgumentParser();p.add_argument('--batch',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
    refs=json.loads((a.batch/'six_references.json').read_text());summary={};paired=[]
    for arm in ['E1','E2','E3','E4','E5','E6']:
        folder=a.batch/('full_'+arm)
        if not (folder/'result.json').exists():summary[arm]=dict(status='not yet verified complete');continue
        metrics=json.loads((folder/'result.json').read_text());data=rows(folder);assert len(data)==4200
        events=records(folder/'native/recovery/events.jsonl')
        detail=dict(status='complete',metrics=metrics,choices=dict(Counter(e['model']['semantic_choice'] for e in events)),
            model_argmax=sum(e['model']['source']=='vlm' for e in events),
            confidence_keep=sum(e['model']['reason']=='confidence_keep' for e in events),
            safety_fallback=sum(e['model']['reason'] not in ('model_argmax','confidence_keep') for e in events),
            semantic_rule_disagreements=sum(e['model']['differs_from_rule'] for e in events),comparisons={})
        for reference in ['A','rule']:
            base_folder=Path(refs[reference]);base=rows(base_folder);assert set(base)==set(data)
            old_events=records(base_folder/'native/recovery/events.jsonl');cases=[]
            for key,r in data.items():
                ref=base[key];assert r['goal_sha256']==ref['goal_sha256'] and r['start_position']==ref['start_position']
                ev=[e for e in events if tuple(e['episode'])==key];oe=[e for e in old_events if tuple(e['episode'])==key]
                # Compare choices only at matched observation/action boundaries.
                different=[]
                for e in ev:
                    match=[o for o in oe if o.get('decision_step')==e['decision_step'] and
                        all(o['view_files'][side]['sha256']==e['view_files'][side]['sha256'] for side in ('forward','left','right'))]
                    if len(match)==1 and e['choice']!=match[0]['choice']:different.append(e['decision_step'])
                treatment=list(different)
                if arm=='E6':treatment += [e['step'] for e in ev+oe]
                if arm=='E5':treatment += [e['step']+4 for e in ev+oe]
                if arm=='E4':treatment += [e['decision_step']+6+4 for e in ev+oe if e['choice'] in ('A','B')]
                name=Path(key[0]).stem+'_'+key[1]+'.npz'
                with np.load(base_folder/'audit_traces'/name,allow_pickle=False) as left,np.load(folder/'audit_traces'/name,allow_pickle=False) as right:
                    first,model_prefix=decision_prefix_audit(left['commands'],left['poses'],right['commands'],right['poses'],different)
                    _,treatment_prefix=decision_prefix_audit(left['commands'],left['poses'],right['commands'],right['poses'],treatment)
                row=dict(arm=arm,reference=reference,scene_id=key[0],episode_id=key[1],reference_success=ref['success'],success=r['success'],
                    reference_spl=ref['spl'],spl=r['spl'],rescue=r['success']>ref['success'],harm=r['success']<ref['success'],
                    first_action_difference=first,matched_view_choice_changes=len(different),model_choice_prefix_supported=model_prefix,
                    treatment_prefix_supported=treatment_prefix,human_cause='',human_notes='')
                cases.append(row);paired.append(row)
            detail['comparisons'][reference]=dict(rescues=sum(r['rescue'] for r in cases),harms=sum(r['harm'] for r in cases),
                sr_delta_pp=100*sum(r['success']-r['reference_success'] for r in cases)/4200,
                spl_delta_pp=100*sum(r['spl']-r['reference_spl'] for r in cases)/4200,
                actual_action_changed_episodes=sum(r['first_action_difference'] is not None for r in cases),
                matched_view_choice_changes=sum(r['matched_view_choice_changes'] for r in cases),
                model_choice_prefix_supported_rescues=sum(r['rescue'] and r['model_choice_prefix_supported'] for r in cases),
                model_choice_prefix_supported_harms=sum(r['harm'] and r['model_choice_prefix_supported'] for r in cases),
                treatment_prefix_supported_rescues=sum(r['rescue'] and r['treatment_prefix_supported'] for r in cases),
                treatment_prefix_supported_harms=sum(r['harm'] and r['treatment_prefix_supported'] for r in cases))
        summary[arm]=detail
    if paired:
        with (a.output/'paired.csv').open('w',newline='') as f:
            w=csv.DictWriter(f,fieldnames=list(paired[0]));w.writeheader();w.writerows(paired)
    (a.output/'summary.json').write_text(json.dumps(dict(arms=summary,
        attribution='Paired rescue/harm describes outcomes. Matched image/step choice differences and action/pose prefixes are behavioral evidence, not human causal truth. E4/E5/E6 alter durations/scan/trigger; their effects are not automatically VLM reasoning gains. Single seed, repeated validation, no tuning on small-set SR.'),indent=2)+'\n')


if __name__=='__main__':main()
