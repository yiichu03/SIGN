"""Fresh independent A/B/C runs; the original jobs and directories are protected."""
import argparse,hashlib,json,os,subprocess,sys,time
from pathlib import Path
ROOT=Path('/scratch/e1538633/liuyi');HERE=Path(__file__).resolve().parent;TREE=ROOT/'SIGN-qwen-ablation'
CONFIGS={'A':'qwen_a128','B':'qwen_b256','C':'geometry_c128'}
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def guard():
    m=json.loads((HERE/'source_manifest.json').read_text())
    for name,item in m['trees'].items():
        t=ROOT/name;assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=t,text=True).strip()==item['commit'],name
        for file,digest in item['files'].items():assert sha(t/file)==digest,(name,file)
    for file,digest in m['assets'].items():assert sha(ROOT/file)==digest,file
    frozen=json.loads((TREE/'docs/experiments/qwen128-reward/ablations/calibration/calibration.json').read_text())
    assert frozen['alpha']==.2927574680399425 and frozen['valid_segments']==1176

def main():
    p=argparse.ArgumentParser();p.add_argument('case',choices=CONFIGS);p.add_argument('stage',choices=['short','formal']);a=p.parse_args()
    assert os.environ.get('PBS_JOBID') and os.environ.get('PYTHONHASHSEED')=='0'
    guard();short=a.stage=='short';support=HERE/a.case;support.mkdir(exist_ok=True)
    output=TREE/'results/qwen_ablation_20261029'/a.case/('short_40960' if short else 'train')
    assert not output.exists(),str(output)
    if not short:assert json.loads((support/'short_validation.json').read_text())['passed']
    opts=['habitat_baselines.num_environments','8','habitat_baselines.rl.ppo.num_steps','256',
          'habitat_baselines.rl.ddppo.pretrained_encoder','True','habitat_baselines.rl.ddppo.pretrained_weights','ckpt/nav_model.pth',
          'habitat_baselines.rl.ddppo.train_encoder','False','habitat_baselines.num_checkpoints','-1',
          'habitat_baselines.checkpoint_interval','20' if short else '250','habitat_baselines.log_interval','1' if short else '10']
    if short:
        opts+=['habitat_baselines.total_num_steps','40960.0']
        if a.case!='C':opts+=['qwen_reward.verify_first_batch','True','qwen_reward.sample_interval','5']
    config='exp_config/ppo_imagenav_gibson.yaml,policy,reward,sensors,qwen_reward,'+CONFIGS[a.case]
    command=[sys.executable,'run_sim.py','--exp-config',config,'--run-type','train','--model-dir',str(output)]+opts
    (support/(a.stage+'_command.json')).write_text(json.dumps(dict(cwd=str(TREE),command=command),indent=2)+'\n')
    print('RUN',a.case,a.stage,json.dumps(command),flush=True);started=time.time()
    with (support/(a.stage+'.log')).open('x') as f:subprocess.run(command,cwd=TREE,stdout=f,stderr=subprocess.STDOUT,check=True)
    (support/(a.stage+'_walltime.json')).write_text(json.dumps(dict(seconds=time.time()-started))+'\n')
    if short:subprocess.run([sys.executable,str(HERE/'verify_case.py'),a.case],check=True)
    guard()
if __name__=='__main__':main()
