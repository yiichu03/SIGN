"""Eval-only telemetry wrapper; calls original reward/done/step without mutation."""
import hashlib,json,os
from pathlib import Path
import numpy as np
import gym
import habitat
from habitat.utils.gym_adapter import HabGymWrapper
from src.environment import NavRLEnvX

class RecordingNavEnv(NavRLEnvX):
    def reset(self):
        obs=super().reset();self._eval_steps=0;self._eval_reward=0.;self._eval_trace=hashlib.sha256();self._action_trace=hashlib.sha256()
        state=self.habitat_env.sim.get_agent_state()
        self._eval_start=[float(v) for v in state.position]
        if os.environ.get('RECOVERY_VIEW_AUDIT'):
            q=state.rotation;self._view_poses=[list(state.position)+[q.x,q.y,q.z,q.w]];self._view_commands=[]
        self._eval_goal_sha=hashlib.sha256(np.ascontiguousarray(obs['imagegoal_sensor_v2']).tobytes()).hexdigest()
        if os.environ.get('RECOVERY_PROBE_IMAGES') and not getattr(self, '_saved_probe', False):
            from PIL import Image
            target = Path(os.environ['RECOVERY_PROBE_IMAGES']);target.mkdir(parents=True, exist_ok=True)
            for name in ['rgb', 'imagegoal_sensor_v2']:
                Image.fromarray(np.asarray(obs[name], dtype=np.uint8)).save(target/(str(os.getpid())+'_'+name+'.png'))
            self._saved_probe = True
        return obs

    def step(self,*args,**kwargs):
        action=kwargs['action']['action_args']
        actual=np.asarray([float(np.asarray(action[n]).reshape(-1)[0]) for n in ['linear_velocity','angular_velocity']],dtype=np.float32)
        self._action_trace.update(actual.tobytes())
        if os.environ.get('RECOVERY_VIEW_AUDIT'):self._view_commands.append(actual)
        obs,reward,done,info=super().step(*args,**kwargs)
        self._eval_steps+=1;self._eval_reward+=float(reward)
        state=self.habitat_env.sim.get_agent_state();q=state.rotation
        self._eval_trace.update(np.asarray(list(state.position)+[q.x,q.y,q.z,q.w],dtype=np.float32).tobytes())
        if os.environ.get('RECOVERY_VIEW_AUDIT'):self._view_poses.append(list(state.position)+[q.x,q.y,q.z,q.w])
        if 'observed_coverage' in info:
            new=float(info['observed_coverage']['new_area_m2']);assert np.isfinite(new) and new>=0
            info['coverage_eval']={'steps':self._eval_steps,'new_area_m2':new,'new_m2_per_step':new/self._eval_steps}
        if done:
            ep=self.habitat_env.current_episode
            if os.environ.get('RECOVERY_VIEW_AUDIT'):
                path=Path(os.environ['RECOVERY_VIEW_AUDIT']);path.mkdir(parents=True,exist_ok=True)
                np.savez_compressed(path/(Path(ep.scene_id).stem+'_'+str(ep.episode_id)+'.npz'),
                    poses=np.asarray(self._view_poses,dtype=np.float32),commands=np.asarray(self._view_commands,dtype=np.float32))
            row={'scene_id':ep.scene_id,'episode_id':str(ep.episode_id),'steps':self._eval_steps,
                 'success':float(info['success']),'spl':float(info['spl']),'view_match':float(info['view_match']),
                 'navigation_reward':self._eval_reward,'collisions':float(info['collisions']['count']),
                 'goal_sha256':self._eval_goal_sha,'start_position':self._eval_start,'pose_trace_sha256':self._eval_trace.hexdigest(),
                 'actual_actions_sha256':self._action_trace.hexdigest()}
            if 'coverage_eval' in info:row.update(new_area_m2=new,new_m2_per_step=new/self._eval_steps)
            target=Path(os.environ['COVERAGE_EVAL_EPISODES']);target.mkdir(parents=True,exist_ok=True)
            with (target/('worker_'+str(os.getpid())+'.jsonl')).open('a') as f:f.write(json.dumps(row,allow_nan=False)+'\n')
        return obs,reward,done,info

@habitat.registry.register_env(name='CoverageEvalGym')
class CoverageEvalGym(gym.Wrapper):
    def __init__(self,config,dataset=None):
        super().__init__(HabGymWrapper(RecordingNavEnv(config=config,dataset=dataset)))
