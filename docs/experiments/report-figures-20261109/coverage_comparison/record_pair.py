"""Single-episode recorder using SIGN's native config, trainer, policy and env.

No vector auto-reset: terminal observations belong to the recorded episode.
Run from repository root with PYTHONHASHSEED=0 and single-thread BLAS.
"""
import argparse
import csv
import gzip
import hashlib
import json
import os
from pathlib import Path
import random
import sys

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)
import numpy as np
import torch
from PIL import Image
import run_sim  # native registrations
from habitat.config import Config
from habitat.utils.gym_definitions import make_gym_from_config
from src.utils import get_config
from src.trainer import PPOTrainer, batch_obs, apply_obs_transforms_batch
from src.metric import ObservedCoverage


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def pixel_sha(array):
    return hashlib.sha256(np.ascontiguousarray(array).tobytes()).hexdigest()


def write_json(path, data):
    Path(path).write_text(json.dumps(data, indent=2, allow_nan=False) + '\n')


def record(task, method, out):
    ckpt = 'ckpt/' + ('nav_model.pth' if method == 'public' else 'coverage256_125952000.pth')
    out.mkdir(parents=True, exist_ok=False)
    random.seed(100); np.random.seed(100); torch.manual_seed(100); torch.cuda.manual_seed_all(100)
    torch.set_num_threads(1)
    opts = ['habitat.dataset.data_path', str(task), 'habitat.dataset.split', 'val',
            'habitat.dataset.content_scenes', "['*']", 'habitat.seed', '100',
            'habitat_baselines.num_environments', '1',
            'habitat_baselines.test_episode_count', '1',
            'habitat_baselines.eval.split', 'val',
            'habitat_baselines.eval.use_ckpt_config', 'False',
            'habitat_baselines.eval_ckpt_path_dir', ckpt,
            'habitat_baselines.rl.policy.safety_model_path', 'ckpt/safety_model.pth',
            'habitat.environment.max_episode_steps', '500',
            'habitat_baselines.video_option', '[]']
    cfg = get_config('exp_config/ppo_imagenav_gibson.yaml,policy,reward,sensors,eval',
                     opts, 'eval', str(out / 'native_config'), False, '', False)
    (out / 'config.yaml').write_text(str(cfg))
    env = make_gym_from_config(cfg)
    try:
        hab = env.env._env.habitat_env
        sim = hab.sim
        trainer = PPOTrainer(cfg)
        trainer.device = torch.device('cuda:0')
        trainer.obs_space = env.observation_space
        trainer.policy_action_space = env.action_space
        trainer.orig_policy_action_space = env.original_action_space
        trainer._setup_actor_critic_agent(cfg.habitat_baselines.rl.ppo)
        checkpoint = trainer.load_checkpoint(ckpt, map_location='cpu')
        loaded = trainer.agent.load_state_dict(checkpoint['state_dict'], strict=False)
        # Fail if a navigation tensor would silently remain randomly initialized.
        assert not [k for k in loaded.missing_keys if k.startswith(('actor_critic.net.', 'actor_critic.action_distribution.'))], loaded
        safe = trainer.load_checkpoint('ckpt/safety_model.pth', map_location='cpu')
        if 'state_dict' not in safe:
            safety_keys = list(safe)
            trainer.agent.actor_critic.Qc.load_state_dict(safe, strict=True)
        else:
            filtered = {k: v for k, v in safe['state_dict'].items() if 'Qc' in k}
            safety_keys = list(filtered)
            trainer.agent.load_state_dict(filtered, strict=False)
        policy = trainer.agent.actor_critic
        policy.eval()
        write_json(out / 'load_audit.json', {'missing': loaded.missing_keys,
                   'unexpected': loaded.unexpected_keys, 'safety_keys': safety_keys,
                   'navigation_checkpoint_sha256': sha(ckpt),
                   'safety_checkpoint_sha256': sha('ckpt/safety_model.pth'),
                   'native_act': 'deterministic=True, eval=False; no extra USL/recovery correction'})
        obs = env.reset()
        episode = hab.current_episode
        source_episode = json.load(gzip.open(task, 'rt'))['episodes'][0]
        assert str(episode.episode_id) == str(source_episode['episode_id'])
        assert Path(episode.scene_id).name == Path(source_episode['scene_id']).name
        goal_sha = pixel_sha(obs['imagegoal_sensor_v2'])
        initial_rgb_sha = pixel_sha(obs['rgb'])
        Image.fromarray(obs['imagegoal_sensor_v2']).save(out / 'goal.png')
        Image.fromarray(obs['rgb']).save(out / 'rgb_000.png')
        meter = ObservedCoverage(sim, Config({'meters_per_pixel': .1, 'visibility_dist': 3., 'fov': 90.}))
        meter.reset_metric(episode)
        initial_seen = meter._seen.copy()
        grid = meter._grid.copy()
        valid_union = grid == 1
        bounds = np.array(sim.pathfinder.get_bounds())
        hidden = torch.zeros(1, policy.num_recurrent_layers, cfg.habitat_baselines.rl.ppo.hidden_size, device='cuda')
        prev = torch.zeros(1, *env.action_space.shape, device='cuda')
        mask = torch.zeros(1, 1, dtype=torch.bool, device='cuda')
        cost = torch.zeros(1, 1, device='cuda')
        rows = []
        path_length = 0.
        previous_position = sim.get_agent_state().position.copy()

        def snapshot(step, raw=None, action=None):
            nonlocal path_length, previous_position
            state = sim.get_agent_state(); q = state.rotation
            displacement = float(np.linalg.norm(state.position - previous_position))
            path_length += displacement; previous_position = state.position.copy()
            metrics = hab.get_metrics()
            row = dict(step=step, x=float(state.position[0]), y=float(state.position[1]), z=float(state.position[2]),
                       qx=float(q.x), qy=float(q.y), qz=float(q.z), qw=float(q.w),
                       action_0=None if action is None else float(action[0]),
                       action_1=None if action is None else float(action[1]),
                       raw_action_0=None if raw is None else float(raw[0]),
                       raw_action_1=None if raw is None else float(raw[1]),
                       angular_velocity_degps=None if action is None else float(action[0]*15),
                       linear_velocity_mps=None if action is None else float((action[1]+1)*.125),
                       displacement_m=displacement, path_length_m=path_length,
                       delta_new_area_m2=meter.get_metric()['delta_m2'],
                       cumulative_new_area_m2=meter.get_metric()['new_area_m2'],
                       success=float(metrics['success']), spl=float(metrics['spl']),
                       distance_to_goal=float(metrics['distance_to_goal']),
                       stop_called=bool(hab.task.is_stop_called), episode_over=bool(hab.episode_over))
            rows.append(row)

        snapshot(0)
        for step in range(1, 501):
            batch = apply_obs_transforms_batch(batch_obs([obs], device=trainer.device), trainer.obs_transforms)
            batch['cost'] = cost
            with torch.inference_mode():
                _, actions, _, hidden = policy.act(batch, hidden, prev, mask, deterministic=True, eval=False)
            assert torch.isfinite(actions).all()
            raw = actions[0].cpu().numpy()
            action = np.clip(raw, env.action_space.low, env.action_space.high).astype(env.action_space.dtype)
            obs, reward, done, info = env.step(action)
            assert pixel_sha(obs['imagegoal_sensor_v2']) == goal_sha
            assert str(hab.current_episode.episode_id) == str(episode.episode_id)
            meter.update_metric(episode)
            valid_union |= meter._grid == 1
            snapshot(step, raw, action)
            prev.copy_(actions); mask.fill_(not done); cost.fill_(float(info['collisions.is_collision']))
            if step in [100, 200, 300, 400, 500] or done:
                Image.fromarray(obs['rgb']).save(out / f'rgb_{step:03d}.png')
            if step % 100 == 0 or done:
                print(method, Path(episode.scene_id).stem, episode.episode_id, step,
                      'success', rows[-1]['success'], 'area', rows[-1]['cumulative_new_area_m2'], flush=True)
            if done: break
        assert done
        with (out / 'steps.csv').open('w') as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)
        np.savez_compressed(out / 'map.npz', grid=grid, valid_union=valid_union,
                            initial_seen=initial_seen, seen=meter._seen, bounds=bounds)
        summary = dict(method=method, scene=Path(episode.scene_id).stem, episode_id=str(episode.episode_id),
                       seed=100, pythonhashseed=0, max_steps=500, recovery=False,
                       episode=source_episode, episode_file_sha256=sha(task),
                       goal_pixel_sha256=goal_sha, initial_rgb_pixel_sha256=initial_rgb_sha,
                       steps=step, success=rows[-1]['success'], spl=rows[-1]['spl'],
                       path_length_m=path_length, new_area_m2=rows[-1]['cumulative_new_area_m2'],
                       start_pose=[rows[0][k] for k in ['x','y','z','qx','qy','qz','qw']],
                       checkpoint_sha256=sha(ckpt), safety_sha256=sha('ckpt/safety_model.pth'),
                       termination='stop' if rows[-1]['stop_called'] else 'step_limit',
                       coverage=dict(meters_per_pixel=.1, radius_m=3, fov_deg=90, initial_view_excluded=True))
        write_json(out / 'summary.json', summary)
        return summary
    finally:
        env.close()


def main():
    p=argparse.ArgumentParser(); p.add_argument('--task',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    args=p.parse_args()
    assert os.environ.get('PYTHONHASHSEED') == '0'
    assert torch.cuda.is_available()
    task=args.task.resolve();out=args.out.resolve()
    records=[record(task, method, out/method) for method in ['public','coverage']]
    identical=['episode','episode_file_sha256','goal_pixel_sha256','initial_rgb_pixel_sha256','start_pose','seed','max_steps','safety_sha256']
    for key in identical: assert records[0][key] == records[1][key],key
    write_json(out/'pair_verification.json',dict(passed=True,identical_fields=identical,records=records))
    print('PAIRED_OK',out,flush=True)

if __name__=='__main__': main()
