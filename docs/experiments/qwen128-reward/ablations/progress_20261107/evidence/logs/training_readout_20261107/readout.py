"""CPU-only incremental training readout; never changes running experiments."""
import csv
import hashlib
import json
import math
import statistics
import struct
import subprocess
from collections import Counter, defaultdict, deque
from datetime import datetime, timedelta, timezone
from pathlib import Path

from tensorboard.compat.proto import event_pb2

ROOT = Path('/scratch/e1538633/liuyi')
HERE = Path(__file__).resolve().parent
PREVIOUS = ROOT/'logs/training_readout_20261105/snapshot_150755'
TZ = timezone(timedelta(hours=8))
NOW = datetime.now(TZ)
OUT = HERE/NOW.strftime('snapshot_%H%M%S')
OUT.mkdir()
(OUT/'readout_script_at_execution.py').write_bytes(Path(__file__).read_bytes())
OLD = json.loads((PREVIOUS/'readout.json').read_text())
PLAN = json.loads((ROOT/'logs/training_continuation_20261103/plan.json').read_text())
CORE = ['metrics/success', 'metrics/spl']
TAGS = CORE + ['reward', 'metrics/collisions.count', 'learner/value_loss',
               'learner/action_loss', 'learner/mrq_loss', 'learner/entropy',
               'learner/coverage_new_area_m2', 'learner/coverage_bonus_sum']
RUNS = {'coverage256': ('1511146', 'coverage'), 'coverage32': ('1511147', 'coverage'),
        'qwen01': ('1511145', 'qwen'), 'A': ('1511143', 'qwen'),
        'B': ('1511148', 'qwen'), 'C': ('1511410', 'geometry')}
report = {'captured_at': NOW.isoformat(timespec='seconds'), 'runs': {}, 'inputs': [],
          'semantics': 'Training means of overlapping native50-update windows; not fresh validation. Incremental TFRecord byte ranges and old-prefix SHA are verified. Raw source files are not copied again; selected CSV and recent ledger rows are frozen.'}
streams = {}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def load_csv(path):
    data = {t: [] if t in CORE else deque(maxlen=6000) for t in TAGS}
    for row in csv.DictReader(path.open()):
        if row['tag'] in data:
            data[row['tag']].append((int(row['step']), float(row['wall_time']), float(row['value'])))
    return data


def window(data, lo, hi):
    result = {}
    for tag, rows in data.items():
        selected = [v for s, _, v in rows if lo < s <= hi]
        if selected:
            result[tag] = {'mean': statistics.mean(selected), 'points': len(selected)}
    return result


