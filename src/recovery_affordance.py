"""Independent candidate views and label-balanced local affordance selection."""
import hashlib
from pathlib import Path
import numpy as np


LABELS = 'A: BLOCKED\nB: UNCERTAIN\nC: OPEN'
REVERSED_LABELS = 'A: OPEN\nB: UNCERTAIN\nC: BLOCKED'


def reversed_prompt(prompt):
    if prompt.count(LABELS) != 1:
        raise ValueError('Expected exactly one affordance label definition')
    return prompt.replace(LABELS, REVERSED_LABELS)


def semantic_probabilities(values, reversed_labels=False):
    p = np.asarray(values, dtype=np.float64)
    if p.shape != (3,) or not np.isfinite(p).all() or (p < 0).any() or not np.isclose(p.sum(), 1., atol=1e-6):
        raise ValueError('Invalid independent candidate probabilities')
    blocked, uncertain, opened = p[::-1] if reversed_labels else p
    return dict(blocked=float(blocked), uncertain=float(uncertain), opened=float(opened),
        support=float(opened+0.5*uncertain))


def select_candidate(left, right, fallback, gap=0.05):
    if fallback not in ('A', 'B') or not np.isfinite(gap) or not 0 < gap <= 1:
        raise ValueError('Invalid candidate fallback or support gap')
    evidence = {}
    for name, item in [('left', left), ('right', right)]:
        evidence[name] = [semantic_probabilities(item['probabilities']),
            semantic_probabilities(item['reversed_probabilities'], True)]
    deltas = [evidence['left'][i]['support']-evidence['right'][i]['support'] for i in range(2)]
    chosen = None
    if all(d >= gap for d in deltas):
        chosen = 'left'
    elif all(d <= -gap for d in deltas):
        chosen = 'right'
    if chosen and not all(p['opened'] > max(p['blocked'], p['uncertain']) for p in evidence[chosen]):
        chosen = None
    label = ('A' if chosen == 'left' else 'B') if chosen else fallback
    return label, dict(source='vlm' if chosen else 'rule_fallback', default_rule_choice=fallback,
        differs_from_rule=bool(chosen and label != fallback), support_deltas=deltas,
        evidence=evidence, support_gap=gap, candidates=dict(left=left, right=right))


def candidate_image(view, goal, destination):
    """Same layout and text for either side; side IDs remain outside model input."""
    from PIL import Image, ImageDraw, ImageFont
    canvas = Image.new('RGB', (512, 384), 'white')
    draw = ImageDraw.Draw(canvas)
    font_path = Path(__file__).resolve().parents[2]/'envs/sign-baseline/lib/python3.8/site-packages/matplotlib/mpl-data/fonts/ttf/DejaVuSans.ttf'
    font = ImageFont.truetype(str(font_path), 16)
    draw.text((6, 4), 'CANDIDATE CAMERA VIEW', fill='black', font=font)
    draw.text((6, 25), 'Assess the visible route for a small forward attempt.', fill='black', font=font)
    canvas.paste(Image.fromarray(np.asarray(view, dtype=np.uint8)).resize((320, 320)), (0, 55))
    draw.text((336, 55), 'GOAL CONTEXT', fill='black', font=font)
    canvas.paste(Image.fromarray(np.asarray(goal, dtype=np.uint8)).resize((160, 160)), (336, 81))
    draw.text((336, 253), 'Local RGB only', fill='black', font=font)
    canvas.save(destination)
    return dict(image=str(destination), image_sha256=hashlib.sha256(Path(destination).read_bytes()).hexdigest())
