#!/usr/bin/env python3
"""Thin launcher around the native evaluator and existing passive telemetry."""
import argparse
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import statistics
import subprocess
import sys
import time
TREE = Path(__file__).resolve().parents[1]
ROOT = TREE.parent
EVAL_TREE = ROOT/'SIGN-coverage-eval' if os.environ.get('RECOVERY_NATIVE_REFERENCE') == '1' else TREE
sys.path.insert(0, str(EVAL_TREE))
sys.path.insert(0, str(TREE/'scripts'))
# Forkserver children re-import this module without calling main(). Register
# simulator, dataset, actions and the telemetry environment in every process.
import run_sim
import recovery_env
from recovery_checkpoint import validate_checkpoint


def read_rows(folder):
    rows = {}
    for path in sorted(folder.glob('*.jsonl')):
        for line in path.read_text().splitlines():
            r = json.loads(line)
            key = (r['scene_id'], r['episode_id'])
            assert key not in rows, key
            rows[key] = r
    return rows


def guard(batch):
    source = json.loads((batch/'source_manifest.json').read_text())
    assert subprocess.check_output(['git','-C',str(TREE),'rev-parse','HEAD'], text=True).strip() == source['commit']
    for name, digest in source['files'].items():
        assert hashlib.sha256((TREE/name).read_bytes()).hexdigest() == digest, name
    for name, digest in source['assets'].items():
        assert hashlib.sha256(Path(name).read_bytes()).hexdigest() == digest, name
    for name, item in source.get('protected_trees', {}).items():
        tree = ROOT/name
        assert subprocess.check_output(['git','-C',str(tree),'rev-parse','HEAD'],text=True).strip() == item['commit']
        for relative,digest in item['files'].items():
            assert hashlib.sha256((tree/relative).read_bytes()).hexdigest() == digest, (name,relative)
    path = ROOT/'logs/gibson_coverage32_selected_eval_20261107/guard.py'
    spec = importlib.util.spec_from_file_location('original_runtime_guard', path)
    module = importlib.util.module_from_spec(spec);spec.loader.exec_module(module);module.guard()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--batch', type=Path, required=True)
    parser.add_argument('--run', type=Path, required=True)
    parser.add_argument('--split', choices=['smoke','pilot','full','develop','confirm','reserve','safety','general'], required=True)
    parser.add_argument('--mode', choices=['off','disabled','rule','qwen','scan'], required=True)
    parser.add_argument('--active', action='store_true')
    parser.add_argument('--candidate', action='store_true')
    args = parser.parse_args()
    batch, out = args.batch.resolve(), args.run.resolve()
    guard(batch)
    assert os.environ.get('PBS_JOBID') and os.environ.get('PYTHONHASHSEED') == '0'
    assert not out.exists(), out
    out.mkdir(parents=True)
    tasks = json.loads((batch/'tasks.json').read_text())
    selected, checkpoint = tasks['splits'][args.split], tasks['checkpoint']
    os.chdir(EVAL_TREE)
    import torch
    from tensorboard.backend.event_processing.event_accumulator import EventAccumulator
    assert torch.cuda.is_available()
    model = torch.load(checkpoint['path'], map_location='cpu')
    reference_dir = validate_checkpoint(tasks, model['extra_state']['step'])
    del model
    os.environ['COVERAGE_EVAL_EPISODES'] = str(out/'episodes')
    if args.active and args.split == 'smoke' and args.mode == 'scan':
        os.environ['RECOVERY_VIEW_AUDIT'] = str(out/'audit_traces')
    if tasks.get('save_audit_traces',False):
        os.environ['RECOVERY_VIEW_AUDIT'] = str(out/'audit_traces')
    if args.split == 'smoke' and args.mode == 'off':
        os.environ['RECOVERY_PROBE_IMAGES'] = str(out/'probe_images')
    opts = ['habitat_baselines.eval_ckpt_path_dir', checkpoint['path'],
        'habitat.env_task','CoverageEvalGym', 'habitat.task.observed_coverage.weight','0.0',
        'habitat.dataset.data_path',selected['path'], 'habitat_baselines.test_episode_count',str(selected['episodes']),
        'inference_recovery.mode', 'qwen' if args.mode == 'disabled' else args.mode]
    diagnostic_envs=tasks.get('diagnostic_num_envs') if args.split!='full' else None
    if diagnostic_envs is not None:
        if diagnostic_envs!=1:
            raise ValueError('Causal diagnostics support exactly one environment')
        opts += ['habitat_baselines.num_environments','1']
    if args.mode == 'disabled':
        opts += ['inference_recovery.max_interventions','0']
    started = time.perf_counter()
    exp_config = 'exp_config/ppo_imagenav_gibson.yaml,policy,reward,sensors,eval,rollout_coverage,'+str(TREE/'src/config/inference_recovery.yaml')
    if args.active:
        exp_config += ','+str(TREE/'src/config/inference_active_view.yaml')
    if args.candidate:
        assert args.active
        exp_config += ','+str(TREE/'src/config/inference_candidate.yaml')
    if tasks.get('recovery_profile'):
        exp_config += ','+str(TREE/tasks['recovery_profile'])
    run_sim.run_exp(exp_config=exp_config,
        run_type='eval', opts=opts, model_dir=str(out/'native'), overwrite=False, note='', debug=False)
    rows = read_rows(out/'episodes')
    assert set(rows) == {tuple(k) for k in selected['episode_keys']}
    for row in rows.values():
        assert 1 <= row['steps'] <= 500
        assert all(math.isfinite(row[k]) for k in ['success','spl','collisions','new_area_m2','navigation_reward'])
    ref = read_rows(reference_dir/'episodes')
    pose_matches = 0
    for key, row in rows.items():
        reference = ref[key]
        assert row['goal_sha256'] == reference['goal_sha256']
        assert max(abs(a-b) for a,b in zip(row['start_position'],reference['start_position'])) < 1e-6
        pose_matches += row['pose_trace_sha256'] == reference['pose_trace_sha256']
        # Filtered datasets require a native reference on the SAME subset.
        if args.mode == 'off' and args.split == 'full':
            for name in ['success','spl','view_match','navigation_reward','collisions','steps']:
                assert abs(row[name]-reference[name]) < 1e-5, (key,name,row[name],reference[name])
    ea = EventAccumulator(str(out/'native/tb'), size_guidance={'scalars':0});ea.Reload()
    native = {tag:ea.Scalars(tag)[-1].value for tag in ea.Tags()['scalars']}
    result = dict(mode=args.mode, split=args.split, training_step=checkpoint['step'],
        checkpoint_sha256=checkpoint['sha256'], checkpoint_path=checkpoint['path'], reference=tasks['reference'],
        episodes=len(rows), scenes=len({key[0] for key in rows}),
        success_rate=statistics.mean(r['success'] for r in rows.values()), spl=statistics.mean(r['spl'] for r in rows.values()),
        view_match=statistics.mean(r['view_match'] for r in rows.values()),
        mean_collisions=statistics.mean(r['collisions'] for r in rows.values()),
        mean_episode_steps=statistics.mean(r['steps'] for r in rows.values()),
        new_m2_per_step_global=sum(r['new_area_m2'] for r in rows.values())/sum(r['steps'] for r in rows.values()),
        native_metrics=native, seconds=time.perf_counter()-started, original_pose_sha_matches=pose_matches,
        matched_goals_and_starts=True, controller_inputs=['rgb','target_rgb','executed_action_history'],
        native_reference=os.environ.get('RECOVERY_NATIVE_REFERENCE') == '1',
        subset_full_reference_outputs_not_assumed_equal=args.split!='full',
        max_episode_steps=500, seed=100, hash_seed=0, source_commit=json.loads((batch/'source_manifest.json').read_text())['commit'])
    result['diagnostic_num_envs']=diagnostic_envs
    result['full_evaluation_parallelism_unchanged']=True
    assert abs(native['eval_metrics/success']-result['success_rate']) < 1e-5
    assert abs(native['eval_metrics/spl']-result['spl']) < 1e-5
    recovery = out/'native/recovery'
    if args.mode != 'off':
        records = [json.loads(line) for line in (recovery/'episodes.jsonl').read_text().splitlines()]
        assert len(records) == len(rows)
        assert len({tuple(r['episode']) for r in records}) == len(records)
        summary = json.loads((recovery/'summary.json').read_text())
        for r in records:
            assert r['steps'] == rows[tuple(r['episode'])]['steps']
            assert r['actions_sha256'] == rows[tuple(r['episode'])]['actual_actions_sha256'], 'Executed action feedback mismatch'
            assert r['attempts'] <= 2 and r['overrides'] <= summary['max_override_steps']
            assert r['overrides'] == r['survey_steps']+r['recovery_steps']
        result['harness'] = dict(attempts=sum(r['attempts'] for r in records), overrides=sum(r['overrides'] for r in records),
            rejected=sum(r['rejected'] for r in records), survey_steps=sum(r['survey_steps'] for r in records),
            recovery_steps=sum(r['recovery_steps'] for r in records), completed_surveys=sum(r['completed_surveys'] for r in records),
            selections={label:sum(r['selections'][label] for r in records) for label in 'ABC'}, **summary)
        for name in ['vlm_selections', 'fallback_selections', 'vlm_rule_disagreements']:
            result['harness'][name] = sum(r.get(name, 0) for r in records)
        if args.mode == 'disabled':
            assert not result['harness']['worker_started'] and result['harness']['overrides'] == 0
    elif recovery.exists():
        raise RuntimeError('Disabled supervisor created output')
    guard(batch)
    (out/'result.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
