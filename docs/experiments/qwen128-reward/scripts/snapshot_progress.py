"""Read-only bounded snapshots of live training; never loads a GPU or simulator."""
import csv,hashlib,json,math,shutil,sys
from pathlib import Path
from datetime import datetime,timezone,timedelta
import numpy as np
from tensorboard.backend.event_processing.event_accumulator import EventAccumulator
from tensorboard.backend.event_processing.event_file_loader import EventFileLoader
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path('/scratch/e1538633/liuyi');HERE=Path(__file__).resolve().parent
RUN=ROOT/'SIGN-qwen128-reward/results/qwen128_reward_20261029/train_personal_8env'
now=datetime.now(timezone(timedelta(hours=8)));OUT=HERE/('progress_'+now.strftime('%Y%m%dT%H%M%S'));OUT.mkdir()

def copy_prefix(source,target):
    size=source.stat().st_size
    with source.open('rb') as rd,target.open('wb') as wr:
        remaining=size
        while remaining:
            block=rd.read(min(1024*1024,remaining));assert block;wr.write(block);remaining-=len(block)
    return dict(source=str(source),bytes=size,sha256=hashlib.sha256(target.read_bytes()).hexdigest())

def write(path,value):path.write_text(json.dumps(value,indent=2,allow_nan=False)+'\n')
(OUT/'events').mkdir();inputs=[]
for source in sorted((RUN/'tb').glob('events*')):inputs.append(copy_prefix(source,OUT/'events'/source.name))
ea=EventAccumulator(str(OUT/'events'),size_guidance={'scalars':0});ea.Reload()
streams={t:[dict(step=e.step,wall_time=e.wall_time,value=e.value) for e in ea.Scalars(t)] for t in ea.Tags()['scalars']}
assert streams and all(math.isfinite(e['value']) for rows in streams.values() for e in rows)
end=max(e['step'] for rows in streams.values() for e in rows);updates=end//2048
for name in ['rollouts.jsonl','segments.jsonl','effective_config.yaml','worker_boot.json','initial_parameter_hashes.json','prompt.txt']:
    inputs.append(copy_prefix(RUN/'qwen'/name,OUT/name))
def jsonl(name):
    raw=(OUT/name).read_text();lines=raw.splitlines(keepends=True)
    return [json.loads(s) for s in lines if s.endswith('\n')]
rollouts=[r for r in jsonl('rollouts.jsonl') if r['rollout_id']<updates]
segments=[s for s in jsonl('segments.jsonl') if s['rollout_id']<updates]
assert len(rollouts)==updates
assert len({s['segment_id'] for s in segments})==len(segments)
assert all(r['nav_rewards_unchanged'] and r['masks_unchanged'] for r in rollouts)
valid=[s for s in segments if s['valid_geometry']]
for s in valid:
    q=s['result'];assert q['valid'] and 0<=q['q']<=1
    assert abs(q['q']-.5*q['p_medium']-q['p_high'])<1e-12
    assert abs(s['bonus']-.1*s['action_count']/256*q['q'])<1e-12
for r in rollouts:
    m=r['metrics'];assert abs(m['qwen_mixed_reward_sum']-m['qwen_nav_reward_sum']-m['qwen_bonus_sum'])<1e-4
    assert abs(sum(s['bonus'] for s in valid if s['rollout_id']==r['rollout_id'])-m['qwen_bonus_sum'])<1e-12
with (OUT/'qwen_scalars.csv').open('w') as f:
    w=csv.writer(f);w.writerow(['tag','step','wall_time','value'])
    for tag,rows in streams.items():
        for e in rows:w.writerow([tag,e['step'],e['wall_time'],e['value']])
# Read only the matched early prefix of the stopped baseline, not its whole history.
baseline_dir=ROOT/'SIGN/results/gibson_frozen_encoder_20261026/train_personal_8env/tb'
base={t:[] for t in ['metrics/success','metrics/spl','reward']}
for source in sorted(baseline_dir.glob('events*')):
    for event in EventFileLoader(str(source)).Load():
        if event.step>end:break
        for v in event.summary.value:
            if v.tag in base:
                value=float(v.simple_value) if v.HasField('simple_value') else float(np.frombuffer(v.tensor.tensor_content,dtype=np.float32)[0]) if v.tensor.tensor_content else float(v.tensor.float_val[0])
                base[v.tag].append(dict(step=int(event.step),wall_time=event.wall_time,value=value))
