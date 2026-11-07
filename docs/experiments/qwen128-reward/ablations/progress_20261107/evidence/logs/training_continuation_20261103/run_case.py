"""Launch exactly one new continuation output; old experiments remain read-only."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT=Path('/scratch/e1538633/liuyi');HERE=Path(__file__).resolve().parent

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def guard():
    manifest=json.loads((HERE/'source_manifest.json').read_text())
    for name,item in manifest['trees'].items():
        tree=ROOT/name
        assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=tree,text=True).strip()==item['commit'],name
        for path,digest in item['files'].items():assert sha(tree/path)==digest,(name,path)
    sys.path.insert(0,str(ROOT/'logs/qwen_ablation_20261029'))
    from run_case import guard as original_guard
    # This module is executed as __main__; the imported module is the old guard.
    original_guard()

def run(case, stage):
    assert os.environ.get('PBS_JOBID') and os.environ.get('PYTHONHASHSEED')=='0'
    guard();p=json.loads((HERE/'plan.json').read_text())[case]
    assert sha(p['checkpoint'])==p['checkpoint_sha256']
    tree=Path(p['tree']);out=tree/'results/continuation_20261103'/case/stage
    assert not out.exists(),str(out)
    if stage=='train':assert json.loads((HERE/case/'short_validation.json').read_text())['passed']
    opts=['habitat_baselines.num_environments','8','habitat_baselines.rl.ppo.num_steps','256',
          'habitat_baselines.rl.ddppo.pretrained_encoder','True','habitat_baselines.rl.ddppo.pretrained_weights','ckpt/nav_model.pth',
          'habitat_baselines.rl.ddppo.train_encoder','False','habitat_baselines.num_checkpoints','-1',
          'habitat_baselines.checkpoint_interval','2' if stage=='short' else '250',
          'habitat_baselines.log_interval','1' if stage=='short' else '10',
          'training_continuation.checkpoint',p['checkpoint'],
          'training_continuation.sha256',p['checkpoint_sha256'],
          'training_continuation.stop_after_steps','4096' if stage=='short' else '0']+p['extra_options']
    if stage=='short' and case in ['qwen01','A','B']:
        opts+=['qwen_reward.verify_first_batch','True']
    command=[sys.executable,'run_sim.py','--exp-config',p['exp_config'],'--run-type','train','--model-dir',str(out)]+opts
    (HERE/case/(stage+'_command.json')).write_text(json.dumps(dict(cwd=str(tree),command=command,output=str(out)),indent=2)+'\n')
    print('START',case,stage,json.dumps(command),flush=True);started=time.time()
    with (HERE/case/(stage+'.log')).open('x') as log:
        subprocess.run(command,cwd=tree,stdout=log,stderr=subprocess.STDOUT,check=True)
    (HERE/case/(stage+'_walltime.json')).write_text(json.dumps(dict(seconds=time.time()-started))+'\n')
    if stage=='short':subprocess.run([sys.executable,str(HERE/'verify_short.py'),case],check=True)
    guard()

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('case');parser.add_argument('stage',choices=['short','train']);args=parser.parse_args()
    run(args.case,args.stage)
