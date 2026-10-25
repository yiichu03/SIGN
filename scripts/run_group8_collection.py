#!/usr/bin/env python3
"""Collect and verify eight repetitions without duplicating episode identities."""
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from preview_trajectory_layouts import white_gradient

BASE=Path(__file__).resolve().parents[1]
ROOT=BASE/'results/qwen_diagnostic/group8_p12'

def main():
    m=json.loads((ROOT/'manifest.json').read_text())
    for g in m['groups']:
        folder=ROOT/g['group']
        if not (folder/'collection_verified.json').exists():
            if list(folder.glob('episode_*/waypoints.json')):
                raise RuntimeError('Partial group present; inspect before restarting: '+str(folder))
            env=dict(os.environ,SIGN_TRACE_DIR=str(folder))
            cmd=[sys.executable,'run_sim.py','--exp-config','exp_config/ppo_imagenav_hm3d.yaml,policy,reward,sensors,eval','--run-type','eval','--model-dir',str(folder/'eval'),
                 'habitat_baselines.eval_ckpt_path_dir','ckpt/nav_model.pth','habitat_baselines.eval.split',g['split'],
                 'habitat_baselines.num_environments','1','habitat_baselines.test_episode_count','-1',
                 'habitat_baselines.eval.evals_per_ep','8','habitat.seed',str(g['seed']),
                 'habitat.dataset.data_path',str(folder/'task.json.gz')]
            print('COLLECT',g['group'],flush=True)
            subprocess.run(cmd,cwd=BASE,env=env,check=True)
            cases=sorted(folder.glob('episode_*/waypoints.json'))
            assert len(cases)==8,len(cases)
            goals=set();starts=set();initials=set();paths=set();rows=[]
            for p in cases:
                d=json.loads(p.read_text());assert str(d['episode_id'])==str(g['task']['episode_id'])
                assert Path(d['scene_id']).name==Path(g['task']['scene_id']).name
                starts.add(json.dumps(d['start'],sort_keys=True))
                goals.add(hashlib.sha256((p.parent/'goal.png').read_bytes()).hexdigest())
                initials.add(hashlib.sha256((p.parent/'rgb/step_0000.png').read_bytes()).hexdigest())
                paths.add(hashlib.sha256(json.dumps(d['waypoints'],sort_keys=True).encode()).hexdigest())
                white_gradient(p.parent,p.parent/'trajectory2.png')
                rows.append(dict(case=p.parent.name,steps=len(d['waypoints'])))
            assert len(starts)==len(goals)==len(initials)==1,(starts,goals,initials)
            verification=dict(episodes=rows,start_variants=len(starts),goal_image_sha256=list(goals)[0],initial_rgb_sha256=list(initials)[0],distinct_trajectories=len(paths),sampling='native stochastic policy; no temperature modification',pbs_job_id=os.environ.get('PBS_JOBID'))
            (folder/'collection_verified.json').write_text(json.dumps(verification,indent=2)+'\n')
            print('VERIFIED',g['group'],verification,flush=True)
    (ROOT/'collection_complete.json').write_text(json.dumps({'groups':10,'trajectories':80,'pbs_job_id':os.environ.get('PBS_JOBID')},indent=2)+'\n')

if __name__=='__main__':main()
