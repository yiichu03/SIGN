"""Observed terminal stages and overlapping behavioral evidence; no causal labels."""
import argparse
from collections import Counter, defaultdict
import csv
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import subprocess
from concurrent.futures import ThreadPoolExecutor

import numpy as np

HERE = Path(__file__).resolve().parent
TAGS = ['strong_blocked_tail_candidate', 'blocked_run_anywhere_candidate',
        'low_gain_closed_loop_candidate', 'stationary_turn_tail_candidate']


def distribution(values):
    values = np.asarray(values, dtype=np.float64)
    if not len(values):
        return dict(n=0, mean=None, p10=None, median=None, p90=None)
    assert np.isfinite(values).all()
    return dict(n=len(values), mean=float(values.mean()),
                p10=float(np.quantile(values, .1)), median=float(np.median(values)),
                p90=float(np.quantile(values, .9)))


def validate_trace(trace, row):
    n = row['steps'] + 1
    fields = {name: i for i, name in enumerate(trace['metric_fields'].tolist())}
    for name, width in [('position_xyz',3), ('rotation_xyzw',4),
                        ('command_mps_degps',2), ('action_normalized_linear_angular',2)]:
        assert trace[name].shape == (n,width), (row['case'],row['episode_id'],name)
        assert np.isfinite(trace[name]).all()
    metrics = trace['metrics']
    assert metrics.shape == (n,len(fields)) and np.isfinite(metrics).all()
    actions = trace['action_normalized_linear_angular'][1:]
    command = trace['command_mps_degps'][1:]
    assert (abs(actions) <= 1.000001).all()
    assert np.allclose(command[:,0], (actions[:,0]+1)*.125, rtol=0, atol=1e-7)
    assert np.allclose(command[:,1], actions[:,1]*15, rtol=0, atol=1e-6)
    # ContinuousAction scales the original float32 action arrays. The stored
    # physical command is a float64 nominal conversion; near the angular STOP
    # boundary its last-bit rounding must not invent a telemetry mismatch.
    effective_linear=(actions[:,0]+1.)/2.*.25
    effective_angular=-15.+(actions[:,1]+1.)/2.*30.
    stopped = (abs(effective_linear) < .025) & (abs(effective_angular) < 1.5)
    assert np.array_equal(stopped, metrics[1:,fields['stop_called']].astype(bool))
    assert bool(metrics[-1,fields['stop_called']]) == row['stop_called']
    assert bool(metrics[-1,fields['step_limit_reached']]) == row['step_limit_reached']
    assert metrics[-1,fields['success']] == row['success']
    area = metrics[:,fields['coverage_new_area_m2']]
    delta = metrics[:,fields['coverage_delta_m2']]
    assert area[0] == delta[0] == 0 and (delta >= 0).all()
    assert np.allclose(np.diff(area),delta[1:],rtol=0,atol=1e-7)
    assert not metrics[:-1,fields['environment_episode_over']].any()
    assert bool(metrics[-1,fields['environment_episode_over']])


def verify_video(item):
    from PIL import Image
    path, expected, goal_sha = item
    with Image.open(path.with_suffix('.goal.png')) as image:
        assert hashlib.sha256(np.ascontiguousarray(np.asarray(image)).tobytes()).hexdigest()==goal_sha
    probe = Path('/scratch/e1538633/liuyi/envs/sign-baseline/bin/ffprobe')
    result = json.loads(subprocess.check_output([
        str(probe), '-v', 'error', '-threads', '1', '-select_streams', 'v:0',
        '-count_frames', '-show_entries', 'stream=nb_read_frames,width,height',
        '-of', 'json', str(path)], text=True))['streams'][0]
    assert int(result['nb_read_frames']) == expected, (path,result,expected)
    assert (result['width'],result['height']) == (256,160), (path,result)
    return expected


