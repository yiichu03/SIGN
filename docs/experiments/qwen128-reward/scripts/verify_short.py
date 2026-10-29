"""Audit actual GPU short training, saved inputs, losses and zero-beta control."""
import hashlib,json,math,sys,time
from pathlib import Path
import numpy as np
import torch
from tensorboard.backend.event_processing.event_accumulator import EventAccumulator
ROOT=Path('/scratch/e1538633/liuyi');HERE=Path(__file__).resolve().parent;TREE=ROOT/'SIGN-qwen128-reward'
sys.path.insert(0,str(TREE))
from src.qwen_geometry import EpisodeCoverage,render
OUT=TREE/'results/qwen128_reward_20261029'
def load(name):return torch.load(str(OUT/name/'ckpts/latest.pth'),map_location='cpu')
def hashes(state):return {k:hashlib.sha256(v.numpy().tobytes()).hexdigest() for k,v in state.items()}
def events(name):
    acc=EventAccumulator(str(OUT/name/'tb'),size_guidance={'scalars':0});acc.Reload()
    rows={tag:[dict(step=e.step,value=e.value,time=e.wall_time) for e in acc.Scalars(tag)] for tag in acc.Tags()['scalars']}
    assert all(math.isfinite(e['value']) for row in rows.values() for e in row)
    return rows
base=load('short_baseline_8192');zero=load('short_zero_8192');qwen=load('short_qwen_40960')
assert base['extra_state']['step']==zero['extra_state']['step']==8192
assert qwen['extra_state']['step']==40960
assert base['state_dict'].keys()==zero['state_dict'].keys()
changed=[k for k in base['state_dict'] if not torch.equal(base['state_dict'][k],zero['state_dict'][k])]
# Original Qc has CUDA reduction nondeterminism. If present, measure it with an
# unchanged-baseline repeat on this same GPU instead of altering Qc or its flags.
qc_differences={k:float((base['state_dict'][k]-zero['state_dict'][k]).abs().max()) for k in changed}
assert all(k.startswith('actor_critic.Qc.') for k in changed),changed
baseline_repeat_differences={}
if changed:
    from run_training import run
    repeat_out=OUT/'short_baseline_repeat_8192'
    if not repeat_out.exists():run(ROOT/'SIGN',repeat_out,8192)
    repeat=load('short_baseline_repeat_8192')
    baseline_repeat_differences={k:float((base['state_dict'][k]-repeat['state_dict'][k]).abs().max())
        for k in base['state_dict'] if not torch.equal(base['state_dict'][k],repeat['state_dict'][k])}
    assert baseline_repeat_differences,'Baseline repeat is exact; unexplained zero-beta discrepancy'
    assert all(k.startswith('actor_critic.Qc.') for k in baseline_repeat_differences)
    assert max(qc_differences.values())<=1e-6
    assert max(qc_differences.values())<=max(baseline_repeat_differences.values())*10
assert not (OUT/'short_zero_8192/qwen/worker.log').exists()
initial_zero=json.loads((OUT/'short_zero_8192/qwen/initial_parameter_hashes.json').read_text())
initial_qwen=json.loads((OUT/'short_qwen_40960/qwen/initial_parameter_hashes.json').read_text())
assert initial_zero==initial_qwen,'Non-encoder initialization differs'
original=torch.load(str(ROOT/'SIGN/ckpt/nav_model.pth'),map_location='cpu')['state_dict']
encoder=[k for k in qwen['state_dict'] if k.startswith('actor_critic.net.visual_encoder.')]
assert len(encoder)==42
assert all(torch.equal(qwen['state_dict'][k],original[k]) for k in encoder)
assert all(torch.isfinite(v).all().item() for v in qwen['state_dict'].values())
fc='actor_critic.net.visual_fc.1.weight'
assert initial_qwen[fc]!=hashes({fc:original[fc]})[fc]
assert initial_qwen[fc]!=hashes({fc:qwen['state_dict'][fc]})[fc]
tb={name:events(name) for name in ['short_baseline_8192','short_zero_8192','short_qwen_40960']}
for tag,values in tb['short_baseline_8192'].items():
    if tag.startswith('perf/') or tag=='learner/qc_loss':continue
    assert [(e['step'],e['value']) for e in values]==[(e['step'],e['value']) for e in tb['short_zero_8192'][tag]],tag
run=OUT/'short_qwen_40960/qwen'
rollouts=[json.loads(s) for s in (run/'rollouts.jsonl').read_text().splitlines()]
segments=[json.loads(s) for s in (run/'segments.jsonl').read_text().splitlines()]
assert [r['rollout_id'] for r in rollouts]==list(range(20))
ids=[s['segment_id'] for s in segments];assert len(ids)==len(set(ids))
valid=[s for s in segments if s['valid_geometry']]
assert valid,'No valid Qwen training segments'
for s in valid:
    q=s['result'];assert q['valid'] and math.isfinite(q['q'])
    assert abs(q['q']-(.5*q['p_medium']+q['p_high']))<1e-12
    assert abs(sum(q[k] for k in ['p_low','p_medium','p_high'])-1)<1e-12
    assert abs(s['bonus']-.1*(s['action_count']/256)*q['q'])<1e-12
    assert s['action_count']==s['end']-s['start']==s['global_end']-s['global_start']
