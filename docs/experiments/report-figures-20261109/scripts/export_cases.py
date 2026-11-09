"""Export recorded navigation evidence with CPU plotting/video decoding only."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import shutil
import numpy as np
import imageio.v2 as imageio
from PIL import Image
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

p=argparse.ArgumentParser();p.add_argument('--workspace',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
ROOT=a.workspace;OUT=a.out;OUT.mkdir(parents=True,exist_ok=True)
DIAG=ROOT/'logs/sign_failure_replay_20261104/full/coverage256/diagnostic'
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':12,'axes.spines.top':False,'axes.spines.right':False,'pdf.fonttype':42,'svg.fonttype':'none'})
sources={};results=[]

def source(path):
    raw=path.read_bytes();sources[str(path)]=dict(sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw));return path

def write_json(path,obj):
    path.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n')

def save(fig,path,vector=True):
    fig.savefig(path.with_suffix('.png'),dpi=200,bbox_inches='tight',facecolor='white')
    if vector:fig.savefig(path.with_suffix('.pdf'),bbox_inches='tight',facecolor='white')
    plt.close(fig)

def csv_write(path,rows):
    with path.open('w') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)

def background(ax,d,show_coverage=True):
    g=d['initial_grid'];b=d['map_bounds_xyz'];im=np.ones((*g.shape,3))
    im[g==1]=[.84,.85,.87]
    if show_coverage:
        im[d['initial_seen'].astype(bool)]=[.17,.30,.55]
        im[d['final_seen'].astype(bool)&~d['initial_seen'].astype(bool)]=[.57,.79,.93]
    ax.imshow(im,origin='lower',extent=[b[0,0],b[1,0],b[0,2],b[1,2]],interpolation='nearest',zorder=0)
    ax.set_aspect('equal');ax.set(xlabel='World X (m)',ylabel='World Z (m)')
    # Remove empty map margins, without changing map/trajectory coordinates.
    rr,cc=np.nonzero((g==1) | (d['final_seen'].astype(bool) if show_coverage else False))
    xlo=b[0,0]+cc.min()/g.shape[1]*(b[1,0]-b[0,0]);xhi=b[0,0]+(cc.max()+1)/g.shape[1]*(b[1,0]-b[0,0])
    zlo=b[0,2]+rr.min()/g.shape[0]*(b[1,2]-b[0,2]);zhi=b[0,2]+(rr.max()+1)/g.shape[0]*(b[1,2]-b[0,2])
    if 'position_xyz' in d:
        points=np.vstack([d['position_xyz'],d['goal_position_xyz'][None,:]])
        xlo=min(xlo,points[:,0].min());xhi=max(xhi,points[:,0].max());zlo=min(zlo,points[:,2].min());zhi=max(zhi,points[:,2].max())
    pad=.035*max(xhi-xlo,zhi-zlo);ax.set_xlim(xlo-pad,xhi+pad);ax.set_ylim(zlo-pad,zhi+pad)

def map_plot(ax,d,steps):
    background(ax,d);xy=d['position_xyz'][:,[0,2]];goal=d['goal_position_xyz']
    ax.plot(xy[:,0],xy[:,1],color='#d34945',lw=1.6,label='Executed path',zorder=2)
    ax.scatter(*xy[0],c='#2b8c4b',s=58,edgecolor='white',label='Start',zorder=5)
    ax.scatter(*xy[-1],c='#21252a',marker='X',s=65,label='End',zorder=6)
    ax.scatter(goal[0],goal[2],marker='*',s=145,color='#ffc947',edgecolor='#5a4624',label='Goal position',zorder=4)
    for s in steps[1:-1]:
        ax.scatter(*xy[s],s=15,color='#94332e',zorder=4)
    handles,labels=ax.get_legend_handles_labels();handles += [Patch(color='#2b4d8c',label='Initial view'),Patch(color='#91c9ed',label='Newly observed')]
    ax.legend(handles=handles,fontsize=8,ncol=2,loc='best')
    ax.set_title('Recorded trajectory and observed coverage',fontsize=13)

def area_plot(ax,d,steps):
    names=d['metric_fields'].tolist();area=d['metrics'][:,names.index('coverage_new_area_m2')]
    ax.plot(np.arange(len(area)),area,c='#2463a2',lw=2.3)
    ax.scatter(steps,area[steps],c='#2463a2',s=25)
    ax.set(xlabel='Executed action step',ylabel='Cumulative new observed area (m²)',xlim=(0,500),ylim=(0,max(1,area[-1]*1.12)))
    ax.set_title('Exploration gain over the full 500 actions',fontsize=13);ax.grid(alpha=.18)
    ax.annotate(f'{area[-1]:.2f} m²',xy=(500,area[-1]),xytext=(-9,12),textcoords='offset points',ha='right',fontsize=11,color='#2463a2')

def rgb_row(fig,gs,goal,images,steps):
    ax=fig.add_subplot(gs[0]);ax.imshow(goal,interpolation='nearest');ax.set_title('GOAL',fontweight='bold');ax.axis('off')
    for i,(step,im) in enumerate(zip(steps,images)):
        ax=fig.add_subplot(gs[i+1]);ax.imshow(im,interpolation='nearest');ax.set_title(f'step {step}');ax.axis('off')

cases=[('Mosquito','3564',[0,184,278,371,465,500],'Repeated revisits with little new coverage'),
       ('Cantwell','1688',[0,120,198,250,375,500],'Persistent local stagnation after earlier exploration')]
for scene,ep,steps,title in cases:
    out=OUT/'failures'/(scene+'_'+ep);out.mkdir(parents=True,exist_ok=True)
    path=source(DIAG/'traces'/scene/(ep+'.npz'))
    with np.load(path,allow_pickle=False) as f:d={k:f[k] for k in f.files}
    meta=json.loads(str(d['metadata_json']));assert meta['steps']==500 and meta['success']==0 and meta['reference_pose_hash_equal']
    assert meta['step_limit_reached'] and not meta['stop_called']
    assert np.array_equal(d['initial_grid'],d['final_grid'])
    names=d['metric_fields'].tolist();metrics=d['metrics'];area=metrics[:,names.index('coverage_new_area_m2')];delta=metrics[:,names.index('coverage_delta_m2')]
    assert area[0]==0 and np.all(np.diff(area)>=-1e-10) and np.allclose(np.cumsum(delta),area,atol=1e-8)
    mask_gain=np.count_nonzero(d['final_seen'].astype(bool)&~d['initial_seen'].astype(bool))*float(d['meters_per_pixel'])**2
    assert abs(mask_gain-area[-1])<1e-7,(mask_gain,area[-1])
    video=source(DIAG/meta['video']);goalpath=source(video.with_suffix('.goal.png'));goal=np.asarray(Image.open(goalpath).convert('RGB'))
    assert hashlib.sha256(np.ascontiguousarray(goal).tobytes()).hexdigest()==meta['goal_sha256']
    shutil.copyfile(goalpath,out/'goal.png')
    images={};reader=imageio.get_reader(str(video),ffmpeg_params=['-threads','1'])
    try:
        for step,frame in enumerate(reader):
            if step in steps:images[step]=frame[:128,128:256].copy()
            if step==500:break
    finally:reader.close()
    assert set(images)==set(steps)
    for step,im in images.items():
        Image.fromarray(im).save(out/f'rgb_step_{step:03d}.png')
        fig,ax=plt.subplots(figsize=(3,3.2),constrained_layout=True);ax.imshow(im,interpolation='nearest');ax.axis('off');ax.set_title(f'{scene} / {ep} — step {step}',fontsize=11);save(fig,out/f'labelled_step_{step:03d}',False)
    fig=plt.figure(figsize=(16,8.8),constrained_layout=True);outer=fig.add_gridspec(2,2,height_ratios=[2.4,1])
    map_plot(fig.add_subplot(outer[0,0]),d,steps);area_plot(fig.add_subplot(outer[0,1]),d,steps)
    rgb_row(fig,outer[1,:].subgridspec(1,7),goal,[images[s] for s in steps],steps)
    fig.suptitle(f'{scene} / episode {ep} | {title}',fontsize=18)
    fig.text(.5, -.025, 'Coverage256 125.952M | recovery OFF | failure at 500 actions | initial view excluded from new-area curve',fontsize=10,ha='center')
    save(fig,out/'case_overview')
    fig,ax=plt.subplots(figsize=(8,6),constrained_layout=True);map_plot(ax,d,steps);save(fig,out/'trajectory_coverage')
    fig,ax=plt.subplots(figsize=(8,4.5),constrained_layout=True);area_plot(ax,d,steps);save(fig,out/'new_coverage_curve')
    fig=plt.figure(figsize=(16,2.8),constrained_layout=True);rgb_row(fig,fig.add_gridspec(1,7),goal,[images[s] for s in steps],steps);save(fig,out/'rgb_storyboard')
    rows=[];pos=d['position_xyz'];commands=d['command_mps_degps'];dist=np.linalg.norm(np.diff(pos,axis=0),axis=1)
    for s in range(501):
        row=dict(scene_id=meta['scene_id'],episode_id=ep,step=s,x=float(pos[s,0]),y=float(pos[s,1]),z=float(pos[s,2]),
                 delta_new_area_m2=float(delta[s]),cumulative_new_area_m2=float(area[s]),
                 displacement_m=0 if s==0 else float(dist[s-1]),linear_velocity_mps=float(commands[s,0]),angular_velocity_degps=float(commands[s,1]))
        row.update({n:float(metrics[s,j]) for j,n in enumerate(names) if n not in ['coverage_delta_m2','coverage_new_area_m2']});rows.append(row)
    csv_write(out/'trajectory_and_coverage.csv',rows)
    selected=dict(scene_id=meta['scene_id'],episode_id=ep,title=title,steps=500,success=False,recovery='off',checkpoint_training_steps=125952000,
       screenshot_steps=steps,frame_source='Original recorded H264 video, cropped right 128x128 panel; lossy recorded RGB, no generative modification.',
       pixel_goal_sha256=meta['goal_sha256'],reference_pose_hash_equal=True,initial_map_equals_final_map=True,
       height_range_m=float(np.ptp(pos[:,1])),coverage_mpp=.1,coverage_radius_m=3,coverage_fov_deg=90,
       coverage='Saved XZ fog-of-war proxy at original resolution; initial view excluded from curve and shown dark blue.',
       initial_area_m2=float(np.count_nonzero(d['initial_seen'])*.01),final_new_area_m2=float(area[-1]),
       path_length_m=float(dist.sum()),area_after_250_m2=float(area[-1]-area[250]),path_after_250_m=float(dist[250:].sum()),
       final_goal_distance_m=float(metrics[-1,0]),interpretation='Purposefully selected behavior evidence, not population prevalence or a causal claim about reward.',
       source_trace=str(path),source_video=str(video))
    write_json(out/'metadata.json',selected);results.append(selected);print('Failure exported',scene,ep,flush=True)

# E2 case: true second-trigger choice changes the matched rule's executed direction.
base=ROOT/'logs/qwen_six_ablation_20261108/runtime_e9396ac';folder=base/'full_E2'
rule=ROOT/'logs/qwen_recovery_iteration_20261108/expanded_v2/expanded03_full/full_rule'
out=OUT/'recovery/E2_Swormville_3216';out.mkdir(parents=True,exist_ok=True)
eventpath=source(folder/'native/recovery/events.jsonl')
events=[json.loads(l) for l in eventpath.open()];e=next(x for x in events if x['id']=='event_0000101')
rule_events=[json.loads(l) for l in source(rule/'native/recovery/events.jsonl').open()]
re=next(x for x in rule_events if x['episode']==e['episode'] and x.get('decision_step')==e['decision_step'])
assert e['model']['semantic_choice']=='left' and e['model']['differs_from_rule'] and re['choice']=='B'
poses={};commands={};episodes={}
for name,folder in [('E2',folder),('rule',rule)]:
    trace=source(folder/'audit_traces/Swormville_3216.npz')
    with np.load(trace) as f:poses[name]=f['poses'];commands[name]=f['commands']
    rows=[]
    for f in sorted((folder/'episodes').glob('*.jsonl')):
        for line in f.open():
            row=json.loads(line)
            if row['scene_id']==e['episode'][0] and row['episode_id']=='3216':episodes[name]=row;source(f)
    assert hashlib.sha256(commands[name].astype(np.float32).tobytes()).hexdigest()==episodes[name]['actual_actions_sha256']
    assert hashlib.sha256(poses[name][1:].astype(np.float32).tobytes()).hexdigest()==episodes[name]['pose_trace_sha256']
    for s,xyz in enumerate(poses[name]):
        row=dict(step=s,x=float(xyz[0]),y=float(xyz[1]),z=float(xyz[2]),qx=float(xyz[3]),qy=float(xyz[4]),qz=float(xyz[5]),qw=float(xyz[6]))
        if s:row.update(linear_velocity_mps=float((commands[name][s-1,0]+1)*.125),angular_velocity_degps=float(commands[name][s-1,1]*15))
        else:row.update(linear_velocity_mps='',angular_velocity_degps='')
        rows.append(row)
    csv_write(out/(name+'_actual_trajectory_actions.csv'),rows)
decision=e['decision_step'];trigger=e['step'];finish=decision+len(e['planned_actions'])
assert np.array_equal(commands['E2'][:decision],commands['rule'][:decision])
assert np.array_equal(poses['E2'][:decision+1],poses['rule'][:decision+1])
assert np.array_equal(commands['E2'][decision:finish],np.asarray(e['planned_actions'],dtype=np.float32))
assert not np.array_equal(commands['E2'][decision],commands['rule'][decision])
assert episodes['E2']['success']==1 and episodes['rule']['success']==0
ims=[]
for item in e['request']['images']:
    path=source(Path(item['image']));assert sources[str(path)]['sha256']==item['image_sha256'];role=item['role']
    shutil.copyfile(path,out/(role+'.png'));ims.append((role,np.asarray(Image.open(path))))
    ref_role={'CURRENT':'forward','LEFT':'left','RIGHT':'right'}[role]
    assert e['view_files'][ref_role]['sha256']==re['view_files'][ref_role]['sha256']
assert [x[0] for x in ims]==['CURRENT','LEFT','RIGHT']
goal=source(Path(e['view_files']['goal']['path']));shutil.copyfile(goal,out/'goal_for_reader_only.png')
raw=e['model']['raw'];prob=np.asarray(raw['probabilities']);logits=np.asarray(raw['logits']);soft=np.exp(logits-logits.max());soft/=soft.sum();assert np.allclose(prob,soft,atol=1e-7)
outcomes=[json.loads(l) for l in source(base/'full_E2/native/recovery/outcomes.jsonl').open() if json.loads(l)['id']==e['id']]
mapfile=source(DIAG/'traces/Swormville/3216.npz')
with np.load(mapfile) as f:md={k:f[k] for k in f.files if k in ['initial_grid','map_bounds_xyz']}

def recovery_map(ax):
    background(ax,md,False)
    for name,col in [('rule','#bf6a62'),('E2','#188878')]:
        xy=poses[name][:,[0,2]];ax.plot(xy[:,0],xy[:,1],color=col,lw=1.6,label=name+(' (success)' if name=='E2' else ' (failed)'))
    xy=poses['E2'][:,[0,2]]
    ax.scatter(*xy[decision],s=75,c='#efaa35',edgecolor='black',marker='D',label=f'Choice at {decision}',zorder=5)
    ax.scatter(*xy[finish],s=60,c='#188878',marker='o',edgecolor='white',label=f'Recovery ends {finish}',zorder=5)
    ax.scatter(*xy[-1],s=75,c='#188878',marker='*',edgecolor='black',label=f'E2 STOP {len(xy)-1}',zorder=5)
    ax.legend(fontsize=8,loc='best');ax.set_title('Same executed prefix; different recovery direction',fontsize=12)

def behavior(ax):
    for name,col in [('rule','#bf6a62'),('E2','#188878')]:
        q=poses[name][:,:3];start=max(0,trigger-20);end=min(len(q),finish+70)
        ax.plot(np.arange(start,end),np.linalg.norm(q[start:end]-q[decision],axis=1),c=col,lw=2,label=name)
    ax.axvspan(trigger,decision,alpha=.12,color='#7b647b',label='Real scan (24 actions)')
    ax.axvspan(decision,finish,alpha=.15,color='#188878',label='Recovery (6 turn + 8 forward)')
    ax.set(xlabel='Executed action step',ylabel='Distance from choice position (m)',title='Recorded motion before and after recovery')
    ax.grid(alpha=.18);ax.legend(fontsize=8)

fig=plt.figure(figsize=(16,9),constrained_layout=True);grid=fig.add_gridspec(2,4,height_ratios=[1,1.35])
for i,(role,im) in enumerate(ims):
    ax=fig.add_subplot(grid[0,i]);ax.imshow(im,interpolation='nearest');ax.axis('off');step=e['view_steps'][{'CURRENT':'forward','LEFT':'left','RIGHT':'right'}[role]]
    ax.set_title(f'{role} | observed step {step}',fontsize=12)
ax=fig.add_subplot(grid[0,3]);bars=ax.bar(['LEFT','RIGHT','KEEP'],prob*100,color=['#188878','#92a0b3','#92a0b3']);ax.set(ylim=(0,100),ylabel='Candidate probability (%)',title='Qwen3.5-2B chooses LEFT')
for bar,pv in zip(bars,prob):ax.text(bar.get_x()+bar.get_width()/2,bar.get_height()+2,f'{pv*100:.2f}%',ha='center',fontsize=11)
recovery_map(fig.add_subplot(grid[1,:2]));behavior(fig.add_subplot(grid[1,2:]))
fig.suptitle('E2 | Swormville / episode 3216 | second recovery event',fontsize=19)
fig.text(.5, -.025, 'CURRENT / LEFT / RIGHT are actual model inputs; no GOAL input. Motion is recorded GT for post-hoc visualization only.',fontsize=10,ha='center')
save(fig,out/'E2_recovery_overview')
fig,axs=plt.subplots(1,4,figsize=(16,4.5),constrained_layout=True)
for ax,(role,im) in zip(axs,ims):
    ax.imshow(im,interpolation='nearest');ax.axis('off');ax.set_title(role,fontsize=15)
bars=axs[3].bar(['LEFT','RIGHT','KEEP'],prob*100,color=['#188878','#92a0b3','#92a0b3'])
axs[3].set(ylim=(0,100),ylabel='Candidate probability (%)',title='Selected: LEFT')
for bar,pv in zip(bars,prob):axs[3].text(bar.get_x()+bar.get_width()/2,bar.get_height()+2,f'{pv*100:.2f}%',ha='center')
fig.suptitle('E2: actual Qwen inputs and first-token probabilities | Swormville / 3216',fontsize=16)
save(fig,out/'E2_inputs_probabilities')
fig,ax=plt.subplots(figsize=(9,5),constrained_layout=True);recovery_map(ax);save(fig,out/'paired_trajectory')
fig,ax=plt.subplots(figsize=(9,4.5),constrained_layout=True);behavior(ax);save(fig,out/'before_after_motion')
fig,axs=plt.subplots(2,1,figsize=(9,5.6),sharex=True,constrained_layout=True)
cmd=commands['E2'][decision:finish];xs=np.arange(decision+1,finish+1)
axs[0].step(xs,(cmd[:,0]+1)*.125,where='mid',color='#188878',lw=2);axs[0].set(ylabel='Linear velocity (m/s)',ylim=(-.02,.27))
axs[1].step(xs,cmd[:,1]*15,where='mid',color='#2463a2',lw=2);axs[1].set(ylabel='Angular velocity (deg/s)',xlabel='Executed action step',ylim=(-2,17))
for ax in axs:
    ax.axvspan(decision+.5,decision+6.5,color='#2463a2',alpha=.10);ax.axvspan(decision+6.5,finish+.5,color='#188878',alpha=.10);ax.grid(alpha=.18)
fig.suptitle('Actual recovery: 6 left-turn actions, then 8 forward actions',fontsize=15)
fig.text(.5,-.025,'1 second/action; +15 deg/s turn, then 0.20 m/s forward. Commands are not measured displacement.',ha='center',fontsize=9)
save(fig,out/'actual_recovery_commands')
action_rows=[]
for k in range(trigger,finish):
    a=commands['E2'][k];phase='scan' if k<decision else 'recovery_turn' if k<decision+6 else 'recovery_forward'
    action_rows.append(dict(action_index_zero_based=k,observation_before=k,observation_after=k+1,phase=phase,
                       normalized_linear=float(a[0]),normalized_angular=float(a[1]),linear_velocity_mps=float((a[0]+1)*.125),angular_velocity_degps=float(a[1]*15),time_step_s=1.))
csv_write(out/'actual_intervention_actions.csv',action_rows)
csv_write(out/'candidate_probabilities.csv',[dict(label=label,logit=float(l),probability=float(pv)) for label,l,pv in zip(raw['labels'],logits,prob)])
write_json(out/'original_E2_event.json',e);write_json(out/'original_rule_event.json',re);write_json(out/'recorded_outcomes.json',outcomes)
meta=dict(scene_id=e['episode'][0],episode_id='3216',event=e['id'],trigger_observation_step=trigger,decision_observation_step=decision,recovery_end_step=finish,
          model='Qwen3.5-2B FP32',model_input_roles=['CURRENT','LEFT','RIGHT'],goal_image_used_by_model=False,
          goal_image='goal_for_reader_only.png is navigation target context, NOT part of E2 model request.',
          probabilities=raw,actual_choice='LEFT',matched_rule_choice='RIGHT',same_action_pose_prefix=True,same_candidate_images=True,
          results=episodes,post_recovery_rgb_available=False,
          limitation='No continuous post-recovery RGB was saved for E2; post-action behavior uses original poses/actions and scalar RGB-change outcome. No resimulation or substituted frames.',
          conclusion='One selected paired rescue with a real model action change. It does not establish a population-level advantage or explain the model intent.',
          units='Commands are linear m/s and angular deg/s, time_step=1s; commanded motion is distinct from measured displacement.',
          source_commit='e9396ac0c989ea515edcbd7f8d0085be38f818e7',checkpoint_steps=125952000)
write_json(out/'metadata.json',meta)
write_json(OUT/'case_manifest.json',dict(failures=results,recovery=meta,sources=sources,mode='CPU-only export of existing observations, no navigation/Qwen inference or PBS submission'))
print('E2 exported',out,flush=True)
