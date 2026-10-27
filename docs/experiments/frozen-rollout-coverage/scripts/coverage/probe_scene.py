"""GPU scene check: actual camera headings, 2D occlusion, reset and metric cost."""
import json
import os
from pathlib import Path
import sys
import time

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import quaternion

ROOT=Path('/scratch/e1538633/liuyi');TREE=ROOT/'SIGN-frozen-rollout-coverage';HERE=Path(__file__).resolve().parent
os.chdir(str(TREE));sys.path.insert(0,str(TREE))
import run_sim
from src.utils import get_config
from habitat.utils.gym_definitions import make_gym_from_config
from habitat.utils.geometry_utils import quaternion_rotate_vector
from habitat.utils.visualizations.fog_of_war import bresenham_supercover_line

opts=['habitat.dataset.content_scenes', '["Adrian"]']
cfg=get_config('exp_config/ppo_imagenav_gibson.yaml,policy,reward,sensors,rollout_coverage',opts,
               'train',str(TREE/'results/gibson_rollout_coverage_20261027/scene_probe'),False,'',False)
assert float(cfg.habitat.simulator.rgb_sensor.hfov)==float(cfg.habitat.task.observed_coverage.fov)==90.
env=make_gym_from_config(cfg)
start=time.perf_counter();env.reset();initial_reset_seconds=time.perf_counter()-start
hab=env.env._env.habitat_env;sim=hab.sim;m=hab.task.measurements.measures['observed_coverage']
assert m.get_metric()['delta_m2']==0.
m.update_metric(None);assert m.get_metric()['delta_m2']==0.
position=np.array(sim.get_agent_state().position)
figure,axes=plt.subplots(2,4,figsize=(13,7),constrained_layout=True)
orientations=[];occluded_examples=[]
for col,yaw in enumerate([0.,np.pi/2,np.pi,-np.pi/2]):
    rotation=quaternion.from_rotation_vector([0.,yaw,0.])
    sim.set_agent_state(position,rotation)
    m.reset_metric(None)
    image=sim.get_sensor_observations()['rgb']
    from habitat.utils.visualizations import maps
    point=np.array(maps.to_grid(position[2],position[0],m._grid.shape,sim=sim))
    forward=quaternion_rotate_vector(rotation,np.array([0.,0.,-1.]))
    direction=np.array([forward[2],forward[0]])
    seen=np.argwhere(m._seen>0);projection=(seen-point).dot(direction)
    assert (projection>=-1.).mean()>.95, 'Coverage points behind actual camera heading'
    visible= m._seen.astype(bool)
    display=np.ones((*m._grid.shape,3));display[m._grid==0]=.15;display[(m._grid==1)&~visible]=.65;display[visible]=[.2,.7,.9]
    axes[0,col].imshow(image);axes[0,col].set_title('Camera yaw {:.0f} deg'.format(yaw*180/np.pi));axes[0,col].axis('off')
    axes[1,col].imshow(display);axes[1,col].plot(point[1],point[0],'ro',markersize=3)
    axes[1,col].arrow(point[1],point[0],direction[1]*12,direction[0]*12,color='red',width=.3)
    axes[1,col].set_title('Rows = +Z, columns = +X');axes[1,col].axis('off')
    orientations.append({'yaw_degrees':yaw*180/np.pi,'visible_cells':int(visible.sum()),'forward_fraction':float((projection>=-1.).mean())})
    # Find actual navigable cells hidden behind a wall inside the 3m / 90deg cone.
    found=None
    for dr in range(-29,30):
        if found is not None:break
        for dc in range(-29,30):
            distance=np.hypot(dr,dc)
            if distance<4 or distance>29 or np.dot([dr,dc],direction)/distance<.75:continue
            target=point+np.array([dr,dc])
            if not (0<=target[0]<m._grid.shape[0] and 0<=target[1]<m._grid.shape[1]):continue
            if m._grid[tuple(target)]!=1 or visible[tuple(target)]:continue
            line=bresenham_supercover_line(point,target)
            if any(m._grid[int(p[0]),int(p[1])]==0 for p in line):
                found={'yaw_degrees':yaw*180/np.pi,'agent_grid':point.tolist(),'hidden_valid_cell':target.tolist()};break
    if found is not None:occluded_examples.append(found)
assert occluded_examples, 'No actual-map occlusion example found within test views'
figure.savefig(HERE/'camera_coverage_alignment.png',dpi=160);plt.close(figure)
durations=[]
for _ in range(100):
    started=time.perf_counter();m.update_metric(None);durations.append(time.perf_counter()-started)
    assert m.get_metric()['delta_m2']==0.
report={'passed':True,'scene':'Adrian','rgb_hfov':90.,'coverage_fov':90.,'visibility_dist_m':3.,'meters_per_pixel':.1,
        'map_shape':list(m._grid.shape),'initial_reset_seconds_including_numba':initial_reset_seconds,
        'repeated_metric_median_ms':float(np.median(durations)*1000),
        'repeated_metric_p95_ms':float(np.percentile(durations,95)*1000),
        'orientations':orientations,'actual_map_occlusion_examples':occluded_examples,
        'proxy_scope':'Episode-local XZ union of visible navmesh cells with 2D wall occlusion; not literal RGB surface area or 3D visibility.'}
(HERE/'scene_probe.json').write_text(json.dumps(report,indent=2)+'\n')
env.close();print(json.dumps(report,indent=2),flush=True)
