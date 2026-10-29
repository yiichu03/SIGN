"""Validate actual40960-step GPU outputs before fresh formal submission."""
import csv,hashlib,json,math,sys
from pathlib import Path
import numpy as np
import torch
import yaml
from tensorboard.backend.event_processing.event_accumulator import EventAccumulator
ROOT=Path('/scratch/e1538633/liuyi');HERE=Path(__file__).resolve().parent;TREE=ROOT/'SIGN-qwen-ablation'
case=sys.argv[1];assert case in ['A','B','C'];OUT=TREE/'results/qwen_ablation_20261029'/case/'short_40960';audit=OUT/'qwen'
checkpoint=torch.load(str(OUT/'ckpts/latest.pth'),map_location='cpu');assert checkpoint['extra_state']['step']==40960
public=torch.load(str(ROOT/'SIGN/ckpt/nav_model.pth'),map_location='cpu')['state_dict'];state=checkpoint['state_dict']
encoder=[k for k in state if k.startswith('actor_critic.net.visual_encoder.')]
assert len(encoder)==42 and all(torch.equal(state[k],public[k]) for k in encoder)
assert all(torch.isfinite(v).all().item() for v in state.values())
initial=json.loads((audit/'initial_parameter_hashes.json').read_text());old=json.loads((ROOT/'SIGN-qwen128-reward/results/qwen128_reward_20261029/short_qwen_40960/qwen/initial_parameter_hashes.json').read_text())
assert initial==old,'Not the original random initialization outside encoder'
fc='actor_critic.net.visual_fc.1.weight'
assert initial[fc]!=hashlib.sha256(state[fc].numpy().tobytes()).hexdigest()
cfg=yaml.safe_load((audit/'effective_config.yaml').read_text());assert cfg['habitat_baselines']['rl']['data_augmentation']['mrq_reward_target']=='navigation'
qcfg=cfg['qwen_reward'];H=256;interval=256 if case=='B' else 128;assert qcfg['settlement_interval']==interval
assert cfg['habitat_baselines']['num_environments']==8 and cfg['habitat_baselines']['rl']['ppo']['num_steps']==256
assert cfg['habitat']['seed']==100 and cfg['habitat']['task']['observed_coverage']['weight']==0
assert (qcfg['meters_per_pixel'],qcfg['visibility_dist'],qcfg['fov'])==(.025,3.,90.)
rollouts=[json.loads(s) for s in (audit/'rollouts.jsonl').read_text().splitlines()]
segments=[json.loads(s) for s in (audit/'segments.jsonl').read_text().splitlines()]
assert len(rollouts)==20 and [r['rollout_id'] for r in rollouts]==list(range(20))
assert len({s['segment_id'] for s in segments})==len(segments)
valid=[s for s in segments if s['valid_geometry']];assert valid
prefix='geometry' if case=='C' else 'qwen';calibration=json.loads((TREE/'docs/experiments/qwen128-reward/ablations/calibration/calibration.json').read_text())
for s in valid:
    L=s['action_count'];area=s['metadata']['new_area_m2'];assert L==s['end']-s['start']==s['global_end']-s['global_start'] and 0<L<=interval
    assert s['end_row']==(s['global_end']-1)%256
    if not s['terminal']:assert s['global_end']%interval==0
    if case=='C':
        assert 'result' not in s and 'q' not in s and s['reward_source']=='geometry'
        expected=calibration['alpha']*area/256
    else:
        result=s['result'];q=result['q'];assert result['valid'] and 0<=q<=1
        assert abs(q-.5*result['p_medium']-result['p_high'])<1e-12
        assert abs(sum(result[k] for k in ['p_low','p_medium','p_high'])-1)<1e-12
        expected=.03*L/256*q
    assert abs(expected-s['bonus'])<1e-12
for s in segments:
    if not s['valid_geometry']:assert s['geometry_reason'] and 'bonus' not in s
