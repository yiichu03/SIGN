# liuyi 当前状态

更新：2026-10-28（Asia/Singapore）。先读 [AGENTS.md](AGENTS.md)；操作与 debug 沿革见 [WORKLOG.md](WORKLOG.md)，命令与复现边界见 [RUNBOOK.md](RUNBOOK.md)。

## 当前目标与分支布局

用户已授权将第一阶段工作归档到两个 yiichu03 仓库的同名 phase1 分支，并让 SIGN 从 origin/main 开始第二阶段。归档、推送和切换已完成；已在独立worktree加入固定rollout覆盖奖励；Gibson 原版短训练和8环境测速已完成，原个人长训练1495073已停止归档，冻结编码器新任务1496716已在个人项目运行，GPU校验通过。

当前用户任务：32步覆盖结算对照已实施并提交。独立SIGN-frozen-coverage-settle32／phase2/frozen-coverage-settle32 @ a7cc9e0已push yiichu03/SIGN，工作树干净。默认interval0兼容旧方案，正式CLI32；8×256、weight0.1、seed100/hash0、冻结初始化、原300M/168h预算和评估均继承。8新测试+9原回归、10组精确兼容及配置审计通过；GPU短跑1502328 Exit0，两组各40960步，42项encoder状态不变，奖励守恒，稳定吞吐343.94/345.64步每秒。正式个人作业1502352已提交（初查Q，node_pool不足），输出results/gibson_coverage_settle32_20261028/train_personal_8env，TensorBoard开启；原1496716/1497416均继续R。短跑不代表学习收益。证据logs/gibson_coverage_settle32_20261028；WORKLOG：COVERAGE-SETTLE32-GPU-PASSED-TRAIN-SUBMITTED-PUSHED。

奖励机制讨论（2026-10-28）：当前coverage自身新增面积/环境步由前5M的0.1403m²升至最近5M的0.1689m²，但基线无覆盖日志，不能归因于该奖励或声称冗余搜索减少。实际末步bonus=w*gain/256，GAE gamma0.99/tau0.95使较早动作的当轮直接反馈衰减。候选为单独weight0.5试验，或保持weight0.1、rollout256而增加32步子片段末结算；后者属于对原结算边界的新提议。其中32步方案随后获用户批准，实施状态见当前任务；weight0.5未实施。证据reward_design_analysis.json；WORKLOG：COVERAGE-REWARD-MECHANISM-AND-NEXT-TRIALS-PROPOSAL。

步数澄清（2026-10-28）：当前8环境各采256步（共2048 transition）后统一加bonus、算returns、执行一轮PPO；训练episode上限1000步，覆盖历史跨rollout延续。32步候选仅增加奖励写入子片段末步的位置，仍采完整256步后处理；不是32步更新一次，也不重置覆盖/真实mask。延长H到512还会使现公式每平方米奖励减半，需单独控制。用户随后批准32步方案，实施状态见当前任务。WORKLOG：COVERAGE-ROLLOUT-VS-SETTLEMENT-EXPLANATION。

当前讨论（2026-10-28）：已按用户选择导出static五组HM3D开发资料（group01/05/06/08/10，各8条同任务）；两套window256/相同长度前缀，共90PNG、80行覆盖统计，含覆盖总比例/扣初始的新增比例/新增面积每步。目录logs/qwen_static_dev5_20261028，打包qwen_static_dev5.zip。894字评分prompt初稿以28对比较换算0–1分，允许并列/未知；未调用Qwen或生成真值，历史开发数据不作独立测试集。等待审核；WORKLOG：QWEN-STATIC-FIVE-GROUP-DEVSET-EXPORTED。

### Habitat-GS 当前进度（2026-10-28）

- GitHub发布：已按用户授权准备发布接入代码95eef9b及docs/experiments/habitat-gs-imagenav资料到yiichu03/SIGN的experiment/habitat-gs-imagenav。发布生成快照核查168/1900、作业仍R；23个资料文件约566KB，哈希／链接／凭据模式和运行源码零差异检查通过。运行工作树HEAD95eef9b保持；发布回执由根WORKLOG追加，包内四文档为生成时点快照。WORKLOG：HABITAT-GS-PUBLICATION-READY。

- **公开原版SIGN完整val评估已提交**：1502487.stdct-mgmt-02，autox／CFP04-SF-109／A40／6h，代码95eef9b；6并行、19场景／1900条、500步／128输入／连续动作、seed100/hash0，公开导航与安全权重SHA守卫通过。CPU已验证全部路径可达、测地距离误差0.0；trainer／网络计算／动作／奖励／指标保持dad87fe作者基线，仅GS接口适配。日志与提交记录logs/habitat_gs_eval_20261028；结果将写SIGN-habitat-gs/results/habitat_gs_full_val_20261028/job_1502487/。已在GN-A40-023运行，实际6环境／完整val配置核对通过，发布快照检查时完成168/1900；尚无完整SR／SPL结果。WORKLOG：HABITAT-GS-FULL-EVAL-RUNNING。

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

- Gibson静态topdown流水线小样本已提交：1502516.stdct-mgmt-02，共享CFP04-SF-109/autox→batch_gpux/A40/2h，已R；旧排队1502509已撤销。Edgemere和Denmark各同任务8条、公开权重随机采样、每条最多256步；独立logs/gibson_topdown_pilot_20261028，原训练源码未变，图片待实际采集验证。WORKLOG：GIBSON-TOPDOWN-PILOT-SUBMITTED。

- 仅训练指标检查已完成（TensorBoard快照2026-10-28T12:38:33+08:00）：1496716／1497416均R，基线60211200步、coverage37621760步，全部已记录scalar有限。按共同37621760步截断，最近500万步SR87.54%／86.00%（coverage -1.55pp），SPL51.90%／48.55%（-3.35pp），导航reward7.532／7.374；最近1000万步SR88.02%／86.05%（-1.96pp）、SPL52.40%／48.91%（-3.49pp）。20M-35M连续三个5M区间也均落后，当前单种子训练曲线未显示收益，尤其SPL偏低。基线已超过50M关闭use_aug_flag阈值，coverage未到，不能拿两者最新单点直接比较。证据logs/gibson_train_check_20261028/comparison.json和matched_training_curves.png。

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

- TensorBoard访问状态（2026-10-26T20:57:49+08:00）：按用户要求关闭本地SSH转发PID1299505及对应登录节点TensorBoard PID3146383，已确认本地16006与远端6006均无监听。用户将自行按RUNBOOK启动；本次未操作PBS训练。WORKLOG GIBSON-TENSORBOARD-USER-HANDOFF。

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
| SIGN-habitat-gs | experiment/habitat-gs-imagenav @ 95eef9b | 完整原版公开权重评估1502487运行中；运行代码保持95eef9b，资料独立发布到origin同名分支 |
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

Habitat-GS完整19场景／1900条公开权重评估1502487已提交，等待实际SR／SPL汇总；不重复提交或调整运行时代码。原1495073已停止；原冻结实验1496716与独立rollout覆盖奖励实验1497416均在个人项目运行，按8×256观察各自TensorBoard／定期checkpoint，不扩展12／16环境。300M为算法上限、168h为单作业预算时限，不承诺7天完成全部300M；本轮覆盖奖励已实现，Qwen未引入。
