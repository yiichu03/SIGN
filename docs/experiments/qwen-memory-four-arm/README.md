# Qwen四组推理恢复：待审实现

从本机已有SIGN的资料提交1e7df23（旧已测行为f0e093c）建立独立分支`phase2/qwen-memory-four-arm`。共同运行实现为`057740b`；之后资料生成器/报告不改变控制行为。本轮只实现、测试和准备命令，**未提交四组正式4200，不训练PPO，不启停旧训练，不修改旧完整结果**。[预先固定方案](PLAN.md) / [根STATUS副本](workspace/STATUS.md) / [逐次操作记录](workspace/WORKLOG.md)。

固定coverage256125,952,000步原ckpt.245：SHA `988c9ecc5b0c704e9a4780f636739aec17cbd323d613f0fbdde4699296886c2c`。加载完整导航checkpoint作推理，没有把公开视觉encoder重新拼装成新导航模型。正式6env、seed100/hash0、500步，所有扫描和恢复均计步；无新增训练reward。原trainer/policy/metric/被动录数wrapper相对f0e093c无修改。

## 数据流与公平对照

共同流程：SIGN照常更新GRU并提出动作 → 原16步停滞检测 → 24步真实扫描（左90°/右90°/回正） → 共享仲裁 → 有限转向/前进 → cooldown64。最多两次，最多76个覆盖动作。SIGN的STOP在扫描/恢复/反馈前始终优先。执行动作走原trainer的prev_actions回填；真实mask和GRU不改。KEEP/RETURN表示本步交回SIGN提议，不是STOP、后退或状态回滚；可少用动作，不能为凑预算填充。

|配置|输入与额外决策|相对A的变化|
|---|---|---|
|A|4张真实独立图：GOAL、CURRENT、LEFT、RIGHT → left/right/keep|有效模型argmax直接执行，不受交替规则否决|
|B|A选向 → 转完6步才取before → 前进4步取after及真实4命令 → continue/return|只决定是否执行剩余4步，不用转向图变化或GT位移|
|C|A + 最多2条匹配候选的before/实际命令/after经验，最多8图|正常导航与恢复中稀疏写入、更新、淘汰，episode清空；模型作最终选向|
|D|A + 最多2张有外观对应的正常导航旧关键帧，最多6图|时间/新颖性保留；无可靠对应时请求与A完全相同，不推断全局地图|
|off|原生SIGN|不创建harness/worker/记忆|
|rule|旧matched-scan交替左右规则|同16检测、24扫描、6转+8前进和76上限，无模型|
|B_visual|A + 同朝向前后MAE≥0.01才继续|反馈用固定视觉阈值，仍保留A仲裁|
|C_rule|A + 同样检索的真实前进低变化经验可改为KEEP|规则记忆结果单列，不记成VLM决策|
|D_recent / D_random|A + 同容量/年龄的最近/私有固定随机历史|对应未经验证；可靠命中记0，保留去记忆影子读数|

记忆不使用GT成功、碰撞、距离、位置或独立目标图编码器。采用CPU ORB+RANSAC+光度核验；阈值、capacity24/stride8/最短历史16步等在GPU输出前写入PLAN。C保存真实控制与视觉变化，只有同朝向前进片段才给出visual_mae，不标“上次左转失败”。D仅正常SIGN动作后写入关键帧。灰度/重复纹理、多视角和光照差异可能漏检或混淆；这里的verified只是通过固定外观核验，不是地点真值。

## Qwen调用与审计

复用[SingleImageJudge](../../../src/qwen_single_image.py)的模型加载、processor与真实答案位置logits；实际文件链接见下方源码表。一个独立qwen35常驻进程，FP32/T1，每次最多2个独立请求、每请求≤8图、每图最多65536像素，保持完整视域。多图是同一消息中的独立image项，角色文字紧邻对应图，绝不拿拼图替代实际多图。候选left/right/keep token IDs=2282/1246/12718，continue/return=9252/671；真实assistant边界需验证。条件softmax只作选择，不是导航成功概率，不沿用旧coverage的q公式。

有效非并列argmax直接生效；全词表候选总概率<0.1、非法/非有限、并列或空白图安全KEEP/RETURN并记录。worker异常安全交回且记technical_errors，整轮不能标成正常成功；ID/SHA错配立即报错。旧三类ABC、生成JSON和benchmark接口保留。

