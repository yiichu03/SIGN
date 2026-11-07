#!/usr/bin/env python3
"""Freeze task splits before observing inference-harness results (CPU only)."""
import argparse
import csv
import gzip
import hashlib
import json
from pathlib import Path

ROOT = Path('/scratch/e1538633/liuyi')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    out = args.output.resolve()
    assert not (out/'tasks.json').exists()
    source = ROOT/'SIGN/data/datasets/imagenav/gibson/v1/val/val.json.gz'
    episodes = json.loads(gzip.decompress(source.read_bytes()))['episodes']
    key = lambda r: (r['scene_id'], str(r['episode_id']))
    excluded = {(r['scene_id'], r['episode_id']) for r in csv.DictReader((ROOT/'logs/sign_failure_replay_20261104/analysis/review/human_review.csv').open())}
    notes = json.loads((ROOT/'logs/sign_failure_replay_20261104/analysis/ai_case_notes.json').read_text())['cases']
    preferred = set()
    for name in notes:
        if name.startswith('baseline_'):
            _, scene, episode = name.split('_')
            preferred.add(('data/scene_datasets/gibson/'+scene+'.glb', episode))
    scenes = sorted({r['scene_id'] for r in episodes})
    rank = lambda r: hashlib.sha256(('|'.join(key(r))+'|harness-v1').encode()).hexdigest()
    smoke, pilot = [], []
    for scene in scenes:
        rows = [r for r in episodes if r['scene_id'] == scene]
        chosen = sorted(rows, key=lambda r: (key(r) not in preferred, rank(r)))[:2]
        smoke.extend(chosen)
        candidates = [r for r in rows if key(r) not in excluded and key(r) not in {key(x) for x in chosen}]
        pilot.extend(sorted(candidates, key=rank)[:20])
    assert len(smoke) == 28 and len(pilot) == 280 and len(scenes) == 14
    assert not {key(r) for r in pilot} & (excluded | {key(r) for r in smoke})
    splits = {}
    for name, rows in [('smoke', smoke), ('pilot', pilot)]:
        folder = out/'datasets'/name
        folder.mkdir(parents=True)
        path = folder/'val.json.gz'
        path.write_bytes(gzip.compress(json.dumps({'episodes':rows}, separators=(',', ':')).encode(), mtime=0))
        splits[name] = dict(path=str(path), sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                            episode_keys=[list(key(r)) for r in rows], episodes=len(rows))
    splits['full'] = dict(path=str(source), sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
                          episode_keys=[list(key(r)) for r in episodes], episodes=len(episodes))
    checkpoint = json.loads((ROOT/'logs/gibson_baseline_final_eval_20261103/manifest.json').read_text())['cases']['baseline']
    output = dict(splits=splits, checkpoint=checkpoint, excluded_review_tasks=[list(k) for k in sorted(excluded)],
        selection='Scene-balanced fixed SHA ranking; pilot excludes prior purposeful review and smoke tasks. Reused Gibson val, not a new independent benchmark.')
    (out/'tasks.json').write_text(json.dumps(output, indent=2)+'\n')
    print(json.dumps({name:v['episodes'] for name,v in splits.items()}))


if __name__ == '__main__':
    main()
