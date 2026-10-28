"""Generate/check the GS progress bundle; never submit, commit, or push."""
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
import argparse
import gzip
import hashlib
import io
import json
import re
import subprocess

ROOT = Path('/scratch/e1538633/liuyi')
TREE = ROOT / 'SIGN-habitat-gs-publication'
CODE = '95eef9bf497bc1d010c7a4b35030fdce4123dce7'
BRANCH = 'experiment/habitat-gs-imagenav'
REL = Path('docs/experiments/habitat-gs-imagenav')
OUT = TREE / REL
PILOT = ROOT / 'SIGN-habitat-gs/results/habitat_gs_20261026/job_1494770'
EVAL = ROOT / 'SIGN-habitat-gs/results/habitat_gs_full_val_20261028/job_1502487'
FILES = {}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def write(name, data, source=None, raw=None, refresh=False):
    path = OUT / name
    if path.exists() and path.read_bytes() != data:
        if name == 'workspace/WORKLOG.md':
            assert data.startswith(path.read_bytes()), 'Published WORKLOG prefix changed'
        else:
            assert refresh, 'Existing evidence changed: ' + name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    FILES[name] = {'sha256': sha(data), 'bytes': len(data)}
    if source is not None:
        FILES[name].update(source=str(source.relative_to(ROOT)), source_sha256=sha(raw), source_bytes=len(raw))


def copy(source, name, compressed=False, refresh=False, raw=None):
    raw = source.read_bytes() if raw is None else raw
    payload = raw
    if compressed:
        buffer = io.BytesIO()
        with gzip.GzipFile(filename='', mode='wb', fileobj=buffer, mtime=0) as stream:
            stream.write(raw)
        payload = buffer.getvalue()
        assert gzip.decompress(payload) == raw
    write(name, payload, source, raw, refresh)
    if compressed:
        FILES[name]['compression'] = 'gzip'


def check():
    manifest = json.loads((OUT / 'publication_manifest.json').read_text())
    assert sha((TREE / 'README.md').read_bytes()) == manifest['root_readme_sha256']
    expected = set(manifest['files']) | {'publication_manifest.json'}
    assert {str(p.relative_to(OUT)) for p in OUT.rglob('*') if p.is_file()} == expected
    for name, item in manifest['files'].items():
        data = (OUT / name).read_bytes()
        assert sha(data) == item['sha256'] and len(data) == item['bytes'], name
        assert len(data) < 12 * 1024 * 1024, name
        assert not name.endswith(('.pth', '.pt', '.glb', '.ply', '.navmesh', '.zip')), name
        if item.get('compression'):
            assert sha(gzip.decompress(data)) == item['source_sha256'], name
        if name.endswith(('.md', '.json', '.py', '.yaml', '.log', '.txt')):
            text = data.decode()
            assert not re.search(r'-----BEGIN [A-Z ]*PRIVATE KEY-----|gh[pousr]_[A-Za-z0-9]{25,}|github_pat_[A-Za-z0-9_]{30,}|sk-(?:proj-)?[A-Za-z0-9_-]{30,}', text), name
        if name.endswith('.md'):
            for target in re.findall(r'!?\[[^\]]*\]\(([^)]+)\)', data.decode()):
                if re.match(r'https?://|#', target):
                    continue
                assert not target.startswith('/'), (name, target)
                assert ((OUT / name).parent / target.split('#')[0]).resolve().exists(), (name, target)
        if name.startswith('workspace/'):
            current = (ROOT / Path(name).name).read_bytes()
            if name.endswith('WORKLOG.md'):
                assert current.startswith(data), 'Server WORKLOG does not extend its published snapshot'
    assert not subprocess.check_output(['git', 'diff', CODE, '--', 'src', 'exp_config', 'scripts', 'run_sim.py', 'ckpt'], cwd=TREE)
    changed = subprocess.check_output(['git', 'diff', '--name-only', CODE], cwd=TREE, text=True).splitlines()
    assert all(name == 'README.md' or name.startswith(str(REL) + '/') for name in changed), changed
    status = json.loads((OUT / 'evidence/full-val/runtime_status.json').read_text())
    if not status['result_available']:
        assert not (OUT / 'evidence/full-val/result.json').exists()
        assert '完整 SR／SPL 尚未产生' in (OUT / 'README.md').read_text()
    print('Publication verified:', len(manifest['files']), 'files,', sum(x['bytes'] for x in manifest['files'].values()), 'bytes')