def projection_audit(trace):
    # This checks the saved 2D raster, not simulator navigability or the
    # physical cause of a collision. Intermediate height maps were not saved.
    if 'initial_grid' not in trace:
        return dict(coverage_projection_audit='map_not_saved',
                    coverage_projected_nonvalid_fraction=None)
    position=trace['position_xyz']
    grid=trace['initial_grid']
    if (float(np.ptp(position[:,1])) > float(trace['meters_per_pixel']) or
            not np.array_equal(grid,trace['final_grid'])):
        return dict(coverage_projection_audit='intermediate_height_maps_unknown',
                    coverage_projected_nonvalid_fraction=None)
    bounds=trace['map_bounds_xyz']
    # Agent positions and PathFinder bounds are float32. Match Habitat's
    # subtraction before its scalar division, including raster-edge rounding.
    lower,upper=bounds.astype(position.dtype)
    row=((position[:,2]-lower[2]).astype(float) /
         (float(upper[2]-lower[2])/grid.shape[0])).astype(int)
    col=((position[:,0]-lower[0]).astype(float) /
         (float(upper[0]-lower[0])/grid.shape[1])).astype(int)
    assert ((row >= 0)&(row < grid.shape[0])&(col >= 0)&(col < grid.shape[1])).all()
    invalid=grid[row,col] != 1
    return dict(coverage_projection_audit='single_saved_grid_assessable',
                coverage_projected_nonvalid_fraction=float(invalid.mean()),
                coverage_projected_nonvalid_states=int(invalid.sum()))


def longest_true_run(values):
    best = current = 0
    for value in values:
        current = current+1 if value else 0
        best = max(best, current)
    return best


def heading(quaternions):
    x, y, z, w = quaternions.T
    return np.arctan2(-2*(x*z+y*w), -(1-2*(x*x+y*y)))


def closed_loops(positions, yaw, traveled, area, profile):
    n = len(positions)
    if n <= profile['loop_min_gap'] or traveled[-1] < profile['loop_min_path_m']:
        return []
    delta = positions[:, None, :]-positions[None, :, :]
    distance_sq = np.einsum('ijk,ijk->ij', delta, delta)
    angle = np.abs((yaw[:, None]-yaw[None, :]+np.pi) % (2*np.pi)-np.pi)
    gap = np.arange(n)[None, :]-np.arange(n)[:, None]
    travel = traveled[None, :]-traveled[:, None]
    gain = area[None, :]-area[:, None]
    candidates = ((gap >= profile['loop_min_gap']) &
                  (distance_sq <= profile['loop_close_distance_m']**2) &
                  (angle <= np.deg2rad(profile['loop_close_heading_deg'])) &
                  (travel >= profile['loop_min_path_m']) &
                  (gain >= -1e-8) & (gain <= profile['loop_max_new_area_m2']))
    loops = []
    previous_end = 0
    # Earliest completion, most recent valid start; nonoverlapping bouts.
    # A bout is still only a low-gain return candidate, never an automatic
    # assertion that this return or common corridor was unnecessary.
    for end in range(profile['loop_min_gap'], n):
        starts = np.flatnonzero(candidates[:, end])
        starts = starts[starts >= previous_end]
        for start in starts[::-1]:
            if np.linalg.norm(np.ptp(positions[start:end+1], axis=0)) < profile['loop_min_spread_m']:
                continue
            loops.append({'start': int(start), 'end': int(end),
                          'path_m': float(travel[start, end]), 'new_area_m2': float(gain[start, end])})
            previous_end = end
            break
    return loops


def observed_stage(row, distance, radius):
    if not np.isfinite(distance).all():
        return 'other_or_invalid'
    ever = bool((distance < radius).any())
    final_near = bool(distance[-1] < radius)
    if row['success']:
        assert row['stop_called'] and final_near, row
        return 'success'
    if row['stop_called']:
        if final_near:
            return 'other_or_invalid'
        return 'stop_after_leaving_goal_region' if ever else 'stop_without_ever_entering_goal_region'
    if row['step_limit_reached']:
        if final_near:
            return 'time_limit_in_goal_region_without_stop'
        return 'time_limit_after_leaving_goal_region' if ever else 'time_limit_never_entered_goal_region'
    return 'other_or_invalid'


