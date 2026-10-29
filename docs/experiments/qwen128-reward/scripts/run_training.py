"""Immutable launch plan: short controls or a fresh formal training process."""
import argparse,hashlib,json,os,subprocess,sys,time
from pathlib import Path
ROOT=Path('/scratch/e1538633/liuyi');HERE=Path(__file__).resolve().parent
TREE=ROOT/'SIGN-qwen128-reward'

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def guard():
    manifest=json.loads((HERE/'source_manifest.json').read_text())
    for name,item in manifest['trees'].items():
        tree=ROOT/name
        assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=tree,text=True).strip()==item['commit'],name
        for file,digest in item['files'].items():assert sha(tree/file)==digest,(name,file)
    for file,digest in manifest['assets'].items():assert sha(ROOT/file)==digest,file

def run(tree,out,steps=None,qwen=False,beta=.1):
    assert not out.exists(),str(out)
    opts=['habitat_baselines.num_environments','8','habitat_baselines.rl.ppo.num_steps','256',
          'habitat_baselines.rl.ddppo.pretrained_encoder','True',
          'habitat_baselines.rl.ddppo.pretrained_weights','ckpt/nav_model.pth',
          'habitat_baselines.rl.ddppo.train_encoder','False','habitat_baselines.num_checkpoints','-1']
    if steps is not None:opts+=['habitat_baselines.total_num_steps',str(float(steps)),
                              'habitat_baselines.checkpoint_interval',str(steps//2048),
                              'habitat_baselines.log_interval','1']
    else:opts+=['habitat_baselines.checkpoint_interval','250','habitat_baselines.log_interval','10']
    config='exp_config/ppo_imagenav_gibson.yaml,policy,reward,sensors'
    if qwen:
        config+=',qwen_reward';opts+=['qwen_reward.beta',str(beta)]
        if steps is not None and beta>0:opts+=['qwen_reward.verify_first_batch','True','qwen_reward.sample_interval','5']
    command=[sys.executable,'run_sim.py','--exp-config',config,'--run-type','train','--model-dir',str(out)]+opts
    out.parent.mkdir(parents=True,exist_ok=True)
    (HERE/(out.name+'_command.json')).write_text(json.dumps(dict(cwd=str(tree),command=command),indent=2)+'\n')
    print('EXECUTE',json.dumps(command),flush=True)
    started=time.time()
    with (HERE/(out.name+'.log')).open('w') as log:subprocess.run(command,cwd=tree,stdout=log,stderr=subprocess.STDOUT,check=True)
    (HERE/(out.name+'_walltime.json')).write_text(json.dumps(dict(seconds=time.time()-started))+'\n')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('mode',choices=['short','formal']);a=p.parse_args()
    assert os.environ.get('PBS_JOBID') and os.environ.get('PYTHONHASHSEED')=='0'
    guard()
    out=TREE/'results/qwen128_reward_20261029'
    if a.mode=='short':
        run(ROOT/'SIGN',out/'short_baseline_8192',8192)
        run(TREE,out/'short_zero_8192',8192,True,0.)
        run(TREE,out/'short_qwen_40960',40960,True,.1)
        subprocess.run([sys.executable,str(HERE/'verify_short.py')],check=True)
    else:
        report=json.loads((HERE/'short_validation.json').read_text());assert report['passed']
        run(TREE,out/'train_personal_8env',qwen=True)
    guard()
