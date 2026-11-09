"""CPU-only TensorBoard export. No model, simulator, or PBS imports."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from tensorboard.backend.event_processing.event_file_loader import RawEventFileLoader
from tensorboard.compat.proto.event_pb2 import Event

p=argparse.ArgumentParser();p.add_argument('--workspace',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
out=a.out/'training';out.mkdir(parents=True,exist_ok=True)
plan=json.loads((a.workspace/'logs/training_continuation_20261103/plan.json').read_text())['coverage256']
paths={'original':Path(plan['old_output'])/'tb','continuation':a.workspace/'SIGN-continue-coverage256/results/continuation_20261103/coverage256/train/tb'}
tags={'metrics/success':'sr','metrics/spl':'spl','reward':'navigation_reward'}
data={};sources=[]
for phase,folder in paths.items():
    values={};duplicates=0
    for f in sorted(folder.glob('events.out.tfevents.*')):
        print('Reading',phase,f.name,flush=True)
        digest=hashlib.sha256()
        with f.open('rb') as stream:
            for block in iter(lambda:stream.read(1024*1024),b''):digest.update(block)
        sources.append(dict(path=str(f),sha256=digest.hexdigest(),bytes=f.stat().st_size,phase=phase))
        for raw in RawEventFileLoader(str(f)).Load():
            ev=Event.FromString(raw)
            for v in ev.summary.value:
                if v.tag not in tags:continue
                assert v.HasField('simple_value'),(v.tag,'Unexpected tensor scalar encoding')
                key=(int(ev.step),tags[v.tag]);duplicates+=key in values
                values[key]=(float(v.simple_value),float(ev.wall_time))
    steps=sorted({k[0] for k in values});rows=[]
    for step in steps:
        assert all((step,t) in values for t in tags.values()),(phase,step)
        row=dict(phase=phase,step=step,wall_time_unix=values[(step,'sr')][1])
        row.update({t:values[(step,t)][0] for t in tags.values()});rows.append(row)
    assert all(np.isfinite([r[t] for t in tags.values()]).all() for r in rows)
    assert all(0<=r['sr']<=1 and 0<=r['spl']<=1 for r in rows)
    data[phase]=rows
    print(phase,'rows',len(rows),'first',steps[0],'last',steps[-1],'duplicate tag/steps',duplicates,flush=True)
with (out/'coverage256_training_raw.csv').open('w') as f:
    w=csv.DictWriter(f,fieldnames=list(data['original'][0]));w.writeheader()
    for rows in data.values():w.writerows(rows)

boundary=plan['start_step'];window=250
plot_data={}
for phase,rows in data.items():
    kept=[r for r in rows if phase!='original' or r['step']<=boundary]
    plot_data[phase]=kept
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':12,'axes.spines.top':False,'axes.spines.right':False,'pdf.fonttype':42,'svg.fonttype':'none'})
colors={'original':'#2463a2','continuation':'#188878'}
labels={'original':'Original training','continuation':'Weights continuation'}
def draw(ax,tag,title,ylabel):
    for phase,rows in plot_data.items():
        x=np.asarray([r['step'] for r in rows])/1e6;y=np.asarray([r[tag] for r in rows]);y=y*(100 if tag in ('sr','spl') else 1)
        n=np.arange(1,len(y)+1);cs=np.r_[0,np.cumsum(y)];start=np.maximum(0,n-window);sm=(cs[n]-cs[start])/(n-start)
        ax.plot(x[::10],y[::10],c=colors[phase],alpha=.16,lw=.55,rasterized=True)
        ax.plot(x,sm,c=colors[phase],lw=1.8,label=labels[phase])
    ax.axvline(boundary/1e6,color='#7b647b',ls='--',lw=1)
    ax.set(title=title,xlabel='Training environment steps (million)',ylabel=ylabel)
    ax.set_xlim(0,max(data['continuation'][-1]['step'],boundary)/1e6);ax.grid(alpha=.18)
    if tag in ('sr','spl'):ax.set_ylim(0,100)

fig,axes=plt.subplots(1,3,figsize=(16,4.9),constrained_layout=True)
for ax,tag,title,ylabel in zip(axes,['sr','spl','navigation_reward'],['Training success rate','Training SPL','Training navigation reward'],['Success rate (%)','SPL (%)','Mean episode reward']):draw(ax,tag,title,ylabel)
axes[0].legend(loc='lower right',fontsize=10);fig.suptitle('Coverage256 | Gibson training curves',fontsize=19)
fig.text(.5, -.025, 'Native rolling episode statistics; bold: 250-log-point trailing mean. Dashed line: continuation from 125.952M.',fontsize=10,ha='center')
for ext in ['png','pdf','svg']:fig.savefig(out/('coverage256_training_curves.'+ext),dpi=200,bbox_inches='tight',facecolor='white')
plt.close(fig)
for tag,title,ylabel in [('sr','Training success rate','Success rate (%)'),('spl','Training SPL','SPL (%)'),('navigation_reward','Training navigation reward','Mean episode reward')]:
    fig,ax=plt.subplots(figsize=(9,5),constrained_layout=True);draw(ax,tag,title,ylabel);ax.legend(fontsize=10)
    fig.text(.5, -.025, 'Coverage256 | training data, not validation | continuation boundary shown',fontsize=9,ha='center')
    for ext in ['png','pdf']:fig.savefig(out/(tag+'.'+ext),dpi=200,bbox_inches='tight',facecolor='white')
    plt.close(fig)
meta=dict(method='Coverage256',native_reward_window_updates=50,ppo_rollout=256,num_envs=8,extra_plot_smoothing_logs=window,
          steps_per_update=2048,smoothing_environment_steps=window*2048,continuation_step=boundary,
          continuation='Weights only; optimizer and episodes restarted. Lines do not bridge restart.',
          reward='Original environment navigation reward; excludes coverage bonus.',
          raw_csv='All points and both phases; original post-checkpoint tail retained, but omitted from the continued main plot.',
          metric_scope='Rolling completed training episodes, not validation SR/SPL and not a fixed training-set evaluation.',
          sources=sources,phases={k:dict(points=len(v),first_step=v[0]['step'],last_step=v[-1]['step'],last_record=v[-1]) for k,v in data.items()})
(out/'metadata.json').write_text(json.dumps(meta,indent=2)+'\n')
print('Training figures saved',out,flush=True)
