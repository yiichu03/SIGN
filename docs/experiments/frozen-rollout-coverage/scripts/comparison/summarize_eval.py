"""Summarize native full-val aggregates; do not infer significance from one seed."""
from pathlib import Path
from datetime import datetime, timezone, timedelta
import json
import sys
import yaml

HERE = Path(__file__).resolve().parent

def flat(value, prefix=''):
    if isinstance(value, dict):
        out = {}
        for k, v in value.items():
            out.update(flat(v, prefix+str(k)+'.'))
        return out
    return {prefix.rstrip('.'): value}

configs = {}
for case in ['baseline', 'coverage']:
    path = next((HERE/('eval_'+case)).glob('eval_run*/config_of_eval.yaml'))
    configs[case] = flat(yaml.safe_load(path.read_text()))
allowed = {'habitat_baselines.checkpoint_folder', 'habitat_baselines.eval_ckpt_path_dir',
           'habitat_baselines.tensorboard_dir', 'habitat_baselines.video_dir', 'habitat_baselines.log_file',
           'habitat_baselines.cmd_trailing_opts'}
for case, config in configs.items():
    assert config['habitat_baselines.cmd_trailing_opts'] == [
        'habitat_baselines.eval_ckpt_path_dir', config['habitat_baselines.eval_ckpt_path_dir']]
differences = {k: {'baseline': configs['baseline'].get(k), 'coverage': configs['coverage'].get(k)}
               for k in set(configs['baseline']) | set(configs['coverage'])
               if configs['baseline'].get(k) != configs['coverage'].get(k)}
assert set(differences) <= allowed, differences
base = configs['baseline']
assert base['habitat.seed'] == 100
assert base['habitat_baselines.num_environments'] == 6
assert base['habitat.environment.max_episode_steps'] == 500
assert base['habitat_baselines.test_episode_count'] == -1
assert 'observed_coverage' not in base['habitat.task.measurements']
(HERE/'eval_config_audit.json').write_text(json.dumps({'passed':True,'allowed_differences':differences},indent=2)+'\n')
if '--audit-only' in sys.argv:
    print('Evaluation configuration audit passed; differences only outputs, weight path and its CLI metadata.')
    raise SystemExit(0)

results = {case: json.loads((HERE/(case+'_eval_result.json')).read_text()) for case in configs}
assert all(r['episodes_completed'] == 4200 for r in results.values())
metrics = {}
for tag in results['baseline']['metrics']:
    a, b = (results[c]['metrics'][tag] for c in ['baseline', 'coverage'])
    metrics[tag] = {'baseline': a, 'coverage': b, 'coverage_minus_baseline': b-a}
record = {'recorded_at': datetime.now(timezone(timedelta(hours=8))).isoformat(timespec='seconds'),
          'matched_step':9216000, 'episodes_per_model':4200, 'metrics':metrics,
          'success_counts':{case:round(r['metrics']['eval_metrics/success']*4200) for case,r in results.items()},
          'evaluation_config_identical_except_outputs_and_weight_path':True,
          'training_seed_count':1,
          'limitations':['One training seed and one checkpoint pair; no across-seed causal claim.',
                         'Native evaluator saves aggregate statistics, not per-episode paired outcomes; no paired significance test.'],
          'elapsed_seconds':{case:r['elapsed_seconds'] for case,r in results.items()}}
(HERE/'full_val_comparison.json').write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps(record,indent=2))
