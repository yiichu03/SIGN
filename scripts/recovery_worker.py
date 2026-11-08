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
from recovery_affordance import reversed_prompt


def emit(row):
    print(json.dumps(row, allow_nan=False), flush=True)


def agent_score(judge, rows, prompts, output, request, verified, verify):
    """One resident model; real role-bound multi-image requests, never collages."""
    results = {}
    for task, labels in [('arbitration',('left','right','keep')),('feedback',('continue','return'))]:
        selected=[r for r in rows if r['task']==task]
        if not selected:continue
        judge.prompt=prompts[task]
        for row in selected:
            roles=[x['role'] for x in row['images']]
            expected=['GOAL','CURRENT','LEFT','RIGHT'] if task=='arbitration' else ['BEFORE_FORWARD','AFTER_FORWARD']
            if roles[:len(expected)]!=expected or len(roles)>8:raise RuntimeError('Multi-image role/order mismatch')
            for image in row['images']:
                if hashlib.sha256(Path(image['image']).read_bytes()).hexdigest()!=image['image_sha256']:
                    raise RuntimeError('Agent image SHA mismatch')
        if verify and task not in verified:
            longest=max(selected,key=lambda r:len(r['images']))
            samples=[selected[0],longest] if longest['id']!=selected[0]['id'] else selected[:2]
            check=judge.verify_choices(samples,labels)
            (output/('verification_'+task+'.json')).write_text(json.dumps(check,indent=2)+'\n')
            if not check['passed']:raise RuntimeError('Multi-image batch/solo/readout verification failed')
            verified.add(task)
        for start in range(0,len(selected),2):
            batch=selected[start:start+2]
            values,audit=judge.choice_probabilities(batch,labels=labels)
            records=[]
            for row,value in zip(batch,values):
                value.update(id=row['id'],prompt_version=hashlib.sha256(judge.prompt.encode()).hexdigest())
                results[row['id']]=value;records.append(value)
            (output/('request_%06d_%s_%d.json'%(request,task,start//2))).write_text(
                json.dumps(dict(inputs=batch,audit=audit,results=records),indent=2,allow_nan=False)+'\n')
    if set(results)!={r['id'] for r in rows}:raise RuntimeError('Unknown/missing agent task ID')
    return [results[r['id']] for r in rows]


def main():
    parser = argparse.ArgumentParser()
    for name in ('model-dir', 'prompt', 'output'):
        parser.add_argument('--'+name, required=True)
    parser.add_argument('--verify', type=int, default=1)
    parser.add_argument('--task', choices=['actions', 'candidate', 'semantic', 'semantic_balanced', 'directional','agent'], default='actions')
    parser.add_argument('--feedback-prompt')
    parser.add_argument('--inverse-prompt')
    args = parser.parse_args()
    output = Path(args.output)
    prompt = Path(args.prompt).read_text()
    inverse = reversed_prompt(prompt) if args.task == 'candidate' else None
    if args.task=='semantic_balanced':
        if not args.inverse_prompt:raise ValueError('Semantic consensus needs the negative question')
        inverse=Path(args.inverse_prompt).read_text()
    labels=(('No','Unknown','Yes') if args.task in ('semantic','semantic_balanced') else
        ('left','right','Unknown') if args.task=='directional' else ('A','B','C'))
    if Path(args.model_dir).name != 'Qwen3.5-2B':
        raise ValueError('This experiment uses only Qwen3.5-2B')
    with contextlib.redirect_stdout(sys.stderr):
        judge = SingleImageJudge(args.model_dir, prompt, dtype='float32',max_image_pixels=65536 if args.task=='agent' else 262144)
    agent_prompts=None
    if args.task=='agent':
        agent_prompts=dict(arbitration=prompt,feedback=Path(args.feedback_prompt).read_text())
        (output/'feedback_prompt.txt').write_text(agent_prompts['feedback'])
    version = hashlib.sha256(prompt.encode()).hexdigest()
    (output/'prompt.txt').write_text(prompt)
    if inverse is not None:
        (output/'reversed_prompt.txt').write_text(inverse)
    emit(dict(ok=True, kind='ready', pid=os.getpid(), prompt_version=version, environment=judge.environment))
    last = -1
    verified = False
    agent_verified=set()
    for line in sys.stdin:
        message = json.loads(line)
        if message['kind'] == 'close':
            break
        request, rows = message['request_id'], message['rows']
        if message['kind'] != 'score' or request <= last or not rows:
            raise RuntimeError('Invalid/duplicate recovery request')
        if len({r['id'] for r in rows}) != len(rows):
            raise RuntimeError('Duplicate recovery event IDs')
        if args.task=='agent':
            started=time.perf_counter()
            with contextlib.redirect_stdout(sys.stderr):
                results=agent_score(judge,rows,agent_prompts,output,request,agent_verified,args.verify)
            emit(dict(ok=True,request_id=request,results=results,seconds=time.perf_counter()-started,
                peak_gpu_gib=judge.torch.cuda.max_memory_allocated()/1024**3))
            last=request
            continue
        for row in rows:
            if hashlib.sha256(Path(row['image']).read_bytes()).hexdigest() != row['image_sha256']:
                raise RuntimeError('Recovery input image SHA mismatch')
        started = time.perf_counter()
        if args.verify and not verified:
            with contextlib.redirect_stdout(sys.stderr):
                audit = judge.verify_readout([r['image'] for r in rows[:3]], None, labels=labels)
            if args.task=='semantic_balanced':
                judge.prompt=inverse
                with contextlib.redirect_stdout(sys.stderr):
                    inverse_check=judge.verify_readout([r['image'] for r in rows[:3]],None,labels=labels)
                judge.prompt=prompt
                audit['inverse_verification']=inverse_check
                audit['passed']=audit['passed'] and inverse_check['passed']
            (output/'verification.json').write_text(json.dumps(audit, indent=2)+'\n')
            if not audit['passed']:
                raise RuntimeError('Recovery ABC batch/solo/generation verification failed')
            verified = True
        results = []
        for start in range(0, len(rows), 8):
            batch = rows[start:start+8]
            with contextlib.redirect_stdout(sys.stderr):
                values, audit = judge.class_probabilities([r['image'] for r in batch], None, labels=labels)
            inverted = [None]*len(batch)
            if inverse is not None:
                judge.prompt = inverse
                with contextlib.redirect_stdout(sys.stderr):
                    inverted, inverse_audit = judge.class_probabilities([r['image'] for r in batch], None, labels=labels)
                judge.prompt = prompt
                audit = dict(standard=audit, reversed=inverse_audit)
            for row, value, reverse in zip(batch, values, inverted):
                if not value['valid']:
                    raise RuntimeError('Invalid recovery ABC logits')
                # Positional probabilities are interpreted by the selected protocol.
                results.append(dict(id=row['id'], probabilities=[value[k] for k in ('p_low', 'p_medium', 'p_high')],
                    logits=value['logits'], candidate_mass=value['candidate_mass'], prompt_version=version))
                if reverse is not None:
                    if not reverse['valid']:
                        raise RuntimeError('Invalid reversed candidate logits')
                    results[-1].update(reversed_probabilities=[reverse[k] for k in ('p_low','p_medium','p_high')],
                        reversed_logits=reverse['logits'], reversed_candidate_mass=reverse['candidate_mass'],
                        reversed_prompt_version=hashlib.sha256(inverse.encode()).hexdigest())
            (output/f'request_{request:06d}_batch_{start//8}.json').write_text(json.dumps(dict(
                inputs=batch,audit=audit,results=results[-len(batch):]),indent=2)+'\n')
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
