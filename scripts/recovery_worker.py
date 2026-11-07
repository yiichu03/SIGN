#!/usr/bin/env python3
"""Resident FP32 worker using the existing single-image ABC readout unchanged."""
import argparse
import contextlib
import hashlib
import json
import os
from pathlib import Path
import sys
import time
import traceback
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'src'))
from qwen_single_image import SingleImageJudge


def emit(row):
    print(json.dumps(row, allow_nan=False), flush=True)


def main():
    parser = argparse.ArgumentParser()
    for name in ('model-dir', 'prompt', 'output'):
        parser.add_argument('--'+name, required=True)
    parser.add_argument('--verify', type=int, default=1)
    args = parser.parse_args()
    output = Path(args.output)
    prompt = Path(args.prompt).read_text()
    if Path(args.model_dir).name != 'Qwen3.5-2B':
        raise ValueError('This experiment uses only Qwen3.5-2B')
    with contextlib.redirect_stdout(sys.stderr):
        judge = SingleImageJudge(args.model_dir, prompt, dtype='float32')
    version = hashlib.sha256(prompt.encode()).hexdigest()
    (output/'prompt.txt').write_text(prompt)
    emit(dict(ok=True, kind='ready', pid=os.getpid(), prompt_version=version, environment=judge.environment))
    last = -1
    verified = False
    for line in sys.stdin:
        message = json.loads(line)
        if message['kind'] == 'close':
            break
        request, rows = message['request_id'], message['rows']
        if message['kind'] != 'score' or request <= last or not rows:
            raise RuntimeError('Invalid/duplicate recovery request')
        if len({r['id'] for r in rows}) != len(rows):
            raise RuntimeError('Duplicate recovery event IDs')
        for row in rows:
            if hashlib.sha256(Path(row['image']).read_bytes()).hexdigest() != row['image_sha256']:
                raise RuntimeError('Recovery input image SHA mismatch')
        started = time.perf_counter()
        if args.verify and not verified:
            with contextlib.redirect_stdout(sys.stderr):
                audit = judge.verify_readout([r['image'] for r in rows[:3]], None)
            (output/'verification.json').write_text(json.dumps(audit, indent=2)+'\n')
            if not audit['passed']:
                raise RuntimeError('Recovery ABC batch/solo/generation verification failed')
            verified = True
        results = []
        for start in range(0, len(rows), 8):
            batch = rows[start:start+8]
            with contextlib.redirect_stdout(sys.stderr):
                values, audit = judge.class_probabilities([r['image'] for r in batch], None)
            for row, value in zip(batch, values):
                if not value['valid']:
                    raise RuntimeError('Invalid recovery ABC logits')
                # A/B/C are actions here. The inherited ordinal q is not used.
                results.append(dict(id=row['id'], probabilities=[value[k] for k in ('p_low', 'p_medium', 'p_high')],
                    logits=value['logits'], candidate_mass=value['candidate_mass'], prompt_version=version))
            (output/f'request_{request:06d}_batch_{start//8}.json').write_text(json.dumps(dict(inputs=batch, audit=audit), indent=2)+'\n')
        emit(dict(ok=True, request_id=request, results=results, seconds=time.perf_counter()-started,
                  peak_gpu_gib=judge.torch.cuda.max_memory_allocated()/1024**3))
        last = request


if __name__ == '__main__':
    try:
        main()
    except Exception:
        error = traceback.format_exc()
        sys.stderr.write(error)
        emit(dict(ok=False, error=error))
        sys.exit(1)
