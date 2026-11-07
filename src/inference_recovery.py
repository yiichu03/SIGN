"""RGB/action-only inference supervisor. No simulator or training imports."""
from collections import deque
from dataclasses import dataclass, field
import hashlib
import json
from pathlib import Path
import time
import numpy as np


def physical(action):
    a = np.asarray(action, dtype=np.float32)
    if a.shape != (2,) or not np.isfinite(a).all():
        raise ValueError('Expected two finite normalized actions')
    a = np.clip(a, -1, 1)
    return float((a[0] + 1) * 0.125), float(a[1] * 15)


def is_stop(action):
    v, w = physical(action)
    return v < 0.025 and abs(w) < 1.5


def thumbnail(rgb):
    a = np.asarray(rgb)
    if a.ndim != 3 or a.shape[2] != 3 or not np.isfinite(a).all():
        raise ValueError('Expected finite HWC RGB')
    if a.min() < 0 or a.max() > 255 or min(a.shape[:2]) < 32:
        raise ValueError('Expected RGB values in [0,255] and size >=32')
    return a[np.linspace(0, a.shape[0]-1, 32).astype(int)][:, np.linspace(0, a.shape[1]-1, 32).astype(int)].astype(np.float32)/255


def detect(frames, commands, cfg):
    if len(frames) != cfg.window+1 or len(commands) != cfg.window:
        return None
    movement = [v >= 0.15 and abs(w) <= 7.5 for v, w in map(physical, commands)]
    median = float(np.median([np.abs(b-a).mean() for a, b in zip(frames, list(frames)[1:])]))
    endpoint = float(np.abs(frames[-1]-frames[0]).mean())
    fraction = sum(movement)/len(movement)
    if fraction >= cfg.min_forward_fraction and median <= cfg.median_change_threshold and endpoint <= cfg.endpoint_change_threshold:
        return dict(forward_fraction=fraction, median_rgb_change=median, endpoint_rgb_change=endpoint)
    return None


def recovery_actions(label, turn_steps, forward_steps):
    if label not in ('A', 'B') or turn_steps < 1 or forward_steps < 1:
        raise ValueError('Invalid bounded recovery')
    return [np.array([-1., 1. if label == 'A' else -1.], dtype=np.float32) for _ in range(turn_steps)] + [np.array([0.6, 0.], dtype=np.float32) for _ in range(forward_steps)]


def choose(probabilities, minimum=0.5, margin=0.1):
    p = np.asarray(probabilities, dtype=np.float64)
    if p.shape != (3,) or not np.isfinite(p).all() or (p < 0).any() or not np.isclose(p.sum(), 1., atol=1e-6):
        raise ValueError('Invalid A/B/C probabilities')
    order = np.argsort(p)
    winner = int(order[-1])
    if p[winner] < minimum or p[winner]-p[order[-2]] < margin:
        return 'C'
    return 'ABC'[winner]


@dataclass
class State:
    key: tuple
    window: int
    step: int = 0
    attempts: int = 0
    overrides: int = 0
    rejected: int = 0
    cooldown_until: int = 0
    last_action: object = None
    actions: deque = field(default_factory=deque)
    active_event: object = None
    frames: deque = field(default_factory=deque)
    images: deque = field(default_factory=deque)
    commands: deque = field(default_factory=deque)
    action_digest: object = field(default_factory=hashlib.sha256)
    finished: bool = False
    earlier_choices: list = field(default_factory=list)

    def observe(self, rgb):
        if self.last_action is not None:
            self.commands.append(self.last_action.copy())
        self.frames.append(thumbnail(rgb))
        self.images.append(np.asarray(rgb, dtype=np.uint8).copy())
        while len(self.frames) > self.window+1:
            self.frames.popleft(); self.images.popleft()
        while len(self.commands) > self.window:
            self.commands.popleft()


