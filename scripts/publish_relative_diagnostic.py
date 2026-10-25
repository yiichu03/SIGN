#!/usr/bin/env python3
"""Build the compact GitHub discussion bundle; does not commit or push."""
import json
import subprocess
import argparse
from collections import Counter
from pathlib import Path
from research_publication import Publication, audit_pilot, require

BASE=Path(__file__).resolve().parents[1]
DATA=BASE/'results/qwen_diagnostic'
PILOT=DATA/'pairwise_pilot_20261013'
WORKTREE=BASE.parent/'SIGN-SRU-reward-review'
OUT=WORKTREE/'docs/research/qwen_relative_diagnostic_2026-10-13'
PUBLICATION=None
LEGACY_DOCUMENTS=(Path('AGENTS.md'),Path('docs/qwen_offline_diagnostic.md'),Path('docs/hm3d_v02_eval.md'))

def add_workspace_snapshot(publication,workspace,output):
    """Export the four maintained root documents; retain retired snapshot docs."""
    for name in Publication.workspace_documents:
        source=workspace/name
        require(source.is_file(),f'Missing workspace document: {source}; no files written.')
        publication.add(output/'workspace'/name,source.read_bytes())
    for relative in LEGACY_DOCUMENTS:
        archived=output/'code'/relative
        require(archived.is_file(),f'Missing legacy snapshot document: {archived}; preserve the archive.')
        publication.add(archived,archived.read_bytes())

def dump(p,d):
    write(p,json.dumps(d,ensure_ascii=False,indent=2)+'\n')

def write(p,data):
    PUBLICATION.add(p,data)

def copy(src,dest):
    write(dest,src.read_bytes())