输入PNG/角色/上下文/内容SHA、rendered chat、token IDs/padding/grids、实际logits/条件概率/候选总质量、耗时、选向/KEEP/反馈/规则分歧均保存。C/D命中时还独立读出同图同prompt去记忆A影子，不执行影子动作。分别统计检索外观命中、进入prompt、影子改变选择；“有效命中”最多表示经外观核验且改变模型选择，不能称已救回。

[配对报告入口](../../../scripts/report_memory_four_arm.py)记录SR/SPL、救回/误伤、实际首次动作分歧及决定前位姿前缀支持；无真实模型动作变化的成功差异单列，不归功Qwen。反馈RETURN和规则记忆干预来源单列。比较C/D对A时使用去记忆变化；仍需正式A对照，影子不是执行反事实。人审原因/备注保持空白。

## 复现与资源

从`/scratch/e1538633/liuyi/SIGN-qwen-memory-four-arm`执行。只改prompt也会改变manifest，必须新建输出、重新固定提交；不能边跑边改源。

```bash
# 本轮已经由Codex准备；此命令本身不会提交PBS。
/scratch/e1538633/liuyi/envs/sign-baseline/bin/python scripts/prepare_memory_four_arm.py \
  --output /scratch/e1538633/liuyi/logs/qwen_memory_four_arm_20261108/formal_review
```

审查通过后才执行以下四条；本轮未执行。各arm输出`formal_review/full_A`至`full_D`。

```bash
qsub -q autox -P CFP04-SF-109 -N memory-A -v MEMORY_TREE=/scratch/e1538633/liuyi/SIGN-qwen-memory-four-arm,MEMORY_BATCH=/scratch/e1538633/liuyi/logs/qwen_memory_four_arm_20261108/formal_review,MEMORY_ARM=A scripts/memory_four_arm.pbs
qsub -q autox -P CFP04-SF-109 -N memory-B -v MEMORY_TREE=/scratch/e1538633/liuyi/SIGN-qwen-memory-four-arm,MEMORY_BATCH=/scratch/e1538633/liuyi/logs/qwen_memory_four_arm_20261108/formal_review,MEMORY_ARM=B scripts/memory_four_arm.pbs
qsub -q autox -P CFP04-SF-109 -N memory-C -v MEMORY_TREE=/scratch/e1538633/liuyi/SIGN-qwen-memory-four-arm,MEMORY_BATCH=/scratch/e1538633/liuyi/logs/qwen_memory_four_arm_20261108/formal_review,MEMORY_ARM=C scripts/memory_four_arm.pbs
qsub -q autox -P CFP04-SF-109 -N memory-D -v MEMORY_TREE=/scratch/e1538633/liuyi/SIGN-qwen-memory-four-arm,MEMORY_BATCH=/scratch/e1538633/liuyi/logs/qwen_memory_four_arm_20261108/formal_review,MEMORY_ARM=D scripts/memory_four_arm.pbs
```

同PBS通过MEMORY_ARM=off/rule/B_visual/C_rule/D_recent/D_random准备强基线和消融，不复制控制器。manifest绑定最终HEAD；资料提交后才准备formal_review，不把旧烟测manifest用于新HEAD。

每组1×A40、36CPU、240GB，autox/CFP04-SF-109，walltime上限6h；四组最多预留24 GPUh。旧同底座完整4200原生/规则/旧Qwen实测分别23.1/54.5/59.3分钟。本次多图、反馈与外部记忆开销尚无4200实测，规划A/B约1–3h/组，C/D约1–4h/组，排队另算；这不是运行时保证。FP32模型常驻每组独立显存，不共享进程。正式提交前仍需核对项目余额与并发名额；短工程PBS被接受只证明当时可提交，不等于已知余额。

```bash
python scripts/report_memory_four_arm.py --batch /scratch/e1538633/liuyi/logs/qwen_memory_four_arm_20261108/formal_review --split full --reference rule --arms A B C D --output /scratch/e1538633/liuyi/logs/qwen_memory_four_arm_20261108/report_vs_rule
python scripts/report_memory_four_arm.py --batch /scratch/e1538633/liuyi/logs/qwen_memory_four_arm_20261108/formal_review --split full --reference A --arms B C D --output /scratch/e1538633/liuyi/logs/qwen_memory_four_arm_20261108/report_vs_A
```

## 源码索引