for case, (job, kind) in RUNS.items():
    run = Path(PLAN[case]['tree'])/'results/continuation_20261103'/case/('train_after_latest_eval' if case == 'C' else 'train')
    data = load_csv(PREVIOUS/case/'selected_scalars.csv')
    finite = OLD['runs'][case]['all_scalars_finite']
    for source in sorted((run/'tb').glob('events*')):
        prior = next(r for r in OLD['inputs'] if r['source'] == str(source))
        size = source.stat().st_size
        old_end = prior['complete_bytes']
        assert size >= old_end
        with source.open('rb') as f:
            prefix = f.read(old_end)
            assert sha(prefix) == prior['sha256'], ('Changed previous prefix', source)
            del prefix
            raw = f.read(size-old_end)
        offset = 0
        while offset+12 <= len(raw):
            length = struct.unpack_from('<Q', raw, offset)[0]
            assert length < 10000000
            if offset+length+16 > len(raw):
                break
            event = event_pb2.Event.FromString(raw[offset+12:offset+12+length])
            for value in event.summary.value:
                assert value.HasField('simple_value')
                finite = finite and math.isfinite(value.simple_value)
                if value.tag in data:
                    rows = data[value.tag]
                    assert not rows or event.step > rows[-1][0], (case, value.tag, event.step)
                    rows.append((event.step, event.wall_time, value.simple_value))
            offset += length+16
        report['inputs'].append({'source': str(source), 'previous_prefix_bytes': old_end,
            'previous_prefix_sha256': prior['sha256'], 'previous_prefix_verified': True,
            'tail_offset': old_end, 'tail_complete_bytes': offset, 'tail_sha256': sha(raw[:offset]),
            'captured_source_bytes': size, 'ignored_incomplete_final_bytes': len(raw)-offset})
    end = min(data[t][-1][0] for t in CORE)
    for tag in data:
        data[tag] = [row for row in data[tag] if row[0] <= end]
    assert [r[0] for r in data[CORE[0]]] == [r[0] for r in data[CORE[1]]]
    assert finite
    last_time = data[CORE[0]][-1][1]
    recent = [r for r in data[CORE[0]] if r[1] > last_time-10800]
    seconds = [b[1]-a[1] for a, b in zip(recent, recent[1:])]
    info = {'job_id': job, 'directory': str(run), 'latest_step': end,
        'last_event_at': datetime.fromtimestamp(last_time, TZ).isoformat(timespec='seconds'),
        'readout_at': datetime.now(TZ).isoformat(timespec='seconds'), 'all_scalars_finite': finite,
        'last1m': window(data, end-1000000, end),
        'previous1m': window(data, end-2000000, end-1000000),
        'last3m': window(data, end-3000000, end),
        'median_seconds_per_2048_recent3h': statistics.median(seconds)}
    if kind == 'coverage':
        a = {s: v for s, _, v in data['learner/coverage_new_area_m2']}
        b = {s: v for s, _, v in data['learner/coverage_bonus_sum']}
        assert set(a) == set(b)
        info['recent_bonus_conservation_max_error'] = max(abs(b[s]-.1*a[s]/256) for s in a)
    else:
        path = run/'qwen/rollouts.jsonl'
        length = path.stat().st_size
        with path.open('rb') as f:
            raw = f.read(length)
        complete = raw.rfind(b'\n')+1
        report['inputs'].append({'source': str(path), 'complete_prefix_bytes': complete,
                                'sha256': sha(raw[:complete]), 'ignored_partial_tail_bytes': length-complete})
        c = json.loads((run/'continuation.json').read_text())
        base = c['qwen_local_rollout_offset']
        records = [json.loads(line) for line in raw[:complete].splitlines()]
        records = [r for r in records if (base+r['rollout_id']+1)*2048 <= end]
        assert [r['rollout_id'] for r in records] == list(range(len(records)))
        assert len(records) == end//2048-base
        assert all(r['nav_rewards_unchanged'] and r['masks_unchanged'] for r in records)
        selected = [r for r in records if end-1000000 < (base+r['rollout_id']+1)*2048 <= end]
        metrics = [r['metrics'] for r in selected]
        valid = sum(m[kind+'_valid_segments'] for m in metrics)
        count = sum(m[kind+'_segments'] for m in metrics)
        actions = sum(m[kind+'_valid_actions'] for m in metrics)
        reasons = Counter()
        for r in selected:
            reasons.update(r['invalid_reasons'])
        info['ledger'] = {'valid_fraction': valid/count, 'invalid_reasons': dict(reasons),
            'new_area_per_valid_action': sum(m[kind+'_new_area_m2'] for m in metrics)/actions,
            'bonus_per_rollout': statistics.mean(m[kind+'_bonus_sum'] for m in metrics),
            'q_mean_per_rollout': statistics.mean(m['qwen_q_mean'] for m in metrics) if kind == 'qwen' else None,
            'timing_means': {k: statistics.mean(m[kind+'_'+k] for m in metrics)
                for k in ['geometry_seconds', 'render_seconds', 'worker_seconds', 'total_seconds']}}
        info['audited_rollouts'] = len(records)
        info['nav_rewards_and_masks_unchanged'] = True
        info['mixed_reward_conservation_max_error'] = max(abs(r['metrics'][kind+'_mixed_reward_sum']-
            r['metrics'][kind+'_nav_reward_sum']-r['metrics'][kind+'_bonus_sum']) for r in records)
        info['qwen_worker_present'] = (run/'qwen/worker_boot.json').exists()
        with (OUT/(case+'_recent_rollouts.jsonl')).open('w') as f:
            for r in records:
                if end-3000000 < (base+r['rollout_id']+1)*2048 <= end:
                    f.write(json.dumps(r, allow_nan=False)+'\n')
    with (OUT/(case+'_selected_scalars.csv')).open('w') as f:
        writer = csv.writer(f)
        writer.writerow(['tag', 'step', 'wall_time', 'value'])
        for tag, rows in data.items():
            writer.writerows((tag, s, w, v) for s, w, v in rows)
    streams[case] = data
    report['runs'][case] = info
    print(case, end, 'last1m SR/SPL', 100*info['last1m'][CORE[0]]['mean'],
          100*info['last1m'][CORE[1]]['mean'], flush=True)

