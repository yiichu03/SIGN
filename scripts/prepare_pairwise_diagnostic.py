#!/usr/bin/env python3
"""Prepare evidence and blind human review for the small relative-search pilot."""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
import numpy as np
from PIL import Image, ImageDraw, ImageFont

BASE = Path(__file__).resolve().parents[1]
SOURCE = BASE / 'results/qwen_diagnostic/group8_p12'
ROOT = BASE / 'results/qwen_diagnostic/pairwise_pilot_20261013'
# Development cases, deliberately covering known questions. No expected answers.
PAIRS = [(3,8,1),(3,4,2),(3,7,5),(3,4,8),
         (6,8,1),(6,5,4),(6,6,2),(6,3,8),
         (5,1,4),(5,4,7),(5,3,6),(5,2,5),
         (10,1,2),(10,1,5),(10,2,7),(10,3,6),(10,4,8),(10,5,6),
         (2,5,4),(2,1,8),(2,7,3),(1,1,4),(4,3,7),(8,1,5)]
SWAPS = [1,3,6,9,13,17,20,24]

def dump(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2)+'\n')

def arrays(payload):
    w=payload['waypoints']
    return (np.array([[p['map_col'],p['map_row']] for p in w],float),
            np.unwrap([p['heading_rad'] for p in w]),
            np.array([p['collision'] for p in w],bool))

def evidence(payload):
    xy,h,c=arrays(payload); windows=[]; candidates=[]
    for a in range(0,len(xy),25):
        b=min(a+25,len(xy));z=xy[a:b];v=np.rad2deg(h[a:b])
        windows.append(dict(id=f'W{len(windows)+1:02d}',steps=[a+1,b],
            start_col_row=z[0].tolist(),end_col_row=z[-1].tolist(),
            col_range=[float(z[:,0].min()),float(z[:,0].max())],
            row_range=[float(z[:,1].min()),float(z[:,1].max())],
            path_length_pixels=round(float(np.linalg.norm(np.diff(z,axis=0),axis=1).sum()),2),
            displacement_pixels=round(float(np.linalg.norm(z[-1]-z[0])),2),
            heading_unwrapped_range_degrees=[round(float(v.min()),2),round(float(v.max()),2)],
            heading_net_degrees=round(float(v[-1]-v[0]),2),
            heading_total_variation_degrees=round(float(np.abs(np.diff(v)).sum()),2),
            collision_records=int(c[a:b].sum()),records=b-a))
    # One best geometrical match for each later window; never labels redundancy.
    for j in range(2,len(windows)):
        a2,b2=windows[j]['steps'];z2=xy[a2-1:b2];options=[]
        for i in range(j-1):
            a1,b1=windows[i]['steps'];z1=xy[a1-1:b1]
            distance=np.linalg.norm(z2[:,None,:]-z1[None,:,:],axis=2)
            near2=distance.min(axis=1)<=8;near1=distance.min(axis=0)<=8
            if max(near1.mean(),near2.mean())<.5:continue
            score=float((near1.mean()+near2.mean())/2)
            nearest=distance.argmin(axis=1)
            angle=np.abs(np.arctan2(np.sin(h[a2-1:b2]-h[a1-1:b1][nearest]),
                                    np.cos(h[a2-1:b2]-h[a1-1:b1][nearest])))
            between=xy[b1:a2-1]
            away=np.linalg.norm(between[:,None,:]-z1[None,:,:],axis=2).min(axis=1)
            item=dict(earlier_window=windows[i]['id'],later_window=windows[j]['id'],
                earlier_steps=[a1,b1],later_steps=[a2,b2],
                earlier_fraction_near_later=round(float(near1.mean()),3),
                later_fraction_near_earlier=round(float(near2.mean()),3),
                later_fraction_near_earlier_with_heading_within_30deg=round(float((near2&(angle<=math.pi/6)).mean()),3),
                intervening_steps=[b1+1,a2-1],
                intervening_max_distance_from_earlier_footprint_pixels=round(float(away.max()),2),
                intervening_col_range=[float(between[:,0].min()),float(between[:,0].max())],
                intervening_row_range=[float(between[:,1].min()),float(between[:,1].max())])
            options.append((score,-i,item))
        if options:
            chosen=max(options,key=lambda x:(x[0],x[1]))[2]
            candidates.append(dict(id=f'E{len(candidates)+1:02d}',**chosen))
    return dict(steps=len(xy),coordinate_system=payload['coordinate_system'],
        method=dict(window_records=25,spatial_match_radius_pixels=8,heading_match_degrees=30,
            candidate_selection='For each later window, retain the best mean bidirectional spatial coverage among nonadjacent earlier windows; ties choose the earliest. At least one directional coverage must be >=0.5.',
            limitations='Pixels are quantized, not meters. Matches can reflect continuous trapping, transit, or search. These are NOT redundancy labels. No candidate does NOT establish no repeated search. All windows are included; adjacent-window revisits and other matches may be omitted. Heading variation is movement, not proof of visual coverage.'),
        windows=windows,candidate_window_matches=candidates)

