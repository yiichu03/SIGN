"""Record a few deterministic SIGN successes/failures without changing SIGN."""
import os
import sys
import json
import hashlib
import math
import random
import subprocess
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import torch
import imageio_ffmpeg
from PIL import Image, ImageDraw, ImageFont

ROOT = Path('/scratch/e1538633/liuyi')
TREE = ROOT / 'SIGN-habitat-gs'
HERE = Path(__file__).resolve().parent
OUT = TREE / 'results/habitat_gs_videos_20261028'
CODE = '95eef9bf497bc1d010c7a4b35030fdce4123dce7'
os.chdir(TREE)
sys.path.insert(0, str(TREE))
import run_sim
import habitat_sim
from habitat.config import read_write
from habitat_baselines.config.default import get_config
from src.utils import change_habitat_config
from src.dataset import HabitatGSImageNavDatasetV1
from src.environment import GymHabitatEnvX
from src.trainer import PPOTrainer, batch_obs, apply_obs_transforms_batch

CONFIGS = ['exp_config/ppo_imagenav_gibson.yaml', 'src/config/policy.yaml',
           'src/config/reward.yaml', 'src/config/sensors.yaml', 'src/config/eval.yaml',
           'exp_config/ppo_imagenav_habitat_gs.yaml']
WEIGHTS = {'ckpt/nav_model.pth': '03fa71b514c8ee2fa272d6276499d51313a43b7d71bb31181c0150cc7c050d1a',
           'ckpt/safety_model.pth': 'b84d291e84216defb730d07d03cb6f25e3555ae447eb1e69057f3427b3c7ec31'}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def clean(value):
    if isinstance(value, dict):
        return {k: clean(v) for k, v in value.items()}
    if isinstance(value, (tuple, list, np.ndarray)):
        return [clean(v) for v in value]
    if isinstance(value, (float, np.floating)):
        return float(value) if math.isfinite(value) else 'NaN' if math.isnan(value) else '+Inf' if value > 0 else '-Inf'
    if isinstance(value, (np.integer, np.bool_)):
        return value.item()
    return value


def show(value):
    return f'{value:.3f}' if math.isfinite(value) else str(value).upper()


def diagnostic(sim, episode, step):
    position = sim.get_agent_state().position
    goal = episode.goals[0].position
    fresh = habitat_sim.ShortestPath()
    fresh.requested_start, fresh.requested_end = position, goal
    found = sim.pathfinder.find_path(fresh)
    return clean({'step': step, 'agent_xyz': position.tolist(), 'goal_xyz': goal,
                  'agent_is_navigable': sim.pathfinder.is_navigable(position),
                  'agent_snapped_xyz': sim.pathfinder.snap_point(position).tolist(),
                  'fresh_path_found': found, 'fresh_distance': fresh.geodesic_distance,
                  'agent_island': sim.pathfinder.get_island(position),
                  'goal_island': sim.pathfinder.get_island(goal)})


def render_video(path, frames, goal, scene, episode, category, metrics):
    font_path = Path(sys.prefix) / f'lib/python{sys.version_info.major}.{sys.version_info.minor}/site-packages/matplotlib/mpl-data/fonts/ttf/DejaVuSans.ttf'
    font = ImageFont.truetype(str(font_path), 18)
    small = ImageFont.truetype(str(font_path), 16)
    large = ImageFont.truetype(str(font_path), 23)
    goal_image = Image.fromarray(goal).resize((384, 384), Image.Resampling.BILINEAR)
    temporary = path.with_name(path.stem + '.part.mp4')
    writer = imageio_ffmpeg.write_frames(str(temporary), (768, 544), fps=10,
        codec='libx264', pix_fmt_out='yuv420p', ffmpeg_log_level='error',
        output_params=['-crf', '20', '-preset', 'fast', '-threads', '4', '-movflags', '+faststart'])
    writer.send(None)
    final_image = None
    try:
        for index, frame in enumerate(frames):
            canvas = Image.new('RGB', (768, 544), (19, 23, 30))
            canvas.paste(Image.fromarray(frame['rgb']).resize((384, 384), Image.Resampling.BILINEAR), (0, 64))
            canvas.paste(goal_image, (384, 64))
            draw = ImageDraw.Draw(canvas)
            color = (71, 214, 129) if category == 'success' else (255, 124, 113)
            draw.text((12, 6), f'{category.upper()}  |  {scene}  |  episode {episode}', fill=color, font=font)
            draw.text((12, 36), 'CURRENT VIEW (policy RGB, enlarged)', fill='white', font=small)
            draw.text((396, 36), 'GOAL IMAGE (policy input, enlarged)', fill='white', font=small)
            draw.text((12, 459), f'Step {index:03d}/500   Distance {show(frame["distance"])} m   Collision {frame["collision"]}', fill='white', font=font)
            draw.text((12, 490), f'Final success {int(metrics["success"])}   SPL {metrics["spl"]:.3f}   View match {metrics["view_match"]:.2f}', fill=color, font=large)
            draw.text((12, 523), 'Deterministic released SIGN | 10 steps/s playback | original 128x128 inputs', fill=(180, 185, 195), font=small)
            if frame['collision']:
                draw.rectangle((1, 65, 382, 446), outline=(255, 65, 65), width=4)
            final_image = np.ascontiguousarray(canvas)
            writer.send(final_image)
        for _ in range(20):
            writer.send(final_image)
    finally:
        writer.close()
    temporary.rename(path)
    return len(frames) + 20


