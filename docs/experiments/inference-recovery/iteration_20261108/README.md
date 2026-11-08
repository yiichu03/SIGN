# Qwen2B推理恢复：迭代与固定版本验证

资料截面：2026-11-08T08:56:28+08:00。行为固定提交`f0e093c4d52c595c71f109d69cbf67ae7fbe3daa`；资料提交可以继续前进，运行快照保持不变。

[逐轮机器可读结果](results.json) · [文件SHA与服务器来源](inputs.json) · [当前STATUS生成副本](workspace/STATUS.md) · [追加式操作记录](workspace/WORKLOG.md)

## 方法与控制

导航模型使用覆盖256的125,952,000步checkpoint；不重新训练，不把Qwen接入PPO奖励。原SIGN继续决策，只有RGB与实际动作历史出现持续受阻迹象时才触发。24个实际原地转向动作获取左右90度RGB；两张图独立输入Qwen3.5-2B，FP32/T=1，读取No/Unknown/Yes真实答案token logits。正问通行性与反问障碍物须同向支持，默认侧在两问中都判可通行时保持规则；其余证据不足回退匹配规则。最多两次恢复，每次90度转向及1.6m短尝试；连扫描最多76个覆盖动作都计入原500步，原STOP/masks/GRU保留。

比较原生off、同扫描/同动作/同触发器的rule，以及qwen。回退到规则和主动扫描的收益不能算作模型判断的额外贡献。Agent不读取GT pose、collision、distance或地图；这些仅供离线选题和事后前缀审计。

三候选softmax只是条件词概率，不是校准的通行或导航成功率；正反问来自同一模型，不按独立事件相乘。VLM职责限于局部受阻方向选择，不承担全局目标规划。

既有完整4200参考：off SR/SPL 87.5714%/53.2996%，旧不扫描规则 88.2857%/53.6766%。旧规则与本轮主动扫描规则的动作预算不同，正式实验须重跑本轮匹配rule；不能把两种规则混作同一对照。

## 全部迭代

初始e9e5c0f/1531403三组各280任务，四事件全回退规则，Qwen与匹配规则280条原始行/动作哈希全等，没有额外模型作用。后续改用真实No/Unknown/Yes词读出、独立RGB和开发迭代；这个零收益版本及其完整复核也保留在evidence中。

原24条开发诊断后，预先登记加入全部额外37条，合61条；扩展诊断改用单环境减少别的episode结束引起的组批干扰。正式4200仍原6环境，不混比不同N和不同任务集的绝对成绩。下表含负结果和看似正向却无因果支持的版本；同一开发数据被反复用于调试，不能当独立测试。

N1与原N6并非逐轨迹相等：34条原生审计最大首动作差0.0015053、只有4条完整位姿哈希相等；具体底层数值来源未因果确定。61条虽然按旧N6失败诊断选择，新N1原生实际成功13条，所以本轮原生、规则、Qwen都重新配对跑，不把旧失败标签当本轮真实失败；小诊断也不替代原6环境正式协议。

|轮次/分组|N|规则成功|Qwen成功|净变化|前缀支持救回|误伤|规则SPL|Qwen SPL|
|---|---:|---:|---:|---:|---:|---:|---:|---:|
|round01/develop|24|6|6|+0|0|0|11.5487%|11.5487%|
|round02/develop|24|9|9|+0|0|0|16.7676%|16.1673%|
|round04/develop|24|9|9|+0|0|0|16.7676%|16.1673%|
|round05/develop|24|9|9|+0|0|1|16.8963%|15.0733%|
|round06/develop|24|9|10|+1|0|0|14.9793%|16.7851%|
|expanded01/develop|61|30|27|-3|1|4|19.3042%|16.3133%|
|expanded03/develop|61|30|31|+1|1|0|19.3042%|19.4396%|
|expanded03/safety|28|27|27|+0|0|0|49.1671%|49.1671%|
|expanded03_repeat/develop|61|30|31|+1|1|0|19.3042%|19.4396%|
|expanded03_repeat/safety|28|27|27|+0|0|0|49.1671%|49.1671%|
|expanded03_confirmation/confirm|24|9|9|+0|0|0|16.2611%|14.9766%|
|expanded03_confirmation/general|112|103|103|+0|0|0|55.6575%|55.6575%|
|expanded03_confirmation/safety|28|27|27|+0|0|0|49.1671%|49.1671%|

