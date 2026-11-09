"""Render actual recorded CSV/NPZ into white-background, NUS-colour figures."""
import argparse
import csv
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from PIL import Image

BLUE='#003D7C'; ORANGE='#EF7C00'
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':11,'pdf.fonttype':42,
                     'axes.spines.top':False,'axes.spines.right':False,'savefig.facecolor':'white'})

def read_csv(path):
    with path.open() as f: rows=list(csv.DictReader(f))
    return {k:np.array([float(r[k]) if r[k] else np.nan for r in rows])
            for k in ['step','x','y','z','cumulative_new_area_m2','path_length_m']}

def plot(case):
    verification=json.loads((case/'pair_verification.json').read_text());assert verification['passed']
    rec=[]
    for name,color,title in [('public',BLUE,'Public SIGN'),('coverage',ORANGE,'SIGN + Coverage Reward')]:
        folder=case/name
        rec.append((json.loads((folder/'summary.json').read_text()),read_csv(folder/'steps.csv'),
                    np.load(folder/'map.npz'),color,title))
    b=rec[0][2]['bounds']; zmin,xmin=b[0,2],b[0,0]; zmax,xmax=b[1,2],b[1,0]
    assert np.array_equal(rec[0][2]['bounds'],rec[1][2]['bounds'])
    assert rec[0][2]['grid'].shape==rec[1][2]['grid'].shape
    shape=rec[0][2]['grid'].shape
    occupied=(rec[0][2]['valid_union'] | rec[1][2]['valid_union'])
    rr,cc=np.where(occupied)
    goal=np.asarray(rec[0][0]['episode']['goals'][0]['position'])
    xlo=min(xmin+cc.min()/shape[1]*(xmax-xmin),goal[0])-.5
    xhi=max(xmin+(cc.max()+1)/shape[1]*(xmax-xmin),goal[0])+.5
    zlo=min(zmin+rr.min()/shape[0]*(zmax-zmin),goal[2])-.5
    zhi=max(zmin+(rr.max()+1)/shape[0]*(zmax-zmin),goal[2])+.5
    fig=plt.figure(figsize=(13.33,8),facecolor='white')
    gs=fig.add_gridspec(2,2,height_ratios=[3.3,1.25],left=.065,right=.975,bottom=.16,top=.85,hspace=.43,wspace=.13)
    fig.suptitle(f"{rec[0][0]['scene']}  |  Episode {rec[0][0]['episode_id']}",x=.065,y=.975,ha='left',fontsize=21,fontweight='bold',color=BLUE)
    fig.text(.065,.925,'Matched start, heading and goal image  ·  Deterministic policy  ·  Recovery off  ·  500-step limit',fontsize=11,color='#555555')
    for col,(s,t,m,color,title) in enumerate(rec):
        ax=fig.add_subplot(gs[0,col]);rgb=np.ones((*shape,3))
        rgb[m['valid_union']]=[.89,.9,.91]
        tint=matplotlib.colors.to_rgb(color)
        rgb[m['seen']>0]=np.array(tint)*.28+.72
        rgb[m['initial_seen']>0]=np.array(tint)*.55+.45
        ax.imshow(rgb,extent=[xmin,xmax,zmax,zmin],origin='upper',interpolation='nearest')
        ax.plot(t['x'],t['z'],color=color,lw=1.5,alpha=.95)
        ax.scatter(t['x'][0],t['z'][0],s=75,marker='o',c='#30936E',edgecolor='white',zorder=5)
        ax.scatter(goal[0],goal[2],s=190,marker='*',c='#222222',edgecolor='white',zorder=6)
        ax.scatter(t['x'][-1],t['z'][-1],s=85,marker='X',c=color,edgecolor='white',zorder=7)
        ax.set(xlim=(xlo,xhi),ylim=(zhi,zlo),xlabel='World X (m)',ylabel='World Z (m)')
        ax.set_aspect('equal',adjustable='box')
        ax.set_title(title,color=color,fontsize=16,fontweight='bold',pad=30)
        ax.text(.5,1.025,f"Success {int(s['success'])}    Steps {s['steps']}    SPL {s['spl']:.3f}",transform=ax.transAxes,ha='center',fontsize=11)
        ax.tick_params(labelsize=9)
    ax=fig.add_subplot(gs[1,:])
    for s,t,m,color,title in rec:
        ax.plot(t['step'],t['cumulative_new_area_m2'],color=color,lw=2.3,label=title)
        ax.scatter(t['step'][-1],t['cumulative_new_area_m2'][-1],color=color,s=28,zorder=4)
    ax.set(xlim=(0,500),ylim=(0,None),xlabel='Environment steps',ylabel='New observed area (m²)')
    ax.grid(axis='y',alpha=.2);ax.legend(loc='lower right',frameon=False,fontsize=10)
    handles=[Line2D([],[],marker='o',ls='',color='#30936E',label='Start'),
             Line2D([],[],marker='*',ls='',color='#222222',markersize=11,label='Goal'),
             Line2D([],[],marker='X',ls='',color=BLUE,label='End'),
             Line2D([],[],marker='s',ls='',color='#BCCDDD',markersize=10,label='Observed area (tinted)')]
    fig.legend(handles=handles,loc='lower center',bbox_to_anchor=(.5,.035),ncol=4,frameon=False,fontsize=10)
    fig.text(.065,.012,'Coverage: 0.1 m grid, 3 m / 90° XZ visibility proxy; initial view excluded. Maps are for analysis only. Single-case evidence.',fontsize=9,color='#666666')
    for ext in ['png','pdf']:fig.savefig(case/f'paired_comparison.{ext}',dpi=220)
    plt.close(fig)
    # Reader can inspect the shared goal and real initial/terminal observations separately.
    fig,axes=plt.subplots(1,5,figsize=(13.33,3.1))
    items=[(case/'public/goal.png','Shared goal'),(case/'public/rgb_000.png','Shared start'),
           (case/'public'/f"rgb_{rec[0][0]['steps']:03d}.png",'Public SIGN: terminal'),
           (case/'coverage/rgb_100.png','Coverage: step 100'),
           (case/'coverage'/f"rgb_{rec[1][0]['steps']:03d}.png",'Coverage: terminal')]
    for ax,(p,title) in zip(axes,items):
        if not p.exists():p=case/'coverage/rgb_000.png';title='Coverage: start'
        ax.imshow(Image.open(p));ax.set_title(title,fontsize=11,color=BLUE);ax.axis('off')
    fig.suptitle(f"{rec[0][0]['scene']} / {rec[0][0]['episode_id']} — recorded RGB observations",color=BLUE,fontsize=16)
    fig.tight_layout()
    for ext in ['png','pdf']:fig.savefig(case/f'rgb_keyframes.{ext}',dpi=200)
    plt.close(fig)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('cases',nargs='*',type=Path);a=p.parse_args()
    for case in a.cases or sorted(Path(__file__).parent.glob('*_*')):
        if (case/'pair_verification.json').exists():plot(case)
