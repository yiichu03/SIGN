"""Inspect a real resumed PPO update without starting another simulator."""
import hashlib
import json
import math
from pathlib import Path
import sys

import torch
import yaml
from tensorboard.backend.event_processing.event_accumulator import EventAccumulator

torch.set_num_threads(1)
HERE=Path(__file__).resolve().parent;case=sys.argv[1]
p=json.loads((HERE/'plan.json').read_text())[case]
out=Path(p['tree'])/'results/continuation_20261103'/case/'short'
before=torch.load(p['checkpoint'],map_location='cpu')
after=torch.load(str(out/'ckpts/latest.pth'),map_location='cpu')
assert after['extra_state']['step']==p['start_step']+4096
assert after['learner_state']['num_updates_done']==after['extra_state']['step']//2048
assert after['learner_state']['optimizer']['state']
keys=[k for k in before['state_dict'] if k.startswith('actor_critic.net.visual_encoder.')]
assert len(keys)==42 and all(torch.equal(before['state_dict'][k],after['state_dict'][k]) for k in keys)
assert all(torch.isfinite(v).all().item() for v in after['state_dict'].values())
assert any(not torch.equal(v,after['state_dict'][k]) for k,v in before['state_dict'].items() if k not in keys)
receipt=json.loads((out/'continuation.json').read_text())
assert receipt['mode']=='legacy_weights_optimizer_reset' and receipt['model_states_restored']==103
assert receipt['mrq_update_active']==(p['start_step']<50000000)
for k,v in before['state_dict'].items():assert hashlib.sha256(v.numpy().tobytes()).hexdigest()==receipt['initial_parameter_hashes'][k]
ea=EventAccumulator(str(out/'tb'),size_guidance={'scalars':0});ea.Reload()
streams={tag:ea.Scalars(tag) for tag in ea.Tags()['scalars']}
assert all(math.isfinite(v.value) for rows in streams.values() for v in rows)
assert [v.step for v in streams['metrics/success']]==[p['start_step']+2048,p['start_step']+4096]
assert after['extra_state']['wall_time']>before['extra_state']['wall_time']

def flat(value,prefix=''):
    if isinstance(value,dict):
        result={}
        for k,v in value.items():result.update(flat(v,prefix+str(k)+'.'))
        return result
    return {prefix[:-1]:value}
original=yaml.safe_load(next(Path(p['old_output']).glob('*run*/config_of_train.yaml')).read_text())
current=yaml.safe_load(next(out.glob('*run*/config_of_train.yaml')).read_text())
a,b=flat(original),flat(current)
allowed={'habitat_baselines.checkpoint_folder','habitat_baselines.tensorboard_dir','habitat_baselines.video_dir',
         'habitat_baselines.log_file','habitat_baselines.eval_ckpt_path_dir','habitat_baselines.cmd_trailing_opts',
         'habitat_baselines.checkpoint_interval','habitat_baselines.log_interval','qwen_reward.verify_first_batch'}
diff={k:[a.get(k),b.get(k)] for k in set(a)|set(b) if a.get(k)!=b.get(k)}
unexpected={k:v for k,v in diff.items() if k not in allowed and not k.startswith('training_continuation.')}
assert not unexpected,unexpected
assert current['habitat_baselines']['total_num_steps']==300000000
reward_audit={}
if case in ['qwen01','A','B','C']:
    rows=[json.loads(line) for line in (out/'qwen/rollouts.jsonl').read_text().splitlines()]
    assert [r['rollout_id'] for r in rows]==[0,1]
    prefix='geometry' if case=='C' else 'qwen'
    for r in rows:
        assert r['nav_rewards_unchanged'] and r['masks_unchanged']
        m=r['metrics'];assert abs(m[prefix+'_mixed_reward_sum']-m[prefix+'_nav_reward_sum']-m[prefix+'_bonus_sum'])<1e-4
    if case=='C':assert not (out/'qwen/worker_boot.json').exists()
    else:
        assert json.loads((out/'qwen/worker_boot.json').read_text())['environment']['dtype']=='torch.float32'
        assert json.loads((out/'qwen/verification.json').read_text())['passed']
    reward_audit={'nav_rewards_and_masks_unchanged':True,'local_rollouts':[0,1],
        'cumulative_rollout_offset':receipt['qwen_local_rollout_offset']}
else:
    area=streams['learner/coverage_new_area_m2'];bonus=streams['learner/coverage_bonus_sum']
    assert all(abs(b.value-.1*a.value/256)<1e-6 for a,b in zip(area,bonus))
    reward_audit={'coverage_bonus_conservation':True}
report=dict(passed=True,case=case,start_step=p['start_step'],end_step=after['extra_state']['step'],
    added_steps=4096,encoder_unchanged_items=len(keys),all_model_and_scalars_finite=True,
    initial_model_exactly_restored=True,original_hyperparameters_preserved=True,
    optimizer_state_saved=True,qc_optimizer_state_entries=len(after['learner_state']['qc_optimizer']['state']),
    global_300m_cap_preserved=True,config_differences=diff,reward_audit=reward_audit,
    latest={tag:streams[tag][-1].value for tag in ['metrics/success','metrics/spl','learner/value_loss']})
(HERE/case/'short_validation.json').write_text(json.dumps(report,indent=2)+'\n')
print('PASSED',case,report['start_step'],report['end_step'],flush=True)
