# liuyi 当前状态

更新：2026-11-09（Asia/Singapore）。先读 [AGENTS.md](AGENTS.md)；操作与 debug 沿革见 [WORKLOG.md](WORKLOG.md)，命令与复现边界见 [RUNBOOK.md](RUNBOOK.md)。

完整训练曲线入口：[全历史TensorBoard命令](RUNBOOK.md#tensorboard-full-history)，本地16200→服务器6200；包含冻结基线、六方法原训练与续跑阶段，旧6009仍为仅续跑模式。

- TensorBoard续训显示排查（2026-11-03T23:30:50+08:00）：16200→6200正常，配置14阶段；首次先读取原训练，API后续已出现coverage256/continue_latest，其余运行续训文件也在更新；coverage32/B仍Q且无续训事件。脚本已改下次启动优先续训，路径/命名不变、兼容现有服务复用，当前会话未重启。证据logs/training_continuation_20261103/full_history_load_diagnosis_20261103.json。

<a id="local-checkpoints-20261109"></a>
## 本地运行权重：公开模型已有，新增Coverage256 125.952M

用户2026-11-09明确要求将checkpoint上传yiichu03供本地运行。GitHub远端ckpt已包含公开nav_model.pth（17,289,707bytes/SHA03fa71b5…）和safety_model.pth（16,399bytes/b84d291e…）。本轮新增原字节Coverage256125.952M/ckpt245为`SIGN-qwen-intervention-memory/ckpt/coverage256_125952000.pth`（7,396,455bytes/SHA988c9ecc…），不是公开完整权重；Gibson4200原策略SR87.571429/SPL53.299601%。不自动上传其他训练点，不使用Release/LFS或改写原权重。

ckpt/README.md含本地3episode、1env、seed100/hash0/max500、可选原生disk预览命令及HM3D替换说明；manifest/SHA256SUMS/validation明确身份。CPU实读103keys/step/有限性/42encoder与公开精确一致、原生配置合并通过；无本轮GPU导航运行。需要本地SIGN/Habitat和场景，Qwen/PBS无需；原生disk没有专用terminal RGB，最终STOP成片需auto-reset前录制。当前发布分支phase2/qwen-intervention-memory，最终SHA见推送回执。记录logs/checkpoint_publication_20261109；WORKLOG：CHECKPOINT-PUBLICATION-FOR-LOCAL-INFERENCE。

<a id="public-sign-demo-20261109"></a>
## 答辩视频：Public SIGN 成功 ImageNav，CPU导出

2026-11-09已从原1503625录像导出24秒/1280×720/30fps/H.264，2.5倍仿真时间，最终STOP停留4秒；保留0–50步全部51观测，完整720帧解码通过。**公开完整权重、Habitat-GS，不是Gibson或Coverage policy**：interior_0651_841463/episode0，success1、SPL0.61433059，公开nav SHA03fa71b5…；原运行源95eef9b。目标图、4张带步数关键帧及原RGB裁图、metadata/原视频/来源SHA/CPU复现脚本位于SIGN-qwen-intervention-memory/docs/experiments/report-figures-20261109/demo_public_sign，普通push至yiichu03同名分支。源logs/public_sign_demo_20261109/artifacts；本批只CPU，不导航回放、不PBS、不重新导训练曲线，旧作业不动。

初始最短路径4.642218m来自任务info，真实累计路径未保存，metadata设null而不由SPL倒推。STOP由原生Success定义和终态success1确认，原速度向量未保存。Gibson公开权重pilot仅稀疏RGB，若以后明确需要Gibson连续演示可回放Edgemere/200/C01（原35步成功），本轮未启动。追加素材盘点：MP3D未找到现成录像；HM3D现有俯视轨迹GIF和每25步稀疏RGB，未找到连续第一视角视频，不能直接拼成完整到达录像（盘点见logs/public_sign_demo_20261109/hm3d_mp3d_inventory.json）。WORKLOG：PUBLIC-SIGN-DEMO-CPU-EXPORT-20261109；已普通push并核对远端SHA `940a78feef440c5e934c07a89261d0c9d5ba21a6`（phase2/qwen-intervention-memory）；回执logs/public_sign_demo_20261109/push_receipt.json。

<a id="report-figures-20261109"></a>
## 报告/PPT配图第一版：CPU导出，GitHub资料发布

已推送并核对远端SHA：`d01459cce7125ac1e9e36602fe012b741d82fff3`，`yiichu03/SIGN` 的 `phase2/qwen-intervention-memory`。

2026-11-09已按用户要求从既有记录导出，不运行导航/Qwen，不提交PBS。目录SIGN-qwen-intervention-memory/docs/experiments/report-figures-20261109；本地源logs/report_figures_20261109/artifacts。47张PNG及PDF/SVG/CSV、原始事件和来源哈希，用户要求push yiichu03同名phase2/qwen-intervention-memory分支。

Coverage256训练SR/SPL/原导航reward曲线覆盖2,048–172,599,296步；原训练61,609点、续训22,777点，125.952M weights-continuation明确分段，50-update原生日志＋250点显示平滑，reward不含coverage bonus。失败案例Mosquito3564与Cantwell1688均同125.952M/recovery-off/500步，目标图＋各6步标记RGB＋轨迹覆盖图＋501行逐步面积数据；与原off目标/位姿/结局一致。Mosquito后250步移动37.99m仅新增0.12m²，Cantwell同期位移/新增都0，受阻与重复探索分开。

E2 Swormville3216第二次事件：394触发/418仲裁，Qwen LEFT50.9446%（RIGHT20.3526/KEEP28.7028），规则RIGHT；到418的位姿/动作和候选图一致，实际6转＋8前进匹配，E2于482成功、规则500失败。只显示真实输入和日志；E2无恢复后连续RGB，后续用记录轨迹/动作/观测变化，未重渲染或借其他方法画面。图内英文，README中文口径；用户之后提供PPT可再按版式调整。WORKLOG：REPORT-FIGURES-CPU-EXPORT-20261109。

<a id="qwen-intervention-memory-20261109"></a>
## 当前任务：P1–P4独立实现、短测后并行正式4200

最新GitHub发布：`yiichu03/SIGN` → `phase2/qwen-intervention-memory`，提交`20f9b503df0117a9b7bfc828cad205d088326c2c`（2026-11-09已push并核对远端SHA）；完整E1–E6结果及P1–P4当前状态均在该分支README入口。运行代码仍为8a94adf。

用户于11月9日批准上一轮建议的四组：P1扫描后固定LEFT、P2扫描后KEEP、P3当前RGB判断是否介入、P4同版加入最近3张历史RGB；先完成实验，汇报措辞稍后讨论。独立分支phase2/qwen-intervention-memory基于3f7d445，原125.952M权重/6env/seed100/hash0/max500。P3/P4在扫描前用同prompt与同16步实际动作，P4图片t-16/-11/-5/t；progress交回SIGN，blocked/unknown执行原matched规则；每次判断消耗两次机会预算之一，veto冷却64，不重复无上限调用。P4保存未执行的当前图shadow，统计是否改变介入。

**2026-11-09T08:23:49+08:00 最新状态**：138项单元/回归全部通过（132控制/worker/单图＋6checkpoint），最终7配置合并通过。代码/协议8a94adf固定，运行树SIGN-qwen-intervention-runtime-8a94adf，manifest批次logs/qwen_intervention_memory_20261109/runtime_8a94adf。GPU短测及正式P1–P4均尚未提交成功，无作业ID；01:58首次qsub失败后，一次性等待器PID1807538保持等待，当前PBS仍Connection refused/errno15010。账户UID解析与GitHub连接已恢复。等待器只在服务恢复后提交check，且技术门passed才提交原授权四组；不要重复启动等待器或手动重复qsub。当前余额未重新查询，01:41共享余额约9073.8321 GPUh是历史快照，不当实时余额。旧训练及旧验证保持原样。发布入口SIGN-qwen-intervention-memory/docs/experiments/qwen-intervention-memory/README.md；WORKLOG条目LATEST-PUBLICATION-SIX-COMPLETE-AND-P1234-PENDING。

<a id="qwen-six-ablation-20261108"></a>
## 当前任务：原A基线的E1–E6单因素推理消融

**2026-11-09T08:23:49+08:00 最终结果已复核**：六组均完成4200，原PBS汇总记录均F/Exit0；E6已于01:22:54结束。逐episode重算SR/SPL、任务/目标/起点和配对救回/误伤通过。正式完整动作前缀汇总已生成，以下旧时间快照不再代表当前进度。

|实验|SR|SPL|触发/完成仲裁|LEFT/RIGHT/KEEP|对A救回/误伤|对规则救回/误伤|
|---|---:|---:|---:|---:|---:|---:|
|E1|88.357143%|53.664525%|161/155|51/51/53|13/16|8/18|
|E2|88.619048%|53.781069%|152/149|147/2/0|8/0|4/3|
|E3|87.928571%|53.476922%|173/168|11/0/157|7/28|6/34|
|E4|88.333333%|53.679747%|160/155|136/0/19|7/11|8/19|
|E5|88.428571%|53.678132%|161/157|129/5/23|13/13|8/15|
|E6|88.428571%|53.644364%|177/170|140/2/28|13/13|14/21|

原A为88.428571/53.715613%，匹配扫描规则88.595238/53.775092%。E2本轮最高，相对A净+8成功、相对规则净+1；模型首次动作前缀支持分别7救回/0误伤、2/2。E6相对A13/13、SPL略低。六组worker技术错误0；E6有1次无效视觉证据安全KEEP，169模型有效选择与170完成仲裁分开统计。P1–P4将进一步检验固定方向、扫描本身及短时视觉历史对介入决策的作用，结果尚待GPU验证。

原证据：logs/qwen_six_ablation_20261108/runtime_e9396ac/formal_review/{summary.json,paired.csv,pbs_status.json}；本次只读复核logs/github_latest_publish_20261109/verification.json。发布副本在SIGN-qwen-intervention-memory/docs/experiments/qwen-six-ablation/evidence/formal_review/。完整4200为既有验证集，无重新采样/调参或人工因果标注。


**11月9日01:05新增完整结果读取**：E1/E2/E3均已输出4200结果；逐episode重算SR/SPL与任务/目标/起点匹配通过。E1为88.357143/53.664525%，E2为88.619048/53.781069%，E3为87.928571/53.476922%。相对A救回/误伤分别13/16、8/0、7/28；相对rule分别8/18、4/3、6/34。E2净多rule1条，147LEFT/2RIGHT；不能归为可靠VLM增益。E3大量KEEP未带来原先期待的总体提升，修正下方00:25潜力假设。完整动作前缀归因仍等依赖汇总，当前仅计结果配对。证据`logs/qwen_six_ablation_20261108/runtime_e9396ac/project_discussion_E123_readout_20261109.json`。

**答辩前讨论边界**：用户说明距答辩约12小时，重视流畅叙事、直观算法和新意，并指出可并行多组评估。建议集中一个短时视觉/动作记忆判断介入必要性的假设，以固定LEFT、扫描后KEEP及无历史同版模块作对照；这些仍是建议，未实现/提交。GPUx重新查得每用户4R上限、当前本人0R；旧训练1511148与E6均在普通GPU且不动。项目余额登录凭据已过期，本轮未核实新余额，不据旧余额声称已通过提交检查。已完成结果、失败诊断与训练结算时间对照应优先用于汇报；不将规则收益、选项偏置或未经验证的记忆作用改称前沿算法收益。

**剩余四组潜力判断（11月9日00:25快照，尚非成绩）**：E1/E2/E3/E6约3820/3893/4093/1945条，均未完成；优先关注E3减少错误恢复、其次E6更早触发，属于待验证机制假设。E3实际166次仲裁155次confidence_KEEP/11LEFT，收益如有仍要区分Qwen筛选与单纯少介入，KEEP仍消耗已发生24扫描步。E1/E2更偏诊断，分别有明显选项A/方向LEFT偏向；不以部分数据SR或表面方向均衡宣称收益，不更改已冻结配置或新提实验。快照见`runtime_e9396ac/other_arms_assessment_20261109T002518.json`（位于本批logs目录）。

**E4/E5完整配对结论（2026-11-09）**：均无超过原A的新总体收益。E4前进4步：SR88.333333/SPL53.679747%，相对A救回7/误伤11、净−4成功；E5扫描/恢复60°：88.428571/53.678132%，相对A救回13/误伤13、净0，二者SPL略低。相对matched-scan rule分别8/19与8/15；相对无恢复Coverage256仍净+32/+36成功，但属于恢复框架已有收益，不能归为本次改动或Qwen能力提高。原A为88.428571/53.715613%，rule88.595238/53.775092%。Qwen分别155/157次有效选择、0技术错误。完整动作/位姿审计与配对CSV保存在`logs/qwen_six_ablation_20261108/runtime_e9396ac/early_E4_E5_review_20261109/`；无人工因果标签、未调参/重跑/修改作业。

**2026-11-09 00:08实时进度**：E4/1533630与E5/1533631已各4200/F/Exit0，SR/SPL分别88.333333/53.679747%、88.428571/53.678132%，完整配对尚待全部完成。E1 3324/4200（约余20–35min）、E2 3466/4200（15–30min）、E3 3784/4200（10–20min）、E6 1383/4200（2–3h），均R；E1–3在GPUx，E6在普通GPU，汇总1533635为依赖H。估算采用最近200/500/1000条吞吐，不是保证；整批主要等E6。旧B训练1511148仍R、PBS预算约余7h10min，11月9日约07:18到限，非300M训练完成时间。证据`logs/qwen_six_ablation_20261108/runtime_e9396ac/eta_20261109T000822.json`；本轮无作业/源码操作。以下11月8日提交/迁移记录为历史快照。

用户授权从本机ffc177c/phase2/qwen-memory-four-arm新建phase2/qwen-arbitration-six-ablation独立工作树。六组共用原A控制器：E1平衡确定性选项映射，E2移除Qwen目标图，E3固定pmax0.5/gap0.1不确定KEEP，E4前进4步，E5扫描/恢复共同60度并同步prompt，E6检测窗口12。先原155审计和E1/E2/E3原图离线重评分，再单元/GPU短测与原A/off对照；技术通过后可提交正式4200并push新分支。保持原A/原结果/既有训练不动，不训练PPO、不按正SR反复调参；正式仍125.952M/6env/seed100/hash0/max500。原A155审计已完成：有效155/回退0，LEFT137/KEEP18/RIGHT0，155次均P(RIGHT)<P(LEFT)，相对匹配扫描规则2救回/9误伤，动作前缀支持1/8。实现及121项测试通过、CPU最终配置6env/seed100/max500/HFOV90核对通过。固定运行代码e9396ac（前置实现7e4d8d8）；GPU工程1533600已F/Exit0，1,240次真实重评分及9组×12任务短测全部通过：原A概率最大差6.8e-6、新旧A/native-off动作位姿精确相同，E5实测±60°、恢复60°，worker错误0。正式4200已提交E1–E6=1533627/1533628/1533629/1533630/1533631/1533632，均autox→batch_gpux、每组1A40/36CPU/240GB/6h，共同125.952M/6env/seed100/hash0/max500。CPU1533635依赖六组afterany，完成后自动生成formal_review/summary.json与paired.csv，失败/缺失组保持未验证，不自动重跑。 已推送yiichu03新分支，发布3f7d445；源码运行仍e9396ac。最新动态（2026-11-08T22:46:20+08:00）：E1–E4在GPUx已R；用户明确要求后，原Q的E5/1533631与E6/1533632已qmove auto→batch_gpu，目前分别Q/Q，ID/资源/源码/输出/依赖不变，不自动移回GPUx；汇总1533635为正常依赖H，原1511148训练仍R。当前正式结果未出，勿把12任务短测当总体SR。离线警讯：E1 raw token A占926/930，六映射语义一致0/155；平衡方向不等于看图判断。E2移除目标后154LEFT/1RIGHT，E3固定门槛145KEEP/10LEFT，不调参。目录logs/qwen_six_ablation_20261108/runtime_e9396ac；原排队1533598在使用资源前取消以修正离线安全KEEP审计，不是失败结果。

<a id="qwen-ab-full-completed-20261108"></a>
## 最新A/B：完整4200均完成，SR88.43%，未超过匹配扫描规则

2026-11-08T19:45+08:00独立复核：A **1532958**、B **1532959**均F/Exit0，用时1:47:28/1:05:34；实际ffc177c、同125.952M ckpt245/SHA988c9ecc…、4200/14场景/6env/seed100/hash0/max500。两组worker技术错误0、真实logits验证通过，任务/目标/起点、全部4200 ledger动作SHA与原始指标复算通过。

|同权重方法|成功数|SR|SPL|
|---|---:|---:|---:|
|Coverage256原策略|3678|87.571429%|53.299601%|
|匹配扫描规则|3721|88.595238%|53.775092%|
|此前Qwen＋规则回退|3723|88.642857%|53.777242%|
|A目标条件VLM仲裁|3714|88.428571%|53.715613%|
|B闭环VLM恢复|3714|88.428571%|53.703237%|

A/B较原策略整体SR+0.857143pp，但较规则均净−7成功（−0.166667pp）。配对A对规则2救回/9误伤，B4/11；有首动作模型差异及位姿前缀支持的子集分别1/8、2/9，其余不归因Qwen。B比A2救回/2误伤，前缀支持1/1，没有净成功收益，SPL略降0.012377pp。

两组各155次有效仲裁，均137 LEFT/18 KEEP/0 RIGHT，方向倾向须进一步核查，不能据此单独认定忽略目标或输入绑定错误。B135次反馈（106CONTINUE/29RETURN），实际改变执行但未带来额外净收益。比较单种子/历史规则对照，不声称统计显著；原策略差异含扫描/恢复框架，不全归Qwen。未提交新实验/改参数/启停训练。

完整复核报告（服务器：`/scratch/e1538633/liuyi/logs/qwen_memory_formal_20261108/completed_ab_review_20261108/REPORT.md`）、机器摘要（服务器：`/scratch/e1538633/liuyi/logs/qwen_memory_formal_20261108/completed_ab_review_20261108/summary.json`）、21000配对行（服务器：`/scratch/e1538633/liuyi/logs/qwen_memory_formal_20261108/completed_ab_review_20261108/paired.csv`）。原A/B结果仍在formal_retry/full_A、full_B；以下提交阶段快照仅作历史，当前状态以上面完成结果为准。C/D仍未通过此前40任务有效使用门，未自动重提。

<a id="qwen-memory-formal-20261108"></a>
## 当前任务：A/B正式4200继续，C/D未达到有效使用门

**2026-11-08T17:28+08:00快照：A1532958 R（503/4200）、B1532959 R（833/4200）**，CFP/autox→GPUx，每组1A40/36CPU240GB/6h。源固定SIGN-qwen-memory-formal-ffc177c detached / ffc177c69ed050d4b349c25632de92a855cb28bb、103源SHA、原125.952M ckpt245/SHA988c9ecc…、6env/seed100/hash0/max500；A/B配置/prompt未改。共同正式manifest与输出为`logs/qwen_memory_formal_20261108/formal_retry/source_manifest.json`和full_A/full_B。实际worker ready、真实读数验证通过、当前technical_errors0。原训练1511148仍R/普通GPU，不启停。

首轮1532929/1532930因首次worker600秒超时已标无效并只取消这两份新验证，旧formal/full_A/B原输出保留、INVALIDATED.json标记。重试仅外置导航前原worker加载/关闭预热（110/112秒），再启动原evaluator；实际lazy worker14.55/7.84秒ready，未改源码/模型/设置或超时。根因未完全定位，不声称已证实NFS/CUDA故障。

**C/D各40任务在线检查已完成，正式两组均未提交。** 固定20历史双触发＋20场景均衡hash单触发，12场景；每组实际34任务/48查询。C可靠检索5、真实模型记忆输入5、shadow有效选择改变0；D分别1/1/0。六次输入概率改变但都保持LEFT，C/D40实际动作/位姿/原指标逐条相同；不能据此称记忆有效。导航/Qwen错误0，未调参追正。

原因复核：每组96候选中75在允许的过去轨迹中无0.25m/15°近位姿代理；阶段排除和稀疏写入也损失视角。少量近位姿对被匹配几何条件拒绝（C4对/D2对），年龄排除未藏可通过匹配条目，容量淘汰仅C1次查询有额外匹配。GT仅事后代理，不作人工真值/Agent输入。详细见本轮报告（服务器：`/scratch/e1538633/liuyi/logs/qwen_memory_formal_20261108/REPORT.md`）。

GPU1532940实际22:27，采集成功但事后统计键大小写错误导致F/Exit1；原脚本/日志保留，CPU1533006已用同数据修正并Exit0（1:24），不重采样/调用模型。只读观测器12任务回归动作/位姿SHA全等，8控制SHA及新修正SHA可追溯。17:28共享CFP可用约9117.8321GPU小时（已含预留）、29873.432CPU小时，GPUx每用户max4，当前正式占2。回执/门决策/状态见`logs/qwen_memory_formal_20261108/submission_and_memory_gate_decision.json`及jobs_final_snapshot.json。

<a id="qwen-memory-four-arm-20261108"></a>
## 当前任务：实现Qwen四组推理恢复，正式验证等待审查

实现/工程验证完成，分支`phase2/qwen-memory-four-arm`独立于旧工作树，基于1e7df23。四组共享控制器：A实际目标/当前/左右多图直决；B同朝向4+4反馈；C动作后果记忆；D正常导航工作记忆；off/matched-rule/B_visual/C_rule/D_recent/D_random准备齐全。固定125.952M ckpt.245/6env/seed100/hash0/max500/16检测/24扫描/76上限；trainer/PPO/GRU/真实mask不改，无导航训练或几何bonus。**四组正式4200未提交，等待用户审查；旧结果与作业不动。**

106单元/回归（74+18+14）、11配置合并、两次独立不可变GPU工程烟测通过。1532788用4:21/6任务0触发；1532823用6:31/12工程任务，各组5触发，B4反馈（1RETURN），实际4前进命令与同朝向及动作SHA独立复核通过；native/off/零干预逐条动作/位姿/指标一致。4对8图非零padding307，FP32真实词logits批单最大差3.22e-6/换序0/生成0；左右交换和空图诊断有记录。共同实测行为057740b，最终增加技术异常计数入summary与对应CPU断言，不改变决策。

**限制：C/D在线可靠记忆命中均0，未证明记忆改变决策或SR收益。** 两组分别329/322次写入并正常更新/淘汰/episode清空，去记忆影子非零命中路径由单元/真实多图接口检查；需正式对照才判断价值。固定检索离线QA为旧扫描331对、35正确命中/0误命中/7漏检，近似位姿标签不是人工地点真值，不能替代正常关键帧召回验证。小工程集不报告泛化SR结论。实现、风险、待审PBS四命令、配对报告入口见新研究报告（服务器：`/scratch/e1538633/liuyi/SIGN-qwen-memory-four-arm/docs/experiments/qwen-memory-four-arm/README.md`），证据logs/qwen_memory_four_arm_20261108；复现[RUNBOOK](RUNBOOK.md#qwen-memory-four-arm-20261108)。已普通push yiichu03/SIGN / phase2/qwen-memory-four-arm / **ffc177c**，ls-remote一致；最终formal_review已绑定该HEAD，103运行源/24资产/4200任务核验通过，无submission.json，正式未提交。推送回执logs/qwen_memory_four_arm_20261108/push_verified.json。

<a id="discussion-and-branches-20261108"></a>
## 当前阶段：先讨论下一版Qwen框架，本轮仅更新文档并发布

2026-11-08T14:25:30+08:00：文档与完整证据已普通push到**yiichu03/SIGN / phase2/qwen-candidate-recovery / 1e7df23**，远端SHA复核一致。[现状与待讨论问题](https://github.com/yiichu03/SIGN/blob/1e7df231fb33dd0e659d913bc58284995f0f3dac/docs/experiments/inference-recovery/iteration_20261108/README.md)、[完整分支清单](https://github.com/yiichu03/SIGN/blob/1e7df231fb33dd0e659d913bc58284995f0f3dac/docs/experiments/inference-recovery/iteration_20261108/BRANCHES.md)、[8条成败变化案例](https://github.com/yiichu03/SIGN/blob/1e7df231fb33dd0e659d913bc58284995f0f3dac/docs/experiments/inference-recovery/iteration_20261108/CASES.md)。96项README/docs变化，644哈希/646索引文件/67本地链接通过；34工作树运行源码不变。工作树仅原data软链未跟踪。本轮0个新PBS作业，下一步先沟通再确定并行方案。推送后根回执单独追加，不循环发布自身。

2026-11-08T14:09:55+08:00 用户明确要求先沟通，再决定下一轮实验；本次只更新资料并push yiichu03，不改算法、不qsub、不启停现有作业。后续可在方案明确后并行多组，具体项目GPU-hour余额及队列约束提交前再核实，当前占用少不等于余额已确认。

分支盘点：SIGN本地19/origin19个同名分支，32工作树中16个detached快照；SIGN-SRU本地3/origin3，2个命名工作树。4个SIGN分支（GS、覆盖256、Qwen128 beta.1、Qwen消融）的本地HEAD与origin不同，但逐文件差异只在README/docs，运行目录保留代码版本。完整分支及目录盘点（服务器：`/scratch/e1538633/liuyi/SIGN-qwen-candidate-recovery/docs/experiments/inference-recovery/iteration_20261108/BRANCHES.md`）。本次发布目标仍phase2/qwen-candidate-recovery，运行行为版本f0e不变，作者main和其他训练分支不动。

讨论重点：现框架Qwen仅左右RGB通行判断，没有目标图/完整历史，不可选择不介入；恢复视觉反馈只记录，不影响后续。98/151回退规则、53采纳中仅23改向，现88.64%不证明独立VLM达到规则效果。当前优先Qwen承担恢复决策，同预算达到规则效果也有价值；目标信息、决策空间、规则回退消融和恢复反馈闭环均待沟通，尚未实现。报告与讨论（服务器：`/scratch/e1538633/liuyi/SIGN-qwen-candidate-recovery/docs/experiments/inference-recovery/iteration_20261108/README.md`）、完整验证案例/输入（服务器：`/scratch/e1538633/liuyi/SIGN-qwen-candidate-recovery/docs/experiments/inference-recovery/iteration_20261108/CASES.md`）。

<a id="qwen-iteration-campaign-20261108"></a>
## Qwen推理恢复：三组完整4200已完成，VLM额外收益仍不明确

用户于本轮明确研究优先级：重视Qwen承担恢复决策，在同观测/动作/步数预算下达到规则效果也有价值；现有88.64%是有规则回退的混合成绩，不能当独立VLM替代规则的证明。当前只做逻辑说明和训练读取，未改变配置/提交新对照；后续应将模型自主选择与规则回退分别检验。

2026-11-08T12:56:08+08:00 独立复核完成：正式GPU **1532001** 与CPU **1532002** 均F/Exit0，11:10前后结束，GPU用时2:17:44。固定`f0e093c`，同coverage256 **125,952,000步**完整导航权重；三组各4200/14场景/6env/max500/seed100/hash0。原生组4200条位姿SHA严格复现原参考，任务/目标/起点、所有指标与native TB逐条复算通过。独立完整复核（服务器：`/scratch/e1538633/liuyi/logs/qwen_recovery_iteration_20261108/expanded_v2/expanded03_full/completed_review_20261108.json`）。

|完整4200方法|成功条数|SR|SPL|碰撞/episode|平均步数|
|---|---:|---:|---:|---:|---:|
|覆盖256原策略|3678|87.5714%|53.2996%|36.679|113.559|
|旧无扫描规则（前批）|3708|88.2857%|53.6766%|32.969|110.464|
|本轮匹配扫描规则|3721|88.5952%|53.7751%|30.798|109.451|
|本轮Qwen2B恢复|3723|88.6429%|53.7772%|30.704|109.279|

Qwen相对本轮匹配规则，描述性SR仅**+0.047619pp（净2/4200）**，SPL仅**+0.002150pp**，不能用两位小数相同的SPL声称明显提升。原生→本轮规则SR+1.02381pp、SPL+0.475491pp，主要可见改善来自恢复框架整体；新扫描规则与旧无扫描规则动作预算不同，不混作同一对照。

**模型贡献核对：**151次完成评分，53次采纳模型但仅23条episode真正偏离规则；Qwen相对规则有5条失败→成功、3条成功→失败。真实模型改向且决定前动作/位姿一致的成败变化中，只有**2救回、3误伤**；另3条救回在该episode没有模型改向，不能直接归功于模型判断。并行batch/episode结束影响是待验证机制假设，不当已证实原因。原producer passes_fixed_gain_gate=True与full_completed回执保留，但其汇总门没有排除这3条无改向救回，不能据True认定VLM有稳定增益。

前缀支持救回：Scioto2230、Swormville3040；前缀支持误伤：Elmira2824、Scioto2314、Swormville3290。无本episode模型改向的成功变化：Mosquito3479、Scioto2174、Swormville3026。全部人工原因/备注留空，不把本自动审计当人工根因真值。该full复用了开发来源benchmark，单次种子也不能作普遍/统计显著性结论。

前序局部结果仍保留：开发61与同版重复规则30→Qwen31（1前缀救回/0误伤、逐条全等复现）；冻结确认24两组9成功，但Qwen SPL16.2611→14.9766%；普通112两组103且逐条相同，安全28两组27且0触发。旧负结果及确认旧False不改；正式提交依据为留出前登记协议v2与独立raw审计，见原放行记录（服务器：`/scratch/e1538633/liuyi/logs/qwen_recovery_iteration_20261108/expanded_v2/expanded03_full/release_authorization.json`）。

结果：完整对照（服务器：`/scratch/e1538633/liuyi/logs/qwen_recovery_iteration_20261108/expanded_v2/expanded03_full/full_comparison.json`）、4200条配对CSV（服务器：`/scratch/e1538633/liuyi/logs/qwen_recovery_iteration_20261108/expanded_v2/expanded03_full/full_paired.csv`）、复核与23条真实改向（服务器：`/scratch/e1538633/liuyi/logs/qwen_recovery_iteration_20261108/expanded_v2/expanded03_full/completed_review_20261108.json`）、[复现入口](RUNBOOK.md#qwen-recovery-frozen-full-20261108)。此前GitHub294f651为提交时证据快照；本轮已获用户明确授权，把完整结果、训练读取、问题及分支盘点一并更新发布，实际新SHA待push成功后记录。无新增训练、9B、启停原作业或ZIP。WORKLOG：QWEN-FULL4200-COMPLETE-ATTRIBUTION-REVIEW-20261108。

<a id="coverage256-rule-completed-20261108"></a>
## 覆盖256125.952M＋规则恢复：完整4200已完成，SR88.29%

2026-11-08T04:15:48+08:00独立复核：1531082 **F/Exit0**，01:49:49起/PBS2:16:52，same checkpoint/SHA/原协议6env/max500/seed100/hash0，Qwen关闭、几何bonus0。

| 完整4200方法 | SR | SPL | 碰撞/episode | 平均步数 |
|---|---:|---:|---:|---:|
| 覆盖256原策略125.952M | 87.5714% | 53.2996% | 36.6786 | 113.5593 |
| 同权重＋旧无扫描规则恢复 | **88.2857%** | **53.6766%** | **32.9686** | **110.4638** |

SR+0.7143pp/SPL+0.3770pp，33失败→成功、3成功→失败，净30。5条变化无直接干预（3救回/2误伤），单列而不全部因果归给恢复。4200任务/目标/起点、动作SHA与controller/步数/预算及raw SR/SPL独立通过；off4200轨迹严格复现缓存原参考。该控制为旧90度+0.8m无扫描规则，与新Qwen扫描库分开，不能混称。见完整对照（服务器：`/scratch/e1538633/liuyi/logs/sign_inference_coverage256_20261108/rule_full/comparison.json`）、独立审计（服务器：`/scratch/e1538633/liuyi/logs/sign_inference_coverage256_20261108/rule_full/completed_review_20261108.json`）。WORKLOG：COVERAGE256-RULE-FULL4200-COMPLETE-INDEPENDENT-AUDIT。

<a id="qwen-candidate-complete-20261108"></a>
## 最新结果：候选Qwen280完成，无额外行为收益；覆盖256全量规则仍运行

2026-11-08T03:05:39+08:00独立复核：**1531403 F/Exit0，03:03:23结束**，三组各280原始任务/目标/起点/动作SHA/指标与producer comparison一致。均使用coverage256125.952M；当前结果不混入74.240M冻结基线。

| 280确认方法 | SR | SPL | 真实模型作用 |
|---|---:|---:|---|
| 原策略off | 89.64% | 55.8011% | — |
| 同扫描动作规则 | 89.64% | 55.8174% | 4次规则恢复 |
| Qwen候选选择＋回退 | 89.64% | 55.8174% | **4次全回退，VLM选择0、偏离默认0** |

Qwen与匹配规则全部280条实际动作摘要及完整episode记录精确相同，当前确认集没有额外VLM行为或SR/SPL收益；不能把回退恢复当模型贡献。技术调用/FP32/真实logits/batch/元数据门均通过；开发14候选中13标签顺序改变后语义argmax变化，评分稳健性不足是实测诊断，非人工准确率。总入口耗时off/rule/qwen分别260.2/301.0/483.8s，包含加载等，不是纯模型推理。见三组原结果（服务器：`/scratch/e1538633/liuyi/logs/sign_qwen_candidate_recovery_20261108/attempt1/comparison.json`）、独立完整复核（服务器：`/scratch/e1538633/liuyi/logs/sign_qwen_candidate_recovery_20261108/attempt1/completed_review_20261108.json`）。

**1531082现已Exit0完成**：完整4200为87.57→88.29% SR、53.30→53.68% SPL，见上方完整结果入口；此前2194/4200仅为03:28历史进度，不再代表当前。

<a id="recovery-live-readout-20261108"></a>
## 最新进度：覆盖256规则恢复与候选Qwen三组确认

2026-11-08T02:58:43+08:00：两项仍按原源码/原预算运行。**1531082** full_off完整4200严格复现**SR87.57/SPL53.30%**；full_rule已1269/4200。相同已完成任务临时SR **86.13→86.68%**、SPL **50.08→50.29%**，失败→成功7、成功→失败0，仅前缀不能当最终4200。

**1531403**开发诊断与34原生等价技术门通过，原策略/匹配扫描规则各280完成，SR均**89.64%**、SPL55.8011/55.8174%；Qwen组226/280，result完成=False。开发7事件全部规则回退，14候选中13改变标签语义顺序后语义argmax变化，VLM额外贡献尚未体现，仍需最终线上选择/偏离默认统计。当前独立进度复核（服务器：`/scratch/e1538633/liuyi/logs/sign_qwen_candidate_recovery_20261108/attempt1/progress_review_20261108T025843.json`）、开发概率复核（服务器：`/scratch/e1538633/liuyi/logs/sign_qwen_candidate_recovery_20261108/attempt1/offline/review_20261108.json`）。两个实验任务范围不同，不混比临时4200前缀与280分数；无改源码/门槛或重提。WORKLOG：COVERAGE256-RULE-AND-CANDIDATE-QWEN-LIVE-READOUT。

<a id="qwen-candidate-recovery-20261108"></a>
## 当前实施：Qwen候选通行性与规则回退，1531403已提交GPUx

2026-11-08T02:38:56+08:00：用户已批准推进。独立SIGN-qwen-candidate-recovery / phase2/qwen-candidate-recovery从96f7783建立，先大纲70efa91，再运行源**e9e5c0f**，已普通push yiichu03并核对远端SHA。固定coverage256125.952M（SHA988c9ecc...）完整导航权重，6env/max500/seed100/hash0/几何bonus0；原策略、trainer/PPO、测量、传感器与SingleImageJudge字节保持。

**新1531403**：CFP04-SF-109/autox→GPUx，1A40/36CPU240GB/2h。当前**R**，已于02:39:04在GN-A40-037启动；GPU检查尚在运行；实际命令（服务器：`/scratch/e1538633/liuyi/logs/sign_qwen_candidate_recovery_20261108/attempt1/submission.json`）、当前回执（服务器：`/scratch/e1538633/liuyi/logs/sign_qwen_candidate_recovery_20261108/attempt1/current_status.json`）。先复用7真实开发扫描做标准/反序ABC、批/单/换序、同图/空白/镜像读数；34 native/off/零干预逐条相同后，再固定三组各280（原策略/同扫描动作规则/Qwen候选选择）。技术通过允许全回退的零效果结果，不强迫方向或自动新4200。

左右图同布局、相同prompt且无左右词入模型；ABC仅表示受阻/未知/开放，反序A/C再算同语义支持。两标签顺序均偏同方向且差>=0.05、OPEN严格最高才用VLM，否则交替规则；该门在新GPU评分前冻结，不以绝对token0.5取消全部恢复。独立记录VLM选择、规则回退、与默认不同，扫描与恢复计500；未加入反馈记忆，留后续独立消融。54项控制器/候选/身份+14旧Qwen测试及CPU最终配置通过；源/输入manifest固定73文件/52资产并保护旧三树。详见首轮方案（服务器：`/scratch/e1538633/liuyi/SIGN-qwen-candidate-recovery/docs/experiments/inference-recovery/CANDIDATE_PLAN.md`）、CPU检查（服务器：`/scratch/e1538633/liuyi/logs/sign_qwen_candidate_recovery_20261108/cpu_preflight.json`）。输出attempt1/offline、technical_gate、comparison、paired_tasks/per_scene；原1531082完整覆盖256off/rule仍按96f7783运行，不改/停旧训练，无9B或ZIP。WORKLOG：QWEN-CANDIDATE-RECOVERY-TESTED-SUBMITTED。

<a id="vlm-recovery-design-direction-20261108"></a>
## 当前设计讨论：让Qwen承担候选视野判断与闭环恢复

2026-11-08T02:18:37+08:00：用户希望继续以VLM框架争取导航收益、用于结题工程创新。本轮分析的首选：保留coverage256125.952M与原策略，规则触发/有限执行，Qwen对左右候选图用同一问题评估可见通行性，证据不足回退匹配规则；先验证图像条件判断与最小选择，再单独加同朝向视觉核验及episode失败记忆。对照匹配观察、动作和记忆预算，VLM额外价值由SR/SPL与配对净收益判断。当前7事件仅5episode/3scene，镜像仍偏同向，不能仅降置信门来认定有效；raw ABC非脱困校准概率。此为未实施方案，1531082完整验证仍按96f7783运行；未新qsub或修改运行源码。WORKLOG：VLM-RECOVERY-FRAMEWORK-DIRECTION-ANALYSIS。

<a id="inference-completed-check-20261108"></a>
## 最新恢复验证：旧冻结基线full完成；覆盖256Qwen短诊断结束；正确底座rule仍运行

最新核对2026-11-08T02:11:57+08:00：

| 作业/模型身份 | 实际状态 | 结果与范围 |
|---|---|---|
| **1530887：冻结视觉基线74.240M＋旧规则** | F/Exit0，01:49:47完成，wall1:43:47 | 完整4200：原SR84.97619/SPL54.39358%，规则**85.85714/54.83824%**；SR+0.88095pp，SPL+0.44465pp。仅补充，不是覆盖256叠加结果 |
| **1531083：覆盖256125.952M＋Qwen主动视图诊断** | F/Exit0，02:03:58完成，wall8:33 | 34开发任务/7真实扫描/4条件28评分，技术门通过；平衡prompt原始argmax **A7/B0/C0**，pA39.53–49.65%，全低0.5而回退C7。未进入280或Qwen在线恢复，不能报新SR收益 |
| **1531082：覆盖256125.952M off/旧规则完整对照** | R，01:49:49开始 | 34 native/off/零干预逐条精确门已通过，正在full_off（约1451/4200时抽查）；full_rule尚未启动，完整新底座结果未知 |

旧full的47失败→成功、10成功→失败，净37；其中13条变化未发生直接干预（3失败→成功、10成功→失败），不把全部配对变化当恢复因果效应。4200唯一任务/goal/start/实际动作SHA/步数与原始SR/SPL已独立复算；旧full结果（服务器：`/scratch/e1538633/liuyi/logs/sign_inference_rule_full_20261107/comparison.json`）、本次复核（服务器：`/scratch/e1538633/liuyi/logs/sign_inference_rule_full_20261107/completed_review_20261108.json`）。

Qwen新诊断原始概率与控制器回退必须分开：保守prompt原始C7，平衡prompt原始A7但置信不足；原生成式抽查也回答A。左右帧/无平移/±45度回中QA通过，ABC32/33/34、FP32、batch/solo最大差2.07e-5、生成logits概率差0。原diagnosis.json的still_all_C指门控后，不代表原始argmaxC；其置换/镜像agreement=1来自全回退C，不能据此证明空间判断不变。保留全部raw，不调整门槛或自动新实验；明确概率复核（服务器：`/scratch/e1538633/liuyi/logs/sign_inference_coverage256_20261108/qwen_active/completed_review_20261108.json`）、原诊断（服务器：`/scratch/e1538633/liuyi/logs/sign_inference_coverage256_20261108/qwen_active/diagnosis.json`）。当前仍应等125.952M完整rule结果，原源96f7783不动，几何128维持停止。WORKLOG：INFERENCE-COMPLETED-RULE-AND-QWEN-GATE-AUDIT-20261108。

<a id="inference-coverage256-base-correction-20261108"></a>
## 当前恢复框架底座：覆盖256125.952M；几何128已停止腾GPUx

2026-11-08T01:33:24+08:00：用户纠正恢复框架应叠加于高SR覆盖256权重。此前助手选择74.240M冻结视觉基线有误；旧pilot/规则1530887仅为明确74.240M的补充，不能当覆盖256叠加结果。**当前导航底座固定coverage256125,952,000步（原ckpt.245），SHA988c9ecc5b0c704e9a4780f636739aec17cbd323d613f0fbdde4699296886c2c；原完整4200 SR87.571429%、SPL53.299601%。** 模型路径与参考目录由tasks绑定，实际step/SHA/参考checkpoint身份错配即报错。

- **1531082：覆盖256同权重off＋规则恢复完整4200对照**，CFP/autox→GPUx，1A40/36CPU240GB/3h。先34同子集native/off/零次精确门，再重新运行完整off（严格对原覆盖256参考）和rule；旧无扫描规则每事件10步/最多20、均计500。输出rule_full（服务器：`/scratch/e1538633/liuyi/logs/sign_inference_coverage256_20261108/rule_full`），最终comparison.json及paired_tasks.csv。
- **1531083：同125.952M的Qwen2B主动视图诊断/条件280四控制**，CFP/autox→GPUx，1A40/2h；观察/真正恢复分开，保留C，不自动Qwen4200或导航训练。输出qwen_active（服务器：`/scratch/e1538633/liuyi/logs/sign_inference_coverage256_20261108/qwen_active`）。两新作业目前Q/node_pool资源不足，提交不等于运行或通过；最新回执（服务器：`/scratch/e1538633/liuyi/logs/sign_inference_coverage256_20261108/current_status.json`）。
- **原错底座Qwen1530921已在Q状态取消**，从未采图或评分；原工作树1ec9a17/旧证据保留。旧规则1530887已用约1.5小时、仍R，保留完成以作74.240M补充，结果不能与新覆盖256混称。
- **几何128 C1511410已按用户新授权于01:24:25停止（F/143）**，释放1A40 GPUx并停止其后续消耗。最新保存ckpt.115/latest＝**81,920,000步**，含learner_state；末控制台82,186,240，未落盘部分不声称已保存。全部权重/TB/ledger/日志保留，不自动续跑或重新计预算；停止证据（服务器：`/scratch/e1538633/liuyi/logs/sign_inference_coverage256_20261108/geometry128_stop.json`）。

独立SIGN-inference-coverage256 / phase2/inference-coverage256-recovery @**96f7783**已普通push yiichu03并核对远端SHA；两旧源码树保持原提交不动。37项控制器/模型身份+14旧Qwen测试、真实权重/参考/config CPU检查通过，src/trainer/policy/控制器/worker字节未变。首次CPU预检错误导入src.default失败，改用已检查的src.utils.get_config后通过，证据日志保留。见明确协议（服务器：`/scratch/e1538633/liuyi/SIGN-inference-coverage256/docs/experiments/inference-recovery/COVERAGE256_PROTOCOL.md`）、CPU检查（服务器：`/scratch/e1538633/liuyi/logs/sign_inference_coverage256_20261108/cpu_preflight.json`）。其他训练未因本批启停/移动，无9B或ZIP；GPU结果尚未知。WORKLOG：COVERAGE256-RECOVERY-CORRECTION-TESTED-SUBMITTED。

<a id="inference-rule-full-active-view-20261108"></a>
## 推理恢复：规则完整4200运行；Qwen主动观察修复版已排队

最新查询（2026-11-08T01:13:22+08:00）：**1530887仍R，已完成2652/4200（63.1%），完整验证尚无最终结果**；同已完成任务的临时配对见进度快照（服务器：`/scratch/e1538633/liuyi/logs/sign_inference_rule_full_20261107/progress_20261108T011322.json`），场景前缀不得当最终4200成绩。**1530921仍Q/用户GPUx运行数上限**，尚无Qwen GPU输入或评分；未重复提交或改动作业。WORKLOG：INFERENCE-RULE-FULL4200-PROGRESS-QWEN-QUEUED。

2026-11-08T00:14:35+08:00：按用户新授权先单独提交旧规则full4200 **1530887**，已R于GPUx/GN-A40-094；固定SIGN-inference-harness @5e3b0d0，74.240M基线完整权重、6env/max500/seed100/hash0，Qwen关闭、几何bonus0，1A40/2h。输出规则完整验证（服务器：`/scratch/e1538633/liuyi/logs/sign_inference_rule_full_20261107`），结束后同PBS自动核对4200唯一任务/目标/起点/实际动作与配对SR/SPL，结果comparison.json。原pilot未触发全量的记录保留，此为新授权独立作业。

Qwen实际旧输入缺左右视图，旧选项要求盲转前进且提示词偏保守；这是待实验检验的原因假设，不是token/阈值错误。独立SIGN-inference-active-view / phase2/inference-recovery-active-view @**1ec9a17**已push yiichu03并核对SHA，旧规则/训练目录不动。先用12个原地转向步获取左45/右45/前RGB，再由2B选已见方向的45度+0.4m短尝试或C。最多两次34步均计500；STOP/GRU/masks/真实action反馈保持，扫描与模型选择动作分开。

新 **1530921**（CFP/autox→GPUx，1A40/2h）目前Q/本用户GPUx运行数上限。31项控制器+14旧Qwen单元测试通过；GPU计划先34开发任务原生/off/零次与真实视图/角度/ABC批单核验。两份prompt预先固定，仅开发比较；若平衡版仍全C则保留解释结束，否则在预先排除旧pilot等任务的新280上跑off/scan-only/scan-rule/scan-qwen。比较扫描及规则控制后才谈Qwen额外价值；不自动发起新Qwen4200，不训练导航。详见大纲（服务器：`/scratch/e1538633/liuyi/SIGN-inference-active-view/docs/experiments/inference-recovery/ACTIVE_VIEW_PLAN.md`）、CPU检查（服务器：`/scratch/e1538633/liuyi/logs/sign_inference_active_view_20261108/cpu_preflight.json`）、提交命令（服务器：`/scratch/e1538633/liuyi/logs/sign_inference_active_view_20261108/attempt1/submission.json`）、当前回执（服务器：`/scratch/e1538633/liuyi/logs/sign_inference_active_view_20261108/attempt1/current_status.json`）。GPU效果尚未知。WORKLOG：QWEN-ACTIVE-VIEW-IMPLEMENTED-TESTED-AND-SUBMITTED。

<a id="inference-harness-discussion-20261107"></a>
## 结题第三方向：推理pilot已完成，Qwen零实际干预未续全量

最新检查（2026-11-07T23:46:21+08:00）：GPU1530286于11月7日23:04:54–23:26:46正常完成（Exit0，walltime21分49秒），CPU1530290也Exit0。同一74.240M权重/280任务：off SR88.57/SPL54.25%，rule SR90.00/SPL54.87%，qwen SR88.57/SPL54.25%。技术门全部通过，但Qwen11事件原始最大概率全部是C（继续SIGN），C约71.49–84.24%，实际覆盖动作0；不是A/B被置信度阈值挡下。自动调度因此未提交完整4200，源代码和原训练不变。

| 280任务对照 | SR | SPL | 触发事件 | 实际干预动作步 |
|---|---:|---:|---:|---:|
| 原SIGN off | 88.57% | 54.25% | — | 0 |
| 规则恢复 rule | 90.00% | 54.87% | 7 | 70 |
| Qwen恢复 qwen | 88.57% | 54.25% | 11 | 0 |

规则的配对结果有5条失败→成功、1条成功→失败，净+4/280（SR+1.43pp），SPL+0.62pp；其中4条成功变化有干预，另外1条失败→成功和1条成功→失败没有直接干预，不能把全部变化当恢复因果收益。并行组批/episode上下文影响尚未因果核实，280任务只能探索性筛查。Qwen与off全部280逐条结果精确一致；28条同子集原生/off/零次完整字段也精确一致。真实FP32 token A/B/C=32/33/34、padding[192,128,0]、batch/solo最大概率误差2.56e-6，排列/生成logits差0，调用链通过。

证据：pilot汇总（服务器：`/scratch/e1538633/liuyi/logs/sign_inference_harness_20261107/retry2/pilot/pilot_comparison.json`）、配对/逐场景报告（服务器：`/scratch/e1538633/liuyi/logs/sign_inference_harness_20261107/retry2/pilot/pilot_review/README.md`）、自动停止后续原因（服务器：`/scratch/e1538633/liuyi/logs/sign_inference_harness_20261107/retry2/pilot_dispatch.json`）、本次原始概率与归因复核（服务器：`/scratch/e1538633/liuyi/logs/sign_inference_harness_20261107/retry2/completed_pilot_review.json`）。下段为实施与排队历史，当前完成状态以本段为准。

用户希望在有限时间增加无需训练的研究点。当前建议固定74.240M冻结基线，先测试RGB/实际动作历史触发的持续停滞恢复，再对照同触发器的Qwen2B有限动作选择；维持原目标、500步和传感器，不使用GT地图/测地距离/真实位姿作为Agent输入。纯SIGN、规则恢复、同预算Qwen恢复三组；小开发集冻结阈值后用固定场景均衡任务筛查，正向再4200，并报告救回/误伤、SR/SPL、碰撞、调用和耗时。旧目的性案例仅debug，不作为总体收益证据；候选症状不当因果标签。用户随后已授权新分支先大纲后实施与验证。现已建立SIGN-inference-harness / phase2/inference-recovery-harness，从453179c开始；大纲见PLAN（服务器：`/scratch/e1538633/liuyi/SIGN-inference-harness/docs/experiments/inference-recovery/PLAN.md`）。GPU试跑1530277因forkserver注册失败、1530280因子集与旧全量输出严格比较失败，均已F；原证据保留。新源码5e3b0d0增加同子集原生参考，1530286已提交retry2，2h/1A40，因GPUx node_pool排队于18:03仅将新Q任务qmove至auto，当前状态见retry2/current_status.json。方案/源码5e3b0d0已push yiichu03/SIGN同名分支并核对远端SHA。自动CPU1530290在afterany依赖等待，不占GPU；检查pilot Exit0、数据审核、原生/off/零次精确对齐、真实Qwen读出、两组实际干预及SR/SPL回退不超过2pp，才可提交单A40/6h完整4200三组；否则只写原因，不自动重试或训练。自动脚本SHA固定于orchestration_manifest.json，新增5项拒绝/报告调度测试通过。尚无通过的完整pilot或正式full作业，实际状态见最新回执（服务器：`/scratch/e1538633/liuyi/logs/sign_inference_harness_20261107/latest_state.json`）；不启动导航训练。

依据：旧覆盖256失败中76条强受阻尾段候选、350条低新增闭环候选，但成功中也有308条闭环，类别重叠。只改停止时机的固定轨迹GT上界约+1.36pp，故优先探索局部恢复。可借鉴[NavHarness](https://arxiv.org/abs/2609.34276)的运行时记忆/核验闭环；完整深度建图与frontier规划如[VLFM](https://arxiv.org/abs/2312.03275)所需输入和接入范围不同，不是当前小实验已实现的功能。

Qwen资源核查：A1511143、β.1 1511145、B1511148均R，分别GN-A40-045[0]/GN-A40-030[0]/GN-A40-020[0]，各1A40；三份独立常驻FP32 worker读同一models/Qwen3.5-2B，各自单份显存，不是共享服务或8环境8模型。最近单条worker峰值约9.36GiB，仅代表worker分配峰值，不是整作业峰值或并发压力测量；训练策略与worker在各自作业内共用GPU，有内部开销，共享文件系统启动I/O仍可能竞争。WORKLOG：REPORT-DIRECTION-AND-QWEN-RESOURCE-REVIEW-20261107。

<a id="github-publication-20261107"></a>
## 最新GitHub资料同步：2026-11-07

- 已普通push到 **yiichu03/SIGN / phase2/qwen-beta003-geometry128**，提交 **f00c15c**，远端SHA复核一致。入口：[11月7日训练、完整验证、失败诊断及代码导航](https://github.com/yiichu03/SIGN/blob/phase2/qwen-beta003-geometry128/docs/experiments/qwen128-reward/ablations/progress_20261107/README.md)。四个continue代码分支也逐一核对远端一致。
- 本次584项文件更新：根四文档生成快照、续跑/同步数统计、七份已完成4200val可复算记录、新评估选点/PBS脚本、失败诊断图文与人审表。728项manifest、75压缩源、342相对链接和旧报告56窗口指标通过；已发布WORKLOG前缀保留。原证据CSV换行/YAML空白有42个SHA一致的精确格式例外，新增文档/代码严格空白检查通过。
- 资料的作业状态固定在 **2026-11-07T13:58:35+08:00**，包含A36.352M完整val SR82.38/SPL52.97%；当时其余新验证仍R/Q，不伪称全完成。模型/场景/环境/完整相机视频未上传，不生成ZIP。11运行树HEAD和源文件守卫通过，作业未启停/移动。
- 发布树SIGN-qwen-ablation-publication现detached @f00c15c且干净；各运行树不pull资料提交。SSH agent无响应已通过仅本命令使用现有本机密钥恢复，未改全局配置。实际回执push_result.json（服务器：`/scratch/e1538633/liuyi/logs/github_publication_20261107/push_result.json`），推送后根日志另追加，不为包含回执循环发布。WORKLOG：GITHUB-PUBLICATION-20261107-PUSHED。

<a id="training-readout-20261108"></a>
## 11月8日训练：最新13:56截面，只有B仍运行

各自当前/最终日志步数，近1M环境步内原生50-update训练滑窗日志均值；日志末步不是checkpoint，训练均值不是val。此前13:02的读取留在原snapshot_130216，不改写。

|方法|日志百万步|近1M SR|近1M SPL|状态|
|---|---:|---:|---:|---|
|冻结视觉基线|74.654|87.87%|54.82%|按用户要求停止|
|覆盖256|172.599|87.80%|50.60%|原PBS时限结束|
|覆盖32|175.868|88.76%|51.37%|原PBS时限结束|
|Qwen128 beta0.1|32.829|87.25%|49.21%|原PBS时限结束|
|A Qwen128 beta0.03|41.552|85.03%|48.14%|原PBS时限结束|
|B Qwen256 beta0.03|38.439|87.94%|49.21%|运行|
|C几何128|82.196|88.64%|51.41%|按用户要求暂停|

B1511148原预算约余17.36h，最新末步38,438,912；近1M SR对前1M-0.42pp，较13:02读取有所恢复，短窗仍波动。其他组保持原末步；覆盖32/β.1/A在今日03:12/07:11/09:10耗尽原预算，覆盖256在11月5日到限，C按用户要求于01:24暂停，未新计预算或重启。

B同预算近3M：

|方法|SR|SPL|
|---|---:|---:|
|冻结基线|86.2498%|51.2080%|
|覆盖256|84.8372%|47.5284%|
|覆盖32|85.1557%|46.8539%|
|Qwen256 beta.03|87.9256%|50.5966%|

B两项均高于同期两覆盖；对基线SR更高、SPL仍低。共同32.829440M及各自预算1/2/3M全部保留，训练/续跑reset历史有混杂，不称严格因果或val优势。近期SR/SPL与匹配参考CSV保持原数值导出，独立重算1M/3M、SR/SPL步数组相同；完整TB不复制。最新简表（服务器：`/scratch/e1538633/liuyi/logs/training_readout_20261108/snapshot_135628/summary.json`）、全部窗口/来源（服务器：`/scratch/e1538633/liuyi/logs/training_readout_20261108/snapshot_135628/readout.json`）、验证与导出来源（服务器：`/scratch/e1538633/liuyi/logs/training_readout_20261108/snapshot_135628/validation.json`）。WORKLOG：DOCS-DISCUSSION-BRANCH-PUBLICATION-PREPARED-20261108。

<a id="gibson-reference"></a>
## Gibson基线与公开权重结果：快速索引

这里的“对照基线”指冻结视觉编码器训练 **1496716**（与两个coverage实验比较的那一组）。

**“自己训练SIGN的最好完整验证”口径：** 保留原SIGN奖励、只加载冻结公开visual_encoder而其余模块重新训练的基线，74.240M点为**SR84.98%／SPL54.39%**。若包括修改奖励后的自训练策略且不加推理恢复，已评估最高SR来自Coverage256125.952M：**87.57%／53.30%**；最高SPL来自Coverage256146.944M：**86.36%／56.24%**。SR和SPL最高不是同一checkpoint，不能合并成87.57/56.24；均为Gibson完整4200，不是训练滑窗，也不是官方完整权重直接加载或Agent辅助成绩。


| 常查事项 | 已核实记录 | 证据入口 |
|---|---|---|
| 冻结基线停止时的训练进度 | **74,653,696环境步，约7465万步**；TensorBoard最终事件为2026-10-28 20:28:29，作业20:28:36停止 | 最终事件快照（服务器：`/scratch/e1538633/liuyi/logs/gibson_train_threeway_20261028/snapshot_132900/comparison.json`） |
| 冻结基线停止时的训练SR／SPL | **最后一个原生50-update滑窗点：SR87.81%、SPL55.13%**；最后100万步的滑窗均值：SR87.87%、SPL54.82%。均为训练日志，未对完整训练集另做离线评估 | 原始末点与区间统计（服务器：`/scratch/e1538633/liuyi/logs/training_readout_20261031/snapshot_005043/readout.json`） |
| 冻结基线最后保存、可用于评估的权重 | **74,240,000步，约7424万步**；后续按checkpoint步数选择同预算对照 | 权重保存记录（服务器：`/scratch/e1538633/liuyi/logs/qwen_token_probabilities_20261028/baseline_stop_1496716/preservation.json`） |
| 冻结基线最终权重完整val（已完成） | **74,240,000步**；1515117 Exit0，4200条：SR **84.98%**、SPL **54.39%**；后处理已CPU复核 | [最终基线评估记录](#baseline-final-eval-20261103) · 完整对照（服务器：`/scratch/e1538633/liuyi/logs/gibson_baseline_final_eval_20261103/comparison.json`） |
| 公开完整SIGN checkpoint的Gibson验证成绩 | **SR 86.00%、SPL 53.01%、View Match 85.08%**；完整val **4200条／14场景**，作业1494521，Exit0 | 完整原始结果（服务器：`/scratch/e1538633/liuyi/logs/gibson_reproduction_20261026/pretrained_full_result.json`） |
| 最新原训练同步数比较 | 基线/覆盖截至48,377,856步，Qwen/覆盖共同截至8,536,064步；分别比较近1M/5M SR-SPL，未混入续跑 | [同步数训练表](#matched-training-20261103) · 曲线（服务器：`/scratch/e1538633/liuyi/logs/matched_training_20261103/snapshot_015509/matched_training.png`） |
| 覆盖32三个选点完整val（全部完成） | **76.288M SR83.98/SPL53.48%；125.952M 86.83/47.80%；151.040M 87.12/54.76%**；三GPU与CPU汇总均Exit0，各4200条已独立复核 | [结果/选择/协议](#coverage32-selected-eval-20261107) · 独立复核（服务器：`/scratch/e1538633/liuyi/logs/gibson_coverage32_selected_eval_20261107/results_review_20261107.json`） |
| 三Qwen按训练曲线选点的完整val（全部完成） | **β.1 20.480M SR80.36/SPL54.60%；A36.352M 82.38/52.97%；B29.696M 84.50/50.35%**；三GPU与CPU汇总均Exit0，各4200条已独立复核 | [结果/选择/协议](#qwen-selected-eval-20261107) · 独立复核（服务器：`/scratch/e1538633/liuyi/logs/qwen_three_checkpoint_eval_20261107/results_review_20261107.json`） |
| 覆盖256两个曲线候选完整val（已完成） | **143.360M SR86.52/SPL52.15%；150.528M SR86.33/SPL51.77%**，各4200条；1523189/1523190/汇总1523191均Exit0，均未超旧125.952M | [结果与完整对照](#coverage256-candidates-eval-20261105) · 独立复核（服务器：`/scratch/e1538633/liuyi/logs/gibson_coverage256_candidates_eval_20261105/results_review_20261107.json`） |
| 覆盖256125.952M保存时训练指标 | **原生50-update窗SR82.71/SPL45.82%；近1M均值86.31/49.18%；近3M88.23/50.71%**；对应完整val87.57/53.30%，训练窗口不混同验证 | 保存点训练证据（服务器：`/scratch/e1538633/liuyi/logs/training_readout_20261107/coverage256_125952000_training_reference.json`） |
| 覆盖256训练峰值附近完整val（已完成） | **146,944,000步／ckpt.40**，1520910 Exit0，4200条：SR **86.36%**、SPL **56.24%**；相对125.952M SR−1.21pp／SPL+2.94pp。146.760M无精确保存 | [结果与协议](#coverage256-peak-eval-20261105) · 完整对照（服务器：`/scratch/e1538633/liuyi/logs/gibson_coverage256_peak_eval_20261105/comparison.json`） |
| 最新训练（11月8日13:56） | **仅B仍R**，B38.439M近1M87.94/49.21%；同预算近3M两项高于两覆盖、SPL仍低基线；其余到限/用户暂停 | [最新训练](#training-readout-20261108) · 完整快照（服务器：`/scratch/e1538633/liuyi/logs/training_readout_20261108/snapshot_135628/readout.json`） |
| 覆盖256训练停止与最后可用权重 | **1511146于11月5日21:45:20到时限结束（Exit−29）**；TB末步172,599,296，最后保存ckpt.90为172,544,000，参数有限，未自动续跑 | [训练停止证据](#training-readout-20261107) · checkpoint实读（服务器：`/scratch/e1538633/liuyi/logs/training_readout_20261107/coverage256_last_checkpoint.json`） |
| 续跑历史快照（11月3日22:06–22:08） | 4R/2Q；256已140.716M，Qwenβ.1 12.911M、A13.922M、C32.455M；原Gibson上限3亿环境步 | [训练进展及共同步数](#training-readout-20261103-evening) · 完整快照（服务器：`/scratch/e1538633/liuyi/logs/training_readout_20261103/snapshot_220651/readout.json`） |
| 11月3日两覆盖权重完整val（已完成） | 256为125,952,000步、32为48,128,000步，训练预算不同；SR87.57/83.05%、SPL53.30/51.90%，各4200条、Exit0 | [最新评估与训练恢复](#coverage-latest-eval-20261103) · 完整结果（服务器：`/scratch/e1538633/liuyi/logs/gibson_coverage_latest_eval_20261103/summary.json`） |
| 10月31日六训练被中断时的训练指标 | 日志末步/末点SR-SPL/近100万步均值已复核，原六训练09:01–09:03记录；与续跑checkpoint步数分别记录 | [中断时训练表](#training-stop-20261031) · 原始统计（服务器：`/scratch/e1538633/liuyi/logs/training_stop_20261031/readout_20261103T014602/report.json`） |
| 最新三方法同预算验证（已完成） | **18,944,000步／ckpt.36**；每组4200条，PBS **1506785 Exit0**。基线/256覆盖/32覆盖：SR **78.31/79.10/82.02%**，SPL **51.64/51.98/51.75%** | 完整结果（服务器：`/scratch/e1538633/liuyi/logs/gibson_threeway_coverage_eval_20261029/full_comparison.json`） · 作业完成记录（服务器：`/scratch/e1538633/liuyi/logs/gibson_threeway_coverage_eval_20261029/runtime.json`） |

控制台最后一次打印是74,649,600步，比最终TensorBoard记录少4096步；这是不同日志更新频率的末端差异。不要将最终训练记录或控制台末步当成最后checkpoint步数。公开成绩对应加载完整公开导航模型；冻结基线则只加载并冻结其visual_encoder，其余模块从原初始化训练。

公开模型评估原记录中PYTHONHASHSEED未显式固定，后来的共同步数对照使用hash0；复现协议细节与权重路径见 [RUNBOOK证据索引](RUNBOOK.md#gibson-checkpoints)，本次核验汇总见 baseline_reference_index_20261029.json（服务器：`/scratch/e1538633/liuyi/logs/gibson_reproduction_20261026/baseline_reference_index_20261029.json`）。

<a id="coverage32-selected-eval-20261107"></a>
## 覆盖32三个checkpoint完整验证：全部完成

11月7日15:34独立复核：三GPU **1528994/1528995/1528996** 与CPU汇总 **1528997** 均F/Exit0，最后GPU于14:47:43结束、汇总14:49:19结束。每份4200条/14场景；结果SHA、成功率/SPL/碰撞/步数/面积逐条复算，任务/目标图/起点与基线和旧覆盖参考完全匹配，11运行树守卫通过。以下均为完整val，不是训练滑窗。

| 精确累计环境步 | 覆盖32文件 | 选择用途 | 验证SR | 验证SPL | 总新增面积/总步数（m²/步） | 碰撞/episode |
|---|---|---|---:|---:|---:|---:|
| **76,288,000** | ckpt.54.pth | 较早训练SR/SPL高位 | 83.98% | 53.48% | 0.09337 | 45.28 |
| **125,952,000** | ckpt.151.pth | 与已有覆盖256同累计步数参考 | 86.83% | 47.80% | 0.09986 | 43.47 |
| **151,040,000** | ckpt.200.pth | 成熟阶段训练稳定高位 | **87.12%** | **54.76%** | 0.09941 | 34.24 |

本批三点中151.040M同时取得最好SR/SPL，相比76.288M高3.14/1.28pp；125.952M的SR上升但SPL明显低。与冻结基线74.240M的84.98/54.39%相比，151.040M高2.14/0.37pp，但训练预算不同。与覆盖256125.952M的87.57/53.30%相比，覆盖32151.040M的SR低0.45pp、SPL高1.46pp；两指标没有同时更高。准确相同步数125.952M对照，覆盖32比覆盖256低SR0.74pp/SPL5.50pp。两组optimizer/episode恢复历史仍不同，即使同步数也不声称严格因果比较。

选择在查看新val之前冻结：更新覆盖32曲线到158,801,920步，检查211个有完整3M阶段内上下文的保存点；76.288M与151.040M近1M训练SR/SPL分别88.95/52.66%、90.13/53.71%，125.952M为事先声明的同预算参考点（88.14/51.89%），未按新val反挑。新三点优于旧48.128M的83.05/51.90%程度见完整对照，不代表没有其他更优保存点。

原协议4200条Gibson val/14场景/6环境/max500/seed100/hash0/deterministic；SIGN-coverage-eval @a7cc9e0只读，加载完整导航权重，eval不用checkpoint训练配置。coverage bonus0、无Qwen，0.1m/3m/90°仅被动面积代理；面积/步为总新增面积÷总动作数，不是逐episode比值的均值。三份权重均103项key/shape兼容、42项冻结encoder与公开部分完全相同；初始资源各1A40/36CPU240GB/2h，现有作业未为本次查结果启停或移动。

证据：完整对照JSON（服务器：`/scratch/e1538633/liuyi/logs/gibson_coverage32_selected_eval_20261107/comparison.json`）、对照CSV（服务器：`/scratch/e1538633/liuyi/logs/gibson_coverage32_selected_eval_20261107/comparison.csv`）、独立逐条复核与完成状态（服务器：`/scratch/e1538633/liuyi/logs/gibson_coverage32_selected_eval_20261107/results_review_20261107.json`）、选点（服务器：`/scratch/e1538633/liuyi/logs/gibson_coverage32_selected_eval_20261107/selection/selected.json`）、权重核验（服务器：`/scratch/e1538633/liuyi/logs/gibson_coverage32_selected_eval_20261107/checkpoint_validation.json`）、实际提交（服务器：`/scratch/e1538633/liuyi/logs/gibson_coverage32_selected_eval_20261107/submission.json`）。无新实验/ZIP/push；GitHub f00c15c仍为13:58历史快照。WORKLOG：QWEN-AND-COVERAGE32-SELECTED-VALS-ALL-COMPLETE-20261107。

<a id="qwen-selected-eval-20261107"></a>
## 三组Qwen训练选点完整验证：全部完成

11月7日15:34独立复核：三个GPU **1528937/1528938/1528939** 和CPU汇总 **1528940** 均F/Exit0；最后GPU14:22:20结束，汇总14:23:39结束。每组完整4200条/14场景，任务/目标/起点与四参考组逐条匹配；成功率/SPL/碰撞/动作/面积均从episode原记录独立复算，结果与汇总SHA一致，运行源守卫通过。

| 方法 | 精确累计环境步 | 续跑文件 | 验证SR | 验证SPL | 总新增面积/总步数（m²/步） | 碰撞/episode |
|---|---:|---|---:|---:|---:|---:|
| Qwen128 β0.1 | **20,480,000** | ckpt.22.pth | 80.36% | **54.60%** | 0.07747 | 47.91 |
| A Qwen128 β0.03 | **36,352,000** | ckpt.54.pth | 82.38% | 52.97% | 0.08612 | 51.81 |
| B Qwen256 β0.03 | **29,696,000** | ckpt.40.pth | **84.50%** | 50.35% | 0.08698 | 48.75 |

<a id="qwen-reward-vs-official"></a>
**Qwen训练奖励是否超过公开完整SIGN（11月8日复核）：** 已完成的8份完整4200评估中，SR最高为Qwen256 β0.03的**84.50%**，低于公开完整权重本地实测**86.00%**（−1.50pp）；Qwen128 β0.1的SPL **54.60%**高于公开权重**53.01%**（+1.59pp），但它的SR仅80.36%。目前没有Qwen训练奖励checkpoint同时超过公开权重的SR/SPL，也没有SR超过的完整验证证据。选点评估时Qwen关闭，PPO训练奖励与后续推理恢复A/B（88.43%）分开，不能混作reward收益。预算/初始化/续跑历史不同，且未评估所有更晚checkpoint；不能据此断言Qwen奖励无效。审计logs/qwen_reward_vs_official_review_20261108.json。

三Qwen本批B的SR最高，β.1的SPL最高；没有某一Qwen保存点同时取得两项最高。冻结基线74.240M为84.98/54.39%：B低0.48/4.04pp；A低2.60/1.42pp；β.1低SR4.62pp、SPL高0.20pp。当前这些选点没有呈现SR/SPL同时领先，但训练步数仅20.480–36.352M、低于基线和成熟覆盖组，不能据此断言Qwen奖励无效或作同预算因果判断。三Qwen的全局面积/步均低于该74.240M基线0.09381，碰撞均高于37.06/episode，同样有训练预算和恢复历史混杂。

选点仅使用11月7日13:06冻结训练曲线，检查125个有完整3M阶段内历史的checkpoint；不按新val排名。β.1 20.480M在较早训练高位内部，A36.352M为最近回升高位且前1M SPL较高，B29.696M兼顾近1M/3M和前后25万步稳定性；分别近1M训练SR/SPL为87.24/48.92%、88.26/52.66%、88.43/51.47%。均CPU实读准确step，不把日志峰值当保存点，也不保证val最佳。

原协议4200条Gibson val/14场景/6环境/max500/seed100/hash0/deterministic，加载完整已训练导航权重。SIGN-coverage-eval @a7cc9e0只读，评估时Qwen worker及历史/图片采集关闭，探索bonus0；0.1m/3m/90°仅被动面积代理，不直接与训练0.025m口径混比。103项state key/shape兼容、42项公开冻结encoder相同，原生策略/传感器等9文件SHA相同。三份原预算各1A40/36CPU240GB/2h，CPU afterok正常完成；没有为查结果停止/重提训练或评估。

证据：完整七组对照JSON（服务器：`/scratch/e1538633/liuyi/logs/qwen_three_checkpoint_eval_20261107/comparison.json`）、对照CSV（服务器：`/scratch/e1538633/liuyi/logs/qwen_three_checkpoint_eval_20261107/comparison.csv`）、独立逐条复核和完成状态（服务器：`/scratch/e1538633/liuyi/logs/qwen_three_checkpoint_eval_20261107/results_review_20261107.json`）、选点（服务器：`/scratch/e1538633/liuyi/logs/qwen_three_checkpoint_eval_20261107/selection/selected.json`）、权重核验（服务器：`/scratch/e1538633/liuyi/logs/qwen_three_checkpoint_eval_20261107/checkpoint_validation.json`）、实际提交（服务器：`/scratch/e1538633/liuyi/logs/qwen_three_checkpoint_eval_20261107/submission.json`）。无新实验/ZIP/push；GitHub f00c15c仅含13:58时已完成的A，其他结果本次在服务器文档更新。WORKLOG：QWEN-AND-COVERAGE32-SELECTED-VALS-ALL-COMPLETE-20261107。

<a id="training-readout-20261107"></a>
## 11月7日最新训练：五组运行，Qwen有局部改善但未持续胜基线

事件采样在13:05–13:06，五组仍R；覆盖256已在11月5日21:45因PBS walltime耗尽结束。以下是各自最近100万步的**原生50-update滑窗日志均值**，不是验证结果；M=100万环境步，SR变化相对各自前100万步。不同进度不直接排名算法。

| 方法 | 累计日志步数 | 训练SR | 训练SPL | SR变化 | 当前状态 | 剩余PBS预算 |
|---|---:|---:|---:|---:|---|---:|
| Qwen128 β0.1 | 29.428M | 86.26% | 49.17% | +0.60pp | R | 18.1h |
| A：Qwen128 β0.03 | 36.415M | 88.40% | 52.71% | +1.68pp | R | 20.1h |
| B：Qwen256 β0.03 | 31.779M | 87.53% | 49.58% | -0.30pp | R | 42.2h |
| 覆盖256 | 172.599M | 87.80% | 50.60% | +1.28pp | 到walltime停止 | 0.0h |
| 覆盖32 | 158.073M | 89.55% | 52.59% | +0.71pp | R | 14.1h |
| C：几何128 | 75.856M | 88.97% | 52.42% | +1.57pp | R | 21.4h |

覆盖2561511146：F/Exit−29，PBS评论exceeded resource walltime，实际68:04:22／申请68:03:22，11月5日21:45:20结束；TB末事件21:45:14、172,599,296步。最后保存权重实读**ckpt.90＝172,544,000步**，全部保存参数有限，SHA70d32dbb047e0cde99afda53f3b287e0fdaf4c6531f10ed3457590495eeae041，含learner_state。训练末步与权重分开，未到300M算法cap；未重提或延长原预算。

Qwen目前最值得区分的结果：

- **A当前36.415M有短窗积极信号**：近1M88.40/52.71%，同预算比基线+0.41/+0.46pp、覆盖256+3.23/+3.21pp、覆盖32+0.69/+3.23pp；但近3M对基线−0.79/−1.01pp、对覆盖32SR−0.97pp，尚非持续全面领先。
- **B当前31.779M近3M对两覆盖SR/SPL均高**：87.96/50.50%，对256+2.03/+1.32pp、对32+0.75/+0.14pp；仍低基线−0.35/−2.37pp。其当前近1M比基线两项都低，保留全部1M/2M/3M，不只呈现3M。
- **β.1在11月5日的领先未延续到当前窗口**：29.428M近1M86.26/49.17%，低同预算基线−2.03/−1.07pp；近3M85.85/47.95%，对基线−2.84/−4.74pp，也低于两覆盖。没有据q均值或自身reward作成功率提升结论。

三Qwen统一截至**29,427,712步**，近3M严格逐点对齐：

| 同步数方法 | SR | SPL |
|---|---:|---:|
| 冻结基线原训练 | 88.69% | 52.69% |
| 覆盖256原训练 | 86.20% | 49.30% |
| 覆盖32原训练 | 87.60% | 49.93% |
| Qwen128 β.1续跑 | 85.85% | 47.95% |
| A Qwen128 β.03续跑 | 86.82% | 50.07% |
| B Qwen256 β.03续跑 | 88.14% | 49.59% |
| C几何128续跑 | 86.90% | 49.19% |

该共同窗口三Qwen的SR/SPL均未超过基线；B比两覆盖SR高，但SPL低于覆盖32。C使用实际续跑完整窗口26.428–29.428M，位于其22.528M重置之后，明确标phase，不使用已不足的旧原C22.587M末端、不跨reset拼接。基线/两覆盖是原训练，Qwen/C各自续跑重置历史不同，单种子/重叠窗口不作严格评分器因果结论。

健康：所有记录标量有限；6份旧事件前缀SHA重新核验，13类来源记录，SR/SPL与全部共同/各自1M/2M/3M step数组一致。三Qwen/C的ledger ID连续、nav_rewards/masks自检未变，混合reward守恒最大误差≤6.54e−5。Qwen有效片段约93.97%–95.35%（非评分准确率）、平均q约0.632/0.638/0.660；C无Qwen worker、render/worker计时0。三Qwen整轮约27–36秒，未修改运行环境/代码，不能将负载变化称实现加速。

证据：完整训练/共同与各自窗口（服务器：`/scratch/e1538633/liuyi/logs/training_readout_20261107/snapshot_130555/readout.json`）、简表（服务器：`/scratch/e1538633/liuyi/logs/training_readout_20261107/snapshot_130555/summary.json`）、导出值独立复算与来源（服务器：`/scratch/e1538633/liuyi/logs/training_readout_20261107/snapshot_130555/validation.json`）、覆盖256最后checkpoint（服务器：`/scratch/e1538633/liuyi/logs/training_readout_20261107/coverage256_last_checkpoint.json`）。仅CPU增量读取，不另复制全历史原始事件、不新增训练/评估、ZIP或GitHub push。WORKLOG：LATEST-TRAINING-AND-COVERAGE-CANDIDATE-EVAL-20261107。

<a id="coverage256-candidates-eval-20261105"></a>
## 两份覆盖256候选完整验证已完成：均未超过125.952M旧权重

143.360M的1523189、150.528M的1523190及CPU汇总1523191全部F/Exit0。GPU分别在11月5日15:44:13／15:09:42结束，汇总15:45:04结束；PBS资源walltime分别1:14:10／0:34:22，原生评估计时4397.15／2038.26秒，时间口径分开记录。11月7日CPU独立复算五组各4200条指标、唯一任务、目标图、起点和来源SHA，11保护树守卫均通过，无重新GPU评估。

| 方法/保存点 | 训练步数 | 成功/4200 | 验证SR | 验证SPL | 碰撞/episode | 总新增面积/总步数 m²/步 |
|---|---:|---:|---:|---:|---:|---:|
| 冻结视觉基线最终 | 74.240M | 3569 | 84.98% | 54.39% | 37.06 | 0.09381 |
| 覆盖256旧权重 | 125.952M | 3678 | **87.57%** | 53.30% | 36.68 | 0.10302 |
| 覆盖256候选1 | 143.360M | 3634 | 86.52% | 52.15% | 43.27 | 0.09959 |
| 覆盖256已验证峰值附近 | 146.944M | 3627 | 86.36% | **56.24%** | 34.26 | 0.09934 |
| 覆盖256候选2 | 150.528M | 3626 | 86.33% | 51.77% | 38.50 | 0.09810 |

相对125.952M，两新候选SR/SPL分别−1.0476/−1.1536pp、−1.2381/−1.5301pp，成功数净少44／52条。训练曲线候选没有带来更高验证结果；**这四份完整覆盖256验证中，SR最好仍125.952M、SPL最好146.944M**。不同训练步数，不是同预算方法因果排名，也不能推断未评估保存点的成绩。

两份均原生Gibson4200条／14场景／6环境／max500／seed100／hash0／deterministic，SIGN-coverage-eval @a7cc9e0只读；0.1m/3m/90°仅被动观测、coverage bonus0、无Qwen。CFP04-SF-109/auto→batch_gpu，每份1A40/36CPU240GB/2h；独立权重副本分别来自续跑ckpt.33/.47，step与SHA已核对。原训练未因评估而停止或移动，覆盖256后来的停止是自己训练walltime耗尽。

证据：自动五组完整对照（服务器：`/scratch/e1538633/liuyi/logs/gibson_coverage256_candidates_eval_20261105/comparison.json`）、11月7日逐条独立复核（服务器：`/scratch/e1538633/liuyi/logs/gibson_coverage256_candidates_eval_20261105/results_review_20261107.json`）、最终三作业状态（服务器：`/scratch/e1538633/liuyi/logs/gibson_coverage256_candidates_eval_20261105/completed_qstat_20261107.json`）、原提交回执（服务器：`/scratch/e1538633/liuyi/logs/gibson_coverage256_candidates_eval_20261105/submission.json`）。旧submission_status/current_status/status_20261105_afternoon均是当时历史状态，不再代表当前。无ZIP或GitHub发布。WORKLOG：LATEST-TRAINING-AND-COVERAGE-CANDIDATE-EVAL-20261107。

<a id="coverage256-peak-eval-20261105"></a>
## 11月5日覆盖256峰值附近完整验证：SR86.36%、SPL56.24%

**1520910.stdct-mgmt-02 F／Exit0**，新加坡时间01:19:04开始、02:14:08完成，PBS walltime55分02秒，原生评估计时3274.77秒。完整4200条／14场景已复核；任务、目标图、起点与此前两参考逐条一致，native TensorBoard与外部逐episode汇总一致，11保护源码树及数据/权重SHA守卫通过。

| 权重 | 累计训练步数 | 成功/4200 | SR | SPL | 碰撞/episode | 总新增面积/总步数 m²/步 |
|---|---:|---:|---:|---:|---:|---:|
| 冻结视觉基线最终 | 74,240,000 | 3569 | 84.98% | 54.39% | 37.06 | 0.09381 |
| 覆盖256上次 | 125,952,000 | 3678 | 87.57% | 53.30% | 36.68 | 0.10302 |
| 覆盖256本次 | **146,944,000** | **3627** | **86.36%** | **56.24%** | **34.26** | **0.09934** |

本次相对上次覆盖256：SR−1.2143pp（净少51次成功），SPL+2.9359pp；共同任务中208条由失败变成功、259条由成功变失败。相对冻结基线SR+1.3810pp、SPL+1.8419pp，但训练预算不同，不作同预算算法因果排名。训练日志SR峰值未对应更高验证SR，本权重提升了SPL，不能称两指标全面变好。平均episode步数113.56→116.64；覆盖效率的总面积/总步数0.10302→0.09934，而逐episode面积/步的算术均值0.20908→0.21259，两种汇总权重不同，分开记录。

用户原目标146,759,680为训练50-update窗SR94.84%的日志步数，无此精确保存权重；ckpt.39=146,432,000、ckpt.40=146,944,000，选更近的后者（+184,320步）。66个已保存checkpoint经CPU扫描确认；103参数项形状匹配旧权重且有限，42项冻结encoder与旧权重完全一致。独立副本SHA db29c1f71b8616e26d50bf24971e1b808dd56e6d84c60a7a4258eb52f132db6b，不把本次称为146.760M精确模型成绩。

原生6环境／max500／seed100／hash0，SIGN-coverage-eval @a7cc9e0只读，0.1m/3m/90°被动观测、几何bonus0、无Qwen。CFP04-SF-109 / auto→batch_gpu，1 A40 / 36 CPU / 240GB / 2h上限，提交前普通GPU2/4、GPUx4/4；无需暂停六训练。精确GPUhr余额仍因amgr未登录未知，不能用队列名额推算额度。

证据：完整对照（服务器：`/scratch/e1538633/liuyi/logs/gibson_coverage256_peak_eval_20261105/comparison.json`）、本次原始汇总（服务器：`/scratch/e1538633/liuyi/logs/gibson_coverage256_peak_eval_20261105/coverage256/result.json`）、4200逐条独立复核及成功迁移（服务器：`/scratch/e1538633/liuyi/logs/gibson_coverage256_peak_eval_20261105/results_review.json`）、配置与选点（服务器：`/scratch/e1538633/liuyi/logs/gibson_coverage256_peak_eval_20261105/manifest.json`）、最终PBS状态（服务器：`/scratch/e1538633/liuyi/logs/gibson_coverage256_peak_eval_20261105/completed_qstat.json`）。旧running_status/submission为提交时历史回执；以completed_qstat和本摘要为当前状态。无ZIP、新训练、额外GPU评估或GitHub发布。WORKLOG：COVERAGE256-PEAK-NEAREST-CHECKPOINT-FULLVAL-RESULTS-VERIFIED。

候选权重复核（11月5日14:12–14:16；两个主候选随后已获授权提交，见[新批次](#coverage256-candidates-eval-20261105)）：完整原训练读到126.175M、续跑读到168.176M，逐个对齐304个有完整3M上下文的保存点。**优先续跑ckpt.33＝143,360,000步**，近1M训练SR/SPL90.16/53.33%，近3M89.42/51.76%；前后各25万步SR91.50/90.38%，仍处于143M高位内部。备选续跑ckpt.47＝150,528,000步，近1M90.41/53.91%，前后25万步90.77/89.64%。143.872M虽然前1M均值较高，保存点附近已回落，不能只按滞后滑窗最大终点就近取权重。原训练105.984M为短窗高点（近1M91.72%，3M87.47%），仅留第三备选。最新168.176M近1M85.27/48.11%，暂不优先；以上均不是val预测。三候选extra_state.step经CPU读取、参数有限及SHA记录：选择证据（服务器：`/scratch/e1538633/liuyi/logs/training_readout_20261105/coverage256_candidates_20261105T141223/recommendations.json`）、局部窗口（服务器：`/scratch/e1538633/liuyi/logs/training_readout_20261105/coverage256_candidates_20261105T141223/local_neighborhoods.json`）。WORKLOG：COVERAGE256-CHECKPOINT-CANDIDATES-TRAINING-CURVE-REVIEW。

<a id="training-readout-20261105-afternoon"></a>
## 11月5日下午训练：Qwen128 β0.1回升，短窗口有积极信号

六组仍R；事件按顺序冻结于15:07–15:20，PBS于批次结束核对。以下为各自近100万步内**原生50-update滑窗日志的均值**，不是验证分数；累计环境步1M=100万。SR变化相对各自前100万步，不按不同训练进度直接排名方法。

| 方法 | 累计步数 | 训练SR | 训练SPL | SR变化 | 近3h秒/2048步 | 本轮剩余预算 |
|---|---:|---:|---:|---:|---:|---:|
| Qwen128 β0.1 | 20.791M | 88.15% | 50.37% | +1.11pp | 47.12s | 63.8h |
| A：Qwen128 β0.03 | 24.580M | 84.66% | 48.52% | -3.12pp | 32.52s | 65.8h |
| B：Qwen256 β0.03 | 19.487M | 85.44% | 49.77% | +2.00pp | 30.08s | 87.9h |
| 覆盖256 | 168.612M | 86.33% | 48.97% | +0.45pp | 12.48s | 6.4h |
| 覆盖32 | 99.224M | 87.03% | 51.71% | -0.94pp | 6.34s | 59.8h |
| C：几何128 | 54.010M | 87.85% | 49.92% | -0.87pp | 15.01s | 67.2h |

Qwen128 β.1的近1M训练SR从凌晨快照83.09%回升至88.15%，SPL47.94→50.37%；当前相对前1M SR+1.11pp。A的近1M比自身前1M低3.12pp，B回升2.00pp；不能将三组均称有优势。

在Qwen128 β.1当前**共同截至20,791,296步**，近1M/2M/3M逐点对齐后：

| 窗口 | Qwen β.1 SR/SPL | 对基线差 SR/SPL | 对覆盖256差 SR/SPL | 对覆盖32差 SR/SPL |
|---|---|---|---|---|
| 近1M | 88.15/50.37% | +1.48/−1.22pp | +2.90/+1.01pp | +0.80/+0.86pp |
| 近2M | 87.60/49.40% | +1.70/−0.89pp | +1.87/+0.36pp | +0.28/+0.13pp |
| 近3M | 86.49/49.05% | +0.17/−0.84pp | +0.95/+0.67pp | −0.16/+0.22pp |

因此存在**近期局部的训练积极信号**：1M/2M同时胜两旧覆盖的SR/SPL，SR也高于基线，但基线SPL仍更好；3M对覆盖32的SR优势消失，尚未证明持续或验证泛化收益。A自己24.580M近1M相对基线SR−4.73/SPL−5.49pp；近3M相对两覆盖的SR/SPL略高（对256+0.26/+0.54、对32+0.58/+0.20pp），仍低于基线−1.52/−3.35pp。B在19.487M近1M相对基线SR−1.02pp、SPL+0.30pp，SR未领先。

更严格的三Qwen共同预算19,486,720步，近3M训练均值：基线86.97/49.56%、覆盖25686.34/48.23%、覆盖3286.57/48.76%、C86.01/48.63%、Qwenβ.1 85.85/48.78%、A84.07/48.47%、B84.79/49.45%。三Qwen在该完整共同区间的SR均低于基线/两覆盖；Qwenβ.1的最近恢复主要发生在该共同终点之后，需要分别看自己的当前同预算窗口，不能只选有利切片。

健康检查：六组全部标量有限，三Qwen与C的rollout ID连续、nav_rewards/masks未变，混合reward守恒最大误差≤6.53e−5。三Qwen几何/输入有效率94.02%–95.39%，不等同评分准确率；平均q约0.63/0.63/0.66，不把q升高当导航进步。C无Qwen worker、render/worker计时0。Qwen自身 worker峰值约9.36GiB（非整作业显存），worker均值约8–10秒/rollout，绘图另约8–13秒，三组整轮约30–47秒；未改运行环境或安装加速库。覆盖256预算约剩6.4h，其余约60–88h，未延长原预算或重启。

Qwen为续跑、对照在这些步数为原训练，optimizer/episode历史不同；单种子、重叠窗口不作独立样本显著性或评分器因果声明。旧0.1m全动作面积与新0.025m有效动作面积口径不同，不跨口径排名效率。

证据：六组当前/各自同预算/共同预算1M–3M（服务器：`/scratch/e1538633/liuyi/logs/training_readout_20261105/snapshot_150755/training_comparison.json`）、完整事件/ledger汇总（服务器：`/scratch/e1538633/liuyi/logs/training_readout_20261105/snapshot_150755/readout.json`）、健康与来源核验（服务器：`/scratch/e1538633/liuyi/logs/training_readout_20261105/snapshot_150755/validation.json`）。旧snapshot_150000为未完成CPU尝试，明确attempt_status，不作结果；v2补读原C完整历史到22,587,392，修复旧18,020,352参照不足。原训练/评估作业未停止或新增，无ZIP或GitHub发布。WORKLOG：TRAINING-READOUT-AFTERNOON-QWEN-RECOVERY-20261105。

<a id="training-readout-20261105"></a>
## 11月5日凌晨训练快照：当时Qwen128近期回落

事件快照读取于00:45–00:47（SG），PBS在批次结束核对六组均R。以下是各自最近100万步的**原生50-update滑窗日志均值**，不是完整验证，步数是累计环境步（1M=100万）。SR变化相对各自前100万步。C使用train_after_latest_eval，不混入已停止的前一续跑阶段。

| 方法 | PBS | 累计步数 | 训练SR | 训练SPL | SR变化 | 近3h秒/2048步 | 快照剩余预算 |
|---|---|---:|---:|---:|---:|---:|---:|
| 覆盖256 | 1511146 R | 159.807M | 87.70% | 49.27% | -0.48pp | 9.32s | 20.9h |
| 覆盖32 | 1511147 R | 82.354M | 86.46% | 49.71% | -0.41pp | 5.40s | 74.4h |
| C 几何128 | 1511410 R | 46.774M | 87.65% | 51.00% | -0.24pp | 13.91s | 81.8h |
| Qwen128 β0.1 | 1511145 R | 18.199M | 83.09% | 47.94% | -4.60pp | 41.80s | 78.4h |
| A Qwen128 β0.03 | 1511143 R | 21.119M | 82.40% | 46.11% | -4.08pp | 28.53s | 80.4h |
| B Qwen256 β0.03 | 1511148 R | 15.837M | 86.23% | 49.45% | +2.85pp | 25.79s | 102.5h |

覆盖256专项复核：截至159.807M，最近五个连续1M区间SR依次88.83→88.90→88.34→88.18→87.70%，呈近期回落；相较11月3日140.716M近1M的89.19%低1.49pp，SPL51.68→49.27%。最新原生单滑窗SR85.15%，不能将单点当整个1M均值。证据snapshot_004537/coverage256_recent_trend.json，尚无对应最新完整val。 后续全段复核：11月3日89.19%之后仍有更高窗口，142.620–143.620M的移动1M峰值SR91.17%/SPL54.22%（11月4日02:11）；146.760M原生50-update窗SR94.84%/SPL57.18%（06:36）。149.716–150.716M非重叠1M均值仍90.52%，之后才有近期回落。见snapshot_004537/coverage256_sr_peaks.json；不同窗口大小分开解释，不将训练峰值当验证最佳。

Qwen128 β0.1：前1M SR87.69/SPL49.10%→当前83.09/47.94%；A：86.48/49.13%→82.40/46.11%，两者近期回落。B：83.38/46.75%→86.23/49.45%，当前有所恢复。C的SR约稳定，SPL49.31→51.00%；两旧覆盖SPL均有回落。不同进度不能据当前六行排名训练方法。

共同截至15,837,184步，最近300万步（12.837–15.837M）训练均值：

| 方法 | SR | SPL |
|---|---:|---:|
| 冻结基线 | 86.42% | 49.07% |
| 覆盖256 | 86.15% | 48.71% |
| 覆盖32 | 86.22% | 48.65% |
| C 几何128 | 85.85% | 49.48% |
| Qwen128 β0.1 | 85.45% | 48.49% |
| A Qwen128 β0.03 | 84.91% | 46.55% |
| B Qwen256 β0.03 | 85.19% | 48.46% |

三Qwen在本共同窗口的SR/SPL均未超过冻结基线，亦未超过两旧覆盖；1M/2M/3M窗口均保留，不只挑有利局部。β0.1相对基线在3M为SR−0.97pp/SPL−0.58pp，B为−1.23/−0.61pp，A为−1.51/−2.52pp。Qwen源为续跑、原参照在此区间尚为未中断原训练，且MRQ/面积与有效性口径不同；单种子与重叠滑窗不作显著性或纯评分器因果声明。

健康检查：六组所有标量有限，事件快照时年龄约7–34秒；三Qwen与C的ledger ID连续，nav_rewards/masks未改，混合奖励守恒最大误差约5.92e-5；旧覆盖守恒约1.79e-8。C无Qwen worker或渲染，旧0.1m全动作面积与新0.025m有效动作面积不跨口径排名。训练reward仍为导航reward，bonus独立记录。

证据：最新快照（服务器：`/scratch/e1538633/liuyi/logs/training_readout_20261105/snapshot_004537/readout.json`）、共同步数1M/2M/3M（服务器：`/scratch/e1538633/liuyi/logs/training_readout_20261105/snapshot_004537/matched_windows.json`）、14输入SHA与健康核验（服务器：`/scratch/e1538633/liuyi/logs/training_readout_20261105/snapshot_004537/validation.json`）。只读提取，未调整/停止/提交PBS，未跑新验证、未打包。WORKLOG：TRAINING-READOUT-SIX-RUNS-20261105。

<a id="sign-failure-replay-goal-20261104"></a>
## 已完成：SIGN全量失败诊断（ZIP已清理，原始报告与证据保留）

三组各4200 Gibson val任务完整重放已完成，固定原checkpoint/起点/目标图/native6环境/max500/seed100/hash0，复用只读SIGN-coverage-eval @a7cc9e0。GPU **1518132/1518133/1518134**、CPU分析 **1518137**均F/Exit0。原11保护树/权重/输入守卫通过；全部12600条的steps/SR/SPL/VM/nav reward/碰撞/goal/start/pose/覆盖面积和效率共11字段逐条与原记录精确一致。**原六训练未修改/停止，未实施推理Agent。**

| checkpoint | 失败/4200 | 从未进1m（占失败） | 曾进1m却失败 | 末64步持续受阻候选 | 低增益移动闭环候选 |
|---|---:|---:|---:|---:|---:|
| 冻结基线74.240M | 631 | 566（89.70%） | 65 | 116（18.38%） | 420（66.56%） |
| 覆盖256125.952M | 522 | 465（89.08%） | 57 | 76（14.56%） | 350（67.05%） |
| 覆盖3248.128M | 712 | 660（92.70%） | 52 | 166（23.31%） | 447（62.78%） |

这些是可核实结束阶段与非互斥行为候选，**不是视觉/规划/控制病因的互斥比例**，也不是不同训练预算下的算法因果排名。闭环成功组发生率8.83/8.37/7.97%，存在合理返回/控制摆动，不能一回访就判冗余；单步碰撞也不等于卡住。强受阻末段的成功组发生率0.11/0.16/0.14%，但这是回顾性末段统计，不当在线检测精度。

原轨迹完美GT停止的SR增量上界为1.55/1.36/1.24pp；会改变路线的恢复/否决过早STOP不受这一固定轨迹上界约束。曾近失败的最长连续目标区窗口中位数为9/8/9个状态，不能把128步探索结算频率直接当到达检测。另有24%–30%失败曾到2m内，局部接近与停止边界需单列。三组500步结束的失败均未同时STOP，消除了此前到限桶歧义。

额外质量审计：0.1m二维栅格与真实navmesh不等价，部分位置投影无效时fog射线在起点退出，覆盖0不等于没有新RGB信息。单地图可审计失败的每轨迹无效投影比例中位数19.35/21.43/18.76%；多高度中间图未保存，is_navigable未记录，不能由此断言真实位置不可达或量化训练因果影响。原指标/奖励/代码未修；规则在数据前固定，栅格审计是发现个例后的补充。SR/结束阶段/运动受阻证据不依赖面积代理。

证据与阅读入口：

- 完整离线报告（服务器：`/scratch/e1538633/liuyi/logs/sign_failure_replay_20261104/analysis/index.html`） · 73案例浏览页（服务器：`/scratch/e1538633/liuyi/logs/sign_failure_replay_20261104/analysis/review/index.html`）。17条AI证据笔记覆盖6场景（含成功闭环/高碰撞成功对照），人工主因标签全部空。
- 数字摘要（服务器：`/scratch/e1538633/liuyi/logs/sign_failure_replay_20261104/analysis/findings.json`）、全量统计/三档敏感性（服务器：`/scratch/e1538633/liuyi/logs/sign_failure_replay_20261104/analysis/analysis.json`）、全部1865模型-任务失败CSV（服务器：`/scratch/e1538633/liuyi/logs/sign_failure_replay_20261104/analysis/failed_episodes.csv`）。涉及1061个至少一模型失败的不同任务，其中257三者都失败；共同任务（服务器：`/scratch/e1538633/liuyi/logs/sign_failure_replay_20261104/analysis/paired_tasks.csv`） / 共同失败（服务器：`/scratch/e1538633/liuyi/logs/sign_failure_replay_20261104/analysis/common_failures.csv`）。
- 数据审计（服务器：`/scratch/e1538633/liuyi/logs/sign_failure_replay_20261104/analysis/data_audit.json`）：12600 trace、1991完整视频/829982帧及原目标PNG字节SHA均通过；原11字段审计（服务器：`/scratch/e1538633/liuyi/logs/sign_failure_replay_20261104/analysis/reference_audit.json`）通过；13项CPU单元测试通过。RGB审查视频/JPEG有损，不能据此重建原Actor隐藏状态。
- 支持脚本/输入/源码SHA/作业回执均在logs/sign_failure_replay_20261104。原生录数运行期按source_manifest固定；分析代码按analysis_source_manifest固定。两个旧失败smoke 1515859/1518122与修复证据保留attempts，新smoke1518125控制/诊断28条及4274帧通过。
- 打包1518613曾F/Exit0，CRC和269解压链接核验记录保留在package_results.json（服务器：`/scratch/e1538633/liuyi/logs/sign_failure_replay_20261104/package_results.json`）。**2026-11-05按用户要求已删除报告/全量证据两个ZIP，共1591855136字节（约1.48GiB）**，见清理回执（服务器：`/scratch/e1538633/liuyi/logs/sign_failure_replay_20261104/zip_cleanup_20261105T004126.json`）。原始analysis/、full/、轨迹、视频、CSV/JSON、源码和日志全部保留；上述报告/案例链接仍可直接使用。以后有明确下载或打包需求再生成ZIP，不自动补包。**本Goal工作已完成，暂无待自动提交的新实验。**

后续方向仅为报告中的待验证推理事件管理器：受阻恢复、循环/访问记忆、目标确认与STOP复核；已有topdown效率q不是到达概率。诊断GT不直接当部署输入；原控制范围只允许前进/转向、物理双低速STOP。未启动任何Agent或导航训练。复现方法见[RUNBOOK](RUNBOOK.md#sign-failure-diagnosis)，操作沿革见WORKLOG FAILURE-REPLAY-ALL-12600-COLLECTED与FAILURE-DIAGNOSIS-REPORT-PACKAGED-COMPLETE。

<a id="sign-failure-analysis-20261104"></a>
## 11月4日：SIGN失败标签与失败原因分析（仅分析，尚不实现Agent）

以下为11月4日初次静态审计的历史记录；随后用户另授权的全量诊断已完成，最新结论以上方完整报告为准。当时仅只读现有代码/结果并做CPU离线统计，未改策略、训练、环境、评估记录器或提交新GPU。当前没有failure_reason/failure_type等语义标签；训练原生保存done/masks和50-update episode统计，native评估结束时聚合，额外录数器有逐episode摘要但没有逐步动作/完整位置/RGB/最近目标距离。pose_trace_sha256只用于核对重放一致，不能还原轨迹。Qwen geometry_reason标注地图统计有效性，不是导航失败病因；定期样图和32条开发轨迹不代表全量失败分布。

实际代码：仅continuous_control，实际线速度<0.025m/s且角速度绝对值<1.5°/s触发is_stop_called；任务因此结束。Success要求STOP且目标测地距离<1m；view_match为0.5/1仍均属于SR成功，朝向未对齐不能自动计为SR失败。ViewAngle在SR失败时写180°默认值，也不能据此认定朝向失败。训练上限1000步、当前val500步，时间上限10000000秒；这两种任务不可混算失败比例。

现有三组各4200条完整val的终止现象（百分比以各自失败数为分母，**不是语义失败原因占比**）：

| 模型/训练步数 | 失败数 | 500步前失败：由代码推断触发STOP | 第500步失败：到限或最后一步STOP尚无法区分 |
|---|---:|---:|---:|
| 冻结基线74.240M | 631（15.02%全部任务） | 100（15.85%失败） | 531（84.15%失败） |
| 覆盖256125.952M | 522（12.43%全部任务） | 111（21.26%失败） | 411（78.74%失败） |
| 覆盖3248.128M | 712（16.95%全部任务） | 97（13.62%失败） | 615（86.38%失败） |

500步前失败可在当前代码/实际时间预算下推断为STOP，但记录未直接写stop_flag；第500步可能同时STOP，不全部命名为精确timeout。三组训练预算不同，不据失败率差声称算法因果优势。覆盖256的到限失败组平均collisions/steps=45.76%，成功组平均逐episode比值15.65%；该相关性提示优先看受阻/局部徘徊，不表示45.76%的失败由碰撞造成。Scioto/Mosquito/Swormville共235/522失败（45.02%），每场景各300任务；场景分层有必要，不据此假定其具体布局原因。

真正病因仍未知，应分开标注：受阻/卡住（前进指令与实际位移不符）、循环重复搜索（轨迹/视野重复且无进展，排除必要返回/共用通路）、未找到目标邻域、曾接近目标后错过/未停止、提前停止但目标判断依据不明。停止失败不直接等于视觉误识别；碰撞/摆动/脱困不自动算重复探索。可多次出现的行为与episode主因分开，一主因加若干次因、允许unknown，AI初审不当人工真值。

后续可考虑、**本轮未实施**：固定checkpoint/协议/任务起点及目标图SHA，按场景×结束方式分层抽取失败和成功对照；确定性重放记录每步实际/指令速度、位姿、碰撞、目标当前/最近距离、覆盖增量及目标/RGB关键帧。用原pose_trace哈希检查重放是否一致；仅有同episode ID不自动保证相同目标图。人工复核后按分层抽样权重还原失败原因占比。GT地图/坐标/目标距离仅作离线诊断，部署Agent只用允许观测；保持同500步预算/动作范围。当前仅CNN+GRU直接输出速度，无独立显式地图/重规划/失败检测模块，适合作为记忆、无进展监控、解困、STOP复核等待检验切入点，不能从架构直接断言主因。USL_correction虽有定义，当前native评估act链没有调用；不把它过度干预当已确认原因。

证据：离线统计/源SHA/逐场景分布（服务器：`/scratch/e1538633/liuyi/logs/sign_failure_audit_20261104/snapshot_001350/analysis.json`）、1865条模型-episode失败记录，人工主因留空（服务器：`/scratch/e1538633/liuyi/logs/sign_failure_audit_20261104/snapshot_001350/failed_episodes_for_review.csv`）、独立计数与18输入SHA核验（服务器：`/scratch/e1538633/liuyi/logs/sign_failure_audit_20261104/snapshot_001350/validation.json`）。完整数据已保留，未新采样；WORKLOG：SIGN-FAILURE-TAXONOMY-AND-END-CONDITION-AUDIT-20261104。

<a id="qwen-matched-assessment-20261103"></a>
## Qwen同训练步数优势：短窗有信号，整体收益未确认

用户进一步追问同预算是否有优势。本次复用22:06–22:08固定快照和已完成8.192M完整val，未重采样、运行GPU或改训练；从六方法CSV按共同终点12,910,592重新计算最近1M/2M/3M，组内SR/SPL step逐项相同。结果不只挑选此前较有利的1M。

截至12.911M，最近3M训练均值（9.911–12.911M）：

| 方法 | 训练SR | 训练SPL |
|---|---:|---:|
| 冻结基线原训练 | 85.82% | 47.26% |
| 旧覆盖256原训练 | 84.14% | 46.67% |
| 旧覆盖32原训练 | 84.45% | 46.99% |
| C几何128原训练 | 84.13% | 47.04% |
| Qwen128 β0.1续跑 | 84.89% | 48.20% |
| A Qwen128 β0.03续跑 | 84.63% | 47.03% |

β0.1比覆盖256 SR/SPL +0.74/+1.53pp，比覆盖32+0.44/+1.21pp，有一定训练优势；相对冻结基线则SR−0.93pp/SPL+0.94pp，是取舍。A相对256仅+0.48/+0.36pp，相对32+0.18/+0.05pp，未超过C的SPL，优势较小。

窗口敏感性，相对同预算冻结基线：

| Qwen版本 | 最近1M ΔSR/ΔSPL | 最近2M ΔSR/ΔSPL | 最近3M ΔSR/ΔSPL |
|---|---|---|---|
| 128 β0.1 | +1.80/+2.81pp | +0.49/+1.32pp | −0.93/+0.94pp |
| A 128 β0.03 | +2.72/+2.46pp | +0.71/+0.95pp | −1.19/−0.23pp |

A在更晚12.922–13.922M自身窗口已回落到84.19/45.84%，不能把11.911–12.911M的86.22/48.21%当其当前值。Qwen续跑重置optimizer/episode，历史参照该段为原训练；旧覆盖与Qwen另有MRQ目标/面积分辨率/有效性规则差异，不能称只替换评分器的因果对照。单种子及重叠滑窗也不支持统计显著性声明。

完整验证（均8,192,000步、4200任务、原协议、训练中断前权重）：基线SR78.50/SPL48.96%，覆盖25679.21/47.00%，覆盖3277.45/50.43%，Qwenβ.177.62/45.16%，A78.98/45.69%，B Qwen256β.0379.17/48.00%，C78.60/49.52%。B相对基线SR+0.67pp但SPL−0.96pp，相对旧256约持平SR/SPL+1.00pp，属于局部取舍；尚无Qwen版本在该点同时超过基线SR和SPL，也未显示超过几何C的稳定独有收益。12–14M新阶段尚无完整val结果。

当前判断：**有局部训练信号，β0.1相对旧覆盖更值得关注；未确认相对基线的稳定整体优势或泛化收益。** 证据1/2/3M同预算复算与8.192M原结果索引（服务器：`/scratch/e1538633/liuyi/logs/training_readout_20261103/qwen_matched_advantage_220651.json`），保留6个输入SHA、每窗分母与所有正负差；WORKLOG：QWEN-MATCHED-BUDGET-ADVANTAGE-ROBUSTNESS-REVIEW。

<a id="queued-training-auto-20261103"></a>
## 11月3日23:03：两排队训练已按用户要求移至auto

覆盖32 **1511147**与B Qwen256β0.03 **1511148**已用qmove原位转入**auto→batch_gpu / CFP04-SF-109**，23:05复核均Q，原因node_pool资源不足。GPUx每用户4个运行上限不再阻塞这两作业；仍须等普通GPU资源，不能称已经开跑。原ID、输出、依赖、1A40/36CPU240GB与walltime99:28:14/127:34:32逐项不变，未重复qsub，未停止四个正在运行的训练，也未改基线验证。保留此前续跑初始化/预算与源码，只有队列改变。回执auto_queue_move_20261103.json（服务器：`/scratch/e1538633/liuyi/logs/training_continuation_20261103/auto_queue_move_20261103.json`）；WORKLOG：QUEUED-COVERAGE32-AND-QWEN256-MOVED-TO-AUTO。

<a id="training-readout-20261103-evening"></a>
## 11月3日22:06–22:08：续跑训练指标与作者默认步数

作者原始提交dad87fe的`exp_config/ppo_imagenav_gibson.yaml:12`为**total_num_steps: 3e8，即所有环境累计3亿步**，num_updates=-1；它不是每个环境3亿，也不是3000万。当前训练保留此累计上限，8×256=2048步/轮，另受PBS剩余时间预算约束。原配置文件SHA已存本次readout。

下表为各自**最近100万步的原生50-update完成episode滑窗日志点均值**，不是完整训练集或验证集成绩；不同当前步数不能直接排方法名次。新阶段仅使用各自最新续跑目录；几何C只用train_after_latest_eval，不混入已主动终止的第一轮续跑。

| 方法 | 状态 | 最新日志累计步数 | 近1M训练SR | 近1M训练SPL | 近3h中位秒/2048步 |
|---|---|---:|---:|---:|---:|
| 冻结视觉基线 | 已停止 | 74,653,696 | 87.87% | 54.82% | — |
| 覆盖256 | R/1511146 | 140,716,032 | 89.19% | 51.68% | 10.30 |
| 覆盖32 | Q/1511147 | 48,377,856（旧日志） | 84.16% | 47.09% | — |
| Qwen128 β0.1 | R/1511145 | 12,910,592 | 85.30% | 48.56% | 35.33 |
| A Qwen128 β0.03 | R/1511143 | 13,922,304 | 84.19% | 45.84% | 26.12 |
| B Qwen256 β0.03 | Q/1511148 | 9,189,376（旧日志） | 85.21% | 48.54% | — |
| C 几何128 | R/1511410 | 32,454,656 | 85.99% | 49.64% | 13.79 |

两排队训练没有新TB，成绩明确引用10月31日原日志，正式续跑将分别从48,128,000/8,704,000步旧checkpoint继承；不将其旧日志末步称已完成的续跑进度。冻结基线为10月28日停止记录。GPUx四运行上限已满，两个Q原因仍是每用户max_run；7424万基线val1515117在快照时仍Q/node_pool，22:13最终查询已R；本次未改作业。

近期趋势（与各自再前100万步均值比较）：覆盖256 SR+1.50pp、SPL−0.05pp；β0.1 −0.49/+0.10pp，较平稳；A −2.04/−2.42pp，有回落；C −1.12/−0.54pp。单个窗口不用于下收敛或稳定退化结论。

以两条已运行Qwen的共同最新步数12,910,592为终点，统一比较(11,910,592,12,910,592]，六方法SR/SPL各489个step逐项相同：

| 方法/历史阶段 | 同预算训练SR | 同预算训练SPL |
|---|---:|---:|
| 冻结基线原训练 | 83.50% | 45.75% |
| 覆盖256原训练 | 82.59% | 45.28% |
| 覆盖32原训练 | 81.73% | 45.14% |
| C几何128原训练 | 81.49% | 44.88% |
| Qwen128 β0.1续跑 | 85.30% | 48.56% |
| A Qwen128 β0.03续跑 | 86.22% | 48.21% |

这段β.1/A较原覆盖256 SR/SPL分别+2.71/+3.28、+3.63/+2.93pp，出现训练数值改善；**两Qwen在8.704M/8.192M重置过优化器/episode，历史参照该区间为原连续训练，故不是仅改变奖励的控制实验，也不是验证集收益。** B尚未到这一预算，未强行纳入；A此窗口的86.22/48.21与它更晚当前窗口的84.19/45.84均保留，避免挑选有利窗口。

4运行组所有训练scalar有限；覆盖bonus守恒最大误差1.79e-8，三新组全局offset映射/局部ledger连续，nav_rewards/masks全程不变，混合reward守恒误差≤5.44e-5。β.1/A/C近1M几何有效率93.03/93.23/93.93%，有效动作面积效率0.17371/0.16005/0.17799m²，旧256为0.19204m²/全部动作但分辨率0.1m、计数口径不同，不跨族排名。C无worker/渲染，未新增Qwen或训练设置。

证据：固定字节事件/ledger与均值（服务器：`/scratch/e1538633/liuyi/logs/training_readout_20261103/snapshot_220651/readout.json`）、16项CSV独立复算/11输入SHA核验（服务器：`/scratch/e1538633/liuyi/logs/training_readout_20261103/snapshot_220651/validation.json`）、只读脚本（服务器：`/scratch/e1538633/liuyi/logs/training_readout_20261103/continuation_readout.py`）。所有快照完整记录，无部分尾记录；原运行源码/作业未变，未新训练/验证或push。WORKLOG：CONTINUATION-TRAINING-READOUT-AND-300M-DEFAULT-20261103。

<a id="baseline-final-eval-20261103"></a>
## 11月3日21:56：冻结基线74.240M最终权重已提交完整val

用户要求评估冻结视觉基线最后保存的**74,240,000步**权重。本轮只评估，不恢复基线训练。原1496716的停训备份`logs/qwen_token_probabilities_20261028/baseline_stop_1496716/last_saved_checkpoint.pth`经SHA c3bf5d3e13a789f28b95c92b93ae7e31c4327f4a328bf59632f504b7b1eed73f核对后复制到独立支持目录；CPU加载核实真实步数、103项状态有限、42项encoder等于公开模型。

**1515117.stdct-mgmt-02**：CFP04-SF-109/auto→batch_gpu，1A40/36CPU240GB/**2h上限**；已接受，21:56为Q/Hold_Types=n，等待node_pool。当前GPUx四个训练占满每用户max_run=4，普通GPU队列有独立每用户上限；此次选择auto保留全部现有训练，没有停C或重复提交训练。剩余额度数字仍未知，不将提交接受称为余额核实。

复用已验证的SIGN-coverage-eval原生评估及两覆盖最新评估脚本，仅把允许的case改为baseline；录数器/固定任务清单字节相同，Python/PBS语法和原11运行树/资产/输入守卫通过。**4200条/14场景、6环境、max500、seed100/hash0、相同public safety、被动0.1m/3m/90°覆盖weight0、无Qwen**，记录SR/SPL、覆盖效率、碰撞、动作数和耗时。无新训练代码修改，准备阶段未用GPU。

**最新进展：22:13查询1515117已R**，在普通GPU队列实际获得资源；初始Q为提交时状态。

**1515118**为CPU汇总，afterok:1515117（当前H(d)正常），将核对本次基线与已完成coverage256/32的4200条任务/目标图/起点一致，生成独立comparison.json，保留旧结果。三组步数分别74.240M/125.952M/48.128M，仍不是同步数对照；覆盖256相对公开完整checkpoint的SR/SPL数值约+1.57/+0.29pp，不据此确认覆盖奖励独立收益。

输出与证据：支持目录（服务器：`/scratch/e1538633/liuyi/logs/gibson_baseline_final_eval_20261103`）、提交回执（服务器：`/scratch/e1538633/liuyi/logs/gibson_baseline_final_eval_20261103/submission.json`）、最新PBS状态（服务器：`/scratch/e1538633/liuyi/logs/gibson_baseline_final_eval_20261103/job_states_latest.json`）、checkpoint审计（服务器：`/scratch/e1538633/liuyi/logs/gibson_baseline_final_eval_20261103/checkpoint_audit.json`）。未来结果为`baseline/result.json`，原记录`baseline/episodes/`与`baseline/native/tb/`；三组汇总`comparison.json`。提交时尚无结果。现已完成：1515117 Exit0、PBS用时00:53:18，SR84.9762%（3569/4200）、SPL54.3936%。CPU汇总1515118因节点PATH缺git报FileNotFoundError而Exit1，导航评估本身正常；11月4日已在登录节点CPU运行未修改的summarize.py，通过源SHA/4200任务/目标图/起点核验并生成comparison.json，无需重跑GPU。旧CPU作业退出码仍为1，未改写为成功。未push新资料。WORKLOG：FROZEN-BASELINE-FINAL-74240K-FULLVAL-SUBMITTED-20261103、BASELINE-FINAL-CPU-SUMMARY-RECOVERED-20261104。

<a id="coverage-latest-eval-20261103"></a>
## 11月3日：最新两覆盖完整val已完成，几何128已恢复

用户已明确选择“立即暂停，接受回退到2252.8万步”。**C1511144已停止，Exit143、实际用时00:53:20**；被停止的该轮未落盘正式checkpoint，最后TB为22,827,008步，回退到22,528,000会舍弃299,008已记录环境步及本轮优化器状态。旧日志/权重保留，未删除或改算法。

两次已在11月3日03:51前完成，**均4200条/14场景、Exit0**；09:36复核逐episode记录无重复、数值有限、任务/目标图/初始位置逐项一致，7项主要指标从原记录独立复算等于result/summary。

| 评估方法 | checkpoint步数 | SR | SPL | 新增面积/动作（全局m²） | 平均碰撞 | 平均动作数 | 作业/用时 |
|---|---:|---:|---:|---:|---:|---:|---|
| 覆盖256 | 125,952,000（ckpt.245） | 87.5714%（3678/4200） | 53.2996% | 0.103023 | 36.6786 | 113.5593 | 1511395 Exit0/00:55:21 |
| 覆盖32 | 48,128,000（ckpt.93） | 83.0476%（3488/4200） | 51.9041% | 0.085819 | 43.4448 | 134.7238 | 1511396 Exit0/00:27:27 |

两权重已复制并冻结SHA，后续训练落盘不改变本次输入。各跑相同**4200条/14场景完整Gibson val，6环境、max500、seed100/hash0**；沿用native evaluator，只读0.1m/3m/90°覆盖记录、coverage奖励0、Qwen关闭。全局效率为sum(新增面积)/sum(实际动作)，不是逐episode比值均值；后者256/32分别0.209079/0.197461m²/动作，二者不能混用。平均新增面积为11.6992/11.5619m²。不同计算节点上的评估耗时不能直接当算法或训练吞吐对比。

相比各自18,944,000步完整val，256的SR/SPL增加8.4762/1.3177pp、全局效率增加34.47%；32增加1.0238/0.1508pp、全局效率增加3.75%。更晚checkpoint有改善；256当前训练步数约为32的2.62倍，不能据本表认定256结算优于32或探索奖励已优于同预算基线。面积/步改善可能同时受更快成功终止影响，单个面积效率比值不能证明无效重复探索减少。公开完整模型历史SR86.00/SPL53.01%仅作参考，不是同初始化/训练预算对照。

有效两GPU作业均为**CFP04-SF-109/autox→batch_gpux，各1A40/36CPU240GB/2h上限**，串行复用释放的槽位；没有在登录节点运行GPU评估。项目请求已接受并实际运行，剩余额度数字仍未知：`hpc project`要求amgr登录，不把许可或默认1000h当余额。初次个人auto尝试1511374/1511375及汇总1511376因node_pool等待，已在未运行时取消，不与有效作业混淆。

自动恢复已实际执行：**1511409** CPU清理Exit0，03:51:30解除覆盖32训练**1511147**与B训练**1511148**的临时u挂起；09:36两者为Q/Hold_Types=n，等待GPUx每用户运行上限，不是依赖或人为挂起。**1511410**为C恢复，已03:51:14在GN-A40-021开始R，从原22,528,000权重继续，上限**126:41:13**（原127:34:33再减53:20），独立输出`SIGN-continue-ablation/results/continuation_20261103/C/train_after_latest_eval`。**1511411**汇总Exit0，已经核对4200任务/目标/起点并生成summary.json。未操作其余训练。

证据与结果：完整结果（服务器：`/scratch/e1538633/liuyi/logs/gibson_coverage_latest_eval_20261103/summary.json`）、本次独立复算/作业状态/原始记录SHA（服务器：`/scratch/e1538633/liuyi/logs/gibson_coverage_latest_eval_20261103/results_review.json`）、输入与协议（服务器：`/scratch/e1538633/liuyi/logs/gibson_coverage_latest_eval_20261103/manifest.json`）、有效提交依赖图（服务器：`/scratch/e1538633/liuyi/logs/gibson_coverage_latest_eval_20261103/priority_submission.json`）、已解除临时挂起（服务器：`/scratch/e1538633/liuyi/logs/gibson_coverage_latest_eval_20261103/released_training_holds.json`）、C回退实测（服务器：`/scratch/e1538633/liuyi/logs/gibson_coverage_latest_eval_20261103/C_pause_progress.json`）。两组result.json/episodes/native TB及PBS原日志均保留；未修改源训练代码或提交新作业，本批次未push资料。WORKLOG：LATEST-COVERAGE-FULLVAL-PRIORITIZED-AND-C-PAUSED-20261103、LATEST-COVERAGE-VAL-FINISHED-REVIEWED-20261103。

## 11月3日：六组中断训练已提交续跑

六旧正式于10月31日09:02左右被root终止（Exit143），未达168h/300M；本次按用户授权恢复六组。旧checkpoint仅模型与步数，无优化器/环境/RNG，**这是从权重继续，PPO/Qc优化器、episode/GRU/覆盖历史与随机数重置，不能称无缝恢复**。全部103项权重严格继承、encoder42项继续冻结；8×256/seed100/hash0/原奖励与算法保持，300M为累计步数上限。旧目录/结果及已人工停止的基线保留。

71项CPU回归和GPU短测 **1511108 Exit0／14:55** 通过，六组各4096步；加载全状态、全局步数、冻结/原配置、Qwen真概率/奖励回填、nav_rewards/masks与coverage守恒正常。短测权重不用于正式，正式均从旧中断checkpoint独立启动。新checkpoint额外保存PPO和Qc optimizer，但仍不包含模拟器/RNG状态。

| 方法 | 继承checkpoint步数 | 新PBS | 首次提交时状态（现状见上） | 正式walltime上限 |
|---|---:|---|---|---|
| A Qwen128 β0.03 | 8,192,000 | 1511143 | R | 127:34:34 |
| C 几何128 | 22,528,000 | 1511144 | R | 127:34:33 |
| Qwen128 β0.1 | 8,704,000 | 1511145 | Q | 125:30:01 |
| 旧覆盖256 | 125,952,000 | 1511146 | Q | 68:03:22 |
| 旧覆盖32 | 48,128,000 | 1511147 | Q | 99:28:14 |
| B Qwen256 β0.03 | 8,704,000 | 1511148 | Q | 127:34:32 |

全部经CFP04-SF-109/autox→batch_gpux、1A40/36CPU240GB提交，A/C优先；Q为资源等待，不重复qsub或停运行作业换队列。每组预算=原168h−旧PBS已用−1h验证保守预留；1h不是实际消费声称，实际共享短测14:55。共享项目剩余额度数值仍未知，接受请求代表当前提交许可。

四独立继续训练树/源码：覆盖256 SIGN-continue-coverage256 @5a86720；覆盖32 SIGN-continue-coverage32 @2e5efba；β.1 SIGN-continue-qwen128 @bb59545；ABC SIGN-continue-ablation @1256ca7，分别基于原6983c91/a7cc9e0/81fedec/d2352f0。四个phase2/continue-*-20261103分支已普通push到yiichu03/SIGN、远端SHA一致，运行树不pull资料。根文档为服务器维护源；11月7日生成快照已随集中资料发布f00c15c，见顶部GitHub同步入口。

正式首轮核验（2026-11-03T01:40:46+08:00）：A已到8,208,384、C已到22,552,576累计环境步，分别67/56项scalar有限，A worker实际FP32；不把重启后短滑窗当收益。证据首次正式更新（服务器：`/scratch/e1538633/liuyi/logs/training_continuation_20261103/formal_progress_first.json`）。

独立输出：各tree的`results/continuation_20261103/CASE/train`，TensorBoard在tb，continuation.json含源SHA/完整初始化哈希/累计步数/局部rollout offset。配置、实际命令与PBS回执在恢复支持目录（服务器：`/scratch/e1538633/liuyi/logs/training_continuation_20261103`），重点正式提交（服务器：`/scratch/e1538633/liuyi/logs/training_continuation_20261103/formal_submission.json`）、最新状态（服务器：`/scratch/e1538633/liuyi/logs/training_continuation_20261103/formal_jobs_final.json`）、短测源审计（服务器：`/scratch/e1538633/liuyi/logs/training_continuation_20261103/checkpoint_audit.json`）。续跑TensorBoard当前推荐独立6009，脚本logs/training_continuation_20261103/view_tensorboard.sh配合SIGN_TENSORBOARD_PORT=6009，本地16009转发命令见RUNBOOK；C已指向train_after_latest_eval，运行名标明窗口/权重；原6006/6007不变，本轮未启动网页服务。

既有Qwenβ.1的8.192M及ABC各4.608M/8.192M共7次4200val已11月2日Exit0完成；8.192M的Qwenβ.1/A/B/C SR77.62/78.98/79.17/78.60%、SPL45.16/45.69/48.00/49.52%。汇总索引（服务器：`/scratch/e1538633/liuyi/logs/training_continuation_20261103/completed_evaluations_summary.json`）。原β.1的4.608M未产生完成结果，不与完成7次混淆，本轮没有重复提交评估。WORKLOG：SIX-CONTINUATIONS-FORMALLY-SUBMITTED-20261103。

<a id="matched-training-20261103"></a>
## 原训练同步数比较（11月3日复核）

只使用10月31日中断前的原训练日志，基线取其原训练同预算区间；不混入11月3日weights continuation。每个比较组内SR/SPL日志step数组逐项相同；100万/500万步列均为原50-update完成episode滑窗点的均值，样本相互关联，不视作独立验证。

基线与覆盖32/256：共同截至 **48,377,856环境步**。近1M区间(47,377,856, 48,377,856]，近5M区间(43,377,856, 48,377,856]。

| 方法 | 近1M SR | 近1M SPL | 近5M SR | 近5M SPL |
|---|---:|---:|---:|---:|
| 冻结视觉基线 | 84.56% | 50.68% | 85.87% | 50.85% |
| 旧覆盖256 | 82.09% | 45.77% | 84.14% | 46.73% |
| 旧覆盖32 | 84.16% | 47.09% | 84.01% | 46.46% |

Qwen与覆盖版本：共同截至 **8,536,064环境步**。近1M区间(7,536,064, 8,536,064]，近5M区间(3,536,064, 8,536,064]。

| 方法 | 近1M SR | 近1M SPL | 近5M SR | 近5M SPL |
|---|---:|---:|---:|---:|
| 冻结视觉基线 | 86.28% | 47.65% | 82.94% | 45.63% |
| 旧覆盖256 | 86.35% | 47.91% | 82.84% | 45.68% |
| 旧覆盖32 | 86.08% | 47.69% | 82.14% | 45.33% |
| Qwen128 β0.1 | 86.10% | 47.67% | 83.56% | 45.54% |
| A Qwen128 β0.03 | 85.95% | 47.54% | 82.05% | 44.66% |
| B Qwen256 β0.03 | 86.58% | 48.60% | 82.81% | 45.40% |
| C 几何128 | 85.73% | 48.66% | 82.25% | 45.06% |

共同43.378–48.378M的5M：两个旧覆盖训练SR约低基线1.73/1.86pp，SPL低4.13/4.39pp，32与256接近。共同7.536–8.536M的1M：B较旧256 SR+0.23pp、SPL+0.69pp，较旧32+0.50/+0.91pp；共同3.536–8.536M的5M则不再领先旧256。β0.1的5M SR较高但SPL接近；A没有稳定优势。C最近1M也有较高SPL，不能据局部训练区间确认Qwen语义带来独有收益。此为单种子训练描述；旧/新面积分辨率和MRQ奖励目标有差异，不把全方法比较误称仅替换评分器的单变量实验。

同预算曲线PNG（服务器：`/scratch/e1538633/liuyi/logs/matched_training_20261103/snapshot_015509/matched_training.png`） · PDF（服务器：`/scratch/e1538633/liuyi/logs/matched_training_20261103/snapshot_015509/matched_training.pdf`） · 完整窗口/碰撞/导航reward/原始输入SHA（服务器：`/scratch/e1538633/liuyi/logs/matched_training_20261103/snapshot_015509/comparison.json`） · 均值CSV（服务器：`/scratch/e1538633/liuyi/logs/matched_training_20261103/snapshot_015509/matched_means.csv`）。曲线额外101-update平滑仅作展示，表格不作该平滑。WORKLOG：MATCHED-LEGACY-AND-QWEN-TRAINING-COMPARISON-20261103。

<a id="training-stop-20261031"></a>
## 10月31日管理员中断时的训练指标（11月3日复核）

下表来自原六训练最后留存的TensorBoard记录，时间2026-10-31 09:01:33–09:03:41。末点是原生50-update完成episode滑窗；近100万步列为这些滑窗点的区间均值，不是完整训练集离线评估。各方法训练预算不同，不据此直接排名；此前续跑的起始步数来自最后checkpoint，与这里的日志末步分开。

| 方法 | 日志末步 | 末点SR | 末点SPL | 近100万步SR | 近100万步SPL |
|---|---:|---:|---:|---:|---:|
| 旧覆盖256 | 126,175,232 | 81.63% | 47.13% | 84.97% | 48.34% |
| 旧覆盖32 | 48,377,856 | 85.90% | 47.85% | 84.16% | 47.09% |
| Qwen128 β0.1 | 8,810,496 | 82.43% | 47.12% | 85.58% | 47.75% |
| A Qwen128 β0.03 | 8,536,064 | 85.23% | 47.85% | 85.95% | 47.54% |
| B Qwen256 β0.03 | 9,189,376 | 79.06% | 45.91% | 85.21% | 48.54% |
| C 几何128 | 22,587,392 | 88.20% | 49.64% | 86.42% | 48.93% |

B末点SR79.06%，低于其近1M均值85.21%约6.15pp，体现短窗波动；原覆盖256末点81.63%也低于区间均值84.97%。没有发现原全历史及最终尾段scalar的NaN/Inf，不能单凭某个末点作退化或方法优劣结论。原reward仍仅导航奖励，bonus另列。

证据：完整末点/均值/碰撞/导航reward/loss/覆盖与奖励（服务器：`/scratch/e1538633/liuyi/logs/training_stop_20261031/readout_20261103T014602/report.json`），同目录各selected.csv可复算；来源为原训练文件及已发布00:53快照的精确SHA前缀，完整TFRecord边界之后的尾段无丢弃字节。所有路径都指旧训练，未混入11月3日续跑。记录时间为本次11月3日，事件时间为10月31日；WORKLOG：OCT31-INTERRUPTION-FINAL-TRAINING-METRICS-REVIEWED。

## 最新训练指标检查（2026-10-31 00:53，新加坡时间）

六个训练作业均R；本次仅CPU只读日志和已落盘权重，不评估、不改训练、不提交新作业。下表为各自最近100万环境步的原生50-update滑窗统计均值；不同末步不能直接排名，reward仍只含导航奖励。

| 方法／作业 | 最新环境步 | 训练SR | 训练SPL | 近3h中位秒／2048步 |
|---|---:|---:|---:|---:|
| 旧覆盖256／1497416 | 115,169,280 | 86.84% | 51.24% | 5.29 |
| 旧覆盖32／1502352 | 43,018,240 | 86.18% | 48.64% | 10.46 |
| Qwen128 β0.1／1507268 | 7,084,032 | 84.65% | 46.67% | 33.55 |
| A Qwen128 β0.03／1507648 | 6,844,416 | 82.52% | 45.32% | 33.13 |
| B Qwen256 β0.03／1507651 | 7,290,880 | 83.81% | 46.85% | 31.48 |
| C 几何128／1507650 | 18,020,352 | 85.25% | 49.51% | 12.20 |

共同5,844,416–6,844,416步：基线/旧覆盖256/旧覆盖32/Qwen128β0.1/A/B/C的训练SR分别82.47/84.36/82.38/83.15/82.52/82.87/80.68%，SPL46.27/46.44/45.60/46.05/45.32/46.07/45.46%；Qwenβ0.1/B略好于旧32，但未超过该窗口的旧256。改用共同最近3M窗口，Qwenβ0.1相对旧256的SR83.02/82.26%、SPL45.11/45.40%，表现随窗口变化，尚未出现稳定全面收益；1/2/3/5M复核（服务器：`/scratch/e1538633/liuyi/logs/training_readout_20261031/snapshot_005043/comparison_followup.json`）。A/B/C同口径有效动作覆盖效率0.15941/0.16081/0.16514m²/动作，C面积略高但SR较低；旧coverage为0.1m口径，新四组为0.025m且仅纳入几何有效段，不跨口径排名。共同阶段每rollout bonus A/B/C=0.13473/0.13992/0.35013；alpha仅在初始短测校准，不保证后续总奖励量继续匹配，未重新拟合alpha。

旧三方法共同38.018–43.018M的5M窗口，基线/覆盖256/覆盖32：SR86.24/85.47/84.96%，SPL51.05/47.49/47.62%，32版未稳定超过基线；这与已发布18.944M验证集成绩属于不同阶段及指标。六组全部scalar有限，各最近稳定checkpoint的42项encoder状态与公开权重逐位一致，四新组全程rollout审计nav_rewards/masks不变。近期几何有效段约92.7–93.2%，低于短测约98%，主要因episode跨楼层高度超限，另有少量距navmesh>5cm；相应bonus按原规则跳过。原作业与所有评估依赖保留。

证据：完整快照／窗口统计（服务器：`/scratch/e1538633/liuyi/logs/training_readout_20261031/snapshot_005043/readout.json`）、同预算训练曲线（服务器：`/scratch/e1538633/liuyi/logs/training_readout_20261031/snapshot_005043/matched_training.png`）、冻结权重检查（服务器：`/scratch/e1538633/liuyi/logs/training_readout_20261031/checkpoint_check.json`）、PBS状态（服务器：`/scratch/e1538633/liuyi/logs/training_readout_20261031/jobs.txt`）。各组事件末时00:51–00:53。WORKLOG：TRAINING-SIX-RUNS-READOUT-20261031。

10月31日资料已同步：yiichu03/SIGN的phase2/qwen-beta003-geometry128新提交 **333b2ae**，远端SHA一致。集中入口[六组训练对照报告](https://github.com/yiichu03/SIGN/blob/phase2/qwen-beta003-geometry128/docs/experiments/qwen128-reward/ablations/training_20261031/README.md)，含1–5M共同窗口/曲线/原始CSV及rollout审计、基线停止训练SR/SPL、只读脚本/TensorBoard运维副本和根四文档生成快照。152项资料manifest、解压SHA、56项指标复算、链接和WORKLOG前缀检查通过；运行源码仍d2352f0，其他训练分支和作业不动。推送回执push_result.json（服务器：`/scratch/e1538633/liuyi/logs/training_readout_20261031/push_result.json`）另存服务器，不为回执循环发布。WORKLOG：TRAINING-READOUT-PUBLISHED-20261031。

## A/B/C正式对照：2026-10-29提交与验收记录

独立SIGN-qwen-ablation / phase2/qwen-beta003-geometry128从33e30d2建立，运行源码 **d2352f0**。A Qwen128 beta.03、B Qwen256 beta.03、C几何128 alpha=0.2927574680399425（旧短测1176有效段冻结校准）；8×256/seed100/hash0/仅公开encoder加载冻结/其余fresh初始化，MRQ三组显式navigation目标、PPO混合奖励、旧coverage bonus0。

63项CPU回归+三组各40960步GPU短测通过。有效率A/B/C=97.85/97.80/97.98%，42项encoder状态逐位不变、原nav/mask不变、bonus守恒；C无worker/render/概率字段。A首轮52张图/统计/ID等于旧验证输入；A/C首轮55段几何统计/有效性一致；103项初始状态三组均等于原初始化。每2048动作中位40.39/35.36/27.87秒，短测不证明学习收益。

正式 **A1507648、C1507650、B1507651** 均已R（CFP04-SF-109/autox→batch_gpux，1A40/36CPU240GB/168h，300M cap）。独立输出 `SIGN-qwen-ablation/results/qwen_ablation_20261029/{A,B,C}/train`、TensorBoard其tb/；不从短测恢复。CFP/autox许可由三短测及三168h正式请求实际接受核实，Express每用户max_run4，余额查询仍需amgr登录，未取得剩余额度数字。

4.608M/8.192M准确milestone/4200val GPU依赖：A **1507653/1507655**，C **1507657/1507660**，B **1507662/1507664**；相应CPU等待A1507652/1507654、C1507656/1507659、B1507661/1507663（初查B两CPU在Q，A/C等待先运行）。全部保留旧1507270/1507272依赖，不占GPU等待。未来eval关闭Qwen/采集，原6环境/max500/seed100/hash0/4200val、0.1m被动覆盖weight0，输出SR/SPL/效率/碰撞/动作与耗时；训练另报段长和bonus分布。三正式均已有TB更新，首次核验A/B/C=4096/6144/26624步、全部scalar有限、初始化SHA等于short；C无worker。当前无新正式val成绩。支撑logs/qwen_ablation_20261029，校准/短测/配置/实际命令/提交回执齐全。已push yiichu03/SIGN同名分支，发布提交ac62298、运行源码d2352f0，远端SHA核对一致；运行目录不pull资料提交。WORKLOG：QWEN-ABC-SHORTS-PASSED-FORMALS-SUBMITTED。

## Qwen128正式训练：2026-10-29提交与验收记录

独立 `SIGN-qwen128-reward` / `phase2/qwen128-reward-beta01` 从453179c建立，运行提交 **81fedec**。54项单测、32原轨迹44窗口离在线精确重放、边界/遮挡/保存函数/评估配置及真实GPU40960步均通过（1507196 Exit0）。有效片段1176/1204=97.67%，42项encoder状态不变，loss/概率有限、真实mask/nav_rewards不变；零权重原训练scalar逐位相同，仅Qc有小于原基线复跑的1.49e-8舍入差。短测每2048步中位59.24s（原基线7.55s），显存5秒采样峰值24947MiB，不能当学习收益或全程恒定速度。

**短测1507196已完成（Qwen部分40960步）；正式1507268是另一条从全新初始化启动的长训练，已经提交并继续运行。** 2026-10-29 16:01只读快照：正式47104步/23更新，55项scalar有限、有效1399/1431=97.76%、SR3.599%/SPL2.807%（训练滑窗），中位64.26s/2048步；同阶段基线SR3.200%/SPL2.212%，尚不足判断学习收益。正式首次checkpoint在512000步，目前未到保存点属正常，4.608M/8.192M评估仍等待。证据logs/qwen128_reward_20261029/progress_20261029T160130；本轮未新qsub或改训练源码。

正式 **1507268.stdct-mgmt-02** 已R、初始化SHA与短测相同（fresh init）：个人auto/1A40/36CPU240GB/168h，300M cap、8×256、seed100/hash0、只加载冻结公开visual_encoder、其他原初始化，**128步/真实终止切段，beta0.1原始q，几何bonus0**，从全新初始化开始。输出 `SIGN-qwen128-reward/results/qwen128_reward_20261029/train_personal_8env`，TensorBoard为其 `tb/`；独立6007查看脚本 `logs/qwen128_reward_20261029/view_tensorboard.sh`，原6006服务不动。

四个Qwen wait/H作业共同服务于同一Qwen训练的两次未来导航验证：1507269=4.608M CPU等待、1507271=8.192M CPU等待（R，无GPU），1507270/1507272=各4200导航val（H，等待CPU校验；评估时Qwen关闭）。正式训练本体仅1507268。

4.608M／8.192M各保存不可变milestone checkpoint并安排原协议4200val：CPU等待1507269／1507271；GPU评估 **1507270／1507272**，当前H依赖等待，待对应权重SHA校验后自动释放，不占等待GPU。使用原SIGN-coverage-eval/6环境/max500/seed100/hash0，Qwen及其轨迹采集关闭，额外0.1m被动覆盖口径与既有三方法评估相同。已核实两评估均经CFP/autox路由到batch_gpux，当前H为afterok依赖；没有处于Q且需要换到gpux的GPU任务。用户偏好后续许可范围内资源排队的GPU任务优先gpux。当前无新评估成绩。回执/配置/短测结论：`logs/qwen128_reward_20261029/`。 已push yiichu03/SIGN同名分支：发布提交33e30d2（含47104步进展）、运行源码81fedec，远端SHA核对一致；运行目录保持81fedec，不pull资料提交。WORKLOG：QWEN128-GPU-SHORT-PASSED-FORMAL-AND-EVALS-SUBMITTED。

## 当前目标与分支布局

用户已授权将第一阶段工作归档到两个 yiichu03 仓库的同名 phase1 分支，并让 SIGN 从 origin/main 开始第二阶段。归档、推送和切换已完成；已在独立worktree加入固定rollout覆盖奖励；Gibson 原版短训练和8环境测速已完成，原个人长训练1495073已停止归档，冻结编码器基线1496716已按用户新授权停止并保留权重/日志，两组覆盖训练继续；Qwen单图概率和离线历史对照已完成；新Qwen128正式奖励训练已提交，见上方当前授权任务。

32步覆盖结算实验（已实施）：32步覆盖结算对照已实施并提交。独立SIGN-frozen-coverage-settle32／phase2/frozen-coverage-settle32 @ a7cc9e0已push yiichu03/SIGN，工作树干净。默认interval0兼容旧方案，正式CLI32；8×256、weight0.1、seed100/hash0、冻结初始化、原300M/168h预算和评估均继承。8新测试+9原回归、10组精确兼容及配置审计通过；GPU短跑1502328 Exit0，两组各40960步，42项encoder状态不变，奖励守恒，稳定吞吐343.94/345.64步每秒。正式个人作业1502352已提交（初查Q，node_pool不足），输出results/gibson_coverage_settle32_20261028/train_personal_8env，TensorBoard开启；原1496716/1497416均继续R。短跑不代表学习收益。证据logs/gibson_coverage_settle32_20261028；WORKLOG：COVERAGE-SETTLE32-GPU-PASSED-TRAIN-SUBMITTED-PUSHED。

奖励机制讨论（2026-10-28）：当前coverage自身新增面积/环境步由前5M的0.1403m²升至最近5M的0.1689m²，但基线无覆盖日志，不能归因于该奖励或声称冗余搜索减少。实际末步bonus=w*gain/256，GAE gamma0.99/tau0.95使较早动作的当轮直接反馈衰减。候选为单独weight0.5试验，或保持weight0.1、rollout256而增加32步子片段末结算；后者属于对原结算边界的新提议。其中32步方案随后获用户批准，实施状态见当前任务；weight0.5未实施。证据reward_design_analysis.json；WORKLOG：COVERAGE-REWARD-MECHANISM-AND-NEXT-TRIALS-PROPOSAL。

步数澄清（2026-10-28）：当前8环境各采256步（共2048 transition）后统一加bonus、算returns、执行一轮PPO；训练episode上限1000步，覆盖历史跨rollout延续。32步候选仅增加奖励写入子片段末步的位置，仍采完整256步后处理；不是32步更新一次，也不重置覆盖/真实mask。延长H到512还会使现公式每平方米奖励减半，需单独控制。用户随后批准32步方案，实施状态见当前任务。WORKLOG：COVERAGE-ROLLOUT-VS-SETTLEMENT-EXPLANATION。

历史开发资料（2026-10-28，后续评分方向已改为单图独立，见当前Qwen条目）：已按用户选择导出static五组HM3D开发资料（group01/05/06/08/10，各8条同任务）；两套window256/相同长度前缀，共90PNG、80行覆盖统计，含覆盖总比例/扣初始的新增比例/新增面积每步。目录logs/qwen_static_dev5_20261028，打包qwen_static_dev5.zip。894字评分prompt初稿以28对比较换算0–1分，允许并列/未知；未调用Qwen或生成真值，历史开发数据不作独立测试集。等待审核；WORKLOG：QWEN-STATIC-FIVE-GROUP-DEVSET-EXPORTED。

### Habitat-GS 当前进度（2026-10-28）

- **成功／失败示例视频已完成**：1503625 Exit0／6分47秒，按同一公开权重与确定性500步协议新录制16条候选，选3成功（scene59、scene64、interior_0651）＋3失败（scene56／57／58），6个H.264 MP4及manifest共12.30MB，1811帧完整解码与标签／SHA检查通过，已实际查看成功末帧与失败中途画面。目录 `SIGN-habitat-gs/results/habitat_gs_videos_20261028/`；不是原1900条录像，且这16条未观测非有限距离，不能替全评估排除异常。支持脚本／验证 `logs/habitat_gs_videos_20261028/`；本地rsync命令见RUNBOOK。WORKLOG：HABITAT-GS-VIDEOS-COMPLETE。

- **Habitat-GS最新代码与进展已推送GitHub**：origin/experiment/habitat-gs-imagenav @ d1f5aa52df7de9004014cc3e91cef6ac1c84c1be，远端SHA核对一致。接入代码95eef9b及docs/experiments/habitat-gs-imagenav资料含数据就绪、pilot结果、进行中的完整val快照和四根文档生成副本。GitHub为发布时进行中快照；当前1502487结束及异常见下；运行目录保持95eef9b且干净，远端多1个资料提交，已跟踪origin同名分支但不pull。临时发布工作树已移除，推送回执logs/habitat_gs_publication_20261028/push_result.json。WORKLOG：HABITAT-GS-PUBLISHED。

- **公开原版SIGN完整val已跑完，但汇总质量检查失败**：1502487于2026-10-28 19:23结束，1900/1900，PBS Exit_status=1、用时4:55:21。TensorBoard原始主指标 **SR16.6842%（317/1900），SPL8.4819%**；reward=NaN、distance_to_goal／distance_to_view=+Inf，evaluate.py有限性断言拒绝生成result.json。原生评估循环已完成，异常在末尾质量检查；主指标暂作原始观察，附加异常的影响条数／场景与根因未知。审计logs/habitat_gs_eval_20261028/result_audit.json，原日志／TB／配置保留；未改源码、未重提任务。WORKLOG：HABITAT-GS-FULL-EVAL-FINISHED-WITH-NONFINITE。

- **完整静态ImageNav数据已下载并校验完成**：auto CPU作业1502380.stdct-mgmt-02，Exit_status=0，用时19分48秒。393文件／26695345591字节（26.70GB），复用6文件、下载387文件；训练110场景／110000条，验证19场景／1900条。全部官方哈希、任务引用与ID检查通过，129个场景配置navmesh引用全部可解析，无part／额外文件。完整清单 `manifests/habitat_gs_imagenav_20261028.json`，日志及提交／完成记录 `logs/habitat_gs_20261028/`；下载器d291c44。WORKLOG：HABITAT-GS-FULL-DOWNLOAD-COMPLETE。

- 官方ImageNav库存核对（2026-10-28）：110个训练场景／110000条train，19个验证场景／1900条val，共129场景／111900条；官方ImageNav目录只有train和val，没有单独test划分。本地场景与原始任务已全部下载，实际读取核对111900条；历史评估仅scene56的10条。来源为官方HF数据卡与固定revision目录API，见WORKLOG的HABITAT-GS-IMAGENAV-INVENTORY。
- 存储：固定HF全库97.51GB中，本轮仅下载静态ImageNav所需26.70GB；GS目录du -sh显示21G（NFS块／逻辑文件口径不同）。最新可读配额快照仍为下载前13:30的57.58G／500G，不能把旧读数当作下载后的实时用量；容量充足。详见WORKLOG的HABITAT-GS-STORAGE-CAPACITY与HABITAT-GS-FULL-DOWNLOAD-COMPLETE。

- 已从 origin/main @ dad87fe 建立 `experiment/habitat-gs-imagenav`，在独立 `SIGN-habitat-gs/` 工作树开发；原 SIGN phase2 保持原路径和源码。
- 第三方 Habitat-GS 固定为 cb01b2fdf850ce3cab28ad00461a68ac7719f23f，所需子模块已就绪。官方数据固定 HF revision ea6453855938dd3d4395c4c449fedefb7e6603b7；首批scene56的6个文件共111428166字节，包含100条原始 val ImageNav，官方哈希全部通过。唯一资产目录 `SIGN/data/scene_datasets/gs_scenes`，新工作树以软链接复用；首批历史清单 `manifests/habitat_gs_20261026.json`，全量清单见上。
- CPU 已验证100条导航路径均可达、最大测地距离误差约3.8e-6米；新配置／dataset适配器和现有导航／安全权重通过加载。旧导航 checkpoint 中历史 LPIPS／旧 Qc 键按原 trainer 规则忽略，独立 safety 权重严格加载；证据 `logs/habitat_gs_20261026/cpu_baseline_probe.json` 明确标记这是旧Sim0.2.2的CPU检查。
- 独立 `envs/sign-habitat-gs` 的Python3.10.22／torch2.5.1+cu121／NumPy2.0.2等库已在禁用user site的条件下导入通过，pip check无依赖错误。构建工具为CMake3.31.6／Ninja1.11.1.4；旧环境和habitat-lab源码未改。
- Habitat-GS原生编译／安装和新版Sim0.3.3 CPU检查已通过：100条路径均可达，测地距离误差0.0。GPU1494739的相机向量类型问题已在实验分支修复；保留全部失败日志。后续 **1494770.stdct-mgmt-02 已成功完成（Exit_status=0，A40，总作业3分29秒）**，实际GS渲染、目标图一致性／姿态保持、策略前向、连续动作均通过。
- scene56的10条小样本评估：**SR 10%（1/10），SPL 5.3543%，view_match 10%**，平均最终距离14.9221米，平均碰撞46.9次。运行链路打通，但现有权重迁移表现较弱；不据此归因或声称完整基准结果。结果与TensorBoard、最终合并配置、探针JSON／预览图集中在 `SIGN-habitat-gs/results/habitat_gs_20261026/job_1494770/`；机器可读汇总result.json，PBS日志logs/habitat_gs_20261026/smoke_03.pbs.log。原trainer未保存逐条轨迹／指标，无法据此分析每条失败原因。
- 初次采用SIGN的128×128输入、连续动作、500步、原成功／view_match定义，固定PYTHONHASHSEED=0；不是官方256×256／离散动作／1000步DDPPO基准。先完成单场景闭环，再决定扩大评估，不预先提交大规模训练。具体方案、失败与修正见WORKLOG的HABITAT-GS-*条目，最新为HABITAT-GS-FULL-DOWNLOAD-COMPLETE。


### Gibson 当前进度

- 2026-10-29 16:22预算估计（只读console）：256版72151040步，近3h352.50步/s，跑到300M尚需179.55h/7.48天；32版20746240步、186.88步/s，固定当前速度需415.08h/17.29天。32在50M后原代码停止MRQ辅助更新，RandomShift仍启用；若之后速度达到当前256水平，分段估计240.49h/约10.02天，此为条件假设、未在32实测。现有PBS分别只剩109.71h/141.14h，均不足跑满300M，未改作业预算或启动续训。证据logs/gibson_training_budget_20261029/estimate.json；WORKLOG：GIBSON-300M-REMAINING-TIME-ESTIMATE。

- 最新三方法同预算完整val已结束：1506785.stdct-mgmt-02于2026-10-29 15:29:34完成，PBS F/Exit0/1:35:43。共同ckpt.36=18944000步、各4200条/14场景；baseline/coverage256/coverage32的SR78.3095/79.0952/82.0238%，SPL51.6374/51.9819/51.7534%，成功3289/3322/3445。总新增面积/总动作数0.0759192/0.0766120/0.0827161m²/动作；平均动作144.4576/145.9731/137.9917，碰撞44.3381/42.7290/50.4871。32版较基线SR+3.7143pp（多156成功），全局覆盖效率+8.9529%，SPL+0.1160pp基本相近但碰撞+6.149/episode；256版SR+0.7857pp、SPL+0.3445pp、效率+0.9126%。保持单种子/单阶段与几何代理限制，不据此声称整体减少碰撞或所有阶段占优。逐条完整/唯一任务集、共同起点/目标、原生TB汇总及无reward改变control均已通过；本轮再次核验每组4200/唯一和SR/global ratio重算一致。结果logs/gibson_threeway_coverage_eval_20261029/full_comparison.json，旧4.608M/8.192M与原训练不动。WORKLOG：GIBSON-18944K-FULL-VAL-RESULTS-REVIEWED。

- 两覆盖训练最新检查（2026-10-29 13:30快照）：1497416与1502352均R，256版68528128步／32版18835456步，全部34项scalar无非有限，bonus守恒最大误差1.79e-8。各自最近1M SR87.34%／85.46%、SPL49.50%／47.98%，步数不同不能直接排名。共同16.835–18.835M的最近2M，SR86.412%／86.233%，SPL48.349%／49.299%，新m²/动作0.167181／0.170575（32版+2.03%）；32有小幅SPL/覆盖效率现象，SR不稳定领先。256版最近5M SR86.948%／SPL49.679%，仍落后同阶段已停止基线89.279%／54.778%，趋平台。只读原日志/事件快照，不评估/改训/提交新任务。证据logs/gibson_two_coverage_training_20261029/snapshot_132741/readout.json；原始CSV/图在logs/gibson_train_threeway_20261028/snapshot_132900。WORKLOG：COVERAGE-TWO-TRAINING-20261029-READOUT。

- TensorBoard用户连接已核验（2026-10-29）：13:26:55新PID1088282，正确三组logdir_spec/6006，初读全部历史时API一度baseline19.8M、coverage25616.3M，后持续增加；13:33:54已追上baseline74.654M（已停故无后续）、coverage25668.610M／32版18.870M（事件13:33）。用户原SSH命令正确、URL应为127.0.0.1:16006；保持连接刷新页面并选两个coverage即可，不反复重启。首读实测约7分钟，非训练停更；未杀进程/改脚本或训练。证据同readout目录tensorboard_http_readout与progress_second/third.json。WORKLOG：TENSORBOARD-INITIAL-LOAD-CAUGHT-UP。

- 当前Qwen黄红同宽实线版已完成并发布：yiichu03/SIGN的phase2/qwen-history-window @453179c，远端一致/工作树干净，运行代码30ed53d。1506387 Exit0/2分36秒，黄红同为1.5pt实线、prompt只微调线型/重合说明；同32原轨迹/64请求→44片段/100有效分（32严格复用＋68新），31测试、像素/面积/CRC/SHA及实际离线浏览/默认盲态开关全通过。ZIP logs/qwen_history_solid_20261029/qwen2b_history_review.zip，6901870 bytes，SHA 17179a590ac4648072dc021d82b9473ee230cb57d753a3dd34c1c8c7068c83d6；源码/图片/概率/实际metadata/报告/人审表/prompt差异/根四文档生成快照在docs/experiments/qwen-history-solid。此前虚线版保留，样本/统计未变，不把输入敏感性当准确率或训练收益。回执同目录push_result.json；WORKLOG：QWEN-HISTORY-SOLID-PUBLISHED。

- 此前虚线版Qwen2B历史窗口代码/资料已发布：yiichu03/SIGN的phase2/qwen-history-window @006c8f1，远端SHA一致、工作树干净，运行时代码0bb9a90保持。最终1505092 Exit0/2分51秒，32源轨迹/64请求→44片段/100评分（32严格复用＋68新），完整128步12段有历史、完整256步5段无历史、短段27单列；31单测、像素/面积/哈希及真实Chromium离线浏览100图/隐藏开关/筛选/空白人审全部通过。完整报告/原始审计/PNG/CSV/JSON/prompt差异/根四文档生成快照在docs/experiments/qwen-history-window；首跑与QA改动原文保留，不以q均值判优，不作人审真值或256历史/训练收益结论。ZIP：logs/qwen_history_window_20261029_revision2/qwen2b_history_review.zip（6902967 bytes），SHA b667f514c41b1940bc2342d9a7df64772fe41bd32a61ecd12f526ff33cf3d734；回执同目录push_result.json。原1504280自然完成，未新增导航训练或9B。下一步用户盲审。WORKLOG：QWEN-HISTORY-RESULTS-PUBLISHED。

- 8.192M已完成前两组的独立对比（2026-10-29 02:03）：同4200val任务/起点/目标图，baseline／coverage256的SR78.50%（3297）／79.2143%（3327），净多成功30条（配对新增387、丢357）；SPL48.9611%／46.9973%（-1.9638pp）。全局新增面积/动作0.0771321／0.0777178（+0.7593%），episode比值均值0.1910168／0.1866146（-2.3046%），碰撞49.8367／57.3905（+15.1571%），平均动作147.0995／146.4962。成功率小升但SPL/逐任务覆盖效率下降，没有整体一致收益；第三组未完成，不混入正式三组结论。证据logs/gibson_threeway_coverage_eval_latest_20261028/completed_two_method_comparison.json；WORKLOG：GIBSON-8192K-BASELINE-VS-COVERAGE256-READOUT。

- 8.192M三组评估已自然完成：1504280 F/Exit0、02:50:52总用时，三组各4200同任务，full_comparison.json完整质量检查通过。基线／coverage256／coverage32的SR78.50%／79.2143%／77.4524%，SPL48.9611%／46.9973%／50.4325%，全局新增面积/动作0.0771321／0.0777178／0.0794908。32版SR仍低、SPL及覆盖效率较高，单种子阶段结果不证明冗余减少；最新完整结果在logs/gibson_threeway_coverage_eval_latest_20261028。现已让该作业自行结束，没有停止或新启动导航训练。WORKLOG：GIBSON-8192K-FULL-COMPLETE-DURING-QWEN-HISTORY。

- Qwen代码与图片/评分资料已发布：yiichu03/SIGN的phase2/qwen-topdown-judge @b1c24dc，远端SHA一致、工作树干净，运行时代码保持4cc7257。docs/experiments/qwen-topdown含32张不同topdown＋4张overview、48次ABC概率评分、9B/2B同图与2B跨场景图文表、CSV/JSON/prompt/原logits、测速/验证/失败审计、根四文档生成快照（截止2026-10-28T23:11:07+08:00），376文件约6.3MB。用户整体正面反馈，下一步等待用户决定；未新增推理或训练。回执logs/qwen_publication_20261028/push_result.json；WORKLOG：QWEN-RESULTS-PUBLISHED。

- 新增2B跨场景评分已完成：1503973 F/Exit0/4分18秒，8个新Gibson场景×2不同任务，共16轨迹/16有效分数，实际44–256动作。同公开SIGN随机策略、同prompt/FP32/ABC-T1；batch/solo差2.23e-5、排列/forward-generation差0。q约0.3962–0.8260，仅待用户人工审核，不代表评分准确性验证。下载包logs/qwen_gibson_diverse_20261028/qwen2b_gibson_diverse_review.zip（761472字节），含16图/CSV/JSON/index/审计；源代码保护通过。WORKLOG：QWEN-2B-GIBSON-DIVERSE-SCENES-COMPLETE-PACKAGED。

- 楼层任务库存审计：train645000条中297000条位于多层场景（46.05%），起终点|ΔY|>1.5m候选16584条（2.57%）；val4200条中1500条位于多层场景（35.71%），跨高度候选76条（1.81%）。原任务无楼层标签，此为端点高度筛查，不代表精确跨楼层数量或途中楼层变化。只读统计与逐场景结果logs/gibson_floor_audit_20261028/result.json；WORKLOG：GIBSON-TRAIN-VAL-FLOOR-TASK-COUNTS。

- 2B同协议补跑1503819已完成：F/Exit0，20:49:41结束，用时57秒；16/16有效、FP32。相同prompt/16图SHA/动作数/面积/效率与9B逐项核对一致。batch/solo概率差1.42e-5<1e-4，排列与forward/首步generation差0；结果logs/qwen_token_probabilities_20261028/run_2b_1503819/scores.csv/json；同9B格式的Denmark8图下载包qwen2b_denmark_review.zip已生成。WORKLOG：QWEN-2B-ABC-SCORING-COMPLETE／QWEN-2B-DENMARK-REVIEW-PACKAGED。

- SIGN冻结视觉基线1496716已按用户新授权停止，为Qwen腾资源：2026-10-28 20:28:36 F/Exit143，运行44:48:17。最后终端74649600步，最后已保存模型74240000步（SHA核对/状态有限），额外备份logs/qwen_token_probabilities_20261028/baseline_stop_1496716；原checkpoint/TB/日志全保留。原实现缺优化器级断点，不自动重启。两覆盖训练继续；Qwen1503691已在释放的GN-A40-045/0运行。WORKLOG：BASELINE-1496716-STOPPED-TO-FREE-QWEN-GPU。

对学长汇报建议（2026-10-28，按完整三组val更新）：三组定位为可控消融，4.608M同阶段4200val已完成；32步结算版有观测效率改善（全局+7.40%、episode平均+2.95%）与SPL小升，但SR低1.00pp，不能称成功率提升或冗余搜索已减少。9.216M两组结果与19:01训练快照仍是各自历史证据，勿与4.608M三组混表。WORKLOG：GIBSON-THREEWAY-FULL-EVAL-COMPLETE-READOUT。

- 当前Qwen任务已完成：9B单图A/B/C真实logits评分4cc7257已push yiichu03/SIGN同名分支，25测试通过。FP32 GPU1503691 Exit0/1分03秒，16/16评分有效；A/B/C=32/33/34，左padding及回答位置通过，batch/solo最大概率差1.74e-5<1e-4、排列差0、forward/首步generation raw logits差0。T1候选softmax，q=0.5*p_medium+p_high，独立不排名。首次BF16差0.02936的失败现场保留，旧JSON/benchmark默认auto不变。结果logs/qwen_token_probabilities_20261028/run_1503691/scores.csv/json，prompt版本cdd6f2fc782f；动作数/平方米已对0.025m显示mask和轨迹核对（非训练0.1m口径）。未改PPO/trainer/采样/coverage；WORKLOG：QWEN-ABC-16-IMAGE-PROBABILITIES-COMPLETE-PUSHED。

- 当前Qwen方向：单图独立0–1评分，8环境8个独立会话batch并行，无同任务分组要求。接口/测速4754fed已push yiichu03/SIGN同名分支（远端SHA一致、工作树干净），16测试通过。1503515四模型A40同节点测速Exit0/3分21秒：9B/4B/2B/0.8B常驻单张0.529/0.533/0.402/0.458s，独立batch8整批1.682/1.593/0.869/0.896s，峰值18.93/9.82/4.79/2.23GiB。严格JSON通过52/52、35/52、52/52、0/52（重复测速，非质量评估）。当前原coverage6.58s/轮，加9B约8.26s或2B7.45s，仅加法估计、未计在线绘图/IPC/争用。建议先验证2B裁判质量，9B作参照；未接PPO。证据logs/qwen_single_latency_20261028；WORKLOG：QWEN-SINGLE-IMAGE-FOUR-MODEL-LATENCY-COMPLETE。

- 三组同阶段覆盖评估已完成并逐条复核：1503479 F/Exit0，2026-10-28 22:22:35结束／2:59:09，三组均4608000训练步、相同4200 Gibson val任务/目标图/起点，native确定性6环境/500步/seed100/hash0。基线／coverage256／coverage32：SR76.3571%／76.0000%／75.3571%，SPL45.8822%／46.3332%／46.3769%；平均动作155.549／154.777／147.583，平均新增面积11.2369／11.2281／11.4500m²。全局总新面积/总动作0.072240／0.072543／0.077583m²，episode比值均值0.180435／0.181156／0.185765m²。32版相对基线全局效率+7.40%、episode平均效率+2.95%、平均步数-5.12%、SPL+0.495pp，但SR-1.00pp；256版整体接近基线。只支持此单种子/早期检查点的观测效率差异，不证明减少冗余或稳定导航收益。证据logs/gibson_threeway_coverage_eval_20261028/full_comparison.json及results_readout_audit.json，原始0.1m/3m/90°统计扣初始视野，非Qwen图2.5cm口径。WORKLOG：GIBSON-THREEWAY-FULL-EVAL-COMPLETE-READOUT。

- 历史八图同会话接口（当前已改为单图独立，见上）：已在独立SIGN-qwen-topdown-judge／phase2/qwen-topdown-judge @ 53a98b8已push并跟踪origin同名分支（yiichu03/SIGN），远端SHA一致、工作树干净；默认关闭，仅离线8图同请求，prompt外置、SHA冻结输入、严格JSON/0–1/null校验。11项测试通过。GPU1502697八图2692token/9.79s生成/18.41GiB跑通，但回答带Markdown围栏，严格校验invalid_response；第二次1502725已产出valid JSON（8图/2713输入token/8.28s生成/18.41GiB），8编号与图例检查通过；只验证输入与结构。未接PPO或修改采样；当前不能声称评分协议/训练收益已验证。证据logs/qwen_topdown_engineering_20261028；WORKLOG：QWEN-TOPDOWN-ENGINEERING-LOCAL-COMMITTED。

- Gibson静态topdown已完成：1502516（CFP/autox→batch_gpux）Exit0/1分32秒，Edgemere和Denmark各8条同任务公开权重随机轨迹，共18静态PNG；实际31–39与36–225步，非等预算排名。logs/gibson_topdown_pilot_20261028/gibson_topdown_pilot.zip；导图0.025m栅格、视野边界校正≤5cm，原始0.1m统计保留，训练未改。WORKLOG：GIBSON-TOPDOWN-PILOT-EXPORTED。

- 最新三组训练指标检查（2026-10-28T19:01–19:02+08:00）：1496716/1497416/1502352均R，基线71964672步、原coverage45021184步、settle32为4536320步，全部scalar有限。按共同3536320–4536320步平均，SR80.59%/82.44%/79.54%，SPL43.73%/44.23%/44.06%；32版SR略低、SPL略高，最近50万步回升但未形成稳定收益。同阶段新增覆盖m²/步原版0.1450、32版0.1444，基本相同。较长共同40021184–45021184步，基线/原coverage SR85.76%/84.28%（-1.48pp）、SPL50.30%/46.69%（-3.62pp），连续30–35M/35–40M/40–45M均落后。仅训练滑动指标、单种子，reward不含bonus；未评估或改作业。证据logs/gibson_train_threeway_20261028/snapshot_190105；WORKLOG：GIBSON-THREEWAY-TRAINING-METRICS-CHECK。

- 覆盖奖励收益检查（2026-10-27T14:31:40+08:00）：覆盖奖励收益检查已完成：各9216000步checkpoint、各4200条Gibson val，SR基线78.36%（3291条）／coverage77.48%（3254条），差-0.88pp；SPL51.98%／50.10%，差-1.88pp。最新训练快照至共同10438656步，最近100万步SR86.17%／84.75%，差-1.42pp（先前共同9488384步时约+0.78pp，未持续）。当前weight0.1没有显示收益；单种子／单checkpoint对不证明该奖励长期必然有害。两长训练1496716／1497416均继续，未改分支／代码／参数／权重。详见WORKLOG的COVERAGE-BENEFIT-FULL-VAL-NO-GAIN与logs/gibson_coverage_comparison_20261027/full_val_comparison.json。

- 覆盖奖励目标已完成（2026-10-27T06:07:03+08:00）：新分支phase2/frozen-rollout-coverage @ 6983c91已推送yiichu03/SIGN，只有指定三文件变更。9项单测通过；短跑1497409 Exit0／10分40秒，baseline／weight0／weight0.1各40960步均有限、encoder42状态项不变。零权重导航reward/SR/SPL/value_loss逐点相同；稳定吞吐277.19／212.72／196.87步/秒，零权重统计对照额外耗时约30.3%。正权重累计面积2109.42m²、bonus0.823992符合0.1*面积/256。Adrian四向RGB+地图／实际墙遮挡检查通过，单次metric中位0.304ms、p95为0.336ms；这不是总体开销。正式个人任务1497416已提交auto→batch_gpu、A40／36CPU240GB／168h，当前R，与原冻结实验同8×256／seed100/hash0／300M上限／评估协议，独立输出train_personal_8env。原1496716仍R、SIGN原44文件SHA不变；未停止或修改原训练。详见logs/gibson_rollout_coverage_20261027/training_submission.json与short_summary.json。

- 新覆盖探索实验（2026-10-27T05:45:48+08:00）：独立worktree SIGN-frozen-rollout-coverage／phase2/frozen-rollout-coverage，基于dac8609，当前本地6983c91，仅修改metric.py、trainer.py、新增rollout_coverage.yaml三项。Measure初始视野只建基线、episode内XZ并集不跨rollout重置，末步按0.1*片段新增面积/H写入buffer后再算returns；不改真实mask、不等各环境同步结束。RGB/覆盖FOV均90°、mpp0.1m、半径3m。独立learner/coverage_*记录bonus，原reward仅导航奖励。9项CPU边界测试通过；个人GPU短跑1497400已提交，地图／朝向／遮挡／统计开销及冻结验证待实际运行。原SIGN44文件哈希与分支保持、1496716继续。证据logs/gibson_rollout_coverage_20261027。

- GitHub同步（2026-10-27T04:37:22+08:00）：按用户要求，将最新代码dac8609ee1dc3e71ad317998a2f5086a1935e84b普通push到yiichu03/SIGN的phase2/frozen-visual-encoder，远端SHA与本地一致，已建立origin同名跟踪并显式设置pushRemote=origin。当前工作树干净；代码与训练运行设置未因发布而改变。

- 最新核验（2026-10-26T23:44:37+08:00）：1496716为R，personal-e1538633、GN-A40-045，23:40:17启动；4096步／2次GPU更新已通过，encoder42个状态项与公开权重逐位一致、权重及29条指标有限、visual_fc不是公开投影。随后独立正式目录从头启动，真实TensorBoard已确认45056步／29条scalar，冻结flag和8×256／300M上限在实际配置中吻合。GPU记录gpu_smoke_validation.json，长训练事件first_long_training_events.json，均在logs/gibson_frozen_encoder_20261026。当前账号仅这一个运行任务。

- 冻结视觉新任务1496716.stdct-mgmt-02已提交（2026-10-26T23:41:14+08:00）：personal-e1538633／auto→batch_gpu，1×A40／36CPU／240GB／168h，已运行并通过GPU校验。SIGN分支phase2/frozen-visual-encoder，提交dac8609（仅trainer.py增加已审14行），已于2026-10-27推送至yiichu03/SIGN的origin同名分支。原生CPU验证通过：同seed非encoder初始化零差异，encoder42项严格匹配公开权重且不进优化器；一次原生PPO／MRQ／RandomShift／Qc更新后encoder参数和buffer不变、visual_fc及其他目标模块仍更新。作业顺序为4096步GPU验证→成功后全新8×256长训练，原300M上限／奖励／其他初始化保留；GPU已通过，正式长训练已开始。新日志logs/gibson_frozen_encoder_20261026/，正式输出SIGN/results/gibson_frozen_encoder_20261026/train_personal_8env，TensorBoard查看脚本已更新到新目录。

- 已批准实施（2026-10-26T23:35:53+08:00）：1495073于23:30:42停止（Exit143、运行7:07:24），TensorBoard实际5785600步，保留ckpts/final.pth为5632000步，已验证有限和SHA一致，删除12个中间／重复权重。原日志、配置、TensorBoard、CSV和曲线保留，汇总logs/gibson_reproduction_20261026/stopped_scratch_run/result.json。SIGN已建立phase2/frozen-visual-encoder并按待审patch只修改src/trainer.py14行；初始化、原生PPO及GPU校验现均已通过，新训练1496716运行中。

- 已审核并实施的原方案（2026-10-26T22:39:53+08:00）：用户选择仅冻结visual_encoder，取代上一轮CNN＋visual_fc一并冻结的建议。只拟修改src/trainer.py两处：当前95行在模型构造后、优化器前，用既有ddppo.pretrained_encoder／pretrained_weights严格载入encoder子集并按train_encoder冻结；当前452行agent.train()后保持冻结encoder.eval。新实验CLI为pretrained_encoder=True、pretrained_weights=ckpt/nav_model.pth、train_encoder=False；visual_fc保持随机初始化和可训练，PPO／MRQ／RandomShift等原逻辑保留。完整待审diff为 logs/gibson_reproduction_20261026/frozen_encoder_review/encoder_only_proposed.patch，已通过不落地AST语法检查和git apply --check，SIGN源码仍干净。用户随后批准，现已完成停1495073及中间权重清理，新任务状态见上。

- 视觉冻结方案审查（2026-10-26 22:07）：git ls-remote与GitHub连接器核对学长Zichen-Yan/SIGN默认main仍为dad87fe（2026-10-14 update readme），本地HEAD相同、44个跟踪文件干净且基线哈希一致。当前自定义trainer未实现Habitat通用pretrained_encoder／train_encoder开关；仅改flag不生效。隔离CPU模型严格加载公开nav_model.pth的视觉42项＋投影2项成功；冻结CNN＋投影并固定eval后，一次合成后端更新视觉状态不变、GRU／Actor／Critic可更新。只冻结梯度时RunningMeanAndVar统计仍可变，需防agent.train重置模式。建议下一轮使用预训练冻结视觉作为独立迁移实验；当前1495073按用户明确选择继续，未执行qdel或改源码。证据 logs/gibson_reproduction_20261026/frozen_encoder_review/。

- 编码器更新审计（2026-10-26 21:53）：当前fast_resnet9视觉编码器未冻结、从零联合训练；实际配置train_encoder=True，原优化器纳入可求导参数。比较个人训练512000与4096000步checkpoint，视觉编码器39/39组weight／bias改变，GRU／actor／普通critic／MRQ在线头／Qc也改变。MRQ目标头使用EMA；cost_critic无对应优化loss，2组参数未改变。只读CPU审计证据 logs/gibson_reproduction_20261026/parameter_update_audit.json，未调整运行中训练。

- TensorBoard访问状态（2026-10-30T03:11:46+08:00）：原PID1958700已退出，6006无服务，用户ssh -N仅留下本地16006监听，因此channel报远端Connection refused。已修view_personal_tensorboard.sh及新增相邻.py为自动启动／核验复用＋信号清理；独立16016端口四项真实集成检查通过，测试进程已关闭。用户应Ctrl+C当前-N后用RUNBOOK统一ssh -t命令。未操作用户现有SSH或训练。WORKLOG：TENSORBOARD-START-OR-REUSE-LIFECYCLE-20261030。

- 用户已明确要求使用个人额度提交8环境正式长训练。新脚本scratch_train_personal_8env.pbs使用personal-e1538633／auto、1×A40、168h、8×256、原300M上限，checkpoint每250更新（512000步）、TensorBoard每次更新记录；不调用此前“必须300M在7天内完成”的外部拦截。qsub已成功返回1495073.stdct-mgmt-02（Exit0）；qstat已确认R，个人项目personal-e1538633、auto→batch_gpu、GN-A40-019、1×A40／36CPU／240GB／168h，16:23:15开始，勿重复提交。状态文件 logs/gibson_reproduction_20261026/personal_training_submission.json。TensorBoard网页已通过HTTP200验证，探针已关闭；正式浏览入口使用view_personal_tensorboard.sh。实际事件已验证29条scalar、至少10240步（2026-10-26 16:25核查），正在发生PPO更新；事件证据personal_training_first_events.json。

- 用户已确定后续采用8环境×256步，取消继续测试12／16环境的想法；12／16测试未创建或提交。当前仅按本次授权推进个人额度8环境正式训练。

- 训练提速对照1494908已成功完成（CFP／autox，GN-A40-045，A40，作业8分36秒）。同节点4×512首次298.91步/秒、8×256为335.48步/秒、4×512复跑295.03步/秒；各40960步／20次更新、相同每批2048步，TensorBoard／40960末步checkpoint均数值正常。8环境加速12.2%–13.7%，峰值显存16.18GiB（4环境11.73GiB），建议后续预算内训练用8×256。新节点4环境自身已明显快于旧GN-A40-096的155.68步/秒，不能把新旧差距全归于8环境；原因尚未单独隔离。当前8环境早期速度外推300M约248.40h，非全程确定耗时。结果和对比图见 logs/gibson_reproduction_20261026/train_parallel_benchmark/summary.json、comparison.png；本轮无待运行测速作业。

- 已从现有 FGPrompt 压缩包解压 train 645000 条／72 场景、val 4200 条／14 场景，放入 SIGN/data/datasets/imagenav/gibson/v1/；清单见 manifests/gibson_reproduction_20261026.json。
- 用户要求查找可直接下载的正规／社区来源，已发现 Meta 公开直链并下载 gibson_habitat.zip（1468698464 字节）。官方 MD5 校验通过，88 对 glb／navmesh 已放入 SIGN/data/scene_datasets/gibson/，覆盖所需全部 72 train + 14 val；172 个所需文件与 10.83 GB 完整包的大小／CRC 一致。无需再等待下载链接；公开可下载不表示免除 Gibson 用户协议。
- 全部任务文件哈希、场景存在性、原版源码与 checkpoint 哈希检查通过；原版 loader 成功读取全部 val 与抽查训练场景。10-episode GPU smoke（1494494）已成功结束，成功率 0.8、SPL 0.4709，实际渲染／导航管线通过；此小样本不代表完整基准指标。
- 独立 envs/sign-baseline 的 torch 2.0.1+cu117／torchvision 0.15.2+cu117／Habitat-Sim 0.2.2 已通过 CPU 导入、checkpoint 加载及 A40 实际评估。原 envs/sign 仍为 torch 1.11.0+cu113；其 Normal.mode 不兼容问题通过新环境解决，没有修改策略源码。
- 现有 checkpoint 完整评估1494521已成功完成全部4200条，用时20分34秒：SR 86.00%、SPL 53.01%，接近论文86.3%／53.3%。结果见 logs/gibson_reproduction_20261026/pretrained_full_result.json。
- 短训练1494520启动时因CLI总步数写为整数而被YACS拒绝，未进行PPO更新；已修正为40960.0并通过原配置合并检查。重试短训练1494564成功完成40960步／20次更新（作业5分15秒），损失和checkpoint有限，曲线已导出；300M任务1494565因启动前耗时检查退出，1494566依赖失败未运行。三项均CFP／autox。旧长训练1494529／后评估1494531未运行。H表示依赖等待；最新ID及历史见 submitted_experiments.json。
- training_preflight.py 已通过短训练20次更新、损失／checkpoint有限检查；最新checkpoint为24576步，TensorBoard实际完成40960步（原版保存频率导致二者不同）。最近更新中位步速155.68步/秒，300M线性估计535.30h，加裕度615.85h，超过168h。正式训练尚未开始，需验证更快的训练配置／硬件或更长作业时限；原代码无完整断点续训，不能把重启当续训。详见 training_preflight_result.json 与 scratch_smoke/curves/。
- 个人年度默认额度为1000 GPUhr／10000 CPUhr，但当前余额查询需要 amgr 登录，尚未确认余额。个人项目短训练曾被调度器接受，但普通队列持续等待，现将该未开始任务转至 CFP／autox；该项尚未消耗个人GPU时数。个人项目只能使用auto。
- 并发对照 1494552（CFP、autox）已提交：固定14场景×20条任务，比较6环境×1线程、14×1、14×2，再复跑6×1；结果目录 logs/gibson_reproduction_20261026/parallel_benchmark/。四组均成功结束：6×1首次211秒、缓存后复跑176秒、14×1为116秒、14×2为138秒（评估循环）。缓存后比较14×1约加速1.52倍，含启动加速1.43倍；两线程反而变慢。完整4200条14环境预计约14–16分钟，但尚未完整实测。结果见 parallel_benchmark/summary.json。
- 复现细节：目标朝向依赖 Python hash(episode_id)。并发对照固定 PYTHONHASHSEED=0；原完整评估未显式固定该值。后续严格配对模型比较须固定相同哈希种子并准备对应参考结果，不能直接声称不同启动的目标图完全一致。
- README 实际训练配置为 4 环境×512 rollout、300M 步，论文为 8×256；先按仓库原配置复现并明确记录差异。现有 checkpoint 只有 state_dict，未提供训练步数或配置元数据。
- 日志复查：scratch_smoke/tb 的29条scalar序列均有20个点、最大step40960；记录已开启，TensorBoard网页服务未常驻。热身后每2048步约13秒，环境交互／等待7.12秒、推理1.62秒、观测统计1.28秒、模型更新2.93秒（原始计时粗分，非CUDA精确profile）。详见 training_timing_analysis.json。论文明确训练300M步，原代码没有reward平台期自动停止；当前已按用户授权提交个人预算内长训练，可观察曲线／手动提前结束。535h为早期速度线性外推，不能当确定全程耗时；论文8×256配置已短测通过且加速约12%–14%；保持每批2048步，但会改变循环长度。

| 本地目录 | 当前分支／提交 | 状态与用途 |
|---|---|---|
| SIGN | phase2/frozen-visual-encoder @ dac8609 | 干净，已推送并跟踪origin同名分支（yiichu03/SIGN）；仅增加已批准的encoder加载／冻结逻辑 |
| SIGN-frozen-rollout-coverage | phase2/frozen-rollout-coverage @ 6983c91 | 保持运行时代码；origin同名分支b39e362新增资料，勿为同步资料pull进运行目录；data为本地资源软链接 |
| SIGN-frozen-coverage-settle32 | phase2/frozen-coverage-settle32 @ a7cc9e0 | 已push origin同名分支、干净；32步结算对照1502352已提交，独立输出 |
| SIGN-coverage-publication | detached @ b39e362 | 独立资料发布树，干净；已普通push到yiichu03/SIGN的coverage分支，无训练 |
| SIGN-habitat-gs | experiment/habitat-gs-imagenav @ 95eef9b | 完整1900条已跑完，附加指标NaN/Inf触发末尾校验失败；源码干净，远端d1f5aa5是此前发布快照 |
| SIGN-SRU | main @ ba3bb4a | 干净，保留学长 Zichen-Yan 最新主分支基线；研究更改未写入 main |
| SIGN-SRU-reward-review | phase1/imagenav-qwen-diagnostics @ dbf6d3c | 干净，跟踪 origin 同名分支；保存研究资料与工作区整理 |
| habitat-lab | detached HEAD @ 1f7cfbdd | 依赖源码未改，官方 origin 保留，默认无目标推送关闭 |

SIGN main 仍为 dad87fe，SIGN-SRU main 仍为 ba3bb4a，均与各自已核对的 origin/main 一致。两个 GitHub 仓库的默认分支仍是 main；“SIGN默认进入phase2”指本地目录的研究入口；当前冻结实验使用phase2/frozen-visual-encoder，原phase2/exploration-reward-try仍保留dad87fe基线。

## Phase1 保存了什么

- SIGN：[phase1/imagenav-qwen-diagnostics](https://github.com/yiichu03/SIGN/tree/phase1/imagenav-qwen-diagnostics)，提交 f2b4bb4b18422ff0da9ada159a0456dc0c84a1e0。51 个原本待提交文件已按原内容保存，包括确定性动作兼容、评估轨迹／RGB／指标采集、轨迹导出模块，以及 45 个采集、Qwen、绘图、统计、PBS 与发布脚本。
- SIGN-SRU：[同名 phase1](https://github.com/yiichu03/SIGN-SRU/tree/phase1/imagenav-qwen-diagnostics)，最终提交 dbf6d3cc437cd5c673648ceac6fa2ddad2ee1656。保留原研究历史、923 个归档文件和两个工作树的文档改动；SRU src／exp_config 相对 main 无变化。
- SRU 原 main README 修改可追溯到 988f4b2，原研究历史通过合并提交 aa57038 保留。旧 docs/qwen-reward-review-20261013 分支仍为 663b0f9，未改写。
- 第一阶段工具只在 SIGN phase1 上；当前 phase2 没有自动继承新增 scripts、trajectory_diagnostic 或 policy／trainer 的诊断修改。需要读取时用 git show，运行时先选正确分支或另建工作树，不把代码快照当作当前实现。
- 本地 SIGN/data、SIGN/results、环境和模型仍保留。SIGN/.git/info/exclude 跨分支忽略实验材料及 Python 缓存，phase2 工作树可保持干净。

## 研究已知事实与决定

这些是第一阶段的历史结果，最新研究决定为 2026-10-14，不代表本日重新执行。

- 固定 SIGN checkpoint 的 HM3D v0.2 ImageNav 评估已跑通；正式库存为 60 开发 + 120 新增 + 10 同任务组×8 次执行，共 260 条，不等同 260 个独立任务。
- 20 prompt×60 条×3 输入共 3600 个回答。p12 JSON-only 在反复使用的 51 条旧人工参考上有无一致 49/51、平衡一致约 96.0%、等级一致约 88.2%，不是独立测试结果。
- 64 请求的成对 pilot 已完成：24 对复用 40 条，A0／A1 严格一致均 6/24，可读字段一致 6/24、9/24，交换一致均 3/8；A1 正常顺序 22/24 次选 A，尚不能提供可靠相对奖励。
- 用户曾暂定：同任务同起点／目标八条轨迹分别输入 p12，NONE／SOME／CLEAR 暂映射 0／1／2，同级并列，UNCERTAIN 不赋零分或当并列；仅 group_05 的非正式人工观察支持此暂定思路，没有新的完整冻结人工参考。
- group_05 的 episode_006 只在当次人工对照中按截断回答可读 CLEAR 临时纳入；原严格结果仍是 JSON 无效，不构成通用解析规则。详见 WORKLOG 的 MIGRATION-BASELINE。pair_04 人工理由歧义也保留原文。
- 只比较重复搜索，纯受困／恢复单列，不采用成功优先排序。约 40 请求的短输出／互换／自比较／候选列表对照仍只是提议，未提交执行。
- 第一阶段没有 Qwen 驱动的 PPO 更新或训练收益证据；phase2 刚建立基线，探索奖励、信用分配、权重和训练接口尚未实现／验证。

## 运行与发布注意

TensorBoard三组同页入口（2026-10-28）：view_personal_tensorboard.sh已通过--logdir_spec和3读取线程同时加载baseline_frozen、coverage_rollout256、coverage_settle32；临时HTTP探针验证三组success/spl均可读取，显示名可能带/.。现有6006网页仍为旧进程，用户需在本地旧SSH终端Ctrl+C后重跑原命令，再刷新127.0.0.1:16006并勾选三组；横轴Step。首次完整历史载入需数分钟。三训练均R，未改或停止训练。WORKLOG：SIGN-THREEWAY-TENSORBOARD-VIEWER。



- 默认 push 到 yiichu03 的 origin，只有用户明确指定学长仓库时才考虑 upstream。SIGN origin fetch 为 HTTPS，push 已改用实际验证成功的 SSH；SRU 原本使用 SSH。
- 历史诊断／资料发布脚本归档在 SIGN phase1。旧发布器仍要求原 docs/qwen-reward-review-20261013 分支；当前研究工作树处于 phase1 时不直接运行该旧同步流程，也不绕过分支检查。
- 旧发布流程另有未解决的人审汇总差异：history/human_review2_notes.md 的 val_hard/episode_013（归档第 366 行）；原始材料未改动，本轮只是提交现有归档，没有重新生成该资料包。
- SRU 本地缺 data、defm、dinov3 及配置指定的 DINO／DeFM 权重，train.txt 保留其他用户路径；运行具体配置前需核对，尚未做 SRU 导入或训练测试。
- 根目录不是 Git 仓库；四份根文档以服务器维护源为准，通过既有资料发布流程生成快照。最新GitHub入口见本页顶部，不向运行目录pull资料提交。

## 已完成验证

- 归档前 32 个 Python 文件按 Python 3.8 语法检查、16 个 Shell／PBS 的 bash -n、17 个 CPU 发布／证据回归检查全部通过；未运行 GPU 训练。
- SIGN 原 51 个文件逐个与 phase1 提交的 blob 哈希核对一致；SRU 923 个研究归档哈希不变，SRU 算法与配置保持学长 main 基线。
- 两个 phase1 远端 SHA 已核对；phase2 远端已建立，本地 HEAD 与 origin/main 相同；三个项目工作树均干净。原 main 与原研究分支保持，未强推。
- 本地实验数据／结果保留；WORKLOG 持续追加。完整过程见 PHASE-BRANCH、PHASE1-SIGN、PHASE1-SRU、PHASE2-CHECKED-OUT 系列条目。

## 下一步

Habitat-GS完整1900条已跑完，SR16.6842%／SPL8.4819%为原始观察；需先定位附加距离Inf／奖励NaN的具体场景与任务，再决定是否重评，不绕过质量守卫。原1495073已停止；原冻结实验1496716已停止；1497416/1502352继续，新Qwen128训练1507268及两个里程碑val已提交，按8×256观察独立TensorBoard/权重，不扩展12/16环境。300M是算法上限、168h是单作业预算，短测速度不承诺全程或7天完成300M；当前Qwen已在独立新分支接入。


本轮发布规则修订的原始预登记：release_protocol_revision2（服务器：`/scratch/e1538633/liuyi/logs/qwen_recovery_iteration_20261108/expanded_v2/release_protocol_revision2.json`），登记时新确认/普通尚无输出且当前f0e开发尚未开始；用于避免用小确认集反复筛选正向，绝不将中性写成泛化收益。


资源旁证（本轮未改原训练）：1511145原Qwen128/beta.1已于07:11:58 F/Exit-29，预算125:30:01、实际125:31:18，符合原墙钟时限结束；最后步数未在本批复核，日志/权重保留，不自动恢复或重计预算。
