#!/usr/bin/env python3
"""Probe semantic-word logits through the existing resident worker."""
import argparse
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
from src.recovery_affordance import raw_candidate_image,select_semantic_candidate,select_directional,select_candidate


def main():
    p=argparse.ArgumentParser();p.add_argument('--batch',type=Path,required=True);p.add_argument('--events',type=Path)
    p.add_argument('--guard',action='store_true')
    a=p.parse_args();b=a.batch.resolve()
    if a.guard:
        from evaluate_recovery import guard
        guard(b)
    out=b/'probe';out.mkdir(exist_ok=False);(out/'inputs').mkdir()
    inputs=json.loads((b/'probe_inputs.json').read_text());event_path=a.events or Path(inputs['events'])
    events=[json.loads(l) for l in event_path.read_text().splitlines()]
    cfg=yaml.safe_load((TREE/'src/config/inference_recovery.yaml').read_text())['inference_recovery']
    cfg.update(yaml.safe_load((TREE/json.loads((b/'tasks.json').read_text())['recovery_profile']).read_text())['inference_recovery'])
    directional=cfg.get('candidate_protocol')=='directional'
    selector=select_candidate if cfg.get('candidate_protocol')=='semantic_balanced' else select_semantic_candidate
    rows=[]
    for e in events:
        if directional:
            rows.append(dict(id=e['id'],image=e['image'],image_sha256=e['image_sha256']))
            continue
        for side in ['left','right']:
            with Image.open(e['view_files'][side]['path']) as im:view=np.asarray(im).copy()
            row=raw_candidate_image(view,out/'inputs'/(e['id']+'_'+side+'.png'))
            row.update(id=e['id']+':'+side,side=side,event_id=e['id']);rows.append(row)
    client=QwenClient(SimpleNamespace(**cfg),out/'worker')
    try:
        result=client.score(0,rows)['results'];assert [x['id'] for x in result]==[x['id'] for x in rows]
        decisions=[]
        for i,e in enumerate(events):
            fallback='A' if e['attempt']%2 else 'B'
            label,detail=(select_directional(result[i],fallback,cfg['candidate_support_gap']) if directional else
                selector(*result[2*i:2*i+2],fallback,cfg['candidate_support_gap'],
                    relative_only=bool(cfg.get('candidate_relative_only',False))))
            decisions.append(dict(id=e['id'],choice=label,evidence=detail))
        gray=np.full((128,128,3),127,dtype=np.uint8);controls=[]
        for side in ['left','right']:
            row=raw_candidate_image(gray,out/'inputs'/('blank_'+side+'.png'));row['id']='blank:'+side;controls.append(row)
        values=client.score(1,controls)['results']
        label,detail=(select_directional(values[0],'A',cfg['candidate_support_gap']) if directional else
            selector(*values,'A',cfg['candidate_support_gap'],
                relative_only=bool(cfg.get('candidate_relative_only',False))))
        (out/'scores.json').write_text(json.dumps(dict(inputs=rows,results=result,decisions=decisions,
            blank=values,blank_decision=dict(choice=label,evidence=detail)),indent=2)+'\n')
        assert label=='A' and detail['source']=='rule_fallback'
        audit=json.loads((out/'worker/verification.json').read_text());assert audit['passed']
        summary=dict(technical_passed=True,token_ids=audit['token_ids'],events=len(events),source_events=str(event_path),
            supported=sum(x['evidence']['source']=='vlm' for x in decisions),
            differs_from_rule=sum(x['evidence']['differs_from_rule'] for x in decisions),
            min_candidate_mass=min(x['candidate_mass'] for x in result),blank_fallback=True,
            note='Development-view readout only; offline direction agreement is not navigation gain or human ground truth.')
        (out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary,indent=2))
    finally:client.close()
    if a.guard:guard(b)


if __name__=='__main__':main()
