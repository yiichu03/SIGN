# 原A的E1–E6推理消融

独立分支`phase2/qwen-arbitration-six-ablation`；运行固定`e9396ac0c989ea515edcbd7f8d0085be38f818e7`，资料提交可继续前进，运行树不pull。导航权重固定Coverage256125.952M/原ckpt245，SHA`988c9ecc5b0c704e9a4780f636739aec17cbd323d613f0fbdde4699296886c2c`；6env/seed100/hash0/max500，不训练PPO，不改旧A、旧结果和既有训练。

## 六组完整4200结果（2026-11-09）

E1–E6均已完成；原PBS快照为F/Exit0，job1533627–1533632。原A SR88.428571/SPL53.715613%，matched-scan rule88.595238/53.775092%；均使用相同125.952M checkpoint。

|实验|SR|SPL|触发/完成仲裁|LEFT/RIGHT/KEEP|对A救回/误伤|对规则救回/误伤|
|---|---:|---:|---:|---:|---:|---:|
|E1|88.357143%|53.664525%|161/155|51/51/53|13/16|8/18|
|E2|88.619048%|53.781069%|152/149|147/2/0|8/0|4/3|
|E3|87.928571%|53.476922%|173/168|11/0/157|7/28|6/34|
|E4|88.333333%|53.679747%|160/155|136/0/19|7/11|8/19|
|E5|88.428571%|53.678132%|161/157|129/5/23|13/13|8/15|
|E6|88.428571%|53.644364%|177/170|140/2/28|13/13|14/21|

E2去掉Qwen目标图后，相对A净多8成功（+0.190476pp），相对匹配扫描规则净多1成功（+0.023810pp）。E2仍147LEFT/2RIGHT；与A的模型决策首次动作前缀支持为7救回/0误伤，与规则为2/2。完整配对结果与模型贡献证据分开呈现。E4/E5/E6的参数变化未超过原A整体SR，E3多数KEEP降低了SR。六组worker技术错误0；E6的170仲裁含169有效模型选择及1无效视觉证据安全KEEP。

[完整汇总与动作前缀归因](evidence/formal_review/summary.json)、[50400行逐任务配对CSV](evidence/formal_review/paired.csv)、[完成时PBS状态](evidence/formal_review/pbs_status.json)、[本次逐episode指标复核](evidence/formal_review/publication_verification.json)。各组原始result.json发布于[evidence/final_results](evidence/final_results)。救回/误伤是同任务结果配对，人工原因标签留空。E4/E5/E6动作时长、扫描角度和触发变化不自动称为VLM语义收益；完整4200为既有验证集，单种子结果。

原提交均CFP/autox、1A40/36CPU240GB/6h；用户随后把E5/E6排队任务移到auto→batch_gpu，ID与源码/预算不变。实际PBS用时依次2:18:35、2:11:31、1:55:46、1:03:20、1:06:13、2:10:51。CPU1533635的正式汇总已生成。旧任务/输出未重跑或覆盖。[原提交命令](evidence/formal_submissions.json)、[初始状态快照](evidence/initial_job_states.json)保留为历史。

下一轮已批准的[P1–P4实现和当前状态](../qwen-intervention-memory/README.md)将区分固定方向、仅扫描及扫描前短时历史介入判断，尚无GPU短测/正式结果。

## 已完成的审计与GPU检查

[预先固定方案与技术门](PLAN.md)、[原A155仲裁/概率审计](evidence/original_A_summary.json)、[实际执行命令审计](evidence/original_A_executed_commands.json)。155仲裁全部有效、无回退，155次均P(RIGHT)<P(LEFT)，均值LEFT.427395/RIGHT.244934/KEEP.327671。39次逻辑分歧均改变了相对交替规则反事实的真实首命令；其中32处有与rule一致的动作/位姿前缀及真实分歧。总体相对rule2救回9误伤，仅1/8有该前缀支持；其余不直接归模型。原A有5次触发扫描未完成，不能把155称作总触发数。

