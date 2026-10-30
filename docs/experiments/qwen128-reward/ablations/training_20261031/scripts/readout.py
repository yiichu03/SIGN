"""CPU-only, fixed-byte snapshots of existing training; no job or source changes."""
import csv
import hashlib
import json
import math
import subprocess
from collections import defaultdict, Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
from tensorboard.backend.event_processing.event_file_loader import RawEventFileLoader
from tensorboard.compat.proto import event_pb2

ROOT = Path('/scratch/e1538633/liuyi')
TZ = timezone(timedelta(hours=8))
NOW = datetime.now(TZ)
OUT = Path(__file__).resolve().parent / NOW.strftime('snapshot_%H%M%S')
OUT.mkdir()
RUNS = {
    'baseline': ('SIGN/results/gibson_frozen_encoder_20261026/train_personal_8env', '1496716', None),
    'coverage256': ('SIGN-frozen-rollout-coverage/results/gibson_rollout_coverage_20261027/train_personal_8env', '1497416', 'coverage'),
    'coverage32': ('SIGN-frozen-coverage-settle32/results/gibson_coverage_settle32_20261028/train_personal_8env', '1502352', 'coverage'),
    'qwen128_beta01': ('SIGN-qwen128-reward/results/qwen128_reward_20261029/train_personal_8env', '1507268', 'qwen'),
    'A_qwen128_beta003': ('SIGN-qwen-ablation/results/qwen_ablation_20261029/A/train', '1507648', 'qwen'),
    'B_qwen256_beta003': ('SIGN-qwen-ablation/results/qwen_ablation_20261029/B/train', '1507651', 'qwen'),
    'C_geometry128': ('SIGN-qwen-ablation/results/qwen_ablation_20261029/C/train', '1507650', 'geometry'),
}
KEYS = ['metrics/success', 'metrics/spl', 'reward', 'metrics/collisions.count', 'metrics/distance_to_goal', 'metrics/view_match', 'learner/value_loss', 'learner/action_loss', 'learner/entropy', 'learner/mrq_loss']
report = dict(captured_at=NOW.isoformat(timespec='seconds'), output_directory=str(OUT),
    semantics='Training only. SR/SPL/reward/collisions are averages of overlapping native 50-update episode-window statistics, not independent samples or validation scores. reward excludes exploration bonus. Coverage .1m and Qwen/geometry .025m valid-only area measurements must not be directly ranked across these two families.',
    snapshots=[], runs={}, windows=[])
streams = {}

def save(path, data):
    path.write_text(json.dumps(data, indent=2, allow_nan=False) + '\n')

def snapshot(source, target):
    target.parent.mkdir(parents=True, exist_ok=True)
    size = source.stat().st_size
    h = hashlib.sha256()
    with source.open('rb') as rd, target.open('wb') as wr:
        left = size
        while left:
            block = rd.read(min(left, 1024 * 1024))
            assert block
            wr.write(block); h.update(block); left -= len(block)
    report['snapshots'].append(dict(source=str(source), snapshot=str(target.relative_to(OUT)), bytes=size, sha256=h.hexdigest()))

def native_window(data, lo, hi):
    result = {}
    for tag, values in data.items():
        if tag not in KEYS and not tag.startswith('learner/'):
            continue
        values = values[(values[:, 0] > lo) & (values[:, 0] <= hi)]
        if len(values):
            result[tag] = float(values[:, 2].mean())
    return result

