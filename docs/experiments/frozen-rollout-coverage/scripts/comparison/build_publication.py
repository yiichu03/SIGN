"""Build/check an allowlisted result bundle; never submit jobs, commit or push."""
from pathlib import Path
from datetime import datetime, timezone, timedelta
import argparse
import gzip
import hashlib
import io
import json
import re
import subprocess

ROOT = Path('/scratch/e1538633/liuyi')
TREE = ROOT/'SIGN-coverage-publication'
REL = Path('docs/experiments/frozen-rollout-coverage')
OUT = TREE/REL
SOURCE = ROOT/'logs/gibson_coverage_comparison_20261027'
SUPPORT = ROOT/'logs/gibson_rollout_coverage_20261027'
CODE = '6983c91e20493ff25ff32c24df02b968cc34f701'
BRANCH = 'phase2/frozen-rollout-coverage'
FILES = {}

def sha(data):
    return hashlib.sha256(data).hexdigest()

def write(relative, data, source=None, refresh=False):
    path = OUT/relative
    if path.exists() and path.read_bytes() != data:
        if relative == 'workspace/WORKLOG.md':
            assert data.startswith(path.read_bytes()), 'Published WORKLOG must remain an exact prefix'
        else:
            assert refresh, 'Existing evidence changed: '+relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    FILES[relative] = {'sha256':sha(data), 'bytes':len(data)}
    if source:
        raw = source.read_bytes()
        FILES[relative].update(source=str(source.relative_to(ROOT)), source_sha256=sha(raw), source_bytes=len(raw))

def copy(source, relative, compressed=False, refresh=False):
    raw = source.read_bytes()
    payload = raw
    if compressed:
        buffer = io.BytesIO()
        with gzip.GzipFile(filename='',mode='wb',fileobj=buffer,mtime=0,compresslevel=6) as handle:
            handle.write(raw)
        payload = buffer.getvalue()
        assert gzip.decompress(payload) == raw
    write(relative, payload, source, refresh)
    if compressed:
        FILES[relative]['compression'] = 'gzip; original bytes verified'

def check():
    manifest = json.loads((OUT/'publication_manifest.json').read_text())
    assert sha((TREE/'README.md').read_bytes()) == manifest['root_readme_sha256']
    assert {str(p.relative_to(OUT)) for p in OUT.rglob('*') if p.is_file()} == set(manifest['files']) | {'publication_manifest.json'}
    for name, item in manifest['files'].items():
        data = (OUT/name).read_bytes()
        assert sha(data) == item['sha256'] and len(data) == item['bytes'], name
        if item.get('compression'):
            assert sha(gzip.decompress(data)) == item['source_sha256'], name
        if name.startswith('workspace/'):
            assert data == (ROOT/Path(name).name).read_bytes(), name
        assert len(data) < 12*1024*1024, name
        assert not name.endswith(('.pth','.pt','.glb','.navmesh','.zip')), name
        if name.endswith(('.md','.py','.yaml','.json','.pbs','.log','.txt')):
            text = data.decode('utf-8')
            assert not re.search(r'-----BEGIN [A-Z ]*PRIVATE KEY-----|gh[pousr]_[A-Za-z0-9]{25,}|github_pat_[A-Za-z0-9_]{30,}|sk-(?:proj-)?[A-Za-z0-9_-]{30,}',text), name
            if name.endswith('.md'):
                for target in re.findall(r'!?\[[^\]]*\]\(([^)]+)\)',text):
                    if re.match(r'https?://|#',target):
                        continue
                    assert not target.startswith('/'), 'Nonportable Markdown link: '+target
                    assert ((OUT/name).parent/target.split('#')[0]).resolve().exists(), (name,target)
    changed = subprocess.check_output(['git','diff','--name-only',CODE],cwd=str(TREE),text=True).splitlines()
    assert all(name == 'README.md' or name.startswith(str(REL)+'/') for name in changed), changed
    # Independent publication must never change runtime source/configuration.
    assert not subprocess.check_output(['git','diff',CODE,'--','src','exp_config','run_sim.py'],cwd=str(TREE))
    previous = subprocess.run(['git','show',CODE+':'+str(REL/'workspace/WORKLOG.md')],cwd=str(TREE),capture_output=True)
    if previous.returncode == 0:
        assert (OUT/'workspace/WORKLOG.md').read_bytes().startswith(previous.stdout)
    print('Publication verified:',len(manifest['files']),'files,',sum(v['bytes'] for v in manifest['files'].values()),'bytes',flush=True)