# Freeze all current job statuses before deriving cross-run comparisons.
ids = [x[0] for x in RUNS.values()]+['1523189', '1523190', '1523191']
jobs = json.loads(subprocess.check_output(['qstat', '-fx', '-F', 'json', *ids], text=True))['Jobs']
fields = ['job_state', 'Exit_status', 'comment', 'queue', 'resources_used', 'Resource_List', 'stime', 'obittime']
report['jobs'] = {k: {f: v.get(f) for f in fields} for k, v in jobs.items()}

reference = ROOT/'logs/training_readout_20261031/snapshot_005043'
refs = {}
for case in ['baseline', 'coverage256', 'coverage32']:
    path = reference/case/'selected_scalars.csv'
    refs[case] = load_csv(path)
    report['inputs'].append({'fixed_reference': str(path), 'sha256': sha(path.read_bytes())})


def compare(end, width, cases):
    result = {'lower_exclusive': end-width, 'upper_inclusive': end, 'runs': {}}
    expected = None
    for case, data in cases.items():
        result['runs'][case] = {}
        for tag in CORE:
            rows = [r for r in data[tag] if end-width < r[0] <= end]
            steps = [r[0] for r in rows]
            if expected is None:
                expected = steps
            else:
                assert steps == expected, (case, tag, end, width)
            assert rows and rows[-1][0] == end
            result['runs'][case][tag] = 100*statistics.mean(r[2] for r in rows)
    result['points'] = len(expected)
    return result


common_end = min(report['runs'][c]['latest_step'] for c in ['qwen01', 'A', 'B'])
common_cases = dict(refs)
common_cases.update({c: streams[c] for c in ['qwen01', 'A', 'B']})
# Use the actual continuation C only when the whole comparison window lies in it.
if streams['C'][CORE[0]][0][0] <= common_end-3000000:
    common_cases['C_continuation'] = streams['C']
report['common_budget'] = {str(w): compare(common_end, w, common_cases) for w in [1000000, 2000000, 3000000]}
report['own_budget'] = {c: {str(w): compare(report['runs'][c]['latest_step'], w, {**refs, c: streams[c]})
    for w in [1000000, 2000000, 3000000]} for c in ['qwen01', 'A', 'B']}
report['caveats'] = ['Means of overlapping training windows; not independent samples or validation.',
    'Original baseline/coverage histories and weights continuations have different reset histories.',
    'C continuation is explicitly labeled, with no silent stitching across its reset.',
    'Different geometry resolution/action validity definitions do not support direct old/new area rankings.']
(OUT/'readout.json').write_text(json.dumps(report, indent=2, allow_nan=False)+'\n')
print('COMMON3M', json.dumps(report['common_budget']['3000000']), flush=True)
print('OUTPUT', OUT, flush=True)
