"""Episode collection and strict once-per-rollout reward addressing; no VLM imports."""
import math
import time
import numpy as np
from src.qwen_geometry import EpisodeCoverage, GeometryError

PAYLOAD_KEY = '__qwen_payload__'


class SegmentCollector:
    def __init__(self, interval=128, rollout_steps=256):
        self.interval, self.H = int(interval), int(rollout_steps)
        if self.interval <= 0 or self.H <= 0:
            raise ValueError('Positive Qwen settlement and rollout lengths required')
        self.env_id = None
        self.reset_index = -1
        self.total_actions = 0
        self.global_start = 0

    def reset(self, scene_id, episode_id, geometry, reason=None):
        self.reset_index += 1
        self.scene_id, self.episode_id = str(scene_id), str(episode_id)
        self.geometry, self.reason = geometry, reason
        self.episode_steps = self.segment_start = 0
        self.global_start = self.total_actions
        self.geometry_seconds = 0.

    def step(self, rc, heading, position, done):
        start = time.perf_counter()
        self.total_actions += 1
        self.episode_steps += 1
        if self.geometry is not None:
            self.geometry.observe(rc, heading, position)
        self.geometry_seconds += time.perf_counter()-start
        token = (self.env_id, self.reset_index, self.episode_id, self.episode_steps, self.total_actions)
        snapshots = []
        if done or self.total_actions % self.interval == 0 or self.total_actions % self.H == 0:
            snapshot = self.geometry.snapshot() if self.geometry is not None else dict(
                valid_geometry=False, geometry_reason=self.reason, start=self.segment_start,
                end=self.episode_steps, action_count=self.episode_steps-self.segment_start)
            snapshot.update(env_id=self.env_id, reset_index=self.reset_index, episode_id=self.episode_id,
                scene_id=self.scene_id, rollout_id=(self.total_actions-1)//self.H,
                global_start=self.global_start, global_end=self.total_actions, terminal=bool(done),
                geometry_seconds=self.geometry_seconds)
            snapshots.append(snapshot)
            self.global_start = self.total_actions
            self.segment_start = self.episode_steps
            self.geometry_seconds = 0.
            if self.geometry is not None:
                self.geometry.cut()
        # Tuple prevents HabGymWrapper.flatten_dict from descending into snapshots.
        return token, tuple(snapshots)


class SegmentLedger:
    def __init__(self, envs, H=256, interval=128):
        self.N, self.H, self.interval = envs, H, interval
        self.rollout_id = 0
        self.reset_indices = [0]*envs
        self.episode_steps = [0]*envs
        self.episode_ids = [None]*envs
        self.global_starts = [0]*envs
        self.episode_starts = [0]*envs
        self.pending = []
        self.rows = 0
        self.applied = False

    def collect(self, row, dones, infos):
        if row != self.rows or self.applied or len(infos) != self.N:
            raise RuntimeError('Qwen rollout collection order mismatch')
        for env, (done, info) in enumerate(zip(dones, infos)):
            try:
                token, snapshots = info.pop(PAYLOAD_KEY)
            except (KeyError, TypeError, ValueError) as exc:
                raise RuntimeError('Missing or malformed Qwen payload') from exc
            expected_end = self.rollout_id*self.H+row+1
            env_id, reset, episode, episode_step, total = token
            if (env_id != env or reset != self.reset_indices[env]
                    or episode_step != self.episode_steps[env]+1 or total != expected_end):
                raise RuntimeError('Qwen env/reset/step identity mismatch')
            if self.episode_ids[env] not in (None, episode):
                raise RuntimeError('Episode ID changed without true reset')
            self.episode_ids[env] = episode
            boundary = bool(done) or total % self.interval == 0 or row+1 == self.H
            if len(snapshots) != int(boundary):
                raise RuntimeError('Qwen missing or duplicate settlement')
            for snapshot in snapshots:
                expected = dict(env_id=env, reset_index=reset, episode_id=episode,
                    rollout_id=self.rollout_id, global_start=self.global_starts[env],
                    global_end=total, start=self.episode_starts[env], end=episode_step,
                    action_count=total-self.global_starts[env], terminal=bool(done))
                if any(snapshot.get(k) != v for k,v in expected.items()):
                    raise RuntimeError('Qwen segment identity/bounds mismatch')
                snapshot['end_row'] = row
                snapshot['segment_id'] = f'r{self.rollout_id:07d}_e{env}_reset{reset}_s{snapshot["start"]}_t{episode_step}'
                self.pending.append(snapshot)
                self.global_starts[env] = total
                self.episode_starts[env] = episode_step
            self.episode_steps[env] = episode_step
            if done:
                self.reset_indices[env] += 1
                self.episode_steps[env] = self.episode_starts[env] = 0
                self.episode_ids[env] = None
        self.rows += 1

    def validate(self, masks):
        if self.rows != self.H or self.applied:
            raise RuntimeError('Qwen rollout incomplete or already scored')
        expected_end = (self.rollout_id+1)*self.H
        if any(x != expected_end for x in self.global_starts):
            raise RuntimeError('Unsettled Qwen tail')
        ids = [s['segment_id'] for s in self.pending]
        if len(ids) != len(set(ids)):
            raise RuntimeError('Duplicate Qwen segment ID')
        for s in self.pending:
            if bool(masks[s['end_row']+1, s['env_id'], 0]) == s['terminal']:
                raise RuntimeError('Qwen terminal payload disagrees with real mask')

    def add(self, rewards, masks, responses, beta):
        self.validate(masks)
        valid = [s for s in self.pending if s['valid_geometry']]
        if len(responses) != len(valid):
            raise RuntimeError('Qwen response count mismatch')
        if [r['id'] for r in responses] != [s['segment_id'] for s in valid]:
            raise RuntimeError('Qwen response ID mismatch')
        bonuses = []
        for s, r in zip(valid, responses):
            q = r.get('q')
            if not r.get('valid') or type(q) not in (int,float) or not math.isfinite(q) or not 0 <= q <= 1:
                raise RuntimeError('Invalid Qwen probability')
            bonuses.append(beta*(s['action_count']/self.H)*q)
        # Validate all rows before mutating any reward.
        for s, bonus in zip(valid, bonuses):
            rewards[s['end_row'], s['env_id'], 0] += bonus
        self.applied = True
        return bonuses

    def advance(self):
        if not self.applied:
            raise RuntimeError('Qwen rollout advanced before scoring')
        self.rollout_id += 1
        self.pending, self.rows, self.applied = [], 0, False

    def add_geometry(self, rewards, masks, alpha):
        """Area has physical units; never route it through a probability response."""
        self.validate(masks)
        if not math.isfinite(alpha) or alpha < 0:
            raise RuntimeError('Invalid geometry alpha')
        valid = [s for s in self.pending if s['valid_geometry']]
        gains = [s['metadata']['new_area_m2'] for s in valid]
        if any(type(g) not in (float, int) or not math.isfinite(g) or g < 0 for g in gains):
            raise RuntimeError('Invalid geometric area')
        bonuses = [alpha * gain / self.H for gain in gains]
        for s, bonus in zip(valid, bonuses):
            rewards[s['end_row'], s['env_id'], 0] += bonus
        self.applied = True
        return bonuses
