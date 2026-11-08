#!/usr/bin/env python3
"""Read-only P1–P4 paired outcomes and intervention attribution."""
import argparse
from collections import Counter
import csv
import hashlib
import json
from pathlib import Path
import sys
import numpy as np
TREE=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(TREE))
from report_memory_four_arm import rows,records
from src.recovery_affordance import decision_prefix_audit


def main():
    p=argparse.ArgumentParser();p.add_argument('--batch',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
    refs={k:Path(v) for k,v in json.loads((a.batch/'references.json').read_text()).items() if not k.startswith('smoke_')}
    refs['P3']=a.batch/'full_P3';manifest=json.loads((a.batch/'source_manifest.json').read_text())
    summaries={};paired=[]
    for arm in ['P1','P2','P3','P4']:
        folder=a.batch/('full_'+arm);result_path=folder/'result.json'
        if not result_path.exists():summaries[arm]=dict(status='not verified complete');continue
        metrics=json.loads(result_path.read_text());data=rows(folder)
        assert metrics['episodes']==len(data)==4200 and metrics['source_commit']==manifest['commit']
        assert abs(sum(r['success'] for r in data.values())/4200-metrics['success_rate'])<1e-12
        assert abs(sum(r['spl'] for r in data.values())/4200-metrics['spl'])<1e-12
        gates=records(folder/'native/recovery/gate_events.jsonl');events=records(folder/'native/recovery/events.jsonl')
        detail=dict(status='complete',metrics=metrics,result_sha256=hashlib.sha256(result_path.read_bytes()).hexdigest(),
            gate_choices=dict(Counter(g['gate_choice'] for g in gates)),gate_reasons=dict(Counter(g['gate_reason'] for g in gates)),
            model_vetoes=sum(g['gate_choice']=='progress' and g['gate_reason']=='model_argmax' for g in gates),
            history_changed_choice=sum(g['history_changed_choice'] for g in gates),
            history_changed_intervention=sum(g['history_changed_intervention'] for g in gates),comparisons={})
        references=['off','rule','A']+(['E2'] if arm=='P1' else ['P3'] if arm=='P4' else [])
        for name in references:
            ref=refs[name]
            if not (ref/'result.json').exists():detail['comparisons'][name]=dict(status='reference missing');continue
            base=rows(ref);assert base.keys()==data.keys()
            ref_gates=records(ref/'native/recovery/gate_events.jsonl');cases=[]
            for key,r in data.items():
                old=base[key];assert r['goal_sha256']==old['goal_sha256'] and r['start_position']==old['start_position']
                current=[g for g in gates if tuple(g['episode'])==key]
                previous=[g for g in ref_gates if tuple(g['episode'])==key]
                model_steps=[]
                for g in current:
                    if name=='P3':
                        matches=[x for x in previous if x['step']==g['step'] and
                            x['gate_request']['images'][-1]['image_sha256']==g['gate_request']['images'][-1]['image_sha256'] and
                            json.loads(x['gate_request']['context'])['actual_executed_actions']==json.loads(g['gate_request']['context'])['actual_executed_actions']]
                        if len(matches)==1 and matches[0]['start_scan']!=g['start_scan']:model_steps.append(g['step'])
                    elif name=='rule' and g['gate_choice']=='progress' and g['gate_reason']=='model_argmax':
                        model_steps.append(g['step'])
                es=[e for e in events if tuple(e['episode'])==key]
                treatment_steps=[e['decision_step'] for e in es]+[e['step'] for e in es]+[g['step'] for g in current]
                file=Path(key[0]).stem+'_'+key[1]+'.npz'
                with np.load(ref/'audit_traces'/file,allow_pickle=False) as l,np.load(folder/'audit_traces'/file,allow_pickle=False) as rr:
                    first,model_prefix=decision_prefix_audit(l['commands'],l['poses'],rr['commands'],rr['poses'],model_steps)
                    _,treatment_prefix=decision_prefix_audit(l['commands'],l['poses'],rr['commands'],rr['poses'],treatment_steps)
                row=dict(arm=arm,reference=name,scene_id=key[0],episode_id=key[1],reference_success=old['success'],success=r['success'],
                    reference_spl=old['spl'],spl=r['spl'],rescue=r['success']>old['success'],harm=r['success']<old['success'],
                    first_action_difference=first,model_intervention_prefix_supported=model_prefix,treatment_prefix_supported=treatment_prefix,
                    actual_gate_vetoes=sum(not g['start_scan'] for g in current),
                    shadow_history_changed_intervention=sum(g['history_changed_intervention'] for g in current),human_cause='',human_notes='')
                cases.append(row);paired.append(row)
            detail['comparisons'][name]=dict(rescues=sum(r['rescue'] for r in cases),harms=sum(r['harm'] for r in cases),
                sr_delta_pp=100*sum(r['success']-r['reference_success'] for r in cases)/4200,
                spl_delta_pp=100*sum(r['spl']-r['reference_spl'] for r in cases)/4200,
                changed_action_episodes=sum(r['first_action_difference'] is not None for r in cases),
                model_prefix_rescues=sum(r['rescue'] and r['model_intervention_prefix_supported'] for r in cases),
                model_prefix_harms=sum(r['harm'] and r['model_intervention_prefix_supported'] for r in cases))
        summaries[arm]=detail
    if paired:
        with (a.output/'paired.csv').open('w',newline='') as f:
            writer=csv.DictWriter(f,fieldnames=list(paired[0]));writer.writeheader();writer.writerows(paired)
    (a.output/'summary.json').write_text(json.dumps(dict(source_commit=manifest['commit'],arms=summaries,
        notes='P4 shadow never executes. Same-prefix action evidence is not a human cause label. Invalid/missing runs are not results. Single-seed repeated validation.'),indent=2)+'\n')


if __name__=='__main__':main()