def build():
    assert subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=TREE, text=True).strip() == CODE
    assert subprocess.check_output(['git', 'remote', 'get-url', '--push', 'origin'], cwd=TREE, text=True).strip() == 'git@github.com:yiichu03/SIGN.git'
    assert subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT / 'SIGN-habitat-gs', text=True).strip() == CODE
    for name in ['result.json', 'probe.json', 'probe.png', 'packages.txt']:
        copy(PILOT / name, 'evidence/pilot/' + name)
    copy(PILOT / 'eval/eval_run0_/config_of_eval.yaml', 'evidence/pilot/config_of_eval.yaml')
    copy(PILOT / 'eval/eval_run0_/log.txt', 'evidence/pilot/native_summary.log')
    for event in (PILOT / 'eval/tb').glob('events.out.tfevents.*'):
        copy(event, 'evidence/pilot/tensorboard/' + event.name)
    copy(ROOT / 'logs/habitat_gs_20261026/cpu_sensor_probe.json', 'evidence/pilot/cpu_sensor_probe.json')
    copy(ROOT / 'manifests/habitat_gs_imagenav_20261028.json', 'evidence/data/imagenav_manifest.json')
    copy(ROOT / 'logs/habitat_gs_20261028/download_submission.json', 'evidence/data/download_submission.json')
    copy(ROOT / 'logs/habitat_gs_20261028/download.pbs.log', 'evidence/data/download.log.gz', compressed=True)
    copy(EVAL / 'inputs.json', 'evidence/full-val/inputs.json')
    copy(EVAL / 'eval/eval_run0_/config_of_eval.yaml', 'evidence/full-val/config_of_eval.yaml')
    copy(ROOT / 'logs/habitat_gs_eval_20261028/preflight.log', 'evidence/full-val/preflight.log')
    copy(ROOT / 'logs/habitat_gs_eval_20261028/submission.json', 'evidence/full-val/submission.json')
    scheduler = subprocess.check_output(['qstat', '-xf', '1502487.stdct-mgmt-02'], text=True)
    selected = {}
    for key in ['job_state', 'queue', 'exec_host', 'resources_used.walltime', 'Exit_status']:
        match = re.search(r'^\s*' + re.escape(key) + r' = (.*)$', scheduler, re.M)
        if match:
            selected[key] = match.group(1)
    active_log = (EVAL / 'evaluation.log').read_bytes()
    matches = re.findall(rb'\b(\d+)/1900\b', active_log)
    completed = int(matches[-1]) if matches else 0
    timestamp = datetime.now(ZoneInfo('Asia/Singapore')).isoformat(timespec='seconds')
    available = (EVAL / 'result.json').is_file()
    # This publication is the ongoing-evaluation snapshot requested by the user.
    assert not available and selected['job_state'] == 'R' and completed < 1900
    status = {'captured_at': timestamp, 'job_id': '1502487.stdct-mgmt-02', 'scheduler': selected,
              'episodes_completed': completed, 'expected_episodes': 1900, 'result_available': available,
              'runtime_code_commit': CODE, 'partial_log_sha256': sha(active_log)}
    write('evidence/full-val/runtime_status.json', (json.dumps(status, indent=2) + '\n').encode(), refresh=True)
    copy(EVAL / 'evaluation.log', 'evidence/full-val/partial_evaluation.log.gz', compressed=True, refresh=True, raw=active_log)
    for name in ['AGENTS.md', 'STATUS.md', 'RUNBOOK.md', 'WORKLOG.md']:
        copy(ROOT / name, 'workspace/' + name, refresh=True)
    copy(Path(__file__), 'scripts/build_publication.py')
    report = f'''# SIGN 在 Habitat-GS 上的 ImageNav 进展

快照时间：**{timestamp}**。运行代码固定 **{CODE}**；本资料提交只增加说明、证据和文档快照。

## 已完成

- 独立环境：Python3.10、torch2.5.1+cu121、NumPy2.0.2、Habitat-GS0.3.3。第三方源码固定cb01b2fdf850ce3cab28ad00461a68ac7719f23f，Habitat-Lab固定1f7cfbdd。
- 已下载129场景静态ImageNav所需GS、navmesh、任务和配置：393文件，26,695,345,591字节。训练110场景／110000条，验证19场景／1900条；全部官方哈希和任务引用检查通过。[完整清单](evidence/data/imagenav_manifest.json)、[下载完成记录](evidence/data/download_submission.json)。
- A40实际GS渲染、目标图重渲染一致性及姿态保持、公开策略前向、连续移动／转向检查通过。[GPU探针](evidence/pilot/probe.json)、[CPU配置探针](evidence/pilot/cpu_sensor_probe.json)。

![左：当前视图；右：目标图](evidence/pilot/probe.png)

## 已完成的小样本评估

作业1494770正常退出；scene56的10条任务：**成功率10%（1/10），SPL5.3543%，view_match10%**。平均最终目标距离14.9221米，平均碰撞46.9次。[原精度结果](evidence/pilot/result.json)、[原生汇总](evidence/pilot/native_summary.log)、[实际配置](evidence/pilot/config_of_eval.yaml)。这是单场景小样本，不能代表完整评估。

## 完整验证集评估正在运行

作业 **1502487.stdct-mgmt-02**，GN-A40-023／A40，快照时 **{completed}/1900**；**完整 SR／SPL 尚未产生**。不把进度或局部任务当成完整结果。

使用公开 `ckpt/nav_model.pth` 与 `ckpt/safety_model.pth`，哈希见[输入清单](evidence/full-val/inputs.json)。19个场景1900条任务CPU检查均可达，测地距离最大误差0.0。6并行、seed100／PYTHONHASHSEED=0、每任务1次，原生确定性评估。

[运行状态快照](evidence/full-val/runtime_status.json) · [实际合并配置](evidence/full-val/config_of_eval.yaml) · [提交记录](evidence/full-val/submission.json) · [进行中日志截面（gzip）](evidence/full-val/partial_evaluation.log.gz)

服务器后续结果位于 `SIGN-habitat-gs/results/habitat_gs_full_val_20261028/job_1502487/result.json`；仅1900/1900完成且指标有限后生成。原trainer不保存逐条指标／轨迹，不能据聚合值恢复每条失败原因。

## 原始 SIGN 的边界与复现

相对作者基线dad87fe，src仅增加GS数据元数据补齐、相机向量类型转换，并移除一个未使用的nis导入；trainer、网络计算、动作、奖励、指标不变。沿用SIGN的128×128输入、连续动作、500步上限和1m成功判定。与官方GS示例256×256、离散动作、1000步协议不同；本实验为公开SIGN权重在完整GS val上的迁移评估。

[单场景配置](../../../exp_config/ppo_imagenav_habitat_gs.yaml) · [数据下载器](../../../scripts/habitat_gs/prepare_data.py) · [编译PBS](../../../scripts/habitat_gs/build.pbs) · [完整评估PBS](../../../scripts/habitat_gs/evaluate.pbs) · [预检与汇总入口](../../../scripts/habitat_gs/evaluate.py)

服务器从工作区根目录提交的命令模板（先检查已有作业并换新日志名，不重复提交当前作业）：

```bash
qsub -v GS_SOURCE_COMMIT=95eef9bf497bc1d010c7a4b35030fdce4123dce7 \\
  -o /scratch/e1538633/liuyi/logs/habitat_gs_eval_20261028/next_full_val.pbs.log \\
  SIGN-habitat-gs/scripts/habitat_gs/evaluate.pbs
```

数据固定[官方HF revision ea645385](https://huggingface.co/datasets/RukawaY/gs_scenes/tree/ea6453855938dd3d4395c4c449fedefb7e6603b7)。环境与资源路径来自当前服务器，移机需按[运行手册](workspace/RUNBOOK.md)调整。数据和权重保留各自来源，本包不新增它们。

[STATUS](workspace/STATUS.md) · [RUNBOOK](workspace/RUNBOOK.md) · [WORKLOG](workspace/WORKLOG.md) · [AGENTS](workspace/AGENTS.md)是服务器根维护源的生成快照；不在GitHub手工双份维护。[发布SHA清单](publication_manifest.json)、[生成器](scripts/build_publication.py)。
'''
    write('README.md', report.encode(), refresh=True)
    original = subprocess.check_output(['git', 'show', CODE + ':README.md'], cwd=TREE)
    addition = '\n\n## Habitat-GS experiment progress\n\n[Data readiness, pilot results, full-validation job status and reproduction](docs/experiments/habitat-gs-imagenav/README.md).\n'
    (TREE / 'README.md').write_bytes(original + addition.encode())
    manifest = {'generated_at': timestamp, 'repository': 'yiichu03/SIGN', 'branch': BRANCH,
                'runtime_code_commit': CODE, 'files': FILES,
                'root_readme_sha256': sha((TREE / 'README.md').read_bytes()),
                'excluded': ['new weights', 'scene assets', 'environments', 'raw camera sequences', 'complete results not yet available']}
    (OUT / 'publication_manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    check()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--check-only', action='store_true')
    if parser.parse_args().check_only:
        check()
    else:
        build()
