"""Generate a small, source-hashed research snapshot; never submit jobs."""
import argparse
import csv
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import statistics

ROOT = Path('/scratch/e1538633/liuyi')
HERE = Path(__file__).resolve().parent
DEV = ROOT / 'SIGN-qwen-candidate-recovery'
PACKAGE = Path('docs/experiments/inference-recovery/iteration_20261108')
DISCUSSION = ROOT/'logs/github_discussion_update_20261108'

PURPOSES = {
    'main':'作者基线，保持不动；跟踪upstream不改变默认push目标',
    'phase1/imagenav-qwen-diagnostics':'第一阶段轨迹采集与Qwen诊断归档',
    'phase2/exploration-reward-try':'原版阶段二起点，当前与main同提交',
    'phase2/frozen-visual-encoder':'仅加载冻结公开visual_encoder的训练基线',
    'phase2/frozen-rollout-coverage':'覆盖256奖励；远端包含后续资料发布',
    'phase2/frozen-coverage-settle32':'覆盖32结算奖励，PPO rollout仍256',
    'phase2/qwen-topdown-judge':'独立单图top-down评分、2B/9B离线诊断',
    'phase2/qwen-history-window':'128/256历史图离线对照，固线版本453179c',
    'phase2/qwen128-reward-beta01':'Qwen128 beta0.1辅助奖励原训练及资料',
    'phase2/qwen-beta003-geometry128':'A Qwen128、B Qwen256 beta0.03和C几何128共用源码',
    'phase2/continue-coverage256-20261103':'覆盖256 weights continuation，原预算续跑',
    'phase2/continue-coverage32-20261103':'覆盖32 weights continuation，原预算续跑',
    'phase2/continue-qwen128-beta01-20261103':'Qwen128 beta0.1续跑',
    'phase2/continue-qwen-ablation-20261103':'A/B/C三组共用续跑代码；当前只有B训练仍R',
    'phase2/inference-recovery-harness':'最早74.240M冻结基线上的推理恢复',
    'phase2/inference-recovery-active-view':'早期主动扫描与Qwen问题排查',
    'phase2/inference-coverage256-recovery':'切换到正确125.952M覆盖底座，旧规则完整验证',
    'phase2/qwen-candidate-recovery':'当前推理框架开发与资料发布；f0e为已测运行版，下一轮先讨论',
    'experiment/habitat-gs-imagenav':'独立Habitat-GS适配及评估，当前非Gibson主线',
}


def branches_markdown(inventory):
    out='# 分支与工作树盘点\n\n盘点时间：'+inventory['captured_at']+'。表中HEAD为本次资料提交前截面；当前资料分支随后会新增文档提交，运行代码仍固定f0e093c。\n\n'
    out+='SIGN与SIGN-SRU是两个Git仓库。一个分支可承载多个超参数实验，detached工作树是固定提交快照，不额外算命名分支。SIGN目录当前检出冻结视觉分支；作者main仍保留。\n\n'
    for name,repo in inventory['repositories'].items():
        out+=f"## {name}\n\n本地{repo['named_branch_count']}个命名分支，origin{repo['origin_branch_count']}个；{len(repo['worktrees'])}个工作树，其中{repo['detached_worktree_count']}个detached。\n\n"
        out+='|分支|用途|本地HEAD|origin HEAD|命名工作树|\n|---|---|---|---|---|\n'
        for b in repo['branches']:
            purpose=PURPOSES.get(b['name'],'历史研究文档归档')
            if name=='SIGN-SRU':
                purpose={'main':'学长SRU基线，保持ba3bb4a',
                    'phase1/imagenav-qwen-diagnostics':'SRU研究归档；根src仍为SRU，docs中的SIGN快照不能覆盖它',
                    'docs/qwen-reward-review-20261013':'较早Qwen奖励研究文档归档'}[b['name']]
            branch=f"[{b['name']}](https://github.com/{repo['repository']}/tree/{b['name']})"
            remote='—' if b['origin_commit'] is None else f"[{b['origin_commit'][:7]}](https://github.com/{repo['repository']}/tree/{b['origin_commit']})"
            paths=', '.join('`'+Path(p).name+'`' for p in b['worktrees']) or '当前无命名工作树'
            out+=f"|{branch}|{purpose}|`{b['local_commit'][:7]}`|{remote}|{paths}|\n"
        detached=[x for x in repo['worktrees'] if x['branch'] is None]
        if detached:
            out+='\n### 固定提交工作树\n\n'
            out+='|目录|HEAD|用途|\n|---|---|---|\n'
            for item in detached:
                folder=Path(item['path']).name
                role='资料发布快照' if 'publication' in folder else '只读原生评估' if folder=='SIGN-coverage-eval' else '迭代实验快照，不是新分支'
                out+=f"|`{folder}`|`{item['commit'][:7]}`|{role}|\n"
        out+='\n'
    out+='## 本地与远端差异\n\n4个SIGN分支的本地/远端HEAD不同：Habitat-GS、frozen-rollout-coverage、qwen128-reward-beta01、qwen-beta003-geometry128。逐文件审计确认差异只在README/docs：运行目录保留源码提交，远端前进到资料提交；不要为同步文档把资料pull进运行目录。其他本地命名分支与origin在盘点时HEAD一致，没有origin-only分支。\n\n'
    out+='默认push仅yiichu03/SIGN；SIGN-SRU仍使用自己的yiichu03/SIGN-SRU。SIGN upstream=Zichen-Yan/SIGN，只有用户明确要求才推学长仓库。当前main跟踪upstream/main不代表默认向upstream推送。habitat-lab等依赖不计入上述项目分支，也不随本次发布。\n\n'
    out+='原始盘点、提交关系与32+2工作树源码守卫见[evidence](evidence/logs/github_discussion_update_20261108/branch_inventory.json)和[差异复核](evidence/logs/github_discussion_update_20261108/branch_relationship_audit.json)。本次不创建/切换/删除分支，不修改训练源码或预算。\n'
    return out


