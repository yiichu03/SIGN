"""Bind recovery evaluations to the actual model and its cached native reference."""
import hashlib
import json
from pathlib import Path


def validate_checkpoint(tasks, loaded_step):
    checkpoint, reference = tasks['checkpoint'], tasks['reference']
    step = checkpoint['step']
    if type(step) is not int or step <= 0 or loaded_step != step:
        raise ValueError('Loaded checkpoint step differs from the task manifest')
    digest = hashlib.sha256(Path(checkpoint['path']).read_bytes()).hexdigest()
    if digest != checkpoint['sha256'] or reference['checkpoint_sha256'] != digest:
        raise ValueError('Checkpoint/reference SHA mismatch')
    directory = Path(reference['directory'])
    cached_checkpoint = json.loads((directory/'checkpoint.json').read_text())
    cached_result = json.loads((directory/'result.json').read_text())
    if any(value != step for value in [reference['training_step'], cached_checkpoint['step'], cached_result['training_step']]):
        raise ValueError('Cached native reference belongs to a different training step')
    if cached_checkpoint['sha256'] != digest:
        raise ValueError('Cached native reference belongs to a different checkpoint')
    if cached_result['episodes'] != 4200:
        raise ValueError('Expected the complete 4200-task native reference')
    return directory
