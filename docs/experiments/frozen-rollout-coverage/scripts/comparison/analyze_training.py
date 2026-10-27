"""Read-only snapshot of the two live TensorBoard streams; no trainer changes."""
from pathlib import Path
from datetime import datetime, timezone, timedelta
import csv
import json
import sys
import numpy as np
from tensorboard.backend.event_processing.event_accumulator import EventAccumulator
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path('/scratch/e1538633/liuyi')
OUT = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path(__file__).resolve().parent
OUT.mkdir(parents=True, exist_ok=True)
RUNS = {
    'baseline': ROOT/'SIGN/results/gibson_frozen_encoder_20261026/train_personal_8env',
    'coverage': ROOT/'SIGN-frozen-rollout-coverage/results/gibson_rollout_coverage_20261027/train_personal_8env',
}
streams = {}
for name, path in RUNS.items():
    print('Reading', name, flush=True)
    ea = EventAccumulator(str(path/'tb'), size_guidance={'scalars': 0})
    ea.Reload()
    data = {}
    with (OUT/(name+'_scalars.csv')).open('w') as handle:
        writer = csv.writer(handle)
        writer.writerow(['tag', 'step', 'wall_time', 'value'])
        for tag in ea.Tags()['scalars']:
            events = ea.Scalars(tag)
            data[tag] = np.array([(v.step, v.wall_time, v.value) for v in events], dtype=float)
            for v in events:
                writer.writerow([tag, v.step, v.wall_time, v.value])
    streams[name] = data
    print(name, 'latest step', int(data['metrics/success'][-1, 0]), flush=True)

common = int(min(d['metrics/success'][-1, 0] for d in streams.values()))
tags = ['metrics/success', 'metrics/spl', 'metrics/view_match', 'metrics/collisions.count',
        'metrics/distance_to_goal', 'reward', 'perf/fps']
report = {'recorded_at': datetime.now(timezone(timedelta(hours=8))).isoformat(timespec='seconds'),
          'common_end_step': common, 'evaluation': 'training-stream comparison only; not validation',
          'window_semantics': 'Native 50-update completed-episode rolling means; additional interval means are descriptive and correlated.',
          'runs': {}, 'matched_intervals': []}
for name, data in streams.items():
    report['runs'][name] = {'path': str(RUNS[name]), 'latest_step': int(data['metrics/success'][-1, 0]),
                           'latest': {tag: float(data[tag][-1, 2]) for tag in tags},
                           'all_scalars_finite': all(np.isfinite(v).all() for v in data.values())}
    if name == 'coverage':
        report['runs'][name]['bonus_last_1m'] = {}
        for tag in ['learner/coverage_bonus_sum', 'learner/coverage_bonus_per_step', 'learner/coverage_new_area_m2']:
            arr = data[tag]; values = arr[arr[:, 0] > common - 1000000, 2]
            report['runs'][name]['bonus_last_1m'][tag] = {'mean': float(values.mean()), 'min': float(values.min()), 'max': float(values.max())}

intervals = [(max(0, end-1000000), end) for end in [1000000,2000000,4000000,6000000,8000000,9216000] if end <= common]
intervals.append((max(0,common-1000000),common))
for lower, upper in intervals:
    rec = {'lower_exclusive': lower, 'upper_inclusive': upper, 'metrics': {}}
    for tag in tags:
        values = {}
        for name, data in streams.items():
            arr = data[tag]; selected = arr[(arr[:, 0] > lower) & (arr[:, 0] <= upper)]
            values[name] = float(selected[:, 2].mean())
        values['coverage_minus_baseline'] = values['coverage'] - values['baseline']
        rec['metrics'][tag] = values
    report['matched_intervals'].append(rec)

fig, axes = plt.subplots(3, 1, figsize=(10, 10), sharex=True, constrained_layout=True)
for ax, tag, label in zip(axes, ['metrics/success', 'metrics/spl', 'reward'], ['Training success (%)', 'Training SPL (%)', 'Navigation reward (bonus excluded)']):
    factor = 100 if tag != 'reward' else 1
    for name, color in [('baseline','#2166ac'), ('coverage','#d95f02')]:
        arr = streams[name][tag]
        matched = arr[arr[:, 0] <= common]
        ax.plot(matched[:, 0]/1e6, matched[:, 2]*factor, color=color, alpha=.18, linewidth=.5)
        width = 101
        smooth = np.convolve(matched[:, 2], np.ones(width)/width, mode='valid')
        ax.plot(matched[width//2:len(matched)-width//2, 0]/1e6, smooth*factor, color=color, label=name, linewidth=1.7)
    ax.axvspan((common-1000000)/1e6, common/1e6, color='gray', alpha=.10)
    ax.set_ylabel(label); ax.grid(alpha=.2)
axes[0].legend(loc='lower right')
axes[-1].set_xlabel('Environment steps (millions); matched training budget')
fig.suptitle('Frozen encoder: coverage bonus vs baseline\nOne seed; training episodes, not held-out evaluation')
fig.savefig(str(OUT/'matched_training_curves.png'), dpi=170)
fig.savefig(str(OUT/'matched_training_curves.pdf'))
(OUT/'training_comparison.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report, indent=2), flush=True)
