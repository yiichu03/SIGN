#!/usr/bin/env python3
"""Freeze ten tasks independently of outcomes; eight stochastic trials per task."""
import gzip
import hashlib
import json
import random
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
OUT = BASE / 'results/qwen_diagnostic/group8_p12'

def main():
    OUT.mkdir(exist_ok=True)
    if (OUT/'manifest.json').exists():
        raise SystemExit('Manifest already exists; use the frozen tasks.')
    source = json.loads((BASE/'results/qwen_diagnostic/additional120/manifest.json').read_text())
    rng = random.Random(20261013)
    groups = []
    scenes = sorted(source['scenes'])
    rng.shuffle(scenes)
    for i, scene in enumerate(scenes):
        split = ('val_easy','val_medium','val_hard')[i % 3]
        pool = [x for x in source['episodes'] if x['split']==split and Path(x['scene_id']).name==scene]
        selected = rng.choice(pool)
        ds = json.load(gzip.open(BASE/'results/qwen_diagnostic/additional120/datasets'/split/(split+'.json.gz'),'rt'))
        ep = next(e for e in ds['episodes'] if e['scene_id']==selected['scene_id'] and str(e['episode_id'])==selected['episode_id'])
        gid = f'group_{i+1:02d}'
        folder = OUT/gid
        folder.mkdir()
        with gzip.open(folder/'task.json.gz','wt') as f:
            json.dump({'episodes':[ep]},f)
        groups.append(dict(group=gid,split=split,task=ep,seed=20261013+i,rollouts=8))
    manifest = dict(groups=groups,selection_seed=20261013,selection='One of the previously sampled tasks in each of ten scenes; cyclic difficulty 4/3/3; no outcome or redundancy filtering.',checkpoint=str(BASE/'ckpt/nav_model.pth'),checkpoint_sha256=source['checkpoint_sha256'],safety_checkpoint_sha256=hashlib.sha256((BASE/'ckpt/safety_model.pth').read_bytes()).hexdigest(),policy='Frozen SIGN checkpoint; sample native action distribution; reset recurrent state each episode; no learning.',pythonhashseed=100,qwen='Unchanged p12; JSON only; eight independent prompts in each same-task batch; NONE/SOME/CLEAR -> redundancy 0/1/2; UNCERTAIN/invalid remains missing; no forced tie-breaking.',review='Independent AI review, not human ground truth. Review before reading Qwen outputs. This is an offline reward diagnostic, not PPO or GRPO training.')
    (OUT/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    print([(x['group'],x['split'],Path(x['task']['scene_id']).name,x['task']['episode_id']) for x in groups])

if __name__=='__main__':main()