|文件|职责|
|---|---|
|[inference_recovery.py](../../../src/inference_recovery.py)|共享扫描/动作/STOP/真实episode生命周期|
|[recovery_agent.py](../../../src/recovery_agent.py)|四组请求、KEEP/同朝向反馈、影子与安全处理|
|[recovery_memory.py](../../../src/recovery_memory.py)|有限动作后果/关键帧记忆、ORB检索、更新与清空|
|[qwen_single_image.py](../../../src/qwen_single_image.py)|复用loader/processor，独立多图与二/三词真实logits|
|[qwen_client.py](../../../src/qwen_client.py) / [worker](../../../scripts/recovery_worker.py)|原常驻通信，增加agent任务，FP32 batch≤2|
|[共享配置](../../../src/config/inference_memory_four_arm.yaml) / [arm表](../../../scripts/memory_four_arm.py)|同一控制器的四组与消融设置|
|[仲裁prompt](../../../scripts/prompts/recovery_agent.txt) / [反馈prompt](../../../scripts/prompts/recovery_feedback.txt)|固定版本，修改即新实验|
|[新增测试](../../../tests/test_memory_four_arm.py)|边界、真实图片时刻、模型直决、空图/ID/记忆与零干预|
|[准备器](../../../scripts/prepare_memory_four_arm.py) / [正式PBS](../../../scripts/memory_four_arm.pbs)|不自动提交，绑定固定4200与源码/输入SHA|
|[GPU工程烟测](../../../scripts/smoke_memory_four_arm.py) / [烟测PBS](../../../scripts/memory_four_arm_smoke.pbs)|必要接口检查，不作新4200结果|
|[检索QA](../../../scripts/check_recovery_retrieval.py) / [证据来源](inputs.json)|独立被动GT核验与可复核SHA|

## 已执行的验证与限制

- CPU：**106项通过（74旧控制器＋18新增＋14旧单图评分）**；包括模型方向不受规则否决、KEEP、转后before/真实四前进/RETURN/CONTINUE、STOP优先、B_visual不发反馈模型请求、ID错误、空白、容量/更新/清空、私有随机不改变策略NumPy状态和零干预。11个配置可实际合并为6env/seed100/max500/geometry0。
- PBS工程 **1532788 Exit0/4:21**：固定6hash任务未触发恢复，native/off/disabled逐条全等；因此增加工程触发样本，未据SR修改参数。
- PBS工程 **1532823 Exit0/6:31**，不可变行为提交057740b：12条工程任务，各组5次真实仲裁；B4次反馈，1RETURN。独立复核实际4条前进命令、同朝向、动作SHA和76上限通过，native/off/零干预指标/位姿/动作逐条全等。A/C/D相对规则各1条episode出现动作差异，B有2条；本工程集均无救回/误伤，不用于推断全4200性能。
- FP32/NVIDIA A40，真实4/6/8图；4对8图batch具有307个padding，批单概率最大差`3.22e-6`、batch换序差0、forward/首生成token logits差0。实际left/right/keep和continue/return边界通过；左右交换right→left，空白KEEP，同图反馈RETURN，仅作偏置诊断。峰值显存8.64GiB。四图单次readout约0.21s、二图反馈约0.185s，启动/输入/批单核验等另计，不据此保证正式总耗时。
- C/D分别329/322次写入、3/5更新、138/128淘汰，但两者在线可靠检索命中/记忆进入prompt/改变决策**均0**，与A实际动作一致；还没有记忆收益证据。正常导航中视角对应召回、目标相关性和记忆效益都需正式对照；不能因程序正常或平均概率变化宣称成功。非零记忆请求路径由单元与真实多图技术fixture检查，不能冒充真实在线命中。
- 固定ORB阈值离线QA：旧151扫描/331历史图对，近似位姿标签TP35/FP0/FN7，precision1.0/recall0.8333。它只覆盖已保存扫描视角，非人工真值或正常关键帧代表数据；重复纹理/无纹理仍是风险。
- 最终比GPU快照多一项审计修复：summary写出technical_errors和agent_variant，worker异常close后落盘回归通过；决策和模型输入不变。GPU快照没有worker异常。不能把异常的safe KEEP当正常模型选择；正式evaluator若计数非零会报错，不产正常result。

[独立工程复核](evidence/review_smoke.json)、[固定检索QA](evidence/retrieval_qa.json)、[非零padding/真实logits核验](evidence/smoke_057740b/worker_probe/verification_arbitration.json)、[工程配对对规则](evidence/smoke_vs_rule/summary.json)、[工程配对对A](evidence/smoke_vs_A/summary.json)。[来源和SHA清单](inputs.json)包含实际输入图、概率/logits、模型输入审计与全部小工程记录，原场景/权重/完整相机数据仍在服务器；没有ZIP。