def digest(data):
    return hashlib.sha256(data).hexdigest()


def build():
    destination = DEV / PACKAGE
    destination.mkdir(exist_ok=True)
    mapping, inputs, rounds = {}, {}, []

    def copy(source):
        source = source.absolute()
        assert source.is_relative_to(ROOT)
        target = destination / 'evidence' / source.relative_to(ROOT)
        raw = source.read_bytes()
        assert len(raw) < 2_000_000, source
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
        mapping[str(source)] = target
        inputs[str(target.relative_to(destination))] = dict(
            source=str(source), bytes=len(raw), sha256=digest(raw))
        return target

    for name in ['tasks.json', 'selection.json', 'completed_rounds_20261108T053319.csv',
                 'completed_rounds_20261108T053319.json', 'completed_90degree_view_audit.json']:
        copy(HERE / name)
    extension = HERE / 'expanded_v2'
    for name in ['tasks.json', 'selection.json', 'preparation_audit.json',
                 'diagnostic_amendment.json', 'release_protocol_revision2.json',
                 'native_parallelism_audit.json', 'causal_cases_motion_audit.json',
                 'submit_iteration.py', 'dispatch_iteration.py', 'dispatch_iteration.pbs',
                 'orchestration_manifest.json', 'control_revision3.json']:
        copy(extension / name)
    for name in ['consensus_veto_cpu_tests.log', 'consensus_qwen_regression.log']:
        copy(HERE / name)
    copy(HERE/'audit_release_v2.py')
    old_full=ROOT/'logs/sign_inference_coverage256_20261108/rule_full'
    for name in ['comparison.json','completed_review_20261108.json','submission.json']:
        copy(old_full/name)
    initial=ROOT/'logs/sign_qwen_candidate_recovery_20261108/attempt1'
    for name in ['comparison.json','completed_review_20261108.json','submission.json']:
        copy(initial/name)
    training_sources=json.loads((DISCUSSION/'training_sources.json').read_text())
    latest_training=Path(training_sources['latest_snapshot'])
    training=json.loads((latest_training/'readout.json').read_text())
    training_summary=json.loads((latest_training/'summary.json').read_text())
    for name in ['prepare.py','branch_inventory.json','protected_trees.json',
                 'branch_relationship_audit.json','training_sources.json']:
        copy(DISCUSSION/name)
    for folder in ['recent_training','reference_scalars']:
        for path in sorted((DISCUSSION/folder).glob('*.csv')):
            copy(path)
    for snapshot in [Path(training_sources['previous_snapshot']),latest_training]:
        for name in ['readout.json','summary.json','validation.json']:
            copy(snapshot/name)
    copy(latest_training/'readout_script_at_execution.py')
    for batch in [HERE / f'round{i:02}' for i in range(1, 7)] + [
            extension / name for name in ['expanded01', 'expanded03',
                'expanded03_repeat', 'expanded03_confirmation', 'expanded03_full',
                'focused_regression', 'consensus_probe']]:
        if not (batch / 'submission.json').exists():
            continue
        sub = json.loads((batch / 'submission.json').read_text())
        result_path = batch / 'iteration_result.json'
        result = json.loads(result_path.read_text()) if result_path.exists() else None
        stage_complete=result is not None
        if (batch/'regression_result.json').exists():
            stage_complete=bool(json.loads((batch/'regression_result.json').read_text())['completed'])
        if 'probe' in sub.get('stage','') and (batch/'probe/summary.json').exists():
            stage_complete=bool(json.loads((batch/'probe/summary.json').read_text())['technical_passed'])
        rounds.append(dict(round=batch.name, job_id=sub['job_id'], commit=sub['commit'],
            stage=sub.get('stage','known_case_regression'), completed=stage_complete,
            comparisons={} if result is None else {
                split: dict(episodes=v['episodes'], net_successes=v['net_successes'],
                    supported_rescues=v['supported_rescues'], harms=len(v['harms']),
                    cases={mode:dict(successes=round(case['episodes']*case['success_rate']),
                        success_rate=case['success_rate'], spl=case['spl'])
                        for mode,case in v['cases'].items()})
                for split,v in result['comparisons'].items()}))
        for name in ['submission.json', 'source_manifest.json', 'tasks.json',
                     'dispatch.json', 'iteration_result.json', 'regression_result.json',
                     'matched_control_identity_audit.json', 'walltime_amendment.json',
                     'no_intervention_identity_audit.json', 'repeat_identity_audit.json',
                     'general_identity_audit.json',
                     'release_authorization.json','status_at_release.json',
                     'version2_release_audit.json','completed_review_20261108.json']:
            if (batch / name).exists():
                copy(batch / name)
        for name in ['probe/summary.json', 'probe/recovered_from_top5.json']:
            if (batch / name).exists():
                copy(batch / name)
        if batch.name=='consensus_probe':
            for name in ['probe/scores.json','offline_direction_screen.json',
                         'preserve_clear_default_screen.json']:
                copy(batch/name)
        if batch.name=='focused_regression':
            for name in ['develop_comparison.json','develop_paired.csv']:
                copy(batch/name)
        if result is not None:
            for split in result['comparisons']:
                for name in [split+'_comparison.json', split+'_paired.csv']:
                    copy(batch / name)
                for mode in ['off','rule','qwen']:
                    folder = batch / (split+'_'+mode)
                    copy(folder / 'result.json')
                    for path in (folder/'episodes').glob('*.jsonl'):
                        copy(path)
                    for name in ['events.jsonl', 'summary.json', 'action_order.json']:
                        path = folder / 'native/recovery' / name
                        if path.exists():
                            copy(path)
            for name in ['probe/summary.json', 'probe/worker/verification.json',
                         'probe/worker/verification_inverse.json']:
                if (batch / name).exists():
                    copy(batch / name)
        if batch.name in ['expanded01','expanded03'] and result is not None:
            events = batch / 'develop_qwen/native/recovery/events.jsonl'
            for line in events.read_text().splitlines():
                event = json.loads(line)
                # All real deviations in both the negative and final development runs.
                if event['model'].get('differs_from_rule'):
                    for candidate in event['candidates']:
                        path = Path(candidate['image'])
                        assert digest(path.read_bytes()) == candidate['image_sha256']
                        copy(path)

    inventory=json.loads((DISCUSSION/'branch_inventory.json').read_text())
    (destination/'BRANCHES.md').write_text(branches_markdown(inventory))
    full_batch=extension/'expanded03_full'
    review=json.loads((full_batch/'completed_review_20261108.json').read_text())
    full_events=list(map(json.loads,(full_batch/'full_qwen/native/recovery/events.jsonl').read_text().splitlines()))
    cases='# 全量成败变化案例与审计\n\n全部8条SR变化都列出；人工原因/备注保持空白，自动前缀审计不是人工根因标签。仅5条有前缀支持的真实模型改向提供候选图；其他3条属于无本episode模型改向的变化。16份NPZ只含commands和poses，供事后核对，不是Agent输入。\n\n'
    cases+='|场景/任务|规则→Qwen成功|首次动作差异步|模型改向步|决定前前缀一致|\n|---|---|---:|---|---|\n'
    for item in review['success_changes']:
        name=item['scene']+'_'+item['episode_id']+'.npz'
        for mode in ['rule','qwen']:
            copy(full_batch/('full_'+mode)/'audit_traces'/name)
        cases+=f"|{item['scene']}/{item['episode_id']}|{int(item['rule_success'])}→{int(item['qwen_success'])}|{item['first_action_difference']}|{item['vlm_decisions']}|{item['prefix_until_decision_matches']}|\n"
    cases+='\n以下5条以成败改变和真实前缀为条件全部纳入，既含2条救回也含3条误伤，没有只挑成功图。输入图/完整正反概率/logits及模型回退信息见[原始事件](evidence/logs/qwen_recovery_iteration_20261108/expanded_v2/expanded03_full/full_qwen/native/recovery/events.jsonl)。\n\n'
    selected={(x['scene'],x['episode_id']) for x in review['success_changes'] if x['prefix_until_decision_matches']}
    for event in full_events:
        key=(Path(event['episode'][0]).stem,event['episode'][1])
        if key not in selected or not event['model'].get('differs_from_rule'):
            continue
        cases+='## '+key[0]+' / '+key[1]+'\n\n'
        paths={}
        for candidate in event['candidates']:
            path=Path(candidate['image']);assert digest(path.read_bytes())==candidate['image_sha256']
            paths[candidate['side']]=copy(path).relative_to(destination)
        cases+='|左：实际Qwen输入|右：实际Qwen输入|\n|---|---|\n'
        cases+='|![left]('+str(paths['left'])+')|![right]('+str(paths['right'])+')|\n\n'
        goal=event['view_files']['goal'];path=Path(goal['path']);assert digest(path.read_bytes())==goal['sha256']
        target=copy(path).relative_to(destination)
        cases+='[目标图：仅供人审，当前Qwen没有接收它]('+str(target)+')。模型只接收上面左右RGB，各自独立对话；没有GT地图/距离/碰撞输入。\n\n'
        cases+=f"决定步{event['decision_step']}，默认规则{event['model']['default_rule_choice']}，实际模型选择{event['choice']}（A左/B右）。\n\n"
        cases+='|候选方向|正问开放支持|反问开放支持|\n|---|---:|---:|\n'
        for side in ['left','right']:
            support=event['model']['evidence'][side]
            cases+=f"|{side}|{support[0]['support']:.6f}|{support[1]['support']:.6f}|\n"
        cases+='\n支持是三词条件概率的组合，不是导航成功概率。原始轨迹留服务器；本包包含上述8个任务的规则/Qwen commands+poses NPZ，可独立重算首次动作分歧及前缀。\n\n'
    (destination/'CASES.md').write_text(cases.rstrip()+'\n')

    for name in ['AGENTS.md', 'STATUS.md', 'RUNBOOK.md', 'WORKLOG.md']:
        mapping[str(ROOT/name)] = destination/'workspace'/name
    for name in ['AGENTS.md', 'STATUS.md', 'RUNBOOK.md', 'WORKLOG.md']:
        source, target = ROOT/name, destination/'workspace'/name
        raw = source.read_bytes()
        if name == 'WORKLOG.md':
            if target.exists():
                assert raw.startswith(target.read_bytes()), 'Append-only WORKLOG prefix'
            output = raw
        else:
            def portable(match):
                marker, label, url = match.groups()
                if url.startswith(('http:', 'https:', '#', 'mailto:')):
                    return match.group(0)
                path, sep, anchor = url.strip('<>').partition('#')
                absolute = Path(path) if path.startswith('/') else ROOT/path
                mapped = mapping.get(str(absolute))
                if mapped is None:
                    try:
                        candidate = DEV/absolute.relative_to(DEV)
                        if candidate.exists():
                            mapped = candidate
                    except ValueError:
                        pass
                if mapped is None:
                    return label+'（服务器：`'+str(absolute)+'`）'
                return marker+'['+label+']('+os.path.relpath(mapped,target.parent)+(sep+anchor if sep else '')+')'
            output = (re.sub(r'(!?)\[([^\]]*)\]\(([^)]+)\)', portable, raw.decode())).encode()
        target.parent.mkdir(exist_ok=True)
        target.write_bytes(output)
        inputs[str(target.relative_to(destination))] = dict(source=str(source),
            source_sha256=digest(raw), sha256=digest(output), bytes=len(output),
            encoding='verbatim' if name=='WORKLOG.md' else 'portable_links')

    snapshot = dict(recorded_at=datetime.datetime.now().astimezone().isoformat(timespec='seconds'),
        behavior_commit='f0e093c4d52c595c71f109d69cbf67ae7fbe3daa',
        checkpoint_steps=125952000, rounds=rounds,
        restrictions='Development reused for tuning; selected cases are not independent. Formal pending unless completed explicitly. Raw large trajectories and weights remain on server.')
    (destination/'results.json').write_text(json.dumps(snapshot,indent=2)+'\n')
    readme = '# SIGN现状与Qwen框架讨论：完整验证已完成\n\n'
    readme += '资料截面：'+snapshot['recorded_at']+'。行为固定提交`'+snapshot['behavior_commit']+'`；资料提交可以继续前进，运行快照保持不变。\n\n'
    readme += '[逐轮机器可读结果](results.json) · [文件SHA与服务器来源](inputs.json) · [当前STATUS生成副本](workspace/STATUS.md) · [追加式操作记录](workspace/WORKLOG.md)\n\n'
    readme += '[全部项目分支与工作树](BRANCHES.md) · [8条成败变化、实际输入与动作前缀](CASES.md)\n\n'
    readme += '**本轮只更新文档和证据，等待与用户进一步沟通；不修改恢复算法，不提交新PBS实验。** 用户更重视Qwen承担恢复决策，同观测/动作/步数预算下达到规则效果也有价值。后续可在讨论明确后并行多组对照，但当前占用少不等于已核实项目GPU-hour余额；提交前仍需核对项目许可/余额/队列约束。\n\n'
    readme += '## 已完成完整验证与贡献边界\n\n所有方法使用同一个125.952M覆盖256导航checkpoint。正式1532001和CPU1532002均Exit0，GPU用时2:17:44；三组各4200任务，原生4200位姿SHA完全复现参考。\n\n'
    readme += '|方法|成功条数|SR|SPL|平均碰撞|平均步数|\n|---|---:|---:|---:|---:|---:|\n'
    comparison=json.loads((full_batch/'full_comparison.json').read_text())
    for label,case in [('覆盖256原策略',comparison['cases']['off']),('旧无扫描规则',json.loads((old_full/'comparison.json').read_text())['cases']['rule']),('本轮匹配扫描规则',comparison['cases']['rule']),('本轮Qwen2B混合恢复',comparison['cases']['qwen'])]:
        readme+=f"|{label}|{round(case['success_rate']*4200)}|{100*case['success_rate']:.4f}%|{100*case['spl']:.4f}%|{case['mean_collisions']:.3f}|{case['mean_episode_steps']:.3f}|\n"
    readme += '\nQwen相对匹配规则描述性净多2/4200（SR+0.047619pp、SPL+0.002150pp）。但5救回/3误伤中，真实模型改向且决定前动作/位姿一致的只有**2救回、3误伤**；另3救回在该episode没有模型改向。并行batch/episode结束影响只是机制假设，尚未重放验证。原producer门True和full_completed回执原样保留；这个汇总门未扣除无改向救回，不能据True称稳定VLM收益。人工标签全部留空。[独立复核](evidence/logs/qwen_recovery_iteration_20261108/expanded_v2/expanded03_full/completed_review_20261108.json)。\n\n'
    readme += '## 当前逻辑与尚待讨论的问题\n\n当前正常动作由SIGN生成；16步窗口75%有前进意图且旋转补偿后RGB低变化时触发；24步扫描获得左右90度图，再选方向。规则第一次左、第二次右；Qwen在左右图上独立问通行/障碍，双问支持差>=.05同向才改默认，两问默认open最高则保持默认，证据不足回退规则。随后计划6步转向+8步前进（指令1.6m）再交回SIGN，冷却64步；每episode最多2次/76覆盖步，全部计入500，原STOP/masks/GRU保持。\n\n'
    readme += '当前151次完成评分中98次回退规则，53次采纳模型但仅23次真正改变规则方向。因此88.64%是混合框架成绩，尚不能证明Qwen独立承担决策也能同效。实际Qwen输入是左右相机RGB；目标图只给SIGN和人审，没有给当前Qwen，也没有完整历史。语义版selector总会返回左或右，Qwen不能选择本次不恢复；恢复后的RGB变化只记录，不用于验收/撤销/记忆失败方向。这些限制由现有代码可直接核查。\n\n'
    readme += '待沟通后再确定：①成功标准是独立VLM替代达到同效，还是混合系统追求增益；②给目标/近期观察/动作反馈的最小输入，以及图像布局偏置检查（旧整组拼图曾失败，不能原样复用）；③是否让Qwen选择左/右/继续SIGN，规则回退作为单独消融；④如何用实际可得视觉反馈核验恢复、记录失败方向，同时保持原预算；⑤同预算多方案并行和未用留出集如何预先固定。以上均为讨论题，**没有实现或排队**。\n\n'
    readme += '## 最新辅助reward训练\n\n此处是此前奖励训练，推理恢复使用固定模型。训练快照'+training['captured_at']+'，最近1M内原生50-update滑窗日志均值；不同步数不直接排名，不是val，日志末步不等于checkpoint步数。\n\n'
    readme += '|方法|日志百万步|近1M SR|近1M SPL|状态|\n|---|---:|---:|---:|---|\n'
    labels={'baseline':'冻结视觉基线','coverage256':'覆盖256','coverage32':'覆盖32','qwen01':'Qwen128 beta0.1','A':'A Qwen128 beta0.03','B':'B Qwen256 beta0.03','C':'几何128'}
    for key,label in labels.items():
        value=training_summary[key]
        state='运行' if value['state']=='R' else '用户暂停' if key=='C' else '用户停止' if key=='baseline' else '原PBS时限结束'
        readme+=f"|{label}|{value['step']/1e6:.3f}|{value['sr']:.2f}%|{value['spl']:.2f}%|{state}|\n"
    own=training['own_budget']['B']['3000000'];value=training_summary['B']
    readme+=f"\n当前只有B1511148运行，原预算约余{value['remaining_hours']:.2f}h。B相同{value['step']/1e6:.6f}M的近3M比较如下；最新1M SR相对前1M仍{value['sr_delta_previous1m']:+.2f}pp。13:02旧快照中B为86.47/48.25%，当前有所恢复，两个快照同时保留，不把短窗起伏当稳定提升。\n\n"
    readme+='|同预算近3M|SR|SPL|\n|---|---:|---:|\n'
    for key,label in [('baseline','冻结基线'),('coverage256','覆盖256'),('coverage32','覆盖32'),('B','Qwen256 beta0.03')]:
        value=own['runs'][key]
        readme+=f"|{label}|{value['metrics/success']:.4f}%|{value['metrics/spl']:.4f}%|\n"
    readme+='\nB两项高于同期两覆盖；对基线仍是SR更高、SPL更低。原训练与续跑优化器/reset历史不同，单种子和重叠训练窗不能作严格因果或val收益结论。完整1/2/3M正负窗口、CORE原数值近期CSV及原文件SHA在本包，完整TB与大日志保留服务器。\n\n'
    readme += '## 方法与控制\n\n'
    readme += '导航模型使用覆盖256的125,952,000步checkpoint；不重新训练，不把Qwen接入PPO奖励。原SIGN继续决策，只有RGB与实际动作历史出现持续受阻迹象时才触发。24个实际原地转向动作获取左右90度RGB；两张图独立输入Qwen3.5-2B，FP32/T=1，读取No/Unknown/Yes真实答案token logits。正问通行性与反问障碍物须同向支持，默认侧在两问中都判可通行时保持规则；其余证据不足回退匹配规则。最多两次恢复，每次90度转向及1.6m短尝试；连扫描最多76个覆盖动作都计入原500步，原STOP/masks/GRU保留。\n\n'
    readme += '比较原生off、同扫描/同动作/同触发器的rule，以及qwen。回退到规则和主动扫描的收益不能算作模型判断的额外贡献。Agent不读取GT pose、collision、distance或地图；这些仅供离线选题和事后前缀审计。\n\n'
    readme += '三候选softmax只是条件词概率，不是校准的通行或导航成功率；正反问来自同一模型，不按独立事件相乘。VLM职责限于局部受阻方向选择，不承担全局目标规划。\n\n'
    old=json.loads((old_full/'comparison.json').read_text())
    readme += '既有完整4200参考：off SR/SPL '+f"{100*old['cases']['off']['success_rate']:.4f}%/{100*old['cases']['off']['spl']:.4f}%"+'，旧不扫描规则 '+f"{100*old['cases']['rule']['success_rate']:.4f}%/{100*old['cases']['rule']['spl']:.4f}%"+'。旧规则与本轮主动扫描规则的动作预算不同，本轮已重跑匹配rule；两种规则分别报告。\n\n'
    readme += '## 全部迭代\n\n'
    readme += '初始e9e5c0f/1531403三组各280任务，四事件全回退规则，Qwen与匹配规则280条原始行/动作哈希全等，没有额外模型作用。后续改用真实No/Unknown/Yes词读出、独立RGB和开发迭代；这个零收益版本及其完整复核也保留在evidence中。\n\n'
    readme += '原24条开发诊断后，预先登记加入全部额外37条，合61条；扩展诊断改用单环境减少别的episode结束引起的组批干扰。正式4200仍原6环境，不混比不同N和不同任务集的绝对成绩。下表含负结果和看似正向却无因果支持的版本；同一开发数据被反复用于调试，不能当独立测试。\n\n'
    readme += 'N1与原N6并非逐轨迹相等：34条原生审计最大首动作差0.0015053、只有4条完整位姿哈希相等；具体底层数值来源未因果确定。61条虽然按旧N6失败诊断选择，新N1原生实际成功13条，所以本轮原生、规则、Qwen都重新配对跑，不把旧失败标签当本轮真实失败；小诊断也不替代原6环境正式协议。\n\n'
    readme += '|轮次/分组|N|规则成功|Qwen成功|净变化|前缀支持救回|误伤|规则SPL|Qwen SPL|\n|---|---:|---:|---:|---:|---:|---:|---:|---:|\n'
    for item in rounds:
        if not item['comparisons']:
            continue
        for split, comparison in item['comparisons'].items():
            if split == 'safety' and item['round'] not in ['expanded03','expanded03_repeat','expanded03_confirmation']:
                continue
            rule, qwen = comparison['cases']['rule'],comparison['cases']['qwen']
            readme += f"|{item['round']}/{split}|{comparison['episodes']}|{rule['successes']}|{qwen['successes']}|{comparison['net_successes']:+d}|{comparison['supported_rescues']}|{comparison['harms']}|{100*rule['spl']:.4f}%|{100*qwen['spl']:.4f}%|\n"
    readme += '\nround03在真实空白输入对照中暴露位置偏好，技术门失败，未跑导航。round06表面多1成功但没有模型改向/前缀支持，被拒绝。expanded01真实1救回4误伤，净-3，未放行；之后仅在开发上调整双问一致性和保留可通行默认。另5条已知案例短回归是事后选择的集成调试，不能另算5个独立样本。\n\n'
    readme += '## 固定版收益与边界\n\n'
    readme += '首次完整61开发：规则30/61→Qwen31/61，SPL19.3042%→19.4396%，1救回/0误伤。35事件中只有2条轨迹真正偏离规则；59条无偏离轨迹的所有原始字段与动作/位姿哈希精确相等。Swormville3040在模型决定前前缀一致，90步改向后123步成功，规则500步失败；Ribera1167仍成功但SPL68.3569%→54.6825%，效率代价保留。安全28均27成功且0触发，因此只验证未触发回归。人工原因列留空，AI描述不是人工真值；1个救回也不构成统计显著性。\n\n'
    current_events=extension/'expanded03/develop_qwen/native/recovery/events.jsonl'
    if current_events.exists():
        for event in map(json.loads,current_events.read_text().splitlines()):
            if not event['model'].get('differs_from_rule'):
                continue
            readme += '### 开发中真实改向：'+Path(event['episode'][0]).stem+' / '+event['episode'][1]+'\n\n'
            readme += '|左侧实际模型输入|右侧实际模型输入|\n|---|---|\n'
            paths={c['side']:mapping[c['image']] for c in event['candidates']}
            readme += '|![left]('+str(paths['left'].relative_to(destination))+')|![right]('+str(paths['right'].relative_to(destination))+')|\n\n'
            readme += '图中没有GT标注，左右图分别独立送模型；人工原因未填写。两问原始概率/logits和实际回退规则见对应events.jsonl。\n\n'
    readme += '开发与同版重复都须净成功>=1且至少1前缀支持救回。确认24、普通112和安全28用冻结版本检查；预登记版本2允许确认中性且其他组成功数不降时进入正式4200进一步检验，不把中性确认称独立优势，也没有承诺SPL不降。原旧门/False/dispatch不覆写，必要时另留版本2审计；确认成功数下降则不放行。完整val复用了开发选择来自的benchmark，不宣称完全未接触测试。\n\n'
    confirmation=next((r for r in rounds if r['round']=='expanded03_confirmation' and r['completed']),None)
    if confirmation:
        item=confirmation['comparisons']['confirm']
        rule,qwen=item['cases']['rule'],item['cases']['qwen']
        readme += f"冻结确认24：规则{rule['successes']}/24、Qwen{qwen['successes']}/24；SPL{100*rule['spl']:.4f}%→{100*qwen['spl']:.4f}%。成功数持平时明确称中性，SPL下降也保留；不以开发上的救回掩盖保留集尚无额外收益。\n\n"
    formal = next((r for r in rounds if r['round']=='expanded03_full'),None)
    if formal:
        readme += f"正式4200作业：**{formal['job_id']}**，固定`{formal['commit']}`，三个对照各4200/14场景/6环境/max500/seed100/hash0；"+('已完成，完整结果见results.json。' if formal['completed'] else '已提交，当前包没有完整最终成绩，不预测整体提升。')+'\n\n'
    else:
        readme += '当前资料截面尚未提交正式4200；待同版重复及冻结确认完成，不将开发门通过写成正式完成。\n\n'
    readme += '## 复现与审计\n\n'
    readme += '行为配置：[inference_semantic_consensus_veto90.yaml](../../../../src/config/inference_semantic_consensus_veto90.yaml)；提示：[通行性](../../../../scripts/prompts/recovery_semantic_forward.txt)、[障碍物](../../../../scripts/prompts/recovery_semantic_obstacle.txt)。各batch的submission/tasks/source_manifest记录完整命令、资源、checkpoint SHA与不可变源文件，配对CSV保留空白人工标签。events.jsonl保留所有事件的模型输入SHA/原始正反logits/概率/回退原因；图像摘录开发改向和完整验证中5条有前缀支持的成败变化，另外8个成败变化任务的16份commands/poses NPZ一起保留；完整相机序列/模型/场景留服务器。\n\n'
    readme += '资料生成器只读取证据，不提交作业。离线核验：在克隆根运行`python docs/experiments/inference-recovery/iteration_20261108/evidence/logs/qwen_recovery_iteration_20261108/publish_iteration.py --check-only --tree .`；按inputs.json逐项复算SHA，不加载模型。实际导航依赖服务器RUNBOOK所列环境与合法数据。代码单元回归74项、旧Qwen14项通过；实际FP32词ID2665/13394/9175、真实答案位置、批单和空白/换序检查均保留原证据。\n'
    (destination/'README.md').write_text(readme)
    for name in ['README.md','results.json','BRANCHES.md','CASES.md']:
        raw=(destination/name).read_bytes()
        inputs[name]=dict(source=str(Path(__file__).resolve()),encoding='generated',
            sha256=digest(raw),bytes=len(raw))
    copy(Path(__file__))
    # Refresh after recording the generator itself.
    (destination/'inputs.json').write_text(json.dumps(inputs,indent=2)+'\n')
    print(json.dumps(dict(destination=str(destination),files=len(inputs),
        source_bytes=sum(x['bytes'] for x in inputs.values()),rounds=len(rounds)),indent=2))


