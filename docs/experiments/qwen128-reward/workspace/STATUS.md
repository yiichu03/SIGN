# liuyi 当前状态

更新：2026-10-29（Asia/Singapore）。先读 [AGENTS.md](AGENTS.md)；操作与 debug 沿革见 [WORKLOG.md](WORKLOG.md)，命令与复现边界见 [RUNBOOK.md](RUNBOOK.md)。

<a id="gibson-reference"></a>
## Gibson基线与公开权重结果：快速索引

这里的“对照基线”指冻结视觉编码器训练 **1496716**（与两个coverage实验比较的那一组）。

| 常查事项 | 已核实记录 | 证据入口 |
|---|---|---|
| 冻结基线停止时的训练进度 | **74,653,696环境步，约7465万步**；TensorBoard最终事件为2026-10-28 20:28:29，作业20:28:36停止 | 最终事件快照（服务器路径：`/scratch/e1538633/liuyi/logs/gibson_train_threeway_20261028/snapshot_132900/comparison.json`） |
| 冻结基线最后保存、可用于评估的权重 | **74,240,000步，约7424万步**；后续按checkpoint步数选择同预算对照 | 权重保存记录（服务器路径：`/scratch/e1538633/liuyi/logs/qwen_token_probabilities_20261028/baseline_stop_1496716/preservation.json`） |
| 公开完整SIGN checkpoint的Gibson验证成绩 | **SR 86.00%、SPL 53.01%、View Match 85.08%**；完整val **4200条／14场景**，作业1494521，Exit0 | 完整原始结果（服务器路径：`/scratch/e1538633/liuyi/logs/gibson_reproduction_20261026/pretrained_full_result.json`） |
| 最新三方法同预算验证（运行中） | **18,944,000步／ckpt.36**；基线＋256覆盖＋32覆盖，各4200条，单一PBS **1506785**，结果待完成 | 本轮清单（服务器路径：`/scratch/e1538633/liuyi/logs/gibson_threeway_coverage_eval_20261029/manifest.json`） · 运行进度（服务器路径：`/scratch/e1538633/liuyi/logs/gibson_threeway_coverage_eval_20261029/runtime.json`） |

控制台最后一次打印是74,649,600步，比最终TensorBoard记录少4096步；这是不同日志更新频率的末端差异。不要将最终训练记录或控制台末步当成最后checkpoint步数。公开成绩对应加载完整公开导航模型；冻结基线则只加载并冻结其visual_encoder，其余模块从原初始化训练。