round03在真实空白输入对照中暴露位置偏好，技术门失败，未跑导航。round06表面多1成功但没有模型改向/前缀支持，被拒绝。expanded01真实1救回4误伤，净-3，未放行；之后仅在开发上调整双问一致性和保留可通行默认。另5条已知案例短回归是事后选择的集成调试，不能另算5个独立样本。

## 固定版收益与边界

首次完整61开发：规则30/61→Qwen31/61，SPL19.3042%→19.4396%，1救回/0误伤。35事件中只有2条轨迹真正偏离规则；59条无偏离轨迹的所有原始字段与动作/位姿哈希精确相等。Swormville3040在模型决定前前缀一致，90步改向后123步成功，规则500步失败；Ribera1167仍成功但SPL68.3569%→54.6825%，效率代价保留。安全28均27成功且0触发，因此只验证未触发回归。人工原因列留空，AI描述不是人工真值；1个救回也不构成统计显著性。

### 开发中真实改向：Swormville / 3040

|左侧实际模型输入|右侧实际模型输入|
|---|---|
|![left](evidence/logs/qwen_recovery_iteration_20261108/expanded_v2/expanded03/develop_qwen/native/recovery/inputs/event_0000012.candidate_left.png)|![right](evidence/logs/qwen_recovery_iteration_20261108/expanded_v2/expanded03/develop_qwen/native/recovery/inputs/event_0000012.candidate_right.png)|

图中没有GT标注，左右图分别独立送模型；人工原因未填写。两问原始概率/logits和实际回退规则见对应events.jsonl。

### 开发中真实改向：Ribera / 1167

|左侧实际模型输入|右侧实际模型输入|
|---|---|
|![left](evidence/logs/qwen_recovery_iteration_20261108/expanded_v2/expanded03/develop_qwen/native/recovery/inputs/event_0000030.candidate_left.png)|![right](evidence/logs/qwen_recovery_iteration_20261108/expanded_v2/expanded03/develop_qwen/native/recovery/inputs/event_0000030.candidate_right.png)|

图中没有GT标注，左右图分别独立送模型；人工原因未填写。两问原始概率/logits和实际回退规则见对应events.jsonl。

开发与同版重复都须净成功>=1且至少1前缀支持救回。确认24、普通112和安全28用冻结版本检查；预登记版本2允许确认中性且其他组成功数不降时进入正式4200进一步检验，不把中性确认称独立优势，也没有承诺SPL不降。原旧门/False/dispatch不覆写，必要时另留版本2审计；确认成功数下降则不放行。完整val复用了开发选择来自的benchmark，不宣称完全未接触测试。

冻结确认24：规则9/24、Qwen9/24；SPL16.2611%→14.9766%。成功数持平时明确称中性，SPL下降也保留；不以开发上的救回掩盖保留集尚无额外收益。

正式4200作业：**1532001.stdct-mgmt-02**，固定`f0e093c4d52c595c71f109d69cbf67ae7fbe3daa`，三个对照各4200/14场景/6环境/max500/seed100/hash0；已提交，当前包没有完整最终成绩，不预测整体提升。

## 复现与审计

行为配置：[inference_semantic_consensus_veto90.yaml](../../../../src/config/inference_semantic_consensus_veto90.yaml)；提示：[通行性](../../../../scripts/prompts/recovery_semantic_forward.txt)、[障碍物](../../../../scripts/prompts/recovery_semantic_obstacle.txt)。各batch的submission/tasks/source_manifest记录完整命令、资源、checkpoint SHA与不可变源文件，配对CSV保留空白人工标签。events.jsonl保留所有事件的模型输入SHA/原始正反logits/概率/回退原因，不仅保留成功案例；图像仅摘录开发中真实改向事件，其他大轨迹/模型/场景保留服务器。

资料生成器只读取证据，不提交作业。离线核验：在克隆根运行`python docs/experiments/inference-recovery/iteration_20261108/evidence/logs/qwen_recovery_iteration_20261108/publish_iteration.py --check-only --tree .`；按inputs.json逐项复算SHA，不加载模型。实际导航依赖服务器RUNBOOK所列环境与合法数据。代码单元回归74项、旧Qwen14项通过；实际FP32词ID2665/13394/9175、真实答案位置、批单和空白/换序检查均保留原证据。
