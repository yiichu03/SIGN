"""CPU readout of fixed continuation-log snapshots; never changes jobs or training."""
import csv
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import struct
import subprocess

import numpy as np
from tensorboard.backend.event_processing.event_file_loader import RawEventFileLoader
from tensorboard.compat.proto import event_pb2

ROOT = Path('/scratch/e1538633/liuyi')
HERE = Path(__file__).resolve().parent
TZ = timezone(timedelta(hours=8))
NOW = datetime.now(TZ)
OUT = HERE / NOW.strftime('snapshot_%H%M%S')
OUT.mkdir()
PLAN = json.loads((ROOT/'logs/training_continuation_20261103/plan.json').read_text())
RUNS = {'coverage256': ('1511146', 'coverage'), 'qwen01': ('1511145', 'qwen'),
        'A': ('1511143', 'qwen'), 'C': ('1511410', 'geometry')}
KEYS = ['metrics/success', 'metrics/spl', 'reward', 'metrics/collisions.count',
        'learner/value_loss', 'learner/action_loss', 'learner/mrq_loss', 'learner/entropy']
report = {'captured_at': NOW.isoformat(timespec='seconds'), 'runs': {}, 'inputs': [],
          'semantics': 'Training only: means of overlapping native50-update episode-window logging points. Navigation reward excludes exploration bonus. Continuations reset optimizer/episodes; do not claim seamless trajectories or a controlled causal comparison against original histories.'}
streams = {}


def snapshot(source, target, record_type):
    target.parent.mkdir(parents=True, exist_ok=True)
    size = source.stat().st_size
    with source.open('rb') as f:
        raw = f.read(size)
    assert len(raw) == size
    if record_type == 'tfrecord':
        end = 0
        while end + 12 <= len(raw):
            length = struct.unpack_from('<Q', raw, end)[0]
            assert length < 10000000
            if end + 16 + length > len(raw):
                break
            end += 16 + length
    else:
        end = raw.rfind(b'\n') + 1
    target.write_bytes(raw[:end])
    report['inputs'].append({'source': str(source), 'snapshot': str(target.relative_to(OUT)),
                             'captured_bytes': size, 'complete_bytes': end,
                             'ignored_partial_tail_bytes': size-end,
                             'sha256': hashlib.sha256(raw[:end]).hexdigest()})


def window(data, lo, hi):
    result = {}
    for tag, a in data.items():
        if tag not in KEYS and not tag.startswith('learner/'):
            continue
        selected = a[(a[:, 0] > lo) & (a[:, 0] <= hi)]
        if len(selected):
            result[tag] = {'mean': float(selected[:, 2].mean()), 'points': len(selected)}
    return result


