import json,csv,hashlib,zipfile
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from matplotlib.lines import Line2D
HERE=Path(__file__).resolve().parent
rows=[]
for group in sorted(HERE.glob('group_*')):
 cases=sorted(group.glob('C*/trajectory.json'))
 assert len(cases)==8
 data=[]
 for path in cases:
  t=json.loads(path.read_text());m=np.load(path.parent/'display_map_data.npz');mpp=float(m['mpp']);t['mpp']=mpp
  for point,rc in zip(t['poses'],m['coords']):point['map_row'],point['map_col']=map(int,rc)
  valid=m['valid_union'].astype(bool);initial=m['initial_seen'].astype(bool)&valid;seen=m['seen'].astype(bool)&valid;new=seen&~initial
  assert valid.any() and np.isfinite([p['position_xyz'] for p in t['poses']]).all()
  row=dict(group=group.name,candidate=path.parent.name,scene=Path(t['scene_id']).stem,steps=t['window_steps'],floor_m2=valid.sum()*mpp*mpp,covered_m2=seen.sum()*mpp*mpp,new_m2=new.sum()*mpp*mpp,covered_percent=100*seen.sum()/valid.sum(),new_percent=100*new.sum()/valid.sum(),grid_changed_steps=t['grid_changed_steps'])
  rows.append(row)
  rgb=np.ones((*valid.shape,3));rgb[valid]=[.83,.84,.85];rgb[initial]=[.61,.70,.78];rgb[new]=[.65,.84,.92]
  data.append((path.parent,t,row,rgb,valid))
 
 def panel(ax,d):
  case,t,r,rgb,valid=d;ys,xs=np.where(valid);bounds=(xs.min()-8,xs.max()+8,ys.max()+100,ys.min()-8);pts=t['poses'];x=[p['map_col'] for p in pts];y=[p['map_row'] for p in pts]
  ax.imshow(rgb,interpolation='nearest');ax.plot(x,y,c='#b82b35',lw=1.5)
  ax.scatter(x[0],y[0],s=50,c='#149253',edgecolors='white',zorder=4);ax.scatter(x[-1],y[-1],s=50,c='#222c41',marker='X',zorder=5)
  ax.set_xlim(bounds[:2]);ax.set_ylim(bounds[2:]);ax.set_aspect('equal');ax.axis('off')
  ax.set_title(f"{r['scene']} / task {t['episode_id']} / {case.name} | {r['steps']} actions\nCovered {r['covered_percent']:.1f}% | New {r['new_percent']:.1f}%",fontsize=12)
  xx=bounds[0]+5;yy=bounds[2]-5;ax.plot([xx,xx+2/t['mpp']],[yy,yy],c='black',lw=3);ax.text(xx+1/t['mpp'],yy-3,'2 m',ha='center',fontsize=9)
 legend=[Patch(color=c,label=l) for c,l in [('#d4d6d9','Navigable floor'),('#9cb3c7','Initial coverage'),('#a6d6eb','New coverage')]]+[Line2D([0],[0],color='#b82b35',label='Path'),Line2D([0],[0],marker='o',color='w',markerfacecolor='#149253',label='Start'),Line2D([0],[0],marker='X',color='w',markerfacecolor='#222c41',label='End')]
 for d in data:
  fig,ax=plt.subplots(figsize=(10,8));panel(ax,d);fig.legend(handles=legend,loc='lower center',ncol=3);fig.subplots_adjust(bottom=.12);fig.savefig(d[0]/'topdown_static.png',dpi=140);plt.close(fig)
 fig,axs=plt.subplots(2,4,figsize=(20,12))
 for ax,d in zip(axs.flat,data):panel(ax,d)
 fig.suptitle(f"Gibson | eight different scenes and tasks | independent trajectories",fontsize=16)
 fig.legend(handles=legend,loc='lower center',ncol=6);fig.tight_layout(rect=(0,.05,1,.95));fig.savefig(group/'overview_static.png',dpi=120);plt.close(fig)
with (HERE/'coverage.csv').open('w') as f:
 writer=csv.DictWriter(f,fieldnames=rows[0]);writer.writeheader();writer.writerows(rows)
(HERE/'render_manifest.json').write_text(json.dumps({'coverage_definition':'seen valid XZ grid cells / navigable union; total includes initial view; new excludes initial view; 0.025m display grid with <=5cm fog-origin boundary correction; raw 0.1m masks preserved, 3m radius, 90deg FOV; proxy not RGB surface area','rows':rows,'images':{str(p.relative_to(HERE)):hashlib.sha256(p.read_bytes()).hexdigest() for p in HERE.glob('group_*/**/*static.png')}},indent=2))
print('Rendered',len(rows),'diverse trajectories')