def collage(state, goal, destination, evidence):
    from PIL import Image, ImageDraw
    canvas = Image.new('RGB', (512, 576), 'white')
    draw = ImageDraw.Draw(canvas)
    frames = [goal, state.images[0], state.images[len(state.images)//2], state.images[-1]]
    labels = ['TARGET PHOTOGRAPH', f'CAMERA step {state.step-state.window}',
              f'CAMERA step {state.step-state.window//2}', f'CAMERA NOW step {state.step}']
    for i, (frame, label) in enumerate(zip(frames, labels)):
        x, y = (i % 2)*256, 40+(i//2)*268
        canvas.paste(Image.fromarray(np.asarray(frame, dtype=np.uint8)).resize((256, 240)), (x, y+18))
        draw.text((x+4, y+2), label, fill='black')
    draw.text((4, 2), f'Last {state.window} actions: forward-command fraction {evidence["forward_fraction"]:.2f}', fill='black')
    draw.text((4, 17), 'Commands are intentions; actual displacement is unknown.', fill='black')
    draw.text((4, 30), 'Earlier recovery decisions: '+','.join(state.earlier_choices), fill='black')
    canvas.save(destination)


class RecoveryHarness:
    def __init__(self, cfg, num_envs, output, client_factory=None,
                 action_names=('linear_velocity', 'angular_velocity')):
        self.cfg = cfg
        if len(action_names) != 2 or set(action_names) != {'linear_velocity', 'angular_velocity'}:
            raise ValueError('Unexpected flattened action names')
        self.action_indices = [action_names.index(n) for n in ('linear_velocity', 'angular_velocity')]
        if cfg.mode not in ('rule', 'qwen') or cfg.window < 2 or cfg.max_interventions < 0 or cfg.cooldown < 0:
            raise ValueError('Invalid recovery settings')
        values = [cfg.min_forward_fraction, cfg.median_change_threshold, cfg.endpoint_change_threshold, cfg.min_probability, cfg.min_margin]
        if not np.isfinite(values).all() or any(not 0 <= v <= 1 for v in values):
            raise ValueError('Invalid detector/confidence thresholds')
        if cfg.turn_steps < 1 or cfg.forward_steps < 1:
            raise ValueError('Invalid recovery duration')
        self.states = [None for _ in range(num_envs)]
        self.output = Path(output)
        self.output.mkdir(parents=True, exist_ok=False)
        (self.output/'inputs').mkdir()
        (self.output/'action_order.json').write_text(json.dumps(dict(flattened=list(action_names),
            canonical=['linear_velocity','angular_velocity'], canonical_indices=self.action_indices), indent=2)+'\n')
        self.client, self.client_factory = None, client_factory
        self.request = 0
        self.events = 0
        self.worker_seconds = 0.
        self.render_seconds = 0.
        self.total_seconds = 0.
        self.episode_serial = 0

    def _append(self, name, row):
        with (self.output/name).open('a') as f:
            f.write(json.dumps(row, allow_nan=False)+'\n')

    def step(self, rgb, goal, proposed, masks, keys):
        started = time.perf_counter()
        flat = np.asarray(proposed)
        if flat.shape != (len(self.states), 2) or len(keys) != len(self.states) or len(rgb) != len(self.states) or len(goal) != len(self.states):
            raise ValueError('Environment rows do not match')
        before = flat[:, self.action_indices]
        original_masks = np.asarray(masks).copy()
        if original_masks.shape != (len(self.states),) or not np.isin(original_masks, [0, 1]).all():
            raise ValueError('Expected one real binary mask per environment')
        result = before.copy()
        pending = []
        for i, (frame, action, key) in enumerate(zip(rgb, before, keys)):
            physical(action)
            key = tuple(key)
            state = self.states[i]
            if not bool(np.asarray(masks)[i]) or state is None:
                state = State(key, self.cfg.window)
                self.states[i] = state
                self.episode_serial += 1
            elif state.key != key or state.finished:
                raise RuntimeError('Episode changed without a real reset')
            state.observe(frame)
            if state.active_event is not None and state.step >= state.active_event['end_step']:
                event = state.active_event
                self._append('outcomes.jsonl', dict(id=event['id'], episode=list(key), step=state.step,
                    rgb_change=float(np.abs(state.frames[-1]-event['before']).mean()),
                    note='Visual change only; not task success or measured displacement'))
                state.active_event = None
            if is_stop(action):
                state.actions.clear()
            elif state.actions:
                result[i] = state.actions.popleft()
                state.overrides += 1
            elif state.attempts < self.cfg.max_interventions and state.step >= state.cooldown_until:
                evidence = detect(state.frames, state.commands, self.cfg)
                if evidence is not None:
                    event_id = f'event_{self.events:07d}'
                    self.events += 1
                    row = dict(id=event_id, env_index=i, episode=list(key), step=state.step, evidence=evidence)
                    image = self.output/'inputs'/(event_id+'.png')
                    render_started = time.perf_counter()
                    collage(state, goal[i], image, evidence)
                    self.render_seconds += time.perf_counter()-render_started
                    row.update(image=str(image), image_sha256=hashlib.sha256(image.read_bytes()).hexdigest())
                    pending.append((i, row))
        choices = []
        if pending and self.cfg.mode == 'qwen':
            if self.client is None:
                if self.client_factory is None:
                    from src.qwen_client import QwenClient
                    self.client_factory = QwenClient
                self.client = self.client_factory(self.cfg, self.output/'worker')
            response = self.client.score(self.request, [r for _, r in pending])
            self.request += 1
            if [r['id'] for r in response['results']] != [r['id'] for _, r in pending]:
                raise RuntimeError('Recovery worker image ID/order mismatch')
            self.worker_seconds += response['seconds']
            for item in response['results']:
                label = choose(item['probabilities'], self.cfg.min_probability, self.cfg.min_margin)
                choices.append((label, item))
        else:
            choices = [('A' if self.states[i].attempts % 2 == 0 else 'B', {}) for i, _ in pending]
        for (i, row), (label, detail) in zip(pending, choices):
            state = self.states[i]
            state.attempts += 1
            state.earlier_choices.append(label)
            state.cooldown_until = state.step+self.cfg.turn_steps+self.cfg.forward_steps+self.cfg.cooldown
            if label != 'C':
                state.actions = deque(recovery_actions(label, self.cfg.turn_steps, self.cfg.forward_steps))
                row['planned_actions'] = [a.tolist() for a in state.actions]
                state.active_event = dict(id=row['id'], before=state.frames[-1].copy(),
                    end_step=state.step+self.cfg.turn_steps+self.cfg.forward_steps)
                result[i] = state.actions.popleft()
                state.overrides += 1
            else:
                state.rejected += 1
            row.update(mode=self.cfg.mode, choice=label, model=detail, attempt=state.attempts)
            self._append('events.jsonl', row)
        for i, action in enumerate(result):
            state = self.states[i]
            actual = np.clip(action, -1, 1).astype(np.float32)
            state.last_action = actual
            state.action_digest.update(actual.tobytes())
            state.step += 1
        assert np.array_equal(np.asarray(masks), original_masks)
        self.total_seconds += time.perf_counter()-started
        output = flat.copy()
        output[:, self.action_indices] = result
        return output

    def finish(self, index, key):
        state = self.states[index]
        if state is None or state.key != tuple(key) or state.finished:
            raise RuntimeError('Terminal episode ID mismatch')
        row = dict(episode=list(key), steps=state.step, attempts=state.attempts,
                   overrides=state.overrides, rejected=state.rejected, actions_sha256=state.action_digest.hexdigest())
        self._append('episodes.jsonl', row)
        state.finished = True
        return row

    def pause(self, indices):
        for i in sorted(indices, reverse=True):
            del self.states[i]

    def close(self):
        if self.client is not None:
            self.client.close()
        (self.output/'summary.json').write_text(json.dumps(dict(events=self.events, worker_started=self.client is not None,
            worker_seconds=self.worker_seconds, render_seconds=self.render_seconds,
            total_controller_seconds=self.total_seconds, mode=self.cfg.mode), indent=2)+'\n')