def main():
    assert os.environ.get('PYTHONHASHSEED') == '0' and torch.cuda.is_available()
    assert subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip() == CODE
    assert not subprocess.check_output(['git', 'status', '--porcelain'], text=True)
    assert habitat_sim.__version__ == '0.3.3'
    assert all(sha(path) == expected for path, expected in WEIGHTS.items())
    OUT.mkdir(parents=True, exist_ok=False)
    cfg = change_habitat_config(get_config(CONFIGS, [
        'habitat.dataset.content_scenes', "['*']", 'habitat_baselines.num_environments', '1',
        'habitat_baselines.eval.split', 'val', 'habitat_baselines.eval_ckpt_path_dir', 'ckpt/nav_model.pth']))
    with read_write(cfg):
        cfg.habitat.environment.iterator_options.shuffle = False
        cfg.habitat.environment.iterator_options.cycle = False
        cfg.habitat.environment.iterator_options.group_by_scene = False
        cfg.habitat_baselines.log_file = str(HERE / 'model.log')
    (HERE / 'config.yaml').write_text(str(cfg))
    dataset = HabitatGSImageNavDatasetV1(cfg.habitat.dataset)
    by_scene = defaultdict(list)
    for ep in dataset.episodes:
        by_scene[Path(ep.scene_id).name.removesuffix('.gs.ply')].append(ep)
    order = sorted(by_scene, key=lambda name: (not name.startswith('scene'), name))
    for episodes in by_scene.values():
        episodes.sort(key=lambda ep: int(ep.episode_id))
    dataset.episodes = [by_scene[scene][index] for index in range(4) for scene in order]
    random.seed(100); np.random.seed(100); torch.manual_seed(100); torch.set_num_threads(1)
    env = GymHabitatEnvX(config=cfg.habitat, dataset=dataset)
    env.seed(100)
    hab = env.env._env.habitat_env
    trainer = PPOTrainer(cfg)
    trainer.device = torch.device('cuda:0')
    trainer.obs_space = env.observation_space
    trainer.policy_action_space = env.action_space
    trainer.orig_policy_action_space = env.original_action_space
    trainer._setup_actor_critic_agent(cfg.habitat_baselines.rl.ppo)
    checkpoint = torch.load('ckpt/nav_model.pth', map_location='cpu', weights_only=False)
    trainer.agent.load_state_dict(checkpoint['state_dict'], strict=False)
    safety = torch.load('ckpt/safety_model.pth', map_location='cpu', weights_only=False)
    trainer.agent.load_state_dict({k: v for k, v in safety['state_dict'].items() if 'Qc' in k}, strict=False)
    policy = trainer.agent.actor_critic
    policy.eval()
    selected = {'success': [], 'failure': []}
    selected_scenes = {'success': set(), 'failure': set()}
    attempts = []
    try:
        for candidate in range(len(dataset.episodes)):
            obs = env.reset()
            ep = hab.current_episode
            scene = Path(ep.scene_id).name.removesuffix('.gs.ply')
            goal = obs['imagegoal_sensor_v2'].copy()
            goal_sha = hashlib.sha256(goal.tobytes()).hexdigest()
            hidden = torch.zeros(1, policy.num_recurrent_layers, cfg.habitat_baselines.rl.ppo.hidden_size, device='cuda')
            previous = torch.zeros(1, *env.action_space.shape, device='cuda')
            mask = torch.zeros(1, 1, dtype=torch.bool, device='cuda')
            cost = torch.zeros(1, 1, device='cuda')
            metrics = hab.get_metrics()
            frames = [{'rgb': obs['rgb'].copy(), 'distance': float(metrics['distance_to_goal']), 'collision': False}]
            first_nonfinite = None
            done = False
            for step in range(1, 501):
                batch = apply_obs_transforms_batch(batch_obs([obs], device=trainer.device), trainer.obs_transforms)
                batch['cost'] = cost
                with torch.inference_mode():
                    _, actions, _, hidden = policy.act(batch, hidden, previous, mask, deterministic=True, eval=False)
                assert torch.isfinite(actions).all()
                action = np.clip(actions[0].cpu().numpy(), env.action_space.low, env.action_space.high).astype(env.action_space.dtype)
                obs, reward, done, info = env.step(action)
                assert hashlib.sha256(obs['imagegoal_sensor_v2'].tobytes()).hexdigest() == goal_sha
                metrics = hab.get_metrics()
                distance = float(metrics['distance_to_goal'])
                collision = bool(info['collisions.is_collision'])
                frames.append({'rgb': obs['rgb'].copy(), 'distance': distance, 'collision': collision})
                if first_nonfinite is None and (not math.isfinite(distance) or not math.isfinite(float(reward))):
                    first_nonfinite = diagnostic(hab.sim, ep, step)
                    first_nonfinite.update(reported_distance=clean(distance), reward=clean(reward))
                previous.copy_(actions); mask.fill_(not done); cost.fill_(float(collision))
                if done:
                    break
            assert done, 'A video must contain the whole episode'
            category = 'success' if float(metrics['success']) == 1.0 else 'failure'
            record = {'candidate': candidate, 'scene': scene, 'episode_id': str(ep.episode_id),
                      'steps': step, 'category': category, 'final_metrics': clean(metrics),
                      'first_nonfinite': first_nonfinite, 'goal_rgb_sha256': goal_sha,
                      'termination': 'timeout' if step == 500 else 'task_ended', 'selected': False}
            if len(selected[category]) < 3 and (scene not in selected_scenes[category] or candidate >= 2 * len(order)):
                filename = f'{category}_{len(selected[category])+1:02d}_{scene}_ep{ep.episode_id}.mp4'
                path = OUT / filename
                count = render_video(path, frames, goal, scene, ep.episode_id, category, metrics)
                record.update(selected=True, video=filename, video_frames=count, fps=10, video_sha256=sha(path))
                selected[category].append(record)
                selected_scenes[category].add(scene)
            attempts.append(record)
            print(json.dumps(clean(record), allow_nan=False), flush=True)
            (HERE / 'progress.json').write_text(json.dumps(clean({'selected': selected, 'attempts': attempts}), indent=2, allow_nan=False) + '\n')
            if all(len(selected[key]) == 3 for key in selected):
                break
        assert all(len(selected[key]) == 3 for key in selected), 'Did not obtain three recordings for each outcome'
        manifest = {'created_at': datetime.now(ZoneInfo('Asia/Singapore')).isoformat(timespec='seconds'),
                    'source_commit': CODE, 'checkpoint_sha256': WEIGHTS, 'job_id': os.environ.get('PBS_JOBID'),
                    'purpose': 'New deterministic example recordings with the full-evaluation protocol; not recovered original videos or a new benchmark.',
                    'policy_input': '128x128 RGB and image goal, enlarged only in the video',
                    'seed': 100, 'pythonhashseed': 0, 'max_episode_steps': 500,
                    'success_definition': 'Original Success metric, including stop and distance threshold',
                    'playback_fps': 10, 'simulation_time_step_s': 1.0,
                    'videos': selected['success'] + selected['failure'], 'candidate_attempts': len(attempts)}
        (OUT / 'manifest.json').write_text(json.dumps(clean(manifest), indent=2, allow_nan=False) + '\n')
        print('COMPLETE:', OUT, '6 videos', flush=True)
    finally:
        env.close()


if __name__ == '__main__':
    main()
