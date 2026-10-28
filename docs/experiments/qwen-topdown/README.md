# Qwen 单图top-down评分（Gibson）

当前代码：`phase2/qwen-topdown-judge @ 4cc7257`。每张图独立评价，一次可将8个独立会话组成batch；无同任务分组要求。本包保存2026-10-28已完成的离线实验，尚未接入PPO或改动trainer、采样、coverage reward。

## 看图片和分数

- **[9B / 2B 同图对照：16张](reports/pilot_9b_2b.md)**：Edgemere、Denmark各8条同任务重复轨迹。
- **[2B 跨场景 / 不同任务：16张](reports/diverse_2b.md)**：8个新场景各2个不同任务。
- [速度记录与原始输出](reports/latency.md)：保留4模型生成式JSON测速，明确区分当前真实logits评分。
- [图片来源与SHA索引](images/index.json)：32张不同top-down图去重存储，另保留4张overview。

## 当前评分方法与验证

[A/B/C评分prompt](prompts/coverage_abc_v1.txt)对应A=LOW、B=MEDIUM、C=HIGH。读取真实assistant回答位置的下一token原logits；当前tokenizer为A32/B33/C34，T=1对三候选softmax，`q=0.5*p_medium+p_high`。这些是三候选条件概率，不是校准的成功率；每图还记录全词表中ABC总概率candidate_mass。

同一模型只加载一次，独立batch预处理复用现有实现。新概率CLI默认FP32；原JSON生成与benchmark默认auto保持。最初BF16单张/batch概率最大差0.02936，检查阻止了产出；[失败run](evidence/failure_bf16/run.json)与[原错误日志](evidence/failure_bf16/pbs.log.gz)保留，没有提高阈值掩盖错误。FP32通过left padding/实际回答位置、单图与batch、排列不变性、forward与生成首步raw logits对照；生成只用于位置核验，正式分数不从JSON数字反推。

| 作业 | 模型 / 图片 | 结果 | batch/solo最大概率差 | 排列 / forward-generation差 |
|---|---|---|---:|---|
| 1503691 | 9B pilot16 | 16/16有效 | 1.74e-5 | 0 / 0 |
| 1503819 | 2B同图16 | 16/16有效 | 1.42e-5 | 0 / 0 |
| 1503973 | 2B跨场景16 | 16/16有效 | 2.23e-5 | 0 / 0 |

25项单测通过。[9B验证](evidence/probability/pilot_9b/verification.json)、[2B同图验证](evidence/probability/pilot_2b/verification.json)、[2B跨场景验证](evidence/probability/diverse_2b/verification.json)。用户给出“我感觉评分还挺不错的”的整体反馈；尚无冻结的逐图人工标签或独立准确率评估，离线评分也不证明训练收益。当前等待用户决定后续方向。

## 面积、动作与图片口径

manifest逐图提供action_count、new_area_m2，并计算/验证new_area_m2_per_action。面积由保存的mask新增有效格数×每像素米数平方重算，与轨迹动作数及CSV核对，**没有从覆盖率百分比推算平方米**。扣初始视野，统计3m/90°的二维可通行区视域并集。图片使用0.025m显示重建、固定初始高度切片和最多5cm的fog原点边界投影；这是导航网格代理，不是RGB表面积，也不同于训练reward的0.1m口径。原0.1m与显示mask、逐步XYZ/朝向/动作在[evidence/trajectories](evidence/trajectories)保留。

轨迹来自公开SIGN导航/安全权重的原生随机动作，不是Qwen控制。最多256动作或真实提前结束。没有中途时间/朝向标注，图片交叉不自动代表无效重复搜索。公开模型权重、场景、环境、第一人称RGB序列不在此包内。

## 复用入口

核心：[src/qwen_single_image.py](../../../src/qwen_single_image.py)；CLI：[scripts/score_qwen_single.py](../../../scripts/score_qwen_single.py)；可编辑prompt：[scripts/prompts/qwen_single_coverage_abc.txt](../../../scripts/prompts/qwen_single_coverage_abc.txt)；测试：[tests/test_qwen_single_image.py](../../../tests/test_qwen_single_image.py)。

在已配置qwen35的PBS GPU作业内，从仓库根执行（模型路径按本机填写，out必须全新）：

```bash
python scripts/score_qwen_single.py \
  --manifest docs/experiments/qwen-topdown/manifests/diverse.json \
  --prompt docs/experiments/qwen-topdown/prompts/coverage_abc_v1.txt \
  --model-dir /path/to/Qwen3.5-2B \
  --out results/my_qwen_scores --batch-size 8 --verify
```

[pilot manifest](manifests/pilot.json)与[diverse manifest](manifests/diverse.json)使用仓库内相对图片路径，可直接复用；只改prompt即可换评分角度，保持A/B/C映射。每次保存prompt内容SHA、图片副本、metadata、输入token/mask/grid、原logits与结果。原始审计JSON中的服务器绝对路径是当时输入的原文，保留以便追溯；仓库内图片位置以可移植manifest和图片索引为准。

[scripts](scripts)保存服务器端采集、导图、面积核对和PBS脚本快照，部分脚本依赖原服务器目录；不是新的Qwen调用框架。[旧八图同会话连通性证据](evidence/legacy_multimage_io)仅用于历史回溯，不属于当前单图评分协议。

## 文档维护与证据

[AGENTS](workspace/AGENTS.md)、[STATUS](workspace/STATUS.md)、[RUNBOOK](workspace/RUNBOOK.md)、[WORKLOG](workspace/WORKLOG.md)是服务器根四文档的自动生成快照，根文件仍是维护源；不要手工维护两份。已有覆盖奖励研究材料留在原位。[publication_manifest.json](publication_manifest.json)记录每个文件的SHA、大小与来源；构建脚本只生成/校验，不自动训练、评分或推送。