def bounds_for(payloads):
    xy=np.concatenate([arrays(p)[0] for p in payloads]);lo=xy.min(0);hi=xy.max(0)
    span=max(float((hi-lo).max()),30)*1.18;center=(hi+lo)/2
    return [float(center[0]-span/2),float(center[0]+span/2),float(center[1]-span/2),float(center[1]+span/2)]

def overview(payload,bounds,target):
    xy,h,c=arrays(payload);n=len(xy)
    fig,ax=plt.subplots(figsize=(7,7),dpi=120)
    seg=np.stack([xy[:-1],xy[1:]],axis=1)
    lc=LineCollection(seg,cmap='turbo',norm=plt.Normalize(0,500),linewidths=2)
    lc.set_array(np.arange(2,n+1));ax.add_collection(lc)
    ax.scatter(*xy[0],c='black',s=35,zorder=4);ax.scatter(*xy[-1],facecolors='white',edgecolors='black',marker='s',s=65,zorder=5)
    indices=sorted(set(np.linspace(0,n-1,min(n,8)).round().astype(int)))
    by_height=sorted(indices,key=lambda i:xy[i,1])
    for members,lane,alignment in ((by_height[::2],.025,'left'),(by_height[1::2],.975,'right')):
        for i,y in zip(members,np.linspace(.94,.08,len(members))):
            label=f'{i+1}'+(' START' if i==0 else ' END' if i==n-1 else '')
            ax.annotate(label,xy[i],xytext=(lane,y),textcoords='axes fraction',
                fontsize=10,fontweight='bold',ha=alignment,va='center',
                arrowprops=dict(arrowstyle='-',color='#aaaaaa',lw=.65),
                bbox=dict(facecolor='white',edgecolor='none',pad=1.5))
    ax.set(xlim=bounds[:2],ylim=(bounds[3],bounds[2]),aspect='equal',xlabel='map column (pixels)',ylabel='map row (pixels)',title=f'Trajectory | {n} recorded steps | no walls shown')
    fig.colorbar(lc,ax=ax,orientation='horizontal',pad=.12,fraction=.04,label='step (shared 0–500 scale)')
    fig.tight_layout();fig.savefig(target);plt.close(fig)

def motion(payload,target):
    xy,h,c=arrays(payload);t=np.arange(1,len(xy)+1)
    fig,axes=plt.subplots(3,1,figsize=(10,6),dpi=110,sharex=True)
    axes[0].plot(t,xy[:,0],label='col');axes[0].plot(t,xy[:,1],label='row');axes[0].legend();axes[0].set_ylabel('map pixels')
    axes[1].plot(t,np.rad2deg(h));axes[1].set_ylabel('unwrapped heading (deg)')
    axes[2].step(t,c.astype(int),where='mid');axes[2].set(yticks=[0,1],ylabel='collision',xlabel='step',xlim=(0,500))
    fig.tight_layout();fig.savefig(target);plt.close(fig)