公开模型评估原记录中PYTHONHASHSEED未显式固定，后来的共同步数对照使用hash0；复现协议细节与权重路径见 [RUNBOOK证据索引](RUNBOOK.md#gibson-checkpoints)，本次核验汇总见 baseline_reference_index_20261029.json（服务器路径：`/scratch/e1538633/liuyi/logs/gibson_reproduction_20261026/baseline_reference_index_20261029.json`）。

## 当前授权任务：Qwen128正式训练已提交

独立 `SIGN-qwen128-reward` / `phase2/qwen128-reward-beta01` 从453179c建立，运行提交 **81fedec**。54项单测、32原轨迹44窗口离在线精确重放、边界/遮挡/保存函数/评估配置及真实GPU40960步均通过（1507196 Exit0）。有效片段1176/1204=97.67%，42项encoder状态不变，loss/概率有限、真实mask/nav_rewards不变；零权重原训练scalar逐位相同，仅Qc有小于原基线复跑的1.49e-8舍入差。短测每2048步中位59.24s（原基线7.55s），显存5秒采样峰值24947MiB，不能当学习收益或全程恒定速度。

**短测1507196已完成（Qwen部分40960步）；正式1507268是另一条从全新初始化启动的长训练，已经提交并继续运行。** 2026-10-29 16:01只读快照：正式47104步/23更新，55项scalar有限、有效1399/1431=97.76%、SR3.599%/SPL2.807%（训练滑窗），中位64.26s/2048步；同阶段基线SR3.200%/SPL2.212%，尚不足判断学习收益。正式首次checkpoint在512000步，目前未到保存点属正常，4.608M/8.192M评估仍等待。证据logs/qwen128_reward_20261029/progress_20261029T160130；本轮未新qsub或改训练源码。

正式 **1507268.stdct-mgmt-02** 已R、初始化SHA与短测相同（fresh init）：个人auto/1A40/36CPU240GB/168h，300M cap、8×256、seed100/hash0、只加载冻结公开visual_encoder、其他原初始化，**128步/真实终止切段，beta0.1原始q，几何bonus0**，从全新初始化开始。输出 `SIGN-qwen128-reward/results/qwen128_reward_20261029/train_personal_8env`，TensorBoard为其 `tb/`；独立6007查看脚本 `logs/qwen128_reward_20261029/view_tensorboard.sh`，原6006服务不动。

4.608M／8.192M各保存不可变milestone checkpoint并安排原协议4200val：CPU等待1507269／1507271；GPU评估 **1507270／1507272**，当前H依赖等待，待对应权重SHA校验后自动释放，不占等待GPU。使用原SIGN-coverage-eval/6环境/max500/seed100/hash0，Qwen及其轨迹采集关闭，额外0.1m被动覆盖口径与既有三方法评估相同。已核实两评估均经CFP/autox路由到batch_gpux，当前H为afterok依赖；没有处于Q且需要换到gpux的GPU任务。用户偏好后续许可范围内资源排队的GPU任务优先gpux。当前无新评估成绩。回执/配置/短测结论：`logs/qwen128_reward_20261029/`。 已push yiichu03/SIGN同名分支：发布提交35b978f、运行源码81fedec，远端SHA核对一致；运行目录保持81fedec，不pull资料提交。WORKLOG：QWEN128-GPU-SHORT-PASSED-FORMAL-AND-EVALS-SUBMITTED。

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

- 当前三组验证任务已提交并运行：1506785.stdct-mgmt-02，CFP04-SF-109/autox→batch_gpux，GN-A40-021／1A40／36CPU／240GB／4h。三组最新共同ckpt.36实际18944000步，均保存独立不可变快照，参数有限/源与快照SHA/CPU合并配置及记录器检查通过。单PBS沿用相同4200 Gibson val、确定性6环境/max500/seed100/hash0、0.1m/3m/90°覆盖weight0；前置control/smoke通过后依次三组full，共12600正式episode，预计开跑起约3h。当前control_baseline，GPU对照和完整结果尚待完成。证据logs/gibson_threeway_coverage_eval_20261029；原两训练1497416/1502352仍R，旧4.608M/8.192M结果不改。WORKLOG：GIBSON-THREEWAY-18944K-EVAL-SUBMITTED。

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

- TensorBoard访问状态（2026-10-28T19:20:08+08:00）：用户已自行运行SSH（本地PID1638312，16006→远端6006），远端TensorBoard PID1069193读取冻结编码器正式训练目录；本地HTTP200、29条scalar核验通过。用户浏览器实际打开http://127.0.0.1:6006/，确认是本地端口用错，已告知改为http://127.0.0.1:16006/，保留用户连接／服务。WORKLOG：TENSORBOARD-LOCAL-URL-PORT-CORRECTED。

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
- 根目录不是 Git 仓库；四份根文档当前仍为本地维护源，未随本次两个仓库的代码提交自动上传。后续备份／发布需明确选择上下文快照方案。

## 已完成验证

- 归档前 32 个 Python 文件按 Python 3.8 语法检查、16 个 Shell／PBS 的 bash -n、17 个 CPU 发布／证据回归检查全部通过；未运行 GPU 训练。
- SIGN 原 51 个文件逐个与 phase1 提交的 blob 哈希核对一致；SRU 923 个研究归档哈希不变，SRU 算法与配置保持学长 main 基线。
- 两个 phase1 远端 SHA 已核对；phase2 远端已建立，本地 HEAD 与 origin/main 相同；三个项目工作树均干净。原 main 与原研究分支保持，未强推。
- 本地实验数据／结果保留；WORKLOG 持续追加。完整过程见 PHASE-BRANCH、PHASE1-SIGN、PHASE1-SRU、PHASE2-CHECKED-OUT 系列条目。

## 下一步

Habitat-GS完整1900条已跑完，SR16.6842%／SPL8.4819%为原始观察；需先定位附加距离Inf／奖励NaN的具体场景与任务，再决定是否重评，不绕过质量守卫。原1495073已停止；原冻结实验1496716已停止；1497416/1502352继续，新Qwen128训练1507268及两个里程碑val已提交，按8×256观察独立TensorBoard/权重，不扩展12/16环境。300M是算法上限、168h是单作业预算，短测速度不承诺全程或7天完成300M；当前Qwen已在独立新分支接入。
