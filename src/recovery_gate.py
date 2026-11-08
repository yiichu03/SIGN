"""Short, observed RGB/action history for a pre-scan intervention decision."""
import json
import numpy as np
from src.recovery_agent import save_rgb


GATE_LABELS = ('progress', 'blocked', 'unknown')


def select_gate(value):
    """Only observed progress vetoes recovery; uncertainty preserves the rule."""
    try:
        p = np.asarray(value['probabilities'], dtype=float)
        mass = float(value['candidate_mass'])
        if (not value.get('valid', True) or p.shape != (3,) or not np.isfinite(p).all()
                or (p < 0).any() or not np.isclose(p.sum(), 1., atol=1e-6)
                or not np.isfinite(mass)):
            raise ValueError('Invalid gate probabilities')
        if mass < .1:
            return 'unknown', 'insufficient_candidate_token_mass'
        rank = np.argsort(p)
        if p[rank[-1]] - p[rank[-2]] <= 1e-6:
            return 'unknown', 'tied_choice'
        return GATE_LABELS[int(rank[-1])], 'model_argmax'
    except (KeyError, TypeError, ValueError):
        return 'unknown', 'invalid_model_evidence'


def gate_request(state, event_id, mode, directory):
    """Images at 0/5/11/16 for the frozen 16-action window, with true timing.

    Both modes receive the same executed actions. P3 only receives the current
    RGB; P4 additionally receives three older RGBs. No GT/detector statistics.
    """
    if mode not in ('current', 'history'):
        raise ValueError('Unknown intervention gate')
    if len(state.images) != state.window + 1 or len(state.commands) != state.window:
        raise RuntimeError('Gate image/action history boundary mismatch')
    indices = sorted(set([0, state.window // 3, (2 * state.window + 2) // 3, state.window]))
    if mode == 'current':
        indices = [state.window]
    start = state.step - state.window
    frames = list(state.images)
    commands = np.asarray(state.commands, dtype=np.float32)
    if commands.shape != (state.window, 2) or not np.isfinite(commands).all():
        raise RuntimeError('Invalid gate executed actions')
    images = []
    for index in indices:
        role = 'CURRENT' if index == state.window else 'HISTORY_STEP_' + str(start + index)
        images.append(save_rgb(role, frames[index], directory / (event_id + '.gate.' + str(index) + '.png')))
    actual = [dict(step=start+i, normalized_action=action.tolist(),
        commanded_linear_velocity_m_s=float((action[0]+1)*.125),
        commanded_angular_velocity_deg_s=float(action[1]*15)) for i, action in enumerate(commands)]
    context = dict(window_start_step=start, current_step=state.step,
        actual_action_count=state.window, image_steps=[start+i for i in indices],
        actual_executed_actions=actual,
        command_note='Executed velocity commands, not measured displacement. RGB at step t precedes action t.')
    return dict(id=event_id + ':gate', task='intervention_gate', images=images,
        context=json.dumps(context, sort_keys=True))


def current_shadow(request):
    """Unexecuted P3 decision at the exact P4 observation, on the same worker."""
    context = json.loads(request['context'])
    context['image_steps'] = [context['current_step']]
    return dict(request, id=request['id'] + ':without_history', images=request['images'][-1:],
        context=json.dumps(context, sort_keys=True))


def validate_gate_request(row):
    images = row['images']
    context = json.loads(row['context'])
    steps = context['image_steps']
    if len(images) not in (1, 4) or len(images) != len(steps):
        raise RuntimeError('Gate image count mismatch')
    if steps != sorted(set(steps)) or steps[-1] != context['current_step']:
        raise RuntimeError('Gate image time/order mismatch')
    roles = ['HISTORY_STEP_' + str(t) for t in steps[:-1]] + ['CURRENT']
    if [x['role'] for x in images] != roles:
        raise RuntimeError('Gate image role/order mismatch')
    start, end = context['window_start_step'], context['current_step']
    actions = context['actual_executed_actions']
    if (end-start != context['actual_action_count'] or len(actions) != end-start
            or [x['step'] for x in actions] != list(range(start, end))
            or any(t < start for t in steps)):
        raise RuntimeError('Gate action/image boundary mismatch')
    if len(images) == 4 and steps != [start, start+(end-start)//3, start+(2*(end-start)+2)//3, end]:
        raise RuntimeError('Gate keyframe sampling mismatch')
    for item in actions:
        a = np.asarray(item['normalized_action'], dtype=float)
        if a.shape != (2,) or not np.isfinite(a).all() or (np.abs(a) > 1).any():
            raise RuntimeError('Gate action values mismatch')
        if not np.isclose(item['commanded_linear_velocity_m_s'], (a[0]+1)*.125) or not np.isclose(item['commanded_angular_velocity_deg_s'], a[1]*15):
            raise RuntimeError('Gate physical action binding mismatch')