def animation(payloads,bounds,target):
    # Equal step, equal spatial scale. No inferred walls or behavior labels.
    side=420;top=48;frames=[];xylist=[arrays(p)[0] for p in payloads]
    font=ImageFont.truetype('/usr/share/fonts/dejavu-sans-fonts/DejaVuSans.ttf',15)
    def coord(p,offset):
        return (round(offset+20+(p[0]-bounds[0])/(bounds[1]-bounds[0])*(side-40)),
                round(top+20+(p[1]-bounds[2])/(bounds[3]-bounds[2])*(side-40)))
    maximum=max(map(len,xylist));ticks=list(range(1,maximum+1,5))
    if ticks[-1]!=maximum:ticks.append(maximum)
    for step in ticks:
        image=Image.new('RGB',(side*2,side+top),'white');draw=ImageDraw.Draw(image)
        for k,xy in enumerate(xylist):
            n=min(step,len(xy));offset=k*side;pts=[coord(p,offset) for p in xy[:n]]
            draw.text((offset+15,12),f'{"AB"[k]}  step {n}/{len(xy)}'+('  ENDED' if step>=len(xy) else ''),font=font,fill='black')
            if len(pts)>1:draw.line(pts,fill=(55,100,175),width=2)
            if len(pts)>2:draw.line(pts[-6:],fill=(230,140,20),width=3)
            x,y=pts[0];draw.ellipse((x-4,y-4,x+4,y+4),fill='black')
            x,y=pts[-1];collision=payloads[k]['waypoints'][n-1]['collision']
            draw.ellipse((x-6,y-6,x+6,y+6),outline='red' if collision else 'blue',width=2)
        draw.line((side,0,side,side+top),fill='#dddddd')
        frames.append(image.convert('P',palette=Image.Palette.ADAPTIVE,colors=64))
    frames[0].save(target,save_all=True,append_images=frames[1:],duration=[120]*(len(frames)-1)+[1400],loop=0,optimize=True)

