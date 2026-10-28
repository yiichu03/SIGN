#!/usr/bin/env python3
"""Replay saved poses on their saved raster. No simulator, policy, or resampling."""
import argparse
import difflib
import gzip
import hashlib
import json
import shutil
from pathlib import Path

import numpy as np


def dump(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def windows(length):
    if type(length) is not int or length <= 0:
        raise ValueError('Trajectory must contain positive actual action count')
    unique = {}
    for requested in (128, 256):
        start = max(0, length - requested)
        unique.setdefault((start, length), []).append(requested)
    return [dict(start=start, end=end, action_count=end-start,
                 history_action_count=start, requested_windows=requests,
                 short_for=[h for h in requests if end-start < h])
            for (start, end), requests in unique.items()]


def area_stats(prior, final, valid, mpp, actions):
    if actions <= 0 or mpp <= 0 or prior.shape != final.shape or prior.shape != valid.shape:
        raise ValueError('Invalid raster or action count')
    prior, final, valid = prior.astype(bool), final.astype(bool), valid.astype(bool)
    if np.any(prior & valid & ~final):
        raise ValueError('Cumulative observation cannot shrink')
    old = int(np.count_nonzero(prior & valid))
    new = int(np.count_nonzero(final & ~prior & valid))
    total = int(np.count_nonzero(final & valid))
    assert old + new == total
    return dict(action_count=actions, new_area_m2=new*mpp*mpp,
                new_area_m2_per_action=new*mpp*mpp/actions,
                prior_seen_area_m2=old*mpp*mpp, total_covered_area_m2=total*mpp*mpp,
                new_valid_cells=new, prior_valid_cells=old, total_valid_cells=total)


def history_prompt(old):
    new = old.replace(
        '深蓝色为初始已见区域，浅蓝色为本段新增观测区域；红线为轨迹，绿色圆点为起点，深色叉为终点。',
        '深蓝色为段前累计已见区域，浅蓝色为本段真正新增观测区域；黄线（如显示）是历史轨迹，红线是当前整段轨迹，绿色圆点为当前红色段起点，深色叉为当前段终点。只评价当前红色段，历史仅作为背景。')
    new = new.replace(
        'action_count是实际动作数，new_area_m2是扣除初始视野后的新增覆盖面积，',
        'action_count只计算当前段的实际动作数，new_area_m2是扣除段前累计已见后的新增覆盖面积，')
    new = new.replace(
        '面积是二维可通行区视域代理，不是RGB表面积。',
        'prior_seen_area_m2是深蓝色面积；total_covered_area_m2是总覆盖面积=深蓝+浅蓝=prior_seen_area_m2+new_area_m2，并随图提供。面积是二维可通行区视域代理，不是RGB表面积。')
    if new == old or new[new.index('请独立判断三类质量：'):] != old[old.index('请独立判断三类质量：'):]:
        raise ValueError('Prompt replacement or unchanged ABC rubric check failed')
    return new


def render(path, coords, grid, prior, final, start, end, bounds, title, variant, mpp):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Patch
    from matplotlib.lines import Line2D
    valid = grid == 1
    rgb = np.ones((*valid.shape, 3))
    rgb[valid] = [.83, .84, .85]
    rgb[prior.astype(bool) & valid] = [.61, .70, .78]
    rgb[final.astype(bool) & ~prior.astype(bool) & valid] = [.65, .84, .92]
    fig, ax = plt.subplots(figsize=(10, 8))
    ax.imshow(rgb, interpolation='nearest')
    if variant == 'history' and start:
        # Wide yellow dashes remain visible on both sides of an overlapping red line.
        ax.plot(coords[:start+1, 1], coords[:start+1, 0],
                c='#f2bd27', lw=4.8, linestyle=(0, (4, 2)), zorder=3)
    current = coords[start:end+1]
    ax.plot(current[:, 1], current[:, 0], c='#b82b35', lw=1.5, zorder=4)
    ax.scatter(current[0, 1], current[0, 0], s=50, c='#149253', edgecolors='white', zorder=5)
    ax.scatter(current[-1, 1], current[-1, 0], s=50, c='#222c41', marker='X', zorder=6)
    ax.set_xlim(bounds[:2]); ax.set_ylim(bounds[2:]); ax.set_aspect('equal'); ax.axis('off')
    ax.set_title(title, fontsize=12)
    xx, yy = bounds[0]+5, bounds[2]-5
    ax.plot([xx, xx+2/mpp], [yy, yy], c='black', lw=3)
    ax.text(xx+1/mpp, yy-3, '2 m', ha='center', fontsize=9)
    historical = variant != 'legacy'
    legend = [Patch(color=c, label=label) for c, label in [
        ('#d4d6d9', 'Navigable floor'),
        ('#9cb3c7', 'Pre-window coverage' if historical else 'Initial coverage'),
        ('#a6d6eb', 'New coverage')]]
    if historical:
        legend.append(Line2D([0], [0], color='#f2bd27', lw=4.8, linestyle='--',
                             label='History (yellow, when shown)'))
    legend += [Line2D([0], [0], color='#b82b35', label='Current path' if historical else 'Path'),
               Line2D([0], [0], marker='o', color='w', markerfacecolor='#149253', label='Start'),
               Line2D([0], [0], marker='X', color='w', markerfacecolor='#222c41', label='End')]
    # Fixed axes, bounds, pixels, and scale in all matched variants.
    fig.legend(handles=legend, loc='lower center', ncol=4 if historical else 3)
    fig.subplots_adjust(bottom=.12)
    fig.savefig(path, dpi=140)
    plt.close(fig)


def prepare(source, out, prompt):
    from habitat.utils.visualizations import fog_of_war
    from scipy.ndimage import distance_transform_edt
    out.mkdir(parents=True, exist_ok=False)
    for sub in ['images', 'sources', 'masks', 'prompts', 'audit']:
        (out/sub).mkdir()
    old_prompt = prompt.read_text()
    assert sha(prompt) == sha(source/'prompts/coverage_abc_v1.txt')
    new_prompt = history_prompt(old_prompt)
    (out/'prompts/legacy.txt').write_text(old_prompt)
    (out/'prompts/history.txt').write_text(new_prompt)
    (out/'prompts/history.diff').write_text(''.join(difflib.unified_diff(
        old_prompt.splitlines(True), new_prompt.splitlines(True),
        fromfile='legacy.txt', tofile='history.txt')))
    segments, inputs, sources, replays, aliases = [], [], [], [], []
    for cohort in ['pilot', 'diverse']:
        spec = json.loads((source/'manifests'/f'{cohort}.json').read_text())
        old_scores = json.loads((source/'evidence/probability'/f'{cohort}_2b/scores.json').read_text())['results']
        for name in ['run.json', 'scores.json', 'verification.json']:
            shutil.copyfile(source/'evidence/probability'/f'{cohort}_2b'/name,
                            out/'sources'/f'{cohort}_2b_{name}')
        score_map = {(r['group_id'], r['id']): r for r in old_scores}
        for group in spec['groups']:
            for item in group['items']:
                trajectory_id = f"{cohort}_{group['id']}_{item['id']}"
                src = source/'evidence/trajectories'/cohort/group['id']/item['id']
                dest = out/'sources'/trajectory_id
                dest.mkdir()
                for name in ['trajectory.json.gz', 'display_map_data.npz', 'map_data.npz', 'task.json.gz']:
                    shutil.copyfile(src/name, dest/name)
                original = source/'manifests'/item['image']
                shutil.copyfile(original, dest/'original.png')
                assert sha(original) == item['image_sha256']
                old_score = score_map[(group['id'], item['id'])]
                assert old_score['image_sha256'] == item['image_sha256']
                dump(dest/'original_2b_score.json', old_score)
                t = json.loads(gzip.decompress((dest/'trajectory.json.gz').read_bytes()))
                poses, length = t['poses'], t['window_steps']
                assert length == item['action_count'] == len(poses)-1
                assert [p['step'] for p in poses] == list(range(length+1))
                with np.load(dest/'display_map_data.npz') as m:
                    grid, coords, mpp = m['grid'], m['coords'], float(m['mpp'])
                    saved_initial, saved_final = m['initial_seen'], m['seen']
                    saved_valid = m['valid_union']
                assert mpp == .025 and t['fov'] == 90 and t['radius'] == 3
                assert len(coords) == len(poses) and np.array_equal(grid == 1, saved_valid)
                valid = grid == 1
                dist, nearest = distance_transform_edt(~valid, return_indices=True)
                origins = []
                for rc in coords:
                    assert float(dist[tuple(rc)]) <= 2.01
                    origins.append(np.array([nearest[0][tuple(rc)], nearest[1][tuple(rc)]], dtype=np.int64))
                def observe(seen, i):
                    return fog_of_war.reveal_fog_of_war(
                        grid, seen, origins[i], poses[i]['heading_rad'], fov=90, max_line_len=3/mpp)
                cumulative, seen = [], np.zeros_like(grid)
                for i in range(length+1):
                    seen = observe(seen, i)
                    cumulative.append(seen.copy())
                assert np.array_equal(cumulative[0], saved_initial)
                assert np.array_equal(cumulative[-1], saved_final)
                ys, xs = np.where(valid)
                bounds = [int(xs.min()-8), int(xs.max()+8),
                          int(ys.max()+(8 if cohort == 'pilot' else 100)), int(ys.min()-8)]
                source_record = dict(trajectory_id=trajectory_id, scene=Path(t['scene_id']).stem,
                    episode_id=t['episode_id'], original_actions=length, image_sha256=sha(original),
                    files={p.name:sha(p) for p in dest.iterdir()}, source_relative=str(src.relative_to(source)))
                sources.append(source_record)
                for w in windows(length):
                    start, end = w['start'], w['end']
                    sid = f'{trajectory_id}_s{start:03d}_e{end:03d}'
                    for h in w['requested_windows']:
                        aliases.append(dict(trajectory_id=trajectory_id, requested_window=h,
                            segment_id=sid, short=length < h, duplicate_alias=len(w['requested_windows']) > 1))
                    isolated = np.zeros_like(grid)
                    for i in range(start, end+1):
                        isolated = observe(isolated, i)
                        if i == start:
                            isolated_initial = isolated.copy()
                    history = area_stats(cumulative[start], cumulative[end], valid, mpp, end-start)
                    legacy = area_stats(isolated_initial, isolated, valid, mpp, end-start)
                    mask_name = f'masks/{sid}.npz'
                    np.savez_compressed(out/mask_name, grid=grid, valid=valid, prior_seen=cumulative[start],
                        final_seen=cumulative[end], legacy_initial_seen=isolated_initial,
                        legacy_seen=isolated, coords=coords, mpp=mpp, start=start, end=end)
                    # Observable cues only; never machine-assigned human labels.
                    delta_xy = np.diff(np.asarray([p['position_xyz'] for p in poses[start:end+1]])[:, [0,2]], axis=0)
                    collision_count = sum(bool(p.get('collision', False)) for p in poses[start+1:end+1])
                    stalled = int(np.count_nonzero(np.linalg.norm(delta_xy, axis=1) < .02))
                    previous_path = {tuple(rc) for rc in coords[:start]}
                    overlap = sum(tuple(rc) in previous_path for rc in coords[start+1:end+1]) / (end-start) if start else 0.
                    segment = dict(id=sid, trajectory_id=trajectory_id, cohort=cohort,
                        scene=source_record['scene'], episode_id=t['episode_id'], **w, masks=mask_name,
                        history_validation_eligible=start > 0, bounds=bounds, meters_per_pixel=mpp,
                        collision_actions=collision_count, low_translation_actions=stalled,
                        exact_history_path_cell_fraction=overlap, legacy_stats=legacy, history_stats=history,
                        current_start_position=poses[start]['position_xyz'], end_position=poses[end]['position_xyz'])
                    segments.append(segment)
                    for variant in ['legacy', 'history'] + (['history_no_yellow'] if start else []):
                        historical = variant != 'legacy'
                        stats = history if historical else legacy
                        stat_keys = ['action_count','new_area_m2','new_area_m2_per_action']
                        if historical:
                            stat_keys += ['prior_seen_area_m2','total_covered_area_m2']
                        metadata = {k:stats[k] for k in stat_keys}
                        image_name = f'images/{sid}_{variant}.png'
                        if variant == 'legacy' and start == 0:
                            # Exact published PNG: strict old-score reuse gate below.
                            shutil.copyfile(original, out/image_name)
                        else:
                            prior = cumulative[start] if historical else isolated_initial
                            final = cumulative[end] if historical else isolated
                            covered = stats['total_valid_cells'] / np.count_nonzero(valid) * 100
                            new_pct = stats['new_valid_cells'] / np.count_nonzero(valid) * 100
                            prefix = f"{item['id']} | {end-start} actions" if cohort == 'pilot' else f"{source_record['scene']} / task {t['episode_id']} / {item['id']} | {end-start} actions"
                            title = prefix + f"\nCovered {covered:.1f}% | New {new_pct:.1f}%"
                            render(out/image_name, coords, grid, prior, final, start, end, bounds, title, variant, mpp)
                        prompt_name = 'prompts/history.txt' if historical else 'prompts/legacy.txt'
                        reuse = None
                        if variant == 'legacy' and start == 0:
                            assert sha(out/image_name) == old_score['image_sha256']
                            assert all(metadata[k] == old_score[k] for k in stat_keys)
                            assert sha(out/prompt_name) == old_score['prompt_version']
                            assert old_score['valid']
                            reuse = str((dest/'original_2b_score.json').relative_to(out))
                        inputs.append(dict(id=sid+'_'+variant, segment_id=sid, trajectory_id=trajectory_id,
                            cohort=cohort, variant=variant,
                            image=image_name, image_sha256=sha(out/image_name), prompt=prompt_name,
                            prompt_version=sha(out/prompt_name), metadata=metadata, reused_score=reuse))
                replays.append(dict(trajectory_id=trajectory_id, initial_and_final_masks_exact=True,
                    actions=length, fog_origin_max_adjustment_m=float(max(dist[tuple(rc)] for rc in coords))*mpp))
    assert len(sources) == 32 and len(aliases) == 64
    dump(out/'sources.json', sources)
    dump(out/'windows.json', dict(segments=segments, requests=aliases, inputs=inputs))
    dump(out/'audit/replay.json', replays)
    dump(out/'audit/preparation.json', dict(trajectories=len(sources), window_requests=len(aliases),
        unique_segments=len(segments), duplicate_requests_removed=len(aliases)-len(segments),
        history_segments=sum(s['history_action_count'] > 0 for s in segments),
        full128=sum(s['action_count']==128 for s in segments),
        full256=sum(s['action_count']==256 for s in segments),
        short_segments=sum(bool(s['short_for']) for s in segments),
        images=len(inputs), reused_scores=sum(bool(i['reused_score']) for i in inputs),
        masks_replayed_exact=True, no_resampling=True, map_resolution_m=.025,
        radius_m=3, fov=90, total_definition='prior_seen_area_m2 + new_area_m2',
        current_actions='poses[start+1:end+1]; current path poses[start:end+1]',
        prior_observations='poses[0:start+1], including shared segment-start observation'))
    print((out/'audit/preparation.json').read_text())


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--prompt', type=Path, required=True)
    a = p.parse_args()
    prepare(a.source.resolve(), a.out.resolve(), a.prompt.resolve())
