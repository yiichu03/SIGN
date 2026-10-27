"""Evaluate immutable same-step snapshots with the existing native eval protocol."""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import sys
import time
import numpy as np
from tensorboard.backend.event_processing.event_accumulator import EventAccumulator

ROOT = Path('/scratch/e1538633/liuyi')
HERE = Path(__file__).resolve().parent
TREE = ROOT/'SIGN-frozen-rollout-coverage'
case = sys.argv[1]
assert case in ('baseline', 'coverage')
manifest = json.loads((HERE/'eval_manifest.json').read_text())
record = manifest['cases'][case]
checkpoint = Path(record['snapshot'])
assert hashlib.sha256(checkpoint.read_bytes()).hexdigest() == record['sha256']
assert os.environ.get('PYTHONHASHSEED') == '0'
subprocess.run([sys.executable, str(ROOT/'logs/gibson_rollout_coverage_20261027/check_inputs.py')], check=True, cwd=str(TREE))
data = json.loads((ROOT/'manifests/gibson_reproduction_20261026.json').read_text())['splits']['val']
for item in data['files']:
    assert hashlib.sha256((ROOT/item['path']).read_bytes()).hexdigest() == item['sha256']
for name in data['scenes']:
    mesh = TREE/'data/scene_datasets/gibson'/name
    assert mesh.is_file() and mesh.with_suffix('.navmesh').is_file()
output = HERE/('eval_'+case)
assert not output.exists(), 'Refuse to overwrite an evaluation'
command = [sys.executable, 'run_sim.py', '--exp-config',
           'exp_config/ppo_imagenav_gibson.yaml,policy,reward,sensors,eval',
           '--run-type', 'eval', '--model-dir', str(output),
           'habitat_baselines.eval_ckpt_path_dir', str(checkpoint)]
print('EXECUTING', json.dumps(command), flush=True)
started = time.time()
with (HERE/(case+'_eval.log')).open('w') as handle:
    completed = subprocess.run(command, cwd=str(TREE), stdout=handle, stderr=subprocess.STDOUT)
assert completed.returncode == 0, 'Native evaluation failed: '+str(completed.returncode)
ea = EventAccumulator(str(output/'tb'), size_guidance={'scalars': 0}); ea.Reload()
metrics = {tag: float(ea.Scalars(tag)[-1].value) for tag in ea.Tags()['scalars']}
assert metrics and all(np.isfinite(v) for v in metrics.values())
assert all(ea.Scalars(tag)[-1].step == 9216000 for tag in metrics)
text = (HERE/(case+'_eval.log')).read_text()
assert '4200/4200' in text
result = {'case': case, 'checkpoint': record, 'command': command,
          'elapsed_seconds': time.time()-started, 'metrics': metrics,
          'episodes_completed': 4200, 'pythonhashseed': 0, 'seed': 100,
          'num_environments': 6, 'max_episode_steps': 500,
          'note': 'Native deterministic evaluation; coverage disabled; common public safety model as in original eval.'}
(HERE/(case+'_eval_result.json')).write_text(json.dumps(result, indent=2)+'\n')
print(json.dumps(result,indent=2), flush=True)
