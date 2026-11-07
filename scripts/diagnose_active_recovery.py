#!/usr/bin/env python3
"""Bounded, independent-image diagnostics on real development scan views."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import re
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'src'))
from qwen_single_image import SingleImageJudge
from inference_recovery import active_collage, choose


def main():
    p=argparse.ArgumentParser();p.add_argument('--events',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
    events=[json.loads(l) for l in a.events.read_text().splitlines()]
    if not events:
        (a.output/'summary.json').write_text(json.dumps(dict(technical_passed=False,reason='No completed real surveys; no synthetic replacement inputs'))+'\n');return
    for r in events:
        assert hashlib.sha256(Path(r['image']).read_bytes()).hexdigest()==r['image_sha256']
        for f in r['view_files'].values():assert hashlib.sha256(Path(f['path']).read_bytes()).hexdigest()==f['sha256']
    tree=Path(__file__).resolve().parents[1]
    conservative=(tree/'scripts/prompts/recovery_active_conservative.txt').read_text()
    balanced=(tree/'scripts/prompts/recovery_active_balanced.txt').read_text()
    permuted=re.sub(r'\b([AB]):',lambda m:'B:' if m[1]=='A' else 'A:',balanced)
    from PIL import Image
    import numpy as np
    mirrored=[]
    for r in events:
        def flipped(name):
            with Image.open(r['view_files'][name]['path']) as im:return np.asarray(im.transpose(Image.Transpose.FLIP_LEFT_RIGHT)).copy()
        survey=dict(views=dict(left=flipped('right'),right=flipped('left'),forward=flipped('forward')),
            view_steps=dict(left=r['view_steps']['right'],right=r['view_steps']['left'],forward=r['view_steps']['forward']),
            commanded_yaw=r['commanded_view_yaw'])
        dest=a.output/(r['id']+'_synthetic_mirror.png');active_collage(survey,flipped('goal'),dest);mirrored.append(str(dest))
    images=[r['image'] for r in events]
    judge=SingleImageJudge('/scratch/e1538633/liuyi/models/Qwen3.5-2B',balanced,dtype='float32')
    verification=judge.verify_readout(images[:min(3,len(images))],None)
    assert verification['passed'];(a.output/'verification.json').write_text(json.dumps(verification,indent=2)+'\n')
    output=[]
    conditions=[('conservative',conservative,images,False),('balanced',balanced,images,False),
                ('permuted_AB',permuted,images,True),('synthetic_mirror',balanced,mirrored,False)]
    for name,prompt,paths,swap in conditions:
        judge.prompt=prompt;version=hashlib.sha256(prompt.encode()).hexdigest()
        (a.output/(name+'_prompt.txt')).write_text(prompt)
        for start in range(0,len(paths),8):
            batch=paths[start:start+8];values,audit=judge.class_probabilities(batch,None)
            (a.output/(name+f'_batch_{start//8}.json')).write_text(json.dumps(audit,indent=2)+'\n')
            for r,image,value in zip(events[start:start+8],batch,values):
                assert value['valid']
                probs=[value[k] for k in ['p_low','p_medium','p_high']]
                action_probs=[probs[1],probs[0],probs[2]] if swap else probs
                selected=choose(probs)
                action={'A':'right','B':'left','C':'continue'}[selected] if swap else {'A':'left','B':'right','C':'continue'}[selected]
                output.append(dict(condition=name,id=r['id'],episode=r['episode'],trigger_step=r['step'],decision_step=r['decision_step'],
                    image=image,image_sha256=hashlib.sha256(Path(image).read_bytes()).hexdigest(),probabilities=probs,
                    p_left=action_probs[0],p_right=action_probs[1],p_continue=action_probs[2],logits=value['logits'],
                    candidate_mass=value['candidate_mass'],selected_label=selected,selected_action=action,prompt_version=version))
    by={name:[r for r in output if r['condition']==name] for name,_,_,_ in conditions}
    original=by['balanced'];mirror=by['synthetic_mirror'];permutation=by['permuted_AB']
    summary=dict(technical_passed=True,development_events=len(events),environment=judge.environment,
        choices={name:{choice:sum(r['selected_action']==choice for r in rows) for choice in ['left','right','continue']} for name,rows in by.items()},
        permutation_action_agreement=sum(x['selected_action']==y['selected_action'] for x,y in zip(original,permutation))/len(original),
        mirror_action_agreement=sum({'left':'right','right':'left','continue':'continue'}[x['selected_action']]==y['selected_action'] for x,y in zip(original,mirror))/len(original),
        balanced_has_directional_choice=any(r['selected_action']!='continue' for r in original),
        note='Development diagnostics only; mirror panels are synthetic symmetry probes, not navigation trajectories or human truth. Balanced prompt fixed before confirmation, not selected by confirmation scores.')
    (a.output/'scores.json').write_text(json.dumps(output,indent=2)+'\n')
    with (a.output/'scores.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(output[0]));w.writeheader();w.writerows(output)
    if not summary['balanced_has_directional_choice']:
        judge.prompt=balanced+'\nDiagnostic request only: briefly explain the visible evidence for your choice. Do not output numerical scores.'
        explanation=judge.score(images[:2])
        explanation['note']='Prose diagnostic. Legacy numeric-JSON parser status is not used as a classifier validity signal.'
        (a.output/'explanations.json').write_text(json.dumps(explanation,indent=2)+'\n')
    (a.output/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary,indent=2))


if __name__=='__main__':main()