def classify(trace, row, rules, profile_name='base'):
    fields = {name: i for i, name in enumerate(trace['metric_fields'].tolist())}
    metrics = trace['metrics']
    position = trace['position_xyz'].astype(np.float64)
    rotation = trace['rotation_xyzw'].astype(np.float64)
    command = trace['command_mps_degps']
    assert len(position) == len(metrics) == row['steps']+1
    distance = metrics[:, fields['distance_to_goal']]
    area = metrics[:, fields['coverage_new_area_m2']]
    stop = metrics[1:, fields['stop_called']].astype(bool)
    moved = np.linalg.norm(np.diff(position, axis=0), axis=1)
    traveled = np.r_[0., np.cumsum(moved)]
    yaw = heading(rotation)
    p = rules['profiles'][profile_name]
    attempts = (command[1:, 0] >= p['forward_command_mps']) & ~stop
    blocked = attempts & (moved < p['blocked_move_m'])
    tail = min(p['tail_steps'], len(moved))
    tail_attempts = int(attempts[-tail:].sum())
    tail_blocked = int(blocked[-tail:].sum())
    ratio = tail_blocked/max(1, tail_attempts)
    longest = longest_true_run(blocked)
    longest_tail = longest_true_run(blocked[-tail:])
    loops = closed_loops(position, yaw, traveled, area, p)
    stationary = rules['stationary_turn_candidate']
    tail_start = max(0, row['steps']-stationary['tail_steps'])
    yaw_turn = np.abs(np.diff(np.unwrap(yaw[tail_start:])))
    stationary_turn = (row['steps']-tail_start >= stationary['minimum_steps'] and
                       traveled[-1]-traveled[tail_start] <= stationary['maximum_path_m'] and
                       np.rad2deg(yaw_turn.sum()) >= stationary['minimum_total_abs_yaw_deg'] and
                       area[-1]-area[tail_start] <= stationary['maximum_new_area_m2'])
    near = np.flatnonzero(distance < rules['success_radius_m'])
    target = np.asarray(row['goal_views_xyzw'], dtype=np.float64)
    if len(target):
        q = rotation/np.linalg.norm(rotation, axis=1, keepdims=True)
        target = target/np.linalg.norm(target, axis=1, keepdims=True)
        angles = np.rad2deg(2*np.arccos(np.clip(np.abs(q@target.T), 0, 1))).min(axis=1)
        near_aligned = int(((distance < rules['success_radius_m']) & (angles <= 25)).sum())
    else:
        near_aligned = None
    result = dict(observed_stage=observed_stage(row, distance, rules['success_radius_m']),
        ever_entered_goal_region=bool(len(near)), first_near_step=int(near[0]) if len(near) else None,
        last_near_step=int(near[-1]) if len(near) else None, near_steps=len(near), near_and_view_aligned_steps=near_aligned,
        longest_goal_region_run=longest_true_run(distance < rules['success_radius_m']),
        initial_distance=float(distance[0]), minimum_distance=float(distance.min()), final_distance=float(distance[-1]),
        path_length_m=float(traveled[-1]), height_range_m=float(np.ptp(position[:, 1])),
        initial_goal_height_difference_m=float(abs(row['goal_position'][1]-position[0, 1])),
        blocked_attempts=int(blocked.sum()), forward_attempts=int(attempts.sum()),
        blocked_fraction_of_forward_attempts=float(blocked.sum()/max(1, attempts.sum())),
        longest_blocked_run=longest, tail_blocked_fraction=float(ratio),
        tail_forward_attempts=tail_attempts, tail_longest_blocked_run=longest_tail,
        strong_blocked_tail_candidate=bool(tail_attempts >= 16 and ratio >= p['tail_blocked_fraction']
                                           and longest_tail >= p['blocked_consecutive_steps']),
        blocked_run_anywhere_candidate=bool(longest >= p['blocked_consecutive_steps']),
        low_gain_closed_loop_candidate=bool(loops), closed_loops=loops,
        stationary_turn_tail_candidate=bool(stationary_turn),
        new_area_m2=float(area[-1]), tail_new_area_m2=float(area[-1]-area[tail_start]),
        collision_steps=int(metrics[-1, fields['collisions']]),
        collision_count_divided_by_steps=float(metrics[-1, fields['collisions']]/row['steps']))
    return result


def load_rows(folder):
    result = []
    for path in sorted(folder.glob('*.jsonl')):
        result.extend(json.loads(line) for line in path.read_text().splitlines())
    assert len(result) == len({(r['scene_id'],r['episode_id']) for r in result})
    return result


