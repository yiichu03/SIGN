"""RGB/action-only inference supervisor. No simulator or training imports."""
from collections import deque
from dataclasses import dataclass, field
import hashlib
import json
from pathlib import Path
import time
import numpy as np
from src.recovery_agent import AgentSupport


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


def yaw_aligned_change(previous, current, degrees, return_overlap=False):
    """RGB residual after the executed yaw command; no measured pose or depth.

    Positive action yaw turns the Habitat camera left. Project current camera
    rays into the previous 90-degree pinhole image, ignoring newly exposed edges.
    Blur reduces thumbnail sampling noise, not temporal scene changes.
    """
    def smooth(a):
        p = np.pad(a, ((1, 1), (1, 1), (0, 0)), mode='edge')
        return sum(p[y:y+32, x:x+32] for y in range(3) for x in range(3))/9
    a, b = smooth(previous), smooth(current)
    yy, xx = np.mgrid[6:26, 6:26]
    x, y = (xx-15.5)/16., (yy-15.5)/16.
    angle = np.deg2rad(degrees)
    z = np.sin(angle)*x+np.cos(angle)
    u = 16*(np.cos(angle)*x-np.sin(angle))/np.maximum(z, 1e-6)+15.5
    v = 16*y/np.maximum(z, 1e-6)+15.5
    valid = (z > 0) & (u >= 0) & (u < 31) & (v >= 0) & (v < 31)
    if valid.mean() < .7:
        return (1., float(valid.mean())) if return_overlap else 1.
    u, v = u[valid], v[valid]
    ui, vi = u.astype(int), v.astype(int)
    du, dv = (u-ui)[:, None], (v-vi)[:, None]
    warped = ((1-du)*(1-dv)*a[vi, ui]+du*(1-dv)*a[vi, ui+1]
        +(1-du)*dv*a[vi+1, ui]+du*dv*a[vi+1, ui+1])
    error = float(np.abs(warped-b[yy[valid], xx[valid]]).mean())
    return (error, float(valid.mean())) if return_overlap else error


def detect(frames, commands, cfg):
    if len(frames) != cfg.window+1 or len(commands) != cfg.window:
        return None
    motions = list(map(physical, commands))
    aligned = bool(getattr(cfg, 'yaw_compensated', False))
    movement = [v >= 0.15 and (aligned or abs(w) <= 7.5) for v, w in motions]
    if aligned:
        median = float(np.median([yaw_aligned_change(a, b, w)
            for a, b, (_, w) in zip(frames, list(frames)[1:], motions)]))
        endpoint, overlap = yaw_aligned_change(frames[0], frames[-1], sum(w for _, w in motions), True)
    else:
        median = float(np.median([np.abs(b-a).mean() for a, b in zip(frames, list(frames)[1:])]))
        endpoint = float(np.abs(frames[-1]-frames[0]).mean())
    fraction = sum(movement)/len(movement)
    endpoint_used = not (aligned and getattr(cfg,'yaw_partial_windows',False) and overlap < .7)
    if fraction >= cfg.min_forward_fraction and median <= cfg.median_change_threshold and (not endpoint_used or endpoint <= cfg.endpoint_change_threshold):
        evidence = dict(forward_fraction=fraction, median_rgb_change=median, endpoint_rgb_change=endpoint,
            yaw_compensated=aligned)
        if aligned:
            evidence.update(endpoint_used=endpoint_used,endpoint_overlap=overlap)
        return evidence
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
    survey: object = None
    action_kind: str = 'recovery'
    survey_overrides: int = 0
    recovery_overrides: int = 0
    completed_surveys: int = 0
    selections: dict = field(default_factory=lambda: dict(A=0, B=0, C=0))
    vlm_selections: int = 0
    fallback_selections: int = 0
    vlm_rule_disagreements: int = 0

    memory: object = None
    probe: object = None
    last_kind: str = "sign"
    issued_kind: str = "sign"
    memory_hits: int = 0
    memory_prompt_entries: int = 0
    memory_changed: int = 0
    feedback_calls: int = 0
    feedback_returns: int = 0

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