for r in rollouts:
    m=r['metrics'];assert r['nav_rewards_unchanged'] and r['masks_unchanged']
    assert abs(m[prefix+'_mixed_reward_sum']-m[prefix+'_nav_reward_sum']-m[prefix+'_bonus_sum'])<1e-4
    assert abs(m[prefix+'_bonus_sum']-sum(s['bonus'] for s in valid if s['rollout_id']==r['rollout_id']))<1e-12
    assert 'exploration_segment_length_mean' in m and 'exploration_bonus_p90' in m
    if case=='C':assert m['geometry_render_seconds']==0 and m['geometry_worker_seconds']==0
if case=='C':
    assert not (audit/'worker.log').exists() and not list(audit.rglob('*.png'))
    assert not (audit/'worker_boot.json').exists() and qcfg['enabled'] is False and qcfg['beta']==0
    verification=None
else:
    verification=json.loads((audit/'verification.json').read_text());assert verification['passed']
    assert json.loads((audit/'worker_boot.json').read_text())['environment']['dtype']=='torch.float32'
ea=EventAccumulator(str(OUT/'tb'),size_guidance={'scalars':0});ea.Reload()
scalars={tag:ea.Scalars(tag) for tag in ea.Tags()['scalars']};assert all(math.isfinite(e.value) for rows in scalars.values() for e in rows)
assert len(scalars['perf/fps'])==20 and scalars['perf/fps'][-1].step==40960
times=np.diff([e.wall_time for e in scalars['perf/fps']]);bonuses=np.array([s['bonus'] for s in valid]);lengths=np.array([s['action_count'] for s in segments])
with (HERE/case/'short_gpu.csv').open() as f:gpu=list(csv.reader(f))[1:]
report=dict(passed=True,case=case,steps=40960,updates=20,encoder_items_unchanged=42,initial_parameters_equal_to_original=True,
    all_model_and_scalar_values_finite=True,scalar_series=len(scalars),mrq_reward_target='navigation',
    interval=interval,source=qcfg['reward_source'],beta=qcfg['beta'],geometry_alpha=qcfg['geometry_alpha'],old_coverage_bonus=0.,
    nav_rewards_and_masks_unchanged=True,no_duplicate_backfill=True,segments=len(segments),valid_segments=len(valid),valid_fraction=len(valid)/len(segments),
    bonus_sum=float(bonuses.sum()),bonus_quantiles={str(q):float(np.percentile(bonuses,q)) for q in [0,50,90,100]},
    segment_length_quantiles={str(q):float(np.percentile(lengths,q)) for q in [0,50,90,100]},
    total_new_area_m2=sum(s['metadata']['new_area_m2'] for s in valid),new_m2_per_all_actions=sum(s['metadata']['new_area_m2'] for s in valid)/40960,
    q_distribution=(None if case=='C' else {str(p):float(np.percentile([s['result']['q'] for s in valid],p)) for p in [0,50,90,100]}),
    invalid_reasons=dict(__import__('collections').Counter(s['geometry_reason'] for s in segments if not s['valid_geometry'])),
    mean_rollout_timings={k:float(np.mean([r['metrics'][prefix+'_'+k] for r in rollouts[1:]])) for k in ['geometry_seconds','render_seconds','worker_seconds','total_seconds']},
    terminal_segments=sum(s['terminal'] for s in segments),median_update_seconds=float(np.median(times)),
    combined_peak_sampled_mib=max(float(row[1].strip().split()[0]) for row in gpu if len(row)>1),
    abc_verification=verification,geometry_does_not_render_or_start_worker=(case=='C'),
    latest_training_metrics={tag:scalars[tag][-1].value for tag in ['metrics/success','metrics/spl','metrics/collisions.count','reward']},
    checkpoint_sha256=hashlib.sha256((OUT/'ckpts/latest.pth').read_bytes()).hexdigest(),learning_benefit_not_tested=True)
(HERE/case/'short_validation.json').write_text(json.dumps(report,indent=2)+'\n')
with (HERE/case/'short_scalars.csv').open('w') as f:
    w=csv.writer(f);w.writerow(['tag','step','wall_time','value'])
    for tag,rows in scalars.items():
        for e in rows:w.writerow([tag,e.step,e.wall_time,e.value])
print(json.dumps(report,indent=2),flush=True)
