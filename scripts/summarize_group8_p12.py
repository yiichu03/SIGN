#!/usr/bin/env python3
"""Compare frozen independent AI grades with p12, retaining ties and abstentions."""
import csv
import hashlib
import itertools
import json
import math
import statistics
from collections import Counter
from pathlib import Path

BASE=Path(__file__).resolve().parents[1]/'results/qwen_diagnostic'
ROOT=BASE/'group8_p12'
AUDIT=BASE/'codex_audit'
LABEL={'NONE':'无或可忽略','SOME':'有','CLEAR':'明显有','UNCERTAIN':'不确定','INVALID':'格式错误'}

def sign(x):return (x>0)-(x<0)

def order_line(rows, source):
    levels=[]
    for score in (0,1,2):
        cases=[r['case'].replace('episode_','') for r in rows if r[source+'_score']==score]
        if cases:levels.append(f'{score}分：'+ '、'.join(cases))
    unknown=[r['case'].replace('episode_','') for r in rows if r[source+'_score'] is None]
    return ' ＜ '.join(levels)+('；不参与排序：'+ '、'.join(unknown) if unknown else '')

def main():
    frozen=json.loads((AUDIT/'group8_labels_frozen_before_comparison.json').read_text())
    assert hashlib.sha256((AUDIT/'notes_group8.tsv').read_bytes()).hexdigest()==frozen['sha256']
    rows=[];groups=[];pairs=[]
    for g in json.loads((ROOT/'manifest.json').read_text())['groups']:
        folder=ROOT/g['group'];assert (folder/'collection_verified.json').exists()
        local=[]
        for f in sorted(folder.glob('episode_*')):
            a=json.loads((f/'codex_review.json').read_text())
            q=json.loads((f/'qwen_p12/result.json').read_text())
            assert hashlib.sha256((f/'qwen_p12/request.txt').read_bytes()).hexdigest()==q['request_sha256']
            payload=json.loads((f/'waypoints.json').read_text())
            sent=json.loads((f/'qwen_p12/request.txt').read_text().split('WAYPOINT_JSON:\n',1)[1]);assert sent==payload
            m=json.loads((f/'metrics.json').read_text())
            r=dict(group=g['group'],case=f.name,ai_label=a['label'],ai_score=a['redundancy_score'],qwen_label=q['parsed']['label'] if q['parsed'] else 'INVALID',qwen_score=q['redundancy_score'],steps=a['steps'],collision_steps=a['collisions'],success=m.get('success'),spl=m.get('spl'),task_return=m.get('reward'),distance_to_goal=m.get('distance_to_goal'),qwen_intervals=q['parsed']['intervals'] if q['parsed'] else [],ai_intervals=a['intervals'],qwen_evidence=q['parsed']['evidence'] if q['parsed'] else q['parse_error'],ai_evidence=a['evidence'],interval_bounds_valid=q['interval_bounds_valid'],output_limited=q['hit_output_limit'])
            local.append(r)
        assert len(local)==8
        values=[r['qwen_score'] for r in local if r['qwen_score'] is not None]
        mean=statistics.mean(values) if values else None;std=statistics.pstdev(values) if values else None
        for r in local:
            r['illustrative_redundancy_advantage']=None if r['qwen_score'] is None else ((mean-r['qwen_score'])/(std+1e-8) if std else 0.)
        counts=Counter()
        for a,b in itertools.combinations(local,2):
            if any(r[k] is None for r in (a,b) for k in ('ai_score','qwen_score')):kind='unresolved'
            else:
                x=sign(a['ai_score']-b['ai_score']);y=sign(a['qwen_score']-b['qwen_score'])
                if x==y:kind='agree_tie' if x==0 else 'agree_order'
                elif x==0:kind='qwen_splits_ai_grade'
                elif y==0:kind='qwen_ties_ai_order'
                else:kind='reverse_order'
            counts[kind]+=1
            pairs.append(dict(group=g['group'],first=a['case'],second=b['case'],comparison=kind,ai_first=a['ai_score'],ai_second=b['ai_score'],qwen_first=a['qwen_score'],qwen_second=b['qwen_score']))
        c,d=counts['agree_order'],counts['reverse_order'];ta,tq=counts['qwen_splits_ai_grade'],counts['qwen_ties_ai_order']
        denom=math.sqrt((c+d+ta)*(c+d+tq))
        timing=json.loads((folder/'qwen_batch.json').read_text())
        summary=dict(group=g['group'],split=g['split'],ai_labels=dict(Counter(r['ai_label'] for r in local)),qwen_labels=dict(Counter(r['qwen_label'] for r in local)),pairs=dict(counts),kendall_tau_b=(c-d)/denom if denom else None,strict_ai_order_pairs=c+d+tq,correct_strict_ai_order_pairs=c,valid_qwen_scores=len(values),qwen_grade_variants=len(set(values)),batch_seconds=timing['seconds'],amortized_seconds=timing['amortized_seconds'],successes=sum(r['success']==1 for r in local))
        groups.append(summary);rows.extend(local)
        report=f'# {g["group"]}：同任务 8 条轨迹\n\n[任务及采样清单](../manifest.json) · [组内身份校验](collection_verified.json)\n\n'
        report+='分数越高表示重复搜索越多：NONE=0、SOME=1、CLEAR=2；不确定不赋分。AI为独立复核，不是人工真值。\n\n'
        report+='- AI 粗等级顺序：'+order_line(local,'ai')+'。\n- p12 粗等级顺序：'+order_line(local,'qwen')+'。\n\n同一等级内保留并列，不用步数或成功率暗中打破平局。\n\n'
        report+='| 试次 | AI 等级 | p12 等级 | 步数 | 碰撞步 | 成功 | p12冗余相对优势示意 | 审核 |\n|---|---|---|---:|---:|---:|---:|---|\n'
        for r in local:
            adv=r['illustrative_redundancy_advantage'];s='—' if adv is None else f'{adv:.3f}'
            report+=f'| {r["case"]} | {LABEL[r["ai_label"]]} | {LABEL[r["qwen_label"]]} | {r["steps"]} | {r["collision_steps"]} | {r["success"]} | {s} | [AI记录]({r["case"]}/codex_review.md) |\n'
        report+='\n相对优势仅演示对 -冗余分做组内标准化；未与导航任务奖励合并，也未用于任何策略更新。整组同分时为0；未知样本不参与均值/方差。\n\n'
        report+='## 逐条证据\n\n'
        for r in local:
            case=r['case'];report+=f'### {case}\n\n![轨迹]({case}/trajectory2.png)\n\nAI：{r["ai_evidence"]}\n\np12：{r["qwen_evidence"]}\n\n[完整模型输入]({case}/qwen_p12/request.txt) · [原始输出]({case}/qwen_p12/response.txt) · [AI复核与RGB]({case}/codex_review.md)\n\n'
        report+='## 人工确认组内关系\n\n- 应并列的试次：\n- 明确先后关系／需要调整的等级：\n- 依据：\n'
        path=folder/'review.md'
        if path.exists() and '## 人工确认组内关系' in path.read_text():report=report.split('## 人工确认组内关系')[0]+'## 人工确认组内关系'+path.read_text().split('## 人工确认组内关系',1)[1]
        path.write_text(report)
    assert len(rows)==80
    total=Counter(p['comparison'] for p in pairs)
    valid=[r for r in rows if r['ai_score'] is not None and r['qwen_score'] is not None]
    confusion=Counter((r['ai_label'],r['qwen_label']) for r in rows)
    result=dict(trajectories=80,tasks=10,ai_reference='Frozen Codex AI ordinal assessment, not human truth; richer observation evidence than Qwen',qwen='Unchanged p12 JSON-only, independent prompts, one same-task batch of eight',ai_labels=dict(Counter(r['ai_label'] for r in rows)),qwen_labels=dict(Counter(r['qwen_label'] for r in rows)),comparable_trajectories=len(valid),exact_grade_agreement=sum(r['ai_score']==r['qwen_score'] for r in valid),binary_agreement=sum((r['ai_score']>0)==(r['qwen_score']>0) for r in valid),tp=sum(r['ai_score']>0 and r['qwen_score']>0 for r in valid),tn=sum(r['ai_score']==0 and r['qwen_score']==0 for r in valid),fp=sum(r['ai_score']==0 and r['qwen_score']>0 for r in valid),fn=sum(r['ai_score']>0 and r['qwen_score']==0 for r in valid),pairs=dict(total),strict_ai_order_pairs=total['agree_order']+total['reverse_order']+total['qwen_ties_ai_order'],correct_strict_ai_order_pairs=total['agree_order'],groups=groups,confusion=[dict(ai=a,qwen=b,n=n) for (a,b),n in sorted(confusion.items())],mean_batch_seconds=statistics.mean(g['batch_seconds'] for g in groups),amortized_seconds_per_trajectory=sum(g['batch_seconds'] for g in groups)/80,invalid_intervals=sum(not r['interval_bounds_valid'] for r in rows),output_limited=sum(r['output_limited'] for r in rows),limits='No human calibration or fine-grained continuous-score validation. Pair counts within tasks are dependent; 280 pairs are not 280 independent samples. Correct labels do not validate factual rationales.')
    (ROOT/'comparison.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    for name,data in [('comparison.csv',rows),('pairs.csv',pairs)]:
        with (ROOT/name).open('w',encoding='utf-8-sig',newline='') as f:w=csv.DictWriter(f,list(data[0]));w.writeheader();w.writerows(data)
    report='# 同任务 8 条：p12 粗等级组内排序诊断\n\n[结论与后续建议](interpretation.md) · [依据核查](rationale_audit.md) · [方法与限制](method.md) · [完整统计](comparison.json) · [逐条对照](comparison.csv) · [组内成对关系](pairs.csv) · [独立 AI 审核索引](../codex_audit/index.md)\n\n'
    report+='10个任务×8条随机策略轨迹，固定checkpoint，未训练；组内起点、目标图、初始RGB均相同。p12只接收完整JSON，8个独立prompt批量推理。AI先依据轨迹、碰撞、朝向、目标图与稀疏RGB形成并固定标签，再读取Qwen结果。\n\n'
    report+=f'## 结果\n\n- AI 标签：{result["ai_labels"]}\n- Qwen 标签：{result["qwen_labels"]}\n- 可比较轨迹：{len(valid)}/80；四级中的已知等级一致：{result["exact_grade_agreement"]}/{len(valid)}；二元有无一致：{result["binary_agreement"]}/{len(valid)}。\n- 相对AI参考：TP {result["tp"]}、TN {result["tn"]}、FP {result["fp"]}、FN {result["fn"]}。\n- AI明确区分等级且Qwen已给分的成对关系：{result["strict_ai_order_pairs"]}；顺序一致 {total["agree_order"]}，颠倒 {total["reverse_order"]}，Qwen压成同分 {total["qwen_ties_ai_order"]}。\n- 双方同等级并列 {total["agree_tie"]} 对；Qwen拆开AI同等级 {total["qwen_splits_ai_grade"]} 对；因不确定/无效而不比较 {total["unresolved"]} 对。\n- 平均每8条批次 {result["mean_batch_seconds"]:.2f}s，摊销每条 {result["amortized_seconds_per_trajectory"]:.2f}s；不含排队、模型加载、报告生成。\n\n'
    report+='| 组 | AI 等级分布 | Qwen 等级分布 | 明确顺序一致/可比较 | 成功数 | 报告 |\n|---|---|---|---:|---:|---|\n'
    for g in groups:
        relation=f'{g["correct_strict_ai_order_pairs"]}/{g["strict_ai_order_pairs"]}' if g['strict_ai_order_pairs'] else '无明确等级差'
        report+=f'| {g["group"]} | {g["ai_labels"]} | {g["qwen_labels"]} | {relation} | {g["successes"]}/8 | [查看]({g["group"]}/review.md) |\n'
    report+='\n## 使用边界\n\n这是粗等级排序可行性检查，不是经人工确认的评分准确率。p12并没有输出校准过的连续奖励；0/1/2只是序数映射，差值尚不具有实测意义。AI同等级并不证明所有细微程度完全相同，但不能据此强行细排。重复搜索为0并不保证任务成功；具体导航指标在各组报告独立列出。\n\n现有SIGN-SRU为PPO/GAE；本轮只计算示意组内优势，没有修改训练损失或把终局分数写入每一步奖励。\n'
    (ROOT/'index.md').write_text(report)
    print(json.dumps({k:v for k,v in result.items() if k not in ('groups','confusion')},ensure_ascii=False,indent=2))

if __name__=='__main__':main()
