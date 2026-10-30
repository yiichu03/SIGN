"""Append the fixed training readout to the existing detached publication tree."""
import argparse
import csv
import gzip
import hashlib
import io
import json
import os
import re
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path('/scratch/e1538633/liuyi')
HERE = ROOT / 'logs/training_readout_20261031'
SNAP = HERE / 'snapshot_005043'
BASE = 'ac6229895361d1551fad5710ddf1f53830d11e20'
PACKAGE = Path('docs/experiments/qwen128-reward')
RELATIVE = PACKAGE / 'ablations/training_20261031'
NAMES = ['baseline', 'coverage256', 'coverage32', 'qwen128_beta01',
         'A_qwen128_beta003', 'B_qwen256_beta003', 'C_geometry128']
LABELS = ['冻结视觉基线', '旧覆盖256', '旧覆盖32', 'Qwen128 beta0.1',
          'A Qwen128 beta0.03', 'B Qwen256 beta0.03', 'C 几何128']

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')

def git(tree, *args):
    return subprocess.check_output(['git', '-C', str(tree), *args])

def verify(tree):
    package, folder = tree / PACKAGE, tree / RELATIVE
    manifest = json.loads((package / 'publication_manifest.json').read_text())
    for name, item in manifest.items():
        raw = (package / name).read_bytes()
        assert len(raw) == item['bytes'] and sha(raw) == item['sha256'], name
    inputs = json.loads((folder / 'inputs.json').read_text())
    for name, item in inputs.items():
        raw = (folder / name).read_bytes()
        if item['encoding'] == 'gzip':
            raw = gzip.decompress(raw)
        assert sha(raw) == item['source_sha256'] and len(raw) == item['source_bytes'], name
    old = git(tree, 'show', BASE + ':' + str(PACKAGE / 'workspace/WORKLOG.md'))
    assert (package / 'workspace/WORKLOG.md').read_bytes().startswith(old)
    assert not git(tree, 'diff', 'd2352f0', '--', 'src', 'scripts', 'tests', 'exp_config', 'run_sim.py')
    readout = json.loads((folder / 'readout.json').read_text())
    followup = json.loads((folder / 'comparison_followup.json').read_text())
    comparisons = 0
    for name in NAMES:
        data = {'metrics/success': [], 'metrics/spl': []}
        with gzip.open(folder / 'data' / (name + '_scalars.csv.gz'), 'rt') as f:
            for row in csv.DictReader(f):
                if row['tag'] in data:
                    data[row['tag']].append((int(row['step']), float(row['value'])))
        for window in followup['windows'].values():
            for tag, rows in data.items():
                selected = [v for step, v in rows if window['lower_exclusive'] < step <= window['upper_inclusive']]
                expected = window['runs'][name][tag]
                assert len(selected) == expected['points']
                assert abs(sum(selected) / len(selected) - expected['mean']) < 1e-12
                comparisons += 1
        end = readout['runs'][name]['latest_step']
        for tag, rows in data.items():
            selected = [v for step, v in rows if end - 1000000 < step <= end]
            assert abs(sum(selected) / len(selected) - readout['runs'][name]['own_last_1m'][tag]) < 1e-12
        if name in NAMES[3:]:
            prefix = 'geometry' if name == 'C_geometry128' else 'qwen'
            with gzip.open(folder / 'data' / (name + '_rollouts.jsonl.gz'), 'rt') as f:
                rows = [json.loads(line) for line in f if line.endswith('\n')]
            rows = [r for r in rows if (r['rollout_id'] + 1) * 2048 <= end]
            assert [r['rollout_id'] for r in rows] == list(range(end // 2048))
            for row in rows:
                assert row['nav_rewards_unchanged'] and row['masks_unchanged']
                m = row['metrics']
                assert abs(m[prefix + '_mixed_reward_sum'] - m[prefix + '_nav_reward_sum'] - m[prefix + '_bonus_sum']) < 1e-4
    markdown = [tree / 'README.md', package / 'README.md', package / 'ablations/README.md', folder / 'README.md']
    markdown += [package / 'workspace' / name for name in ['AGENTS.md', 'STATUS.md', 'RUNBOOK.md']]
    for path in markdown:
        text = re.sub(r'```.*?```', '', path.read_text(), flags=re.S)
        for target in re.findall(r'\[[^\]]*\]\(([^)]+)\)', text):
            if target.startswith(('https://', 'http://', '#', 'mailto:')):
                continue
            assert (path.parent / target.split('#')[0]).exists(), (str(path), target)
    for path in folder.rglob('*'):
        if not path.is_file():
            continue
        assert path.suffix not in ['.pth', '.pt', '.glb', '.navmesh', '.safetensors']
        raw = path.read_bytes()
        assert len(raw) < 20 * 1024 * 1024, str(path)
        if path.suffix != '.gz' and path.suffix != '.png':
            assert not re.search(rb'-----BEGIN [A-Z ]*PRIVATE KEY-----|ghp_[A-Za-z0-9]{30,}|hf_[A-Za-z0-9]{30,}', raw), str(path)
    return dict(passed=True, manifest_files=len(manifest),
                package_bytes=sum(item['bytes'] for item in manifest.values()),
                recomputed_window_metrics=comparisons, compressed_sources_verified=len(inputs),
                relative_markdown_links_passed=True, old_worklog_prefix_preserved=True,
                training_source_unchanged=True)

def build(tree):
    assert git(tree, 'rev-parse', 'HEAD').decode().strip() == BASE
    assert not git(tree, 'status', '--porcelain')
    package, folder = tree / PACKAGE, tree / RELATIVE
    for name, item in json.loads((package / 'publication_manifest.json').read_text()).items():
        assert sha((package / name).read_bytes()) == item['sha256'], name
    previous = (package / 'workspace/WORKLOG.md').read_bytes()
    assert (ROOT / 'WORKLOG.md').read_bytes().startswith(previous)
    folder.mkdir()
    inputs, mapping = {}, {}

    def copy(source, relative, compress=False):
        raw = source.read_bytes()
        target = folder / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(gzip.compress(raw, compresslevel=6, mtime=0) if compress else raw)
        inputs[relative] = dict(source=str(source), source_sha256=sha(raw), source_bytes=len(raw), encoding='gzip' if compress else 'identity')
        mapping[str(source)] = target

    for name in ['readout.json', 'comparison_followup.json', 'matched_training.png']:
        copy(SNAP / name, name)
    for name in ['checkpoint_check.json', 'checkpoint_check.log', 'capture.log']:
        copy(HERE / name, 'evidence/' + name)
    copy(HERE / 'jobs.txt', 'evidence/jobs.txt.gz', True)
    copy(ROOT / 'logs/github_sync_audit_20261031/013212/audit.json', 'evidence/github_sync_before.json')
    for name in NAMES:
        copy(SNAP / name / 'selected_scalars.csv', 'data/' + name + '_scalars.csv.gz', True)
        if name in NAMES[3:]:
            copy(SNAP / name / 'rollouts.jsonl', 'data/' + name + '_rollouts.jsonl.gz', True)
    copy(HERE / 'readout.py', 'scripts/readout.py')
    copy(Path(__file__).resolve(), 'scripts/publish_readout.py')
    for name in ['view_personal_tensorboard.sh', 'view_personal_tensorboard.py', 'tensorboard_launcher_checks_20261030.json']:
        copy(ROOT / 'logs/gibson_reproduction_20261026' / name, 'operations/' + name)
    write_json(folder / 'inputs.json', inputs)
    r = json.loads((folder / 'readout.json').read_text())
    followup = json.loads((folder / 'comparison_followup.json').read_text())
    text = '''# 六组训练对照：2026-10-31固定快照

事件取样末时为新加坡时间2026-10-31 00:51–00:53，以下不是实时看板。仅汇总原训练日志与已保存权重；本次没有提交/停止训练，没有重新采样或评估。原生SR/SPL是50-update完成episode滑窗，区间均值的相邻点相互关联，不作独立统计样本。

## 各自最新进度

每轮为8环境×256动作=2048环境步。SR/SPL取各自最后100万步的滑窗均值；步数不同不能直接排名。耗时为近期3h实测中位数，节点不同，不作受控速度基准。

| 方法 | 训练作业 | 环境步 | SR | SPL | 秒/轮 |
|---|---|---:|---:|---:|---:|
'''
    for name, label in zip(NAMES[1:], LABELS[1:]):
        x = r['runs'][name]; m = x['own_last_1m']
        text += f"| {label} | {x['job_id']} | {x['latest_step']:,} | {100*m['metrics/success']:.2f}% | {100*m['metrics/spl']:.2f}% | {x['recent_3h']['median_update_seconds']:.2f} |\n"
    text += '\n## 相同训练预算比较\n\n统一取5,844,416–6,844,416步的100万步区间，已停止基线使用相同历史区间。\n\n| 方法 | SR | SPL | 平均碰撞/episode |\n|---|---:|---:|---:|\n'
    window = r['windows'][0]['runs']
    for name, label in zip(NAMES, LABELS):
        m = window[name]
        text += f"| {label} | {100*m['metrics/success']:.2f}% | {100*m['metrics/spl']:.2f}% | {m['metrics/collisions.count']:.2f} |\n"
    text += '''
在此窗口Qwen beta0.1/B略好于旧覆盖32，三Qwen均未超过旧覆盖256。改用同结束步的最近300万步，beta0.1 SR83.02%高于旧256的82.26%，SPL45.11%仍低于45.40%；最近500万步则为79.58%/43.49%对79.88%/43.65%。结论对窗口敏感，当前没有稳定全面收益证据，不能按单个末点或平均q判定算法优劣。

旧三方法共同38.018–43.018M的5M窗口，基线/256/32 SR86.24/85.47/84.96%，SPL51.05/47.49/47.62%。它们与18.944M固定checkpoint的val结果属于不同阶段与统计口径；本页只讨论训练。

![同预算训练曲线](matched_training.png)

图仅为展示额外采用101-update平滑；表格来自未额外平滑的原生日志。[完整统计](readout.json)保存各组末点/近期均值、共同区间与原始快照SHA，[1/2/3/5M复核](comparison_followup.json)保存窗口与点数。

## 几何128、覆盖与奖励尺度

C是A的几何对照：相同2.5cm/3m/90°采集、episode历史和几何有效性，128步/真实terminal切段，PPO仍256步。A段末bonus=.03*(L/256)*raw_q；C为alpha*new_area_m2/256，无Qwen、topdown渲染或伪概率。alpha=.2927574680399425来自[既有冻结校准](../calibration/calibration.json)，仅保证原校准集总量匹配，不保证训练中持续匹配。

共同5.844–6.844M的A/B/C有效动作覆盖效率为0.15941/0.16081/0.16514m²/动作，C面积略高但SR较低。每轮bonus为0.13473/0.13992/0.35013，C约为A的2.60倍；未重拟合alpha。原reward仍是导航奖励，bonus独立记录。

旧覆盖的0.1m全动作统计，与新组0.025m且仅纳入几何有效段的面积统计不直接排名。基线训练本身没有面积日志；这些数据不能证明新增奖励已减少冗余搜索。

新四组各自近1M的有效段约92.7–93.2%，低于短测约98%；主要为episode高度跨度≥0.5m，少量距navmesh超过5cm，按既有规则跳过bonus。A/B有效片段平均q约0.625/0.653，仅描述裁判输出，不作效果指标。共同段统计、valid动作数和面积在JSON中分开保留。

## 冻结基线停止记录

基线1496716于2026-10-28 20:28:36停止，最终训练步74,653,696；控制台末步74,649,600；最后已保存、可用于评估的checkpoint为74,240,000步，三者不同。

| 训练统计 | SR | SPL |
|---|---:|---:|
| 最后一个原生滑窗点 | 87.81% | 55.13% |
| 最后100万步滑窗均值 | 87.87% | 54.82% |
| 最后500万步滑窗均值 | 89.42% | 55.66% |

这不是额外的完整训练集离线评估；公开完整checkpoint的4200条val SR86.00%/SPL53.01%是另一个结果。快速索引见[STATUS](../../workspace/STATUS.md#gibson-reference)。

## 完整性与复核

六个训练作业在快照时均R，所有scalar历史有限；最近稳定编号checkpoint均全有限，42项encoder状态逐位匹配公开权重。四新组已完成rollout编号连续、nav_rewards和真实masks不变，混合奖励守恒误差小于5.1e-5；旧coverage bonus守恒误差小于1.8e-8。[权重检查](evidence/checkpoint_check.json)记录实际checkpoint步与SHA，不用事件末步代替权重步。

[data](data/)保存七组所选scalar CSV及四组固定前缀rollout审计的确定性gzip；[inputs.json](inputs.json)记录原路径、原字节数与SHA。完整TensorBoard二进制事件、模型/场景/环境保留在服务器，没有重复上传。JSON中的绝对路径属于服务器来源证据，不代表仓库内存在该文件。

在已安装TensorBoard/numpy/matplotlib的服务器环境，从liuyi根执行原只读工具（每次新建快照，不提交作业）：

```bash
envs/sign-baseline/bin/python logs/training_readout_20261031/readout.py
```

从本仓库根离线核验已发布gzip SHA、56项窗口均值、导航奖励/mask审计和相对链接，无需模型或GPU：

```bash
python3 docs/experiments/qwen128-reward/ablations/training_20261031/scripts/publish_readout.py --tree . --check-only
```

[operations](operations/)保留10月30日TensorBoard启动/复用/会话清理脚本及四项已完成集成检查，原三组logdir/6006不变。线上命令仍见[RUNBOOK](../../workspace/RUNBOOK.md)，脚本副本用于复现和审阅；本次未启动/停止网页服务。

本次仅资料发布，运行源码保持原提交；没有重跑单测/GPU训练，资料SHA、解压、指标复算、WORKLOG追加关系及链接另行检查。评估作业沿用既有安排，本页不复核或报告新val结果。[A/B/C设置与提交回执](../README.md)、[根四文档快照](../../workspace/)保留进一步索引。
'''
    (folder / 'README.md').write_text(text)
    for name in ['AGENTS.md', 'STATUS.md', 'RUNBOOK.md', 'WORKLOG.md']:
        source = ROOT / name; raw = source.read_bytes()
        if name == 'WORKLOG.md':
            (package / 'workspace' / name).write_bytes(raw)
            continue
        def portable(match):
            label, target = match.groups()
            if target.startswith(('http://', 'https://', '#')) or target.split('#')[0] in ['AGENTS.md', 'STATUS.md', 'RUNBOOK.md', 'WORKLOG.md']:
                return match.group(0)
            path, sep, anchor = target.partition('#')
            source_path = ROOT / path
            mapped = mapping.get(str(source_path))
            if mapped is None and str(source_path).startswith(str(ROOT / 'SIGN-qwen-ablation') + '/'):
                candidate = tree / source_path.relative_to(ROOT / 'SIGN-qwen-ablation')
                if candidate.exists(): mapped = candidate
            if mapped:
                return '[' + label + '](' + os.path.relpath(mapped, package / 'workspace') + (sep + anchor if sep else '') + ')'
            return label + '（服务器路径：`' + str(source_path) + '`）'
        (package / 'workspace' / name).write_text(re.sub(r'\[([^\]]+)\]\(([^)]+)\)', portable, raw.decode()))
    readme = package / 'README.md'
    text = readme.read_text().replace('## 最新进展：2026-10-29 16:01快照',
        '## 最新训练对照：2026-10-31\n\n六组训练的同预算SR/SPL、覆盖与奖励尺度、基线停止记录及可复核数据见[最新训练快照](ablations/training_20261031/README.md)。本页下方保留原beta0.1启动验收记录，运行源码81fedec；新ABC运行源码d2352f0。\n\n## 早期进展：2026-10-29 16:01快照', 1)
    readme.write_text(text)
    readme = package / 'ablations/README.md'
    text = readme.read_text().replace('## 实际正式配置与作业',
        '## 最新训练记录\n\n[2026-10-31六组训练对照、曲线和原始统计](training_20261031/README.md)。下面保留2026-10-29的启动/短测及评估提交记录；不以这些历史状态代替最新作业状态。\n\n## 实际正式配置与作业', 1)
    text = text.replace('当前尚无这三组正式模型的val结果', '2026-10-29提交时尚无这三组正式模型的val结果')
    readme.write_text(text)
    readme = tree / 'README.md'
    readme.write_text(readme.read_text() + '\n\n最新训练资料（2026-10-31）：[六组同预算比较、曲线、基线停止记录与复核数据](docs/experiments/qwen128-reward/ablations/training_20261031/README.md)。\n')
    write_json(folder / 'publication_info.json', dict(created_at=datetime.now(timezone(timedelta(hours=8))).isoformat(timespec='seconds'),
        publication_base=BASE, runtime_commit='d2352f06bc56386d098c8b94d2754e9e21bf2cb3',
        branch='phase2/qwen-beta003-geometry128', workspace_source_sha256={n: sha((ROOT / n).read_bytes()) for n in ['AGENTS.md','STATUS.md','RUNBOOK.md','WORKLOG.md']}))
    manifest = {str(p.relative_to(package)): dict(sha256=sha(p.read_bytes()), bytes=p.stat().st_size)
                for p in sorted(package.rglob('*')) if p.is_file() and p.name != 'publication_manifest.json'}
    write_json(package / 'publication_manifest.json', manifest)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--tree', type=Path, required=True)
    parser.add_argument('--check-only', action='store_true')
    args = parser.parse_args(); tree = args.tree.resolve()
    if not args.check_only:
        build(tree)
    print(json.dumps(verify(tree), indent=2))

if __name__ == '__main__':
    main()
