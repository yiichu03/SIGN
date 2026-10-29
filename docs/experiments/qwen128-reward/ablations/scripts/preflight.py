"""CPU merged-config and source audits; no simulator construction."""
import json,sys
from pathlib import Path
ROOT=Path('/scratch/e1538633/liuyi');HERE=Path(__file__).resolve().parent;TREE=ROOT/'SIGN-qwen-ablation'
sys.path.insert(0,str(TREE));sys.path.insert(0,str(HERE))
import run_sim
from habitat_baselines.config.default import get_config
from src.utils import change_habitat_config
from run_case import guard,CONFIGS
guard()
paths=['exp_config/ppo_imagenav_gibson.yaml']+['src/config/'+s+'.yaml' for s in ['policy','reward','sensors','qwen_reward']]
opts=['habitat_baselines.num_environments','8','habitat_baselines.rl.ppo.num_steps','256','habitat_baselines.rl.ddppo.pretrained_encoder','True','habitat_baselines.rl.ddppo.train_encoder','False','habitat_baselines.num_checkpoints','-1','habitat_baselines.checkpoint_interval','250']
def flat(c,p=''):
    if hasattr(c,'items'):
        result={}
        for k,v in c.items():result.update(flat(v,p+str(k)+'.'))
        return result
    return {p[:-1]:c}
base=change_habitat_config(get_config(paths,opts));diffs={}
for case,name in CONFIGS.items():
    cfg=change_habitat_config(get_config(paths+['src/config/'+name+'.yaml'],opts));values=flat(cfg);reference=flat(base)
    diffs[case]={k:[reference[k],v] for k,v in values.items() if reference.get(k)!=v};assert all(k.startswith('qwen_reward.') for k in diffs[case])
    assert cfg.habitat_baselines.rl.data_augmentation.mrq_reward_target=='navigation'
    assert cfg.habitat_baselines.total_num_steps==3e8 and cfg.habitat.seed==100
    assert cfg.habitat.simulator.rgb_sensor.hfov==cfg.qwen_reward.fov==90
    assert cfg.habitat.task.observed_coverage.weight==0
    assert cfg.qwen_reward.meters_per_pixel==.025 and cfg.qwen_reward.visibility_dist==3.
    assert cfg.habitat_baselines.rl.ddppo.pretrained_encoder and not cfg.habitat_baselines.rl.ddppo.train_encoder
    if case=='C':assert not cfg.qwen_reward.enabled and cfg.qwen_reward.geometry_alpha==.2927574680399425 and cfg.qwen_reward.beta==0
    else:assert cfg.qwen_reward.enabled and cfg.qwen_reward.beta==.03
    (HERE/case/'formal_config_preinit.yaml').write_text(str(cfg))
(HERE/'config_audit.json').write_text(json.dumps(dict(passed=True,case_differences=diffs,other_hyperparameters_identical=True,navigation_mrq_all_cases=True,seed=100,hash_seed='PBS exports0',num_envs=8,rollout_steps=256,geometry_calibration_frozen=True),indent=2)+'\n')
print('A/B/C configs match approved changes only; original initialization/other hyperparameters unchanged')