def check(tree):
    destination = tree.resolve()/PACKAGE
    inputs=json.loads((destination/'inputs.json').read_text())
    for relative, item in inputs.items():
        data=(destination/relative).read_bytes()
        assert digest(data)==item['sha256'], relative
        assert len(data)==item['bytes'], relative
    evidence=destination/'evidence/logs'
    meta=json.loads((evidence/'github_discussion_update_20261108/training_sources.json').read_text())
    latest=evidence/Path(meta['latest_snapshot']).relative_to(ROOT/'logs')
    training=json.loads((latest/'readout.json').read_text())
    summary=json.loads((latest/'summary.json').read_text())
    def csv_rows(path):
        with path.open() as handle:
            return list(csv.DictReader(handle))
    core=['metrics/success','metrics/spl']
    recent={k:csv_rows(evidence/'github_discussion_update_20261108/recent_training'/(k+'.csv')) for k in summary}
    baseline=summary['baseline']
    for tag,key in [('metrics/success','sr'),('metrics/spl','spl')]:
        values=[float(v['value']) for v in recent['baseline'] if v['tag']==tag and baseline['step']-1000000<int(v['step'])<=baseline['step']]
        assert abs(100*statistics.mean(values)-baseline[key])<1e-10
    for name,run in training['runs'].items():
        end=run['latest_step']
        for width,key in [(1000000,'last1m'),(3000000,'last3m')]:
            for tag in core:
                values=[float(v['value']) for v in recent[name] if v['tag']==tag and end-width<int(v['step'])<=end]
                assert len(values)==run[key][tag]['points']
                assert abs(statistics.mean(values)-run[key][tag]['mean'])<1e-12
    references={k:csv_rows(evidence/'github_discussion_update_20261108/reference_scalars'/(k+'.csv')) for k in ['baseline','coverage256','coverage32']}
    for name,windows in training['own_budget'].items():
        for window in windows.values():
            expected=None
            for case,metrics in window['runs'].items():
                rows=recent[case] if case==name else references[case]
                for tag in core:
                    selected=[v for v in rows if v['tag']==tag and window['lower_exclusive']<int(v['step'])<=window['upper_inclusive']]
                    steps=[int(v['step']) for v in selected]
                    if expected is None:expected=steps
                    else:assert steps==expected
                    assert abs(100*statistics.mean(float(v['value']) for v in selected)-metrics[tag])<1e-10
    batch=evidence/'qwen_recovery_iteration_20261108/expanded_v2/expanded03_full'
    case_rows={}
    for mode in ['off','rule','qwen']:
        result=json.loads((batch/('full_'+mode)/'result.json').read_text())
        data={}
        for path in (batch/('full_'+mode)/'episodes').glob('*.jsonl'):
            for row in map(json.loads,path.read_text().splitlines()):
                key=(row['scene_id'],row['episode_id']);assert key not in data;data[key]=row
        assert len(data)==4200
        assert abs(statistics.mean(v['success'] for v in data.values())-result['success_rate'])<1e-12
        assert abs(statistics.mean(v['spl'] for v in data.values())-result['spl'])<1e-12
        case_rows[mode]=data
    assert all(set(x)==set(case_rows['off']) for x in case_rows.values())
    for data in case_rows.values():
        for key,row in data.items():
            assert row['goal_sha256']==case_rows['off'][key]['goal_sha256']
            assert row['start_position']==case_rows['off'][key]['start_position']
    print('Verified',len(inputs),'published hashes; full3x4200 metrics/tasks and training windows recomputed without model/GPU.')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--check-only',action='store_true')
    parser.add_argument('--tree',type=Path,default=DEV)
    args=parser.parse_args()
    check(args.tree) if args.check_only else build()
