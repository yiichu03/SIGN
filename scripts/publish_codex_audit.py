#!/usr/bin/env python3
"""Publish explicitly authored AI notes, without modifying human annotations."""
import csv
import hashlib
import json
import os
from collections import Counter
from datetime import datetime,timezone
from pathlib import Path

BASE=Path(__file__).resolve().parents[1]/'results/qwen_diagnostic'
OUT=BASE/'codex_audit'
LABEL={'NONE':'无或可忽略','SOME':'有','CLEAR':'明显有','UNCERTAIN':'不确定'}
FULL_RGB={'val_easy/episode_002','val_easy/episode_012','val_easy/episode_023','val_easy/episode_027','val_hard/episode_004','val_hard/episode_006','val_hard/episode_008'}

def publish(kind,dataset,evidence_tag):
    note=OUT/('notes_'+kind+'.tsv')
    if not note.exists():return []
    notes=list(csv.DictReader(note.open(),delimiter='\t'))
    evidence={x['case']:x for x in json.loads((OUT/evidence_tag/'evidence.json').read_text())}
    assert len({x['case'] for x in notes})==len(notes)
    rows=[]
    for r in notes:
        folder=BASE/dataset/r['case'];key=dataset+'/'+r['case'];ev=evidence[key]
        intervals=json.loads(r['intervals']);assert all(1<=a<=b<=ev['steps'] for a,b in intervals)
        assert r['label'] in LABEL
        p=folder/'waypoints_corrected.json'
        if not p.exists():p=folder/'waypoints.json'
        row=dict(r,dataset=dataset,intervals=intervals,reviewer='Codex AI',review_status='AI reviewed; not human ground truth',redundancy_score={'NONE':0,'SOME':1,'CLEAR':2}.get(r['label']),steps=ev['steps'],collisions=ev['collisions'],waypoints_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),reviewed_at=datetime.now(timezone.utc).isoformat(),confidence_note='Qualitative reviewer confidence, not calibrated probability',viewing='Time-colored full trajectory; position/heading time series; collision markers; goal and up to five evenly spaced saved RGB frames when available',full_rgb_contact_sheet_also_inspected=dataset=='additional120' and r['case'] in FULL_RGB)
        if dataset=='graded60':row['viewing']='Trajectory plot, position/heading time series and collisions; no RGB/goal available; prior study context known'
        elif dataset=='group8_p12':row['viewing']+='; own labels recorded before reading Qwen results'
        rows.append(row)
        assets=os.path.relpath(OUT/evidence_tag,folder)
        report=f'# {dataset}/{r["case"]} — Codex AI 复核\n\n**性质：AI 复核，不是人工真值。** 范围：重复搜索；纯卡住、碰撞、脱困单独报告。\n\n'
        report+=f'- 冗余探索程度：**{LABEL[r["label"]]}**（{r["label"]}）\n- 大致 step 区间：{intervals or "无"}\n- 判断把握：{r["confidence"]}（主观等级，非概率）\n- 总步数：{ev["steps"]}；碰撞步数：{ev["collisions"]}。这些数值不直接决定标签。\n\n'
        report+='## 依据\n\n'+r['evidence']+'\n\n## 卡住／脱困\n\n'+r['recovery']+'\n\n'
        report+='![完整轨迹](trajectory2.png)\n\n[逐步数据]('+p.name+')\n\n'
        if 'page' in ev:report+=f'[轨迹、朝向与观测审核页]({assets}/page_{ev["page"]:02d}.png)\n\n'
        if (folder/'goal.png').exists():
            report+=f'[全部已保存 RGB 关键帧]({assets}/{folder.parent.name}_{folder.name}_rgb.png) · [目标图](goal.png)\n\n'
        report+='## 证据限制\n\n'+row['viewing']+'。\n\nRGB 为动作前观测，waypoint 为动作后姿态；step k 的 RGB 对应执行第 k+1 个动作前。稀疏关键帧可能遗漏中间视野或与周期运动发生采样混叠；相似帧不证明没有转动。地图坐标为像素，不是米。未将成功、失败或总步数直接作为冗余标签依据。\n\n'
        report+='## 人工确认\n\n- 是否同意：\n- 修订标签／区间／依据：\n'
        path=folder/'codex_review.md'
        # Preserve any subsequently filled human confirmation block.
        if path.exists() and '## 人工确认' in path.read_text():report=report.split('## 人工确认')[0]+'## 人工确认'+path.read_text().split('## 人工确认',1)[1]
        path.write_text(report)
        (folder/'codex_review.json').write_text(json.dumps(row,ensure_ascii=False,indent=2)+'\n')
    return rows

def main():
    rows=publish('additional120','additional120','additional120')+publish('graded60_priority','graded60','graded60_priority')+publish('group8','group8_p12','group8')
    (OUT/'reviews.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n')
    with (OUT/'reviews.csv').open('w',encoding='utf-8-sig',newline='') as f:
        cols=['dataset','case','label','redundancy_score','intervals','confidence','steps','collisions','evidence','recovery']
        w=csv.DictWriter(f,cols,extrasaction='ignore');w.writeheader();w.writerows(rows)
    text='# Codex 轨迹 AI 复核\n\n口径：只评重复搜索，卡住／脱困单独报告。所有标签为 AI 判断，原人工备注保持独立。\n\n[结构化记录](reviews.json) · [汇总 CSV](reviews.csv)\n\n'
    text+='每条检查完整轨迹、位置/朝向时间曲线及碰撞标记；新增数据还看目标图和最多5个均匀抽取的已保存RGB，部分复杂案例追加查看全部已保存关键帧。不是逐帧完整视频审核。脚本只绘图和计算统计，标签与理由逐条由Codex撰写。\n\n'
    for dataset in ('additional120','graded60','group8_p12'):
        local=[r for r in rows if r['dataset']==dataset]
        if not local:continue
        counts=Counter(r['label'] for r in local)
        text+=f'## {dataset}：{len(local)} 条\n\n'+ '；'.join(f'{LABEL[k]} {counts[k]}' for k in LABEL)+'。\n\n'
        text+='| 序列 | AI 判断 | 区间 | 把握 | 报告 |\n|---|---|---|---|---|\n'
        for r in local:text+=f'| {r["case"]} | {LABEL[r["label"]]} | {r["intervals"]} | {r["confidence"]} | [查看](../{dataset}/{r["case"]}/codex_review.md) |\n'
        text+='\n'
    text+='## 解读\n\nNONE 只表示未发现有分量的重复搜索，不保证导航有效；长期卡住可能为 NONE。UNCERTAIN 不映射为零分。SOME/CLEAR 是有序等级，0/1/2 的数值间距尚未校准。稀疏RGB与运动周期可能混叠，角度以逐步记录为准。\n'
    (OUT/'index.md').write_text(text)
    print(dict(Counter((r['dataset'],r['label']) for r in rows)))

if __name__=='__main__':main()
