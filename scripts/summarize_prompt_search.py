#!/usr/bin/env python3
"""Export the complete 20-prompt development comparison and shared case reviews."""
import csv
import hashlib
import json
import os
import statistics
from pathlib import Path
from qwen_prompt_search import ROOT,DATA,MODES,CONTEXT,FORMAT,HEADER

NAMES={'image_only':'PNG','json_only':'JSON','image_json':'PNG＋JSON'}
ZH={'NONE':'无/可忽略','SOME':'有','CLEAR':'明显有','UNCERTAIN':'不确定','INVALID':'格式错误'}

def main():
 refs=json.loads((ROOT/'human_reference.json').read_text());ref={r['case']:r for r in refs}
 ids=[f'p{i:02d}' for i in range(1,21)]
 summaries=[];specs={};records={};complete=[]
 for pid in ids:
  spec=json.loads((ROOT/'prompts'/(pid+'.json')).read_text());specs[pid]=spec
  meta=json.loads((ROOT/pid/'run.json').read_text());assert meta['status']=='complete',(pid,meta['status'])
  summary=json.loads((ROOT/pid/'summary.json').read_text());assert len(summary)==3
  for s in summary:assert s['completed']==60 and s['clear_reference_n']==51
  summaries.extend(summary)
  for case in ref:
   for mode in MODES:
    p=ROOT/pid/case/mode;r=json.loads((p/'result.json').read_text())
    assert hashlib.sha256((p/'request.txt').read_bytes()).hexdigest()==r['request_sha256']
    assert (p/'response.txt').exists()
    assert (r['image'] is None)==(mode=='json_only')
    records[(pid,case,mode)]=r
  complete.append(dict(prompt_id=pid,job_id=meta['job_id'],status=meta['status']))
  # Full reusable instructions, including common wrapper and output contract.
  for mode in MODES:
   text=HEADER[mode]+'\n'+spec.get('context',CONTEXT)+'\n'+spec['body'].strip()+'\n\n'+spec.get('output_format',FORMAT)
   if mode!='image_only':text+='\nWAYPOINT_JSON:\n{{FULL_CORRECTED_WAYPOINT_JSON}}'
   if spec.get('footer'):text+='\n\nFINAL TASK REMINDER:\n'+spec['footer']
   p=ROOT/'templates'/f'{pid}_{mode}.txt';p.parent.mkdir(exist_ok=True);p.write_text(text+'\n')
 hashes=json.loads((ROOT/'input_hashes.json').read_text())
 for case,files in hashes.items():
  for name,expected in files.items():assert hashlib.sha256((DATA/case/name).read_bytes()).hexdigest()==expected
 # Source annotations were never modified; report any external edits separately.
 changed=[r['case'] for r in refs if hashlib.sha256((DATA/r['case']/'review2.md').read_bytes()).hexdigest()!=r['review2_sha256']]
 rankings=[]
 for pid in ids:
  ss=[s for s in summaries if s['prompt_id']==pid]
  rankings.append(dict(prompt_id=pid,name=specs[pid]['name'],mean_balanced_agreement=statistics.mean(s['balanced_accuracy'] for s in ss),mean_four_level_agreement=statistics.mean(s['four_level_agreement'] for s in ss),total_fp=sum(s['fp'] for s in ss),total_fn=sum(s['fn'] for s in ss),total_abstentions=sum(s['abstentions_on_clear'] for s in ss)))
 rankings.sort(key=lambda r:(-r['mean_balanced_agreement'],-r['mean_four_level_agreement']))
 best={m:max((s for s in summaries if s['mode']==m),key=lambda s:(s['balanced_accuracy'],s['four_level_agreement'])) for m in MODES}
 (ROOT/'final_ranking.json').write_text(json.dumps(dict(overall=rankings,best_by_mode=best,completed_jobs=complete,formal_responses=len(records),source_annotations_changed=changed),ensure_ascii=False,indent=2)+'\n')
 with (ROOT/'final_ranking.csv').open('w',encoding='utf-8-sig',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(rankings[0]));w.writeheader();w.writerows(rankings)
 priority=[];case_index='# 60 条逐案例对照\n\n每条只展示一次轨迹图和 GIF，集中列出全部 20 个 prompt 的三组判断。人工参考来自冻结的原始评论，未输入 Qwen。\n\n'
 for case,h in ref.items():
  dest=ROOT/'case_review'/f'{case}.md';dest.parent.mkdir(parents=True,exist_ok=True)
  rel=os.path.relpath(DATA/case,dest.parent)
  eligible=h['reference_label'] in ('NONE','SOME','CLEAR') and not h['stuck_related']
  text=f'# {case}\n\n原人工标注：**{h["human"]}**；进入主要统计：**{"是" if eligible else "否，需要补充/重新复核"}**。\n\n{h["comment"]}\n\n![PNG]({rel}/trajectory2.png)\n\n![人工 GIF]({rel}/trajectory.gif)\n\n[完整 JSON]({rel}/waypoints_corrected.json)\n\n'
  text+='| Prompt | PNG | JSON | PNG＋JSON |\n| --- | --- | --- | --- |\n'
  for pid in ids:
   cells=[]
   for mode in MODES:
    r=records[(pid,case,mode)];label=r['parsed']['label'] if r['parsed'] else 'INVALID'
    link=os.path.relpath(ROOT/pid/case/mode/'response.txt',dest.parent)
    cells.append(f'[{ZH[label]}]({link})')
   text+=f'| {pid} | '+ ' | '.join(cells)+' |\n'
  text+='\n## 各输入当前最高平衡一致率候选的原始回答\n\n'
  reasons=[]
  if not eligible:reasons.append('旧标注存在口径/确定性问题或未填写')
  for mode,s in best.items():
   pid=s['prompt_id'];r=records[(pid,case,mode)];obj=r['parsed'];lab=obj['label'] if obj else 'INVALID'
   raw=(ROOT/pid/case/mode/'response.txt').read_text()
   request=os.path.relpath(ROOT/pid/case/mode/'request.txt',dest.parent)
   text+=f'### {NAMES[mode]}：{pid}\n\n[实际输入]({request})\n\n```text\n{raw}\n```\n\n'
   if eligible and (lab in ('UNCERTAIN','INVALID') or (lab=='NONE')!=(h['reference_label']=='NONE')):reasons.append(f'{mode} 与旧人工参考不一致')
  text+='## 按新口径人工复核\n\n只判断重复搜索；卡住、碰撞、脱困单独记录。\n\n- 重复搜索：无/可忽略／有／明显有／不确定：\n- 重复搜索区间及事实依据：\n- 卡住/脱困区间（不计入重复搜索）：\n- 哪个候选的判断和依据更合理：\n'
  if dest.exists() and '## 按新口径人工复核' in dest.read_text():text=text.split('## 按新口径人工复核')[0]+dest.read_text()[dest.read_text().index('## 按新口径人工复核'):]
  dest.write_text(text)
  case_index+=f'- [{case}]({case}.md)'+(' — **优先复核**：'+'；'.join(reasons) if reasons else '')+'\n'
  if reasons:priority.append(dict(case=case,human=h['human'],reasons='；'.join(reasons)))
 (ROOT/'case_review/index.md').write_text(case_index)
 with (ROOT/'review_priority.csv').open('w',encoding='utf-8-sig',newline='') as f:
  w=csv.DictWriter(f,fieldnames=['case','human','reasons']);w.writeheader();w.writerows(priority)
 table='| Prompt | PNG | JSON | PNG＋JSON | 三组平均 |\n| --- | ---: | ---: | ---: | ---: |\n'
 for rank in rankings:
  pid=rank['prompt_id'];values=[next(s['balanced_accuracy'] for s in summaries if s['prompt_id']==pid and s['mode']==m) for m in MODES]
  table+=f'| [{pid}]({pid}/index.md) | '+ ' | '.join(f'{v:.1%}' for v in values)+f' | {rank["mean_balanced_agreement"]:.1%} |\n'
 text='# 英文 Prompt 迭代：20 个版本全部完成\n\n'
 text+='共 20 × 60 × 3 = **3,600 个正式回答**，按四轮各 5 个自适应设计。先前广义口径的中止试跑单独归档，不混入结果。\n\n'
 text+='## 口径与统计\n\n只判断重复搜索冗余，卡住/碰撞/脱困单独报告。主要统计为 51 条旧标注：23 条无或可忽略、28 条有或明显有；排除 5 条边界、1 条未标注和 3 条明确涉及卡住的旧正例，原标签不改写。旧标注仍可能包含其他口径分歧。\n\n'
 text+='下表为**对旧人工参考的平衡二分类一致率**：(正例召回率＋负例识别率)/2。不确定和不可解析回答在主要案例上均计为未匹配，避免靠弃答或全判无提高成绩。SOME/CLEAR 合并为有；程度完全一致率、覆盖率、格式错误、区间越界和耗时另存于 CSV/JSON。部分格式错误仍有可读判断，辅助统计见各候选 diagnostics.json 的 decision_only；不改写原输出。区间合法不代表区间判断正确，当前没有人工区间真值。\n\n'
 text+='这 60 条来自两个场景，并已反复用于调参，因此不是独立测试准确率。新增 120 条未用于本次调参或推理。\n\n'
 text+='## 全部版本\n\n'+table+'\n## 各输入最高分候选\n\n| 输入 | Prompt | TP / 28 | TN / 23 | 误报 | 漏报 | 不确定/格式错误（主要案例） | 程度完全一致率 | 平均秒/条 |\n| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |\n'
 for mode,s in best.items():text+=f'| {NAMES[mode]} | [{s["prompt_id"]}](templates/{s["prompt_id"]}_{mode}.txt) | {s["tp"]} | {s["tn"]} | {s["fp"]} | {s["fn"]} | {s["abstentions_on_clear"]} | {s["four_level_agreement"]:.1%} | {s["mean_seconds"]:.2f} |\n'
 text+='\n分数筛选只是候选排序；依据是否真实、卡住与搜索是否区分正确，以及程度标签是否符合人工口径，需要继续复核。平均耗时为单条请求的预处理、传输及生成，不含排队、加载和报告导出；均为 A40、greedy、关闭 thinking、最多 512 输出 token。\n\n'
 text+='## 对结果的理解与候选建议\n\n- 如果先保留一套共同模板，p17 的三种输入平均平衡一致率最高（90.0%），但与 p12（89.4%）差距很小，不能据此断言有稳定优势。按输入分别复核时，优先看 PNG 的 p17、JSON 的 p12、组合输入的 p13。它们是人工复核候选，不是已验证的自动奖励模型。\n- 有效调整主要是具体的正常/重复搜索对照、明确一个观察扫视不等于多次搜索，以及较紧凑的输出。不断追加排除条款、把标准在长 JSON 后再重复一遍、或要求先给有无再分程度，都没有在这组数据上稳定改进。p08/p09 的英文指令配不同回答语言也出现明显差异，说明输出形式同样影响结果。\n- 在相同 51 条参考案例上，历史 review2 的 JSON 为 20 个误报、0 个漏报；本轮 p12 为 1 个误报、1 个漏报。组合输入从 15 个误报、0 个漏报变为 p13 的 1 个误报、3 个漏报。但 PNG 的旧 review2 为 49/51 一致，本轮 p17 为 46/51，未全面超越旧版本。这不是纯语言对照：定义、格式等也有变化。\n- 程度划分仍弱于有无识别：PNG p17 的程度完全一致率为 56.9%，JSON p12 为 88.2%，组合 p13 为 60.8%。旧评论中的“明显”也可能同时表达程度和判断把握，仍需统一口径。\n- 高分类分数不保证依据真实或遵守搜索/脱困边界。以下审计只核查事实和明显的归因冲突，不改变人工标签，也不是新的规则分类器。\n\n### 依据审计：需要优先复核的具体例子\n\n| 案例 | 模型表述 | 记录核查 |\n| --- | --- | --- |\n| hard/007，step 7–500 | p12 JSON / p13 组合描述反复完整 360° 扫视，并把同段卡住计为搜索 | 展开周期角后的朝向跨度约 104.1°；494/494 个记录点碰撞，不能支持完整 360° 的说法 |\n| hard/017，step 50–500 | p12 / p13 将长期受困段描述为完整环向扫描 | 朝向跨度约 121.8°，不支持反复完整 360° 的表述 |\n| hard/015，step 46–115 | p12 描述多次 360° 扫视；p13 的依据明确说卡住，仍给搜索正例 | 朝向跨度约 91.9°；分类与其自身“纯脱困”解释需要重新核对 |\n| medium/011 | p12 JSON 声称没有碰撞 | JSON 实际记录 13 个碰撞 step |\n\n[审计数值、区间和计算方法](evidence_audit.json)。角度跨度是将相邻记录角差按 2π 展开后取最大值减最小值，不是绝对转角之和，也不是首尾净转角。\n\n建议先按新口径审核 [16 条优先案例](review_priority.csv)，特别是卡住/脱困和模型依据失真的情况，再决定候选是否值得应用到另外 120 条。那 120 条仍未参与本轮调参。\n\n本轮借鉴了观察覆盖和新信息的探索视角，但位置重复不等于观察信息重复；这些轨迹级规则是本项目的操作性定义，不是论文提供的现成标签标准。参考：[Learning Exploration Policies for Navigation](https://arxiv.org/abs/1903.01959)、[Frontier-Based Exploration](https://www.cs.cmu.edu/~motionplanning/papers/sbp_papers/integrated2/yamauchi_frontier_explor.pdf)。\n\n'
 text+='## 审核与复现入口\n\n- [按案例集中对照全部版本](case_review/index.md)\n- [优先复核列表](review_priority.csv)\n- [全部指标和平均耗时](leaderboard.csv)\n- [详细耗时和 token 数](timing_summary.csv)\n- [20 个 PBS 作业退出核验](pbs_completion.json)\n- [综合排名](final_ranking.csv)\n- [统计与完成核验](final_ranking.json)\n- [冻结人工参考](human_reference.json)\n- [历史中文版本在同一 51 条上的参考结果](historical_baselines51.json)\n- [研究来源及其使用边界](research_sources.json)\n\n'
 text+='每个 pXX 目录保留全部实际 request.txt、response.txt、result.json 和审核报告；templates/ 保存可直接修改的完整英文指令模板，JSON 使用占位符，PNG 需单独作为图片附件发送。各轮设计理由在 wave2_design.json、wave3_design.json、wave4_design.json。\n'
 (ROOT/'summary.md').write_text(text)
 index=ROOT/'index.md';old=index.read_text();link='[最终汇总与建议入口](summary.md) · [逐案例对照](case_review/index.md)\n\n'
 if link not in old:index.write_text(link+old.replace('结果链接在对应作业完成后可用。','20 个正式实验已完成。'))
 print(json.dumps(dict(responses=len(records),best={k:v['prompt_id'] for k,v in best.items()},top_overall=rankings[:5],priority_cases=len(priority),source_annotations_changed=changed),ensure_ascii=False,indent=2))

if __name__=='__main__':main()
