#!/usr/bin/env python3
"""Fixed, outcome-independent sampling of 120 episodes in ten unseen scenes."""
import gzip
import hashlib
import json
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'results/qwen_diagnostic/additional120'

def main():
    if (OUT/'manifest.json').exists():
        raise SystemExit('Sampling manifest already exists; reuse it instead of resampling.')
    rng = random.Random(20261001)
    seen = set()
    for p in (ROOT/'results/qwen_diagnostic').glob('**/waypoints.json'):
        seen.add(Path(json.loads(p.read_text())['scene_id']).name)
    pools = {}
    for split in ('val_easy','val_medium','val_hard'):
        pools[split] = {}
        for p in sorted((ROOT/'data/datasets/imagenav/hm3d/v1'/split/'content').glob('*.json.gz')):
            eps = json.load(gzip.open(p,'rt'))['episodes']
            scene = Path(eps[0]['scene_id']).name
            local = ROOT/'data/scene_datasets'/eps[0]['scene_id'].replace('hm3d/val/','hm3d/')
            if scene not in seen and len(eps) >= 4 and local.is_file() and local.with_suffix('.navmesh').is_file():
                pools[split][scene] = eps
    eligible = sorted(set.intersection(*(set(v) for v in pools.values())))
    scenes = sorted(rng.sample(eligible, 10))
    entries = []
    for split, pool in pools.items():
        chosen = []
        for scene in scenes:
            selected = rng.sample(pool[scene],4)
            chosen.extend(selected)
            for i,e in enumerate(selected):
                entries.append(dict(split=split,scene_id=e['scene_id'],episode_id=str(e['episode_id']),review_round=1 if i<2 else 2))
        folder = OUT/'datasets'/split
        folder.mkdir(parents=True,exist_ok=True)
        with gzip.open(folder/(split+'.json.gz'),'wt') as f:
            json.dump({'episodes':chosen},f)
    ckpt = ROOT/'ckpt/nav_model.pth'
    manifest = dict(seed=20261001,episodes=entries,scenes=scenes,excluded_scenes=sorted(seen),eligible_scenes=len(eligible),checkpoint=str(ckpt),checkpoint_sha256=hashlib.sha256(ckpt.read_bytes()).hexdigest(),sampling='Ten new scenes; four random episodes per difficulty per scene; no outcome filtering',rgb_interval=25)
    (OUT/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:v for k,v in manifest.items() if k!='episodes'},indent=2))

if __name__ == '__main__':
    main()