for r in rollouts:
    assert r['nav_rewards_unchanged'] and r['masks_unchanged']
    m=r['metrics'];assert abs(m['qwen_mixed_reward_sum']-m['qwen_nav_reward_sum']-m['qwen_bonus_sum'])<1e-4
    assert abs(sum(s['bonus'] for s in valid if s['rollout_id']==r['rollout_id'])-m['qwen_bonus_sum'])<1e-12
check=json.loads((run/'verification.json').read_text());assert check['passed']
boot=json.loads((run/'worker_boot.json').read_text());assert boot['environment']['dtype']=='torch.float32'
# Replay a genuinely long-history sampled segment from saved actual poses only.
long=[]
for p in sorted((run/'samples').glob('*.json')):
    row=json.loads(p.read_text());s=row['identity']
    if s['start']>=128:long.append((p,row))
assert long,'No true long-history example saved'
p,row=max(long,key=lambda item:item[1]['identity']['start']);s=row['identity'];png=p.with_suffix('.png')
with np.load(p.with_suffix('.npz')) as a:
    g=EpisodeCoverage(a['grid'])
    for i,(rc,heading,xyz) in enumerate(zip(a['coords'],a['headings'],a['positions'])):
        g.observe(rc,float(heading),xyz)
        if i==s['start']:g.cut()
    rebuilt=g.snapshot()
    assert np.array_equal(rebuilt['prior_seen'],a['prior_seen'])
    assert np.array_equal(rebuilt['final_seen'],a['final_seen'])
    for k,v in row['row']['metadata'].items():assert rebuilt['metadata'][k]==v,k
    stats=rebuilt['metadata'];n=np.count_nonzero(a['grid']==1)
    title=f"{Path(s['scene_id']).stem} / task {s['episode_id']} / E{s['env_id']:02d} | {stats['action_count']} actions\nCovered {100*stats['total_valid_cells']/n:.1f}% | New {100*stats['new_valid_cells']/n:.1f}%"
    replay=HERE/'short_long_history_replay.png'
    render(replay,a['coords'],a['grid'],a['prior_seen'],a['final_seen'],s['start'],s['end'],g.bounds,title,'history',float(a['mpp']))
    assert replay.read_bytes()==png.read_bytes(),'Online/offline rendering mismatch'
# Timing measures all PPO updates; exclude first update for steady-state comparison.
def timing(name):
    ts=tb[name]['perf/fps'];return dict(updates=len(ts),median_update_seconds=float(np.median(np.diff([e['time'] for e in ts]))),
                                     wall_seconds=json.loads((HERE/(name+'_walltime.json')).read_text())['seconds'])
metrics=[r['metrics'] for r in rollouts[1:]]
import csv
with (HERE/'short_gpu.csv').open() as handle:
    gpu_rows=list(csv.reader(handle))[1:]
sampled_peak=max(float(row[1].strip().split()[0]) for row in gpu_rows if len(row)>1)
report=dict(passed=True,steps=40960,updates=20,
    checkpoint_sha256={name:hashlib.sha256((OUT/name/'ckpts/latest.pth').read_bytes()).hexdigest() for name in tb},zero_beta_bitwise_checkpoint_items=len(base['state_dict'])-len(changed),
    zero_beta_qc_roundoff_max_abs=qc_differences,baseline_repeat_qc_roundoff_max_abs=baseline_repeat_differences,
    initial_parameter_hashes_identical=True,encoder_items_unchanged=42,all_model_and_scalar_values_finite=True,
    independent_worker_pid=boot['pid'],worker=boot['environment'],abc_verification=check,
    segment_count=len(segments),valid_segments=len(valid),valid_fraction=len(valid)/len(segments),
    invalid_reasons=dict(__import__('collections').Counter(s['geometry_reason'] for s in segments if not s['valid_geometry'])),
    q_min=min(s['result']['q'] for s in valid),q_mean=float(np.mean([s['result']['q'] for s in valid])),q_max=max(s['result']['q'] for s in valid),
    bonus_sum=sum(s['bonus'] for s in valid),nav_rewards_and_masks_unchanged=True,no_duplicate_backfill=True,
    true_terminal_segments=sum(s['terminal'] for s in segments),longest_history_actions=max(s['start'] for s in segments),
    long_history_input=str(png),long_history_sample_prior_actions=s['start'],offline_online_actual_sample_pixels_masks_statistics_exact=True,
    timing={name:timing(name) for name in tb},
    mean_timing_seconds={k:float(np.mean([m[k] for m in metrics])) for k in ['qwen_geometry_seconds','qwen_render_seconds','qwen_worker_seconds','qwen_total_seconds']},
    worker_peak_gpu_gib=max(r['metrics']['qwen_worker_peak_gpu_gib'] for r in rollouts),
    combined_gpu_peak_sampled_mib=sampled_peak,gpu_sampling_interval_seconds=5,
    scalar_series={k:len(v) for k,v in tb.items()},learning_benefit_not_tested=True)
(HERE/'short_validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2),flush=True)