for case, (job, prefix) in RUNS.items():
    run = Path(PLAN[case]['tree'])/'results/continuation_20261103'/case/('train_after_latest_eval' if case == 'C' else 'train')
    data = defaultdict(list)
    for source in sorted((run/'tb').glob('events*')):
        target = OUT/case/'events'/source.name
        snapshot(source, target, 'tfrecord')
        for raw in RawEventFileLoader(str(target)).Load():
            event = event_pb2.Event.FromString(raw)
            for value in event.summary.value:
                assert value.HasField('simple_value'), value.tag
                data[value.tag].append((event.step, event.wall_time, value.simple_value))
    data = {tag: np.asarray(rows, dtype=np.float64) for tag, rows in data.items()}
    assert data, case
    assert all((np.diff(a[:, 0]) > 0).all() for a in data.values()), case
    assert np.array_equal(data['metrics/success'][:, 0], data['metrics/spl'][:, 0])
    end = int(data['metrics/success'][-1, 0])
    last = float(data['metrics/success'][-1, 1])
    first = int(data['metrics/success'][0, 0])
    assert first <= end-2000000, (case, first, end)
    finite = all(np.isfinite(a[:, 2]).all() for a in data.values())
    recent = data['metrics/success'][data['metrics/success'][:, 1] > last-10800]
    times = np.diff(recent[:, 1])
    info = {'job_id': job, 'directory': str(run), 'latest_step': end,
            'last_event_at': datetime.fromtimestamp(last, TZ).isoformat(timespec='seconds'),
            'continuation_first_logged_step': first, 'scalar_series': len(data),
            'all_scalars_finite': finite,
            'last1m': window(data, end-1000000, end),
            'previous1m': window(data, end-2000000, end-1000000),
            'latest': {t: float(a[-1, 2]) for t, a in data.items() if t in KEYS},
            'recent3h': {'median_seconds_per_2048': float(np.median(times)),
                         'steps_per_second': float(np.diff(recent[:, 0]).sum()/times.sum())}}
    assert finite, case
    if prefix == 'coverage':
        a, b = data['learner/coverage_new_area_m2'], data['learner/coverage_bonus_sum']
        assert np.array_equal(a[:, 0], b[:, 0])
        info['bonus_conservation_max_error'] = float(np.max(np.abs(b[:, 2]-.1*a[:, 2]/256)))
        info['last1m_area_per_all_actions'] = info['last1m']['learner/coverage_new_area_m2']['mean']/2048
    else:
        c = json.loads((run/'continuation.json').read_text())
        offset = c['qwen_local_rollout_offset']
        assert offset*2048 == c['cumulative_start_step']
        target = OUT/case/'rollouts.jsonl'
        snapshot(run/'qwen/rollouts.jsonl', target, 'jsonl')
        rows = [json.loads(line) for line in target.read_text().splitlines()]
        rows = [r for r in rows if (offset+r['rollout_id']+1)*2048 <= end]
        assert len(rows) == end//2048-offset
        assert [r['rollout_id'] for r in rows] == list(range(len(rows)))
        assert all(r['nav_rewards_unchanged'] and r['masks_unchanged'] for r in rows)
        info['nav_rewards_and_masks_unchanged'] = True
        info['audited_rollouts'] = len(rows)
        info['qwen_worker_present'] = (run/'qwen/worker_boot.json').exists()
        selected = [r for r in rows if end-1000000 < (offset+r['rollout_id']+1)*2048 <= end]
        metrics = [r['metrics'] for r in selected]
        valid = sum(m[prefix+'_valid_segments'] for m in metrics)
        segments = sum(m[prefix+'_segments'] for m in metrics)
        actions = sum(m[prefix+'_valid_actions'] for m in metrics)
        area = sum(m[prefix+'_new_area_m2'] for m in metrics)
        invalid = Counter()
        for r in selected:
            invalid.update(r['invalid_reasons'])
        info['last1m_ledger'] = {'valid_fraction': valid/segments, 'new_m2_per_valid_action': area/actions,
            'bonus_per_rollout': float(np.mean([m[prefix+'_bonus_sum'] for m in metrics])),
            'mean_segment_length': 2048*len(metrics)/segments, 'invalid_reasons': dict(invalid),
            'timing_means': {k: float(np.mean([m[prefix+'_'+k] for m in metrics]))
                             for k in ['geometry_seconds', 'render_seconds', 'worker_seconds', 'total_seconds']}}
        info['mixed_reward_conservation_max_error'] = max(abs(r['metrics'][prefix+'_mixed_reward_sum']-r['metrics'][prefix+'_nav_reward_sum']-r['metrics'][prefix+'_bonus_sum']) for r in rows)
    with (OUT/case/'selected_scalars.csv').open('w') as f:
        writer = csv.writer(f)
        writer.writerow(['tag', 'step', 'wall_time', 'value'])
        for tag, a in data.items():
            if tag in KEYS or any(k in tag for k in ['bonus_sum', 'new_area_m2', 'valid_actions', 'q_mean', 'valid_segments', 'segments']):
                writer.writerows((tag, int(step), wall, value) for step, wall, value in a)
    report['runs'][case] = info
    streams[case] = data
    print(case, end, 'last1m SR/SPL', info['last1m']['metrics/success']['mean']*100,
          info['last1m']['metrics/spl']['mean']*100, flush=True)