def link(target,source):
    if not target.exists():target.symlink_to(os.path.relpath(source,target.parent))

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--root',type=Path,default=ROOT);args=parser.parse_args();root=args.root
    root.mkdir(parents=True,exist_ok=True);records=[]
    for number,(g,a,b) in enumerate(PAIRS,1):
        pair=f'pair_{number:02d}';folder=root/pair;folder.mkdir(exist_ok=True)
        cases=[f'group_{g:02d}/episode_{e:03d}' for e in (a,b)]
        payloads=[json.loads((SOURCE/c/'waypoints.json').read_text()) for c in cases]
        bounds=bounds_for(payloads)
        record=dict(id=pair,group=f'group_{g:02d}',A=cases[0],B=cases[1],swap=number in SWAPS,shared_bounds_col_row=bounds,source_sha256={s:hashlib.sha256((SOURCE/c/'waypoints.json').read_bytes()).hexdigest() for s,c in zip('AB',cases)})
        records.append(record)
        for side,case,payload in zip('AB',cases,payloads):
            source=SOURCE/case
            link(folder/f'{side}_waypoints.json',source/'waypoints.json')
            link(folder/f'{side}_rgb',source/'rgb')
            link(folder/f'{side}_goal.png',source/'goal.png')
            link(folder/f'{side}_scene.png',source/'trajectory.png')
            contact=BASE/'results/qwen_diagnostic/codex_audit/group8'/f'{case.replace("/","_")}_rgb.png'
            link(folder/f'{side}_rgb_sheet.png',contact)
            if not (folder/f'{side}_overview.png').exists():overview(payload,bounds,folder/f'{side}_overview.png')
            if not (folder/f'{side}_motion.png').exists():motion(payload,folder/f'{side}_motion.png')
            if not (folder/f'{side}_evidence.json').exists():dump(folder/f'{side}_evidence.json',evidence(payload))
        if not (folder/'comparison.gif').exists():animation(payloads,bounds,folder/'comparison.gif')
        if not (folder/'review.md').exists():
            text=f'# {pair}：同任务两条轨迹\n\n[返回入口](../README.md) · [填写人工判断](../human_labels.md)\n\n'
            text+=f'A：`{cases[0]}`；B：`{cases[1]}`。请在 human_labels.md 的 `{pair}` 行填写。\n\n'
            text+='只比较重复搜索负担；纯卡住、碰撞和脱困不计入。不按总步数或任务成败排序。可以并列或无法判断。\n\n'
            text+='## 同步动画（仅供人工）\n\n同一时刻、同一空间比例；蓝线为已走轨迹，橙色为最近约5步，红圈表示当前步碰撞。较短轨迹结束后停留在终点，并标注 ENDED。动画每5步一帧；精确事实请对照 JSON。\n\n![同步轨迹](comparison.gif)\n\n'
            for side in 'AB':
                text+=f'## 轨迹 {side}\n\n![{side} 全程]({side}_overview.png)\n\n![{side} 运动事实]({side}_motion.png)\n\n![{side} RGB]({side}_rgb_sheet.png)\n\n'
                text+=f'[原始逐步 JSON]({side}_waypoints.json) · [RGB 原图目录]({side}_rgb/) · [原始场景轨迹图]({side}_scene.png) · [目标图]({side}_goal.png)\n\n'
            text+='## 证据说明\n\n白底图不显示墙体。RGB 的 step 是已执行动作数：step 0 为初始观测，step 25 对应第25个动作之后、下个动作之前的观测；末张通常是终止前一次动作的观测，不是终止后的画面。RGB 为稀疏采样，不能补出未保存的帧。审核无需证明真实信息增益为零；请根据可见证据判断是否存在有分量的再次搜索。\n'
            (folder/'review.md').write_text(text)
        print(f'{pair} ready',flush=True)
    if not (root/'manifest.json').exists():dump(root/'manifest.json',dict(source=str(SOURCE),pairs=records,swapped_pairs=[f'pair_{i:02d}' for i in SWAPS],conditions=['A0','A1'],planned_requests=64,selection='Purposeful development-case selection from existing same-task groups; not an independent benchmark. No expected pair preferences assigned.'))
    if not (root/'human_labels.md').exists():
        text='# 人工成对判断：只填写本文件\n\n[查看全部审核页](README.md)\n\n'
        text+='判断填：`A更少`、`B更少`、`并列`、`无法判断`。比较额外重复搜索，纯卡住/脱困不计入。\n\n'
        text+='“并列”表示证据足够、没有值得区分的差别；“无法判断”表示关键行为或差异证据不足。把握填高/中/低。区间是可选项，可写“无”“不清楚”或“60–105”；不要为填写而强行寻找冗余。理由请至少写一句，可同时记录卡住区间。表格单元格内请勿使用竖线字符。\n\n'
        text+='| 编号 | 判断 | 把握 | A重复搜索区间（可选） | B重复搜索区间（可选） | 依据／疑问（必填） |\n|---|---|---|---|---|---|\n'
        for r in records:text+=f'| [{r["id"]}]({r["id"]}/review.md) |  |  |  |  |  |\n'
        (root/'human_labels.md').write_text(text)
    if not (root/'README.md').exists():
        text='# 相对重复搜索诊断：24 对人工审核\n\n**只需填写 [human_labels.md](human_labels.md)。** 每行编号链接到对应审核页。可分批保存；生成脚本不会覆盖你的填写。\n\n'
        text+='每对来自相同任务与 checkpoint，包含共用比例的俯视图、同步 GIF、位置/朝向/碰撞曲线、全部已保存 RGB。审核页不展示旧 AI 或 Qwen 判断。GIF 与 RGB 当前仅供人工审核；A1 模型条件是概览图＋计算事实。\n\n'
        text+='请先独立审核并填写。人工判断固定后，再运行 A0/A1 并比较结果；未知可以保留，无需强行排序。这是开发诊断，不是独立测试集，也不修改 PPO。\n\n'
        text+='| 编号 | A | B | 审核 |\n|---|---|---|---|\n'
        for r in records:text+=f'| {r["id"]} | {r["A"]} | {r["B"]} | [打开]({r["id"]}/review.md) |\n'
        (root/'README.md').write_text(text)

if __name__=='__main__':main()