def main(check_only=False):
    global PUBLICATION
    branch=subprocess.check_output(['git','symbolic-ref','--short','HEAD'],cwd=WORKTREE,text=True).strip()
    remote=subprocess.check_output(['git','remote','get-url','origin'],cwd=WORKTREE,text=True).strip()
    require(branch=='docs/qwen-reward-review-20261013','Wrong publication branch; no files written.')
    require(remote in ('git@github.com:yiichu03/SIGN-SRU.git','https://github.com/yiichu03/SIGN-SRU.git'),'Wrong publication origin; no files written.')
    audit=audit_pilot(PILOT)
    PUBLICATION=Publication(OUT)
    add_workspace_snapshot(PUBLICATION,BASE.parent,OUT)
    # Text/code snapshot of the actual SIGN checkout; never overwrite SRU code.
    tracked=subprocess.check_output(['git','ls-files'],cwd=BASE,text=True).splitlines()
    selected={Path(p) for p in tracked if Path(p).suffix in ('.py','.yaml','.yml','.md','.txt','.sh','.cfg','.toml','.msg','.launch') and not (set(Path(p).parts)&Publication.forbidden_parts)}
    for directory in ('src','exp_config','deployment'):
        selected.update(p.relative_to(BASE) for p in (BASE/directory).rglob('*') if p.is_file() and
                        p.suffix in ('.py','.yaml','.yml','.md','.txt','.sh','.cfg','.toml','.msg','.launch') and
                        not (set(p.relative_to(BASE).parts)&Publication.forbidden_parts))
    selected.update(p.relative_to(BASE) for p in (BASE/'scripts').glob('*') if p.suffix in ('.py','.pbs','.sh'))
    selected.update(p.relative_to(BASE) for p in (BASE/'docs').glob('*.md'))
    selected.update([Path('src/trajectory_diagnostic.py'),Path('constraints-hm3d.txt'),Path('.gitignore')])
    selected.difference_update(LEGACY_DOCUMENTS)
    for p in sorted(selected):copy(BASE/p,OUT/'code'/p)
    patch=subprocess.check_output(['git','diff','HEAD','--','src/policy.py','src/trainer.py'],cwd=BASE)
    write(OUT/'code/local_sign_changes.patch',patch)
    write(OUT/'code/SNAPSHOT.md','''# Actual SIGN evaluation/diagnostic code snapshot

This directory contains the server SIGN checkout's source/configuration plus local diagnostic scripts. It is separate from SIGN-SRU's repository-root training implementation. Source baseline: Zichen-Yan/SIGN commit 21274be. local_sign_changes.patch records the two modified tracked Python files; the added trajectory recorder and scripts are included in full. These scripts were used for evaluation and offline diagnosis, not policy training.

Checkpoints, scenes, camera images and installed environments are not included. Paths in PBS files are the actual server paths. The parent report identifies completed experiments versus pending work. The archived original README and docs describe earlier stages and may contain older status statements.

Since the workspace documentation migration, code/AGENTS.md and the two code/docs Markdown files retain their previously published bytes as historical documentation. Current server workspace rules, status, runbook and append-only operation log are exported under ../workspace/; start with [current status](../workspace/STATUS.md). These legacy documents are not the current server instructions.

Pairwise entry points: scripts/prepare_pairwise_diagnostic.py, scripts/qwen_pairwise_diagnostic.py, scripts/qwen_pairwise_diagnostic.pbs. Run from a reconstructed SIGN checkout with the documented environment and local results layout. This snapshot is for inspection/reproduction; it is not an instruction to overwrite SIGN-SRU's src directory.
''')
    copy(Path.home()/'qwen_relative_redundancy_guidance_20261013.md',OUT/'guidance_20261013.md')
    public=OUT/'pilot'
    for name in ['human_labels_frozen.md','human_labels_frozen.json','manifest.json','requests.json','protocol.md','submission.json','model_run.json','comparison.json','model_review.md','decision_diagnostics.json','decision_diagnostics.md']:
        if (PILOT/name).exists():copy(PILOT/name,public/name)
    # Keep the byte-identical human table under both filenames so its links work.
    copy(PILOT/'human_labels_frozen.md',public/'human_labels.md')
    m=json.loads((PILOT/'manifest.json').read_text())
    unique=set()
    for pair in m['pairs']:
        src=PILOT/pair['id'];dst=public/pair['id']
        for name in ('A_overview.png','B_overview.png','A_motion.png','B_motion.png','comparison.gif'):
            copy(src/name,dst/name)
        text=f'# {pair["id"]}\n\n[返回](../README.md) · [冻结人工判断](../human_labels.md)\n\nA: `{pair["A"]}`；B: `{pair["B"]}`。\n\n'
        text+='## 同步轨迹动画（人工查看）\n\n![同步轨迹](comparison.gif)\n\n每5步一帧，空间比例相同；蓝线为走过的路径、橙线为最近约5步，红圈为该步碰撞。较短轨迹结束后保持终点，标注 ENDED。\n\n'
        for side in 'AB':
            case=pair[side];unique.add(case)
            target=public/'trajectories'/case
            copy(src/f'{side}_waypoints.json',target/'waypoints.json')
            copy(src/f'{side}_evidence.json',target/'evidence.json')
            text+=f'## {side}\n\n![全程]({side}_overview.png)\n\n![运动事实]({side}_motion.png)\n\n[完整逐步 JSON](../trajectories/{case}/waypoints.json) · [计算事实](../trajectories/{case}/evidence.json)\n\n'
        text+='本地人工审核还可见稀疏 RGB、目标图和原始场景轨迹图；这些场景图像没有纳入此轻量公开包。Qwen A0/A1 均不接收这些额外图像。白底图不含墙体，不支持推断未显示的障碍与信息增益。\n'
        write(dst/'review.md',text)
    for src in (PILOT/'model_requests').glob('*/*'):
        if src.name in ('request.txt','input.json','response.txt','result.json'):
            copy(src,public/'model_requests'/src.parent.name/src.name)
    text='# 24 对成对诊断\n\n[冻结人工判断](human_labels.md) · [原始参考及哈希](human_labels_frozen.json) · [协议](protocol.md) · [选择清单](manifest.json) · [实际请求清单](requests.json)\n\n'
    text+='目的性挑选的开发案例，包含已知分歧、卡住/重复搜索混淆、正常返回和同为 CLEAR 的比较。不能用来估计总体冗余发生率。每对为同任务轨迹，部分轨迹重复出现在不同对中。\n\n'
    text+='图片、GIF、完整 waypoint JSON 和计算事实均可直接查看；原始数据按轨迹去重。实际 request.txt 原样保存，input.json 中的绝对路径是服务器运行记录；其中图片对应各 pair 页面中的 A_overview.png/B_overview.png，交换条件需按 shown_as 和文件名核对。人工记录没有传给模型。\n\n'
    text+='| 配对 | A | B | 审核 | A0 输入 | A1 输入 |\n|---|---|---|---|---|---|\n'
    for p in m['pairs']:
        key=p['id'];text+=f'| {key} | {p["A"]} | {p["B"]} | [图与动画]({key}/review.md) | [JSON](model_requests/{key}_A0_normal/request.txt) | [图＋事实](model_requests/{key}_A1_normal/request.txt) |\n'
    if (PILOT/'comparison.json').exists():
        text+='\n[严格统计](comparison.json) · [可读判断辅助分析](decision_diagnostics.md) · [逐回答审核](model_review.md)。两种统计口径分开，辅助提取不修复或替换原始回答。\n'
    else:
        text+='\n模型完成后发布 comparison.json 与 model_review.md；请以最新状态文件为准，不能把准备好的输入视为已经得到结果。\n'
    write(public/'README.md',text)
    # Historical prompt search: all 20 templates and all 3,600 outputs, without
    # repeating full trajectory inputs in each request.
    history=OUT/'history/prompt_iteration';old=DATA/'prompt_iteration'
    for name in ['summary.md','final_ranking.csv','final_ranking.json','leaderboard.csv','leaderboard.json','timing_summary.csv','human_reference.json','protocol.json','scope_decision.json','evidence_audit.json','historical_baselines51.json','review_priority.csv','pbs_completion.json','research_sources.json']:
        copy(old/name,history/name)
    for sub in ('prompts','templates'):
        for f in (old/sub).glob('*'):
            if f.is_file():copy(f,history/sub/f.name)
    output_count=0;case_comparison={}
    for i in range(1,21):
        key=f'p{i:02d}';records=[]
        for f in sorted((old/key).glob('val_*/episode_*/*/result.json')):
            records.append(dict(result=json.loads(f.read_text()),raw_response=(f.parent/'response.txt').read_text()))
        require(len(records)==180,f'{key}: expected 180 historical answers; do not publish a truncated archive.')
        output_count+=len(records)
        for record in records:
            result=record['result'];parsed=result['parsed']
            case_comparison.setdefault(result['case'],{}).setdefault(key,{})[result['mode']]=parsed['label'] if parsed else 'INVALID'
        dest=history/key
        write(dest/'outputs.jsonl',''.join(json.dumps(row,ensure_ascii=False)+'\n' for row in records))
        for name in ('comparison.csv','summary.json','diagnostics.json','run.json'):
            copy(old/key/name,dest/name)
        write(dest/'index.md',f'# {key}\n\n[Prompt](../prompts/{key}.json) · [统计](summary.json) · [逐例比较](comparison.csv) · [原始回答与运行记录](outputs.jsonl) · [诊断](diagnostics.json)\n\n保存 {len(records)} 个正式回答。旧完整请求中的逐步输入未重复上传；原始 request SHA256 保存在结果中。本地仍保留全部输入。\n')
    case_index='# 旧60条：按案例查看20个prompt\n\n此轻量索引保留全部标签并链接原始回答；旧60条图片/GIF仍在服务器，没有重复上传。人工原文见[旧审核记录](../../human_review2_notes.md)。\n\n'
    for case,comparisons in sorted(case_comparison.items()):
        path=history/'case_review'/f'{case}.md'
        case_index+=f'- [{case}]({case}.md)\n'
        body=f'# {case}\n\n[返回](../index.md) · [冻结旧人工参考](../../human_reference.json)\n\n| Prompt | PNG | JSON | PNG+JSON | 全部原始回答 |\n|---|---|---|---|---|\n'
        for key,values in sorted(comparisons.items()):
            body+=f'| {key} | {values.get("image_only","缺失")} | {values.get("json_only","缺失")} | {values.get("image_json","缺失")} | [JSONL](../../{key}/outputs.jsonl) |\n'
        write(path,body)
    write(history/'case_review/index.md',case_index)
    # Preserve the original human prose separately from generated interpretations.
    notes='# 原60条 review2 人工复核原文\n\n按原文件的人工作答区逐字摘录；旧口径与新“只计重复搜索”口径可能不同。\n\n'
    for p in sorted((DATA/'graded60').glob('val_*/episode_*/review2.md')):
        original=p.read_text();tail=original.split('## 人工复核',1)[1] if '## 人工复核' in original else '未找到人工复核区'
        notes+=f'## {p.parent.relative_to(DATA/"graded60")}\n'+tail+'\n'
    require(len(list((DATA/'graded60').glob('val_*/episode_*/review2.md')))==60,'Expected all 60 original human review pages.')
    write(OUT/'history/human_review2_notes.md',notes)
    for name in ('timing_summary.csv','timing_summary.json'):
        copy(DATA/'graded60'/name,OUT/'history/followup'/name)
    for name in ('case_comparison.csv','summary.json'):
        copy(DATA/'graded60/analysis_followup'/name,OUT/'history/followup'/name)
    # Inventory all formal executions, distinguishing executions from tasks.
    inventory=[]
    for dataset,pattern in [('graded60','val_*/episode_*/waypoints.json'),('additional120','val_*/episode_*/waypoints.json'),('group8_p12','group_*/episode_*/waypoints.json')]:
        for p in sorted((DATA/dataset).glob(pattern)):
            d=json.loads(p.read_text());row=dict(dataset=dataset,case=str(p.parent.relative_to(DATA/dataset)),scene_id=d['scene_id'],episode_id=d['episode_id'],steps=len(d['waypoints']))
            for name,field in [('metrics.json','navigation_metrics'),('codex_review.json','ai_review')]:
                if (p.parent/name).exists():row[field]=json.loads((p.parent/name).read_text())
            inventory.append(row)
    dump(OUT/'history/trajectory_inventory.json',inventory)
    require(dict(Counter(r['dataset'] for r in inventory))=={'graded60':60,'additional120':120,'group8_p12':80},'Formal trajectory inventory is incomplete or changed; inspect before publishing.')
    group=DATA/'group8_p12';group_public=OUT/'history/group8_p12'
    for name in ('comparison.json','comparison.csv','pairs.csv','qwen_run.json','completion.json','rationale_numeric_checks.json'):
        copy(group/name,group_public/name)
    for name in ('method','interpretation','rationale_audit'):
        copy(group/f'{name}.md',group_public/f'{name}.txt')
    group_outputs=[]
    for result in sorted(group.glob('group_*/episode_*/qwen_p12/result.json')):
        group_outputs.append(dict(case=str(result.parent.parent.relative_to(group)),result=json.loads(result.read_text()),
                                  raw_response=(result.parent/'response.txt').read_text()))
    require(len(group_outputs)==80 and json.loads((group/'qwen_run.json').read_text())['status']=='complete','Expected all 80 completed group8 answers.')
    write(group_public/'outputs.jsonl',''.join(json.dumps(row,ensure_ascii=False)+'\n' for row in group_outputs))
    for source in sorted((group/'single_control').rglob('*')):
        if source.is_file() and source.name in ('request.txt','response.txt','result.json','results.json'):
            copy(source,group_public/'single_control'/source.relative_to(group/'single_control'))
    write(group_public/'README.md','''# 同任务八条独立评分历史索引

10 个任务各执行 8 次，共 80 条轨迹；p12 JSON-only 在 batch8 中独立判断每条，未直接比较完整八条。参考是 AI 初审，不是人工真值；相对分数没有参与 PPO 更新。

[统计](comparison.json) · [逐轨迹比较](comparison.csv) · [组内关系](pairs.csv) · [全部 80 个原始回答及结果](outputs.jsonl) · [运行记录](qwen_run.json) · [完成记录](completion.json)。

[原方法全文](method.txt) · [原解释全文](interpretation.txt) · [依据审计全文](rationale_audit.txt) · [数值核查](rationale_numeric_checks.json) · [两条标准单条对照](single_control/results.json)。原 Markdown 按字节保存在 txt 文件中，其服务器审核链接不代表公开包包含 RGB。

历史完整长请求与轨迹仍保存在服务器，JSONL 保留每条结果中的 request SHA256；两条单条对照另保存实际请求、原始回答和结果。
''')
    labels=json.loads((PILOT/'human_labels_frozen.json').read_text())['labels']
    counts=dict(Counter(v['preference'] for v in labels.values()))
    state=json.loads((PILOT/'model_run.json').read_text()) if (PILOT/'model_run.json').exists() else dict(status='submitted_waiting_for_model_start')
    completed=len(list((PILOT/'model_requests').glob('*/result.json')))
    status=dict(snapshot_at=PUBLICATION.timestamp,job='1455625.stdct-mgmt-02',model_run=state,completed_requests=completed,planned_requests=64,human_counts=counts,unique_pilot_trajectories=len(unique),history_outputs=output_count,trajectory_inventory_counts=dict(Counter(r['dataset'] for r in inventory)))
    dump(OUT/'status.json',status)
    # Actual common template, without any trajectory data or review labels.
    first_request=json.loads((PILOT/'requests.json').read_text())[0]['id']
    write(OUT/'pairwise_prompt.txt',(PILOT/'model_requests'/first_request/'request.txt').read_text().split('\nINPUT:',1)[0])
    summary=audit['summary']
    rows=''
    for mode in ('A0','A1'):
        s=summary[mode]
        rows+=f"| {mode} | {s['strict_valid']}/24 | {s['strict_agreement']}/24 | {s['readable_agreement']}/24 | {s['readable_swap_consistent']}/{s['readable_swap_valid']} |\n"
    write(OUT/'README.md',f'''# Qwen 相对重复搜索研究入口

更新：{status['snapshot_at']}。

## 当前研究问题

Qwen 能否可靠比较同一 ImageNav 任务、起点和目标的多次执行，提供额外重复搜索的相对反馈？HM3D v0.2 验证场景与现有 SIGN checkpoint；已有奖励负责成功和任务进展。纯卡住、碰撞、脱困及普通分支返回不自动计为重复搜索。当前没有 Qwen 辅助 PPO 更新或训练收益。

## 最新实验状态与结论

用户在 2026-10-14 暂定 p12 JSON-only 对同任务 8 条轨迹独立分级、再计算 batch 内相对分数的思路：NONE/SOME/CLEAR 对应 0/1/2，同级保留并列，未知不赋零分。group_05 的初步人工观察支持暂时采用此思路，尚未构成完整冻结人工参考或训练收益证据。006 按可读 CLEAR 纳入的临时排序与原严格统计分开；[已确认决策](workspace/STATUS.md#已确认的研究决策) · [采样方法](workspace/RUNBOOK.md#轨迹采集与-qwen-诊断入口)。

2026-10-13 成对试验已完成：24 对复用 {len(unique)} 条轨迹，A0 双完整 JSON、A1 双概览图＋计算事实；48 个正常请求与 16 个顺序互换，共 **{completed}/64**。运行状态 **{state['status']}**；[实际运行记录](pilot/model_run.json)、[同步状态](status.json)。人工参考原样冻结：A 更少 {counts['A_LESS']}、B 更少 {counts['B_LESS']}、并列 {counts['TIE']}；pair_04 的理由歧义保留。

| 输入 | 完整合法 JSON | 严格人工一致 | 可读字段一致 | 可读顺序互换一致 |
|---|---:|---:|---:|---:|
{rows}
A1 正常展示中 {summary['A1']['readable_distribution']['A_LESS']}/24 次选 A；始终并列即可匹配 13/24。部分理由与选择反向，仍有把几何匹配或受困归为搜索的问题。当前比较尚不能提供可靠奖励。严格统计与可读字段提取分开，后者不修复 JSON、不验证理由。

[全部 24 对证据](pilot/README.md) · [64 个实际请求清单](pilot/requests.json) · [冻结人工参考](pilot/human_labels_frozen.md) · [严格统计](pilot/comparison.json) · [辅助诊断](pilot/decision_diagnostics.md) · [原始回答与人工复核栏](pilot/model_review.md)。输入和回答按字节保存；人工额外可见稀疏 RGB，模型没有。目的性选择的配对不能用于估计总体冗余发生率。

## 代码与研究记录位置

实际运行代码在服务器 `SIGN/`，对应 [代码快照](code/SNAPSHOT.md)、[源码](code/src/)、[脚本](code/scripts/)。SIGN-SRU 自身的 SRU 训练代码仍在仓库根目录 `src/`；代码快照保存在本研究目录 `code/`，两者各自维护。

[当前工作区状态](workspace/STATUS.md) · [操作与 debug 日志](workspace/WORKLOG.md) · [运行手册](workspace/RUNBOOK.md) · [工作规则](workspace/AGENTS.md)。四文档维护源在服务器 liuyi 根目录，这里是发布副本；WORKLOG 仅追加。文中服务器绝对路径用于定位未纳入公开包的本地资源。

[历史研究记录](code/docs/qwen_offline_diagnostic.md) · [历史目录与 Git 结构](code/docs/qwen_offline_diagnostic.md#本地目录与-git-结构) · [历史环境说明](code/docs/hm3d_v02_eval.md)保留发布时原文，不作为当前工作区入口。SIGN 的 origin 是 `yiichu03/SIGN`；本研究发布入口仍是 SIGN-SRU 的 `docs/qwen-reward-review-20261013` 分支。

## 下一步

先继续人工抽查同任务组，检验暂定 p12 粗分组的方向、并列与搜索／脱困边界；输出长度调整稍后讨论。约 40 个短输出、顺序互换、自比较和候选匹配列表移除对照请求仍为备选提议，尚未实现或提交。完整八条直接比较、相对奖励与训练接口均待验证，不强制八个不同名次。

## 历史实验索引

- [20 个 prompt、全部 {output_count} 个回答和统计](history/prompt_iteration/summary.md) · [逐案例索引](history/prompt_iteration/case_review/index.md) · [p12 原模板](history/prompt_iteration/templates/p12_json_only.txt)：旧开发集 49/51 二元一致不能外推为独立测试或成对能力。
- [10 组×8 条独立 p12 评分、80 个原始回答及单条对照](history/group8_p12/README.md)：参考为 AI 初审，不是人工真值；batch8 不代表直接比较完整八条。
- [260 条正式执行库存](history/trajectory_inventory.json) · [60 条原人工复核](history/human_review2_notes.md) · [历史单条／batch 耗时](history/followup/timing_summary.csv)。
- [历史研究报告](../qwen_redundancy_reward_2026-10-13/README.md) · [当时研究指导原文](guidance_20261013.md)。历史过程以当时记录为准，最新状态见上文。

## 一键同步

在服务器任意目录运行：

```bash
bash /scratch/e1538633/liuyi/SIGN/scripts/sync_research_github.sh
```

追加 `--check-only` 可只检查和预览。脚本核对目标分支、remote、远端历史及工作区，再发布、显示变更、检查哈希／链接、提交和普通 push；材料没有变化时不更新快照时间或创建空提交。已有记录变化、缺失、未完成 Git 操作或历史分歧会停止，保留现场；不自动合并、重置、清理或删除文件。

[文件 SHA256 清单](publication_manifest.json)。包内包含代码、统计、人工参考、当前完整请求／回答及必要轨迹图；不包含权重、原始 HM3D 场景／RGB、Python 环境或缓存。历史重复长请求和大体积中间材料保留在服务器。同步不运行模型、采集或训练。
''')
    audit.update(history_outputs=output_count,group8_outputs=len(group_outputs))
    base_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=BASE,text=True).strip()
    PUBLICATION.finish(base_commit,audit,check_only=check_only)

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check-only',action='store_true',help='Validate and show planned changes without writing files.')
    main(check_only=parser.parse_args().check_only)
