"""Reuse native SIGN policy and original pilot collector for 16 distinct tasks."""
import os,sys,json,hashlib,random
from pathlib import Path
import numpy as np
import torch
from PIL import Image
ROOT=Path('/scratch/e1538633/liuyi');HERE=Path(__file__).resolve().parent;TREE=ROOT/'SIGN-coverage-eval'
os.chdir(TREE);sys.path.insert(0,str(TREE))
import run_sim
from src.utils import get_config
from src.trainer import PPOTrainer,batch_obs,apply_obs_transforms_batch
from src.metric import ObservedCoverage
from habitat.config import Config
from habitat.utils.gym_definitions import make_gym_from_config
from habitat.utils.visualizations import maps
from habitat.utils.geometry_utils import quaternion_rotate_vector
assert torch.cuda.is_available() and os.environ['PYTHONHASHSEED']=='0';torch.set_num_threads(1)
plan=json.loads((HERE/'plan.json').read_text());results=[]
for group in plan['groups']:
 for index,item in enumerate(group['cases']):
  case=HERE/group['id']/item['id'];assert not (case/'trajectory.json').exists()
  opts=['habitat.dataset.data_path',str(case/'task.json.gz'),'habitat.dataset.split','val',
        'habitat.dataset.content_scenes',str([item['scene']]),'habitat_baselines.num_environments','1']
  cfg=get_config('exp_config/ppo_imagenav_gibson.yaml,policy,reward,sensors,eval',opts,'eval',str(case/'config'),False,'',False)
  random.seed(100);np.random.seed(100);torch.manual_seed(100)
  env=make_gym_from_config(cfg);hab=env.env._env.habitat_env;sim=hab.sim
  trainer=PPOTrainer(cfg);trainer.device=torch.device('cuda:0');trainer.obs_space=env.observation_space
  trainer.policy_action_space=env.action_space;trainer.orig_policy_action_space=env.original_action_space
  trainer._setup_actor_critic_agent(cfg.habitat_baselines.rl.ppo)
  checkpoint=torch.load(TREE/'ckpt/nav_model.pth',map_location='cpu');loaded=trainer.agent.load_state_dict(checkpoint['state_dict'],strict=False)
  safe=torch.load(TREE/'ckpt/safety_model.pth',map_location='cpu')
  if 'state_dict' not in safe:trainer.agent.actor_critic.Qc.load_state_dict(safe,strict=False)
  else:trainer.agent.load_state_dict({k:v for k,v in safe['state_dict'].items() if 'Qc' in k},strict=False)
  policy=trainer.agent.actor_critic;policy.eval()
  (case/'load_audit.json').write_text(json.dumps({'missing':loaded.missing_keys,'unexpected':loaded.unexpected_keys},indent=2))
  obs=env.reset();seed=3000+len(results);torch.manual_seed(seed);torch.cuda.manual_seed_all(seed)
  assert str(hab.current_episode.episode_id)==item['episode_id'] and Path(hab.current_episode.scene_id).stem==item['scene']
  m=ObservedCoverage(sim,Config({'meters_per_pixel':.1,'visibility_dist':3.,'fov':90.}));m.reset_metric(None)
  grid=m._grid.copy();valid_union=grid==1;initial=m._seen.copy()
  Image.fromarray(obs['rgb']).save(case/'initial_rgb.png');Image.fromarray(obs['imagegoal_sensor_v2']).save(case/'goal.png')
  hidden=torch.zeros(1,policy.num_recurrent_layers,cfg.habitat_baselines.rl.ppo.hidden_size,device='cuda')
  prev=torch.zeros(1,*env.action_space.shape,device='cuda');mask=torch.zeros(1,1,dtype=torch.bool,device='cuda');cost=torch.zeros(1,1,device='cuda')
  def pose(step):
   state=sim.get_agent_state();q=state.rotation;rc=maps.to_grid(state.position[2],state.position[0],m._grid.shape,sim=sim)
   f=quaternion_rotate_vector(q,np.array([0.,0.,-1.]))
   return {'step':step,'position_xyz':state.position.tolist(),'rotation_xyzw':[float(q.x),float(q.y),float(q.z),float(q.w)],'map_row':int(rc[0]),'map_col':int(rc[1]),'heading_rad':float(np.arctan2(f[0],f[2]))}
  points=[pose(0)];done=False;reward_total=0.;grid_changes=0
  for step in range(1,257):
   batch=apply_obs_transforms_batch(batch_obs([obs],device=trainer.device),trainer.obs_transforms);batch['cost']=cost
   with torch.inference_mode():_,actions,_,hidden=policy.act(batch,hidden,prev,mask,deterministic=False,eval=False)
   action=np.clip(actions[0].cpu().numpy(),env.action_space.low,env.action_space.high).astype(env.action_space.dtype)
   obs,reward,done,info=env.step(action);m.update_metric(None)
   grid_changes+=int(not np.array_equal(grid,m._grid));valid_union|=m._grid==1
   point=pose(step);point.update(action=action.tolist(),collision=bool(info['collisions.is_collision']),delta_m2=m.get_metric()['delta_m2']);points.append(point)
   prev.copy_(actions);mask.fill_(not done);cost.fill_(float(info['collisions.is_collision']));reward_total+=reward
   if step%64==0 or done:Image.fromarray(obs['rgb']).save(case/('rgb_%03d.png'%step))
   if done:break
  np.savez_compressed(case/'map_data.npz',grid=grid,valid_union=valid_union,initial_seen=initial,seen=m._seen)
  data={'scene_id':hab.current_episode.scene_id,'episode_id':str(hab.current_episode.episode_id),'sampling_seed':seed,'stochastic':True,'done':bool(done),'window_steps':len(points)-1,'grid_changed_steps':grid_changes,'mpp':.1,'fov':90,'radius':3,'poses':points,'navigation_reward':float(reward_total),'final_metrics':{k:float(v) for k,v in info.items() if isinstance(v,(int,float,np.number))}}
  (case/'trajectory.json').write_text(json.dumps(data,indent=2)+'\n');results.append({'group':group['id'],'case':item['id'],'scene':item['scene'],'episode_id':item['episode_id'],'steps':len(points)-1,'done':bool(done),'height_range':float(np.ptp([p['position_xyz'][1] for p in points]))})
  print(results[-1],flush=True);env.close();del trainer,policy,env,sim,hab;torch.cuda.empty_cache()
(HERE/'collection_complete.json').write_text(json.dumps({'job':os.environ.get('PBS_JOBID'),'trajectories':results},indent=2)+'\n')
