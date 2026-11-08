# 原A的E1–E6推理消融

独立分支`phase2/qwen-arbitration-six-ablation`；运行固定`e9396ac0c989ea515edcbd7f8d0085be38f818e7`，资料提交可继续前进，运行树不pull。导航权重固定Coverage256125.952M/原ckpt245，SHA`988c9ecc5b0c704e9a4780f636739aec17cbd323d613f0fbdde4699296886c2c`；6env/seed100/hash0/max500，不训练PPO，不改旧A、旧结果和既有训练。

## 已提交正式4200，结果尚未出

|实验|单一因素|PBS job|正式SR/SPL|触发/仲裁/选择/配对救回误伤|
|---|---|---|---|---|
|原A（已完成）|目标条件LEFT/RIGHT/KEEP仲裁|1532958|88.428571% / 53.715613%|160触发/155仲裁；137LEFT、18KEEP、0RIGHT；相对rule2救回/9误伤，前缀支持1/8|
|matched-scan rule（已完成）|交替方向，24扫描+6转向+8前进|1532001批次|88.595238% / 53.775092%|原A比较参考，非新作业|
|E1|ABC对方向的六排列平衡映射|1533627|待完整4200，尚未验证|待正式输出|
|E2|仅Qwen移除GOAL（SIGN仍有目标）|1533628|待完整4200，尚未验证|待正式输出|
|E3|pmax≥0.5且gap≥0.1，否则KEEP|1533629|待完整4200，尚未验证|待正式输出|
|E4|forward8→4；派生最大干预68|1533630|待完整4200，尚未验证|待正式输出|
|E5|scan/recovery90→60°；派生最大干预56|1533631|待完整4200，尚未验证|待正式输出|
|E6|停滞窗口16→12|1533632|待完整4200，尚未验证|待正式输出|

六组CFP/autox→batch_gpux，每组1A40/36CPU/240GB/6h；GPUx最多4R，其余排队，原训练1511148不动。参考原A实测1:47:28，估计每组约1–2小时计算、6h为保守上限，排队时间未知，不保证六组同日出齐。[实际提交命令/输出/源码SHA](evidence/formal_submissions.json)，[提交后PBS状态快照](evidence/initial_job_states.json)，[正式前余额](evidence/resources_before_formal.json)。

CPU1533635（1CPU6GB30min，afterany依赖六组）会自动生成服务器`logs/qwen_six_ablation_20261108/runtime_e9396ac/formal_review/{summary.json,paired.csv,pbs_status.json}`。其H是等待依赖，勿解除。失败/缺失组保持未验证，不自动重跑。旧4200只读；单seed/反复使用val，配对胜负不是因果证明，无模型实际改变不能归功Qwen。最终报告同时保留与A及rule的总体配对、同观测选向差异、首次真实动作差异与动作/位姿前缀支持；E4/E5/E6的动作时长/扫描/触发变化不自动称作VLM语义收益。

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

根文档为服务器维护源，以下自动生成副本：[STATUS](workspace/STATUS.md)、[RUNBOOK](workspace/RUNBOOK.md)、[WORKLOG](workspace/WORKLOG.md)、[AGENTS](workspace/AGENTS.md)。
