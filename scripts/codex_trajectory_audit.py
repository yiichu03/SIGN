#!/usr/bin/env python3
"""Evidence sheets and arithmetic for manual AI review; never assigns labels."""
import argparse
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
from PIL import Image

BASE=Path(__file__).resolve().parents[1]
OUT=BASE/'results/qwen_diagnostic/codex_audit'

def load(folder):
    p=folder/'waypoints_corrected.json'
    if not p.exists():p=folder/'waypoints.json'
    d=json.loads(p.read_text());w=d['waypoints']
    xy=np.array([[r['map_col'],r['map_row']] for r in w],float)
    h=np.rad2deg(np.unwrap([r['heading_rad'] for r in w]))
    c=np.array([r['collision'] for r in w],bool)
    return d,xy,h,c

def stats(folder):
    d,xy,h,c=load(folder);rows=[]
    for a in range(0,len(xy),50):
        z=xy[a:a+50];v=h[a:a+50]
        rows.append(dict(steps=[a+1,min(a+50,len(xy))],start=z[0].astype(int).tolist(),end=z[-1].astype(int).tolist(),bbox_span=np.ptp(z,axis=0).astype(int).tolist(),heading_span_deg=round(float(np.ptp(v)),1),heading_net_deg=round(float(v[-1]-v[0]),1),collisions=int(c[a:a+50].sum())))
    return dict(case=str(folder.relative_to(BASE/'results/qwen_diagnostic')),steps=len(xy),collisions=int(c.sum()),distinct_pixels=len(set(map(tuple,xy))),windows=rows)

def sheet(folders,target):
    fig=plt.figure(figsize=(14,3.15*len(folders)),dpi=110)
    outer=fig.add_gridspec(len(folders),3,width_ratios=[1.12,1,1.9],hspace=.31,wspace=.19)
    for i,folder in enumerate(folders):
        d,xy,h,c=load(folder);n=len(xy);t=np.arange(1,n+1)
        ax=fig.add_subplot(outer[i,0]);segments=np.stack([xy[:-1],xy[1:]],axis=1)
        lc=LineCollection(segments,cmap='turbo',norm=plt.Normalize(0,n),linewidths=1.6);lc.set_array(t[1:]);ax.add_collection(lc)
        ax.scatter(*xy[0],c='black',s=16);ax.scatter(*xy[-1],facecolors='white',edgecolors='black',marker='s',s=30,zorder=5)
        for j in sorted(set([0,n-1]+list(range(24,n,25)))):
            ax.annotate(str(j+1),xy[j],fontsize=7,xytext=(2,2),textcoords='offset points',color='black')
        span=max(np.ptp(xy,axis=0).max(),10);mid=(xy.max(0)+xy.min(0))/2
        ax.set(xlim=(mid[0]-.57*span,mid[0]+.57*span),ylim=(mid[1]+.57*span,mid[1]-.57*span),aspect='equal')
        ax.tick_params(labelsize=6);ax.set_title(folder.parent.name+'/'+folder.name+'\n'+f'{n} steps | {c.sum()} collisions',fontsize=10)
        inner=outer[i,1].subgridspec(2,1,hspace=.35)
        a=fig.add_subplot(inner[0]);a.plot(t,xy[:,0]-xy[0,0],label='col',lw=1);a.plot(t,xy[:,1]-xy[0,1],label='row',lw=1);a.legend(fontsize=6,loc='upper left');a.set_title('Position vs step (pixels)',fontsize=8);a.tick_params(labelsize=6)
        a=fig.add_subplot(inner[1]);a.plot(t,h-h[0],lw=1);a.scatter(t[c],(h-h[0])[c],s=2,c='red');a.set_title('Unwrapped heading (deg), red=collision',fontsize=8);a.tick_params(labelsize=6)
        frames=sorted((folder/'rgb').glob('*.png'));chosen=[]
        if (folder/'goal.png').exists():chosen=[folder/'goal.png']
        chosen += [frames[j] for j in sorted(set(np.linspace(0,len(frames)-1,min(5,len(frames))).round().astype(int)))] if frames else []
        rgb=outer[i,2].subgridspec(2,3,hspace=.20,wspace=.04)
        for j,p in enumerate(chosen):
            a=fig.add_subplot(rgb[j//3,j%3]);a.imshow(Image.open(p));a.set_title(p.stem,fontsize=8);a.axis('off')
        if not chosen:
            a=fig.add_subplot(rgb[:,:]);a.imshow(Image.open(folder/'trajectory2.png'));a.axis('off')
    fig.subplots_adjust(top=.95,bottom=.035,left=.045,right=.99)
    target.parent.mkdir(parents=True,exist_ok=True);fig.savefig(target);plt.close(fig)

def rgb_sheet(folder,target):
    frames=([folder/'goal.png'] if (folder/'goal.png').exists() else [])+sorted((folder/'rgb').glob('*.png'))
    if not frames:return
    cols=6;rows=(len(frames)+cols-1)//cols
    fig,axes=plt.subplots(rows,cols,figsize=(13,2.2*rows),dpi=110,squeeze=False)
    for a in axes.flat:a.axis('off')
    for a,p in zip(axes.flat,frames):a.imshow(Image.open(p));a.set_title(p.stem,fontsize=9)
    fig.suptitle(folder.parent.name+'/'+folder.name,fontsize=13);fig.tight_layout();fig.savefig(target);plt.close(fig)

def main():
    p=argparse.ArgumentParser();p.add_argument('root',type=Path);p.add_argument('--tag',required=True);a=p.parse_args()
    a.root=a.root.resolve()
    folders=sorted(a.root.glob('val_*/episode_*')) if (a.root/'val_easy').exists() else sorted(f for f in a.root.glob('group_*/episode_*') if (f.parent/'collection_verified.json').exists())
    target=OUT/a.tag;target.mkdir(parents=True,exist_ok=True)
    rows=[]
    for k in range(0,len(folders),4):
        group=folders[k:k+4]
        page=target/f'page_{k//4+1:02d}.png'
        if not page.exists():sheet(group,page)
        for folder in group:
            r=stats(folder);r['page']=k//4+1;rows.append(r)
            rgb=target/(folder.parent.name+'_'+folder.name+'_rgb.png')
            if not rgb.exists():rgb_sheet(folder,rgb)
    (target/'evidence.json').write_text(json.dumps(rows,indent=2)+'\n')
    print(f'{len(rows)} evidence records, {len(rows)//4} sheets',flush=True)

if __name__=='__main__':main()
