"""Compare native unchanged frozen baseline, weight zero, and rollout coverage."""
import json
import math
import os
from pathlib import Path
import statistics
import subprocess
import sys
import time

import numpy as np
import torch
from tensorboard.backend.event_processing.event_accumulator import EventAccumulator

ROOT=Path('/scratch/e1538633/liuyi');TREE=ROOT/'SIGN-frozen-rollout-coverage';HERE=Path(__file__).resolve().parent
original=torch.load(str(TREE/'ckpt/nav_model.pth'),map_location='cpu')['state_dict']
rows=[]
for name,coverage,weight in [('baseline',False,0.),('coverage_zero',True,0.),('coverage',True,.1)]:
    output=TREE/'results/gibson_rollout_coverage_20261027'/name
    assert not output.exists(), 'Existing short-check output'
    env=os.environ.copy();env.update(PYTHONHASHSEED='0',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',PYTHONUNBUFFERED='1')
    exp='exp_config/ppo_imagenav_gibson.yaml,policy,reward,sensors'+(',rollout_coverage' if coverage else '')
    args=[sys.executable,'run_sim.py','--exp-config',exp,'--run-type','train','--model-dir',str(output),
          'habitat_baselines.num_environments','8','habitat_baselines.rl.ppo.num_steps','256',
          'habitat_baselines.rl.ddppo.pretrained_encoder','True',
          'habitat_baselines.rl.ddppo.pretrained_weights','ckpt/nav_model.pth',
          'habitat_baselines.rl.ddppo.train_encoder','False',
          'habitat_baselines.total_num_steps','40960.0','habitat_baselines.num_checkpoints','-1',
          'habitat_baselines.checkpoint_interval','20','habitat_baselines.log_interval','1']
    if coverage:args+=['habitat.task.observed_coverage.weight',str(weight)]
    start=time.monotonic();print('START',name,flush=True)
    with (HERE/(name+'.log')).open('w') as stream:
        subprocess.run(args,cwd=str(TREE),env=env,stdout=stream,stderr=subprocess.STDOUT,timeout=1800,check=True)
    events=EventAccumulator(str(output/'tb'),size_guidance={'scalars':0});events.Reload();tags=events.Tags()['scalars']
    assert all(math.isfinite(e.value) for tag in tags for e in events.Scalars(tag)), 'Nonfinite metric'
    fps=events.Scalars('perf/fps');assert len(fps)==20 and fps[-1].step==40960
    recent=fps[-11:];rate=statistics.median([(b.step-a.step)/(b.wall_time-a.wall_time) for a,b in zip(recent,recent[1:])])
    ckpt=torch.load(str(output/'ckpts/latest.pth'),map_location='cpu')
    encoder=[k for k in ckpt['state_dict'] if k.startswith('actor_critic.net.visual_encoder.')]
    assert len(encoder)==42 and all(torch.equal(ckpt['state_dict'][k],original[k]) for k in encoder)
    assert all(torch.isfinite(v).all() for v in ckpt['state_dict'].values())
    scalars={tag:[e.value for e in events.Scalars(tag)] for tag in tags}
    if weight>0:
        sums=np.array(scalars['learner/coverage_bonus_sum']);areas=np.array(scalars['learner/coverage_new_area_m2'])
        np.testing.assert_allclose(sums,.1*areas/256,rtol=2e-6,atol=1e-7)
        assert (areas>=0).all() and areas.sum()>0
    row={'case':name,'wall_seconds':time.monotonic()-start,'steps':40960,'updates':20,'steady_steps_per_second':rate,
         'all_finite':True,'encoder_unchanged_items':len(encoder),'command':args,'scalars':scalars}
    rows.append(row);(HERE/'short_results.json').write_text(json.dumps(rows,indent=2)+'\n')
    print('FINISH',name,rate,flush=True)
base=rows[0]['scalars'];zero=rows[1]['scalars']
for tag in base:
    np.testing.assert_allclose(zero[tag],base[tag],rtol=2e-5,atol=2e-6) if tag!='perf/fps' else None
summary={'passed':True,'cases':[{k:v for k,v in row.items() if k!='scalars'} for row in rows],
         'zero_weight_common_metrics_match_baseline':True,
         'coverage_measure_steady_time_overhead_fraction':rows[0]['steady_steps_per_second']/rows[1]['steady_steps_per_second']-1,
         'positive_coverage_total_logged_area_m2':sum(rows[2]['scalars']['learner/coverage_new_area_m2']),
         'positive_coverage_total_bonus':sum(rows[2]['scalars']['learner/coverage_bonus_sum']),
         'navigation_reward_log':'reward remains environment navigation reward; rollout bonus is learner/coverage_bonus_sum and learner/coverage_bonus_per_step.',
         'limitations':'Short performance/validity check, not convergence evidence. Positive reward changes later trajectories; zero-weight pairing is the overhead control.'}
(HERE/'short_summary.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary,indent=2),flush=True)