def build():
    assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=str(TREE),text=True).strip() == CODE
    assert subprocess.check_output(['git','remote','get-url','--push','origin'],cwd=str(TREE),text=True).strip() == 'git@github.com:yiichu03/SIGN.git'
    for name in ['full_val_comparison.json','baseline_eval_result.json','coverage_eval_result.json',
                 'eval_manifest.json','eval_config_audit.json','checkpoint_integrity.json','comparison_submission.json',
                 'scheduler_final.json','publication_runtime_status.json','descriptive_training_diagnostics.json']:
        copy(SOURCE/name,'evidence/comparison/'+name)
    for case in ['baseline','coverage']:
        copy(SOURCE/(case+'_eval.log'),'evidence/comparison/'+case+'_eval.log.gz',compressed=True)
        copy(SOURCE/('eval_'+case)/'eval_run0_/config_of_eval.yaml','evidence/config/eval_'+case+'.yaml')
        copy(SOURCE/('eval_'+case)/'eval_run0_/log.txt','evidence/comparison/'+case+'_native_summary.log')
        events = list((SOURCE/('eval_'+case)/'tb').glob('events.out.tfevents.*'))
        assert len(events) == 1
        copy(events[0],'evidence/comparison/tensorboard_'+case+'/'+events[0].name)
    for folder, prefix in [(SOURCE,'initial_1340'),(SOURCE/'latest_training_snapshot','latest')]:
        for name in ['training_comparison.json','matched_training_curves.png','matched_training_curves.pdf']:
            copy(folder/name,'evidence/training/'+prefix+'/'+name)
        if prefix == 'latest':
            for case in ['baseline','coverage']:
                copy(folder/(case+'_scalars.csv'),'evidence/training/latest/'+case+'_scalars.csv.gz',compressed=True)
    for name in ['unit_results.json','unit_tests.log','short_summary.json','short_results.json','scene_probe.json',
                 'config_audit.json','source_manifest.json','original_worktree_before.json','training_submission.json']:
        copy(SUPPORT/name,'evidence/validation/'+name)
    for name in ['test_coverage.py','probe_scene.py','run_short_checks.py','check_inputs.py','short_checks.pbs','train_personal.pbs']:
        copy(SUPPORT/name,'scripts/coverage/'+name)
    for name in ['analyze_training.py','evaluate_checkpoint.py','summarize_eval.py','baseline.pbs','coverage.pbs','build_publication.py']:
        copy(SOURCE/name,'scripts/comparison/'+name)
    copy(ROOT/'logs/gibson_frozen_encoder_20261026/train_personal.pbs','scripts/baseline/train_personal.pbs')
    for case, directory in [('baseline','SIGN/results/gibson_frozen_encoder_20261026/train_personal_8env'),
                            ('coverage','SIGN-frozen-rollout-coverage/results/gibson_rollout_coverage_20261027/train_personal_8env')]:
        configs = list((ROOT/directory).glob('train_run*/config_of_train.yaml'))
        assert len(configs) == 1
        copy(configs[0],'evidence/config/train_'+case+'.yaml')
    for name in ['AGENTS.md','STATUS.md','RUNBOOK.md','WORKLOG.md']:
        copy(ROOT/name,'workspace/'+name,refresh=True)
    timestamp = datetime.now(timezone(timedelta(hours=8))).isoformat(timespec='seconds')
    report = r'''# Frozen encoder：固定 rollout 覆盖奖励实验

当前结论：**weight=0.1 尚未显示成功率收益。** 同步数的完整 Gibson val 结果略低；这是一个训练种子、一个模型时点的观察，不能据此判定长期必然有害。

## 同阶段完整验证

两份模型均训练至 **9,216,000 环境步**（各自 ckpt.17），每组完成全部 **4,200 条 Gibson val**。seed=100、PYTHONHASHSEED=0、6 个环境、每条最多 500 步；原生确定性动作和公共 safety 权重加载行为均保留，评估不启用 coverage。两份实际配置仅模型路径、输出路径及对应命令元数据不同。

| 指标 | 冻结基线 | 覆盖奖励 weight=0.1 | 覆盖组减基线 |
|---|---:|---:|---:|
| 成功率 | 78.36%（3291/4200） | 77.48%（3254/4200） | −0.88 个百分点，少成功37条 |
| SPL | 51.98% | 50.10% | −1.88 个百分点 |
| view_match | 76.64% | 75.08% | −1.56 个百分点 |

评估作业1498509、1498510均已完成且Exit_status=0。验证结果在2026-10-27约14:30 +08:00生成。[完整精度结果](evidence/comparison/full_val_comparison.json)、[配置审计](evidence/comparison/eval_config_audit.json)、[checkpoint冻结审计](evidence/comparison/checkpoint_integrity.json)、[模型步数／SHA](evidence/comparison/eval_manifest.json)。权重文件保留在服务器。

原生评估器只保存汇总，不保存逐episode成败；不能恢复成对结果或进行McNemar检验。未做多训练种子检验，也未完成300M训练。

## 最新训练曲线与观察沿革

下图快照时间 **2026-10-27T14:24:40+08:00**，基线23,646,208步、覆盖组10,438,656步；图中只比较共同前10,438,656步。最近100万步的原生训练滑动指标均值：

| 指标 | 基线 | 覆盖组 | 差值 |
|---|---:|---:|---:|
| 训练成功率 | 86.17% | 84.75% | −1.42 个百分点 |
| 训练SPL | 48.23% | 48.38% | +0.15 个百分点 |
| 导航reward | 7.270 | 7.174 | −0.097 |

![相同步数训练曲线](evidence/training/latest/matched_training_curves.png)

[最新指标与区间统计](evidence/training/latest/training_comparison.json) · [PDF](evidence/training/latest/matched_training_curves.pdf) · [基线全部scalar CSV.gz](evidence/training/latest/baseline_scalars.csv.gz) · [覆盖组全部scalar CSV.gz](evidence/training/latest/coverage_scalars.csv.gz)

原生训练指标是50次update内已完成episode的滑动均值；图中粗线再用101点移动平均便于查看，表格使用原生值的区间均值。相邻点高度相关，不能视为独立样本。训练reward仍只记录环境导航奖励，不包含coverage bonus；训练指标也不等于验证集成功率。

13:40初次检查至共同9,488,384步时，最近100万步训练SR曾领先约0.78个百分点；更早区间亦有落后，整段训练SR曲线均值接近相等。14:24刷新后，领先关系反转。保留[初次快照](evidence/training/initial_1340/training_comparison.json)，不把早期小幅领先当成持续收益。

## 实验实现与固定设置

冻结基线代码dac8609；覆盖代码6983c91，仅改[src/metric.py](../../../src/metric.py)、[src/trainer.py](../../../src/trainer.py)、[新增YAML](../../../src/config/rollout_coverage.yaml)。两组均从公开checkpoint加载并冻结actor_critic.net.visual_encoder（42个状态项），其余模块按原初始化训练；保持原PPO/MRQ/RandomShift/Qc、seed100/hash0、8环境×256步、300M算法上限、个人项目A40／36CPU240GB／168h预算。两份9216000步模型encoder仍与公开权重逐位一致，参数全部有限。

覆盖是训练侧可行走区域的二维XZ视域并集代理，不输入Actor。初始视野只建立基线；重复观察不重复计数；episode重置清空，rollout边界不清空。mpp=0.10m、统计范围3m、FOV90°（匹配RGB）、weight=0.1。

每个固定rollout完成后、returns之前，各环境按真实episode边界独立分段，并在rollout末创建结算边界。每段只在末步加入 `bonus = weight * segment_new_area / H`，H=256；真实终止mask不变，不等待各环境同时结束。bonus独立记录在learner/coverage_*。

最新100万步平均bonus约0.130824/rollout，即每环境步约6.39e-5。信号量级较小只是待检验假设，尚未证明是当前未获益的原因。本轮没有调整权重或网络。

9项CPU边界测试和三组GPU短跑通过：初始／重复／重置、跨rollout、多episode结算位置、bonus总量、mask不变及weight0奖励不变；三组各40960步，42项encoder状态不变。[单测](evidence/validation/unit_tests.log)、[GPU短跑](evidence/validation/short_summary.json)、[朝向／遮挡代理检查](evidence/validation/scene_probe.json)。原同节点统计对照每步额外耗时约30.3%；长跑到相同9.216M步耗时基线20710s、覆盖26390s（+27.4%，不同节点，不作为纯统计开销隔离对照）。

## 运行状态、复现与来源

发布前核查时间及控制台步数见[运行状态快照](evidence/comparison/publication_runtime_status.json)：1496716、1497416均R；未停止、重启或更改两组训练。后续进展会超过本资料包的固定快照。

[基线训练PBS](scripts/baseline/train_personal.pbs) · [覆盖训练PBS](scripts/coverage/train_personal.pbs) · [基线评估PBS](scripts/comparison/baseline.pbs) · [覆盖评估PBS](scripts/comparison/coverage.pbs) · [评估程序](scripts/comparison/evaluate_checkpoint.py) · [训练曲线导出器](scripts/comparison/analyze_training.py) · [验证汇总器](scripts/comparison/summarize_eval.py)

本轮实际已执行命令为 `qsub baseline.pbs`／`qsub coverage.pbs`（作业ID见上），经由辅助程序调用原生run_sim.py。复现评估的命令形状如下；路径为示意，使用新的输出目录：

```bash
PYTHONHASHSEED=0 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 \
python run_sim.py --exp-config exp_config/ppo_imagenav_gibson.yaml,policy,reward,sensors,eval \
  --run-type eval --model-dir results/your_fresh_eval_directory \
  habitat_baselines.eval_ckpt_path_dir /path/to/the_same_step_checkpoint.pth
```

PBS及辅助脚本保留已执行版本中的服务器绝对路径，移到其他机器需重设路径，并自行准备Habitat环境、授权场景、任务数据和公开权重；不会自动下载数据或自动启动新实验。两组[实际训练与评估配置](evidence/config/)均已保存。全量训练指标以gzip发布，解压后的SHA记录在[发布清单](publication_manifest.json)。压缩的原生评估控制台日志和原始评估TensorBoard事件也在evidence/comparison/。

[工作区状态](workspace/STATUS.md) · [操作日志](workspace/WORKLOG.md) · [运行手册](workspace/RUNBOOK.md) · [稳定规则](workspace/AGENTS.md)。四文档是liuyi根维护源的自动生成快照，文中服务器路径用于定位未公开资源；发布副本WORKLOG保持追加关系。

本包不含checkpoint、场景、Python环境或原始相机数据；既有第一阶段Qwen资料不在本轮重建。运行时代码仍分别是dac8609和6983c91，本次发布只增加资料及导航。
'''
    write('README.md',report.encode(),refresh=True)
    top = TREE/'README.md'
    original = subprocess.check_output(['git','show',CODE+':README.md'],cwd=str(TREE))
    addition = b'\n\n## Frozen-encoder rollout-coverage experiment\n\n'
    addition += '[Results, matched-step Gibson evaluation, training curves and reproduction](docs/experiments/frozen-rollout-coverage/README.md).\n'.encode()
    top.write_bytes(original+addition)
    manifest = {'generated_at':timestamp,'repository':'yiichu03/SIGN','branch':BRANCH,'runtime_code_commit':CODE,
                'workspace_source':'/scratch/e1538633/liuyi','files':FILES,
                'root_readme_sha256':sha(top.read_bytes()),
                'excluded':['model weights','scene assets','environments','raw camera data','live training event streams'],
                'notes':['Latest immutable CSV exports published; initial full CSV retained on server.',
                         'Manifest excludes its own hash; documents are generated server snapshots.']}
    (OUT/'publication_manifest.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False)+'\n')
    check()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--check-only',action='store_true')
    if parser.parse_args().check_only:
        check()
    else:
        build()
