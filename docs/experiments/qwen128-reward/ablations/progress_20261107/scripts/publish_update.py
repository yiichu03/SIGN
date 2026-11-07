"""Build/check a versioned evidence update in a detached publication worktree.

No model, simulator, training process or PBS mutation is performed by this tool.
"""
import argparse
import csv
import gzip
import hashlib
import html
import importlib.util
import json
import math
import os
import re
import shutil
import statistics
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import unquote

ROOT = Path('/scratch/e1538633/liuyi')
HERE = ROOT/'logs/github_publication_20261107'
BASE = '333b2aeb0903515c97a5b8a416bb3025a34518c3'
RUNTIME = 'd2352f06bc56386d098c8b94d2754e9e21bf2cb3'
BRANCH = 'phase2/qwen-beta003-geometry128'
PACKAGE = Path('docs/experiments/qwen128-reward')
RELATIVE = PACKAGE/'ablations/progress_20261107'
TZ = timezone(timedelta(hours=8))
NAMES = ['AGENTS.md', 'STATUS.md', 'RUNBOOK.md', 'WORKLOG.md']
FAMILIES = ['qwen_three_checkpoint_eval_20261107', 'gibson_coverage32_selected_eval_20261107']
CODE_BRANCHES = {
    'phase2/continue-coverage256-20261103': '5a86720fdcaf69a842ce40a660e2598f3fc052a0',
    'phase2/continue-coverage32-20261103': '2e5efbaf6caa4962e458e898d6c107e06a59138b',
    'phase2/continue-qwen128-beta01-20261103': 'bb59545f0c5663163e17cfe1dea37c441f09ccd2',
    'phase2/continue-qwen-ablation-20261103': '1256ca70497592d2df178e6f77d10c14380689d8',
}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def now():
    return datetime.now(TZ).isoformat(timespec='seconds')


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, allow_nan=False)+'\n')


def git(tree, *args):
    return subprocess.check_output(['git', '-C', str(tree), *args])


def absolute(path):
    return os.path.abspath(str(path))