def survey_actions(k):
    if type(k) is not int or k < 1:
        raise ValueError('Invalid survey turn count')
    return [np.array([-1., sign], dtype=np.float32) for sign in ([1.]*k+[-1.]*(2*k)+[1.]*k)]


def active_collage(survey, goal, destination):
    from PIL import Image, ImageDraw, ImageFont
    canvas = Image.new('RGB', (512, 680), 'white')
    draw = ImageDraw.Draw(canvas)
    try:
        font_path = Path(__file__).resolve().parents[2]/'envs/sign-baseline/lib/python3.8/site-packages/matplotlib/mpl-data/fonts/ttf/DejaVuSans.ttf'
        font = ImageFont.truetype(str(font_path), 18)
        small = ImageFont.truetype(str(font_path), 14)
    except OSError:
        font = small = ImageFont.load_default()
    draw.text((6, 3), 'LOCAL VIEWS AFTER COMMANDED TURNS', fill='black', font=font)
    draw.text((6, 29), 'RGB only; no measured pose or collision input.', fill='black', font=small)
    draw.text((6, 49), 'Compare visible space; target photograph is context.', fill='black', font=small)
    views = survey['views']
    images = [goal, views['left'], views['forward'], views['right']]
    angle = survey['commanded_yaw']
    names = ['GOAL', f'LEFT VIEW (+{angle} cmd)', 'FORWARD (0 cmd)', f'RIGHT VIEW (-{angle} cmd)']
    times = ['context', str(survey['view_steps']['left']), str(survey['view_steps']['forward']), str(survey['view_steps']['right'])]
    for i, (frame, label, step) in enumerate(zip(images, names, times)):
        x, y = (i%2)*256, 72+(i//2)*304
        draw.text((x+4,y), label, fill='black', font=font)
        draw.text((x+4,y+22), 'RGB step '+step, fill='black', font=small)
        canvas.paste(Image.fromarray(np.asarray(frame, dtype=np.uint8)).resize((256,256)),(x,y+44))
    canvas.save(destination)
    files = {}
    for name, frame in zip(['goal','left','forward','right'], images):
        path = Path(destination).with_name(Path(destination).stem+'.'+name+'.png')
        Image.fromarray(np.asarray(frame, dtype=np.uint8)).save(path)
        files[name] = dict(path=str(path), sha256=hashlib.sha256(path.read_bytes()).hexdigest())
    return files


class RecoveryHarness(AgentSupport):
    def __init__(self, cfg, num_envs, output, client_factory=None,
                 action_names=('linear_velocity', 'angular_velocity')):
        self.cfg = cfg
        self.arm = getattr(cfg,'agent_variant','legacy')
        if self.arm not in ('legacy','A','B','C','D'):raise ValueError('Unknown agent variant')
        self.agent = self.arm != 'legacy' and cfg.mode=='qwen'
        self.technical_errors=0
        self.option_index=0
        if len(action_names) != 2 or set(action_names) != {'linear_velocity', 'angular_velocity'}:
            raise ValueError('Unexpected flattened action names')
        self.action_indices = [action_names.index(n) for n in ('linear_velocity', 'angular_velocity')]
        self.active_survey = bool(getattr(cfg, 'active_survey', False))
        self.candidate_affordance = bool(getattr(cfg, 'candidate_affordance', False))
        self.candidate_protocol = getattr(cfg, 'candidate_protocol', 'abc')
        if self.candidate_protocol not in ('abc','semantic','semantic_balanced','directional','agent'):
            raise ValueError('Unknown candidate protocol')
        self.candidate_gap = float(getattr(cfg, 'candidate_support_gap', 0.05))
        if self.candidate_affordance and (not self.active_survey or not np.isfinite(self.candidate_gap) or not 0 < self.candidate_gap <= 1):
            raise ValueError('Candidate affordances require active views and a positive support gap')
        if self.agent and (not self.active_survey or self.candidate_protocol!='agent' or (cfg.survey_turn_steps,cfg.turn_steps) not in ((6,6),(4,4)) or cfg.forward_steps not in (4,8)):
            raise ValueError('Agents require aligned bounded scan/recovery angles and durations')
        if self.agent and self.arm=='B' and (cfg.turn_steps!=6 or cfg.survey_turn_steps!=6 or cfg.forward_steps!=8):
            raise ValueError('Original closed-loop B requires its frozen 6-turn / 8-forward protocol')
        self.survey_k = getattr(cfg, 'survey_turn_steps', 3)
        if self.active_survey and (type(self.survey_k) is not int or self.survey_k < 1):
            raise ValueError('Invalid survey duration')
        if cfg.mode == 'scan' and not self.active_survey:
            raise ValueError('Scan-only mode requires active views')
        if cfg.mode not in ('rule', 'qwen', 'scan') or cfg.window < 2 or cfg.max_interventions < 0 or cfg.cooldown < 0:
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
        self.max_override_steps = cfg.max_interventions * (cfg.turn_steps+cfg.forward_steps+(4*self.survey_k if self.active_survey else 0))

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
                if state is not None and state.memory is not None:state.memory.clear('real_reset')
                state = State(key, self.cfg.window)
                self._agent_reset(state)
                self.states[i] = state
                self.episode_serial += 1
            elif state.key != key or state.finished:
                raise RuntimeError('Episode changed without a real reset')
            if self.agent:self._agent_observe(state,frame)
            state.observe(frame)
            if state.active_event is not None and state.step >= state.active_event['end_step']:
                event = state.active_event
                self._append('outcomes.jsonl', dict(id=event['id'], episode=list(key), step=state.step,
                    rgb_change=float(np.abs(state.frames[-1]-event['before']).mean()),
                    note='Visual change only; not task success or measured displacement'))
                state.active_event = None
            if is_stop(action):
                state.actions.clear()
                if self.agent and state.active_event is not None:
                    self._append('outcomes.jsonl',dict(id=state.active_event['id'],episode=list(key),step=state.step,
                        phase='policy_stop',after_rgb_sha256=hashlib.sha256(np.ascontiguousarray(frame).tobytes()).hexdigest()))
                    state.active_event=None
                if self.agent and state.probe is not None:
                    self._append("feedback.jsonl",dict(id=state.probe["id"],episode=list(key),step=state.step,phase="cancelled_by_policy_stop"))
                    state.probe=None
                if state.survey is not None:
                    self._append('surveys.jsonl', dict(id=state.survey['row']['id'], episode=list(key),
                        step=state.step, phase='cancelled_by_policy_stop'))
                state.survey = None
            elif self.agent and state.probe is not None and state.probe.get("ready"):
                pending.append((i,dict(id=state.probe["id"]+":feedback",task="feedback")))
            elif state.survey is not None:
                survey = state.survey
                elapsed = state.step-survey['start_step']
                if elapsed == self.survey_k:
                    survey['views']['left'] = np.asarray(frame, dtype=np.uint8).copy()
                    survey['view_steps']['left'] = state.step
                if elapsed == 3*self.survey_k:
                    survey['views']['right'] = np.asarray(frame, dtype=np.uint8).copy()
                    survey['view_steps']['right'] = state.step
                if elapsed == 4*self.survey_k:
                    assert not state.actions and set(survey['views']) == {'left', 'right'}
                    survey['views']['forward'] = np.asarray(frame, dtype=np.uint8).copy()
                    survey['view_steps']['forward'] = state.step
                    row = survey['row']
                    image = self.output/'inputs'/(row['id']+'.png')
                    render_started = time.perf_counter()
                    view_files = active_collage(survey, goal[i], image)
                    if self.candidate_affordance and not self.agent:
                        from src.recovery_affordance import candidate_image, raw_candidate_image
                        row['candidates'] = []
                        for side in ['left', 'right']:
                            destination=image.with_name(image.stem+'.candidate_'+side+'.png')
                            candidate = (raw_candidate_image(survey['views'][side],destination)
                                if getattr(self.cfg,'candidate_raw_view',False) else
                                candidate_image(survey['views'][side],goal[i],destination))
                            candidate.update(id=row['id']+':'+side, side=side)
                            row['candidates'].append(candidate)
                    self.render_seconds += time.perf_counter()-render_started
                    row.update(image=str(image), image_sha256=hashlib.sha256(image.read_bytes()).hexdigest(),
                        active_survey=True, decision_step=state.step, view_steps=survey['view_steps'],
                        survey_command_steps=4*self.survey_k, view_files=view_files,
                        commanded_view_yaw=survey['commanded_yaw'])
                    pending.append((i, row))
                    state.completed_surveys += 1
                    state.survey = None
                else:
                    if not state.actions:
                        raise RuntimeError('Survey action/frame boundary mismatch')
                    result[i] = state.actions.popleft()
                    state.issued_kind="scan"
                    state.overrides += 1
                    state.survey_overrides += 1
            elif state.actions:
                state.issued_kind="probe" if state.probe is not None else "recovery"
                result[i] = state.actions.popleft()
                state.overrides += 1
                state.recovery_overrides += 1
            elif state.attempts < self.cfg.max_interventions and state.step >= state.cooldown_until:
                evidence = detect(state.frames, state.commands, self.cfg)
                if evidence is not None:
                    event_id = f'event_{self.events:07d}'
                    self.events += 1
                    row = dict(id=event_id, env_index=i, episode=list(key), step=state.step,
                        evidence=evidence, attempt=state.attempts+1)
                    if self.active_survey:
                        state.attempts += 1
                        state.survey = dict(row=row, start_step=state.step, views={}, view_steps={}, commanded_yaw=15*self.survey_k)
                        state.actions = deque(survey_actions(self.survey_k))
                        state.cooldown_until = state.step+4*self.survey_k+self.cfg.turn_steps+self.cfg.forward_steps+self.cfg.cooldown
                        result[i] = state.actions.popleft()
                        state.issued_kind="scan"
                        state.overrides += 1
                        state.survey_overrides += 1
                        self._append('surveys.jsonl', dict(id=event_id, episode=list(key), step=state.step,
                            phase='started', planned_command_steps=4*self.survey_k))
                    else:
                        image = self.output/'inputs'/(event_id+'.png')
                        render_started = time.perf_counter()
                        collage(state, goal[i], image, evidence)
                        self.render_seconds += time.perf_counter()-render_started
                        row.update(image=str(image), image_sha256=hashlib.sha256(image.read_bytes()).hexdigest())
                        pending.append((i, row))
        choices = []
        if self.agent:
            pending,choices=self._agent_pending(pending,result)
        elif pending and self.cfg.mode == 'qwen':
            if self.client is None:
                if self.client_factory is None:
                    from src.qwen_client import QwenClient
                    self.client_factory = QwenClient
                self.client = self.client_factory(self.cfg, self.output/'worker')
            requests = [r for _, r in pending]
            if self.candidate_affordance and self.candidate_protocol != 'directional':
                requests = [candidate for row in requests for candidate in row['candidates']]
            response = self.client.score(self.request, requests)
            self.request += 1
            if [r['id'] for r in response['results']] != [r['id'] for r in requests]:
                raise RuntimeError('Recovery worker image ID/order mismatch')
            self.worker_seconds += response['seconds']
            if self.candidate_affordance and self.candidate_protocol == 'directional':
                from src.recovery_affordance import select_directional
                for (_, row), item in zip(pending, response['results']):
                    choices.append(select_directional(item,'A' if row['attempt']%2 else 'B',self.candidate_gap))
            elif self.candidate_affordance:
                from src.recovery_affordance import select_candidate,select_semantic_candidate
                selector=select_semantic_candidate if self.candidate_protocol=='semantic' else select_candidate
                selection_kwargs={}
                if self.candidate_protocol in ('semantic','semantic_balanced'):
                    selection_kwargs['relative_only']=bool(getattr(self.cfg,'candidate_relative_only',False))
                if self.candidate_protocol=='semantic_balanced':
                    selection_kwargs['preserve_clear_default']=bool(getattr(self.cfg,'candidate_preserve_clear_default',False))
                for j, (_, row) in enumerate(pending):
                    choices.append(selector(*response['results'][2*j:2*j+2],
                        'A' if row['attempt'] % 2 else 'B', self.candidate_gap,
                        **selection_kwargs))
            else:
                for item in response['results']:
                    label = choose(item['probabilities'], self.cfg.min_probability, self.cfg.min_margin)
                    choices.append((label, item))
        else:
            choices = [('C' if self.cfg.mode == 'scan' else 'A' if row['attempt'] % 2 == 1 else 'B', {}) for i, row in pending]
        for (i, row), (label, detail) in zip(pending, choices):
            state = self.states[i]
            if not row.get('active_survey', False):
                state.attempts += 1
            assert state.attempts == row['attempt']
            state.selections[label] += 1
            if self.candidate_affordance and self.cfg.mode == 'qwen':
                state.vlm_selections += detail['source'] == 'vlm'
                state.fallback_selections += detail['source'] in ('rule_fallback','safe_keep')
                state.vlm_rule_disagreements += detail['differs_from_rule'] and detail['source']=='vlm'
            state.earlier_choices.append(label)
            state.cooldown_until = state.step+self.cfg.turn_steps+self.cfg.forward_steps+self.cfg.cooldown
            if label != 'C':
                forward_steps=4 if self.agent and self.arm=="B" else self.cfg.forward_steps
                state.actions = deque(recovery_actions(label, self.cfg.turn_steps, forward_steps))
                state.issued_kind="recovery"
                if self.agent and self.arm=="B":state.probe=dict(id=row["id"],start=state.step,commands=[])
                row['planned_actions'] = [a.tolist() for a in state.actions]
                state.active_event = dict(id=row['id'], before=state.frames[-1].copy(),
                    end_step=state.step+self.cfg.turn_steps+self.cfg.forward_steps)
                result[i] = state.actions.popleft()
                state.overrides += 1
                state.recovery_overrides += 1
            else:
                state.rejected += 1
                if self.agent:state.cooldown_until=state.step+self.cfg.cooldown
            row.update(mode=self.cfg.mode, choice=label, model=detail, attempt=state.attempts)
            self._append('events.jsonl', row)
        for i, action in enumerate(result):
            state = self.states[i]
            actual = np.clip(action, -1, 1).astype(np.float32)
            state.last_action = actual
            state.last_kind=state.issued_kind
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
                   overrides=state.overrides, rejected=state.rejected, actions_sha256=state.action_digest.hexdigest(),
                   survey_steps=state.survey_overrides, recovery_steps=state.recovery_overrides,
                   completed_surveys=state.completed_surveys, selections=state.selections)
        row.update(vlm_selections=state.vlm_selections, fallback_selections=state.fallback_selections,
            vlm_rule_disagreements=state.vlm_rule_disagreements)
        assert state.overrides == state.survey_overrides+state.recovery_overrides
        assert state.overrides <= self.max_override_steps
        if state.survey is not None:
            self._append('surveys.jsonl', dict(id=state.survey['row']['id'], episode=list(key),
                step=state.step, phase='ended_with_real_episode'))
        row.update(agent_variant=self.arm,memory_hits=state.memory_hits,memory_prompt_entries=state.memory_prompt_entries,
            memory_changed_decisions=state.memory_changed,feedback_calls=state.feedback_calls,feedback_returns=state.feedback_returns)
        if state.memory is not None:
            row["memory_stats"]=dict(state.memory.stats)
            state.memory.clear("real_episode_finish")
        state.probe=None
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
            total_controller_seconds=self.total_seconds, mode=self.cfg.mode, active_survey=self.active_survey,
            max_override_steps=self.max_override_steps, candidate_affordance=self.candidate_affordance,
            agent_variant=self.arm, technical_errors=self.technical_errors), indent=2)+'\n')
