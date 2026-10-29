# liuyi 工作区约定

## 启动与文档职责

- 用户统一从 `/scratch/e1538633/liuyi` 启动 Codex，以这里为 SIGN / SIGN-SRU 工作区根目录。项目命令仍使用各自仓库要求的工作目录。
- 每个新窗口先读本文件和 [STATUS.md](STATUS.md)，再按需查 [RUNBOOK.md](RUNBOOK.md) 及 [WORKLOG.md](WORKLOG.md) 的相关时间段；不要默认通读全部历史补录。
- 长期主动维护四份根文档：本文件保存稳定规则；STATUS 保存当前目标、进度和下一步；RUNBOOK 保存操作与复现方法；WORKLOG 保存带时间戳的操作、错误、debug、实验结论和决策沿革。
- Gibson对照基线停止步数、最后可评估权重及公开完整checkpoint验证分数，固定入口为 [STATUS快速索引](STATUS.md#gibson-reference)；原始证据和复核方法见 [RUNBOOK索引](RUNBOOK.md#gibson-checkpoints)。训练末步、控制台末步与checkpoint步数分开记录。
- 项目 README 保留项目介绍与导航；已发布研究报告、证据和代码快照留在原位。不要另建重复的 CONTEXT、MEMORY、HANDOFF、研究进度或会话总结文件，用户明确要求除外。
- 当前用户指令优先；旧日志、指导文件和待验证方案本身不触发新实验、训练或发布。

## 操作日志：只追加

- 每个有实质操作的批次、失败尝试或 debug 阶段结束后，向 WORKLOG 末尾追加记录，使用真实的新加坡时间 `YYYY-MM-DDTHH:MM:SS+08:00`，附可引用的条目编号。
- 记录目标、工作目录、关键命令／修改、实际结果、必要的原始错误、排查假设、尝试及验证结果、剩余问题和证据位置。普通读目录可合并描述；会影响复现、判断或后续工作的失败应保留。
- 命令注明已执行还是仅供参考；区分事实、假设与未验证结论，不把部分结果写成完成。
- 已写条目不删除、不改写、不重新排序。纠错通过新条目引用原条目并说明原因。历史补录使用补录时的真实时间戳，注明已知的原事件日期，不捏造旧操作时间。
- 更新 STATUS 的当前摘要；长期有效的操作方法归入 RUNBOOK，稳定规则归入本文件。研究判断与改变方向的原因记入 WORKLOG，STATUS 仅保留目前有效的结论及条目索引。
- 不在持久文档中写入 token、密码或凭据。长终端输出留在原日志，WORKLOG 保存关键片段与位置。

## 仓库边界

- `SIGN/`：当前Gibson冻结视觉实验入口，检出 `phase2/frozen-visual-encoder`；原版阶段二基线保留在 `phase2/exploration-reward-try`，阶段一评估、采集和Qwen诊断保存在 `phase1/imagenav-qwen-diagnostics`。`SIGN-SRU/` 保留学长主分支基线。
- `SIGN-frozen-rollout-coverage/`：独立worktree，分支 `phase2/frozen-rollout-coverage`，从yiichu03/SIGN的dac8609建立；用于固定rollout、按episode片段末步结算覆盖奖励。原SIGN目录不得为该实验切换／修改；1496716已于2026-10-28按用户新授权停止为Qwen腾资源，原权重和日志保留，不自动重启；数据以软链接复用，独立日志与输出。
- `SIGN-frozen-coverage-settle32/`：独立worktree，分支 `phase2/frozen-coverage-settle32`；通过 `habitat.task.observed_coverage.settlement_interval=32` 在完整256步rollout内增加子片段末结算，默认0保持原覆盖方案。沿用weight0.1与冻结初始化，正式作业1502352、独立输出；不得修改或停止前两组训练。
- `SIGN-qwen-topdown-judge/`：独立worktree，分支 `phase2/qwen-topdown-judge`，基于a7cc9e0；当前推进单图独立评分，8环境对应8个独立请求，可在batch维并行；无需同任务分组。Qwen使用envs/qwen35；旧八图同会话接口留作历史，当前未接入PPO奖励或改训练采样。
- `SIGN-qwen-history-window/`：独立worktree与分支`phase2/qwen-history-window`，从b1c24dc建立；仅复用已发布pilot_2b/diverse_2b的32原始轨迹进行128/256窗口历史图离线2B对照。无重新采样、无导航训练或9B；测评作业期间保持对应运行代码固定，输入/窗口/图/概率/prompt/空白人审与来源均须保留。无前置历史的256步不作历史能力验证，不能用平均q判断方案优劣。
- `SIGN-qwen128-reward/`：用户于2026-10-29另行授权从453179c建立独立`phase2/qwen128-reward-beta01`，接入2B训练奖励并在验证后提交正式训练；原离线工作树及现有作业不动。Qwen128/beta0.1使用原始q、不居中，几何bonus0；MRQ只预测nav_rewards，GAE/PPO/critic使用混合奖励。运行期间保持代码提交固定，资料通过独立发布树更新。
- `SIGN-coverage-eval/`：独立detached工作树a7cc9e0，只读复用原native evaluator，用于三组同训练步数的覆盖评估；外部录数wrapper与脚本保存在各批次`logs/gibson_threeway_coverage_eval*/`，具体步数/作业见STATUS，不在此训练。旧批次证据、训练源码与目录原样保留。
- `SIGN-coverage-publication/`：独立detached发布工作树，用于将coverage结果和根四文档生成副本发布到yiichu03/SIGN的覆盖奖励分支；不在此提交训练。训练工作树保持各自运行时代码提交，不为资料同步切换／合并。
- `SIGN-habitat-gs/`：SIGN 的独立工作树，分支 `experiment/habitat-gs-imagenav`，用于 Habitat-GS ImageNav 接入。原 SIGN 路径有已提交的 Gibson 作业，不通过切换它的分支开发新仿真；新工作树以软链接复用数据，环境放 `envs/sign-habitat-gs`，第三方仿真源码放 `habitat-gs/`。 GS评估作业提交后保持此工作树的运行时代码与分支；后续需要改算法时另用独立工作树，不能把Gibson冻结／coverage分支替代原版公开权重评估。
- `SIGN-SRU-reward-review/`：SIGN-SRU 的另一工作树，当前检出同名 phase1；其根目录 `src/` 仍是 SRU 实现，`docs/research/.../code/` 是 SIGN 发布快照，不能互相覆盖。原 docs 研究分支保留。
- 两个 main 保留作者基线；研究改动放阶段分支。SIGN phase2 按用户要求从 origin/main 建立，第一阶段工具不自动继承；后续复用按当前任务选择。
- `habitat-lab/` 是独立依赖仓库；`envs/`、`models/`、`downloads/`、`logs/`、`manifests/` 是配套资源。
- 根目录当前不是 Git 仓库。不要为统一入口移动仓库、合并历史或自动初始化根仓库。四份根文档的发布副本由既有资料发布流程生成，不手工双份维护。
- 操作前核对相应仓库的实际分支与修改，保留用户已有工作。不得用强制推送、reset、clean 或未授权删除来修复同步冲突。

## 研究与证据

- Gibson ImageNav 原版复现保留学长源码及奖励，先评估checkpoint、再从零训练；原从零任务1495073已按用户批准停止并仅留最后落盘权重和日志。用户于2026-10-26另行批准冻结视觉实验：只从公开checkpoint加载并冻结actor_critic.net.visual_encoder，visual_fc及其余模块保留原初始化，仅在独立研究分支修改trainer的两处加载／冻结逻辑，奖励保持原版。运行时不使用monkeypatch、不自动移入phase1修补；新任务使用自身source_manifest校验，不能用原版源哈希守卫拒绝已批准变更。Habitat-GS在独立分支做必要接口适配，明确记录与官方GS基准的动作、目标图、步数及指标差异。
- 历史 HM3D 实验使用 v0.2 验证场景；任务目录 `hm3d/v1` 不代表场景版本。当前任务不因阅读旧 Qwen 方案而转为奖励集成。最终合并配置、运行路径和集群约定见 RUNBOOK。
- 只计重复搜索。纯卡住、碰撞、受阻摆动、脱困单列；没有独立搜索证据时排除。普通分支返回和共同通路不自动算冗余，“成功优先”排序未被采用。
- 区分单条分级、独立请求的推理 batch、直接成对比较和整组排序。八个并行环境不自动构成同任务八次执行。
- 保留并列与未知；不得强制八个不同名次、把未知当零分／并列，或用构造上均值为零的相对分声称训练进步。
- 保留实际输入、原始输出、冻结人工参考与人工复核原文。AI 初审不等同人工真值；修订与重标另行版本化。严格 JSON 结果与可读字段辅助提取分开报告。
- 检查真实请求与原始回答后再归因。重复使用的开发数据不是独立测试；目的性配对不能估计总体发生率；离线评分和固定 checkpoint 评估不证明 PPO 收益。
- 优先有区分度的小规模诊断；大规模 prompt 搜索、PPO 接入和训练结论需相应任务范围与证据支持。

## 集群与发布

- GPU 推理和采集使用 PBS 计算节点；用户要求长任务使用 `auto` / `autox` 路由。环境、项目和复现命令见 RUNBOOK。
- 默认推送目标为用户的 `yiichu03` GitHub：SIGN 使用 origin（yiichu03/SIGN），SIGN-SRU 及其研究工作树使用 origin（yiichu03/SIGN-SRU）。用户说“push”“同步 GitHub”时均按此处理；执行前核对有效 push URL 与目标分支。
- 只有用户明确指定向学长的 GitHub 仓库推送时，才考虑 SIGN 的 upstream（Zichen-Yan/SIGN）。不能因为分支跟踪 upstream/main，就把它当作默认推送目标；fetch／pull 与 push 的目标分别核对。
- Habitat 是第三方依赖，保留官方 origin，常规项目发布不包含它；其无目标默认推送已关闭。不要自动创建或猜测 yiichu03 的依赖 fork。
- SIGN 与 SIGN-SRU 的 remote 和历史分开维护，不能将 SIGN 历史推到 SRU main，也不能用 SIGN trainer 覆盖 SRU trainer。
- 既有项目记录中，向 yiichu03 的研究分支发布已获用户授权；按当前任务范围使用既有发布流程与普通 push，不因阅读本文件自行发布。
- 发布前核对哈希、相对链接、实际完成状态和 WORKLOG 的追加关系。排除权重、场景、凭据、环境与大体积相机数据；已有证据变化、缺失或 Git 历史冲突时保留现场，单独处理。
- 发布副本中的 WORKLOG 同样只允许追加；当前四份根文档是服务器维护源，发布材料是生成副本。具体检查命令与已知发布阻塞见 RUNBOOK 和 STATUS。
