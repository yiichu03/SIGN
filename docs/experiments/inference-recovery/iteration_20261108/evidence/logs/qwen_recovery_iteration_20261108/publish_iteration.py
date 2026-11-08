"""Generate a small, source-hashed research snapshot; never submit jobs."""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import re

ROOT = Path('/scratch/e1538633/liuyi')
HERE = Path(__file__).resolve().parent
DEV = ROOT / 'SIGN-qwen-candidate-recovery'
PACKAGE = Path('docs/experiments/inference-recovery/iteration_20261108')


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
                     'version2_release_audit.json']:
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
    readme = '# Qwen2B推理恢复：迭代与固定版本验证\n\n'
    readme += '资料截面：'+snapshot['recorded_at']+'。行为固定提交`'+snapshot['behavior_commit']+'`；资料提交可以继续前进，运行快照保持不变。\n\n'
    readme += '[逐轮机器可读结果](results.json) · [文件SHA与服务器来源](inputs.json) · [当前STATUS生成副本](workspace/STATUS.md) · [追加式操作记录](workspace/WORKLOG.md)\n\n'
    readme += '## 方法与控制\n\n'
    readme += '导航模型使用覆盖256的125,952,000步checkpoint；不重新训练，不把Qwen接入PPO奖励。原SIGN继续决策，只有RGB与实际动作历史出现持续受阻迹象时才触发。24个实际原地转向动作获取左右90度RGB；两张图独立输入Qwen3.5-2B，FP32/T=1，读取No/Unknown/Yes真实答案token logits。正问通行性与反问障碍物须同向支持，默认侧在两问中都判可通行时保持规则；其余证据不足回退匹配规则。最多两次恢复，每次90度转向及1.6m短尝试；连扫描最多76个覆盖动作都计入原500步，原STOP/masks/GRU保留。\n\n'
    readme += '比较原生off、同扫描/同动作/同触发器的rule，以及qwen。回退到规则和主动扫描的收益不能算作模型判断的额外贡献。Agent不读取GT pose、collision、distance或地图；这些仅供离线选题和事后前缀审计。\n\n'
    readme += '三候选softmax只是条件词概率，不是校准的通行或导航成功率；正反问来自同一模型，不按独立事件相乘。VLM职责限于局部受阻方向选择，不承担全局目标规划。\n\n'
    old=json.loads((old_full/'comparison.json').read_text())
    readme += '既有完整4200参考：off SR/SPL '+f"{100*old['cases']['off']['success_rate']:.4f}%/{100*old['cases']['off']['spl']:.4f}%"+'，旧不扫描规则 '+f"{100*old['cases']['rule']['success_rate']:.4f}%/{100*old['cases']['rule']['spl']:.4f}%"+'。旧规则与本轮主动扫描规则的动作预算不同，正式实验须重跑本轮匹配rule；不能把两种规则混作同一对照。\n\n'
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
    readme += '行为配置：[inference_semantic_consensus_veto90.yaml](../../../../src/config/inference_semantic_consensus_veto90.yaml)；提示：[通行性](../../../../scripts/prompts/recovery_semantic_forward.txt)、[障碍物](../../../../scripts/prompts/recovery_semantic_obstacle.txt)。各batch的submission/tasks/source_manifest记录完整命令、资源、checkpoint SHA与不可变源文件，配对CSV保留空白人工标签。events.jsonl保留所有事件的模型输入SHA/原始正反logits/概率/回退原因，不仅保留成功案例；图像仅摘录开发中真实改向事件，其他大轨迹/模型/场景保留服务器。\n\n'
    readme += '资料生成器只读取证据，不提交作业。离线核验：在克隆根运行`python docs/experiments/inference-recovery/iteration_20261108/evidence/logs/qwen_recovery_iteration_20261108/publish_iteration.py --check-only --tree .`；按inputs.json逐项复算SHA，不加载模型。实际导航依赖服务器RUNBOOK所列环境与合法数据。代码单元回归74项、旧Qwen14项通过；实际FP32词ID2665/13394/9175、真实答案位置、批单和空白/换序检查均保留原证据。\n'
    (destination/'README.md').write_text(readme)
    for name in ['README.md','results.json']:
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
    print('Verified',len(inputs),'published source hashes; no model or GPU loaded.')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--check-only',action='store_true')
    parser.add_argument('--tree',type=Path,default=DEV)
    args=parser.parse_args()
    check(args.tree) if args.check_only else build()