121项CPU测试通过：旧恢复74、旧四方案18、原单图14、新六方案15；[实际合并配置](evidence/effective_settings_cpu.json)核实6env/seed100/max500/HFOV90。GPU工程1533600 Exit0/18:47，[完整工程报告](evidence/gpu_check_summary.json)：原A155选择全复现、最大概率差6.813e-6；三协议真实token/batch/solo/生成位置验证通过；12任务新旧A/native-off动作/位姿/指标精确一致；六组真实模型短测均0技术错误，E5实际左右60°、恢复60°并回到原朝向，E4/E5动作预算68/56。12任务只验实现，不挑正SR、不据此声明总体效果。

[离线完整结果](evidence/offline/summary.json)、[CSV](evidence/offline/decisions.csv)、[输入/原事件/概率/logits记录](evidence/offline/records.json)：

|组|原155输入的选向（不是导航结果）|诊断|
|---|---|---|
|A重放|137LEFT/18KEEP|全155与原选择一致|
|E1预定单映射|51LEFT/51RIGHT/53KEEP|全六映射930次中raw A926、C4；155组方向一致0，表面平衡来自映射，不能当看图能力提升|
|E2|154LEFT/1RIGHT|较原19次变更，仍明显LEFT偏好|
|E3|10LEFT/145KEEP|145次confidence_keep；较原127次变更，门槛不是校准正确率|

输入为复用原A155真实仲裁，不是独立泛化测试。E1正式每次只用一次预定映射，不平均六次/不挑最有利；完整6调用块每标签/方向各2次，SHA排序的不足6尾块报告实际频数，不保证每个局部前缀最均匀。最初PLAN“尾块最小偏差”表述过强，原件保留并在此/RUNBOOK纠正；映射算法/参数未改，不据评分调顺序。所有偏置和负结果保留。

## 数据流与最小改动

同一[RecoveryHarness](../../../src/inference_recovery.py)按RGB/实际动作历史检测停滞→真实扫描→[AgentSupport](../../../src/recovery_agent.py)绑定图片角色→复用[QwenClient](../../../src/qwen_client.py)/[worker](../../../scripts/recovery_worker.py)→FP32/T1候选logits→LEFT/RIGHT有限恢复或KEEP交还SIGN。E1只增加[选项映射](../../../src/recovery_options.py)，raw ABC logits与语义概率分开；E2实际只有CURRENT/LEFT/RIGHT三图；E3只在读出后加门；E4–E6通过原控制器参数改变动作/扫描/检测。

[中央实验开关](../../../scripts/memory_four_arm.py)、[新增默认兼容配置](../../../src/config/inference_six_ablation.yaml)、[三个最小prompt变体](../../../scripts/prompts/)、[新单元测试](../../../tests/test_six_ablation.py)。原A prompt/四方案基础配置、trainer/policy/metric与ffc177c无差异；STOP优先、每步GRU与真实执行动作回填、真实masks、500总步上限均保留。每次调用输入SHA/role/context/映射、raw logits/概率、KEEP/回退原因、时间和执行动作/位姿可追溯。

## 复现

在已提交固定树运行以下命令（仅示例，不要对现有输出重跑）：

```bash
python scripts/prepare_six_ablation.py --output /absolute/new_batch
# prepare只生成manifest和命令；先执行prepared_commands.json中的check命令。
# 检查passed后执行E1–E6命令；不可用短集SR筛选。
python scripts/report_six_ablation.py --batch /absolute/new_batch --output /absolute/new_report
```

[固定源码/资产manifest](evidence/source_manifest.json)、[任务与checkpoint](evidence/tasks.json)、[实际提交门检查脚本](launch/submit_formal.py)、[CPU汇总脚本](launch/report.pbs)。tasks/prepared_commands的submitted=False是准备时快照，真实状态以formal_submissions.json为准，不能为改布尔破坏固定assets。原图与完整worker输入token审计保留服务器原路径，Git仅发布轻量结果/manifest，不包含权重/环境/场景/大相机流，不自动ZIP。

根文档为服务器维护源，本轮最新自动生成副本：[STATUS](../qwen-intervention-memory/workspace/STATUS.md)、[RUNBOOK](../qwen-intervention-memory/workspace/RUNBOOK.md)、[WORKLOG](../qwen-intervention-memory/workspace/WORKLOG.md)、[AGENTS](../qwen-intervention-memory/workspace/AGENTS.md)。
