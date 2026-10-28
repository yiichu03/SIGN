"""Offline topdown judge boundary; intentionally independent of Habitat and PPO."""
import hashlib
import json
import math
import shutil
from pathlib import Path


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def dump(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n')


def strict_json(text):
    def unique(pairs):
        result = {}
        for k, v in pairs:
            if k in result:
                raise ValueError('Duplicate JSON key: ' + k)
            result[k] = v
        return result
    def invalid(value):
        raise ValueError('Non-finite JSON constant: ' + value)
    return json.loads(text, object_pairs_hook=unique, parse_constant=invalid)


def prepare(manifest_path, prompt_path, output, allow_unequal_steps=False):
    """Freeze an eight-image request. Caller supplies task identity per candidate."""
    source = Path(manifest_path).resolve()
    spec = strict_json(source.read_text())
    candidates = spec['candidates']
    ids = [c['id'] for c in candidates]
    if len(ids) != 8 or len(set(ids)) != 8 or not all(isinstance(x, str) and x.isalnum() for x in ids):
        raise ValueError('Expected eight unique alphanumeric candidate IDs')
    tasks = [c['task'] for c in candidates]
    required = {'scene_id', 'episode_id', 'start_position', 'start_rotation', 'goal_sha256', 'policy_sha256'}
    if any(not required.issubset(t) for t in tasks):
        raise ValueError('Incomplete task/initial-condition identity')
    if len({json.dumps(t, sort_keys=True, allow_nan=False) for t in tasks}) != 1:
        raise ValueError('Candidates must share task, start, goal, and policy version')
    steps = [c['steps'] for c in candidates]
    if any(type(s) is not int or s <= 0 for s in steps):
        raise ValueError('Steps must be positive integers')
    equal = len(set(steps)) == 1
    if not equal and not allow_unequal_steps:
        raise ValueError('Unequal action budgets; use explicit diagnostic override')
    if any(c.get('window_start_step') != 0 for c in candidates):
        raise ValueError('This initial pilot accepts episode-start windows only')
    # Validate before creating an immutable request directory.
    images = [(source.parent / c['image']).resolve() for c in candidates]
    for p in images:
        if not p.is_file() or p.read_bytes()[:8] != b'\x89PNG\r\n\x1a\n':
            raise ValueError('Expected local PNG: ' + str(p))
    prompt = Path(prompt_path).read_text()
    if not prompt.strip():
        raise ValueError('Empty prompt')
    folder = Path(output)
    folder.mkdir(parents=True, exist_ok=False)
    (folder / 'images').mkdir()
    content = [{'type': 'text', 'text': prompt}]
    metadata = []
    for c, p in zip(candidates, images):
        target = Path('images') / (c['id'] + '.png')
        shutil.copyfile(p, folder / target)
        # Deliberate allowlist: do not leak success, model labels or human scores.
        public = {k: c[k] for k in ('id', 'steps', 'covered_percent', 'new_percent', 'new_m2') if k in c}
        for k, value in public.items():
            if k not in ('id', 'steps') and (type(value) not in (int, float) or not math.isfinite(value) or value < 0 or ('percent' in k and value > 100)):
                raise ValueError('Invalid coverage metadata')
        metadata.append(public)
        content.extend([{'type': 'text', 'text': json.dumps(public, ensure_ascii=False)}, {'type': 'image', 'image': str(target)}])
    if not equal:
        content.insert(1, {'type': 'text', 'text': 'DIAGNOSTIC ONLY: unequal action budgets; raw coverage totals are not efficiency rankings.'})
    request = {'version': 1, 'group_id': spec['group_id'], 'candidate_ids': ids,
               'equal_steps': equal, 'reward_integration': False,
               'messages': [{'role': 'user', 'content': content}]}
    dump(folder / 'request.json', request)
    dump(folder / 'provenance.json', {'manifest': spec, 'manifest_sha256': sha256(source),
         'prompt_sha256': sha256(prompt_path), 'images': {str(p): sha256(folder / p) for p in [Path('images') / (x + '.png') for x in ids]}})
    dump(folder / 'seal.json', {p: sha256(folder / p) for p in ('request.json', 'provenance.json')})
    return folder


def verify(folder):
    folder = Path(folder)
    for p, expected in strict_json((folder / 'seal.json').read_text()).items():
        if sha256(folder / p) != expected:
            raise ValueError('Changed request/provenance: ' + p)
    provenance = strict_json((folder / 'provenance.json').read_text())
    for p, expected in provenance['images'].items():
        if sha256(folder / p) != expected:
            raise ValueError('Changed image: ' + p)
    return strict_json((folder / 'request.json').read_text())


def parse_response(raw, ids, response_format='relative_scores_v1', truncated=False):
    """No regex repair, no coercion of unknown/ties into zero or unique ranks."""
    if truncated:
        raise ValueError('Generation hit token limit')
    value = strict_json(raw)
    if not isinstance(value, dict):
        raise ValueError('Response must be a JSON object')
    if response_format == 'json_object':
        return value
    if response_format != 'relative_scores_v1':
        raise ValueError('Unknown response format')
    scores = value.get('scores')
    if not isinstance(scores, list) or len(scores) != len(ids):
        raise ValueError('Expected exactly eight scores')
    if len({s['id'] for s in scores}) != len(ids) or {s['id'] for s in scores} != set(ids):
        raise ValueError('Missing, duplicate or unknown score IDs')
    for s in scores:
        score = s['score']
        if score is not None and (type(score) not in (int, float) or not math.isfinite(score) or not 0 <= score <= 1):
            raise ValueError('Scores must be numeric in [0,1] or null')
    return value


def run(folder, output, config):
    """One request containing eight images, not eight independent requests."""
    if not config['enabled']:
        return {'status': 'disabled'}  # No filesystem, torch, model or GPU work.
    import os
    import time
    import copy
    import torch
    import transformers
    from transformers import AutoProcessor, Qwen3_5ForConditionalGeneration
    if not os.environ.get('PBS_JOBID') or not torch.cuda.is_available():
        raise RuntimeError('Qwen inference requires a PBS GPU job')
    request = verify(folder)
    result_dir = Path(output)
    result_dir.mkdir(parents=True, exist_ok=False)
    dump(result_dir / 'run_config.json', config)
    model_dir = Path(config['model_dir'])
    model_files = {p.name: {'bytes': p.stat().st_size} for p in model_dir.glob('*.safetensors')}
    audit = {'status': 'loading', 'job': os.environ['PBS_JOBID'], 'torch': torch.__version__,
             'transformers': transformers.__version__, 'model_files': model_files,
             'model_config_sha256': sha256(model_dir / 'config.json'), 'request_sha256': sha256(Path(folder) / 'request.json')}
    dump(result_dir / 'audit.json', audit)
    try:
        torch.manual_seed(config['seed'])
        processor = AutoProcessor.from_pretrained(model_dir, local_files_only=True)
        model = Qwen3_5ForConditionalGeneration.from_pretrained(model_dir, dtype='auto', device_map='cuda:0', local_files_only=True).eval()
        messages = copy.deepcopy(request['messages'])
        for item in messages[0]['content']:
            if item['type'] == 'image':
                item['image'] = str((Path(folder) / item['image']).resolve())
        # Bound visual tokens: no unbounded default-resolution eight-image prefill.
        inputs = processor.apply_chat_template(messages, add_generation_prompt=True, enable_thinking=False,
            tokenize=True, return_dict=True, return_tensors='pt',
            images_kwargs={'size': {'shortest_edge': 65536, 'longest_edge': config['max_image_pixels']}}).to(model.device)
        tokens = inputs['input_ids'].shape[-1]
        if tokens > config['max_input_tokens']:
            raise ValueError('Input exceeds configured token budget: ' + str(tokens))
        dump(result_dir / 'actual_input.json', {'rendered_chat': processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True, enable_thinking=False), 'input_ids': inputs['input_ids'][0].tolist(), 'image_grid_thw': inputs['image_grid_thw'].cpu().tolist()})
        torch.cuda.reset_peak_memory_stats();torch.cuda.synchronize();start = time.perf_counter()
        with torch.inference_mode():
            generated = model.generate(**inputs, max_new_tokens=config['max_new_tokens'], do_sample=False)
        torch.cuda.synchronize()
        ids = generated[0, tokens:].tolist()
        raw = processor.decode(ids, skip_special_tokens=True, clean_up_tokenization_spaces=False)
        (result_dir / 'response.txt').write_text(raw)
        dump(result_dir / 'output_token_ids.json', ids)
        eos = model.generation_config.eos_token_id
        eos = eos if isinstance(eos, list) else [eos]
        truncated = len(ids) >= config['max_new_tokens'] and ids[-1] not in eos
        audit.update(status='generated', input_tokens=tokens, output_tokens=len(ids), image_count=8,
            generation_seconds=time.perf_counter()-start, peak_gpu_gib=torch.cuda.max_memory_allocated()/1024**3, truncated=truncated)
        try:
            parsed = parse_response(raw, request['candidate_ids'], config['response_format'], truncated)
            dump(result_dir / 'parsed.json', parsed)
            audit.update(status='valid', parse_error=None)
        except (ValueError, KeyError, TypeError) as exc:
            audit.update(status='invalid_response', parse_error=str(exc))
        # Input integrity checked once more after inference.
        verify(folder)
    except Exception as exc:
        audit.update(status='failed', error=repr(exc));raise
    finally:
        dump(result_dir / 'audit.json', audit)
    return audit
