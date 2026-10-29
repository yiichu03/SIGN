from typing import Optional

import gym
import habitat
from habitat import Config, Dataset
from habitat_baselines.common.baseline_registry import baseline_registry
from habitat.utils.gym_adapter import HabGymWrapper
from src.custom_habitat_env import RLDroneEnv

class NavRLEnvX(RLDroneEnv):
    def __init__(self, config: Config, dataset: Optional[Dataset] = None):
        self._config = config
        # self._core_env_config = config.TASK_CONFIG
        if len(self._config.task.reward_measure) > 0:
            self._reward_measure_names = [self._config.task.reward_measure]
            self._reward_scales = [1.0]
        else:
            self._reward_measure_names = self._config.task.reward_measure
            self._reward_scales = self._config.task.reward_scales

        self._success_measure_name = self._config.task.success_measure
        habitat.logger.info('NavRLEnvX: '
                            f'Reward Measures={self._reward_measure_names}, '
                            f'Reward Scales={self._reward_scales}, '
                            f'Success Measure={self._success_measure_name}')
        self._previous_measure = None
        self._previous_action = None
        super().__init__(self._config, dataset)

    def reset(self):
        self._previous_action = None
        observations = super().reset()
        self._previous_measure = self._get_reward_measure()
        return observations

    def _get_reward_measure(self):
        current_measure = 0.0
        for reward_measure_name, reward_scale in zip(
                self._reward_measure_names, self._reward_scales
        ):
            if "." in reward_measure_name:
                reward_measure_name = reward_measure_name.split('.')
                measure = self._env.get_metrics()[
                    reward_measure_name[0]
                ][reward_measure_name[1]]
            else:
                measure = self._env.get_metrics()[reward_measure_name]
            current_measure += measure * reward_scale
        return current_measure

    def step(self, *args, **kwargs):
        self._previous_action = kwargs["action"]
        return super().step(*args, **kwargs)

    def get_reward_range(self):
        return (
            self._config.task.slack_reward - 1.0,
            self._config.task.success_reward + 1.0,
        )

    def get_reward(self, observations):
        reward = self._config.task.slack_reward

        current_measure = self._get_reward_measure()

        reward += self._previous_measure - current_measure
        self._previous_measure = current_measure

        if self._episode_success():
            reward += self._episode_success() * self._config.task.success_reward

        return reward

    def _episode_success(self):
        return self._env.get_metrics()[self._success_measure_name]

    def get_done(self, observations):
        done = False
        if self._env.episode_over or self._episode_success():
            done = True
        return done

    def get_info(self, observations):
        dic = self.habitat_env.get_metrics()
        return dic


class QwenNavRLEnvX(NavRLEnvX):
    """Snapshot the completed action before VectorEnv's automatic reset."""
    def __init__(self, config, dataset=None):
        from src.qwen_rollout import SegmentCollector
        self.qwen_cfg = config.qwen_reward
        self.qwen_collector = SegmentCollector(self.qwen_cfg.settlement_interval, self.qwen_cfg.rollout_steps)
        super().__init__(config, dataset)

    def _qwen_pose(self):
        import numpy as np
        from habitat.utils.geometry_utils import quaternion_rotate_vector
        from habitat.utils.visualizations import maps
        state = self.habitat_env.sim.get_agent_state()
        geometry = self.qwen_collector.geometry
        rc = maps.to_grid(state.position[2], state.position[0], geometry.grid.shape,
                          sim=self.habitat_env.sim) if geometry is not None else (0, 0)
        forward = quaternion_rotate_vector(state.rotation, np.array([0., 0., -1.]))
        return rc, float(np.arctan2(forward[0], forward[2])), state.position.copy()

    def reset(self):
        from src.qwen_geometry import EpisodeCoverage, GeometryError
        from habitat.utils.visualizations import maps
        observations = super().reset()
        cfg = self.qwen_cfg
        try:
            grid = maps.get_topdown_map_from_sim(self.habitat_env.sim, draw_border=False,
                                               meters_per_pixel=cfg.meters_per_pixel)
            geometry = EpisodeCoverage(grid, cfg.meters_per_pixel, cfg.visibility_dist,
                                       cfg.fov, cfg.max_height_range)
            reason = None
        except (GeometryError, RuntimeError, ValueError) as exc:
            geometry, reason = None, 'map_unavailable_' + type(exc).__name__ + ':' + str(exc)
        episode = self.habitat_env.current_episode
        self.qwen_collector.reset(episode.scene_id, episode.episode_id, geometry, reason)
        if geometry is not None:
            geometry.observe(*self._qwen_pose())
        return observations

    def step(self, *args, **kwargs):
        from src.qwen_rollout import PAYLOAD_KEY
        observations, reward, done, info = super().step(*args, **kwargs)
        info = dict(info)
        info[PAYLOAD_KEY] = self.qwen_collector.step(*self._qwen_pose(), done)
        return observations, reward, done, info


@habitat.registry.register_env(name="GymHabitatEnvX")
class GymHabitatEnvX(gym.Wrapper):
    """
    A registered environment that wraps a RLTaskEnv with the HabGymWrapper
    to use the default gym API.
    """

    def __init__(self, config: Config, dataset: Optional[Dataset] = None):
        cfg = getattr(config, 'qwen_reward', None)
        cls = QwenNavRLEnvX if cfg is not None and cfg.collect else NavRLEnvX
        base_env = cls(config=config, dataset=dataset)
        env = HabGymWrapper(base_env)
        super().__init__(env)

    def set_qwen_env_index(self, index):
        self.env._env.qwen_collector.env_id = index