def capture():
    families = {}
    ids = ['1511143', '1511145', '1511146', '1511147', '1511148', '1511410']
    for name in FAMILIES:
        folder = ROOT/'logs'/name
        submitted = json.loads((folder/'submission.json').read_text())
        manifest = json.loads((folder/'manifest.json').read_text())
        families[name] = {'cases': manifest['cases'], 'gpu_jobs': submitted['gpu_jobs'],
                          'summary_job': submitted['summary_job']}
        ids += [r['job_id'] for r in submitted['gpu_jobs']]
        ids += [submitted['summary_job']['job_id']]
    jobs = json.loads(subprocess.check_output(['qstat', '-fx', '-F', 'json', *ids], text=True))['Jobs']
    keep = ['Job_Name', 'job_state', 'Exit_status', 'queue', 'project', 'comment',
            'depend', 'resources_used', 'Resource_List', 'stime', 'obittime']
    jobs = {k: {f: v.get(f) for f in keep} for k, v in jobs.items()}
    for name, family in families.items():
        for row in family['gpu_jobs']:
            case = row['case']
            state = jobs[row['job_id']]
            complete = state['job_state'] == 'F' and state['Exit_status'] == 0
            row['complete'] = complete
            row['state'] = state['job_state']
            if complete:
                result = json.loads((ROOT/'logs'/name/case/'result.json').read_text())
                assert result['episodes'] == 4200 and result['training_step'] == row['step']
                assert math.isfinite(result['success_rate']) and math.isfinite(result['spl'])
                row['result'] = result
        sj = jobs[family['summary_job']['job_id']]
        family['summary_complete'] = sj['job_state'] == 'F' and sj['Exit_status'] == 0
    remote = git(ROOT/'SIGN', 'ls-remote', 'origin', *['refs/heads/'+b for b in CODE_BRANCHES]).decode()
    heads = {line.split()[1][len('refs/heads/'):]: line.split()[0] for line in remote.splitlines()}
    assert heads == CODE_BRANCHES, heads
    guard_path = ROOT/'logs/gibson_coverage32_selected_eval_20261107/guard.py'
    spec = importlib.util.spec_from_file_location('publication_runtime_guard', guard_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.guard()
    current = {'captured_at': now(), 'jobs': jobs, 'families': families,
               'code_branches_verified_on_origin': heads, 'runtime_source_guard_passed': True,
               'publication_base': BASE, 'publication_branch': BRANCH}
    write_json(HERE/'current.json', current)
    return current


class Builder:
    def __init__(self, tree, current):
        self.tree = tree
        self.folder = tree/RELATIVE
        self.current = current
        self.inputs = {}
        self.mapping = {}
        self.omitted = []
        self.html_files = []

    def copy(self, source, target=None, force_identity=False, register=True):
        source = Path(source)
        target = target or self.folder/'evidence'/source.relative_to(ROOT)
        raw = source.read_bytes()
        encoding = 'identity'
        if not force_identity and (source.suffix == '.jsonl' or
                (source.suffix == '.csv' and len(raw) > 2_000_000) or len(raw) > 15_000_000):
            target = target.with_name(target.name+'.gz')
            published = gzip.compress(raw, compresslevel=6, mtime=0)
            encoding = 'gzip'
        else:
            published = raw
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(published)
        self.inputs[str(target.relative_to(self.folder))] = {
            'source': str(source), 'source_sha256': sha(raw), 'source_bytes': len(raw),
            'encoding': encoding, 'published_sha256': sha(published)}
        if register:
            self.mapping[absolute(source)] = target
        if source.suffix == '.html' and register:
            self.html_files.append((source, target, raw.decode()))
        return target

    def allowed(self, p, base, completed_family=None):
        rel = p.relative_to(base)
        parts = rel.parts
        if any(x in parts for x in ['__pycache__', 'checkpoints', 'tb', 'events',
                                    'historical_C_events', 'traces', 'videos']):
            return False
        if p.suffix not in ['.py', '.pbs', '.sh', '.json', '.jsonl', '.csv', '.yaml',
                             '.yml', '.txt', '.md', '.png', '.pdf', '.log']:
            return False
        if p.suffix == '.log' and (p.name.endswith('.pbs.log') or p.name in ['train.log', 'worker.log'] or p.stat().st_size > 1_000_000):
            return False
        if 'native' in parts and p.suffix not in ['.yaml', '.yml', '.json']:
            return False
        if p.suffix == '.jsonl' and 'episodes' not in parts and not p.name.endswith('_recent_rollouts.jsonl'):
            return False
        if completed_family:
            family = self.current['families'][completed_family]
            states = {x['case']: x['complete'] for x in family['gpu_jobs']}
            if parts[0] in states and not states[parts[0]]:
                if 'episodes' in parts or p.name == 'result.json':
                    return False
            if p.name in ['comparison.json', 'comparison.csv'] and not family['summary_complete']:
                return False
        return True

    def collect(self):
        batches = [
            'training_continuation_20261103', 'training_stop_20261031', 'matched_training_20261103',
            'training_readout_20261107', 'gibson_coverage_latest_eval_20261103',
            'gibson_baseline_final_eval_20261103', 'gibson_coverage256_peak_eval_20261105',
            'gibson_coverage256_candidates_eval_20261105', *FAMILIES]
        for name in batches:
            base = ROOT/'logs'/name
            for source in sorted(base.rglob('*')):
                if source.is_file() and self.allowed(source, base, name if name in FAMILIES else None):
                    self.copy(source)
        for name in ['training_readout_20261103', 'training_readout_20261105']:
            base = ROOT/'logs'/name
            for source in sorted(base.rglob('*')):
                if 'snapshot_150000' in source.parts:
                    if source.name not in ['attempt_status.json', 'readout_script_at_execution.py']:
                        continue
                if source.is_file() and self.allowed(source, base):
                    self.copy(source)
        # Context for the fixed matched-budget references, already published elsewhere.
        old = ROOT/'logs/training_readout_20261031/snapshot_005043'
        for case in ['baseline', 'coverage256', 'coverage32']:
            self.copy(old/case/'selected_scalars.csv')
        self.copy(ROOT/'logs/gibson_reproduction_20261026/pretrained_full_result.json')
        failure = ROOT/'logs/sign_failure_replay_20261104'
        for source in sorted(failure.iterdir()):
            if source.is_file() and self.allowed(source, failure):
                self.copy(source)
        analysis = failure/'analysis'
        for source in sorted(analysis.rglob('*')):
            if not source.is_file():
                continue
            rel = source.relative_to(analysis)
            if rel.parts[0] == 'source':
                take = source.suffix in ['.py', '.pbs', '.json', '.yaml', '.yml', '.csv', '.txt', '.md']
            else:
                take = source.suffix in ['.json', '.csv', '.html', '.png', '.pdf', '.txt', '.md']
            if take:
                self.copy(source, force_identity=source.suffix == '.csv')
            else:
                self.omitted.append({'source': str(source), 'bytes': source.stat().st_size,
                                     'reason': 'Raw video/camera/trace or binary runtime data retained on server.'})
        self.copy(HERE/'current.json', self.folder/'publication_state.json')
        self.copy(Path(__file__).resolve(), self.folder/'scripts/publish_update.py')

    def portable_html(self):
        for source, target, raw in self.html_files:
            self.copy(source, target.with_name(target.stem+'.server.html'), force_identity=True, register=False)
            text = re.sub(r'<video\b[^>]*src=["\']([^"\']+)["\'][^>]*>.*?</video>',
                lambda m: '<p class="note">完整视频保留服务器，未上传GitHub：<code>'+
                html.escape(absolute(source.parent/unquote(m.group(1))))+'</code></p>', raw, flags=re.S)
            text = text.replace('逐案例图像与完整视频', '逐案例图像（完整视频保留服务器）')
            text = text.replace('<h1>', '<p class="note">GitHub资料版：保留图像与统计，完整视频/原始轨迹在服务器；原HTML另存.server.html。</p><h1>', 1)
            def link(m):
                kind, url = m.groups()
                if url.startswith(('http:', 'https:', '#', 'data:', 'mailto:')):
                    return m.group(0)
                name, sep, anchor = url.partition('#')
                mapped = self.mapping.get(absolute(source.parent/unquote(name)))
                assert mapped is not None, (source, url)
                return kind+'="'+os.path.relpath(mapped, target.parent)+(sep+anchor if sep else '')+'"'
            text = re.sub(r'(href|src)=["\']([^"\']+)["\']', link, text)
            target.write_text(text)
            record = self.inputs[str(target.relative_to(self.folder))]
            record['encoding'] = 'portable_html_no_videos'
            record['published_sha256'] = sha(target.read_bytes())

    def workspace(self, original_tree):
        target_dir = self.tree/PACKAGE/'workspace'
        old = (original_tree/PACKAGE/'workspace/WORKLOG.md').read_bytes()
        assert (ROOT/'WORKLOG.md').read_bytes().startswith(old), 'WORKLOG prefix mismatch'
        for name in NAMES:
            self.mapping[absolute(ROOT/name)] = target_dir/name
        for name in NAMES:
            source = ROOT/name
            raw = source.read_bytes()
            if name == 'WORKLOG.md':
                text = raw.decode()
            else:
                def portable(m):
                    image, label, url = m.groups()
                    if url.startswith(('https:', 'http:', '#', 'mailto:')):
                        return m.group(0)
                    path, sep, anchor = url.strip('<>').partition('#')
                    candidate = Path(path) if path.startswith('/') else ROOT/path
                    mapped = self.mapping.get(absolute(candidate))
                    if mapped is None:
                        for prefix in ['SIGN-qwen-ablation', 'SIGN-qwen128-reward']:
                            try:
                                relative = candidate.relative_to(ROOT/prefix)
                            except ValueError:
                                continue
                            possible = self.tree/relative
                            if possible.exists():
                                mapped = possible
                    if mapped is None:
                        return label+'（服务器路径：`'+str(candidate)+'`）'
                    return image+'['+label+']('+os.path.relpath(mapped, target_dir)+(sep+anchor if sep else '')+')'
                text = re.sub(r'(!?)\[([^\]]*)\]\(([^)]+)\)', portable, raw.decode())
                text = '\n'.join(line.rstrip() for line in text.splitlines())+'\n'
            (target_dir/name).write_text(text)
        assert (target_dir/'WORKLOG.md').read_bytes().startswith(old)
        return {'bytes': len(old), 'sha256': sha(old)}

    def readme(self):
        current = self.current
        readout = json.loads((ROOT/'logs/training_readout_20261107/snapshot_130555/readout.json').read_text())
        summary = json.loads((ROOT/'logs/training_readout_20261107/snapshot_130555/summary.json').read_text())
        comparison = json.loads((ROOT/'logs/gibson_coverage256_candidates_eval_20261105/comparison.json').read_text())
        text = '# SIGN / Gibson：训练、验证与失败诊断更新（2026-11-07）\n\n'
        text += '资料状态截面：'+current['captured_at']+'；训练指标使用11月7日13:05–13:06冻结事件，非实时看板。'
        text += '这是独立资料发布，训练源码/目录/作业没有为发布而修改；本分支源码保持d2352f0，实际续跑代码见下方分支。\n\n'
        text += '[当前STATUS](../../workspace/STATUS.md) · [操作RUNBOOK](../../workspace/RUNBOOK.md) · [追加式WORKLOG](../../workspace/WORKLOG.md) · [输入与来源](inputs.json)\n\n'
        text += '## 最新训练\n\n近1M为原生50-update完成episode滑窗日志的均值；不是完整训练集离线评估。相邻点重叠，不作独立样本。\n\n|方法|累计环境步|训练SR|训练SPL|状态|\n|---|---:|---:|---:|---|\n'
        names = {'qwen01':'Qwen128 β.1','A':'A Qwen128 β.03','B':'B Qwen256 β.03','coverage256':'覆盖256','coverage32':'覆盖32','C':'几何128'}
        for case in ['qwen01','A','B','coverage256','coverage32','C']:
            r = summary[case]
            state = current['jobs'][readout['runs'][case]['job_id']+'.stdct-mgmt-02']['job_state']
            text += f"|{names[case]}|{r['step']:,}|{r['sr']:.2f}%|{r['spl']:.2f}%|{state}|\n"
        text += '\n覆盖256已于11月5日21:45达到PBS时限，日志172,599,296步；最后可用权重172,544,000步。算法cap仍300M，不把一轮墙钟预算当训练完成。\n\n'
        text += 'Qwen：A在36.415M的近1M窗口比同预算基线SR/SPL高0.41/0.46pp，但近3M又低0.79/1.01pp；B在31.779M近3M比两覆盖两指标均高，仍低于基线。β.1此前短期领先未持续。三Qwen统一29.428M近3M，SR/SPL均未超过基线。原训练/续跑reset历史不同，单种子日志不证明奖励因果收益。\n\n'
        text += '[完整训练与1M/2M/3M同预算窗口](evidence/logs/training_readout_20261107/snapshot_130555/readout.json) · [独立复核](evidence/logs/training_readout_20261107/snapshot_130555/validation.json)\n\n'
        text += '## 已完成完整验证\n\n每组4200任务/14场景、6环境/max500/seed100/hash0；任务/目标/起点已逐条匹配。不同训练步数，不是同预算方法排名。\n\n|方法|训练步数|SR|SPL|\n|---|---:|---:|---:|\n'
        for key, label in [('baseline','冻结视觉基线'),('coverage256_previous','覆盖256'),('coverage256_143360000','覆盖256'),('coverage256_146944000','覆盖256'),('coverage256_150528000','覆盖256')]:
            r = comparison['cases'][key]
            text += f"|{label}|{r['training_step']:,}|{100*r['success_rate']:.2f}%|{100*r['spl']:.2f}%|\n"
        old32 = json.loads((ROOT/'logs/gibson_coverage_latest_eval_20261103/coverage32/result.json').read_text())
        text += f"|覆盖32|{old32['training_step']:,}|{100*old32['success_rate']:.2f}%|{100*old32['spl']:.2f}%|\n"
        text += '\n四个已列覆盖256保存点中，SR最好125.952M（87.57%）、SPL最好146.944M（56.24%）。新143.360M/150.528M都未超过125.952M的两项成绩。公开完整SIGN权重另有4200 val SR86.00%/SPL53.01%，原记录未显式hash0，不冒充这里的逐任务成对记录。\n\n'
        text += '[五组完整对照](evidence/logs/gibson_coverage256_candidates_eval_20261105/comparison.json) · [逐条复核](evidence/logs/gibson_coverage256_candidates_eval_20261105/results_review_20261107.json)\n\n'
        text += '125.952M保存时训练单50-update窗82.71/45.82%，近1M86.31/49.18%、近3M88.23/50.71%；与其val87.57/53.30%分开解释。[训练参考](evidence/logs/training_readout_20261107/coverage256_125952000_training_reference.json)。\n\n'
        text += '## 新提交的选点验证\n\n选点仅使用训练曲线和明确的125.952M参考点；加载完整导航权重，评估时关闭探索bonus、Qwen worker和Qwen图片历史采集。\n\n|实验|保存步数|作业|截面状态|新val SR/SPL|\n|---|---:|---|---|---|\n'
        for family_name, family in current['families'].items():
            for row in family['gpu_jobs']:
                case = row['case']
                label = names.get(case, '覆盖32')
                value = f"{100*row['result']['success_rate']:.2f}/{100*row['result']['spl']:.2f}%" if row['complete'] else '未完成，不填零分'
                text += f"|{label}|{row['step']:,}|{row['job_id'].split('.')[0]}|{row['state']}|{value}|\n"
        text += '\nQwen分别选20.480M/36.352M/29.696M；覆盖32选76.288M/125.952M/151.040M。覆盖32125.952M与覆盖256步数相同，但续跑历史不同，仍非严格因果对照。CPU汇总的H是afterok依赖；实际当前状态见[publication_state.json](publication_state.json)，旧提交状态回执仅代表其记录时点。\n\n'
        text += '## 全量失败诊断\n\n[可离线打开的总体报告](evidence/logs/sign_failure_replay_20261104/analysis/index.html) · [73案例/人审表](evidence/logs/sign_failure_replay_20261104/analysis/review/index.html)。三组各4200重放与原11字段逐条一致，12600 trace和1991视频已在服务器完整审计。失败数基线631、覆盖256522、覆盖32712；失败中从未进入1m分别89.70/89.08/92.70%。闭环/受阻是非互斥行为候选，不是人工病因比例；必要回访不自动算冗余。人工标签保持空，17条AI笔记是目的性样本，不是人工真值。\n\n'
        text += '本资料保留选中topdown/接触表图像、CSV/JSON、源代码、规则和审计；完整视频、原始RGB/trace、模型/场景/环境留服务器。浏览页的视频位置已明确转成服务器来源文字，原HTML另存.server.html；未伪造完整可下载相机证据。0.1m二维覆盖有投影/高度限制，不能把零新增等同没有新RGB信息。\n\n'
        text += '## 运行代码与复现\n\n|续跑代码分支|固定源码commit|\n|---|---|\n'
        for branch, commit in CODE_BRANCHES.items():
            text += f'|[{branch}](https://github.com/yiichu03/SIGN/tree/{branch})|[{commit[:7]}](https://github.com/yiichu03/SIGN/commit/{commit})|\n'
        text += '\n这些代码分支已核对与origin一致。运行目录保持固定HEAD，不为取得资料而pull文档提交。新增readout/评估/诊断/PBS脚本在evidence/logs对应批次归档；服务器绝对路径是来源定位，不代表仓库存在同路径。历史命令不意味着应重复提交训练/评估。\n\n'
        text += '离线完整性核验（仅CPU、无需模型/场景，不提交作业）：\n\n```bash\npython3 docs/experiments/qwen128-reward/ablations/progress_20261107/scripts/publish_update.py --tree . --check-only\n```\n\n'
        text += 'CSV/JSONL等较大表使用确定性gzip，inputs.json记录原字节SHA与编码；未上传checkpoint、TB二进制、环境或场景。根四文档由服务器维护源生成，WORKLOG保持旧发布前缀；推送回执另追加服务器日志，不为包含回执循环生成提交。\n'
        (self.folder/'README.md').write_text(text)


def check(tree, fallback_tree=None):
    package, folder = tree/PACKAGE, tree/RELATIVE
    manifest = json.loads((package/'publication_manifest.json').read_text())
    for name, item in manifest.items():
        raw = (package/name).read_bytes()
        assert len(raw) == item['bytes'] and sha(raw) == item['sha256'], name
    inputs = json.loads((folder/'inputs.json').read_text())
    copied = {}
    compressed = 0
    for name, item in inputs.items():
        raw = (folder/name).read_bytes()
        assert sha(raw) == item['published_sha256'], name
        if item['encoding'] == 'gzip':
            raw = gzip.decompress(raw)
            compressed += 1
        if item['encoding'] in ['identity', 'gzip']:
            assert sha(raw) == item['source_sha256'] and len(raw) == item['source_bytes'], name
            copied[item['source']] = raw
    info = json.loads((folder/'publication_info.json').read_text())
    prefix = (package/'workspace/WORKLOG.md').read_bytes()[:info['previous_worklog']['bytes']]
    assert sha(prefix) == info['previous_worklog']['sha256']
    recomputed = 0
    evaluation_rows = {}
    eval_batches = ['gibson_coverage_latest_eval_20261103', 'gibson_baseline_final_eval_20261103',
                    'gibson_coverage256_peak_eval_20261105', 'gibson_coverage256_candidates_eval_20261105', *FAMILIES]
    for source, raw in copied.items():
        if not any(source.startswith(str(ROOT/'logs'/batch)+'/') for batch in eval_batches):
            continue
        if not source.endswith('/result.json') or 'success_rate' not in raw.decode(errors='ignore'):
            continue
        result = json.loads(raw)
        if result.get('episodes') != 4200:
            continue
        parent = str(Path(source).parent/'episodes')+'/'
        rows = {}
        for path, payload in copied.items():
            if path.startswith(parent) and path.endswith('.jsonl'):
                for line in payload.decode().splitlines():
                    row = json.loads(line)
                    key = (row['scene_id'], row['episode_id'])
                    assert key not in rows
                    rows[key] = row
        assert len(rows) == 4200, source
        assert abs(statistics.mean(r['success'] for r in rows.values())-result['success_rate']) < 1e-10
        assert abs(statistics.mean(r['spl'] for r in rows.values())-result['spl']) < 1e-10
        evaluation_rows[source] = rows
        recomputed += 1
    baseline_source = str(ROOT/'logs/gibson_baseline_final_eval_20261103/baseline/result.json')
    baseline_rows = evaluation_rows[baseline_source]
    for source, rows in evaluation_rows.items():
        assert set(rows) == set(baseline_rows), source
        for key, row in rows.items():
            ref = baseline_rows[key]
            assert row['goal_sha256'] == ref['goal_sha256'], (source, key)
            assert max(abs(a-b) for a, b in zip(row['start_position'], ref['start_position'])) < 1e-6
    secret = re.compile(rb'-----BEGIN [A-Z ]*PRIVATE KEY-----|ghp_[A-Za-z0-9]{30,}|hf_[A-Za-z0-9]{30,}')
    for path in folder.rglob('*'):
        if not path.is_file():
            continue
        assert path.suffix not in ['.pth', '.pt', '.safetensors', '.glb', '.navmesh', '.mp4', '.zip']
        raw = path.read_bytes()
        assert len(raw) < 20*1024*1024, (path, len(raw))
        if path.suffix == '.gz':
            raw = gzip.decompress(raw)
        if path.suffix not in ['.png', '.pdf']:
            assert not secret.search(raw), ('Credential-shaped content', path)
        if path.suffix == '.py':
            compile(raw.decode(), str(path), 'exec')
    documents = [tree/'README.md', package/'README.md', package/'ablations/README.md', folder/'README.md']
    documents += [package/'workspace'/n for n in NAMES if n != 'WORKLOG.md']
    documents += [p for p in folder.rglob('*.html') if not p.name.endswith('.server.html')]
    link_count = 0
    for path in documents:
        text = re.sub(r'```.*?```', '', path.read_text(), flags=re.S)
        targets = re.findall(r'\[[^\]]*\]\(([^)]+)\)', text) if path.suffix == '.md' else re.findall(r'(?:href|src)=["\']([^"\']+)', text)
        for url in targets:
            if url.startswith(('https:', 'http:', '#', 'data:', 'mailto:')):
                continue
            target = Path(absolute(path.parent/unquote(url.strip('<>').split('#')[0])))
            exists = target.exists()
            if not exists and fallback_tree is not None:
                # Staging contains only this update; inherited links may point
                # to unchanged reports elsewhere in the publication worktree.
                relative = target.relative_to(tree)
                exists = (fallback_tree/relative).exists()
            assert exists, (path, url)
            link_count += 1
    if (tree/'.git').exists():
        assert not git(tree, 'diff', RUNTIME, '--', 'src', 'scripts', 'tests', 'exp_config', 'run_sim.py')
    return {'passed': True, 'package_manifest_files': len(manifest), 'copied_sources': len(inputs),
            'compressed_sources_verified': compressed, 'completed_4200_evaluations_recomputed': recomputed,
            'relative_links_checked': link_count, 'old_worklog_prefix_preserved': True,
            'runtime_code_unchanged': True, 'artifact_bytes': sum(p.stat().st_size for p in folder.rglob('*') if p.is_file())}


def build(tree):
    assert git(tree, 'rev-parse', 'HEAD').decode().strip() == BASE
    assert not git(tree, 'status', '--porcelain'), 'Publication worktree must be clean'
    assert git(tree, 'remote', 'get-url', '--push', 'origin').decode().strip() == 'git@github.com:yiichu03/SIGN.git'
    old_manifest = json.loads((tree/PACKAGE/'publication_manifest.json').read_text())
    for name, item in old_manifest.items():
        raw = (tree/PACKAGE/name).read_bytes()
        assert sha(raw) == item['sha256'] and len(raw) == item['bytes'], ('Changed old evidence', name)
    current = json.loads((HERE/'current.json').read_text())
    stage = HERE/datetime.now(TZ).strftime('staging_%H%M%S')
    stage.mkdir()
    shutil.copytree(tree/PACKAGE, stage/PACKAGE)
    shutil.copy2(tree/'README.md', stage/'README.md')
    builder = Builder(stage, current)
    builder.folder.mkdir(parents=True, exist_ok=False)
    builder.collect()
    builder.portable_html()
    old_prefix = builder.workspace(tree)
    builder.readme()
    for path in [stage/PACKAGE/'README.md', stage/PACKAGE/'ablations/README.md']:
        relative = 'ablations/progress_20261107/README.md' if path.parent == stage/PACKAGE else 'progress_20261107/README.md'
        text = path.read_text()
        first, sep, rest = text.partition('\n')
        path.write_text(first+'\n\n## 最新更新：2026-11-07\n\n[训练、完整验证、失败诊断、续跑代码及新评估提交]('+relative+')。下方保留此前日期的原记录。\n'+sep+rest)
    readme = stage/'README.md'
    readme.write_text('最新研究资料（2026-11-07）：[训练、验证结果、失败诊断与当前代码入口]('+str(RELATIVE/'README.md')+')。\n\n'+readme.read_text())
    write_json(builder.folder/'inputs.json', builder.inputs)
    write_json(builder.folder/'omitted_server_data.json', builder.omitted)
    write_json(builder.folder/'publication_info.json', {'created_at': now(), 'publication_base': BASE,
        'publication_branch': BRANCH, 'runtime_base_on_publication_branch': RUNTIME,
        'current_runtime_code_branches': CODE_BRANCHES, 'previous_worklog': old_prefix,
        'workspace_source_sha256': {n: sha((ROOT/n).read_bytes()) for n in NAMES},
        'cutoff_state_at': current['captured_at'], 'large_model_scene_camera_data_included': False})
    manifest = {str(p.relative_to(stage/PACKAGE)): {'sha256': sha(p.read_bytes()), 'bytes': p.stat().st_size}
                for p in sorted((stage/PACKAGE).rglob('*')) if p.is_file() and p != stage/PACKAGE/'publication_manifest.json'}
    write_json(stage/PACKAGE/'publication_manifest.json', manifest)
    return install_stage(stage, tree)


def install_stage(stage, tree):
    verified = check(stage, fallback_tree=tree)
    write_json(HERE/'staging_check.json', verified)
    changed = []
    for source in sorted(stage.rglob('*')):
        if not source.is_file():
            continue
        relative = source.relative_to(stage)
        assert relative == Path('README.md') or str(relative).startswith(str(PACKAGE)+'/')
        target = tree/relative
        if not target.exists() or sha(target.read_bytes()) != sha(source.read_bytes()):
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
            changed.append(str(relative))
    write_json(HERE/'build_receipt.json', {'built_at': now(), 'stage': str(stage), 'tree': str(tree),
        'base': BASE, 'changed_files': changed, 'verification': verified})
    return check(tree)


def resume(stage, tree):
    assert stage.parent == HERE and stage.name.startswith('staging_')
    assert git(tree, 'rev-parse', 'HEAD').decode().strip() == BASE
    assert not git(tree, 'status', '--porcelain'), 'Publication worktree must be clean'
    assert git(tree, 'remote', 'get-url', '--push', 'origin').decode().strip() == 'git@github.com:yiichu03/SIGN.git'
    builder = Builder(stage, json.loads((HERE/'current.json').read_text()))
    builder.inputs = json.loads((builder.folder/'inputs.json').read_text())
    for name, item in builder.inputs.items():
        if item['encoding'] != 'portable_html_no_videos' and not name.endswith('.server.html'):
            builder.mapping[absolute(item['source'])] = builder.folder/name
    builder.copy(Path(__file__).resolve(), builder.folder/'scripts/publish_update.py')
    previous = builder.workspace(tree)
    write_json(builder.folder/'inputs.json', builder.inputs)
    info_path = builder.folder/'publication_info.json'
    info = json.loads(info_path.read_text())
    assert info['previous_worklog'] == previous
    info['workspace_source_sha256'] = {n: sha((ROOT/n).read_bytes()) for n in NAMES}
    info['resumed_at'] = now()
    write_json(info_path, info)
    manifest = {str(p.relative_to(stage/PACKAGE)): {'sha256': sha(p.read_bytes()), 'bytes': p.stat().st_size}
                for p in sorted((stage/PACKAGE).rglob('*')) if p.is_file() and p != stage/PACKAGE/'publication_manifest.json'}
    write_json(stage/PACKAGE/'publication_manifest.json', manifest)
    return install_stage(stage, tree)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--tree', type=Path)
    parser.add_argument('--capture-only', action='store_true')
    parser.add_argument('--check-only', action='store_true')
    parser.add_argument('--resume-stage', type=Path)
    args = parser.parse_args()
    if args.capture_only:
        data = capture()
        print(json.dumps({'captured_at': data['captured_at'], 'families': {
            n: [(r['case'], r['state'], r['complete']) for r in f['gpu_jobs']]
            for n, f in data['families'].items()}}, indent=2))
    else:
        assert args.tree is not None
        if args.resume_stage:
            result = resume(args.resume_stage.resolve(), args.tree.resolve())
        else:
            result = check(args.tree.resolve()) if args.check_only else build(args.tree.resolve())
        print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
