# SIGN / Gibson：训练、验证与失败诊断更新（2026-11-07）

资料状态截面：2026-11-07T13:58:35+08:00；训练指标使用11月7日13:05–13:06冻结事件，非实时看板。这是独立资料发布，训练源码/目录/作业没有为发布而修改；本分支源码保持d2352f0，实际续跑代码见下方分支。

[当前STATUS](../../workspace/STATUS.md) · [操作RUNBOOK](../../workspace/RUNBOOK.md) · [追加式WORKLOG](../../workspace/WORKLOG.md) · [输入与来源](inputs.json)

## 最新训练

近1M为原生50-update完成episode滑窗日志的均值；不是完整训练集离线评估。相邻点重叠，不作独立样本。

|方法|累计环境步|训练SR|训练SPL|状态|
|---|---:|---:|---:|---|
|Qwen128 β.1|29,427,712|86.26%|49.17%|R|
|A Qwen128 β.03|36,415,488|88.40%|52.71%|R|
|B Qwen256 β.03|31,778,816|87.53%|49.58%|R|
|覆盖256|172,599,296|87.80%|50.60%|F|
|覆盖32|158,072,832|89.55%|52.59%|R|
|几何128|75,855,872|88.97%|52.42%|R|

覆盖256已于11月5日21:45达到PBS时限，日志172,599,296步；最后可用权重172,544,000步。算法cap仍300M，不把一轮墙钟预算当训练完成。

Qwen：A在36.415M的近1M窗口比同预算基线SR/SPL高0.41/0.46pp，但近3M又低0.79/1.01pp；B在31.779M近3M比两覆盖两指标均高，仍低于基线。β.1此前短期领先未持续。三Qwen统一29.428M近3M，SR/SPL均未超过基线。原训练/续跑reset历史不同，单种子日志不证明奖励因果收益。

[完整训练与1M/2M/3M同预算窗口](evidence/logs/training_readout_20261107/snapshot_130555/readout.json) · [独立复核](evidence/logs/training_readout_20261107/snapshot_130555/validation.json)

## 已完成完整验证

每组4200任务/14场景、6环境/max500/seed100/hash0；任务/目标/起点已逐条匹配。不同训练步数，不是同预算方法排名。

|方法|训练步数|SR|SPL|
|---|---:|---:|---:|
|冻结视觉基线|74,240,000|84.98%|54.39%|
|覆盖256|125,952,000|87.57%|53.30%|
|覆盖256|143,360,000|86.52%|52.15%|
|覆盖256|146,944,000|86.36%|56.24%|
|覆盖256|150,528,000|86.33%|51.77%|
|覆盖32|48,128,000|83.05%|51.90%|

四个已列覆盖256保存点中，SR最好125.952M（87.57%）、SPL最好146.944M（56.24%）。新143.360M/150.528M都未超过125.952M的两项成绩。公开完整SIGN权重另有4200 val SR86.00%/SPL53.01%，原记录未显式hash0，不冒充这里的逐任务成对记录。

[五组完整对照](evidence/logs/gibson_coverage256_candidates_eval_20261105/comparison.json) · [逐条复核](evidence/logs/gibson_coverage256_candidates_eval_20261105/results_review_20261107.json)

125.952M保存时训练单50-update窗82.71/45.82%，近1M86.31/49.18%、近3M88.23/50.71%；与其val87.57/53.30%分开解释。[训练参考](evidence/logs/training_readout_20261107/coverage256_125952000_training_reference.json)。

## 新提交的选点验证

选点仅使用训练曲线和明确的125.952M参考点；加载完整导航权重，评估时关闭探索bonus、Qwen worker和Qwen图片历史采集。

|实验|保存步数|作业|截面状态|新val SR/SPL|
|---|---:|---|---|---|
|A Qwen128 β.03|36,352,000|1528937|F|82.38/52.97%|
|Qwen128 β.1|20,480,000|1528938|R|未完成，不填零分|
|B Qwen256 β.03|29,696,000|1528939|R|未完成，不填零分|
|覆盖32|125,952,000|1528994|R|未完成，不填零分|
|覆盖32|76,288,000|1528995|Q|未完成，不填零分|
|覆盖32|151,040,000|1528996|Q|未完成，不填零分|

Qwen分别选20.480M/36.352M/29.696M；覆盖32选76.288M/125.952M/151.040M。覆盖32125.952M与覆盖256步数相同，但续跑历史不同，仍非严格因果对照。CPU汇总的H是afterok依赖；实际当前状态见[publication_state.json](publication_state.json)，旧提交状态回执仅代表其记录时点。

## 全量失败诊断

[可离线打开的总体报告](evidence/logs/sign_failure_replay_20261104/analysis/index.html) · [73案例/人审表](evidence/logs/sign_failure_replay_20261104/analysis/review/index.html)。三组各4200重放与原11字段逐条一致，12600 trace和1991视频已在服务器完整审计。失败数基线631、覆盖256522、覆盖32712；失败中从未进入1m分别89.70/89.08/92.70%。闭环/受阻是非互斥行为候选，不是人工病因比例；必要回访不自动算冗余。人工标签保持空，17条AI笔记是目的性样本，不是人工真值。

本资料保留选中topdown/接触表图像、CSV/JSON、源代码、规则和审计；完整视频、原始RGB/trace、模型/场景/环境留服务器。浏览页的视频位置已明确转成服务器来源文字，原HTML另存.server.html；未伪造完整可下载相机证据。0.1m二维覆盖有投影/高度限制，不能把零新增等同没有新RGB信息。

## 运行代码与复现

|续跑代码分支|固定源码commit|
|---|---|
|[phase2/continue-coverage256-20261103](https://github.com/yiichu03/SIGN/tree/phase2/continue-coverage256-20261103)|[5a86720](https://github.com/yiichu03/SIGN/commit/5a86720fdcaf69a842ce40a660e2598f3fc052a0)|
|[phase2/continue-coverage32-20261103](https://github.com/yiichu03/SIGN/tree/phase2/continue-coverage32-20261103)|[2e5efba](https://github.com/yiichu03/SIGN/commit/2e5efbaf6caa4962e458e898d6c107e06a59138b)|
|[phase2/continue-qwen128-beta01-20261103](https://github.com/yiichu03/SIGN/tree/phase2/continue-qwen128-beta01-20261103)|[bb59545](https://github.com/yiichu03/SIGN/commit/bb59545f0c5663163e17cfe1dea37c441f09ccd2)|
|[phase2/continue-qwen-ablation-20261103](https://github.com/yiichu03/SIGN/tree/phase2/continue-qwen-ablation-20261103)|[1256ca7](https://github.com/yiichu03/SIGN/commit/1256ca70497592d2df178e6f77d10c14380689d8)|

这些代码分支已核对与origin一致。运行目录保持固定HEAD，不为取得资料而pull文档提交。新增readout/评估/诊断/PBS脚本在evidence/logs对应批次归档；服务器绝对路径是来源定位，不代表仓库存在同路径。历史命令不意味着应重复提交训练/评估。

离线完整性核验（仅CPU、无需模型/场景，不提交作业）：

```bash
python3 docs/experiments/qwen128-reward/ablations/progress_20261107/scripts/publish_update.py --tree . --check-only
```

CSV/JSONL等较大表使用确定性gzip，inputs.json记录原字节SHA与编码；未上传checkpoint、TB二进制、环境或场景。根四文档由服务器维护源生成，WORKLOG保持旧发布前缀；推送回执另追加服务器日志，不为包含回执循环生成提交。