def run(output):
    rules = json.loads((HERE/'analysis_rules.json').read_text())
    report = {'recorded_at': datetime.now(timezone(timedelta(hours=8))).isoformat(timespec='seconds'),
              'rules_sha256': hashlib.sha256((HERE/'analysis_rules.json').read_bytes()).hexdigest(),
              'observed_stage_is_not_a_causal_label': True, 'cases': {}, 'paired': {}}
    all_results = []
    by_case = {}
    videos = []
    checked_traces = 0
    for case in ['baseline', 'coverage256', 'coverage32']:
        folder = HERE/'full'/case/'diagnostic'
        raw = load_rows(folder/'diagnostics')
        assert len(raw) == 4200
        items = []
        for i, row in enumerate(raw):
            with np.load(folder/row['trace'], allow_pickle=False) as trace:
                values = {name: trace[name] for name in ['position_xyz', 'rotation_xyzw',
                          'command_mps_degps', 'action_normalized_linear_angular', 'metrics', 'metric_fields']}
                projection=projection_audit(trace)
            validate_trace(values,row)
            checked_traces += 1
            if row['video']:
                videos.append((folder/row['video'], row['steps']+1,row['goal_sha256']))
            digest = hashlib.sha256(np.c_[values['position_xyz'][1:], values['rotation_xyzw'][1:]].astype(np.float32).tobytes()).hexdigest()
            assert digest == row['pose_trace_sha256']
            profiles = {name: classify(values, row, rules, name) for name in rules['profiles']}
            record = dict(row)
            record.update(profiles=profiles, **projection, **profiles['base'],
                          human_primary_cause='', human_secondary_causes='', human_review_notes='')
            items.append(record)
            if i % 500 == 0:
                print(case, 'analyzed', i, flush=True)
        failed = [r for r in items if not r['success']]
        succeeded = [r for r in items if r['success']]
        summary = dict(episodes=len(items), failures=len(failed), success_rate=len(succeeded)/len(items),
                       spl=float(np.mean([r['spl'] for r in items])),
                       reference_pose_matches=sum(r['reference_pose_hash_equal'] for r in items),
                       reference_step_matches=sum(r['reference_steps_equal'] for r in items),
                       reference_outcome_matches=sum(r['reference_success_equal'] for r in items),
                       observed_stages=dict(Counter(r['observed_stage'] for r in failed)),
                       sensitivity={}, by_scene={})
        for profile in rules['profiles']:
            summary['sensitivity'][profile] = {
                'failed': {tag: sum(r['profiles'][profile][tag] for r in failed) for tag in TAGS},
                'succeeded': {tag: sum(r['profiles'][profile][tag] for r in succeeded) for tag in TAGS}}
        summary['failure_behavior_overlap'] = dict(Counter('|'.join(tag for tag in TAGS if r[tag]) or 'none_of_the_predeclared_flags' for r in failed))
        summary['failures_ever_near'] = sum(r['ever_entered_goal_region'] for r in failed)
        summary['failures_near_and_view_aligned'] = sum(bool(r['near_and_view_aligned_steps']) for r in failed)
        summary['stop_and_step_limit_both'] = sum(r['stop_called'] and r['step_limit_reached'] for r in failed)
        summary['oracle_stop_sr_increment_pp'] = 100*summary['failures_ever_near']/4200
        summary['failed_stop_distance_bins'] = dict(Counter(
            '1_to_1.5m' if r['final_distance'] < 1.5 else
            '1.5_to_2m' if r['final_distance'] < 2 else
            '2_to_5m' if r['final_distance'] < 5 else 'at_least_5m'
            for r in failed if r['stop_called']))
        summary['failed_minimum_distance_bins'] = dict(Counter(
            'below_1m' if r['minimum_distance'] < 1 else
            '1_to_1.5m' if r['minimum_distance'] < 1.5 else
            '1.5_to_2m' if r['minimum_distance'] < 2 else 'at_least_2m'
            for r in failed))
        # Descriptive strata and positive controls; these do not assign a cause.
        summary['behavior_by_stage'] = {
            stage: dict(n=sum(r['observed_stage'] == stage for r in failed),
                        **{tag: sum(r['observed_stage'] == stage and r[tag] for r in failed)
                           for tag in TAGS})
            for stage in sorted({r['observed_stage'] for r in failed})}
        summary['descriptive_by_outcome'] = {}
        for name, selected in [('failed', failed), ('succeeded', succeeded)]:
            summary['descriptive_by_outcome'][name] = {
                key: distribution([r[key] for r in selected])
                for key in ['steps', 'initial_distance', 'minimum_distance', 'final_distance',
                            'path_length_m', 'height_range_m', 'new_area_m2',
                            'collision_count_divided_by_steps', 'blocked_fraction_of_forward_attempts',
                            'tail_new_area_m2']}
        summary['failed_goal_region_dwell_steps'] = distribution([r['near_steps'] for r in failed if r['ever_entered_goal_region']])
        summary['failed_longest_goal_region_run'] = distribution([r['longest_goal_region_run'] for r in failed if r['ever_entered_goal_region']])
        summary['failed_steps_after_last_near'] = distribution([r['steps']-r['last_near_step'] for r in failed if r['ever_entered_goal_region']])
        summary['failed_multiheight_gt03m'] = sum(r['height_range_m'] > .3 for r in failed)
        summary['coverage_raster_projection_audit'] = dict(
            purpose='2D raster caveat, not simulator navigation validity or a causal label',
            audit_states=dict(Counter(r['coverage_projection_audit'] for r in failed)),
            assessable_failed_with_any_nonvalid_projection=sum(
                bool(r['coverage_projected_nonvalid_fraction']) for r in failed),
            low_gain_loop_candidates_with_any_nonvalid_projection=sum(
                r['low_gain_closed_loop_candidate'] and bool(r['coverage_projected_nonvalid_fraction']) for r in failed),
            low_gain_loop_candidates_with_all_projected_states_valid=sum(
                r['low_gain_closed_loop_candidate'] and r['coverage_projected_nonvalid_fraction'] == 0 for r in failed),
            low_gain_loop_candidates_with_unknown_height_maps=sum(
                r['low_gain_closed_loop_candidate'] and r['coverage_projected_nonvalid_fraction'] is None for r in failed),
            assessable_failed_projection_fraction=distribution([
                r['coverage_projected_nonvalid_fraction'] for r in failed
                if r['coverage_projected_nonvalid_fraction'] is not None]))
        for scene in sorted({r['scene_id'] for r in items}):
            selected = [r for r in items if r['scene_id'] == scene]
            failures = [r for r in selected if not r['success']]
            summary['by_scene'][Path(scene).stem] = dict(episodes=len(selected), failures=len(failures),
                stages=dict(Counter(r['observed_stage'] for r in failures)),
                behaviors={tag: sum(r[tag] for r in failures) for tag in TAGS})
        report['cases'][case] = summary
        by_case[case] = {(r['scene_id'],r['episode_id']):r for r in items}
        all_results.extend(items)
    assert set(by_case['baseline']) == set(by_case['coverage256']) == set(by_case['coverage32'])
    overlap = Counter()
    for key in by_case['baseline']:
        pattern = ''.join('F' if not by_case[c][key]['success'] else 'S' for c in ['baseline','coverage256','coverage32'])
        overlap[pattern] += 1
    report['paired']['success_failure_patterns_baseline_256_32'] = dict(overlap)
    report['paired']['models_differ_in_training_budget'] = True
    report['paired']['descriptive_pairs'] = {}
    for left, right in [('baseline','coverage256'), ('baseline','coverage32'), ('coverage256','coverage32')]:
        counts = Counter(('S' if by_case[left][key]['success'] else 'F') +
                         ('S' if by_case[right][key]['success'] else 'F') for key in by_case[left])
        report['paired']['descriptive_pairs'][left+'__'+right] = dict(counts)
    output.mkdir(parents=True, exist_ok=False)
    print('Auditing all complete videos:',len(videos),flush=True)
    with ThreadPoolExecutor(max_workers=4) as workers:
        frames = sum(workers.map(verify_video,videos))
    (output/'data_audit.json').write_text(json.dumps(dict(
        checked_traces=checked_traces, checked_video_files=len(videos),
        decoded_video_frames=frames, command_mapping_stop_flags_and_coverage_verified=True,
        trace_pose_hash_reconstruction_verified=True, saved_goal_png_matches_original_goal_sha=True),indent=2)+'\n')
    (output/'analysis.json').write_text(json.dumps(report, indent=2, allow_nan=False)+'\n')
    (output/'episodes.json').write_text(json.dumps(all_results, allow_nan=False)+'\n')
    fields = ['case','scene_id','episode_id','success','steps','observed_stage','initial_distance','minimum_distance',
              'final_distance','ever_entered_goal_region','near_and_view_aligned_steps','path_length_m','height_range_m',
              'first_near_step','last_near_step','near_steps','longest_goal_region_run',
              'stop_called','step_limit_reached','strong_blocked_tail_candidate','blocked_run_anywhere_candidate',
              'low_gain_closed_loop_candidate','stationary_turn_tail_candidate','longest_blocked_run','tail_blocked_fraction',
              'coverage_projection_audit','coverage_projected_nonvalid_fraction',
              'collision_count_divided_by_steps','new_area_m2','reference_pose_hash_equal','reference_success_equal',
              'trace','video','human_primary_cause','human_secondary_causes','human_review_notes']
    for filename,records in [('episodes.csv',all_results),
                             ('failed_episodes.csv',[r for r in all_results if not r['success']])]:
        with (output/filename).open('w') as f:
            writer = csv.DictWriter(f, fieldnames=fields, extrasaction='ignore')
            writer.writeheader();writer.writerows(records)
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, required=True)
    run(parser.parse_args().out)
