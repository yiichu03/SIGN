#!/usr/bin/env python3
"""One-time, pre-outcome development/confirmation split for blocked episodes."""
import csv
import datetime
import gzip
import hashlib
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
HERE=ROOT/'logs/qwen_recovery_iteration_20261108'


def key(row):return row['scene_id'],str(row['episode_id'])


def ranked(rows,salt):
    return sorted(rows,key=lambda row:hashlib.sha256(('|'.join(key(row))+'|'+salt).encode()).hexdigest())


def balanced(rows,n,salt):
    buckets={scene:ranked([r for r in rows if r['scene_id']==scene],salt)
        for scene in sorted({r['scene_id'] for r in rows})}
    selected=[]
    while len(selected)<n:
        for scene in buckets:
            if buckets[scene]:selected.append(buckets[scene].pop(0))
            if len(selected)==n:break
        if not any(buckets.values()) and len(selected)<n:raise ValueError('Insufficient eligible episodes')
    return selected


def main():
    HERE.mkdir(exist_ok=True)
    assert not (HERE/'tasks.json').exists(),'Do not replace the pre-outcome split'
    previous=json.loads((ROOT/'logs/sign_inference_coverage256_20261108/qwen_active/tasks.json').read_text())
    data=json.loads(gzip.decompress(Path(previous['splits']['full']['path']).read_bytes()))['episodes']
    index={key(row):row for row in data};excluded=set()
    for name in ['logs/sign_inference_harness_20261107/tasks.json','logs/sign_inference_active_view_20261108/tasks.json']:
        for split,info in json.loads((ROOT/name).read_text())['splits'].items():
            if split!='full':excluded.update(map(tuple,info['episode_keys']))
    for row in csv.DictReader((ROOT/'logs/sign_failure_replay_20261104/analysis/review/human_review.csv').open()):
        excluded.add(key(row))
    diagnostics=list(csv.DictReader((ROOT/'logs/sign_failure_replay_20261104/analysis/failed_episodes.csv').open()))
    eligible=[row for row in diagnostics if row['case']=='coverage256' and row['success']=='0.0'
        and int(row['steps'])==500 and int(row['longest_blocked_run'])>=16 and key(row) not in excluded]
    available=[index[key(row)] for row in eligible];splits={};selection=[];used=set(excluded)
    for split in ['develop','confirm','reserve']:
        chosen=balanced([row for row in available if key(row) not in used],24,'blocked-campaign-v1-'+split)
        splits[split]=chosen;used.update(map(key,chosen))
        selection.extend(dict(split=split,scene_id=key(row)[0],episode_id=key(row)[1]) for row in chosen)
    reference={}
    folder=Path(previous['reference']['directory'])/'episodes'
    for p in folder.glob('*.jsonl'):
        for line in p.read_text().splitlines():
            row=json.loads(line);reference[key(row)]=row
    successes=[row for row in data if reference[key(row)]['success']==1 and key(row) not in used]
    splits['safety']=balanced(successes,28,'success-safety-v1');used.update(map(key,splits['safety']))
    splits['general']=balanced([row for row in data if key(row) not in used],112,'general-confirm-v1')
    used.update(map(key,splits['general']))
    result={k:v for k,v in previous.items() if k!='splits'}
    result.update(save_audit_traces=True,splits={},selection_recorded_at=datetime.datetime.now(
        datetime.timezone(datetime.timedelta(hours=8))).isoformat(timespec='seconds'),
        targeted_subset=True,target_selection='original full baseline failure at500 with longest_blocked_run>=16; prior smoke/pilot/human-review excluded',
        source_eligible_count=len(eligible),selection_uses_no_new_vlm_outcomes=True)
    for split,rows in splits.items():
        path=HERE/'datasets'/split/'val.json.gz';path.parent.mkdir(parents=True)
        path.write_bytes(gzip.compress(json.dumps({'episodes':rows},separators=(',',':')).encode(),mtime=0))
        result['splits'][split]=dict(path=str(path),sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
            episode_keys=[list(key(r)) for r in rows],episodes=len(rows))
    result['splits']['smoke']=previous['splits']['smoke'];result['splits']['full']=previous['splits']['full']
    (HERE/'tasks.json').write_text(json.dumps(result,indent=2)+'\n')
    (HERE/'selection.json').write_text(json.dumps(dict(excluded_keys=[list(k) for k in sorted(excluded)],
        eligibility_rows=eligible,targeted_selection=selection,development_labels_not_human_truth=True),indent=2)+'\n')
    print(json.dumps(dict(eligible=len(eligible),splits={k:v['episodes'] for k,v in result['splits'].items()}),indent=2))


if __name__=='__main__':main()