for name, (relative, job, prefix) in RUNS.items():
    run = ROOT / relative
    data = defaultdict(list)
    for source in sorted((run / 'tb').glob('events*')):
        target = OUT / name / 'events' / source.name
        snapshot(source, target)
        for raw in RawEventFileLoader(str(target)).Load():
            event = event_pb2.Event.FromString(raw)
            for value in event.summary.value:
                if value.HasField('simple_value'):
                    v = float(value.simple_value)
                elif value.HasField('tensor'):
                    tensor = value.tensor
                    v = float(np.frombuffer(tensor.tensor_content, dtype=np.float32)[0]) if tensor.tensor_content else float(tensor.float_val[0])
                else:
                    continue
                data[value.tag].append((event.step, event.wall_time, v))
    data = {tag: np.asarray(rows, dtype=np.float64) for tag, rows in data.items()}
    assert data
    bad = {tag: int((~np.isfinite(rows[:, 2])).sum()) for tag, rows in data.items() if not np.isfinite(rows[:, 2]).all()}
    steps = data['metrics/success'][:, 0]
    assert (np.diff(steps) > 0).all(), name
    end = int(steps[-1]); last = float(data['metrics/success'][-1, 1])
    times = data['metrics/success']
    recent = times[times[:, 1] > last - 10800]
    duration = np.diff(recent[:, 1]); delta_steps = np.diff(recent[:, 0])
    info = dict(job_id=job, directory=str(run), latest_step=end, last_event_at=datetime.fromtimestamp(last, TZ).isoformat(timespec='seconds'),
        tags=len(data), nonfinite=bad, all_scalars_finite=not bad,
        latest={tag: float(rows[-1, 2]) for tag, rows in data.items() if tag in KEYS or tag.startswith('learner/')},
        own_last_1m=native_window(data, end - 1e6, end), own_previous_1m=native_window(data, end - 2e6, end - 1e6),
        recent_3h=dict(start_step=int(recent[0, 0]), end_step=end, updates=len(recent), median_update_seconds=float(np.median(duration)),
            p90_update_seconds=float(np.percentile(duration, 90)), steps_per_second=float(delta_steps.sum() / duration.sum())),
        checkpoints=sorted(p.name for p in (run / 'ckpts').glob('milestone*')),
        stage=dict(mrq_auxiliary_update=end < 50000000, random_shift_still_configured=True))
    if prefix == 'coverage':
        a = data['learner/coverage_new_area_m2']; b = data['learner/coverage_bonus_sum']
        assert np.array_equal(a[:, 0], b[:, 0])
        info['bonus_conservation_max_error'] = float(np.max(np.abs(b[:, 2] - .1 * a[:, 2] / 256)))
        info['own_last_1m_area_per_all_actions'] = info['own_last_1m']['learner/coverage_new_area_m2'] / 2048
    elif prefix:
        snapshot(run / 'qwen/rollouts.jsonl', OUT / name / 'rollouts.jsonl')
        rows = [json.loads(line) for line in (OUT / name / 'rollouts.jsonl').read_text().splitlines(keepends=True) if line.endswith('\n')]
        rows = [row for row in rows if (row['rollout_id'] + 1) * 2048 <= end]
        assert len(rows) == end // 2048
        assert [row['rollout_id'] for row in rows] == list(range(end // 2048))
        assert all(row['nav_rewards_unchanged'] and row['masks_unchanged'] for row in rows)
        errors = [abs(r['metrics'][prefix+'_mixed_reward_sum'] - r['metrics'][prefix+'_nav_reward_sum'] - r['metrics'][prefix+'_bonus_sum']) for r in rows]
        info['nav_rewards_and_masks_unchanged_all_rollouts'] = True
        info['mixed_reward_conservation_max_error'] = max(errors)
        info['rollout_audit_count'] = len(rows)
        info['area_resolution_m'] = .025
        info['qwen_worker_boot_present'] = (run / 'qwen/worker_boot.json').exists()
        info['rollout_windows'] = {}
        for label, lo, hi in [('own_last_1m', end - 1e6, end), ('own_previous_1m', end - 2e6, end - 1e6)]:
            selected = [r for r in rows if lo < (r['rollout_id']+1)*2048 <= hi]
            metrics = [r['metrics'] for r in selected]
            valid = sum(m[prefix+'_valid_segments'] for m in metrics)
            segments = sum(m[prefix+'_segments'] for m in metrics)
            valid_actions = sum(m[prefix+'_valid_actions'] for m in metrics)
            area = sum(m[prefix+'_new_area_m2'] for m in metrics)
            invalid = Counter()
            for r in selected: invalid.update(r['invalid_reasons'])
            x = dict(valid_fraction=valid/segments, valid_segments=valid, segments=segments, valid_action_fraction=valid_actions/(2048*len(metrics)),
                area_m2=area, new_m2_per_valid_action=area/valid_actions, bonus_per_rollout=float(np.mean([m[prefix+'_bonus_sum'] for m in metrics])),
                mean_segment_length=2048*len(metrics)/segments, invalid_reasons=dict(invalid),
                timings_mean_seconds={k: float(np.mean([m[prefix+'_'+k] for m in metrics])) for k in ['geometry_seconds','render_seconds','worker_seconds','total_seconds']})
            if prefix == 'qwen':
                x['segment_weighted_q_mean'] = sum(m.get('qwen_q_mean',0)*m['qwen_valid_segments'] for m in metrics)/valid
                x['length_weighted_q_mean'] = sum(m['qwen_bonus_sum'] for m in metrics)*256/((.1 if name == 'qwen128_beta01' else .03)*valid_actions)
            info['rollout_windows'][label] = x
    with (OUT / name / 'selected_scalars.csv').open('w') as f:
        writer = csv.writer(f); writer.writerow(['tag','step','wall_time','value'])
        for tag, values in data.items():
            if tag in KEYS or tag.startswith('learner/') and any(t in tag for t in ['bonus_sum', 'new_area_m2', 'valid_fraction', 'q_mean', 'total_seconds']):
                for step, wall, value in values: writer.writerow([tag, int(step), wall, value])
    report['runs'][name] = info; streams[name] = data
    print(name, end, 'SR', round(info['own_last_1m']['metrics/success']*100,3), 'SPL', round(info['own_last_1m']['metrics/spl']*100,3), 'nonfinite', bad, flush=True)

def window(label, names, lo, hi):
    row = dict(label=label, lower_exclusive=int(lo), upper_inclusive=int(hi), runs={})
    for name in names:
        metrics = native_window(streams[name], lo, hi)
        prefix = RUNS[name][2]
        if prefix:
            area = metrics['learner/'+prefix+'_new_area_m2']
            metrics['new_m2_per_all_actions'] = area/2048
            if prefix != 'coverage':
                metrics['new_m2_per_valid_action'] = area/metrics['learner/'+prefix+'_valid_actions']
                metrics['valid_segment_fraction_from_counts'] = metrics['learner/'+prefix+'_valid_segments']/metrics['learner/'+prefix+'_segments']
        row['runs'][name] = metrics
    report['windows'].append(row)

names = list(RUNS)
common = min(report['runs'][n]['latest_step'] for n in names)
window('all_methods_common_last_1m', names, common-1e6, common)
window('all_methods_common_previous_1m', names, common-2e6, common-1e6)
abc = ['baseline','A_qwen128_beta003','B_qwen256_beta003','C_geometry128']
end = min(report['runs'][n]['latest_step'] for n in abc)
window('ABC_and_baseline_common_last_1m', abc, end-1e6, end)
for width in [1e6, 5e6]:
    end = min(report['runs'][n]['latest_step'] for n in ['baseline','coverage256','coverage32'])
    window('legacy_threeway_common_last_'+str(int(width)), ['baseline','coverage256','coverage32'], end-width, end)
end = min(report['runs'][n]['latest_step'] for n in ['baseline','coverage256'])
window('baseline_coverage256_common_last_5m', ['baseline','coverage256'], end-5e6, end)
for lo in range(0, common, 1000000):
    window('all_methods_1m_bins', names, lo, min(lo+1000000, common))
save(OUT / 'readout.json', report)

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
colors = ['#111111','#a1a1a1','#888800','#9467bd','#d62728','#1f77b4','#2ca02c']
fig, axes = plt.subplots(1,3,figsize=(17,5),constrained_layout=True)
for ax, tag, title, scale in zip(axes, ['metrics/success','metrics/spl','reward'], ['Training SR (%)','Training SPL (%)','Navigation reward (exploration excluded)'], [100,100,1]):
    for name, color in zip(names,colors):
        values = streams[name][tag]; values = values[values[:,0] <= common]
        width = 101
        y = np.convolve(values[:,2], np.ones(width)/width, mode='valid')*scale
        x = values[(width-1)//2:len(values)-(width-1)//2,0]/1e6
        ax.plot(x,y,label=name,color=color,linewidth=1.5)
    ax.grid(alpha=.2); ax.set_title(title); ax.set_xlabel('Environment steps (M)')
axes[0].legend(fontsize=7)
fig.suptitle('Same training budget; one seed; 101-update display smoothing; training only')
fig.savefig(OUT/'matched_training.png',dpi=160);plt.close(fig)
print('OUTPUT',OUT,flush=True)
