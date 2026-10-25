#!/usr/bin/env python3
"""Verify selected factual claims against existing pose/collision records."""
import json,math
from qwen_prompt_search import ROOT,DATA

rows=[]
for case,start,claim in [
 ('val_hard/episode_007',7,'p12 JSON calls this a sustained 360-degree sweep; p13 combined calls it 0-to-2pi sweeps.'),
 ('val_hard/episode_017',50,'p12 JSON and p13 combined describe repeated full 360-degree sweeps during the prolonged trapped segment.'),
 ('val_hard/episode_015',46,'p12 JSON describes multiple full 360-degree heading sweeps during the trapped interval.'),
 ('val_medium/episode_012',52,'p12 JSON/p13 combined acknowledge trapping but still count the same interval as repeated search.')]:
 w=[p for p in json.loads((DATA/case/'waypoints_corrected.json').read_text())['waypoints'] if p['step']>=start]
 unwrapped=[w[0]['heading_rad']]
 increments=[]
 for x,y in zip(w,w[1:]):
  delta=(y['heading_rad']-x['heading_rad']+math.pi)%(2*math.pi)-math.pi
  increments.append(delta);unwrapped.append(unwrapped[-1]+delta)
 rows.append(dict(case=case,interval=[start,w[-1]['step']],claim_to_check=claim,recorded_samples=len(w),collision_samples=sum(p['collision'] for p in w),distinct_integer_positions=len({(p['map_row'],p['map_col']) for p in w}),heading_excursion_deg=(max(unwrapped)-min(unwrapped))*180/math.pi,max_step_heading_change_deg=max(map(abs,increments))*180/math.pi,method='Unwrap adjacent recorded headings modulo 2*pi, then take max-min (not sum of absolute turns or net turn). This audits a claim, not a redundancy classifier or relabeling rule.',scope_note='Repeated visual search versus failed control requires review. An explicit recovery description alone cannot justify a search-positive label under the user scope.'))
w=json.loads((DATA/'val_medium/episode_011/waypoints_corrected.json').read_text())['waypoints']
rows.append(dict(case='val_medium/episode_011',claim_to_check='p12 JSON says no collisions or recovery behaviors observed.',collision_samples=sum(p['collision'] for p in w),collision_steps=[p['step'] for p in w if p['collision']],note='The no-collision factual statement is false regardless of the redundancy label.'))
(ROOT/'evidence_audit.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n')
print('Saved',len(rows),'factual/scope audit cases; no human labels changed.')
