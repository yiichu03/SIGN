"""Passive telemetry around the existing native environment, before auto-reset."""
import hashlib
import json
import os
from pathlib import Path
import random

import gym
import habitat
import imageio.v2 as imageio
import numpy as np
from PIL import Image, ImageDraw
from habitat.utils.gym_adapter import HabGymWrapper

from control_recording_env import RecordingNavEnv

HERE = Path(__file__).resolve().parent
CASE = os.environ['DIAG_CASE']
OUTPUT = Path(os.environ['DIAG_OUTPUT'])
PLAN = json.loads((HERE/'plan.json').read_text())['cases'][CASE]
REFERENCE = json.loads(Path(PLAN['reference']).read_text())
CONTROLS = set(PLAN['success_controls'])
METRIC_FIELDS = ['distance_to_goal', 'distance_to_view', 'view_angle', 'success',
                 'view_match', 'collisions', 'collision_step', 'coverage_delta_m2',
                 'coverage_new_area_m2', 'stop_called', 'step_limit_reached',
                 'environment_episode_over']


class DiagnosticNavEnv(RecordingNavEnv):
    def reset(self):
        obs = super().reset()
        hab = self.habitat_env
        ep = hab.current_episode
        self._key = Path(ep.scene_id).stem + ':' + str(ep.episode_id)
        self._reference = REFERENCE[self._key]
        assert self._eval_goal_sha == self._reference['goal_sha256'], self._key
        assert np.allclose(self._eval_start, self._reference['start_position'], rtol=0, atol=1e-6)
        self._positions, self._rotations, self._metrics = [], [], []
        self._normalized_actions, self._physical_actions = [[0., 0.]], [[0., 0.]]
        self._frames = [np.asarray(obs['rgb'], dtype=np.uint8).copy()]
        self._goal_image = np.asarray(obs['imagegoal_sensor_v2'], dtype=np.uint8).copy()
        self._goal_position = [float(v) for v in ep.goals[0].position]
        self._goal_views = hab.task.sensor_suite.sensors['imagegoal_sensor_v2'].get_goal_views()
        coverage = hab.task.measurements.measures['observed_coverage']
        self._initial_grid = coverage._grid.copy()
        self._initial_seen = coverage._seen.copy()
        self._bounds = np.asarray(hab.sim.pathfinder.get_bounds(), dtype=np.float64)
        self._capture(hab.get_metrics())
        return obs

    def _capture(self, info):
        hab = self.habitat_env
        state = hab.sim.get_agent_state()
        q = state.rotation
        collision = info['collisions']
        if collision is None:
            # Habitat's collision measure is None immediately after reset and
            # creates its count on the first action. Normalize only the local
            # initial trace row; never mutate the original metric/info object.
            assert hab._elapsed_steps == 0, 'Missing collision metric after an action'
            collision = {'count': 0, 'is_collision': False}
        self._positions.append(np.asarray(state.position, dtype=np.float32).copy())
        self._rotations.append([q.x, q.y, q.z, q.w])
        self._metrics.append([
            float(info['distance_to_goal']), float(info['distance_to_view']),
            float(info['view_angle']), float(info['success']), float(info['view_match']),
            float(collision['count']), float(collision['is_collision']),
            float(info['observed_coverage']['delta_m2']), float(info['observed_coverage']['new_area_m2']),
            float(getattr(hab.task, 'is_stop_called', False)),
            float(hab._elapsed_steps >= hab._max_episode_steps), float(hab.episode_over)])

    def step(self, *args, **kwargs):
        # Read the same named arguments which ContinuousAction receives. Do not
        # reinterpret the Gym flattened-vector ordering or mutate the dictionary.
        action = kwargs['action']['action_args']
        lin = float(np.asarray(action['linear_velocity']).reshape(-1)[0])
        ang = float(np.asarray(action['angular_velocity']).reshape(-1)[0])
        cfg = self._config.task.actions.continuous_control
        physical = [float(cfg.lin_vel_range[0] + (lin+1.)/2.*(cfg.lin_vel_range[1]-cfg.lin_vel_range[0])),
                    float(cfg.ang_vel_range[0] + (ang+1.)/2.*(cfg.ang_vel_range[1]-cfg.ang_vel_range[0]))]
        obs, reward, done, info = super().step(*args, **kwargs)
        assert self._eval_steps == self.habitat_env._elapsed_steps
        self._normalized_actions.append([lin, ang])
        self._physical_actions.append(physical)
        self._capture(info)
        self._frames.append(np.asarray(obs['rgb'], dtype=np.uint8).copy())
        if done:
            # Encoding and archival may use libraries with private randomness.
            # Preserve the two global CPU RNGs as an additional passivity guard.
            py_state, np_state = random.getstate(), np.random.get_state()
            try:
                self._finish(info)
            finally:
                random.setstate(py_state)
                np.random.set_state(np_state)
        return obs, reward, done, info

    def _finish(self, info):
        hab = self.habitat_env
        scene, episode = self._key.split(':')
        assert episode.isdigit()
        basename = scene + '/' + episode
        trace = OUTPUT/'traces'/(basename+'.npz')
        trace.parent.mkdir(parents=True, exist_ok=True)
        assert not trace.exists(), self._key
        metrics = np.asarray(self._metrics, dtype=np.float64)
        steps = self._eval_steps
        assert len(metrics) == len(self._frames) == steps+1
        reference = self._reference
        captured = bool(os.environ['DIAG_PHASE'] == 'smoke' or not info['success']
                        or not reference['success'] or self._key in CONTROLS)
        stop = bool(getattr(hab.task, 'is_stop_called', False))
        row = dict(scene_id=hab.current_episode.scene_id, episode_id=episode, case=CASE,
                   steps=steps, success=float(info['success']), spl=float(info['spl']),
                   view_match=float(info['view_match']), final_distance=float(info['distance_to_goal']),
                   minimum_distance=float(np.min(metrics[:, 0])), stop_called=stop,
                   step_limit_reached=bool(hab._elapsed_steps >= hab._max_episode_steps),
                   underlying_episode_over=bool(hab.episode_over),
                   goal_sha256=self._eval_goal_sha, pose_trace_sha256=self._eval_trace.hexdigest(),
                   reference_pose_hash_equal=self._eval_trace.hexdigest() == reference['pose_trace_sha256'],
                   reference_steps_equal=steps == reference['steps'],
                   reference_success_equal=float(info['success']) == reference['success'],
                   reference_success=reference['success'], reference_steps=reference['steps'],
                   start_position=self._eval_start, goal_position=self._goal_position,
                   goal_views_xyzw=self._goal_views, trace=str(trace.relative_to(OUTPUT)),
                   video=None, captured_images=captured,
                   nonfinite_distance_samples=int((~np.isfinite(metrics[:, 0])).sum()))
        arrays = dict(position_xyz=np.asarray(self._positions, dtype=np.float32),
                      rotation_xyzw=np.asarray(self._rotations, dtype=np.float32),
                      action_normalized_linear_angular=np.asarray(self._normalized_actions, dtype=np.float32),
                      command_mps_degps=np.asarray(self._physical_actions, dtype=np.float64),
                      metrics=metrics, metric_fields=np.asarray(METRIC_FIELDS),
                      map_bounds_xyz=self._bounds, goal_position_xyz=np.asarray(self._goal_position),
                      metadata_json=np.asarray(json.dumps(row, allow_nan=False)))
        if captured:
            coverage = hab.task.measurements.measures['observed_coverage']
            arrays.update(initial_grid=self._initial_grid, initial_seen=self._initial_seen,
                          final_grid=coverage._grid, final_seen=coverage._seen,
                          meters_per_pixel=np.asarray(coverage.mpp))
            video = OUTPUT/'videos'/(basename+'.mp4')
            video.parent.mkdir(parents=True, exist_ok=True)
            self._save_video(video, metrics)
            row['video'] = str(video.relative_to(OUTPUT))
            Image.fromarray(self._goal_image).save(video.with_suffix('.goal.png'))
            # Frames needed for report/contact-sheet review; videos contain every frame.
            for index in sorted(set([0, steps//4, steps//2, 3*steps//4, steps])):
                Image.fromarray(self._frames[index]).save(video.with_name(episode+'.rgb_%03d.jpg'%index), quality=90)
            arrays['metadata_json'] = np.asarray(json.dumps(row, allow_nan=False))
        temporary = trace.with_suffix('.partial.npz')
        np.savez_compressed(temporary, **arrays)
        temporary.replace(trace)
        folder = OUTPUT/'diagnostics'
        folder.mkdir(exist_ok=True)
        with (folder/('worker_%d.jsonl'%os.getpid())).open('a') as f:
            f.write(json.dumps(row, allow_nan=False)+'\n')
        self._frames = []

    def _save_video(self, path, metrics):
        temporary = path.with_suffix('.partial.mp4')
        writer = imageio.get_writer(str(temporary), fps=10, codec='libx264', quality=6,
                                    macro_block_size=16, ffmpeg_log_level='error',
                                    ffmpeg_params=['-threads', '1'])
        goal = Image.fromarray(self._goal_image).resize((128, 128))
        try:
            for step, raw in enumerate(self._frames):
                canvas = Image.new('RGB', (256, 160), 'white')
                canvas.paste(goal, (0, 0))
                canvas.paste(Image.fromarray(raw).resize((128, 128)), (128, 0))
                draw = ImageDraw.Draw(canvas)
                draw.text((3, 130), 'GOAL | OBS step=%d d=%.2fm'%(step, metrics[step, 0]), fill='black')
                draw.text((3, 144), 'collision=%d stop=%d'%(metrics[step, 6], metrics[step, 9]), fill='black')
                writer.append_data(np.asarray(canvas))
        finally:
            writer.close()
        assert temporary.stat().st_size > 0
        temporary.replace(path)


@habitat.registry.register_env(name='FailureDiagnosticGym')
class FailureDiagnosticGym(gym.Wrapper):
    def __init__(self, config, dataset=None):
        super().__init__(HabGymWrapper(DiagnosticNavEnv(config=config, dataset=dataset)))
