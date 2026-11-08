# 原A的E1–E6推理消融

本批在独立分支`phase2/qwen-arbitration-six-ablation`开发，导航固定Coverage256125.952M/原ckpt245，不训练PPO。策略运行提交`e9396ac`；旧A源码ffc177c和完整结果原样保留。

[预先固定的单因素方案与放行门](PLAN.md)，[实际CPU合并配置](evidence/effective_settings_cpu.json)，[原A155仲裁审计](evidence/original_A_summary.json)，[资源记录](evidence/resources_before.json)。

原A：SR88.428571%、SPL53.715613%，155次有效选择、0回退，137LEFT/18KEEP/0RIGHT；155次均P(RIGHT)<P(LEFT)。相对matched-scan rule的SR88.595238%/SPL53.775092%，A救回2/误伤9，前缀支持1/8。重复val/单seed，不能把全部配对差异或扫描收益归因于Qwen。

实现沿用`RecoveryHarness`、`AgentSupport`、`QwenClient`与常驻worker，FP32/T1候选logits读出。E1保留raw ABC logits与映射后LEFT/RIGHT/KEEP概率，完整六块平衡且不触动策略随机数；E2真正移除目标图；E3置信度不足交还SIGN，明确记录confidence_keep。E4/E5派生预算68/56，仍全动作计入500，原A76。trainer、policy、metric、原A prompt及四组基础配置与ffc177c无差异。

单元/回归121项通过。GPU工程作业1533600（CFP/autox→batch_gpux，1A40/36CPU/240GB/6h）正在排队或运行；E组正式4200尚未通过工程门/尚未提交，不列伪造SR。旧排队检查1533598在运行前取消，原因是离线审计需保留合法安全KEEP，不是性能失败。

```bash
# 在已提交的固定运行树准备；输出目录必须全新。prepare不提交PBS。
python scripts/prepare_six_ablation.py --output /absolute/new_batch
# 执行该batch prepared_commands.json中的check命令。
# checks/check_summary.json通过后，方可执行E1–E6命令（GPUx最多4同时运行）。
# 完成后对比原A和规则；输出目录全新，旧结果只读。
python scripts/report_six_ablation.py --batch /absolute/new_batch --output /absolute/new_report
```

GPU检查包含原A155概率复现、全部六映射930次/无目标155次离线评分、E3原概率CPU重算；再在固定12个工程任务做native/off精确回归、旧A/新A动作与位姿精确回归、六组真实模型短测及E5命令/实际位姿角度。小集不用于调参或挑正SR。E3的qmax门槛预先固定为0.5、gap0.1，这不是经过校准的模型正确率。

全部参数、任务、prompt、原输入SHA、raw logits、概率、选向、KEEP/回退原因、时间、真实执行动作和位姿均由manifest/worker/telemetry留痕。后续正式报告同时列全量配对与前缀支持，E4/E5/E6的时长/扫描/触发效应不自动称为VLM语义收益。

根文档的自动生成发布副本：[STATUS](workspace/STATUS.md)、[RUNBOOK](workspace/RUNBOOK.md)、[WORKLOG](workspace/WORKLOG.md)、[AGENTS](workspace/AGENTS.md)。
