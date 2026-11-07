#!/usr/bin/env python3
"""Real view diagnostics through the same resident worker used online."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import sys
from types import SimpleNamespace
import numpy as np
from PIL import Image
import yaml
TREE=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(TREE))
from src.qwen_client import QwenClient
from src.recovery_affordance import candidate_image, select_candidate, semantic_probabilities


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--events',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();out=args.output.resolve();out.mkdir(parents=True,exist_ok=False)
    events=[json.loads(line) for line in args.events.read_text().splitlines()]
    assert events
    images=out/'inputs';images.mkdir()
    original=[];mirrored=[];control=[]
    for event in events:
        raw={}
        for name,item in event['view_files'].items():
            assert hashlib.sha256(Path(item['path']).read_bytes()).hexdigest()==item['sha256']
            with Image.open(item['path']) as im:raw[name]=np.asarray(im).copy()
        for side in ['left','right']:
            row=candidate_image(raw[side],raw['goal'],images/(event['id']+'_'+side+'.png'))
            row.update(id=event['id']+':'+side,side=side,event_id=event['id'],episode=event['episode'],
                trigger_step=event['step'],view_step=event['view_steps'][side],attempt=event['attempt'])
            original.append(row)
            mirror=candidate_image(raw['right' if side=='left' else 'left'][:,::-1].copy(),
                raw['goal'][:,::-1].copy(),images/(event['id']+'_mirror_'+side+'.png'))
            mirror.update(id=event['id']+':mirror:'+side,side=side,event_id=event['id'],attempt=event['attempt'])
            mirrored.append(mirror)
        # Same view on both sides, plus a blank pair: neither may create a VLM preference.
        if len(control)==0:
            for kind,view,goal in [('same_view',raw['left'],raw['goal']),
                    ('blank',np.full_like(raw['left'],127),np.full_like(raw['goal'],127))]:
                for side in ['left','right']:
                    item=candidate_image(view,goal,images/(kind+'_'+side+'.png'))
                    item.update(id=kind+':'+side);control.append(item)
    cfg=yaml.safe_load((TREE/'src/config/inference_recovery.yaml').read_text())['inference_recovery']
    cfg.update(candidate_affordance=True,prompt='scripts/prompts/recovery_candidate_affordance.txt')
    client=QwenClient(SimpleNamespace(**cfg),out/'worker');request=0
    def score(rows):
        nonlocal request
        result=client.score(request,rows);request+=1
        assert [x['id'] for x in result['results']]==[x['id'] for x in rows]
        return result['results']
    try:
        values=score(original)
        inverse_batch=score(original[::-1])[::-1]
        singles=[score([row])[0] for row in original]
        permutation_delta=max(abs(a[k][i]-b[k][i]) for a,b in zip(values,inverse_batch)
            for k in ['probabilities','reversed_probabilities'] for i in range(3))
        solo_delta=max(abs(a[k][i]-b[k][i]) for a,b in zip(values,singles)
            for k in ['probabilities','reversed_probabilities'] for i in range(3))
        assert max(permutation_delta,solo_delta)<=1e-4
        mirror_values=score(mirrored);control_values=score(control)
        for start in [0,2]:
            for fallback in ['A','B']:
                label,detail=select_candidate(*control_values[start:start+2],fallback)
                assert label==fallback and detail['source']=='rule_fallback'
        decisions=[];mirror_decisions=[]
        for i,event in enumerate(events):
            fallback='A' if event['attempt']%2 else 'B'
            label,detail=select_candidate(*values[2*i:2*i+2],fallback)
            mirrored_label,mirrored_detail=select_candidate(*mirror_values[2*i:2*i+2],
                'B' if fallback=='A' else 'A')
            decisions.append(dict(id=event['id'],choice=label,**detail))
            mirror_decisions.append(dict(id=event['id'],choice=mirrored_label,**mirrored_detail))
        paired=[(a,b) for a,b in zip(decisions,mirror_decisions) if a['source']==b['source']=='vlm']
        verification=json.loads((out/'worker/verification.json').read_text());assert verification['passed']
        summary=dict(technical_passed=True,development_events=len(events),
            model_selections=sum(v['source']=='vlm' for v in decisions),
            rule_fallbacks=sum(v['source']=='rule_fallback' for v in decisions),
            disagreements_with_rule=sum(v['differs_from_rule'] for v in decisions),
            permutation_delta=permutation_delta,batch_solo_delta=solo_delta,
            same_image_and_blank_fallback_passed=True,
            mirror_both_supported=len(paired),mirror_direction_flips=sum(a['choice']!=b['choice'] for a,b in paired),
            mirror_unknown_or_fallback=len(events)-len(paired),
            note='Reused development observations, no human accuracy labels. Mirror comparison excludes rule fallback. Technical gates only; zero supported choices is allowed and is reported, never forced.')
        (out/'scores.json').write_text(json.dumps(dict(inputs=original,results=values,decisions=decisions,
            mirror_inputs=mirrored,mirror_results=mirror_values,mirror_decisions=mirror_decisions,
            control_inputs=control,control_results=control_values),indent=2)+'\n')
        with (out/'human_review.csv').open('w',newline='') as f:
            writer=csv.DictWriter(f,fieldnames=['id','side','image','human_affordance','human_notes'])
            writer.writeheader();writer.writerows(dict(id=row['id'],side=row['side'],image=row['image'],
                human_affordance='',human_notes='') for row in original)
        (out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
        print(json.dumps(summary,indent=2))
    finally:
        client.close()


if __name__=='__main__':main()