with (OUT/'baseline_matched_scalars.csv').open('w') as f:
    w=csv.writer(f);w.writerow(['tag','step','wall_time','value'])
    for tag,rows in base.items():
        for e in rows:w.writerow([tag,e['step'],e['wall_time'],e['value']])
selected=['metrics/success','metrics/spl','reward','learner/qwen_q_mean','learner/qwen_valid_fraction','learner/qwen_bonus_sum','learner/qwen_new_area_m2','learner/qwen_total_seconds']
latest={t:streams[t][-1] for t in selected}
qvalues=np.array([s['result']['q'] for s in valid]);times=np.diff([e['wall_time'] for e in streams['perf/fps']])
from collections import Counter
report=dict(captured_at=now.isoformat(timespec='seconds'),training_job='1507268.stdct-mgmt-02',runtime_commit='81fedec56b37921c350ce8064106c32788bb3e04',
    short_validation_job='1507196.stdct-mgmt-02',short_validation_steps=40960,short_validation_status='completed Exit0',
    formal_training_status='running, confirmed by qstat and live events',formal_is_separate_fresh_initialization=True,
    latest_step=end,completed_updates=updates,last_event_at=datetime.fromtimestamp(streams['perf/fps'][-1]['wall_time'],timezone(timedelta(hours=8))).isoformat(timespec='seconds'),
    checkpoint_count=len(list((RUN/'ckpts').glob('ckpt.*.pth'))),first_regular_checkpoint_step=512000,scalar_series=len(streams),all_scalars_finite=True,
    latest=latest,segments=len(segments),valid_segments=len(valid),valid_fraction=len(valid)/len(segments),
    invalid_reasons=dict(Counter(s['geometry_reason'] for s in segments if not s['valid_geometry'])),
    q=dict(min=float(qvalues.min()),mean=float(qvalues.mean()),max=float(qvalues.max())),bonus_sum=sum(s['bonus'] for s in valid),
    nav_rewards_and_masks_unchanged=True,no_duplicate_ids=True,bonus_formula_and_conservation_passed=True,
    longest_history_actions=max(s['start'] for s in segments),median_update_seconds=float(np.median(times)),
    last10_update_seconds_median=float(np.median(times[-10:])),median_steps_per_second=float(2048/np.median(times)),
    baseline_matched_latest={t:rows[-1] for t,rows in base.items()},
    expected_evaluation_jobs={'4608000':'1507270','8192000':'1507272'},evaluation_status='dependency held until exact checkpoint; no evaluation result yet',
    inputs=inputs,semantics='Training only; success/SPL are original overlapping episode-window metrics. reward is navigation only. q and bonus logged separately. Too early and one seed; no claimed learning benefit.')
write(OUT/'progress.json',report)
fig,axes=plt.subplots(2,3,figsize=(14,8),constrained_layout=True)
for ax,(tag,title,scale) in zip(axes.flat,[('metrics/success','Training success (%)',100),('metrics/spl','Training SPL (%)',100),('reward','Navigation reward',1),('learner/qwen_q_mean','Mean q in each rollout',1),('learner/qwen_valid_fraction','Valid segments (%)',100),('learner/qwen_total_seconds','Render + worker settlement seconds',1)]):
    rows=streams[tag];ax.plot([e['step']/1000 for e in rows],[e['value']*scale for e in rows],label='Qwen128',color='#2864a0')
    if tag in base:
        rows=base[tag];ax.plot([e['step']/1000 for e in rows],[e['value']*scale for e in rows],label='Frozen baseline',color='#a46534',alpha=.8);ax.legend()
    ax.set_title(title);ax.set_xlabel('Environment steps (thousands)');ax.grid(alpha=.2)
fig.suptitle('Early training snapshot | one seed | navigation reward excludes Qwen bonus')
fig.savefig(OUT/'training_progress.png',dpi=150);plt.close(fig)
print('OUTPUT',OUT);print(json.dumps({k:report[k] for k in ['captured_at','latest_step','completed_updates','latest','valid_fraction','q','median_update_seconds','checkpoint_count']},indent=2))
