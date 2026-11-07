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
        obs=super().reset();self._eval_steps=0;self._eval_reward=0.;self._eval_trace=hashlib.sha256()
        state=self.habitat_env.sim.get_agent_state()
        self._eval_start=[float(v) for v in state.position]
        self._eval_goal_sha=hashlib.sha256(np.ascontiguousarray(obs['imagegoal_sensor_v2']).tobytes()).hexdigest()
        return obs

    def step(self,*args,**kwargs):
        obs,reward,done,info=super().step(*args,**kwargs)
        self._eval_steps+=1;self._eval_reward+=float(reward)
        state=self.habitat_env.sim.get_agent_state();q=state.rotation
        self._eval_trace.update(np.asarray(list(state.position)+[q.x,q.y,q.z,q.w],dtype=np.float32).tobytes())
        if 'observed_coverage' in info:
            new=float(info['observed_coverage']['new_area_m2']);assert np.isfinite(new) and new>=0
            info['coverage_eval']={'steps':self._eval_steps,'new_area_m2':new,'new_m2_per_step':new/self._eval_steps}
        if done:
            ep=self.habitat_env.current_episode
            row={'scene_id':ep.scene_id,'episode_id':str(ep.episode_id),'steps':self._eval_steps,
                 'success':float(info['success']),'spl':float(info['spl']),'view_match':float(info['view_match']),
                 'navigation_reward':self._eval_reward,'collisions':float(info['collisions']['count']),
                 'goal_sha256':self._eval_goal_sha,'start_position':self._eval_start,'pose_trace_sha256':self._eval_trace.hexdigest()}
            if 'coverage_eval' in info:row.update(new_area_m2=new,new_m2_per_step=new/self._eval_steps)
            target=Path(os.environ['COVERAGE_EVAL_EPISODES']);target.mkdir(parents=True,exist_ok=True)
            with (target/('worker_'+str(os.getpid())+'.jsonl')).open('a') as f:f.write(json.dumps(row,allow_nan=False)+'\n')
        return obs,reward,done,info

@habitat.registry.register_env(name='CoverageEvalGym')
class CoverageEvalGym(gym.Wrapper):
    def __init__(self,config,dataset=None):
        super().__init__(HabGymWrapper(RecordingNavEnv(config=config,dataset=dataset)))
