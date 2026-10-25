#!/usr/bin/env python3
"""Create human-only review assets and verify the sampled episode identities."""
import argparse
import json
from pathlib import Path
from preview_trajectory_layouts import white_gradient
from render_trajectory_gifs import render_episode, REVIEW_HEADING

ROOT = Path(__file__).resolve().parents[1]/'results/qwen_diagnostic/additional120'

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('split',choices=('val_easy','val_medium','val_hard'))
    args=parser.parse_args()
    manifest=json.loads((ROOT/'manifest.json').read_text())
    expected={(Path(e['scene_id']).name,e['episode_id']):e for e in manifest['episodes'] if e['split']==args.split}
    folders=sorted((ROOT/args.split).glob('episode_*/waypoints.json'))
    assert len(folders)==40, len(folders)
    actual=set()
    links=[]
    for p in folders:
        folder=p.parent
        data=json.loads(p.read_text())
        key=(Path(data['scene_id']).name,str(data['episode_id']))
        assert key in expected and key not in actual, key
        actual.add(key)
        round_id=expected[key]['review_round']
        assert (folder/'goal.png').exists() and (folder/'metrics.json').exists()
        white_gradient(folder,folder/'trajectory2.png')
        report=folder/'review.md'
        if not report.exists():
            frames=sorted((folder/'rgb').glob('step_*.png'))
            text=f'# {args.split}/{folder.name}\n\n场景：{key[0]}；episode：{key[1]}；审核轮次：{round_id}；动作数：{len(data["waypoints"])}。\n\n'
            text+='![白底轨迹](trajectory2.png)\n\n[完整 waypoint JSON](waypoints.json) · [导航指标](metrics.json)\n\n'
            text+=f'{REVIEW_HEADING}\n\n![动态轨迹](trajectory.gif)\n\n'
            text+='## 目标图与 RGB 关键帧\n\n![目标图](goal.png)\n\nRGB 为动作执行前的原始观测；step 0 为初始观测，每 25 步保存，并补充最后一个动作前的观测。终止后的环境自动重置画面不保存。\n\n'
            text+='\n\n'.join(f'**{f.stem}**\n\n![{f.stem}](rgb/{f.name})' for f in frames)
            text+='\n\n## 人工复核\n\n- 冗余探索程度（无或可忽略／有／明显有／不确定）：\n- 大致 step 区间：\n- 行为类型与依据：\n- 备注：\n'
            report.write_text(text)
        if not (folder/'trajectory.gif').exists():
            render_episode(folder,180)
        links.append((round_id,f'- [{folder.name}]({folder.name}/review.md) — {key[0]} / {key[1]}'))
    assert actual==set(expected)
    index=f'# {args.split} 新增轨迹：40 条\n\n'
    for i in (1,2):
        index+=f'## 第 {i} 轮审核：20 条\n\n'+'\n'.join(t for r,t in links if r==i)+'\n\n'
    (ROOT/args.split/'index.md').write_text(index)
    overall='# 新增 120 条 ImageNav 轨迹\n\n10 个新场景；每场景每难度随机取 4 条。每个难度的审核名单在采集前分为两轮，每轮 20 条。\n\n'
    for split in ('val_easy','val_medium','val_hard'):
        status='40 条完成，报告可用' if (ROOT/split/'index.md').exists() else '待完成'
        overall+=f'- [{split}]({split}/index.md)：{status}\n'
    overall+='\n[采样名单、随机种子与 checkpoint 校验值](manifest.json)\n\n本轮只采集和生成供人工审核的图像、JSON 与报告，未运行 Qwen。\n'
    (ROOT/'index.md').write_text(overall)
    print(f'{args.split}: 40 identities verified; images, GIFs, keyframes and reports ready.',flush=True)

if __name__=='__main__':main()
