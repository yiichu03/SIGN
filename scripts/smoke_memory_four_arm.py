#!/usr/bin/env python3
"""Short engineering checks only. Never launches a formal split."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import numpy as np
TREE=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(TREE))
sys.path.insert(0,str(TREE/'scripts'))
from src.recovery_agent import image_item,save_rgb,select_agent
from src.qwen_client import QwenClient
from types import SimpleNamespace


def write(path,value):path.write_text(json.dumps(value,indent=2,allow_nan=False)+'\n')

def main():
    p=argparse.ArgumentParser();p.add_argument('--batch',type=Path,required=True);a=p.parse_args();b=a.batch.resolve()
    assert os.environ.get('PBS_JOBID') and os.environ.get('PYTHONHASHSEED')=='0'
    started=time.perf_counter()
    probes=json.loads((b/'probe_inputs.json').read_text());rows=[]
    for j,p in enumerate(probes):
        images=[image_item(role,p['view_files'][side]['path']) for role,side in [('GOAL','goal'),('CURRENT','forward'),('LEFT','left'),('RIGHT','right')]]
        rows.append(dict(id='probe'+str(j),task='arbitration',images=images,context='Technical input binding probe; no memory.'))
    swapped=dict(rows[0],id='swapped',images=[dict(x) for x in rows[0]['images']])
    swapped['images'][2]=dict(rows[0]['images'][3],role='LEFT');swapped['images'][3]=dict(rows[0]['images'][2],role='RIGHT')
    blank=save_rgb('GOAL',np.zeros((256,256,3),np.uint8),b/'blank.png')
    rows += [swapped,dict(id='blank',task='arbitration',images=[dict(blank,role=r) for r in ['GOAL','CURRENT','LEFT','RIGHT']],context='No usable visual evidence.')]
    memory=dict(rows[0],id='eight_images',images=list(rows[0]['images']))
    for j in range(2):
        memory['images'] += [dict(rows[1]['images'][2],role='MEMORY_'+str(j)+'_BEFORE'),dict(rows[1]['images'][3],role='MEMORY_'+str(j)+'_AFTER')]
    memory['context']='Technical image-count fixture only: historical before/after views, no verified correspondence or task outcome. Ignore if irrelevant.'
    rows.append(memory)
    rows.append(dict(rows[0],id='six_images',images=list(rows[0]['images'])+[
        dict(rows[1]['images'][2],role='MEMORY_0_BEFORE'),dict(rows[1]['images'][3],role='MEMORY_1_BEFORE')],
        context='Technical historical-keyframe fixture; correspondence unknown.'))
    rows.append(dict(id='feedback',task='feedback',images=[dict(rows[0]['images'][1],role='BEFORE_FORWARD'),dict(rows[0]['images'][1],role='AFTER_FORWARD')],
        context=json.dumps(dict(actual_commands=[[.6,0]]*4,note='Identical before/after technical control, not a newly collected outcome.'))))
    cfg=SimpleNamespace(request_timeout=600,startup_timeout=600,python_executable=str(TREE.parent/'envs/qwen35/bin/python'),
        model_dir=str(TREE.parent/'models/Qwen3.5-2B'),prompt='scripts/prompts/recovery_agent.txt',feedback_prompt='scripts/prompts/recovery_feedback.txt',
        worker_script='scripts/recovery_worker.py',verify_first_batch=True,candidate_affordance=True,candidate_protocol='agent')
    client=QwenClient(cfg,b/'worker_probe')
    try:response=client.score(0,rows)
    finally:client.close()
    write(b/'multi_image_probe.json',dict(inputs=rows,response=response,
        decisions={v['id']:select_agent(v,v['id']=='feedback') for v in response['results']},
        note='Swap/blank output is a bias diagnostic, not a performance label or tuning target.'))
    for arm in ['native','off','disabled','rule','A','B','C','D']:
        env=dict(os.environ)
        if arm=='native':env['RECOVERY_NATIVE_REFERENCE']='1'
        command=[sys.executable,str(TREE/'scripts/evaluate_recovery.py'),'--batch',str(b),'--run',str(b/('smoke_'+arm)),
            '--split','smoke','--mode','off','--arm','off' if arm=='native' else arm]
        with (b/('smoke_'+arm+'.log')).open('w') as log:subprocess.run(command,env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
    from evaluate_recovery import read_rows
    native=read_rows(b/'smoke_native/episodes')
    keys=['success','spl','view_match','navigation_reward','collisions','steps','pose_trace_sha256','actual_actions_sha256']
    for arm in ['off','disabled']:
        rows2=read_rows(b/('smoke_'+arm)/'episodes')
        assert set(rows2)==set(native)
        for key in native:
            for name in keys:assert native[key][name]==rows2[key][name],(arm,key,name)
    result=dict(passed=True,engineering_only=True,formal_submitted=False,seconds=time.perf_counter()-started,
        native_off_disabled_exact=True,arms={arm:json.loads((b/('smoke_'+arm)/'result.json').read_text()) for arm in ['native','off','disabled','rule','A','B','C','D']})
    write(b/'smoke_summary.json',result)

if __name__=='__main__':main()
