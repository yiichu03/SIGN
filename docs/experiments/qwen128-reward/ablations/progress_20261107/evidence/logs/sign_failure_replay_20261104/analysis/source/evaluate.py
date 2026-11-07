"""Original native evaluator, with passive telemetry as the only extension."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path('/scratch/e1538633/liuyi')
HERE = Path(__file__).resolve().parent
TREE = ROOT/'SIGN-coverage-eval'
os.chdir(TREE)
sys.path.insert(0, str(TREE))
sys.path.insert(0, str(HERE))
case, phase, mode = sys.argv[1:]
assert case in ['baseline', 'coverage256', 'coverage32']
assert phase in ['smoke', 'full'] and mode in ['control', 'diagnostic']
out = HERE/phase/case/mode
os.environ.update(DIAG_CASE=case, DIAG_PHASE=phase, DIAG_OUTPUT=str(out), COVERAGE_EVAL_EPISODES=str(out/'episodes'))
import run_sim
import control_recording_env
if mode == 'diagnostic':
    import diagnostic_env
from guard import guard


def main():
    # Forkserver imports this file as __mp_main__ in each environment worker.
    # Filesystem creation/preconditions belong to the parent entry point only.
    out.mkdir(parents=True, exist_ok=True)
    assert not (out/'native').exists(), 'Existing evaluation output'
    guard()
    if phase == 'full':
        smoke = json.loads((HERE/'smoke_passed.json').read_text())
        assert smoke['passive_control_matches_diagnostic']
    import numpy as np
    import torch
    from tensorboard.backend.event_processing.event_accumulator import EventAccumulator
    assert os.environ['PYTHONHASHSEED'] == '0' and os.environ.get('PBS_JOBID') and torch.cuda.is_available()
    manifest = json.loads((HERE/'manifest.json').read_text())['cases'][case]
    path = Path(manifest['path']);step = manifest['step']
    assert hashlib.sha256(path.read_bytes()).hexdigest() == manifest['sha256']
    ckpt = torch.load(path, map_location='cpu')
    assert ckpt['extra_state']['step'] == step
    env = 'FailureDiagnosticGym' if mode == 'diagnostic' else 'CoverageEvalGym'
    opts = ['habitat_baselines.eval_ckpt_path_dir', str(path), 'habitat.env_task', env,
            'habitat.task.observed_coverage.weight', '0.0']
    if phase == 'smoke':
        opts += ['habitat_baselines.test_episode_count', '28']
    started = time.time()
    run_sim.run_exp(exp_config='exp_config/ppo_imagenav_gibson.yaml,policy,reward,sensors,eval,rollout_coverage',
                     run_type='eval', opts=opts, model_dir=str(out/'native'), overwrite=False, note='', debug=False)
    rows = []
    for p in (out/'episodes').glob('*.jsonl'):
        rows.extend(json.loads(line) for line in p.read_text().splitlines())
    keys = {(r['scene_id'], r['episode_id']) for r in rows}
    assert len(keys) == len(rows)
    expected = {tuple(k) for k in json.loads((HERE/'eval_protocol.json').read_text())['episode_keys']}
    assert keys <= expected
    if phase == 'full':
        assert keys == expected and len(rows) == 4200
    else:
        assert 28 <= len(rows) <= 34
    assert all(np.isfinite(r[k]) for r in rows for k in ['success', 'spl', 'new_area_m2', 'navigation_reward'])
    ea = EventAccumulator(str(out/'native/tb'), size_guidance={'scalars': 0}).Reload()
    native = {tag:ea.Scalars(tag)[-1].value for tag in ea.Tags()['scalars']}
    assert all(np.isfinite(v) for v in native.values())
    assert abs(native['eval_metrics/success']-np.mean([r['success'] for r in rows])) < 1e-5
    assert abs(native['eval_metrics/spl']-np.mean([r['spl'] for r in rows])) < 1e-5
    result = dict(case=case, phase=phase, mode=mode, training_step=step, episodes=len(rows),
                  success_rate=float(np.mean([r['success'] for r in rows])), spl=float(np.mean([r['spl'] for r in rows])),
                  seconds=time.time()-started, native_metrics=native)
    if mode == 'diagnostic':
        diag = [json.loads(line) for p in (out/'diagnostics').glob('*.jsonl') for line in p.read_text().splitlines()]
        assert {(r['scene_id'],r['episode_id']) for r in diag} == keys and len(diag) == len(rows)
        assert all((out/r['trace']).exists() for r in diag)
        assert all((out/r['video']).exists() for r in diag if r['captured_images'])
        result.update(reference_pose_hash_matches=sum(r['reference_pose_hash_equal'] for r in diag),
                      reference_step_matches=sum(r['reference_steps_equal'] for r in diag),
                      reference_success_matches=sum(r['reference_success_equal'] for r in diag),
                      failures=sum(r['success']==0 for r in diag))
    guard()
    (out/'result.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