# Fixed historical references at the latest budget reached by both active Qwen runs.
end = min(report['runs'][case]['latest_step'] for case in ['A', 'qwen01'])
reference = ROOT/'logs/training_readout_20261031/snapshot_005043'
old_report = json.loads((reference/'readout.json').read_text())
group = {'lower_exclusive': end-1000000, 'upper_inclusive': end,
         'continuation_runs': ['A', 'qwen01'], 'original_history_references': ['baseline', 'coverage256', 'coverage32', 'C'],
         'warning': 'Qwen runs include optimizer/episode reset; original references do not at this window. Budgets match, continuation histories differ; B has not reached this budget.', 'runs': {}}
expected_steps = None
for case, old_name in [('baseline', 'baseline'), ('coverage256', 'coverage256'), ('coverage32', 'coverage32'), ('C', 'C_geometry128'), ('A', None), ('qwen01', None)]:
    if old_name:
        path = reference/old_name/'selected_scalars.csv'
        rows = defaultdict(list)
        raw_digest = hashlib.sha256(path.read_bytes()).hexdigest()
        with path.open() as f:
            for r in csv.DictReader(f):
                if r['tag'] in ['metrics/success', 'metrics/spl']:
                    rows[r['tag']].append((int(r['step']), float(r['wall_time']), float(r['value'])))
        arrays = {t: np.asarray(a) for t, a in rows.items()}
        assert old_report['runs'][old_name]['latest_step'] >= end
        report['inputs'].append({'source': str(path), 'sha256': raw_digest, 'fixed_historical_reference': True})
        assert hashlib.sha256(path.read_bytes()).hexdigest() == raw_digest
    else:
        arrays = streams[case]
    group['runs'][case] = {}
    for tag in ['metrics/success', 'metrics/spl']:
        a = arrays[tag];a = a[(a[:, 0] > end-1000000) & (a[:, 0] <= end)]
        if expected_steps is None:
            expected_steps = a[:, 0]
        else:
            assert np.array_equal(a[:, 0], expected_steps), (case, tag)
        group['runs'][case][tag] = {'mean': float(a[:, 2].mean()), 'points': len(a)}
report['matched_latest_active_qwen_budget'] = group

historical = json.loads((ROOT/'logs/training_stop_20261031/readout_20261103T014602/report.json').read_text())
report['queued_historical_last_metrics'] = {name: historical['runs'][old_name] for name, old_name in [('coverage32', 'coverage32'), ('B', 'B_qwen256_beta003')]}
report['stopped_baseline'] = old_report['runs']['baseline']
ids = ['1511143', '1511145', '1511146', '1511147', '1511148', '1511410', '1515117', '1515118']
jobs = json.loads(subprocess.check_output(['qstat', '-fx', '-F', 'json', *ids], text=True))['Jobs']
report['jobs'] = {j: {k: s.get(k) for k in ['job_state', 'Exit_status', 'comment', 'Hold_Types', 'project', 'queue']} for j, s in jobs.items()}
author = subprocess.check_output(['git', 'show', 'dad87fe225a4dc1073787d8d2cc83f67e61c0a9d:exp_config/ppo_imagenav_gibson.yaml'], cwd=ROOT/'SIGN', text=True)
assert 'total_num_steps: 3e8' in author
report['author_gibson_default'] = {'total_environment_steps': 300000000, 'num_updates': -1,
    'source_commit': 'dad87fe225a4dc1073787d8d2cc83f67e61c0a9d', 'file': 'exp_config/ppo_imagenav_gibson.yaml',
    'file_sha256': hashlib.sha256(author.encode()).hexdigest()}
(OUT/'readout.json').write_text(json.dumps(report, indent=2, allow_nan=False)+'\n')
print('MATCHED', json.dumps(group), flush=True)
print('OUTPUT', str(OUT), flush=True)
