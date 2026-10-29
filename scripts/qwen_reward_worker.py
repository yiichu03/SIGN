#!/usr/bin/env python3
"""JSON-lines worker in qwen35. One resident FP32 Qwen3.5-2B, no navigation imports."""
import argparse
import contextlib
import hashlib
import json
import os
from pathlib import Path
import sys
import time
import traceback
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from qwen_single_image import SingleImageJudge


def emit(value):
    print(json.dumps(value,allow_nan=False),flush=True)


def main():
    p=argparse.ArgumentParser()
    for name in ['model-dir','prompt','output']:p.add_argument('--'+name,required=True)
    p.add_argument('--verify',type=int,default=0)
    a=p.parse_args();out=Path(a.output);prompt=Path(a.prompt).read_text()
    if Path(a.model_dir).name!='Qwen3.5-2B':raise ValueError('Training reward supports only Qwen3.5-2B')
    with contextlib.redirect_stdout(sys.stderr):
        judge=SingleImageJudge(a.model_dir,prompt,dtype='float32')
    version=hashlib.sha256(prompt.encode()).hexdigest()
    (out/'prompt.txt').write_text(prompt)
    emit(dict(ok=True,kind='ready',pid=os.getpid(),prompt_version=version,environment=judge.environment))
    verified=False;last_request=-1
    for line in sys.stdin:
        message=json.loads(line)
        if message['kind']=='close':break
        request=message['request_id'];rows=message['rows'];start=time.perf_counter()
        if message['kind']!='score' or request<=last_request:raise RuntimeError('Duplicate/out-of-order rollout request')
        ids=[r['id'] for r in rows]
        if len(set(ids))!=len(ids):raise RuntimeError('Duplicate image IDs')
        for row in rows:
            if hashlib.sha256(Path(row['image']).read_bytes()).hexdigest()!=row['image_sha256']:
                raise RuntimeError('Input image SHA mismatch')
        if a.verify and not verified and rows:
            probe=rows[:1]+rows[len(rows)//2:len(rows)//2+1]+rows[-1:]
            with contextlib.redirect_stdout(sys.stderr):
                check=judge.verify_readout([r['image'] for r in probe],[r['metadata'] for r in probe])
            (out/'verification.json').write_text(json.dumps(check,indent=2)+'\n')
            if not check['passed']:raise RuntimeError('Worker batch/solo verification failed')
            verified=True
        judge.torch.cuda.reset_peak_memory_stats()
        results=[]
        for index in range(0,len(rows),8):
            batch=rows[index:index+8]
            with contextlib.redirect_stdout(sys.stderr):
                values,audit=judge.class_probabilities([r['image'] for r in batch],[r['metadata'] for r in batch])
            for row,value in zip(batch,values):
                if not value['valid']:raise RuntimeError('Invalid logit readout: '+str(value['error']))
                results.append(dict(id=row['id'],**value,prompt_version=version,batch_seconds=audit['seconds']))
            if request==0:
                (out/f'first_batch_{index//8}.json').write_text(json.dumps(dict(items=batch,audit=audit,results=values),indent=2)+'\n')
        emit(dict(ok=True,request_id=request,results=results,seconds=time.perf_counter()-start,
                  batches=(len(rows)+7)//8,peak_gpu_gib=judge.torch.cuda.max_memory_allocated()/1024**3))
        last_request=request


if __name__=='__main__':
    try:main()
    except Exception:
        error=traceback.format_exc();sys.stderr.write(error);emit(dict(ok=False,error=error));sys.exit(1)
