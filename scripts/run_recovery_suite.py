#!/usr/bin/env python3
"""One PBS GPU, sequential paired controls. Never starts navigation training."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace
TREE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TREE))
sys.path.insert(0, str(TREE/'scripts'))
from evaluate_recovery import read_rows, guard


def run_case(batch, stage, split, mode):
    out = batch/stage/(split+'_'+mode)
    out.parent.mkdir(parents=True, exist_ok=True)
    log = out.with_suffix('.log')
    command = [sys.executable, str(TREE/'scripts/evaluate_recovery.py'), '--batch', str(batch),
        '--run', str(out), '--split', split, '--mode', mode]
    print('RUN', json.dumps(command), flush=True)
    with log.open('x') as f:
        subprocess.run(command, cwd=TREE, stdout=f, stderr=subprocess.STDOUT, check=True)
    return out


def compare(batch, stage, split):
    folders = {mode:batch/stage/(split+'_'+mode) for mode in ['off','rule','qwen']}
    results = {mode:json.loads((folder/'result.json').read_text()) for mode,folder in folders.items()}
    rows = {mode:read_rows(folder/'episodes') for mode,folder in folders.items()}
    baseline = rows['off']
    paired = {}
    for mode in ['rule','qwen']:
        assert set(rows[mode]) == set(baseline)
        for key,row in rows[mode].items():
            ref = baseline[key]
            assert row['goal_sha256'] == ref['goal_sha256']
            assert max(abs(a-b) for a,b in zip(row['start_position'],ref['start_position'])) < 1e-6
        paired[mode] = dict(rescued=sum(not baseline[k]['success'] and r['success'] for k,r in rows[mode].items()),
            harmed=sum(baseline[k]['success'] and not r['success'] for k,r in rows[mode].items()),
            sr_delta_pp=100*(results[mode]['success_rate']-results['off']['success_rate']),
            spl_delta_pp=100*(results[mode]['spl']-results['off']['spl']))
    report = dict(split=split, cases=results, paired=paired,
        source_commit=results['off']['source_commit'], all_episodes_and_goals_paired=True,
        small_screen_only=split!='full', note='Reused Gibson val; fixed decisions before this screen, not an independent unseen benchmark.')
    (batch/stage/(split+'_comparison.json')).write_text(json.dumps(report, indent=2)+'\n')
    import csv
    with (batch/stage/(split+'_comparison.csv')).open('w') as f:
        fields = ['mode','episodes','success_rate','spl','view_match','mean_collisions','mean_episode_steps','new_m2_per_step_global','seconds']
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction='ignore');writer.writeheader()
        writer.writerows(results.values())
    return report


def probe_worker(batch, stage, smoke):
    from PIL import Image
    import yaml
    from src.qwen_client import QwenClient
    cfg = SimpleNamespace(**yaml.safe_load((TREE/'src/config/inference_recovery.yaml').read_text())['inference_recovery'])
    out = batch/stage/'worker_probe'
    out.mkdir()
    sources = sorted((smoke/'probe_images').glob('*.png'))
    assert len(sources) >= 3
    rows = []
    for i, source in enumerate(sources[:3]):
        image = out/f'input_{i}.png'
        with Image.open(source) as frame:
            frame.resize([(256,256),(512,256),(512,512)][i]).save(image)
        rows.append(dict(id=f'probe_{i}', image=str(image), image_sha256=hashlib.sha256(image.read_bytes()).hexdigest()))
    client = QwenClient(cfg, out/'worker')
    try:
        result = client.score(0, rows)
        assert [r['id'] for r in result['results']] == [r['id'] for r in rows]
        audit = json.loads((out/'worker/verification.json').read_text())
        assert audit['passed'] and len(set(audit['padding_counts'])) > 1
        result.update(purpose='Technical token/padding/batch check on resized real RGB; not semantic recovery accuracy', passed=True)
        (out/'result.json').write_text(json.dumps(result, indent=2)+'\n')
    finally:
        client.close()


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--batch', type=Path, required=True)
    p.add_argument('--stage', required=True)
    p.add_argument('--full', action='store_true')
    a = p.parse_args();batch = a.batch.resolve()
    assert os.environ.get('PBS_JOBID') and os.environ.get('PYTHONHASHSEED') == '0'
    guard(batch)
    target = batch/a.stage
    assert not target.exists(), target
    target.mkdir()
    if a.full:
        pilot = json.loads((batch/'pilot/pilot_comparison.json').read_text())
        assert pilot['all_episodes_and_goals_paired']
        assert (batch/'pilot/quality_gate.json').exists()
        assert json.loads((batch/'pilot/quality_gate.json').read_text())['passed']
        for mode in ['off','rule','qwen']:
            run_case(batch, a.stage, 'full', mode)
        compare(batch, a.stage, 'full')
    else:
        off = run_case(batch, a.stage, 'smoke', 'off')
        disabled = run_case(batch, a.stage, 'smoke', 'disabled')
        original, zero = read_rows(off/'episodes'), read_rows(disabled/'episodes')
        assert original == zero, 'Zero-intervention eval is not exactly native-equivalent'
        probe_worker(batch, a.stage, off)
        for mode in ['rule','qwen']:
            run_case(batch, a.stage, 'smoke', mode)
        for mode in ['off','rule','qwen']:
            run_case(batch, a.stage, 'pilot', mode)
        report = compare(batch, a.stage, 'pilot')
        # This is a predeclared regression screen, not a statistical efficacy claim.
        checks = dict(zero_intervention_exact=True, real_worker_readout=True, task_goal_start_pairing=True,
            rule_triggered=report['cases']['rule']['harness']['attempts'] > 0,
            qwen_triggered=report['cases']['qwen']['harness']['attempts'] > 0,
            no_large_sr_regression=all(report['paired'][m]['sr_delta_pp'] >= -2 for m in ['rule','qwen']),
            no_large_spl_regression=all(report['paired'][m]['spl_delta_pp'] >= -2 for m in ['rule','qwen']))
        (target/'quality_gate.json').write_text(json.dumps(dict(passed=all(checks.values()), checks=checks,
            note='Screen only. No significance claim or threshold tuning on these 280 tasks.'), indent=2)+'\n')
    guard(batch)
    print('SUITE COMPLETE', a.stage, flush=True)


if __name__ == '__main__':
    main()
