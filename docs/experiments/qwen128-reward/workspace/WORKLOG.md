# liuyi 操作日志

本文件只追加，时间统一为 Asia/Singapore（UTC+08:00）。新窗口先读 STATUS，再按条目编号与日期检索本日志；无需默认通读历史导入。纠错追加新条目并引用旧编号，不修改旧记录。

每条记录包含时间戳与编号、目标／工作目录、关键操作或命令、观察到的结果和错误、debug 尝试与依据、验证及未完成事项。长终端输出保留在原文件，这里只保留追溯所需内容与位置。不记录凭据。

## 2026-10-26T02:25:14+08:00 — MIGRATION-BASELINE：历史基线补录与文档结构决定

- 记录性质：本日迁移补录；原研究事件主要发生于 2026-10-13／14。下方原文的“当前”“已提交”等均指写作当时，不代表本日重新执行，也不虚构当时未记录的时分秒。
- 用户确认统一从 `/scratch/e1538633/liuyi` 启动，要求核心文档不超过四份，其中一份是带日期和时间戳、持续追加的操作／错误／debug 日志，并授权代理判断旧文档处置。
- 本轮采用根 AGENTS.md（规则）、STATUS.md（现状）、RUNBOOK.md（操作）、WORKLOG.md（追加历史）。研究结论和决策沿革入本日志，当前有效摘要入 STATUS；不再单列 RESEARCH 或 CONTEXT。
- 工作目录：`/scratch/e1538633/liuyi`。整理前核对本地 Git 状态，保留 SIGN 原有 policy／trainer 修改；备份将修改／删除的文档与发布脚本，并记录 965 个研究归档及导航源码文件的 SHA256。临时回退材料：`/tmp/liuyi-doc-migration-dtq0smkn`；长期需要的原研究正文完整导入下方。
- 已知问题（前序窗口发现，本轮未改动人审材料）：发布预览因 `Existing evidence/review would change: history/human_review2_notes.md` 停止。当前生成汇总与归档有一处差异，归属于 val_hard/episode_013、归档第 366 行。保留原样，后续单独核对来源与版本化。
- 旧材料处置：原 15 份中的 SIGN/AGENTS、研究工作树/AGENTS、SIGN/docs/qwen_offline_diagnostic、SIGN/docs/hm3d_v02_eval 内容迁移后删除；三个项目 README 保留导航；其余八份发布／历史说明保持原位。前轮新建的根 CONTEXT 同时拆分并删除。
- 实施中的工具错误：首次 apply_patch 在同一补丁内对 AGENTS 同时 Delete/Add，被工具校验拒绝、未写文件；改为顺序操作后成功创建规则、状态和运行手册。此处记录工具层失败，不归因于项目代码。
- 后续：调整发布脚本从根收集四文档，保留既有旧路径快照；修正 README、删除迁移源、验证链接／证据／源码哈希与发布保护。完成结果追加后续条目。
- 迁移来源：`SIGN/docs/qwen_offline_diagnostic.md`，迁移前 UTF-8 原文 SHA256：`2775c40d8e1ac2447c1b626ae2bc9a14d93fc5c429e818d1c917de175d81eacc`。原文全文置于下方代码块，属于历史材料，不是当前执行指令。

<details>
<summary>迁移前 SIGN 详细研究记录全文（347 行；含历史错误与 debug 经过）</summary>

<!-- BEGIN IMPORT SIGN/docs/qwen_offline_diagnostic.md sha256=2775c40d8e1ac2447c1b626ae2bc9a14d93fc5c429e818d1c917de175d81eacc -->
````````markdown
# Qwen 离线轨迹诊断

工作区入口于 2026-10-26 统一到 `/scratch/e1538633/liuyi`：先读根目录 `AGENTS.md`（工作规则）和 `CONTEXT.md`（跨窗口进度与决策摘要）。本文继续维护 SIGN / Qwen 的详细研究事实、流程及历史；下述实验状态日期保持原样。

## 当前状态（2026-10-14）

SIGN checkpoint 在 **HM3D v0.2 验证场景**上的 ImageNav 评估已跑通。目标是让 Qwen 提供同任务8条轨迹的相对重复搜索反馈，作为未来策略训练的辅助项。已有奖励负责成功与任务进展；**目前没有把 Qwen 输出接入 PPO，也没有训练收益证据**。

只计重复搜索；纯卡住、碰撞、受阻摆动和脱困单独报告。正常首次扫描、分支探查后的返回、进入不同分支的共同通路，不自动算冗余。“成功优先”的整体排序曾讨论，但当前实验没有采用。

2026-10-14 用户暂定 **p12 JSON-only 独立分级后计算同任务 batch 内相对分数**，作为后续研究思路；依据包括对 group_05 的初步人工观察。方案尚未接入训练，分数尺度与权重未校准。

### 数据与已完成阶段

| 阶段 | 规模 | 已验证内容与边界 |
|---|---|---|
| 初始开发 | graded60：easy/medium/hard各20 | 三种输入、动作字段修正、单条与独立batch8推理已跑通 |
| 新增采集 | additional120：各40 | 新增场景轨迹与AI初审；AI标签不是人工真值 |
| 同任务组 | group8_p12：10任务×8次随机执行 | 固定checkpoint；每组同起点/目标；p12每条独立判断，Qwen未直接比较另外7条 |
| 直接成对诊断 | 24对，复用40条轨迹 | 新成对prompt；A0双JSON，A1双图＋计算事实；64请求，batch=2，全部完成 |

总计260条正式执行记录，不是260个独立任务；早期graded15等先导数据不计入。24对是目的性选取，包含既有混淆、排序分歧、同为CLEAR及正常返回对照，不能估计总体冗余发生率。

### 单条 p12 的结论

20个英文prompt×60条×3种输入，共3600个回答。p12在仅JSON条件下，相对51条纳入主要统计的旧人工参考：有无一致49/51，平衡一致率约96.0%，等级完全一致约88.2%。这是参与迭代的开发数据，不能外推为独立测试准确率或成对排序能力。

原文：`results/qwen_diagnostic/prompt_iteration/templates/p12_json_only.txt`；统计：该目录的 `summary.md`。p12输出NONE/SOME/CLEAR/UNCERTAIN；JSON-only模板仍含共用的Plot说明，应如实保留历史输入。

### 暂定 batch 内评分思路

- batch 的含义是同一任务、起点与目标下的 8 次执行。每条完整 JSON 独立输入 p12，batch8 只做推理并行，模型不直接比较另 7 条。
- 重复搜索负担暂按 NONE=0、SOME=1、CLEAR=2 表示，同等级保留并列；UNCERTAIN 不自动当作并列或零分。已有取负并做组内归一化的相对分数只作示意，奖励权重及训练信用分配后续再确定。
- 用户查看 group_05 静态图后表示，p12 的粗等级排序与其人工观察大致相符，并接受该方案作为暂定思路。这是初步人工反馈，未形成新的完整冻结人工标注，也不改变此前 AI 初审或严格统计。
- 本次人工对照将 episode_006 按截断原文中明确的 CLEAR 暂时纳入：`002=004=005=008 < 001 < 003=006=007`（重复搜索由少到多）。严格结果仍将 006 记为输出达到 512 token 上限、JSON 无效；不修补或替换原始回答，输出长度后续再调整。这次临时纳入不代表已采用统一的无效输出处理规则。
- 采样使用固定 SIGN checkpoint，每组启动一次评估进程，以一个环境设置 `evals_per_ep=8`，连续执行同一任务 8 次。`SIGN_EVAL_SAMPLE_ACTIONS=1` 启用原策略动作分布的随机采样，每个 episode 重置环境和循环状态；无训练更新。起点、目标图和初始 RGB 的一致性已保存哈希核对。

后续优先抽查其他同任务组及搜索／脱困边界，检验此粗分组是否符合人工观察；不因与 AI 初审不一致就直接认定模型错误，也不从 group_05 一组反馈推断所有组都可靠。

### 当前成对结果

目录：`results/qwen_diagnostic/pairwise_pilot_20261013/`。人工24对原样冻结，A更少8、B更少3、并列13、未知0。pair_04的并列理由存在“难对比”歧义，保留原文，未自行重标。group_10的6对全部人工并列，不应默认需要细排。

作业 `1455625.stdct-mgmt-02`，autox / CFP04-SF-109 / A40，2026-10-13新加坡时间22:25–22:55完成模型阶段。24对×2条件=48请求；8对在两个条件下交换A/B再问=16请求；共64。每批2个独立成对请求，不是一次比较完整8条轨迹。

| 指标 | A0：双完整JSON | A1：双概览图＋事实 |
|---|---:|---:|
| 正常顺序完整合法JSON | 22/24 | 14/24 |
| 严格解析下与人工一致 | 6/24 | 6/24 |
| 单独提取明确preference字段后与人工一致 | 6/24 | 9/24 |
| 严格解析的交换一致/可比较对数 | 2/7 | 2/5 |
| 可读字段的交换一致/可比较对数 | 3/8 | 3/8 |
| 正常顺序可读判断分布 | A更少6、B更少18 | A更少22、B更少1、并列1 |
| 平均输入tokens（含互换） | 47,857 | 7,425 |
| 平均摊销秒/请求（batch=2，含互换） | 46.67 | 10.34 |

严格统计见 `comparison.json`；可读字段辅助分析见 `decision_diagnostics.md/json`。辅助分析只读取唯一明确的preference字段，不修复JSON、不覆盖原结果、不验证理由。一直回答并列可匹配13/24，因此当前不能声称模型比较已有效；A1较快，但22/24选A且交换不稳定，不能将其8/11明确偏好命中视为可靠收益（始终选A也能命中这11对中的8对）。

具体问题：A1 pair_01选择A_LESS，理由却说A重复搜索负担更高；A0 pair_13也存在理由与选择反向。多处把候选空间匹配数量、小范围摆动或脱困当作重复搜索。A0/A1公共prompt是新写的成对版本，并非原样复用p12；不能把两种任务的结果混为一谈。人工可见稀疏RGB，Qwen没有；证据不足与推理错误要区分。

### 当前实现与下一步问题

- `scripts/prepare_pairwise_diagnostic.py`：共享比例图、人工动画、25步事实窗口和候选匹配。候选匹配是几何启发式，不是冗余标签；可能包含持续受困，也可能漏掉相邻窗口回访。
- `scripts/qwen_pairwise_diagnostic.py`：prepare/freeze/run/summarize；新增 `diagnose` 仅做可读字段辅助分析。实际request/response原样保存；`model_review.md`人工栏不会被重新汇总覆盖。
- 已提出但**尚未实现/提交**的下一轮：8个既有标注对正反顺序＋4个自比较，两种输入（保留/移除候选匹配列表），共约40个短请求，检查方向、并列、自比较和候选列表诱导。先讨论确认具体方案；当前用户要求维护文档与代码，没有启动该实验。
- 尚未验证完整8条直接排序、可靠相对reward、PPO信用分配或训练收益。既有64请求不应重跑覆盖。新实验独立版本化，不据此开启大规模prompt搜索。

### 复查与发布

```bash
/scratch/e1538633/liuyi/envs/sign/bin/python scripts/qwen_pairwise_diagnostic.py diagnose
```

SIGN环境：`/scratch/e1538633/liuyi/envs/sign`；Qwen环境：`/scratch/e1538633/liuyi/envs/qwen35`；官方模型：`/scratch/e1538633/liuyi/models/Qwen3.5-9B`。GPU作业使用PBS auto/autox；手册在 `~/liuyi/Vanda Cluster User Guide 05Jun25.pdf`。

当前 SIGN 的 origin 已按用户要求设为 `https://github.com/yiichu03/SIGN.git`；原项目 `Zichen-Yan/SIGN` 为 upstream，main 仍跟踪 upstream/main。SIGN-SRU 的 origin 保持 `git@github.com:yiichu03/SIGN-SRU.git`。研究发布继续使用工作树 `/scratch/e1538633/liuyi/SIGN-SRU-reward-review` 的 `docs/qwen-reward-review-20261013` 分支，不把 SIGN 代码覆盖到 SRU 训练源码。

`scripts/publish_relative_diagnostic.py` 更新该分支的资料包和代码快照，不自动 commit/push；`scripts/sync_research_github.sh` 提供一键校验、发布、提交和普通 push。入口为 `docs/research/qwen_relative_diagnostic_2026-10-13/README.md`。上传代码、人工记录、当前轨迹/图/GIF、请求/回答与历史统计；不上传权重、场景、RGB或环境。资料包约 33MB，原始结果继续保存在服务器。

## 本地目录与 Git 结构

目录与仓库状态按 2026-10-14 整理。三个 SIGN 相关目录归属于两个独立 Git 仓库；`SIGN-SRU-reward-review` 是 `SIGN-SRU` 的另一份工作树。`yiichu03/SRU-Predictor` 远端可访问，但当前 `/scratch/e1538633/liuyi/` 下没有它的独立检出目录，当前 SIGN 的 remote 也未关联它。

### 本地相关目录

```text
/scratch/e1538633/liuyi/
├── AGENTS.md                ← 统一工作区规则与阅读入口
├── CONTEXT.md               ← 跨窗口进度、决策与材料索引
├── SIGN/                    ← 当前工作目录：导航评估、采集、Qwen 诊断
├── SIGN-SRU/                ← SRU 导航代码，main 分支
├── SIGN-SRU-reward-review/  ← SIGN-SRU 的研究发布工作树
├── habitat-lab/             ← Habitat 依赖源码，也是独立 Git 仓库
├── envs/                    ← SIGN、Qwen Python 环境
├── models/                  ← Qwen 模型
├── downloads/               ← 下载工具
├── logs/                    ← 日志
└── manifests/               ← 清单目录
```

### SIGN 文件结构

下面展开主要源码和研究目录，省略缓存、部分脚本及大量逐轨迹文件。

```text
SIGN/
├── .git/                         ← 当前 SIGN 自己的 Git 元数据
├── .gitignore
├── AGENTS.md                     ← 项目维护规则
├── README.md
├── requirements.txt
├── constraints-hm3d.txt
├── run_sim.py                    ← 仿真训练／评估入口
├── run_deploy.py                 ← 部署入口
│
├── src/                         ← 当前实际运行的 SIGN 代码
│   ├── policy.py                ← 导航策略与安全机制
│   ├── models.py                ← 网络模块
│   ├── trainer.py               ← PPO 训练与评估、采集入口
│   ├── environment.py           ← 环境与任务奖励
│   ├── trajectory_diagnostic.py ← 轨迹导出
│   ├── sensor.py
│   ├── metric.py
│   ├── dataset.py
│   ├── custom_action.py
│   ├── custom_habitat_env.py
│   ├── custom_habitat_simulator.py
│   ├── custom_embodied_task.py
│   ├── custom_rollout_storage.py
│   ├── resnet.py
│   ├── transforms.py
│   ├── utils.py
│   ├── visualization.py
│   ├── algo/
│   │   └── PPO.py
│   └── config/
│       ├── policy.yaml
│       ├── reward.yaml
│       ├── sensors.yaml
│       └── eval.yaml
│
├── exp_config/
│   ├── ppo_imagenav_hm3d.yaml
│   ├── ppo_imagenav_gibson.yaml
│   ├── ppo_imagenav_mp3d.yaml
│   └── base_task_config/
│
├── docs/
│   ├── qwen_offline_diagnostic.md ← 当前研究状态与目录说明
│   └── hm3d_v02_eval.md           ← 环境与数据说明
│
├── scripts/                      ← 采集、推理、审核和发布脚本
│   ├── run_group8_collection.py
│   ├── score_group8_p12.py
│   ├── prepare_pairwise_diagnostic.py
│   ├── qwen_pairwise_diagnostic.py
│   ├── qwen_chunked_prefill.py
│   ├── publish_relative_diagnostic.py
│   └── …其他 Python 脚本与 PBS 作业脚本
│
├── results/
│   ├── hm3d_eval/
│   └── qwen_diagnostic/
│       ├── graded15/             ← 早期先导数据
│       ├── graded60/             ← 60 条开发轨迹
│       ├── additional120/        ← 120 条新增轨迹
│       ├── group8_p12/           ← 10 组×8 条执行
│       ├── prompt_iteration/     ← 20 个 prompt 实验
│       ├── pairwise_pilot_20261013/ ← 当前 64 请求成对实验
│       ├── codex_audit/          ← AI 初审
│       └── …其他评估与预览目录
│
├── ckpt/                         ← 导航／安全模型权重
├── data/
│   ├── datasets/
│   ├── scene_datasets/
│   └── versioned_data/
└── deployment/                   ← 部署代码
```

`data/`、`results/` 和 Python 缓存在当前 `.gitignore` 中被忽略。研究发布脚本从这些本地结果中选择可公开的证据，另存到 SIGN-SRU 的研究目录；列出目录不表示其中全部内容已经上传 GitHub。

### Git 仓库与工作树

```text
SIGN/：独立 Git 仓库，保留原 SIGN 历史
├── 本地分支：main @ 21274be
├── 跟踪分支：upstream/main
├── upstream → git@github.com:Zichen-Yan/SIGN.git
└── origin   → https://github.com/yiichu03/SIGN.git

SIGN-SRU/：另一个独立 Git 仓库
├── origin → git@github.com:yiichu03/SIGN-SRU.git
├── main @ ba3bb4a
│   └── 工作目录：SIGN-SRU/
└── docs/qwen-reward-review-20261013
    └── 工作目录：SIGN-SRU-reward-review/
```

配置 remote 地址不会自动合并代码或提交历史。SIGN 的 origin 指向 yiichu03/SIGN，SIGN-SRU 的 origin 指向 yiichu03/SIGN-SRU；两个本地仓库各有自己的 `.git` 和历史。研究资料仍发布到 SIGN-SRU 的研究分支。

`SIGN-SRU-reward-review/.git` 是一个文本文件，内容为：

```text
gitdir: /scratch/e1538633/liuyi/SIGN-SRU/.git/worktrees/SIGN-SRU-reward-review
```

因此，SIGN-SRU 的两个工作目录共享提交历史和 Git 数据，同时检出不同分支。研究资料发布在 [docs/qwen-reward-review-20261013 分支](https://github.com/yiichu03/SIGN-SRU/tree/docs/qwen-reward-review-20261013)。

### 提交与发布状态

目录说明最初在研究分支提交 `d31259de3920641f0877057b52ab77ad52a87152`（2026-10-14 18:06，新加坡时间）发布。后续同步会推进研究分支；一键脚本会打印当次提交 SHA 和固定 GitHub 链接。以下状态区分实际开发工作区与已经发布的代码快照。

| 目录 | 分支与工作区 | 提交与发布关系 |
|---|---|---|
| `SIGN` | `main @ 21274be`，有未提交修改和新增文件 | 当前开发修改没有直接在此仓库提交；对应代码快照已发布到研究分支 |
| `SIGN-SRU` | `main @ ba3bb4a`，工作区干净 | 2026-10-14 核对时与 GitHub `main` 一致；研究分支尚未合并到此分支 |
| `SIGN-SRU-reward-review` | `docs/qwen-reward-review-20261013` | 已有研究资料已 commit、push；本节沿用该分支发布 |

当前 SIGN 未提交的已有文件修改包括 `README.md`、`src/policy.py`、`src/trainer.py`；新增内容包括 `.gitignore`、`AGENTS.md`、`constraints-hm3d.txt`、`docs/`、`scripts/` 和 `src/trajectory_diagnostic.py`。

两个 `src/` 的用途必须区分：`SIGN/src/` 是实际评估代码；`SIGN-SRU/src/` 是 SRU 导航代码。前者在研究分支中保存于 `docs/research/qwen_relative_diagnostic_2026-10-13/code/src/`，没有覆盖后者。2026-10-14 的核对中，已发布代码快照的 89 个对应文件与当时实际 SIGN 工作区逐字节一致。

当前 SIGN 的本地 `upstream/main` 缓存仍是 `21274be`；2026-10-14 查询 GitHub 时，原作者 `main` 是 `dad87fe225a4dc1073787d8d2cc83f67e61c0a9d`，因此尚未同步原作者最新代码。`SRU-Predictor` 的远端 `main` 在同日查询为 `64b3bb6f0d2f7ec72e3f274d76080491b5688b57`；这里没有它的本地 Git 工作区，不能据此判断它是否存在其他未提交或未推送的本地修改。

### GitHub 一键同步流程

保持现有目录布局，运行以下命令即可同步研究资料：

```bash
bash /scratch/e1538633/liuyi/SIGN/scripts/sync_research_github.sh
```

只校验和预览、不写发布文件或提交时，追加 `--check-only`。脚本使用 SIGN Python 的标准库，不运行 Qwen、采集、PPO、重新汇总或修改训练逻辑。

1. 核对发布工作树、研究分支和 SIGN-SRU origin；拒绝脏工作区、未完成的 Git 操作和并发同步。只 fetch 该研究分支；远端超前或历史分歧时停止，不自动合并。
2. 读取服务器材料，在内存中构建发布计划。核对 64 个请求的完整 input/request/response/result、源轨迹和图片 SHA256、冻结人工参考、严格统计及可读字段辅助统计；保留所有无效／截断回答。
3. 核对旧资料包 manifest 与实际文件。已有人工记录、模型输入／回答、历史统计等若变化或缺失，停止并保留现场，需另行版本化；不静默覆盖或删除。限制文件类型和体积，排除数据、权重、环境、缓存与凭据目录，检查相对链接。
4. 写入发生变化的发布文件，显示 Git 变更并仅提交研究资料目录，普通 push 后核对远端 SHA，输出固定链接。材料相同时不更新快照时间、不产生空提交。push 失败保留本地提交，工作区干净且远端仍是其祖先时可重新运行。

当前同步范围：实际 SIGN 代码／配置与研究文档；64 个成对请求的四件原始记录及统计／人工参考；20 个 prompt 的 3600 个原始回答和统计；同任务组的 80 个 p12 原始回答、统计和两条标准单条对照；260 条执行库存、60 条人工复核原文与历史耗时。历史重复长请求、RGB 和大体积中间材料保留在服务器；新实验须独立版本化后再扩展发布范围。

安全检查可在 CPU 上运行：`/scratch/e1538633/liuyi/envs/sign/bin/python scripts/test_research_publication.py`。研究入口 README 优先显示当前问题、最新结论、代码位置、下一步和历史索引；现有历史报告保留。

## 历史流程与命令

以下保留各阶段的原始流程与当时状态，最新结论以上面的“当前状态”为准。初期正式采集为各难度20条；更早的easy/medium各5条保存在graded15，属于先导数据。

## 采集

`src/trainer.py` 在设置 `SIGN_TRACE_DIR` 时启用 Habitat 俯视图记录。每条 episode 导出按执行顺序排列的 `waypoints.json` 和 `trajectory.png`。JSON 保存起点和每次动作后的俯视坐标、朝向、动作、碰撞；图片标注起点、终点、稀疏 step 和朝向，轨迹由蓝变橙。不显示最短路径或目标标记。

采集 PBS 脚本为 `scripts/collect_sign_trace1.pbs`，通过 `SIGN_SPLIT`、`SIGN_EPISODE_COUNT`、`SIGN_TRACE_DIR` 指定数据集分级、数量与目录。例如：

```bash
qsub -q auto -P personal-e1538633 -v SIGN_SPLIT=val_easy,SIGN_EPISODE_COUNT=20,SIGN_TRACE_DIR=/scratch/e1538633/liuyi/SIGN/results/qwen_diagnostic/graded60/val_easy scripts/collect_sign_trace1.pbs
```

三组正式结果位于 `results/qwen_diagnostic/graded60/val_{easy,medium,hard}/episode_001` 至 `episode_020`，序号在每个难度内从 1 开始。

## 三种输入条件

同一条 episode 分别独立发送给官方 `Qwen/Qwen3.5-9B`：

1. 仅俯视轨迹图；
2. 仅完整 waypoint JSON；
3. 俯视轨迹图与完整 waypoint JSON。

三个请求使用相同的四项中文回答格式：冗余探索行为判断、大致 step 区间、重复路径判断、依据。提示词明确区分重复路径与冗余探索。模型位于 `/scratch/e1538633/liuyi/models/Qwen3.5-9B`，运行环境为 `/scratch/e1538633/liuyi/envs/qwen35`。

`scripts/qwen_three_way.pbs` 调用 `scripts/run_qwen_three_way.py`，加载模型一次后逐条处理 60 条 episode。该作业使用 `autox` 路由和有效的 `CFP04-SF-109` 项目。每条保存 `request_<condition>.txt`、`response_<condition>.txt`、`timing_<condition>.json`、`review.md`；组合输入也另存为 `request.txt`。`review.md` 集中展示轨迹、三组原始回答和人工复核栏。总入口为 `results/qwen_diagnostic/graded60/index.md`。PBS 作业应在三组采集全部完成后运行；当前已提交带 `afterok` 依赖的作业。

先导单条案例在 `results/qwen_diagnostic/traces/episode_001`，最初请求、回答、耗时和审核表保存在其 `pilot_v1` 子目录。目标图和 RGB 关键帧留待人工审核发现信息不足时再补。

## 人工审核动画

已保存的 `waypoints.json` 和 `trajectory.png` 足以生成动态轨迹，无需重跑 ImageNav。`scripts/render_trajectory_gifs.py` 把每条轨迹转成 `trajectory.gif`，显示逐步增长的路径、最近 20 步、当前位置朝向、碰撞与 step 进度，并把 GIF 嵌入对应的 `review.md`。动画仅供人工审核，不参与 Qwen 输入。完整 60 条由 `scripts/render_trajectory_gifs.pbs` 在 CPU 节点生成；单条可直接运行：

```bash
/scratch/e1538633/liuyi/envs/sign/bin/python scripts/render_trajectory_gifs.py results/qwen_diagnostic/graded60/val_easy/episode_001
```

## v2：纯白底渐变轨迹

经人工确认，v2 使用 `scripts/preview_trajectory_layouts.py` 的 `white_gradient` 布局：纯白背景、连续 turbo 色条、step 标签和保存的朝向。直接从同一份 `waypoints.json` 等比例绘图，无需重跑 ImageNav。`START` 为首个已保存位置（step 1），图片不展示墙体或障碍物。此前 `trajectory_v2.png` 是未采用的预览；本次实际输入名为 **`trajectory2.png`**。

`prepare_qwen_v2.py` 为全部 60 条准备图片和实际提示词；四项判断要求与原版一致，仅更新图例说明。`run_qwen_v2.py` 重新调用仅 PNG 和 PNG + waypoint JSON 两组，共 120 个独立请求，保持原模型、greedy 解码、关闭 thinking、最多输出 512 tokens。纯 JSON 组直接引用原输入、输出和原运行耗时。新版布局和图例文字均有变化，比较结果时应一并考虑。

每条新增 `trajectory2.png`、`request_image_only2.txt`、`request_image_json2.txt`、对应的 `response_*2.txt` / `timing_*2.json` 和 `review2.md`。原文件全部保留。审核表显示三组回答和人工复核栏，同时保留仅供人看的原 GIF。入口是 `results/qwen_diagnostic/graded60/index2.md`，准备阶段显示待运行状态，每条新推理完成后自动更新。

CPU 绘图和 GPU 推理均使用 `autox`、`CFP04-SF-109`，按依赖顺序提交：

```bash
render_job=$(qsub scripts/prepare_qwen_v2.pbs)
qsub -W depend=afterok:"$render_job" scripts/qwen_v2.pbs
```

绘图日志为 `prepare_v2.log`，推理日志为 `qwen_v2.log`，运行元数据为 `run_metadata2.json`。推理脚本可跳过已完成的新版本请求；若中断，只需重新提交 GPU 脚本。人工填写 `review2.md` 后避免重新运行尚未完成的该条推理，以免自动生成报告覆盖填写内容。

## 人工审核后的三组后续实验

`scripts/qwen_followup.py` 提供 `prepare`、`run --version 2/3/4`、`summarize`。
动作向量实际顺序为 `[angular_velocity, linear_velocity]`；原导出器的文字说明写反，现已修正。
每条新增 `waypoints_corrected.json`，只修正此说明，坐标、朝向、动作数值与原始记录一致。
历史 `waypoints.json` 和原版 `review.md` 保留，以便对应历史输入。

- 实验 1（version 2）：60 条仅 JSON、PNG+JSON，共 120 次；直接在旧实际请求中替换动作说明，其他提示词不改。原 v2 PNG 回答复用。JSON 组使用新的 `request_json_only2.txt` 等文件；组合组替换 `request_image_json2.txt` 等文件。更新 `review2.md`，逐字保留原人工复核部分。
- 实验 2（version 3）：60 条、三种输入，共 180 次单条推理；新提示词明确正常转向/观察/折返与可疑冗余、卡住/脱困的区别，输出四级程度判断。结果为 `review3.md` 和各条件 `*3.txt/json`。
- 实验 3（version 4）：输入与实验 2 字节一致，使用真实 batch_size=8；八个独立会话分别占输入张量的一行，左侧 padding，不共享会话内容。60 条按轨迹长度降序分成七批八条、末批四条，三种输入各运行八批。完整轨迹不截断。结果为 `review4.md` 和各条件 `*4.txt/json`。

准备阶段先将原案例目录、报告及人工备注完整复制到 `archive_before_action_fix/`，并保存 SHA256 清单。
`review3/4` 引用已有人工判断，同时另留本轮人工复核栏。所有 GIF 仍只供人工查看。
旧 `analysis_review2/` 是修正前统计，不能当作动作字段修正后的统计。

三个 GPU 作业可独立提交，都使用 `scripts/qwen_followup.pbs`、`autox`、`CFP04-SF-109`、单张 A40：

```bash
qsub -N qwen-jsonfix -v QWEN_REVIEW_VERSION=2 -o "$PWD/results/qwen_diagnostic/graded60/qwen_followup2.log" scripts/qwen_followup.pbs
qsub -N qwen-criteria -v QWEN_REVIEW_VERSION=3 -o "$PWD/results/qwen_diagnostic/graded60/qwen_followup3.log" scripts/qwen_followup.pbs
qsub -N qwen-batch8 -v QWEN_REVIEW_VERSION=4 -o "$PWD/results/qwen_diagnostic/graded60/qwen_followup4.log" scripts/qwen_followup.pbs
```

运行元数据为 `run_followup2/3/4.json`，记录实际 GPU、软件版本、模型加载时间和 PBS 作业号。
每个作业退出时自动更新 `timing_summary.csv/json`；三个作业都结束后包含全部九个条件。
耗时包含处理器预处理、数据传输及模型生成，不含排队、加载模型和写报告。
同时记录预处理/生成分段耗时、真实输入 token、padding 后长度、输出 token、峰值显存与首批标记。
汇总提供平均、中位数、P95、总推理时间、吞吐量与每条摊销耗时。批次总耗时不等于每条摊销耗时；历史 PNG 时间注明复用。
批量与单条使用同一模型、greedy 解码、关闭 thinking、输出上限 512 tokens。

首次 batch8 长序列尝试在 SDPA 的 padding 掩码分配处显存不足，日志留存在 `qwen_followup4_oom1416944.log`。
批量组随后使用 `qwen_chunked_prefill.py` 按 2048 token 分块 prefill，并跨块保留全部混合注意力缓存；每个 forward 仍包含八个独立上下文，不截断轨迹、不划分独立判断窗口。
仍使用 SDPA，不替换模型权重或注意力后端。启动时用八个独立多模态短请求，在两个相同强制前缀下比较分块与原路径的 logits 和概率分布，通过数值核对才运行正式批次。BF16 分块运算可能改变接近并列的 token 选择，因此不要求后续生成文本逐字相同；记录相对 RMS、最大 logit 误差、概率总变差及首 token 一致数量。核对耗时单独记录，不混入正式推理均值。

本次有效作业记录在 `followup_jobs.json`：实验 1 为 `1416942`，实验 2 为 `1416943`，批量实验重试为 `1417038`。
批量组指定 `host=gn-a40-030`，等待实验 1 的正常节点资源；`gn-a40-040` 曾发生 PBS 启动失败，未执行模型。
批量日志为 `qwen_followup4_chunked_final.log`。独立 CPU 汇总作业 `1417051` 依赖上述三个作业结束，重新生成耗时表并核对三组实验的九个条件均为 60 条；不完整时会明确报错。

### 后续检查与补跑

实验 1、2 均已完成，分别生成 120、180 个新回答。实验 3 的 `1417038` 未通过旧的 BF16 相对 logit 误差阈值，未生成正式批量回答；其最终汇总因此正确报告不完整。
已增加 FP32 文本层的实现核对：原路径与分块路径最大 logit 误差约 `8.54e-5`，8 条首 token 全部一致；BF16 的概率总变差约 `0.0051`，作为数值差异单独记录。
随后正式长输入暴露 `masked_scatter` 在隐藏维度展开后分配巨大临时索引的问题。改用二维 token 行索引原位写入图像特征，模型输入内容不变。
补跑作业与最终汇总的最新编号以 `followup_jobs.json` 为准，当前批量日志为 `qwen_followup4_tokenrows.log`。

`analysis_followup/case_comparison.csv` 和 `summary.json` 比较修正后的 review2 与新提示词 review3，人工参考仍采用最初 23 条无/可忽略、8 条有、23 条明显有、5 条不确定/边界、1 条未标注的分类。
报告中仅 JSON 组误附 PNG 链接的文字已修正；实际 runner 一直没有向该条件发送图片，timing 的 image 字段为 null。
`val_easy/episode_019` 的 review3 组合输入回答达到 512 token 上限，依据末尾截断，已在报告中标记并保留原始输出。

````````
<!-- END IMPORT SIGN/docs/qwen_offline_diagnostic.md -->

</details>

## 2026-10-26T02:27:02+08:00 — MIGRATION-IMPLEMENTED：四文档落地与发布兼容调整

- 工作目录：`/scratch/e1538633/liuyi`。实际创建根 STATUS、RUNBOOK、WORKLOG，收敛根 AGENTS；已迁移后删除根 CONTEXT、两个活动项目 AGENTS，以及 SIGN/docs 下两份旧研究／环境文档。三个项目 README 保留并改为四文档导航。
- 研究历史：原 SIGN 研究正文按字节导入 MIGRATION-BASELINE 的代码块，保留原 SHA256；未手工改动已发布研究目录、冻结标注或导航源码。
- 修改 `SIGN/scripts/publish_relative_diagnostic.py`：从根收集四文档到生成计划的 workspace/；旧 code/AGENTS 与两份 code/docs 从现有归档按原字节保留，不再读取已删除的本地路径；生成入口指向新文档并标明历史说明。
- 修改 `SIGN/scripts/research_publication.py`：仅允许四个明确的 workspace 文档更新；已发布 WORKLOG 必须保持原字节前缀，只可追加。原人工证据保护与归档哈希检查保持。
- 添加针对缺失源文件、历史说明保留、日志追加／改写／截断、状态可更新且其他证据不可覆盖的 CPU 回归检查。尚未执行，结果在后续条目追加。
- 未启动推理、采集或训练；未写发布资料、提交或推送。下一步执行本地链接／哈希检查、CPU 回归和只读构建预览。

## 2026-10-26T02:29:52+08:00 — MIGRATION-VERIFIED：验证结果与保留的发布阻塞

- 已执行（工作目录 SIGN）：`/scratch/e1538633/liuyi/envs/sign/bin/python scripts/test_research_publication.py`，17 项通过，运行报告为 OK。覆盖真实 64 请求证据、原人工记录保护、只读预览、旧快照保留、根文档缺失、WORKLOG 追加／改写／截断及状态更新范围。
- 已执行（工作目录 liuyi）：检查根目录恰有 AGENTS／STATUS／RUNBOOK／WORKLOG 四份 Markdown，确认五份迁移源已删除；七份活动文档的本地 Markdown 链接有效，三个相关仓库 `git diff --check` 通过。
- 哈希验证：迁移前记录的 965 个研究归档与导航源码文件 SHA256 全部不变；从 WORKLOG 导出 MIGRATION-BASELINE 中的原研究正文，与迁移前原文逐字节相同。
- 构建 debug：只在内存中构建完整资料计划，先检查所有计划链接、四根文档与三份旧快照的字节一致性，再调用原有 check-only 终检。前述检查通过；终检仍报 `Existing evidence/review would change: history/human_review2_notes.md; preserve it and version the change separately.`，与已知阻塞一致。未放宽、跳过或修复该人工证据保护，也未写入发布目录。
- 结果：四文档迁移完成；发布脚本不再依赖被删除的本地 AGENTS／研究／环境说明，旧归档保留。STATUS 已改为当前完成状态，WORKLOG 的既有条目保持原样，仅在末尾追加。
- 未完成事项：后续发布需先核对 val_hard/episode_013 的人工汇总差异并单独版本化，处理发布工作树的已有文档变更；未查询远端或队列。本轮未提交、推送、训练、采集或模型推理。四文档发布副本将在下一次成功发布时生成，目前根文件保存在本地。

## 2026-10-26T02:36:35+08:00 — GIT-ORGANIZATION-AUDIT：远端盘点与默认推送要求

- 用户要求先整理当前项目，并明确：默认 push 到 yiichu03 的 GitHub；只有用户特别指定学长的 GitHub 仓库时才考虑 upstream。此要求作为后续持久规则。本轮先整理／核对配置，不执行 push。
- 工作目录 liuyi。已执行四个目录的 status、remote -v、branch -vv、worktree list 和配置查询；SIGN 与 SRU 为独立仓库，研究工作树与 SRU 共用 Git 配置。
- 已核对远端：SIGN origin 为 https://github.com/yiichu03/SIGN.git，upstream 为 git@github.com:Zichen-Yan/SIGN.git；SRU origin 为 git@github.com:yiichu03/SIGN-SRU.git；Habitat origin 为 https://github.com/facebookresearch/habitat-lab.git。
- GitHub 连接的只读仓库查询确认：yiichu03/SIGN 为 public，yiichu03/SIGN-SRU 为 private，两个仓库均报告 push 权限；Zichen-Yan/SIGN 为 public，当前 GitHub 连接报告 pull 权限、无 push 权限。这不等同服务器 Git 凭据已通过实际推送验证。
- 观察到的错误：SIGN 的 `git rev-parse --abbrev-ref --symbolic-full-name @{push}` 报 `fatal: cannot resolve 'simple' push to a single destination`。进一步按键查询发现 remote.pushDefault 与 branch.main.pushRemote 已为 origin，而 push.default 未设置；main 跟踪 upstream/main。早先大小写敏感的正则查询漏显了已有 pushDefault／pushRemote，改为逐键核对后确认。
- 处理方案：SIGN 与 SRU 设置仓库本地 remote.pushDefault=origin、push.default=current，并为现有分支明确 pushRemote=origin；不修改 SIGN 的 upstream/main 取更新关系，不改 remote 地址。Habitat 保留官方依赖 origin，将 push.default 设为 nothing，避免默认向第三方发布。
- 本轮同时把研究工作树 README 收敛为资料导航，SRU 完整运行说明继续保存在 SIGN-SRU/README。操作前备份三份 Git config、四根文档与研究入口 README，保存 965 个归档／导航源码 SHA256：/tmp/liuyi-git-organization-othzrizi。

## 2026-10-26T02:38:44+08:00 — GIT-ROUTING-DEBUG：配置写入与引用解析检查

- 已执行三个仓库的本地 Git 配置更新：SIGN／SIGN-SRU（含共享工作树）默认 remote 为 origin、push.default=current、现有分支 pushRemote=origin；Habitat push.default=nothing。remote 地址、SIGN upstream/main 跟踪关系和本地分支 HEAD 均未改。
- 研究工作树 README 已从重复安装说明收敛为资料／源码／配置导航；完整 SRU 安装运行说明仍在 SIGN-SRU/README。
- 第一轮验证失败于检查脚本对 `%(push:remoteref)` 的断言：Git 2.43.5 在没有显式 remote push refspec 时该字段为空，不能据此断言实际 push 目标未配置。后续改用有效配置、push remote 与 @{push}／push:short 检查。
- 进一步只读核对确认 SIGN 的 origin 抓取映射正常，但本地 refs/remotes/origin 下没有引用，配置更新后 @{push} 报 unknown revision；SRU 两个分支均解析到 origin 的同名分支。
- 下一步只抓取 yiichu03/SIGN 的 main 到远端跟踪缓存，以验证缺失引用；不合并、不重置，不改变本地 main 或现有源码。此项是 Git 配置核验所需的抓取，不是推送。

## 2026-10-26T02:40:58+08:00 — GIT-ORGANIZATION-VERIFIED：默认 yiichu03 推送与项目入口整理完成

- 实际执行 `GIT_TERMINAL_PROMPT=0 timeout 45s git -c credential.interactive=never -C SIGN fetch --no-tags origin refs/heads/main:refs/remotes/origin/main`，成功建立 origin/main 缓存。只抓取指定用户仓库主分支，没有合并、移动本地分支或修改导航源码。
- fetch 后 origin/main 为 dad87fe225a4dc1073787d8d2cc83f67e61c0a9d，本地 SIGN main 仍为 21274be425a7de28c86c8005fbb234ad5f0c65f6；`git rev-list --left-right --count main...origin/main` 为 0／1。本地比用户远端落后 1 提交，后续推送前需保留现有修改后处理，不能强推。
- 核验三份活动目录：remote.pushDefault=origin、push.default=current；各本地分支 pushRemote=origin，有效 origin push URL 都为 yiichu03；SIGN 与 SRU 的 main 均解析到 origin/main，研究工作树解析到 origin/docs/qwen-reward-review-20261013。
- 已更正验证方法：用 `%(push:remotename)` 与 `%(push:short)` 核对目标，ROOT RUNBOOK 的查询模板同步更新；不再将缺省为空的 push:remoteref 当作失败。
- 用户偏好已写入根 AGENTS／STATUS／RUNBOOK：常规 push／GitHub 同步走用户 origin，只有用户明确指定学长仓库时才考虑 upstream。SIGN 保留 upstream/main 的取更新关系；Habitat 保留官方 origin 并关闭无目标默认 push。所有配置均为仓库本地；SRU 研究工作树共享配置。
- 研究工作树 README 已收敛为 14 行资料导航，移除重复安装说明；完整运行说明继续在 SIGN-SRU README。根文档仍为四份，无新建交接文档。
- 验证通过：默认目标与有效 URL、取更新关系、本地 HEAD 不变、Habitat 依赖设置、相关仓库 git diff --check、七份活动文档链接、WORKLOG 原字节前缀，以及 965 个归档／导航源码 SHA256。
- 未执行 commit、push、merge、rebase、训练、模型推理或研究资料写入；原人审汇总差异仍保留。GitHub 元信息和连接权限已查询，但服务器推送认证尚未通过真实 push 测试。下次代码同步注意 SIGN 落后 1 提交，下次资料发布仍需先核对已登记的人审差异。

## 2026-10-26T02:46:45+08:00 — BRANCH-RELATION-CLARIFIED：工作树分支映射与上游实时对比

- 用户询问“同名分支”是否指两个目录的名字，以及 SIGN 比 origin/main 落后一个的含义和相对学长仓库的状态。
- 已执行 branch --show-current、worktree list、HEAD／@{upstream}／@{push} 查询：SIGN-SRU 目录检出 main，默认推送 origin/main；SIGN-SRU-reward-review 目录检出 docs/qwen-reward-review-20261013，默认推送同名研究分支。两者共享 yiichu03/SIGN-SRU 仓库，目录名不是分支名。
- 对 origin 与 upstream 实际执行只读 `git ls-remote --heads <remote> main`，并用公开 HTTPS 对学长仓库补充核对；均返回 dad87fe225a4dc1073787d8d2cc83f67e61c0a9d。本地 SIGN main 仍为 21274be425a7de28c86c8005fbb234ad5f0c65f6。本地 upstream/main 缓存仍在旧提交，不能用该缓存推断学长 GitHub 当前状态。
- 已用 git show --stat 和 git diff main..origin/main -- README.md 核对差异：唯一新增提交 dad87fe，作者日期 2026-10-14T13:28:02+08:00，标题 update readme，仅从 README 删除一行访客计数徽章；没有修改导航源码。
- 结论：“落后 1”指一条已提交历史记录，不是一个分支，也不包含本地尚未提交的自定义代码／研究脚本。当前用户与学长的 SIGN main 相同；本地提交基线相对两者都少这一个 README 提交。
- STATUS 已补充准确映射与差异性质；没有 fetch 新引用、切换分支、合并、提交或推送。WORKLOG 只在末尾追加。

## 2026-10-26T02:55:26+08:00 — README-FF-START：同步用户远端的 README 提交

- 用户授权把 README 的上游小改同步到本地，并询问尚未提交的 policy／trainer／研究脚本位于哪里。目标为 yiichu03/SIGN 的 origin/main，不推送本地研究修改。
- 工作目录 liuyi；已核对 SIGN 的待提交文件共 51 个，暂存区为空，完整备份与 SHA256 位于 /tmp/sign-readme-ff-eu14gcr6。
- 计划只临时 stash README，使用 --ff-only 接纳远端已有提交，然后恢复本地 README 研究入口；policy、trainer、45 个脚本及其他新增文件保留原样。

## 2026-10-26T02:55:28+08:00 — README-FF-VERIFIED：main 与 origin/main 已同步

- 已执行只含 README 的临时 stash、git merge --ff-only origin/main、stash apply，保留本地研究入口，仅接纳远端删除访客徽章的变化。
- SIGN main 已从 21274be 快进到 dad87fe，与 yiichu03/SIGN origin/main 相同，领先／落后均为 0。没有新建代码提交或 push。
- 原有 51 个待提交文件的路径／Git 状态保持；除 README 的预期一行变化，其余 50 个文件 SHA256 全部一致。暂存区为空，git diff --check 通过；本轮临时 stash 在验证后清理，其他 stash 不动。
- 代码位置：SIGN/src/policy.py、SIGN/src/trainer.py；新增轨迹模块 SIGN/src/trajectory_diagnostic.py；SIGN/scripts 下 45 个脚本（29 Python、15 PBS、1 shell），另有 SIGN/.gitignore、constraints-hm3d.txt 和 README 的本地修改。
- SHA256、迁移前内容和结果记录保存在 /tmp/sign-readme-ff-eu14gcr6；根 STATUS 随后更新。SIGN-SRU 及研究工作树的源码／分支不在本次同步范围。

## 2026-10-26T02:57:25+08:00 — README-FF-STATUS：同步状态与文件位置登记

- 额外执行只读 fetch upstream main 到 refs/remotes/upstream/main，修正之前缓存停留在 21274be 导致 status 显示“领先上游一提交”的现象；没有向学长仓库 push。最终 HEAD、origin/main、upstream/main 全部为 dad87fe225a4dc1073787d8d2cc83f67e61c0a9d。
- 再次核对除 README 外的 50 个待提交文件哈希、空暂存区和原 stash 栈均保持；git diff --check 通过。根 STATUS 已移除 README 落后待办并登记 policy／trainer／轨迹模块／45 脚本的确切目录与用途。
- 这里的未提交主要针对 SIGN 本身；SIGN-SRU 仅有 README 文档变更，研究工作树只有 README 与旧 AGENTS 删除，未修改其 SRU 策略或 trainer。未新增研究代码提交或 push。

## 2026-10-26T03:08:18+08:00 — PHASE-BRANCH-PLAN：归档 phase1 并建立干净 phase2

- 用户授权将 SIGN 全部尚未提交的代码／脚本归档并推送 origin 新分支，前缀 phase1；随后从 origin/main 新建 phase2/exploration-reward-try 并让 SIGN 默认检出该分支。用户进一步要求 SRU main 保留学长最新基线，已有工作归档到与 SIGN 同名的 phase1。
- 采用统一分支名 phase1/imagenav-qwen-diagnostics，概括 ImageNav 轨迹采集、Qwen 独立／组内／成对诊断、绘图汇总、PBS 和资料发布工具。SIGN 待保存 51 个文件；SRU main 待保存一个 README 修改，研究工作树有 README 修改与旧 AGENTS 删除。
- 实时核对：SIGN origin/main 为 dad87fe，SRU origin/main 为学长 Zichen-Yan 署名的 ba3bb4a；目标 phase1／phase2 远端分支尚不存在。SRU 现有研究分支相对 main 无 src／exp_config 差异。
- 计划保留既有 SRU 研究分支历史：先在 SRU phase1 提交 main 工作树的入口修改，再合并既有研究历史并纳入研究工作树的入口整理；SRU main 分支不前移，最终两个工作树分别停在 main 与 phase1。
- 预检：32 个 Python 文件按 Python 3.8 语法解析通过，16 个 Shell／PBS 文件 bash -n 通过；待提交文本约 318KB，没有新增模型／数据文件。CPU 发布回归检查单独记录结果。
- 备份：/tmp/liuyi-phase-branches-wwmpkdrn，包含三个目录全部本地待保存内容、四根文档、Git 配置和 923 个研究归档哈希。
- phase2 按用户要求使用 origin/main 基线，不自动继承 phase1 工具。结果、场景和 Python 缓存使用 Git 本地 info/exclude 保持忽略，切换分支不删除这些本地材料。

## 2026-10-26T03:09:54+08:00 — PHASE1-SIGN-PUSH-RETRY：HTTPS 推送失败，使用同仓库 SSH

- 本地归档提交 f2b4bb4b18422ff0da9ada159a0456dc0c84a1e0 已通过检查；直接向配置的 origin HTTPS push 失败。
- Git 输出：
```text
fatal: could not read Username for 'https://github.com': terminal prompts disabled

```
- 使用已有 SSH 身份重试同一 yiichu03/SIGN 仓库与同一新分支，不更换 owner、不强推，也不修改永久 remote 地址。

## 2026-10-26T03:10:00+08:00 — PHASE1-SIGN-PUBLISHED：SIGN 阶段一归档完成

- 32 个 Python 语法、16 个 Shell／PBS 语法与 17 个 CPU 回归检查通过。
- 51 个原有本地文件以原内容提交到 phase1/imagenav-qwen-diagnostics，提交 f2b4bb4b18422ff0da9ada159a0456dc0c84a1e0；所有文件逐个与备份哈希核对一致，SIGN 工作树干净。
- 已普通推送到 yiichu03/SIGN 的同名 origin 分支并核对远端 SHA。传输方式：one-command SSH override to same origin repository。未更新 origin/main 或 upstream，也没有运行实验。
- 后续从最新 origin/main 建立 phase2/exploration-reward-try；尚未切换。

## 2026-10-26T03:12:12+08:00 — PHASE1-SRU-MERGE-DEBUG：处理暂存中的旧 AGENTS

- SRU phase1 的入口提交 988f4b2 已保存原 main README 修改，随后合并原研究历史时仅 README 冲突，已采用备份的 14 行研究导航解决。
- 普通 git rm AGENTS.md 被拒，原因是该文件是本次合并新增并已暂存的文件，不是未保存用户修改。没有强制删除或规范化档案；合并保持待完成。
- 核对该文件与原研究提交中的内容一致后，仅从索引移除并删除这份已迁移的旧入口，再继续哈希验证和归档提交。

## 2026-10-26T03:12:20+08:00 — PHASE1-SRU-COMMITTED：main 基线与研究历史归档完成

- 原 main README 修改精确保存于提交 988f4b231b322f9e05f6f54ce6c239251846300f；既有研究分支 663b0f98dfae45a3b7249ea460e839f3a4160f86 的完整历史作为合并父提交保留。最终 phase1 提交 aa570383d6a237dec11bf24beaa9f1f03e1ffc24 保存精简研究入口和旧 AGENTS 的删除。
- 923 个研究归档 SHA256 保持；SRU src／exp_config 相对 main 无差异。没有规范化历史 CSV 或更改冻结证据。
- SIGN-SRU 已回到 main @ ba3bb4a 且干净；SIGN-SRU-reward-review 已检出 phase1/imagenav-qwen-diagnostics 且干净。原研究分支仍为 663b0f98dfae45a3b7249ea460e839f3a4160f86，未被改写。SRU phase1 尚待推送。

## 2026-10-26T03:13:55+08:00 — PHASE1-SRU-PUBLISHED：同名归档分支推送完成

- 更新 phase1 的研究 README，准确标明归档分支与旧发布脚本仍锁定原 docs 分支的边界；本次未运行旧资料同步，未绕过人工证据冲突检查。
- 已将 SRU 的 phase1/imagenav-qwen-diagnostics 普通推送到 yiichu03/SIGN-SRU，远端核对为 dbf6d3cc437cd5c673648ceac6fa2ddad2ee1656；main 仍为学长 ba3bb4a，原研究分支保留。
- SIGN phase1 已通过 SSH 成功推送；其 HTTPS 推送缺少非交互凭据。为使后续默认 push 可直接使用已验证身份，将 SIGN origin 的 push URL 明确设为 git@github.com:yiichu03/SIGN.git，fetch URL 仍为原 HTTPS，owner 不变。SRU 原有 SSH 地址不变。
- 两仓库均未向 main 或学长 upstream 推送；接下来建立 SIGN phase2。

## 2026-10-26T03:15:35+08:00 — PHASE2-CHECKED-OUT：SIGN 默认进入新阶段基线

- 通过 GitHub 连接在 yiichu03/SIGN 创建远端 phase2/exploration-reward-try，明确基于已核对的 origin/main @ dad87fe；随后 fetch 该引用并在 SIGN 本地创建跟踪分支、设 pushRemote=origin。
- SIGN 当前检出 phase2/exploration-reward-try，HEAD 与 origin/main、origin/phase2/exploration-reward-try 完全一致，工作树干净；没有将 phase1 的诊断实现合入该基线。
- 原 51 个 SIGN 文件均能从已推送的 phase1 提交 f2b4bb4b18422ff0da9ada159a0456dc0c84a1e0 按原哈希读取；当前 data／results 目录保留，info/exclude 跨分支忽略实验材料。
- SIGN-SRU 当前为干净 main；研究工作树当前为干净同名 phase1。923 个研究归档哈希均不变。两仓库 GitHub 默认分支 main 未改，“默认进入 phase2”指本地 SIGN 目录当前检出的工作分支。
- 尚未实现 exploration reward，也未运行 GPU 实验或策略训练；本轮完成的是归档、推送与分支布局。根状态和运行手册随后按这一布局更新。

## 2026-10-26T03:20:28+08:00 — PHASE-ARCHIVE-VERIFIED：两个 phase1 与当前 phase2 最终核对

- 远端再次核对：yiichu03/SIGN main 和 phase2/exploration-reward-try 均为 dad87fe，phase1/imagenav-qwen-diagnostics 为 f2b4bb4b18422ff0da9ada159a0456dc0c84a1e0；yiichu03/SIGN-SRU main 为 ba3bb4a，同名 phase1 为 dbf6d3cc437cd5c673648ceac6fa2ddad2ee1656，旧 docs 研究分支仍为 663b0f9。
- 本地最终布局：SIGN 当前 phase2；SIGN-SRU 当前 main；SIGN-SRU-reward-review 当前 phase1。三处工作树均干净，分别跟踪正确 origin 分支。GitHub 默认分支 main 未修改，未向学长 upstream 推送。
- 保存完整性：SIGN 51 个原待提交文件在 phase1 中逐个哈希一致；SRU 两个工作树原 README 编辑分别能从历史提交 988f4b2 与 aa57038 完整恢复，最后的 phase1 README 另明确了归档分支。923 个历史研究文件字节不变，SRU src／exp_config 保持作者 main 基线。
- 32 Python／16 Shell-PBS 语法检查与 17 CPU 回归通过；未运行 GPU 模型或 PPO 训练。SIGN 当前 phase2 未包含 phase1 新工具与诊断修改，是 origin/main 的干净基线。
- 根 AGENTS／STATUS／RUNBOOK 已反映分支职责、阶段一工具的读取／运行条件、原发布脚本的分支保护与 SSH 推送设置；四根文档的本地链接与 WORKLOG 既有前缀检查通过。根文档仍未自动纳入这次子仓库代码提交，已在 STATUS 明确。
- 数据、结果、环境和模型留在原处；本地 info/exclude 保证跨分支忽略实验材料。阶段一旧资料发布的人工汇总差异继续保留，没有通过本次归档重跑或修复。
- 备份与前后核对记录：/tmp/liuyi-phase-branches-wwmpkdrn。用户本轮要求的归档、推送、主分支保留与默认工作分支切换已完成；后续按用户任务在 SIGN phase2 推进探索奖励。

## 2026-10-26T03:34:26+08:00 — GIBSON-BASELINE-PREP：原版 Gibson 复现数据与环境核对

- 用户将关注点转回 SIGN，授权先梳理 pipeline、按 README 下载与放置 Gibson、用现有 checkpoint 评估，然后在不修改代码和奖励的前提下尝试从零训练并观察训练曲线／最终性能。当前仍在 phase2 @ dad87fe，未移入 phase1 修补。
- 按 FGPrompt 官方 README 核对 episode 与场景数据分别准备；使用现有 downloads/fgprompt_datasets.zip 解压 Gibson 的 74 个 gz 文件到 SIGN/data/datasets/imagenav/gibson/v1/，得到 train 645000 条／72 场景，val 4200 条／14 场景。没有覆盖不同内容的已有文件。
- 86 个期望场景的 glb／navmesh 都尚未存在；官方 Gibson 数据 README 的下载入口先要求许可表单 https://forms.gle/36TW9uVpjrE1Mkf9A 。用户已回复尚未获取，会自行填写；已给出链接并说明获取 Habitat-sim 版本。等待用户提供授权下载链接／本地路径，未代填或绕过许可。
- 数据与文件哈希清单：manifests/gibson_reproduction_20261026.json；SIGN 已跟踪源码／checkpoint 哈希快照与配置探针目录：logs/gibson_reproduction_20261026。SIGN 源码保持原样。
- 配置事实：README 训练组合为 4 环境×512 rollout、3e8 步，eval 组合为 6 环境、500 步上限；论文报告 8 环境×256 rollout、300M 步，Gibson 72／14 场景、SR 86.3%、SPL 53.3%。先保留 README 合并配置并记录差异，不偷偷改训练设置。
- 环境错误：现有 sign 为 torch 1.11.0+cu113，CPU 实测 Normal.mode 抛 AttributeError；原 SafeNavNetPolicy 的确定性评估直接读取 mode。官方 PyTorch v2.0.1 源码已有 Normal.mode 属性；计划使用隔离的兼容环境，不修改 SIGN 源码或 monkeypatch。旧 sign 环境保留。
- 现有 nav_model.pth 仅含 state_dict（121 个张量键），没有 config／extra_state，不能从该文件确认训练步数；从零训练的当前 _init_train 没有加载 nav checkpoint 或恢复优化器。
- 已阅读 Vanda 集群手册；无本用户排队作业。hpc project 提示需用户自行 amgr login，未获取／输入密码。GPU 任务将在计算节点使用 auto／autox 与既有授权项目；当前等待场景前不启动空跑评估／长训练。

## 2026-10-26T03:49:36+08:00 — GIBSON-PUBLIC-DOWNLOAD：公开来源核验与场景准备完成

- 用户追问现有 Habitat-Sim 场景，并要求先查 GitHub／开源社区是否能直接下载 Gibson、避免等待申请。已确认旧数据为 HM3D v0.2 val 100 场景，不能替代 Gibson；本轮没有重新下载 HM3D。
- 搜索官方 Gibson／Habitat 文档、FGPrompt、Object-Goal-Navigation、NAVER Kinaema、AllenAI embodied-clip、AudibleLight、habitat_sim2real、社区复现文章与 Hugging Face。HF 的 imagenav_gibson 等仅含任务或派生数据；ToughStoneX/gibson 仍为 manual gated，没有下载优势。原始来源清单保存在 logs/gibson_reproduction_20261026/download_source_research.json。
- 在两个社区仓库找到 Meta 文件服务器公开直链。实测小包 https://dl.fbaipublicfiles.com/habitat/data/scene_datasets/gibson_habitat.zip 返回 HTTP 200、1468698464 字节；大包同目录 gibson_habitat_trainval.zip 返回 HTTP 200、10833075327 字节。未使用登录、token 或隐藏入口。公开可访问不代表免除协议，官方说明与 AudibleLight 脚本仍要求用户协议；没有代签或代填表单。
- 使用 HTTP Range 读取 ZIP 目录而非先下载 10.83 GB：小包 88 对 glb／navmesh，大包 492 对；SIGN 所需 72 train + 14 val 全覆盖，172 个所需文件大小与 CRC 在两包一致。AudibleLight 将小包注释为 4 scenes，与实测不符，未采信；未运行第三方下载脚本的 navmesh 清理选项。证据见 public_source_probe.json、public_archive_coverage.json、两份 directory.json。
- 已通过 curl 下载小包到 downloads/gibson_habitat.zip。官方 MD5 35f274a781eba9ed1b77feba50d040da 实测一致；SHA256 09639602d7427177bca25ea5352a041f518b8a3e76230441f4e162e1ec244d51。解压 176 个文件到 SIGN/data/scene_datasets/gibson，逐个 CRC 由 zipfile 校验，未覆盖不同已有内容。场景和任务清单已更新，所需 86 场景零缺失。
- 输入 guard --split all 实际通过：episode 哈希、场景文件存在性、44 个原版跟踪文件／checkpoint 哈希全部保持；SIGN phase2 工作树干净。准备的五个 PBS 已通过 bash -n，smoke 与完整训练输出分开；未提交 GPU 作业。TensorBoard 导出器已准备，仅读取真实事件，未产生训练曲线。
- 环境：独立 envs/sign-baseline 正通过 conda --clone --offline 克隆旧 sign；torch 2.0.1+cu117、torchvision 0.15.2+cu117、numpy 1.24.4 及完整 wheel 依赖已下载到 downloads/sign-baseline-wheels。此刻 clone 仍在 Executing transaction，不视为可用环境；旧 sign 没有被升级。此前 Normal.mode 错误通过环境版本解决的方案尚待验证。
- CPU 独立 navmesh 加载检查正在执行；实际渲染与原策略 GPU 评估尚未完成。RUNBOOK 已记录下载入口、数据分层、原 pipeline、300M 配置与论文差异、无原生断点续训及 168 小时队列限制。STATUS 的下一步已改为先原版 Gibson 复现。

## 2026-10-26T03:50:04+08:00 — GIBSON-NAVMESH-CPU：88 个导航网格可加载

- 使用原 envs/sign 的 Habitat-Sim 0.2.2 PathFinder，在 CPU 上逐个加载全部 88 个 .navmesh，全部返回成功且 navigable_area 大于零；未初始化渲染器／GPU。结果保存于 logs/gibson_reproduction_20261026/navmesh_cpu_validation.json。
- 旧 navmesh 载入时提示 NavMeshSettings aren't present, guessing that they are the default；这是旧包元数据缺失提示，文件加载实际成功，没有重建或改写 navmesh。GPU 渲染与实际 episode 运行仍待验证。
- conda 克隆仍在执行事务，兼容 wheel 安装任务已设置为等待克隆进程退出且 Python／conda history 存在后才启动；只写 envs/sign-baseline，安装日志为 env_install.log。

## 2026-10-26T13:38:43+08:00 — GIBSON-README-CONFORMANCE：数据目录与原版 loader 核对

- 按用户要求逐项对照 SIGN/README.md 第二节与原版 dataset 配置。train／val 路径、glb／navmesh 布局符合 README；任务总数仍为 645000／4200，场景需求为 72／14，所需场景全部存在。
- 用原 envs/sign 和原 src.dataset.ImageNavDatasetV1 实际加载：发现 train 72 场景，抽取 Adrian 的 9000 条任务成功；val 14 场景的全部 4200 条任务加载成功，所加载 episode 的 scene_id 路径和目标字段均有效。证据见 logs/gibson_reproduction_20261026/original_dataset_loader_validation.json。没有声称这次已逐条通过原 loader 加载全部 645000 条训练任务。
- val 不含 content 子目录是合法布局，全部 episode 在 val.json.gz；train 使用 train.json.gz 入口与 72 个 content 文件。基础配置中的 Ackermanville 是初始占位场景，原 custom_habitat_env 在建仿真器前用当前 episode.scene_id 替换，实际所需场景以任务引用为准。
- 独立环境 clone 与 torch／torchvision wheel 安装已成功退出，原入口导入与 checkpoint CPU 兼容探针进行中；GPU 渲染和完整评估还没有完成，数据准备完成不等于已经复现论文指标。SIGN 跟踪文件仍无修改。

## 2026-10-26T13:39:20+08:00 — GIBSON-RUNTIME-READY-SMOKE-QUEUED：兼容环境通过并提交首个 GPU 检查

- envs/sign-baseline 的 torch 2.0.1+cu117／torchvision 0.15.2+cu117／Habitat-Sim 0.2.2 已通过 CPU 探针：原 run_sim 入口可导入，Normal.mode 可用，原 nav_model.pth 的 121 个 state_dict 键可读取。torch 模块实际路径位于新环境。证据 baseline_runtime_cpu_validation.json，包快照 baseline_pip_freeze.txt。没有修改 SIGN 源码。
- 按此前用户授权的现有 checkpoint 评估安排，执行 qsub logs/gibson_reproduction_20261026/pretrained_eval_smoke.pbs，返回 1494494.stdct-mgmt-02。1 环境、10 episode，仅验证完整仿真与导航管线，不作为完整 Gibson 指标。
- qstat 实测 job_state=Q，autox 路由至 batch_gpux，project=CFP04-SF-109 接受。调度器将申请的 8 CPU／64 GB 规范为 36 CPU／240 GB／1 A40，walltime 2h；当前等待 node_pool 资源。未重复提交或更换项目，完整评估／训练未提交。下次推进先查该任务和日志。
- 提交记录与脚本 SHA256：logs/gibson_reproduction_20261026/pretrained_smoke_submission.json。数据符合 README 的结论以布局、任务引用、完整性和原 loader 验证为依据，GPU 成功与最终性能另待作业结果。

## 2026-10-26T13:45:12+08:00 — GIBSON-TRAIN-SUBMISSION-PROJECT：个人项目路由限制

- 用户明确授权配置评估／训练环境并提交实验，可使用共享 CFP 或个人预算。原评估 1494494 已进入 Running，A40 驱动 575.57.08、torch 2.0.1+cu117、Habitat-Sim 0.2.2 的 CUDA 检查与场景初始化通过。
- hpc project／project-usage 仍要求 amgr login，未读取到实际余额；手册为每年 1000 GPUhr、10000 CPUhr，不能当作当前剩余额度。
- 训练 smoke 从 4096 步扩大到 40960 步（20 次 4×512 rollout），保持 PPO／MRQ／奖励配置，仅缩短总步数并提高日志频率；输出 scratch_smoke，与正式从零训练分离。添加 checkpoint 已存在保护和真实 TensorBoard 曲线导出。
- 首次用 personal-e1538633 + autox 提交被调度器拒绝：Express queue not allowed for your project, Please submit to auto queue. 该次未创建作业。已按返回要求将个人短训练路由改为 auto 后重试；正式任务仍优先 CFP。未重复提交同一有效作业。

## 2026-10-26T13:48:26+08:00 — GIBSON-EVAL-TRAIN-PIPELINE-SUBMITTED：评估通过 smoke，训练链已提交

- 现有 checkpoint smoke 1494494.stdct-mgmt-02 已 Exit_status=0，耗时 1m23s；10 episode 成功率 0.8、SPL 0.4709。只作为管线验证，不作为完整基准结果。实际 A40 CUDA、Habitat 渲染与原策略确定性动作均已验证。
- 完整现有模型评估 1494521.stdct-mgmt-02（CFP04-SF-109，autox→batch_gpux，6 环境、4200 episode、12h）依赖 smoke 成功，现已运行。输出 pretrained_full；未覆盖 smoke。
- 个人短训练 1494520.stdct-mgmt-02（personal-e1538633，auto→batch_gpu，4×512、40960 环境步、2h）已接受并排队。个人不允许 autox 的拒绝与修正见前条；此轮无法通过 hpc project 查询剩余额度，未宣称实际仍余 1000h。
- 正式从零训练 1494529.stdct-mgmt-02（CFP04-SF-109，autox，300M 步、168h）已提交，依赖短训练 1494520 和完整现有模型评估 1494521 均成功。初始状态 H 是 PBS 依赖等待，不是需用户批准。输出 scratch_full，不承接 scratch_smoke 权重。
- 训练后完整评估 1494531.stdct-mgmt-02（CFP04-SF-109，autox，4200 episode、12h）已提交，依赖正式训练 1494529 成功，使用 scratch_full/ckpts/latest.pth；评估其余参数与 README 组合一致，包括默认 safety_model 配置。原仿真策略 act 未应用 USL 修正。
- 原算法／源码／配置文件不修改。新增外部 training_preflight.py 读取真实短训 TensorBoard 与 checkpoint，要求20更新完成、关键损失与权重有限，并用最后10次更新的中位步速估计300M耗时，加15%裕度与15分钟启动时间。若超过168h，长任务在训练开始前退出并保存 training_preflight_result.json，后续评估不会释放。估计明确注明 MRQ 在50M停用可能加速、场景混合也影响速度，不声称精确ETA。
- 两次训练结束后通过外部 exporter 导出 CSV／PNG；未模拟曲线。新 preflight 按Python3.8语法检查通过，PBS bash -n 通过，preflight 的真实数据运行待短训完成。
- 检查原 BaseRLTrainer.should_checkpoint 发现严格小于阈值且完成时不强制保存：短训 num_checkpoints=2 的 latest 可能早于40960，正式100 checkpoints也可能早于300M。训练完成由TensorBoard最大step判定，评估模型步数另读checkpoint extra_state.step，不能混为同一个数字。preflight 未错误要求短训 latest 恰等于40960。
- 调度器将每个1×A40申请规范为36 CPU、240GB主存；正式训练最长168 GPUhr，个人短训最长2 GPUhr，均为申请上限而非实际消耗。项目接受提交不等于已查询出余额。作业状态、项目、依赖、资源与脚本哈希见 submitted_experiments.json。

## 2026-10-26T13:53:55+08:00 — HABITAT-GS-PLAN：新仿真分支范围与隔离方案

- 用户授权为 SIGN 新开分支尝试 Peng Sida 团队 ECCV 2026 Habitat-GS 的 ImageNav，先分析方案、复用本地数据、缺失时下载，保持目录整洁。已读四份根文档及本日 Gibson 记录，未通读历史补录。
- 已执行只读核对：SIGN phase2 @ dad87fe 干净，只有一个 SIGN 工作树；qstat 显示 1494521 正在运行，1494520 排队，1494529／1494531 等依赖。决定从 origin/main @ dad87fe 新建 experiment/habitat-gs-imagenav 和 SIGN-habitat-gs 工作树，避免改变已有作业路径。
- 已查官方项目／论文／README 与数据说明：https://github.com/zju3dv/habitat-gs 、https://arxiv.org/abs/2604.12626 、https://huggingface.co/datasets/RukawaY/gs_scenes 。git ls-remote 实测 HEAD=cb01b2fdf850ce3cab28ad00461a68ac7719f23f。官方静态 ImageNav 支持明确；动态 avatar 扩展先不纳入。
- 兼容风险：Habitat-GS pyproject 要求 Python≥3.9、NumPy≥2.0，旧 SIGN 环境是 Python3.8／NumPy1；先检查源码及可行的独立环境方案，不修改现有环境和 habitat-lab。不把 metadata 兼容或导入成功当成渲染已通过。
- 本地 rg 未发现 .gs.ply／.3dgs.ply；已有 Gibson／HM3D mesh 不能替代 GS。官方数据允许按文件取用，先准备一个 val 场景与对应官方 ImageNav episode；无需下载全量约95GB。
- 已遇并恢复的只读失败：沙箱 qstat cannot connect to server、git Could not resolve host；按权限升级后查询成功。web 打开 HF 页面 Internal Error，改读官方 resolve/main/README.md 成功。用户随后启用完整权限。无安装、下载大资产或 GPU 新任务已执行。
- 具体步骤和目录职责已写 STATUS；唯一原始日志目录 logs/habitat_gs_20261026，唯一数据清单 manifests/habitat_gs_20261026.json。先小样本闭环，不预先启动大规模训练；不存在新总结文档。

## 2026-10-26T13:57:47+08:00 — HABITAT-GS-ASSETS：隔离分支与官方单场景数据就绪

- 实际创建 SIGN-habitat-gs 工作树和 experiment/habitat-gs-imagenav 分支，基于 origin/main @ dad87fe；解除自动继承的 origin/main upstream，pushRemote 仍指 origin。原 SIGN phase2 保持原位。第三方 habitat-gs 浅克隆到 cb01b2f，关闭默认 push；所需渲染／绑定子模块仍在固定 SHA 初始化。
- 已执行 scripts/habitat_gs/prepare_data.py：固定官方 HF revision ea6453855938dd3d4395c4c449fedefb7e6603b7，下载 scene56 的 .gs.ply（111314377字节）、navmesh（99900字节）、官方 val 入口与100条 scene56 ImageNav、原评估配置和 val 场景配置，总计6个文件。LFS SHA256／非LFS Git blob SHA1与官方元数据全部一致；本地 SHA256 见 manifests/habitat_gs_20261026.json。未生成或更改任务坐标。
- 唯一资产目录 SIGN/data/scene_datasets/gs_scenes；SIGN-habitat-gs/data 为 ../SIGN/data 的软链接。下载直接写最终资源树，校验后从 .part 原子改名，没有额外 HF 全量缓存／压缩包。没有下载 mesh、avatar、VLN 或训练场景。
- 数据元信息首次使用系统 Python urllib 遇 SSLCertVerificationError: unable to get local issuer certificate；改用能验证 TLS 的系统 curl 成功，未关闭证书校验。原始准备日志 logs/habitat_gs_20261026/data_preparation.log。
- 正在创建独立 envs/sign-habitat-gs（Python3.10）；拟以 torch2.5.1+cu121／NumPy2.1.3 满足新版仿真依赖，复用只读 habitat-lab @1f7cfbdd 源码。尚未通过导入／GPU 验证。依赖版本和接入配置写入新分支 scripts/habitat_gs 与 exp_config。
- 代码检查发现 DroneEnv 会以 episode.scene_dataset_config 覆盖配置，官方 episodes 未提供该字段；新分支增加 HabitatGSImageNav-v1 适配器，仅把明确配置的场景数据集路径补入内存 episode，避免场景注册信息丢失。未修改策略、动作、奖励或原始任务文件。采用 SIGN 原500步连续动作和成功定义，不能把后续结果标为官方1000步离散 DDPPO 基准。

## 2026-10-26T13:59:59+08:00 — GIBSON-EVAL-ETA-PARALLEL：预计耗时与独立并行对照

- 用户要求估算完整评估耗时，并利用CPU／GPU资源尝试多线程并行。读取实际 tqdm 进度：13:54:39 完成1950/4200，评估循环502秒，累计3.884 episode/s、最近120秒4.242 episode/s，估计尚需约9–10分钟；13:58:38 完成3146/4200、738秒，累计4.263 episode/s，线性剩余约4.1分钟。估计不保证尾部速度，场景切换与部分环境提前结束会影响；最新计算保存 evaluation_eta.json。12h 是PBS申请上限，不是预计运行时长。
- 当前完整评估已经使用6个独立环境进程和GPU批量推理；OMP/MKL=1 是每进程计算线程限制。VectorEnv使用forkserver，step先向所有worker发送动作再收集返回；目标场景14个，故先测试14环境。PBS采样GPU利用率约25.1%、最大显存7043MB，CPU使用约2–3核量级，相对分配的36 CPU／A40存在扩展空间，但尚无并发提速的实测结论。
- 创建固定280条任务包：从14个验证场景各选20条，选择seed=20261026，源JSON不变；输入清单与哈希在 parallel_benchmark/inputs.json。提交独立任务1494552.stdct-mgmt-02，CFP04-SF-109、autox、1 A40、90分钟上限。顺序比较6环境×1线程、14×1、14×2，再复跑6×1以识别缓存／预热影响。保留原完整评估继续运行；训练4×512配置未被性能尝试改写。
- runner仅启动原run_sim.py的独立子进程，用CLI与环境变量配置并发；没有修改源码或运行时monkeypatch。每条件保存墙钟时间、tqdm评估循环耗时、相同任务集合的聚合指标、/usr/bin/time资源信息与nvidia-smi采样，结果写 parallel_benchmark/results.json。Python3.8语法与PBS bash -n通过；任务还在等待节点资源。
- 新发现的复现细节：src/sensor.py 的 ImageGoalSensorV2 uniform模式使用 abs(hash(episode.episode_id)) 作为目标朝向随机种子，habitat.seed=100并不能固定不同Python启动间的字符串hash。并行对照统一PYTHONHASHSEED=0，避免将目标图变化混入并发对比。原完整评估没有显式固定该环境变量，保留为README原设置的一次运行；后续模型的严格配对比较需要相同哈希种子与对应参考评估，不能将不同目标图的结果说成逐任务配对。当前尚未重跑完整参考，也未改已提交训练／后评估的hash设置。

## 2026-10-26T14:04:21+08:00 — HABITAT-GS-CPU-COMPAT：路径／配置验证与 checkpoint 兼容检查

- 在旧 envs/sign-baseline 做 CPU 检查，没有初始化渲染或占用登录节点GPU：Habitat-Sim0.2.2 的 PathFinder 加载 scene56 navmesh，100条任务全部有有限路径，navigable_area=4034.61255平方米，测地距离与官方记录最大差约3.8147e-6米。实际 GS0.3.3 渲染仍待后续GPU检查。
- 新配置组合保留 Gibson基础PPO参数并依次叠加 policy,reward,sensors,eval,GS；CPU 原 loader 实测100条、1环境、10条评估上限，episode.scene_dataset_config 均为官方 val 场景配置。新 dataset 类只负责元信息适配。
- 首版 probe 对 nav_model 所有键要求无冗余而失败：原发布文件含 loss_fn.*（LPIPS）及 Qc.mlp.*，当前原版策略已不使用这些键；原 trainer 本来 strict=False，并另载 safety_model。随后检查又因把 safety 外层 state_dict 当裸参数而失败。均已保留在 cpu_baseline_probe.log；读取真实结构后按前缀提取，导航／循环／动作／价值参数无缺失，当前 VecQc 从单独 safety state_dict 严格加载成功。没有改动 checkpoint 或算法。
- 最终 CPU 证据 cpu_baseline_probe.json：nav SHA256=03fa71b514c8ee2fa272d6276499d51313a43b7d71bb31181c0150cc7c050d1a；safety SHA256=b84d291e84216defb730d07d03cb6f25e3555ae447eb1e69057f3427b3c7ec31。结果明确标记旧仿真版本及 gpu_probe=false。
- conda独立环境创建成功，官方所需子模块已按固定SHA完成；版本清单 submodule_versions.txt。pip首次发现Python3.10用户site包被视为已满足（numpy1.26.4／typing-extensions）；GPU脚本已设置PYTHONNOUSERSITE=1，安装完成后必须以同样隔离条件再核对／补齐依赖，不能据首次pip返回认定独立环境完整。
- GPU脚本计划使用autox／CFP04-SF-109／A40，GCC11.3、CUDA12.2、架构86、EGL=ON、Bullet/GUI=OFF；尚未提交。原SIGN仍干净。本轮还观察到其他会话新增Gibson并行探针1494552，未修改／重复提交该任务。

## 2026-10-26T14:06:00+08:00 — GIBSON-SHORT-TRAIN-CFP-ROUTE：将未开始的个人短训练转到共享CFP

- 原个人短训练1494520仍处于Q，普通auto队列持续等待node_pool；同一期间CFP/autox的完整评估与并发对照已获得节点。根据用户已授权的项目选择范围，核对本地qalter/qmove手册后，执行 qalter -P CFP04-SF-109 1494520.stdct-mgmt-02，再执行 qmove autox 1494520.stdct-mgmt-02，均成功。
- 保留原job ID和后续依赖，没有取消、重复提交或重跑已执行任务；该任务此前未运行，因此没有由这项短训练消耗个人GPU时数。原提交脚本保存为scratch_train_smoke.initial_personal.pbs，当前脚本模板改为CFP/autox，registry保存调度器覆盖和两份哈希。以qstat和submitted_experiments.json的有效项目为准。
- 并发对照第一组6环境×1线程完成280条任务：评估循环211秒，含启动257.12秒，SR0.8536、SPL0.5195。14环境组正在运行，尚不能下并发收益结论。

## 2026-10-26T14:10:11+08:00 — HABITAT-GS-DEPENDENCY-RESOLVE：NumPy约束冲突与隔离重试

- torch2.5.1+cu121／torchvision0.20.1+cu121 已安装到 envs/sign-habitat-gs。随后 requirements 解析失败，pip实际指出 numba0.60.0 要求 numpy<2.1，而初拟numpy2.1.3冲突（ResolutionImpossible）。没有强制忽略依赖冲突。
- 将新分支 requirements 与当前 STATUS／RUNBOOK 的拟用版本更正为 numpy2.0.2，仍满足 Habitat-GS 的numpy≥2.0与scipy1.14.1要求；历史HABITAT-GS-ASSETS中的2.1.3是当时计划，不改写旧条目。补充setuptools75.6.0用于旧包构建。
- 已以 PYTHONNOUSERSITE=1 重新执行 pip install -r，再安装 smplx/chumpy 并安排 pip check，整个过程继续追加 logs/habitat_gs_20261026/packages.log。首次torch安装时用户site参与过依赖解析，最终导入／pip check必须在隔离条件下通过。当前重试仍在进行，GS尚未提交GPU。

## 2026-10-26T14:10:58+08:00 — GIBSON-FULL-EVAL-DONE-TRAIN-RETRY：完整指标与短训练参数类型修正

- 完整评估1494521 Exit_status=0，4200条全部完成，PBS实际耗时20分34秒，于14:06:25输出指标。TensorBoard精确值SR=0.8600000143、SPL=0.5300576091、ViewMatch=0.8508333564，完整指标保存pretrained_full_result.json。论文Table I（https://arxiv.org/html/2508.12394v1）为SR86.3%、SPL53.3%，本次现有checkpoint结果接近；不代表从零训练已完成。
- CPU结果导出辅助命令首次在Python3.8中导入zoneinfo失败；改用标准库datetime.timezone(timedelta(hours=8))后成功，不安装新依赖，评估作业本身未受影响。
- 短训练1494520转入CFP后实际启动，15秒内因YACS类型校验失败退出1：Type mismatch float vs int，原配置total_num_steps=300000000.0而CLI写40960。失败发生在环境／策略训练初始化前，无PPO更新和checkpoint。原依赖长训练1494529与后评估1494531未运行并随失败依赖终止。
- 将CLI修正为40960.0，保留原算法配置；用原get_config在CPU实际合并成功，total_num_steps为float、num_checkpoints=2、log_interval=1。旧失败日志保留scratch_train_smoke.pbs.log，新日志为scratch_train_smoke.retry1.pbs.log。
- 重建任务链：短训练1494564→正式300M训练1494565→训练后完整评估1494566，均CFP04-SF-109／autox。现有checkpoint完整评估已成功，正式训练仅需等待新短训成功，并仍执行实测耗时guard。没有重跑已完成的4200条评估。旧ID和失败原因保留于registry superseded_jobs。

### 2026-10-26T14:17:50+08:00 — GIBSON-PARALLEL-BENCHMARK-DONE

并发作业1494552成功退出（12分47秒），原SIGN源码未改。相同280条任务／固定PYTHONHASHSEED=0，评估循环6×1首次211秒、14×1为116秒、14×2为138秒、6×1复跑176秒；含启动分别257.12、140.34、163.11、200.15秒。首轮文件读取2335256块、复跑0块，故此前1.82倍包含缓存影响；缓存后循环加速1.52倍、端到端1.43倍。14×2较14×1慢约19%，不推荐增加进程内线程。6环境两次指标相同，14环境两组指标相同；不同batch下SPL有小幅差异。保留原6环境4200条完整评估（20分34秒），14环境完整评估约14–16分钟只是投影。结果与限制见 logs/gibson_reproduction_20261026/parallel_benchmark/summary.json。短训练1494564已进入真实PPO更新，截至核查已完成11次／22528步，正式300M尚未启动；将继续等待耗时检查结果。

## 2026-10-26T14:18:57+08:00 — HABITAT-GS-GPU-SUBMITTED：独立运行环境检查通过并提交编译／smoke

- 独立环境实际为Python3.10.22、torch2.5.1+cu121、torchvision0.20.1+cu121、NumPy2.0.2、Numba0.60.0、SciPy1.14.1。PYTHONNOUSERSITE=1下导入torch／torchvision／NumPy／Numba／SciPy／quaternion／scikit-build-core成功，模块路径均在envs/sign-habitat-gs，user_site=False。
- pip check曾报cmake3.27.9和ninja1.11.1.1 not supported on this platform；直接执行两工具可成功，检查原WHEEL发现Tag前有空行，元数据存在问题。替换为官方PyPI cmake3.31.6与ninja1.11.1.4后pip check明确返回No broken requirements found。smplx0.1.28、chumpy0.70仅为包依赖，未下载任何人体模型或avatar资产。所有错误及重试仍在packages.log。
- 已实际提交qsub scripts/habitat_gs/smoke.pbs，返回 1494650.stdct-mgmt-02，申请autox／CFP04-SF-109／1 A40／12CPU／96GB／2h。提交参数与实际代码哈希在submission_01.json，PBS日志smoke_01.pbs.log。
- 作业顺序：GCC11.3／CUDA12.2编译官方GS源码 → 保存包版本 → GS真实RGB／深度／目标图与姿态恢复、连续动作、SIGN权重前向探针 → 原run_sim.py 10 episode评估；任一步失败则停止。编译与结果目录按PBS ID生成，尚未获得GPU结果，不能把提交当成跑通。
- 全局CUDA架构设86，上游GS rasterizer仍显式编译70/75/80/86/90 fatbin，未改第三方源码以缩减架构。GUI/Bullet关闭，EGL开启。原SIGN及其Gibson作业路径／环境保持独立。

### 2026-10-26T14:19:45+08:00 — GIBSON-SMOKE-PASS-FULL-WALLTIME-BLOCK

短训练1494564 Exit0，作业5分15秒，真实完成40960步／20次PPO更新并导出29条TensorBoard scalar序列、CSV与曲线。training_preflight检查全部训练指标和checkpoint有限；原版latest.pth实际24576步，不能声称模型已保存至40960步。最近10次更新中位155.675步/秒，300M线性投影535.302小时、加15%和启动裕度615.848小时，超过168小时上限。1494565在18秒内由预检查主动Exit1，未开始正式训练；1494566依赖失败未执行。此处是运行时限约束，不是PPO数值错误。MRQ在50M停用可能改变速度，短测投影不等于实际全程时间；但不能无证据假设可缩短至7天。需要下一阶段验证训练提速／队列时限，原代码没有优化器级续训。评估14环境的1.52倍不能当训练提速证据。再次运行check_inputs.py --split val通过，SIGN phase2仍干净；未修改原算法或奖励，未重提同配置长任务。

## 2026-10-26T14:28:01+08:00 — HABITAT-GS-BRANCH-SAVED：实验入口提交与排队状态

- 已在独立 experiment/habitat-gs-imagenav 提交 747aa88a43e5cfc85c50ff46bc3094354b03f85c（feat: add isolated Habitat-GS ImageNav pilot），9个文件，工作树干净。只增加GS数据集元信息适配器、两份配置、选择性下载／探针／依赖／PBS入口、README导航与data软链接忽略规则；原策略／动作／奖励／trainer不变。未推送远端。
- 提交后的实际运行文件逐一与submission_01.json记录的SHA256一致。源代码已固定，但GPU检查仍未执行；不把该提交标成已验证迁移完成。
- 1494650仍为Q，调度器comment=Not Running: Insufficient amount of resource: node_pool；暂无PBS运行日志或GS渲染结果，未重复提交。继续等待原作业资源并检查实际输出。

### 2026-10-26T14:31:44+08:00 — GIBSON-TRAINING-LOGS-SPEED-STOPPING-AUDIT

用户询问TensorBoard、训练耗时与300M是否只作上限。只读检查原配置／trainer／DA_PPO和真实事件：scratch_smoke/tb有29条scalar序列，各20点，最大40960步；reward -1.2726→-0.5608，训练success末值0.02636，短测不足以判断收敛。未启动常驻TensorBoard网页服务。每次更新写入事件，log_interval仅影响终端输出。原配置total_num_steps=3e8、num_updates=-1，BaseRLTrainer.is_done仅检查percent_done>=1，无reward早停；原train不穿插验证。浏览论文 https://arxiv.org/html/2508.12394v1 的V-A.4明确300M步、RTX4090、8环境×256步，所以没有证据认定300M是随意占位或作者实际提前停训。

原日志更新10→20差分每2048步：环境7.1177秒、推理1.6163秒、观测统计1.2817秒、更新模型2.9310秒，已计时共12.9451秒，环境约55%、更新模型约23%；为time.time粗分，不能解释为精确CUDA核耗时。当前4环境×512采样batch小，循环收集与模型更新分阶段执行；MRQ每更新10epoch×2mini，PPO4×2且RandomShift增加前向，Qc另有更新。stop_step=50M只停MRQ，RandomShift继续。535.3h仅按早期速度线性外推；先前“必须单作业跑完300M”的外部预检查是本轮采用的运行策略，不是原算法要求。可以选择预算内观察并根据训练reward与固定验证SR／SPL决定提前停止，但本轮未提交新长训练，也未改源码／参数。下一步建议短测论文8×256配置（相同2048 batch但不同轨迹长度），不能预称可加速多少。分析证据 logs/gibson_reproduction_20261026/training_timing_analysis.json，SIGN工作树检查仍干净。

## 2026-10-26T14:31:51+08:00 — HABITAT-GS-CPU-BUILD-ROUTE：GPU无预计资源时前置CPU编译

- GPU1494650持续等待node_pool，qstat -T未给预计开始时间。分析后将无需实际GPU的CUDA源码编译／新Sim CPU探针前置到auto CPU队列；显式CUDA架构，无需运行GPUkernel。新增scripts/habitat_gs/build.pbs，仍只安装到同一个隔离环境并复用同一源码build目录。
- 已确认GPU仍Q后qhold，提交CPU作业1494685.stdct-mgmt-02，qalter原GPU依赖afterok:1494685并qrls；原GPU作业保留，未重复提交GPU任务。命令／返回／脚本哈希见build_submission_01.json，CPU PBS日志build_01.pbs.log。CPU作业申请auto／CFP04-SF-109／12CPU／96GB／2h，无GPU。
- CPU作业编译后仅运行probe.py的CPU模式，检查真正GS0.3.3导入／路径／权重兼容；成功才释放GPU。原已提交GPU脚本还会执行增量构建检查，复用对象缓存，不同时编译或新建环境／数据副本。尚无编译／渲染通过结果。

## 2026-10-26T14:34:24+08:00 — HABITAT-GS-BUILD-GIT：计算节点缺Git导致配置失败并修复

- CPU1494685进入batch_cpu并在CN-010实际执行35秒，Exit_status=1；申请12CPU／96GB被规范为12CPU／83GB。CMake已能使用CUDA工具链，但OpenEXR配置需要FetchContent获取Imath v3.1.9，报error: could not find git for clone of imath-populate。原始错误见logs/habitat_gs_20261026/build_1494685/build.log。
- 原GPU1494650在该依赖失败后未分配节点而结束，没有GS渲染结果。没有运行新的训练或碰到用户原SIGN源码。
- 在两个PBS脚本明确加载git/2.40.0，bash -n通过；实际重试CPU作业为1494689.stdct-mgmt-02，日志build_02.pbs.log和build_submission_02.json保留新参数／哈希。先等CPU编译与探针结果，再重提GPU，避免每次构建失败连带创建无效GPU任务。

## 2026-10-26T14:39:39+08:00 — HABITAT-GS-BUILD-GLM：复用集群GLM头文件继续增量构建

- CPU1494689在CN-010运行2分19秒，Exit_status=1；Git模块修复有效，Imath v3.1.9已下载到CMake构建缓存，固定SHA d690a3fcff4e877ead5ae56c7e964595ade8a35e。GCC／G++实际11.3.0，CUDA实际12.2.140。构建推进约620/886项时，CUDA forward.cu与rasterizer_impl.cu报fatal error: glm/glm.hpp: No such file or directory。原日志build_1494689/build.log。
- 查到集群已有GLM0.9.9.8，路径/app1/ebapps/arches/flat-avx2/software/GLM/0.9.9.8-GCCcore-11.3.0/include。已用nvcc -E做只预处理的头文件检查，成功；没有下载另一份GLM。两个构建入口加入该CPATH并先检查文件存在，保留既有Ninja对象缓存。
- 新CPU重试1494725.stdct-mgmt-02，证据build_submission_03.json和build_03.pbs.log。GPU脚本现默认使用已经构建好的环境，仅GS_REBUILD=1时才重编译，节约后续GPU分配时间。当前无GPU作业在运行或排队；等待CPU实际通过后再提交。

## 2026-10-26T14:50:07+08:00 — HABITAT-GS-NATIVE-READY：实际GS运行库CPU检查通过，提交GPU评估

- CPU1494725的原生构建成功，生成并安装habitat_gs0.3.3 wheel（380935087字节，SHA256 60c6ccbe79da296ec7ed436115f243b9c4a7e03a61e44db22e60f3e762837c06）；wheel为PBS临时产物，未额外复制保存。该作业整体Exit_status=1、用时5分23秒，是随后SIGN导入碰到ModuleNotFoundError: No module named nis，而非C++编译失败。
- 检查src/policy.py后确认match只出现于from nis import match、从未使用；仅在新分支删除这条无用导入，不改网络、动作、奖励或权重。原SIGN不变。修复后在登录节点运行CPU-only探针，不初始化渲染器／GPU。
- 实际envs/sign-habitat-gs中的Habitat-GS0.3.3、torch2.5.1+cu121、NumPy2.0.2成功加载100条路径，最大测地距离误差0.0，导航网络参数完整、独立安全权重严格加载；pip check返回No broken requirements found。证据build_1494725/cpu_probe.json与cpu_gs_probe.log，gpu_probe仍为false。
- 集群构建／Python兼容修改已提交3c345ab894f4d8d1d85d4983b6e75c7132b41908，新工作树干净。GPU脚本默认不再编译；实际qsub返回1494739.stdct-mgmt-02，autox／CFP04-SF-109／A40，固定代码及CPU证据见submission_02.json，PBS日志smoke_02.pbs.log。此刻仍没有GPU渲染或10条任务指标。

## 2026-10-26T15:02:31+08:00 — HABITAT-GS-SENSOR-API：相机向量接口修复并重试GPU

- GPU1494739已实际分配A40，初始化CameraSensorSpec时报TypeError: supported (SensorSpec, _magnum.Vector3), invoked [0, 1.25, 0]，没有生成渲染或评估指标。日志logs/habitat_gs_20261026/smoke_02.pbs.log保留原错与部分构造后析构错误。
- CPU逐项测试真实RGB／depth配置，确认position列表赋值失败；在新工作树src/custom_habitat_simulator.py显式转换position／orientation为mn.Vector3。probe.py增加不创建渲染器的真实create_sim_config检查，100条导航和权重检查同时通过；证据cpu_sensor_probe.json／cpu_sensor_probe.log。
- 已提交24b4c02926c80ac64cfd1c828c6b999f2ef97b7e，git diff --check通过。实际qsub重试1494770.stdct-mgmt-02，固定提交／命令见submission_03.json，日志smoke_03.pbs.log。未重编译原生库；仍是单场景10条的闭环试验，等待GPU结果。

## 2026-10-26T15:07:32+08:00 — HABITAT-GS-PILOT-COMPLETE：真实GS渲染与10条ImageNav评估完成

- GPU1494770.stdct-mgmt-02在GN-A40-096成功结束，qstat -xf确认Exit_status=0、walltime=00:03:29。代码24b4c02926c80ac64cfd1c828c6b999f2ef97b7e；原SIGN、Habitat-Lab与Habitat-GS源码未改，新工作树git status干净。
- probe.json确认实际Habitat-GS0.3.3／A40、100条路径误差0.0、RGB和目标图标准差41.35／41.47、目标图与指定位置重渲染完全一致且保持智能体姿态、SIGN策略输出有限、连续控制位移0.18795米并旋转。已实际查看probe.png，当前视图与目标图为正常室外建筑场景。
- 原run_sim.py完成10/10，评估循环1分44秒；TensorBoard提取SR0.10000000149、SPL0.05354254320、soft_SPL0.15099440515、view_match0.1、平均最终距离14.9221239米、平均碰撞46.9次。证明运行链路打通，现有Gibson权重在此小样本迁移较弱；没有训练，也不与官方DDPPO／完整GS基准混称。
- 证据集中SIGN-habitat-gs/results/habitat_gs_20261026/job_1494770/：probe.json、probe.png、packages.txt、eval/eval_run0_/config_of_eval.yaml与log.txt、eval/tb，另将TensorBoard汇总提取为result.json（已执行CPU脚本）。PBS原始输出logs/habitat_gs_20261026/smoke_03.pbs.log。原trainer不落盘逐条指标／轨迹，本轮未增加采集，不能据聚合指标解释具体失败。
- 官方全场景配置报告未下载的其他navmesh及缺语义描述，当前仅scene56和RGB／depth实际可用；Gym的NumPy2通用提示也保留。无额外场景／模型／渲染视频副本。四份根文档持续按既有职责维护，没有新建总结文档；分支仅本地提交，未推送。后续建议小规模失败轨迹诊断后再扩大，目前没有待运行GS作业。

### 2026-10-26T15:30:09+08:00 — GIBSON-TRAIN-SPEED-BENCH-SUBMITTED

用户要求实际尝试训练提速，优先8环境。先核对AGENTS／STATUS、SIGN phase2干净与现有任务（当前用户无排队／运行作业），保留其他窗口GS工作。新增外部测速launcher与PBS到 logs/gibson_reproduction_20261026/train_parallel_benchmark，不修改SIGN源码／奖励。原get_config逐项验证4×512与8×256，float40960.0、num_checkpoints=-1、checkpoint_interval=10、log_interval=1均通过；Python3.8编译和bash -n通过。提交1494908（CFP04-SF-109，autox，1×A40／36CPU／240GB，75分钟）。同一GPU按4×512→8×256→4×512运行，各20次更新／40960步，固定hash0，最后10次更新比较步速，复跑控制缓存／节点漂移；各组日志、GPU2秒采样、TensorBoard、40960末步checkpoint和曲线独立保存。性能测试改变并行度及轨迹长度，不证明学习质量／完全相同轨迹；初期MRQ开启，全程300M投影仅线性估计。当前等待调度／实际运行。

### 2026-10-26T15:40:28+08:00 — GIBSON-TRAIN-SPEED-BENCH-COMPLETE

1494908 Exit0，GN-A40-045／NVIDIA A40／Intel Xeon Platinum8452Y，同作业8分36秒。三组原版SIGN训练均完成40960步／20次更新，29条scalar和末步checkpoint有限且保存成功。热身后最后10次更新中位：4×512首次298.913步/秒（6.8515秒/更新），8×256为335.478（6.1047秒），4×512复跑295.027（6.9417秒）；8环境相对两基准加速1.1223×／1.1371×，复跑基准差约-1.30%。4环境重复训练最终指标逐项一致；不同并行组不是相同轨迹，不据短reward声称收敛改善。

8环境每次更新平均环境2.1698秒、动作推理0.5350秒、观测统计0.5494秒、模型更新2.7761秒；4环境首次对应2.5212／0.8397／0.5803／2.8026秒。PPO／MRQ模型更新时间基本相同，增加环境主要减少采样及推理开销。峰值显存4环境12010MiB、8环境16569MiB。原GPU采样含启动，plot_results另按最后10次更新墙钟窗口汇总稳定期利用率，图comparison.png已生成。旧GN-A40-096的4环境仅155.68步/秒；本轮新节点4环境已更快，未隔离CPU／节点负载／运行环境等贡献，不将总差距归于8环境。当前8环境300M线性投影248.402小时，MRQ50M后停用和场景变化使其不是确定全程时长。建议后续预算内训练用8×256；本轮未启动新长训练。

完成后原check_inputs --split train再次通过，44个基线源码／checkpoint哈希一致，SIGN phase2仍干净。证据 logs/gibson_reproduction_20261026/train_parallel_benchmark/{submission.json,results.json,summary.json,comparison.png}；各独立model-dir保留TensorBoard、每10次更新checkpoint、CSV和曲线。

### 2026-10-26T15:57:51+08:00 — GIBSON-KEEP8-QUEUE-STATUS

用户先询问默认上限是否3000万并提出12／16环境，已说明原配置3e8即3亿（300M）并只读取现场；随后用户明确取消扩并发、确定8环境，再询问当前实验。取消前尚未创建12／16脚本、未提交作业，因此无需删除或取消任务。2026-10-26 15:57（新加坡）实际执行qstat -u e1538633为空；ps也无本账号run_sim.py／run_benchmark.py／tensorboard进程。历史1494908再次确认为F／Exit0、15:39:19结束、8分36秒；完整Gibson评估、短训练和GS pilot均已结束，300M正式训练仍未启动。记录用户选择8×256，不因状态查询提交新实验。

### 2026-10-26T16:18:23+08:00 — GIBSON-PERSONAL-LONG-SUBMIT-INFLIGHT

用户明确要求个人额度正式长训练，并提供本地浏览器TensorBoard命令。新增scratch_train_personal_8env.pbs：personal-e1538633／auto、A40、36CPU240GB、168小时、8×256、保留3e8上限，num_checkpoints=-1、checkpoint_interval=250、log_interval=10，hash0、OMP/MKL/OPENBLAS1，原源码／奖励未改。独立输出scratch_personal_8env，拒绝已存在ckpts目录，不承接smoke权重；外部完整300M耗时拦截不适用于用户已授权的预算内观察运行。bash -n与check_inputs train通过；CPU配置合并探针因共享存储filemap_update_page等候，尚未返回。qsub已执行，session87437仍在等待PBS响应，qstat亦等待，未声称已成功／未重复提交。

TensorBoard2.8.0试启动遇共享存储读取延迟，后成功提供127.0.0.1:6006；首页与/data/logdir均HTTP200，目录确认为scratch_personal_8env/tb。已正常终止网页探针，避免占用用户SSH启动端口。新增view_personal_tensorboard.sh让用户在同一SSH连接的远端启动网页，以本地16006转发远端127.0.0.1:6006，兼容vanda登录入口可能分配不同主机。探针证据tensorboard_web_probe.json。仍待PBS作业号及实际参数核查。

### 2026-10-26T16:23:28+08:00 — GIBSON-PERSONAL-LONG-SUBMITTED

前条的qsub等待已结束，Exit0并返回1495073.stdct-mgmt-02。正式训练使用用户指定personal-e1538633／auto，没有转用CFP、没有重复提交。延迟期间原get_config合并探针成功返回，确认300M上限、8×256、checkpoint每512000步；完整配置探针personal_8env_config_probe.yaml。提交后qstat -f1495073尚在等待，暂未确认运行／排队状态，不声称已发生PPO更新。当前PBS日志尚未产生，待调度核验。新任务写入submitted_experiments.json与personal_training_submission.json，STATUS已更新；原SIGN phase2仍干净。用户本地SSH入口及浏览器说明已加入RUNBOOK，网页版实测通过而探针进程已关闭，用户用SSH命令启动服务。

### 2026-10-26T16:23:59+08:00 — GIBSON-PERSONAL-RUNNING-CONFIRMED

提交后qstat已返回：1495073为R，project=personal-e1538633，queue=batch_gpu（auto路由），GN-A40-019/1*36，资源1A40／36CPU／240GB、168h，实际启动16:23:15。原始响应personal_training_qstat.txt，登记文件已更新；尚需确认首次PPO更新／事件写入，不把运行状态等同完成训练。

### 2026-10-26T16:26:13+08:00 — GIBSON-PERSONAL-FIRST-PPO-TENSORBOARD-VERIFIED

1495073个人项目原版训练初始化完成，读取真实TensorBoard事件确认29条scalar、5次更新／10240步，包含reward、success、SPL、learner与fps；此为当次观察点，不是训练结束。证据personal_training_first_events.json；网页探针HTTP200证明实际目录可展示。正式训练尚未到每250更新的首个checkpoint，不宣称已保存模型。原源码哈希在计算节点启动检查通过，仍保留原奖励和算法，8×256／300M上限／168h预算，个人auto→batch_gpu。最终用户命令通过同一SSH连接启动127.0.0.1:6006 TensorBoard并映射本地16006，关闭该连接不停止PBS训练。共享存储与PBS响应曾显著延迟，均已恢复到可完成提交／读取的状态；没有重复任务、没有转用CFP。

### 2026-10-26T20:35:38+08:00 — GIBSON-TENSORBOARD-SSH-RESTORED

用户报告远程TensorBoard在本地无法打开并授权直接访问Vanda排查。初查本地16006无监听；SSH公钥认证成功，登录stdct-login-01，远端6006无监听，本账号无TensorBoard进程。原view_personal_tensorboard.sh路径／训练事件有效；用户贴出命令开头为sh，正确命令应为ssh，但未获取用户原始报错，不能确定此前唯一失败原因。远端无rg，改用grep完成RUNBOOK定向检查。

已执行ssh -T，ExitOnForwardFailure=yes、ServerAliveInterval=30、ServerAliveCountMax=3、-L 127.0.0.1:16006:127.0.0.1:6006，同一连接执行原启动脚本；本地SSH PID1299505，保留连接。启动出现Python3.8 FutureWarning／CryptographyDeprecationWarning及TensorFlow installation not found，随后正常报告TensorBoard2.8.0监听6006。早期启动前curl连接拒绝；启动后首页HTTP200，/data/logdir目录正确，plugins_listing标量启用，scalars/tags共29项，reward接口返回1000个下采样点、最新step3420160。证据tensorboard_ssh_recovery.json。未改依赖／训练脚本／奖励，未提交或停止PBS作业。浏览器自动打开未完成：CUA无iab且浏览器库存为空；HTTP与真实曲线API已从本地直接验证，用户可自行打开本地URL。RUNBOOK补充本地执行位置、等待就绪与警告解释，STATUS更新当前连接。

### 2026-10-26T20:57:49+08:00 — GIBSON-TENSORBOARD-USER-HANDOFF

用户明确要求关闭代理建立的SSH转发，改为自行运行。先核对本地PID1299505命令与16006监听，执行kill -TERM并确认16006无监听。SSH退出后远端TensorBoard未自动退出，实际在stdct-login-01发现PID3146383（20:33:42启动），完整命令匹配本轮脚本及训练tb目录；核对主机和/proc命令后仅对该PID发送SIGTERM，ss确认6006无监听。未操作PBS训练。STATUS／RUNBOOK已更新，保留历史验证证据。

### 2026-10-26T21:53:57+08:00 — GIBSON-ENCODER-TRAINABILITY-AUDIT

用户询问当前是否冻结Vision encoder。读取实际config_of_train.yaml、原SafeNavNetPolicy／EarlyFuseCNNEncoder、DA_PPO和上游PPO优化器：当前fast_resnet9未设requires_grad=False，使用可求导参数Adam，在线视觉前向参与PPO和MRQ损失；采样阶段detach／inference_mode不等于冻结。原配置ddppo.train_encoder=True，本次自定义trainer无需仅凭该flag推断，已用原代码路径和实际checkpoint交叉验证。CPU只读比较ckpt.0@512000与ckpt.7@4096000步，视觉编码器39/39组weight／bias、GRU8组、actor2组、普通critic2组、MRQ在线16组、Qc10组均有变化；视觉weight／bias最大绝对差0.36997。MRQ目标头EMA变化，cost_critic2组不变且源码未将其cost-value loss加入总损失。

辅助分类最初用包含匹配误将actor_critic前缀中的critic归组，并混入归一化计数buffer的较大变化；已改为剥离actor_critic前缀后精确匹配，另列weight／bias排除buffer，补充GRU的weight_ih等命名，最终审计JSON已修正。未修改运行中模型、源码或配置。21:50日志显示真实训练已到4464640步，此为日志观察点，不是结束。证据logs/gibson_reproduction_20261026/parameter_update_audit.json。

### 2026-10-26T22:08:36+08:00 — SIGN-UPSTREAM-ENCODER-FREEZE-REVIEW

用户要求核对学长最新GitHub提交、编码器清单和加载公开checkpoint冻结视觉的可行性，起初表达可能停训。通过async明确询问后用户选择“暂时继续，等分析结论”；本轮无qdel、无运行中参数修改、无新GPU任务。git ls-remote HTTPS实时返回HEAD/main均dad87fe225a4dc1073787d8d2cc83f67e61c0a9d；GitHub连接器get_repo确认默认main，fetch_commit确认Zichen-Yan于2026-10-14提交update readme。本地HEAD和tree274f6344一致，44跟踪文件工作树干净，原check_inputs train再次通过。CPU／数据／CLI调整和历史phase1、GS工作树不等同当前SIGN源码修改；repo核对清单repository_audit.json。

梳理当前factory：Fast resnet7／9／9_fixup／18／18_fixup／50可路由，Habitat resnet18／50／se_resnet50可路由；SimpleCNN调用当前导入依赖时参数数目不符，clip／clip_feat未提供constructor，其他SE／ResNeXt函数存在但并非都能经当前路由选择。当前只用单个6通道RGB早融合fast_resnet9，goal_visual_encoder=None。当前自定义SIGN trainer未读取标准ddppo pretrained_encoder／train_encoder开关，冻结迁移需独立接入代码。

外部review脚本在CPU构造独立模型，未修改SIGN源文件；公开nav_model.pth SHA256=03fa71b514c8ee2fa272d6276499d51313a43b7d71bb31181c0150cc7c050d1a，严格加载视觉42状态项（1302400参数）和投影2项（65664参数），均零缺失／多余。冻结1368064参数并固定eval，一次合成后端梯度检查CNN／投影所有状态不变，GRU、actor、critic更新成功。初次仅2图的归一化统计未观察到变化；发现预训练float32_count=2877947904，增量2可被精度掩盖，改用单独normalizer的1024×6×2×2小张量验证后_var／_count确有变化。因此必须同时冻结参数和统计，并防原agent.train()重启归一化训练模式。该检查是提取／冻结语义验证，不是完整PPO验证。

建议加载并冻结视觉CNN＋投影、重训GRU与策略／价值头，作为视觉迁移实验；若加载完整policy再冻结视觉则是微调，应另标。完整视觉固定后MRQ只训练自身预测头，是否停用需明确记录，不假定对导航仍有相同益处；RandomShift下特征缓存需区别增强输入，不能先声称加速倍数。当前端到端训练仍是有效原版对照，不因新建议而视为错误。22:07核查1495073仍R。证据frozen_encoder_review/{inspect_checkpoint.py,cpu_review.json,repository_audit.json,proposal.json}，仅维护既有根四文档与机器证据，未新增交接文档。

### 2026-10-26T22:39:53+08:00 — SIGN-ENCODER-ONLY-MINIMAL-PATCH-PROPOSAL

用户明确限定只冻结actor_critic.net.visual_encoder，并只从学长公开checkpoint加载该模块；visual_fc及其余初始化保持原样。要求先展示准确位置和代码，审核同意后再实现、提交训练，并允许停止1495073和清理冗余checkpoint，最多保留最后权重／TensorBoard／实验记录。此条件尚未满足，不执行修改／qsub／qdel／删除。实际源码为src/trainer.py而非train.py；run_sim只调用trainer.train，模型在train→_init_train→_setup_actor_critic_agent才创建。拟于当前95行插入12行：读取既有ddppo配置，torch.load指定state_dict，筛并剥离actor_critic.net.visual_encoder.前缀，strict=True载入；train_encoder=False时requires_grad_(False)并eval。该位置在创建PPO／DA_PPO优化器前，原优化器自带requires_grad过滤。拟于当前452行agent.train后加两行条件eval，防RunningMeanAndVar统计更新。默认配置不启用新行为，CLI开启pretrained_encoder并指定公开ckpt、train_encoder=False。MRQ／RandomShift／reward／8×256等保留，MRQ仍可更新随机初始化visual_fc。

生成外部encoder_only_proposed.patch和encoder_only_plan.json供审核；在内存AST parse通过，git apply --check通过但未应用，git status确认SIGN phase2仍干净。上轮cpu_review验证冻结CNN＋投影，其记录保留但不当作本次CNN-only实施。审批后将验证同seed除encoder外初始化一致、encoder权重／统计固定且visual_fc／策略等仍更新，再按授权处理新旧任务。清理范围只限旧run中间checkpoint；原代码qdel不补存内存模型，拟保留最近完整落盘权重并标清实际step。22:35核查1495073仍R，日志5038080步；本轮仍继续运行。

### 2026-10-26T23:35:53+08:00 — SIGN-ENCODER-ONLY-APPROVED-STOP-AND-APPLY

用户明确“好的，我同意”，授权范围含已审14行代码、个人新实验、停止1495073与旧checkpoint精简。先qstat核对任务归属和personal项目，qdel Exit0，PBS确认23:30:42结束／Exit143／7小时7分24秒。确认任务结束后，校验最后编号ckpt.10.pth权重有限，复制到final.pth、核对SHA及step5632000，随后仅删除本run的11个ckpt.N与latest共12份中间／重复权重；final.pth为目录中唯一权重。TensorBoard最大5785600步，保留配置／日志／事件并导出29条scalar CSV和曲线，差异因原代码停训不补存内存权重。实验汇总stopped_scratch_run/result.json含删除清单及哈希，历史parameter_update_audit引用的中间文件按用户要求不再保留，但审计JSON保留。

停止旧作业后在SIGN建立phase2/frozen-visual-encoder，由dad87fe出发准确应用encoder_only_proposed.patch，只增src/trainer.py14行。git diff --check通过，尚未提交；其余源码未改，main和phase2/exploration-reward-try原基线保持。正在外部CPU脚本验证实际setup初始值与原生DA_PPO/MRQ/RandomShift/Qc更新，未提交新GPU任务。

### 2026-10-26T23:41:14+08:00 — SIGN-FROZEN-CPU-PASS-COMMIT-PERSONAL-SUBMIT

实际_setup_actor_critic_agent和_update_agent验证完成：公开encoder42状态项逐项一致、1302400参数冻结且从Adam排除，visual_fc保持可训练；相同seed100构造默认模型与冻结模型，所有非encoder初始状态零差异。以原CostRolloutStorage构造4步×2环境CPU小rollout，原DA_PPO／MRQ10epoch／RandomShift／Qc完整更新后，encoder全部权重和统计不变、eval保持，visual_fc／GRU／actor／critic／MRQ在线／Qc发生更新，所有loss有限。首次辅助脚本用Config(yaml.safe_load(savedconfig))导致eps科学计数值被保留为字符串，Adam报TypeError（float<=str），尚未训练；改用原get_config合并路径后通过，保留cpu_validation.log失败与cpu_validation.retry1.log成功，未为此改算法代码。

通过验证后本地提交dac8609ee1dc3e71ad317998a2f5086a1935e84b，分支phase2/frozen-visual-encoder；仅src/trainer.py14行新增，git diff --check和干净状态通过，44个跟踪文件仅trainer哈希变化，main和原phase2保留dad87fe；本轮未推送GitHub。生成独立source_manifest与输入守卫，保护所有其余源码／公开权重／任务数据，不再误用旧原版sourceguard。新个人PBS1496716提交成功：personal-e1538633／auto→batch_gpu、1A40／36CPU／240GB、168h，当前Q因node_pool。同一作业先2次GPU更新4096步，verify_gpu_smoke检查encoder42项逐位不变、末步checkpoint和29项指标有限，成功后重新随机初始化后端进入300M上限正式训练，输出新目录。正式训练与smoke均只加载公开encoder，没有继承旧策略／投影或smoke权重。

已更新旧TensorBoard viewer脚本指向新正式目录；没有终止用户当前网页服务。已有SSH会话需重启以采用新脚本。AGENTS／STATUS／RUNBOOK反映本次明确批准和新源码边界，全部实验证据保留在logs/gibson_frozen_encoder_20261026，当前GPU验证尚未发生，不宣称通过或新训练已运行。

### 2026-10-26T23:44:37+08:00 — SIGN-FROZEN-GPU-PASS-LONG-TRAINING-RUNNING

1496716于23:40:17在GN-A40-045进入R，个人project确认。原run_sim GPU预检完成4096步／2次更新，checkpoint实际step4096，29条指标及全部模型值有限，encoder42状态项与学长公开nav_model逐位一致（含归一化buffer），visual_fc不等于公开投影。校验脚本返回通过，才在独立train_personal_8env重新构造模型并启动正式长训练；没有承接smoke后端权重。

23:42:56读取正式TensorBoard，29条scalar、最大45056步；实际config确认pretrained_encoder=True、pretrained_weights=ckpt/nav_model.pth、train_encoder=False、num_env8、rollout256、total300M。当前qstat账号仅1496716一个R。SIGN工作树干净，main基线未变，本地dac8609仅trainer14行；未推送。旧1495073的final.pth／TensorBoard／配置日志与曲线保留，12个旧中间／重复checkpoint删除。记录与源哈希见logs/gibson_frozen_encoder_20261026/{source_manifest.json,cpu_validation.json,gpu_smoke_validation.json,first_long_training_events.json,submission.json}；任务是已启动而非训练完成，不依据短样本reward声明收益或收敛。

### 2026-10-27T04:37:22+08:00 — SIGN-FROZEN-BRANCH-PUSH

用户明确要求最新代码push到yiichu03对应branch。核对SIGN当前phase2/frozen-visual-encoder、HEAD dac8609ee1dc3e71ad317998a2f5086a1935e84b、干净工作树、最新提交仅src/trainer.py14行新增；有效origin push URL为git@github.com:yiichu03/SIGN.git，远端尚无同名分支。本次无需空提交，执行普通git push -u origin HEAD:refs/heads/phase2/frozen-visual-encoder成功，新建对应远端分支；显式设置branch.phase2/frozen-visual-encoder.pushRemote=origin。随后git ls-remote origin refs/heads/phase2/frozen-visual-encoder核对返回相同完整SHA，git status确认干净且跟踪origin同名分支。未推upstream、未强推、未改其他分支或训练源码，未打包本地权重／环境／数据／运行日志。GitHub入口 https://github.com/yiichu03/SIGN/tree/phase2/frozen-visual-encoder 。

### 2026-10-27T05:45:48+08:00 — ROLLOUT-COVERAGE-GOAL-WORKTREE-UNIT-PASS

用户明确以goal模式推进：从yiichu03/SIGN的phase2/frozen-visual-encoder@dac8609建立独立worktree与phase2/frozen-rollout-coverage，只加固定rollout末按episode片段结算的探索奖励，原作业1496716不停不改。已create_goal，git ls-remote确认基线，原SIGN干净44文件SHA快照保存；git worktree add创建SIGN-frozen-rollout-coverage，data软链接复用，仅新worktree改源码。实现原提示未写完的ObservedCoverage_observe_count/reset/update：世界-Z前向quaternion旋转后投影为map行Z列X，0.1m栅格、3m半径、90°视域，navmesh遮挡，初始视野seen但delta=0；episode重置、rollout不重置，楼层按XZ union不重复。提示中的_add_coverage_bonus末尾缺return，补充coverage_bonus_sum／per_step／new_area_m2三个独立learner指标；环境reward统计未改，真实mask由astype(bool)复制后只改结算边界。

外部test_coverage.py9项通过（初始／重复／重置、四向／半径、墙遮挡、重叠楼层、rollout连续覆盖、多episode位置和总bonus、weight0精确不变、异常输入、最终config仅追加measure且FOV匹配）。本地提交6983c91e20493ff25ff32c24df02b968cc34f701只含指定3文件，尚未push。新data软链接未跟踪且明确不加入提交。source_manifest和check_inputs保护新代码／数据及原SIGN所有文件，验证通过；个人short任务1497400提交成功，2h、1A40／36CPU240GB、auto，包含真实场景4朝向／遮挡／开销探针及baseline/weight0/weight0.1各40960步顺序短跑。GPU待验证，不声称短跑已通过。

### 2026-10-27T05:51:46+08:00 — ROLLOUT-COVERAGE-PROBE-CLI-RETRY

个人GPU短跑1497400取得GN-A40-025但25秒内Exit1，尚未渲染／训练：外部probe_scene.py将content_scenes写为[Adrian]字符串，YACS报list/str Type mismatch。改成合法字面量["Adrian"]，仅修辅助探针，不改实验源码；短跑PBS输出改为short_checks.retry1.pbs.log保留失败原日志，重新提交1497409。另辅助实际配置对比发现保存YACS repr的None重载为字符串None，修比较逻辑将这些nullable序列化值正规化；原同路径base/coverage严格相等（剔除measure）已由单元测试通过，没有改运行设置来掩盖差异。正式训练仍未提交，等待GPU短跑成功。

### 2026-10-27T06:07:03+08:00 — ROLLOUT-COVERAGE-SHORT-PASS-TRAIN-SUBMIT-PUSH

重试GPU1497409在GN-A40-019运行10分40秒后Exit0。真实Adrian场景四个相机yaw与XZ地图视域方向一致、找到实际墙后不可见的可行走格；初始reset约2.05秒含JIT，100次重复metric中位0.304ms、p95 0.336ms，图camera_coverage_alignment.png已人工查看。随后同节点8×256短跑baseline、coverage weight0、coverage weight0.1，各20次更新40960步；全部TensorBoard／权重有限，三组encoder42项与公开checkpoint逐位一致。零权重reward/SR/SPL/value_loss记录精确相同，其他公共指标通过逐点比较。稳定吞吐277.1938／212.7223／196.8703步/秒；零权重相对baseline时间开销30.3078%，非单次metric毫秒数所能代表，正权重因策略轨迹变化不当纯统计开销对照。

正权重20个rollout累计新增面积2109.420013m²，累计bonus0.823992191，逐rollout验证等于0.1*area/256（TensorBoard float32容差）；原reward日志仍导航奖励，coverage另记learner三项。真实mask不变／片段末位置／跨rollout不重置／episode重置／weight0奖励逐元素不变由9项CPU边界测试确认。实际冻结任务配置审计config_audit.json除测量配置与输出路径外一致，评估保留6环境、500步、4200val、不启用coverage YAML。所有验证证据已保存，短跑不证明学习收益。

通过后提交正式训练1497416.stdct-mgmt-02：personal-e1538633／auto→batch_gpu、1A40／36CPU／240GB、168h、seed100/hash0、8×256、300M上限，原encoder冻结/随机后端/MRQ等设置原样继承，独立输出。当前状态R，不声称训练已更新。随后普通push新分支phase2/frozen-rollout-coverage至yiichu03/SIGN成功，远端SHA与本地6983c91e20493ff25ff32c24df02b968cc34f701一致，建立origin跟踪和pushRemote。只有用户指定的3个文件被提交，data资源软链接未跟踪／未上传；原目录SIGN分支HEAD与44个文件SHA再次一致，原1496716仍R，未切换／修改／停止原训练。

完整命令见train_personal.pbs；提交登记training_submission.json，目标任务已达到“实现、验证、提交并push、报告”阶段，不表示300M训练完成。

### 2026-10-27T06:11:25+08:00 — ROLLOUT-COVERAGE-FORMAL-UPDATES-CONFIRMED

实读正式1497416日志已完成30次更新／61440步，随后直接读取正式TensorBoard确认34个scalar、96256步，reward仍为原导航奖励；learner/coverage_bonus_sum、coverage_bonus_per_step、coverage_new_area_m2独立存在且有限。记录formal_first_events.json；当时最近一轮bonus0.098796874、面积252.919998m²，与0.1*面积/256一致。qstat确认1497416及原1496716均R。仅诊断读取首次因Python3.8无zoneinfo报ModuleNotFoundError，改用标准库timezone(timedelta(hours=8))重读成功，未改训练源码／设置。已更新STATUS与提交登记；本轮交付目标完成不代表训练结束或获得学习收益结论。

### 2026-10-27T13:43:19+08:00 — COVERAGE-BENEFIT-MATCHED-TRAIN-SNAPSHOT-EVAL-SUBMIT

用户要求检查coverage是否辅助成功率。只读qstat及两训练日志／事件：两任务R，基线约22.4M步／coverage9.49M步，不将不同训练预算直接比较。外部analyze_training.py导出两完整scalar CSV和PNG/PDF，共同末步9488384，最近100万步SR83.525%对84.304%、SPL46.799%对47.568%，约+0.78／+0.77pp；7M-8M区间SR为86.106%对82.882%（-3.224pp），窗口均值高度相关且训练任务不同，不作独立样本显著性检验，当前无法声称稳定收益。reward原日志不含bonus；最近bonus均值每rollout0.117336／每动作5.7293e-5。两组ckpt.17的extra_state.step均9216000，复制到本条证据目录并核对SHA，原权重未修改；同阶段覆盖训练耗时26390s对20710s约+27.4%。

已执行qsub baseline.pbs与coverage.pbs，个人auto各1A40／36CPU240GB／2h，返回1498509／1498510；原生eval使用同一独立coverage工作树、无coverage YAML、6env／500步／全4200val／seed100/hash0，保留公共safety权重加载行为；只模型checkpoint不同。baseline已R，coverage暂Q（Insufficient node_pool），未因排队重提或改路由。外部脚本与登记comparison_submission.json、eval_manifest.json；训练输入和原SIGN源文件仍受哈希守卫。尚无验证集结果，不把已提交写为完成。

### 2026-10-27T14:06:20+08:00 — COVERAGE-BENEFIT-BASELINE-VAL-COMPLETE

原生完整验证baseline任务1498509完成4200/4200，程序成功返回，模型固定9216000步；TensorBoard SR0.783571422（3291/4200）、SPL0.519764483、view_match0.766428590。baseline_eval_result.json与原生baseline_eval.log已保存。覆盖组1498510仍在运行，当前约2320条；此时尚不能计算完整验证差值。两组长训练继续，未改代码、权重或配置。

### 2026-10-27T14:31:40+08:00 — COVERAGE-BENEFIT-FULL-VAL-NO-GAIN

继COVERAGE-BENEFIT-MATCHED-TRAIN-SNAPSHOT-EVAL-SUBMIT与BASELINE-VAL-COMPLETE，两原生评估1498509／1498510均完成4200/4200且程序成功返回；两不可变模型均9216000步，seed100/hash0、6env／500步／相同全部val、关闭coverage测量，保留原公共safety checkpoint行为。完整SR为3291/4200=78.357142%对3254/4200=77.476191%，coverage少成功37条、差-0.880951pp；SPL51.976448%对50.101399%，差-1.875049pp；view_match76.642859%对75.083333%，差-1.559526pp。两份模型encoder42状态与公共checkpoint逐位相等、全部参数有限，checkpoint_integrity.json通过。eval_config_audit.json通过，运行设定相同，仅模型路径、输出路径和对应CLI元数据不同；初次辅助审计AssertionError因未把habitat_baselines.cmd_trailing_opts中的同一checkpoint路径副本列入允许项，现严格验证该列表只包含预期eval_ckpt_path_dir键和值后通过，无运行配置改动或重跑。

已执行summarize_eval.py生成full_val_comparison.json；baseline_eval_result.json、coverage_eval_result.json及原生log／TB／实际config保留。原生评估只存汇总，无逐条成败，不能做McNemar／成对bootstrap；仅一个训练seed和一个模型时点，不作显著性或长期因果结论。观察结论：当前weight0.1没有显示成功率收益，当前验证SR及SPL均较低；不宣称已证明奖励长期有害。

等待验证时再执行analyze_training.py，新增latest_training_snapshot目录，未覆盖13:40初始CSV／曲线。14:24:40真实事件快照：基线23646208步、coverage10438656步，所有scalar有限；按共同末步截取最近100万步，SR86.170118%对84.749914%（-1.420204pp），SPL48.227654%对48.381285%（+0.153631pp），view_match82.348028%对80.869866%。先前约+0.78pp的训练SR领先未持续；共同前9.49M整段曲线均值也近乎相等。最新每rollout bonus均值0.130824／每环境步6.38787e-5，非零且守恒；量级偏小只能列为待验证假设，未调整权重。相同9.216M模型训练耗时覆盖26390s对基线20710s（+27.4%），不同节点长跑不作为纯统计开销隔离对照；原同GPU零权重短跑约+30.3%为统计开销对照。

最终只读git核对：SIGN仍phase2/frozen-visual-encoder，跟踪源码干净；独立coverage仍phase2/frozen-rollout-coverage，只有既有data资源软链接未跟踪。qstat两长训练继续R，日志最近约23.78M／10.55M步；未修改源码／超参数／分支、未停止或重启训练、未新增训练、未push本地诊断证据。后续可观察更晚同阶段模型和其他seed；本条不自动授权新评估／训练。STATUS已更新为当前结论。

### 2026-10-27T14:58:29+08:00 — COVERAGE-RESULTS-PUBLICATION-PREPARE

用户要求将当前实验情况推送到yiichu03以便分析。核对origin有效push为git@github.com:yiichu03/SIGN.git，远端phase2/frozen-rollout-coverage当前6983c91，与发布基点相同；两训练工作树分别仍dac8609／6983c91，只有coverage既有data软链接未跟踪。旧发布器锁定第一阶段SRU历史研究分支，未运行或更改其保护；本轮使用独立detached SIGN-coverage-publication @6983c91。14:53:57 qstat两训练均R，最后控制台基线24432640步、coverage11018240步，保存publication_runtime_status.json。

已准备阶段二限定发布器build_publication.py，拟生成docs/experiments/frozen-rollout-coverage及根README导航：完整4200val比较、两版训练曲线、最新所有scalar CSV的gzip、原生验证日志与事件、实际配置、冻结/单测/GPU证据、原执行PBS和分析脚本、四根文档生成副本及逐文件SHA。数据结论沿用已完成评估，不新增实验或refresh模型；训练目录/代码/参数/作业不变。排除所有checkpoint、场景、环境和原始相机数据，原始服务器材料保留。相对链接、哈希、gzip解压一致性、发布WORKLOG前缀、运行代码零差异及远端历史将核对后才提交普通push；此条仍为准备阶段，最终commit与远端核验另追加回执。

### 2026-10-27T15:00:43+08:00 — COVERAGE-RESULTS-PUBLICATION-CHECKED

build_publication.py已实际执行成功，55个材料文件（另有发布清单）共11950488字节；gzip解压SHA、逐文件SHA、相对Markdown链接、禁止资产与已知凭据格式检查通过，发布树仅根README导航和docs/experiments/frozen-rollout-coverage，src／exp_config／run_sim.py相对6983c91零差异。进一步核对原SIGN44个、coverage45个受保护文件SHA全部不变。原始评估汇总及snapshot未重新生成；最新完整CSV以gzip发布，13:40早期JSON/曲线保留，初次完整CSV仍在服务器。即将重建根四文档副本，使本条检查记录包含在包内；已有发布WORKLOG副本作为严格前缀保留。提交与远端回执尚待执行，不将本条写成push成功。

### 2026-10-27T15:03:30+08:00 — COVERAGE-RESULTS-PUBLICATION-PUSHED

在独立SIGN-coverage-publication detached树执行git add README.md docs/experiments/frozen-rollout-coverage，限定资料和导航；57文件、9805行新增，55个材料文件加manifest及根导航，共约12MB（原始scalar以gzip发布）。核对必要文档/脚本git diff --check、全部材料SHA、解压SHA、相对链接、root WORKLOG旧前缀、原SIGN44／coverage45源文件SHA、运行代码零差异均通过；未重新运行GPU模型或训练。执行git commit产生b39e3626aae31125f018a81b047a593da71e468b（Document matched-step Gibson coverage reward results），随后已执行git push origin HEAD:refs/heads/phase2/frozen-rollout-coverage，普通快进6983c91→b39e362成功；git ls-remote核对远端SHA完整相等，发布工作树干净。入口https://github.com/yiichu03/SIGN/blob/b39e3626aae31125f018a81b047a593da71e468b/docs/experiments/frozen-rollout-coverage/README.md。

包内含完整精度4200val汇总、两份模型步数/权重SHA元数据（无权重文件）、前后两版训练图和统计、最新两组全scalar CSV.gz、原生验证日志/TB事件、实际训练/验证config、42项冻结审计、单测/短跑证据、原命令/PBS和分析脚本、根四文档生成快照。未上传checkpoint、场景、环境或原始相机数据；旧phase1历史材料未重新发布。published WORKLOG包含截至PUBLICATION-CHECKED的完整前缀；本条实际push回执在根维护源追加，包内snapshot以manifest生成时点为准。

发布后再次只读核对：原SIGN仍dac8609，coverage训练树仍6983c91；远端同名分支比训练树多本次资料提交，不为此切换/修改/快进训练目录。qstat1496716及1497416均R，两个训练未停止或重启。publication_receipt.json记录远端校验、代码边界与运行状态；STATUS已更新。

### 2026-10-28T01:58:42+08:00 — QWEN-SEMANTIC-COVERAGE-PROPOSAL

用户仅要求1000字以内思考如何用Qwen给出与新增观测覆盖同语义地位的附加reward，本轮为方案讨论，未实现、未推送、未启动/停止/修改任何作业。先读根AGENTS/STATUS及Qwen历史结果；本地可用模型记录为Qwen3.5-9B，旧p12开发集一致不等同新指标可靠，历史成对请求存在位置偏差及低一致，不能直接作为相对奖励。查阅官方模型卡https://huggingface.co/Qwen/Qwen3.5-9B、SENSEI原论文https://arxiv.org/abs/2503.01584、语言抽象探索https://arxiv.org/abs/2202.08938及VLM奖励局限https://arxiv.org/abs/2310.12921；这些支持研究方向，不验证SIGN具体设计。

拟议定义为新增有效观测率：与几何覆盖都奖励episode内新增可辨别空间搜索信息，Qwen输出是语义代理，不估算真实平方米，也不混入成功/总体验证或八环境强制排名。输入按时间顺序RGB和同episode历史关键帧，必要位姿辅助对齐；初始观测只建历史，历史跨rollout保留、episode重置；仅换视角但无新增证据不给正收益，转头确实揭示新空间可得分，同类不同空间不应合并为一类。Qwen为每片段独立给出有效观测比例s∈[0,1]及证据帧，不确定标为缺失并重试、不当零分标签。沿用rollout后/returns前片段末结算bonus=lambda_Q*(L/H)*s，不修改真实mask、冻结或原导航损失。lambda_Q按实际量级校准，不能因几何权重为0.1而照搬。

建议先在独立未用于prompt迭代的小样本上人工冻结参考，验证新增/重复/转头/受困/相似走廊、跨rollout历史、抽帧与分段稳定性及推理开销；通过后再讨论原导航、几何附加、Qwen附加三组独立对照，避免先叠加两奖励造成归因混淆。以上均是待验证提议，无新实验授权或已获训练收益结论。

### 2026-10-28T12:39:12+08:00 — COVERAGE-TRAIN-ONLY-3762M-COMPARISON

用户提出以后或需重制带场景背景的topdown图，但本轮明确只看两个正在运行实验的train指标，不做评估。先只读qstat与两PBS日志、实际保存config、运行源码及git状态；无新增/排队评估作业，两长训练均R。控制台按同一步数筛查近期1M/5M/10M区间，初步指向coverage较低；随后外部CPU脚本logs/gibson_train_check_20261028/analyze.py读取原始TensorBoard，以size_guidance=0保留全部scalar并核查有限性，导出选定指标CSV、JSON与PNG/PDF，既有快照和GitHub资料未覆盖。脚本已实际执行成功，不使用GPU、不运行Habitat，也没有qsub/qdel或改动训练目录。

12:38:33事件快照：基线60211200步、coverage37621760步，29/34类scalar均无非有限值。按共同末步37621760对齐，最近5M每组2442个原生记录：SR87.5435%对85.9980%（-1.5456pp），SPL51.8990%对48.5507%（-3.3483pp），view_match84.5754%对83.0110%（-1.5644pp），导航reward7.532276对7.373540。最近10M每组4883个记录：SR88.0176%对86.0534%（-1.9642pp），SPL52.4010%对48.9063%（-3.4948pp）。20M-25M／25M-30M／30M-35M各自5M区间的SR差-1.7975/-2.5357/-1.5254pp，SPL差-3.6717/-3.6004/-3.2884pp；近期较弱表现跨多个区间，未显示正收益，但仍仅一个种子的训练描述，不能作跨种子因果或验证集结论。

coverage最近5M bonus均值0.135152/rollout、6.59924e-5/环境步（非零），新增面积均值345.9903m²/rollout；导航reward原日志仍不含该bonus。实际config两组stop_step=50000000，trainer在跨阈值后令use_aug_flag=False；基线已过阈值、coverage尚未到，因此最新单点既不同训练预算又处于不同阶段，此观察不归因于某个开关。两源树git状态保持：原SIGN干净、coverage仅旧data软链接未跟踪且因远端资料提交behind1；未pull/切换/修改/停训/推送。

结果comparison.json与matched_training_curves.png；runtime_status.json保存PBS只读核查。本轮没有评估、Qwen推理、topdown图制作或新训练。后续带背景topdown仅作为用户提出的候选工作，不由本条自动触发。STATUS已更新为当前有效结论。

### 2026-10-28T12:50:11+08:00 — COVERAGE-REWARD-MECHANISM-AND-NEXT-TRIALS-PROPOSAL

用户询问现状是否体现探索/减少冗余的作用，以及可尝试的权重或公式小改动；本批仅分析与候选实验讨论，未实现、提交或启动新训练/评估，未修改或停止原作业。沿用12:38:33训练快照，不把本条时间当新运行状态。只读核对src/trainer.py的片段末步bonus=w*(L/H)*(gain/L)=w*gain/H、实际config的H256/N8/gamma0.99/tau0.95/use_gae=True/use_normalized_advantage=False、CostRolloutStorage继承的compute_returns，以及原environment.py的-0.01步惩罚与导航距离变化奖励。查阅GAE原论文https://arxiv.org/abs/1506.02438；局部数值推导以实际源码为准。首次查找src/ppo.py及algos通配路径不存在，纠正为src/algo/PPO.py并核对；没有代码执行失败或运行训练影响。

已实际执行外部CPU CSV汇总和公式计算，保存logs/gibson_train_check_20261028/reward_design_analysis.json（含源CSV SHA）。coverage自身0-5M新增面积/环境步0.140309m²，5-10M0.149537，10-15M0.160033，15-20M0.164180，20-25M0.172461，25-30M0.169699，30-35M0.168765，最近5M0.168941。仅说明该组自身覆盖速率曾提升后趋平；基线无覆盖同指标，且任务/episode分布随训练变化，不能归因于附加奖励，更不能直接声称冗余搜索减少。固定H下原奖励确实鼓励单位采样预算新增面积，L代数抵消不等于完全不鼓励效率；但不区分朝目标的有效探索与偏离目标的新区域，也不直接识别重复搜索。原日志导航reward不含bonus。

最近5M bonus均值6.59924e-5/环境步，约为步惩罚绝对值的0.66%；末步稀疏奖励量级不能只用这个平均数判断策略梯度。固定value预测时，同片段距bonus末步d的直接GAE贡献乘(0.99*0.95)^d：d32约14.04%，64约1.97%，128约0.0389%；不能据此说早期动作完全学不到，critic后续学习及MRQ路径仍存在。

候选单变量试验尚未执行：A保持原公式/边界，仅weight0.1→0.5，用于诊断弱信号，不预设会改善；B保持weight0.1、rollout256和分母256，收完整轮后增加最长32步的子片段末结算边界，同轨迹bonus未折扣总额不变，真实mask和跨rollout覆盖历史不变。B会明确改变用户此前仅episode/rollout边界的设计，作为新方案讨论，不擅自实施。两项不可同时改以免混淆。后续对照应补齐两组覆盖效率、episode长度及SR/SPL；严格冗余搜索需轨迹证据，正常回访/共同通路、碰撞和脱困不能直接算冗余。当前训练/验证差距仍引用COVERAGE-TRAIN-ONLY-3762M-COMPARISON，不做显著性或长期因果断言。

### 2026-10-28T12:59:35+08:00 — COVERAGE-ROLLOUT-VS-SETTLEMENT-EXPLANATION

用户询问当前8环境每次reward计算/更新的步数，提出可能延长步数，并要求展开32步子片段方案。本轮只读实际训练config、trainer采集循环、algo/PPO.py与coverage Measure；未把讨论当作修改或提交新实验的指令。当前每环境256步、8环境共2048条transition后调用一次_update_agent；导航reward/覆盖增量每环境步产生，覆盖bonus在完整rollout后、returns前统一写入各环境真实episode结束及rollout末尾位置，随后PPO更新。PPO为4 epoch×2 minibatch，此外MRQ启用阶段另有10×2次辅助更新，不能将一轮训练说成只进行一次梯度step。每个环境episode独立自动重置，不等8个episode同步结束；未终止episode及其覆盖历史跨rollout延续。

实际训练environment.max_episode_steps=1000（config第21行，另有task配置1000）；与此前完整验证所用500步分开。256是采样/更新窗口，不是episode最大长度或覆盖记忆长度。若8环境H从256加到512，采样批量从2048变4096，同时现公式每平方米bonus由w/256变w/512，固定权重下减半；增加窗口也可能延长片段末步奖励的直接反馈距离，不能只视为增加探索时间。

进一步说明32步候选：保持8×256采样及原PPO循环，整轮采完后，增加第32/64/…/256步等结算边界并叠加真实episode边界；每子片段bonus仍w*gain/256，覆盖记忆仅episode重置，不改真实mask或RNN状态，不实施每32步PPO更新。同轨迹未折扣奖励总和相同，但折扣returns/GAE及训练效果会改变，正是待隔离变量。举例同一episode前32步新增4m²、后224步0：现0.0015625放256，候选放32，后续子段0；不是重复奖励已有面积。依据GAE原论文https://arxiv.org/html/1506.02438v6及已核对源码，在固定value预测时末步bonus的直接贡献按(0.99*0.95)^d衰减；critic与其他训练路径仍可能传递长期影响，不能把系数解释为全部学习能力。仅建议先固定H/权重、独立对照结算间隔，不同时调长H和调weight；未实施该新结算规则。

### 2026-10-28T13:13:58+08:00 — COVERAGE-SETTLE32-IMPLEMENTED-CPU-PASSED

用户批准保持8×256、weight0.1的32步子片段结算对照并要求实施、提交训练。已核对两原作业1496716/1497416均R并保存两源树HEAD/分支/全部跟踪文件SHA至logs/gibson_coverage_settle32_20261028/protected_worktrees_before.json。远端yiichu03/SIGN coverage分支b39e362已核对，新增独立worktree SIGN-frozen-coverage-settle32和分支phase2/frozen-coverage-settle32，从b39e362建立（训练源码与6983c91一致）。data是本地忽略目录，内含到SIGN/data各资源的软链接；新工作树干净，不修改原训练目录。首次查找旧日志目录的rollout_coverage.yaml不存在，改读实际src/config/rollout_coverage.yaml，无运行影响。

仅训练源码增加9行和YAML两行：settlement_interval默认0、拒绝布尔/非整数/负数；正整数在复制出的ends数组增加rollout固定网格结算边界，真实episode边界仍保留，真实mask不变，分母H不改。另提交8项CPU单测和独立实验README。已实际执行8新测试+原9回归全部通过；外部preflight用原代码方法比较10组H/weight/随机done/奖励，默认0的奖励和指标完全一致；实际native合并config仅多interval32/对应CLI与输出路径，eval合并配置字节一致。无GPU模拟在登录节点运行。git diff --check、支持脚本编译、两PBS脚本bash -n通过。

本地commit a7cc9e09fe3c0a9abfa054307cfb80474217d1a2（Add configurable coverage reward settlement intervals），尚未push。source_manifest.json固定本实验所有跟踪文件；check_inputs.py会验证两原工作树和数据。拟提交同GPU短跑interval0/32各40960步，再核对指标有限、42项encoder状态不变、bonus守恒、首rollout同面积/同总奖励。通过后才提交全新独立输出的长训练；目前未提交长训练、未调整权重/rollout/评估或停止旧任务。

### 2026-10-28T13:15:11+08:00 — COVERAGE-SETTLE32-GPU-CHECK-QUEUED

已实际执行qsub logs/gibson_coverage_settle32_20261028/short_checks.pbs，返回1502328.stdct-mgmt-02，personal-e1538633/auto、1A40/36CPU/240GB/2h；提交登记short_submission.json。source/input保护检查通过。首次qstat为Q，comment为Not Running: Insufficient amount of resource: node_pool；作业尚未运行，因此pbs日志尚不存在（tail显示cannot open），不当作训练失败或短跑通过。本轮未重复提交、改路由或终止任何原作业。正式训练脚本已经准备，含短跑passed门禁及独立输出保护，尚未qsub。

### 2026-10-28T13:23:08+08:00 — COVERAGE-SETTLE32-GPU-PASSED-TRAIN-SUBMITTED-PUSHED

GPU短跑1502328于GN-A40-043成功完成，PBS F/Exit_status=0、总walltime00:06:02。interval0/32各40960步、20次更新；全部scalar及模型权重有限，42项encoder状态与公共nav_model.pth逐位相同，实际config验证train_encoder=False/8×256/seed100/weight0.1及对应interval。首轮参数更新前两组新增面积、bonus总和及导航指标相同。每rollout bonus均验证0.1*area/256；interval0累计面积2109.420013m²、bonus0.823992191；interval32累计面积2133.590004m²、bonus0.833433593。后半段稳定吞吐343.935/345.638步每秒，接近；不同奖励位置使后续轨迹不同，该比率不是纯结算计算开销，更不证明学习收益。short_summary.json、short_results.json、两原生日志/config/checkpoint/TB均保留。

短跑通过且check_inputs重新核对自身源码/两原源树/数据后，已实际执行qsub train_personal.pbs，返回1502352.stdct-mgmt-02。正式个人auto，1A40/36CPU/240GB/168h，seed100/hash0、8×256、weight0.1、settlement_interval32、原300M上限/每250更新保存/每更新TensorBoard；新目录train_personal_8env，从公共encoder及原随机后端初始化，不接短跑权重。training_submission.json登记命令/参数/输出。初查Q，node_pool资源不足，尚未声称正式更新已发生。没有额外评估作业，也未实施weight0.5或延长rollout。

已在新分支普通push --set-upstream origin HEAD:refs/heads/phase2/frozen-coverage-settle32，远端创建成功，ls-remote完整SHA=a7cc9e09fe3c0a9abfa054307cfb80474217d1a2与本地相同，pushRemote=origin。新commit仅4文件，训练代码11行增加，另8项单测与实验README；未发布新权重/数据/环境或手工复制根文档。新工作树干净。publication_receipt.json记录发布与作业状态。两旧训练1496716/1497416再核对均R，原目录HEAD/跟踪源码SHA仍符合保护快照，未切换/修改/停止。根AGENTS、STATUS、RUNBOOK已更新新实验入口。

## 2026-10-28T13:32:27+08:00 — HABITAT-GS-IMAGENAV-INVENTORY：官方训练／评估数据规模核对

- 用户询问Habitat-GS ImageNav数据量。已执行只读在线核查：官方HF数据卡 https://huggingface.co/datasets/RukawaY/gs_scenes#-about-this-dataset 明确ImageNav train110000、val1900，总111900；场景train110（55自建+55InteriorGS）、val19（10自建+9InteriorGS），合计129。
- HF API当前main仍为ea6453855938dd3d4395c4c449fedefb7e6603b7，与现有下载固定revision相同。递归目录API实际列出train110个content任务文件+空入口、val19个content任务文件+空入口；压缩字节合计9365934／173560。ImageNav顶层仅train／val，无独立test目录。此处总episode条数采用官方数据卡，未逐文件全量下载重数；HF网页n<1K标签不代表真实episode数量。
- 本地CPU读取实际content文件确认：train0场景／0条，val仅scene56／100条，原GPU只评估其中10条。没有下载新的场景、任务包，未提交实验或更改运行中训练。当前规模摘要已加入STATUS；无需新增文档／数据副本。

### 2026-10-28T13:34:51+08:00 — QWEN-TOPDOWN-RELATIVE-REWARD-GRPO-PROPOSAL

用户要求1000字初步方案：八环境topdown加描述，让Qwen相对打分，并借鉴GRPO反馈SIGN训练。本批仅研究讨论，未生成图像/采轨迹/运行Qwen、未修改源码或提交/停止作业。核对当前settle32的_add_coverage_bonus接口、根AGENTS关于重复搜索/并列/未知与组的规则，以及旧Qwen成对试验A1偏选首位22/24等记录。旧开发集一致不代表独立验证；八个并行环境未按同一条件任务组采样。

阅读原始论文：DeepSeekMath/GRPO https://arxiv.org/html/2402.03300v3 （4.1，同一问题多输出、组内相对优势；其原算法直接使用优势且去除value模型，不是把标准化分数加到PPO reward再过GAE）；SENSEI https://arxiv.org/html/2503.01584v2 （成对VLM语义兴趣偏好蒸馏为探索reward）；VARP https://arxiv.org/abs/2503.13817 （在视觉观测叠加轨迹以支持偏好判断）；多图位置偏差 https://arxiv.org/abs/2503.13792 （CVPR2025，候选图顺序影响推理）；LRM https://arxiv.org/abs/2603.16065 （2026-09-30 v3，专门训练VLM提供进度等reward用于机器人PPO）。这些结果的任务/模型不同，不能作为Qwen在SIGN有效的证据。额外查阅NavOne topdown规划、VLM-PBRS等检索结果，但不据此声称已验证本方案或改变当前奖励定义。

拟议分工：程序计算几何面积/步数/碰撞；Qwen判断新增观测的信息价值、重复搜索与必要回访。输入同尺度topdown背景、可见性/历史/新增区分、时间与方向轨迹，配少量关键RGB及目标图、短结构描述；真实未知区域标明未知，不能凭地图线条推断未观察语义。保留同episode历史跨rollout，任务重置才清空。先证据区间，再成对偏好/并列/未知；采用均衡比较、候选交换复核而不是改变帧时间顺序，汇总相对评分，不强制8种名次。碰撞、卡住、脱困、共同通路及必要返回不直接算重复搜索。

GRPO式分组需同场景/目标/起点/采样预算，中途片段还要共同前缀历史及相应策略状态；这需要新的采样组织，不能把现有八条不同任务归为同一问题。若保持原采样，可先分别与固定参考样例比较，得到可校准的评分，不能称为同任务组相对GRPO。建议先在离线可比组验证Qwen，再讨论在线采样器。

仅候选训练公式：z_i=clip((s_i-mean_group)/max(std_group,sigma_floor),-c,c)，b_i=beta*(L_i/256)*z_i；低差异组需抑制噪声，未知重试或跳过该组Qwen附加项，不把未知作为0分标签。保留导航reward，Qwen替换几何附加项做独立对照；在完整rollout后/returns前把b放32步子片段末，真实mask保持。beta须按实际优势量级校准，不能照搬面积权重0.1。这个最小接入是GRPO启发的reward shaping，并非原GRPO；真正GRPO需另改优势估计/策略目标，不能声称单加标准化bonus已实现。

建议固定Qwen版本与提示词，用未参与prompt调整的人工参考检验偏好、并列、未知、换序稳定性和单位请求开销；通过后原导航/几何附加/Qwen附加三组对照，再考虑蒸馏小reward模型减少推理成本。相对分组均值构造为0，不能作为学习收益；保留固定参考标尺的原始分、覆盖/步、SR/SPL和严格重复搜索证据。全为提议，无实现或新实验授权。

### 2026-10-28T13:35:11+08:00 — QWEN-PROPOSAL-STATUS-ANCHOR-REFRESH

承接QWEN-TOPDOWN-RELATIVE-REWARD-GRPO-PROPOSAL：研究条目已成功追加，但首次STATUS插入脚本因旧章节日期锚点2026-10-26不存在而AssertionError，STATUS当次未写入。重新读取发现Habitat-GS章节已更新至2026-10-28并增加官方库存记录；保留这项已有更新，使用局部patch加入本轮Qwen方案摘要，未回滚或覆盖其他内容。只修复文档插入位置，没有训练操作。

## 2026-10-28T13:35:14+08:00 — HABITAT-GS-STORAGE-CAPACITY：完整数据体积与个人剩余空间

- 用户询问数据体积与存储是否足够。已执行只读HF tree API递归分页统计（固定revision ea6453855938dd3d4395c4c449fedefb7e6603b7，1213文件），总97509335986字节=97.509GB；train资产24572715073字节、val资产3426127187字节，二者共27.999GB。只取train／val的.gs.ply与.navmesh、全部ImageNav任务、train／val场景配置和两份ImageNav配置为393文件、26695345591字节=26.695GB。官方卡标全库约95GB、场景约27GB，为近似值；本次使用实际远程文件size，不下载数据本体。VLN轨迹为68863591771字节，是全库最大部分。
- df -B1 /scratch实测可用20605772496896字节（约18.74TiB，df -h显示19T），共享卷使用98%；此数不是个人配额。通用quota -s与quota -s -f /scratch失败，原错Cannot connect to RPC quota service；lfs不存在，myquota不存在（不能套用NSCC的配额）。
- 查本地Vanda手册和hpc脚本确认应用hpc s。已执行返回scratch57.58G／500.00G、11.5%，余约442.42G；home17.55G／40G。管理员原始scratch配额快照修改时间2026-10-28 13:30，Hard Exceeded: No；其统计口径FSLogical，Physical含开销62.97G。当前GS目录du -sh为134M，NFS块计数与原111.4MB逻辑资产量不同。全scratch的du -sx扫描设置45秒超时，未用不完整扫描替代配额读数。
- 容量足以放完整ImageNav或全库；后续ImageNav建议按GS+navmesh+任务选择约27GB、预留40–50GB工作空间（规划估计，不含新增大量训练checkpoint），避免无关VLN与重复缓存。已更新STATUS和RUNBOOK，不下载、删除或调整运行中任务。

## 2026-10-28T13:38:02+08:00 — HABITAT-GS-FULL-DOWNLOAD-PLAN：用户批准完整ImageNav下载

- 用户已批准按前述范围下载：固定HF revision ea6453855938dd3d4395c4c449fedefb7e6603b7，train110+val19场景的.gs.ply／.navmesh、110000+1900条ImageNav与必要配置，预计393文件／26695345591字节；不包含mesh／avatar／VLN。唯一数据目录继续使用SIGN/data/scene_datasets/gs_scenes，新GS工作树data软链接复用。
- 已检查SIGN-habitat-gs为experiment/habitat-gs-imagenav @24b4c02且干净，无内层AGENTS。hpc s显示scratch57.58G／500G，共享余19T。现有3个Gibson GPU训练1496716／1497416／1502352均R，不调整它们。
- 分析方案：扩展既有prepare_data.py支持全场景及只校验模式，按官方size与LFS SHA256／Git blob SHA1校验；已存在文件直接复核，缺失文件原位.part下载后原子改名，有限4并发、支持部分文件续传，不引入第二份HF缓存。长期下载使用auto CPU PBS入口，输出同一下载日志和一个全量manifest。完成后实际读取全部任务验证场景、条数与引用，再报告占用；当前尚未启动下载。

## 2026-10-28T13:38:55+08:00 — HABITAT-GS-FULL-DOWNLOAD-SUBMITTED：全量下载器预检通过并进入auto队列

- 在SIGN-habitat-gs扩展既有prepare_data.py，增加all-scenes／plan-only／verify-only、4并发、原位续传与校验；新增download.pbs并在原README加入口导航。Python3.9语法编译、bash -n、git diff --check通过。实际plan-only列393文件／26695345591字节、本地6文件；verify-only复核已有scene56全部哈希与100条任务通过，临时结果仅/tmp/habitat_gs_scene56_verify_20261028.json，没有修改旧资产或旧manifest。
- 已本地提交d291c448f5059debc8f2fad63ebda4cd5757ef4f，未push。实际qsub返回1502380.stdct-mgmt-02，auto／CFP04-SF-109／4CPU／8GB／4h。唯一提交记录logs/habitat_gs_20261028/download_submission.json含脚本哈希／代码提交，PBS输出download.pbs.log。
- 最终清单manifests/habitat_gs_imagenav_20261028.json将在所有393文件哈希与任务库存通过后生成；当前只证明预检／提交成功，没有声称全部下载完成。RUNBOOK已补充复用／续传／核验流程。

## 2026-10-28T13:42:23+08:00 — HABITAT-GS-EPISODES-DOWNLOADED：全部原始任务已读取核对，场景传输继续

- 1502380已在CN-017的batch_cpu运行，脚本保持4并发。已下载全部131个ImageNav gzip文件及配置；实际CPU逐文件读取content确认train110场景、每场1000、共110000；val19场景、每场100、共1900。原官方train／val场景配置分别引用110／19个navmesh。
- 当前总数据含part约3.34GB／26.70GB（12.5%），日志已校验161/393；场景正在传输，尚无完整全量manifest。原位.part用于未完成文件，正式文件已过官方哈希；无第二缓存。完成后再给出所有资产的最终结果，不将任务文件完成混称场景全量完成。

### 2026-10-28T13:50:17+08:00 — QWEN-TOPDOWN-STATIC-PREVIEW-EXPORTED

用户提供topdown_reference.png，授权参考样式导出给Qwen的候选图片供人工审核，倾向不展示复杂时序。已实际执行离线CPU导图；未调用Qwen、未改训练源码/作业、未push。参考图只作为样式，实际地图来自本地navmesh，路径来自原始waypoints，不从旧PNG擦线或生成虚构背景。

证据目录logs/qwen_topdown_preview_20261028，脚本export_preview.py，manifest.json保存来源/地图/输出SHA、视域设定与局限。首先发现旧原始trajectory.png对应map_resolution512，1024探针shape加倍；改按原图尺寸推断并严格核对栅格shape。初选group03有较多点不在起始楼层切片，无法从缺少逐步Y的旧记录确认楼层变化，故该次材料移至rejected_group03保留，不作为推荐图。floor_audit.json记录10组粗筛；最终group10所有前256步位置在navmesh有效区或2像素邻域，最大约1.414像素，8条任务scene/start/episode_id相同，目标图SHA只有1种。边缘像素误差不视为碰撞或冗余。

最终8条均取真实前256步，历史HM3D v0.2资料（不是当前Gibson训练），同尺度灰色可行走navmesh背景、深蓝窗口前已见、浅蓝窗口新增、红路径、绿起点/深色终点。A静态版不标中途时间；B只加64/128/192/256四处朝向与步数，已调整标签避让并实际查看。各8张独立PNG、两8图总览、A/B对照、C01后续257-316窗口图，共20PNG，PIL校验及人工视觉查看通过。第二窗口保留前256步覆盖记忆及淡灰历史线；不是512步补齐。最初第二窗口文件名写成257_500，内容标题实际257-316，已改生成器与最终文件名，初稿重命名history_window_257_316_initial.png保留。

覆盖是原栅格精度下3m/90度的固定起始楼层二维视域重建，初始视野不计新增；不是训练0.1m网格的实测面积，不等于RGB真正可见表面积。完整灰色背景属于训练侧额外几何信息，不是策略输入。图片不含成功率/策略名称/面积数值/排名，避免暗示评分；参考图覆盖曲线未放进Qwen候选。topdown_review.zip仅含20图、manifest与生成脚本，不含未采用稿。

建议主输入先采用A，B作为方向/先后有歧义时的对照；静态路径重叠仅说明重复经过，不能单凭此确认无效搜索，必要回访/脱困需保留未知或补RGB。统一收256步不等于同一episode完整结束；当前32步结算版本若需逐片段Qwen评分，单张256总览不能直接提供各段归因，后续须另设计简洁片段定位。当前仅完成输入格式样例，等待用户审核，不据此启动裁判评测。

## 2026-10-28T14:00:01+08:00 — HABITAT-GS-FULL-DOWNLOAD-COMPLETE：完整静态ImageNav数据下载校验完成

- 已实际完成PBS1502380.stdct-mgmt-02，CN-017／batch_cpu／4CPU，qstat -xf确认Exit_status=0、walltime=00:19:48。执行代码d291c448f5059debc8f2fad63ebda4cd5757ef4f。唯一资产目录SIGN/data/scene_datasets/gs_scenes，新工作树仍data -> ../SIGN/data。既有三组GPU训练1496716／1497416／1502352均继续R，未调整。
- 下载器最终393/393文件逐个通过官方size与LFS SHA256／Git blob SHA1；复用6、下载387，合计26695345591字节=26.695GB。完整manifest为manifests/habitat_gs_imagenav_20261028.json（179474字节），固定HF ea6453855938dd3d4395c4c449fedefb7e6603b7。原scene56清单保留，不生成数据副本或全量HF缓存。
- 下载器已实际读取全部任务验证train110场景／110000条、val19场景／1900条、episode_id在每场唯一、scene_id引用及GS／navmesh存在。登录节点随后独立检查manifest路径集合与实际文件集合完全相同、393文件大小全部匹配、无part或额外文件；train110／val19个官方navmesh配置引用全部解析到本地。没有重新读取26.7GB做无必要的第二轮哈希，也没有新跑GPU评估／训练。
- 原始输出logs/habitat_gs_20261028/download.pbs.log；download_submission.json已追加completion字段记录最终状态／manifest SHA／库存／复用数。登录节点紧接PBS结束首次test -f暂未看见manifest、返回1，随后ls及完整读取成功；未因此重新提交或下载，最终文件审核通过。du -sh为21G，与26.70GB逻辑文件大小属于不同统计口径。hpc s当前仍读13:30快照57.58G／500G，不能报告为下载后的实时占用。
- STATUS／RUNBOOK已更新完整就绪和复现入口，新GS工作树干净且未push。完整数据仅覆盖静态ImageNav必需GS／navmesh／任务／配置，未下载无关mesh／avatars／VLN；当前用户下载目标完成。

### 2026-10-28T14:19:26+08:00 — QWEN-STATIC-FIVE-GROUP-DEVSET-EXPORTED

用户选择无中途步数/朝向标记的static图，要求导出覆盖占比、5个不同场景各8条同任务历史HM3D轨迹，用于prompt调整；追加要求评分方案1000字以内。本轮已实际离线CPU导出，未调用Qwen、未产生AI评分/人工真值、未改训练或提交/停止实验。重新对10组执行2像素容差底图对齐审计，排除group02/03，选group01/05/06/08/10；每组8条scene/起点/episode一致且目标PNG哈希唯一。选择依据是数据对齐与轨迹长度，不是表现排名；历史数据此前用于prompt开发，明确不是独立测试集。

目录logs/qwen_static_dev5_20261028，audit.py/floor_audit.json记录筛选；build.py+render_template.py生成图。提供window256（每episode最多前256步，提前结束保留实际步数）与matched_prefix（组内相同前缀长度34/46/110/85/256步）两套。共80独立静态PNG+10组总览，coverage.csv共80行，manifest.json保留源JSON/地图SHA、参数、2像素对齐检查及图片哈希；全部图片解码/哈希/百分比算术通过并实际查看group06样图。相同前缀组可能较短，仅用于公平性诊断，不能替代长轨迹重复搜索观察。

覆盖率定义为初始视野加后续新观测的可行走栅格并集/整个起始高度navmesh有效栅格（灰色+蓝色），不含白背景，绘图红线标记不参与计数。新增覆盖率扣除初始视野，另列m²与新增面积/实际步数。3m/90度、原栅格精度下重算的二维视域代理，非训练0.1m网格实测，非RGB真实面积；整张可行走截面可能含不可从起点到达部分，此次没有改成起点可达连通分量分母，不跨场景直接排名。

scoring_prompt_zh.txt为894字符初稿：先可见证据，再28对组内比较a_win/b_win/tie/unknown；s_i=(胜场+0.5*平局)/7，有未知的候选返回null，不强制各不同名次或每组达到0/1。覆盖率作为辅助，不将路径重叠、碰撞、卡住、脱困、共同通路、必要回访直接计为重复搜索；不能从静态线条编造时间/次数/搜索意图。aggregate_scores.py对28对完整性/唯一性/枚举作验证并复算，合成全并列与未知传播检查通过；这不代表真实裁判质量。后续需要换序稳定性、人工冻结参考与独立保留集。

qwen_static_dev5.zip包含90图、CSV、manifest、初稿和生成/聚合脚本，未含权重、原相机序列或训练数据大资产。本轮完成导出与评分草案，未运行prompt搜索或裁判推理，等待用户审阅。

## 2026-10-28T14:25:05+08:00 — HABITAT-GS-FULL-EVAL-PLAN：公开SIGN权重的完整验证集评估

- 用户明确要求提交原始SIGN在评估集上的完整SR／SPL实验，使用公开checkpoint。结合当前会话，此评估集为Habitat-GS val的19场景／1900条。已读取当前四文档、实际分支／任务和下载manifest；现有3个Gibson训练继续R，不修改或停训。
- SIGN-habitat-gs为experiment/habitat-gs-imagenav @d291c44，工作树干净。已实际git diff dad87fe -- src核查：仅dataset的GS元数据补齐、CameraSensorSpec向量转换、policy删除未使用nis导入；trainer／网络计算／动作／奖励／指标保持作者基线。不能拿当前SIGN冻结／coverage训练分支代替原始算法。
- 方案：沿用原eval的6并行、500步、128×128、连续动作、原成功／SPL及安全模型，显式val、全部content_scenes、1900条，seed100／PYTHONHASHSEED=0。公开nav_model.pth与safety_model.pth按已知SHA256守卫；先CPU验证合并配置、全部任务／NavMesh／测地距离与源码边界，再经autox／A40提交独立完整评估。原run_sim.py／trainer实际执行，外部入口只负责预检／调用／提取结果，不monkeypatch或改训练源码。

## 2026-10-28T14:27:57+08:00 — HABITAT-GS-FULL-EVAL-SUBMITTED：完整验证集CPU预检通过并提交GPU

- 新增scripts/habitat_gs/evaluate.py与evaluate.pbs，并在既有README导航。入口只预检／调用原run_sim／提取TensorBoard，不修改src。语法编译、bash -n、git diff --check通过；本地提交95eef9bf497bc1d010c7a4b35030fdce4123dce7，工作树干净，未push。
- 已在GS独立环境执行CPU-only预检：19场景／1900条唯一任务，全部可达，最大测地距离误差0.0；6并行、val、全部场景、500步、128输入、连续动作、1m、seed100/hash0、原SIGN／SafeNavNetPolicy，禁用视频且每任务1次。导航SHA03fa71b514c8ee2fa272d6276499d51313a43b7d71bb31181c0150cc7c050d1a、安全SHAb84d291e84216defb730d07d03cb6f25e3555ae447eb1e69057f3427b3c7ec31均匹配。预检原输出logs/habitat_gs_eval_20261028/preflight.log；GPU未在登录节点初始化。
- 实际qsub返回1502487.stdct-mgmt-02，autox／CFP04-SF-109／A40／6h，GS_SOURCE_COMMIT锁定95eef9b。提交JSON保存时间／完整命令／脚本与预检哈希，位于logs/habitat_gs_eval_20261028/submission.json；PBS输出full_val.pbs.log。运行目录SIGN-habitat-gs/results/habitat_gs_full_val_20261028/job_1502487/，全部1900/1900完成且指标有限后才产出result.json。
- 这次为完整GS val上的原始SIGN协议迁移评估，不使用冻结／coverage权重，也不改成官方GS离散动作DDPPO协议。当前只是预检和提交成功，尚无完整SR／SPL；现有3个Gibson训练不受影响。

## 2026-10-28T14:32:05+08:00 — HABITAT-GS-FULL-EVAL-RUNNING：A40正式评估已开始完成任务

- 1502487已在GN-A40-023进入batch_gpux，实际A40／驱动575.57.08／46068MiB；PBS将资源规范为36CPU／240GB／6h。计算节点重复预检通过并生成inputs.json，6个Nav-Drone环境初始化／公开权重加载后进入原trainer评估循环；检查时真实进度15/1900，作业仍R，无终止错误。
- 已实际读取eval/eval_run0_/config_of_eval.yaml，确认num_environments6、test_episode_count1900、val、content_scenes=['*']、500步和ckpt/nav_model.pth，与计划一致。运行证据与输入哈希集中SIGN-habitat-gs/results/habitat_gs_full_val_20261028/job_1502487/；原始进度在evaluation.log，PBS预检日志logs/habitat_gs_eval_20261028/full_val.pbs.log。
- submission.json已补运行核验时间／节点／进度／结果目录。当前用户的完整评估提交请求已落实，实验独立继续运行；没有将部分任务结果当作完整SR／SPL，result.json仅在全部完成后生成。保留原三个Gibson训练，不重复提交。


## 2026-10-28T14:38:26+08:00 [GIBSON-TOPDOWN-PILOT-SUBMITTED]

- 用户授权用公开SIGN权重采集Gibson静态topdown示例，若需新采集则一两组同任务不同轨迹。331份既有waypoints未发现Gibson逐步轨迹，准备Edgemere episode200和Denmark episode3800，各8次策略原生随机采样、最多256步，固定组内起点/目标；不是标准确定性评估。
- 独立脚本和输出：logs/gibson_topdown_pilot_20261028；collect.py使用公开完整导航及安全权重、实际逐步XYZ/朝向；render.py生成静态覆盖图和覆盖比例，不调用Qwen、不训练。两脚本AST检查通过，运行与图片尚待验证。
- 已执行qsub collect.pbs：沙箱首次报mkstemp: Read-only file system（/var/tmp），获工具提权后提交1502509.stdct-mgmt-02，auto→batch_gpu／personal-e1538633／A40／2h；当前Q，node_pool不足。qstat短ID报illegally formed job identifier，改完整ID成功。
- 三个原训练工作树HEAD和源码SHA核对未变；未停止或修改训练。plan.json、protected_sources.json、submission.json留证。等待作业运行，不能将已提交称为导图完成。


## 2026-10-28T14:41:41+08:00 [GIBSON-TOPDOWN-PILOT-GPUX-RUNNING]

- 用户要求改gpux；核对RUNBOOK个人项目不支持autox，使用已授权CFP04-SF-109。qdel撤销尚未启动1502509成功。首次新提交工具被用户中断，随后核对队列与脚本均无新采集任务，未发生重复提交。
- 用户调整权限后，已执行qsub logs/gibson_topdown_pilot_20261028/collect_autox.pbs，返回1502516.stdct-mgmt-02；实际batch_gpux、R、GN-A40-025。原三训练与GS评估均R，未干预。待采集、导图与验证。

## 2026-10-28T14:44:17+08:00 — HABITAT-GS-PUBLICATION-PLAN：用户授权推送代码与最新进展

- 用户明确要求将Habitat-GS分支最新进展推送到yiichu03 GitHub。已核对SIGN origin有效push URL为git@github.com:yiichu03/SIGN.git，目标experiment/habitat-gs-imagenav，远端当前无该分支；源工作树95eef9b且干净。相对origin/main待发布5个代码提交，没有新增权重／资产提交。
- 完整评估1502487仍R，GN-A40-023，核查时117/1900，未生成result.json；不是完整SR／SPL结果。保留运行目录HEAD95eef9b，不为资料同步修改或切换源码。
- 沿用既有资料发布模式，但coverage构建器／工作树锁定自身实验，不直接复用。为GS新建临时detached工作树，新增docs/experiments/habitat-gs-imagenav资料及根README导航；完成后普通push HEAD到明确目标并核对远端SHA，再移除本轮临时工作树。发布包包含小样本已完成结果、完整数据manifest、明确标记的进行中评估快照及根四文档生成副本；不上传场景、环境、额外权重或大相机数据。

## 2026-10-28T14:46:51+08:00 — HABITAT-GS-PUBLICATION-READY：生成资料包及发布检查通过

- 已执行git worktree add --detach SIGN-habitat-gs-publication 95eef9b；没有改动SIGN-habitat-gs的HEAD／源码。新GS构建器logs/habitat_gs_publication_20261028/build_publication.py复用既有发布规范，独立选取GS证据；旧coverage脚本／工作树未改。
- 已实际生成并检查23文件、566204字节，包含已完成pilot结果／探针／一张预览、全量数据manifest／完成记录、完整val的输入／实际配置／提交与进行中日志截面，以及四根文档自动副本、构建器和发布SHA清单。状态快照2026-10-28T14:45:55+08:00，168/1900、R、无完整result.json；README明确完整SR／SPL未产生。
- 文件哈希／gzip解压SHA／相对链接／体积／凭据模式检查通过；src／exp_config／scripts／run_sim.py／ckpt相对运行代码零差异，目标URL与分支再次锁定yiichu03/SIGN／experiment/habitat-gs-imagenav。后续普通push后核对远端SHA；最终回执仅追加根WORKLOG，不为自包含回执循环生成包。


## 2026-10-28T14:47:37+08:00 [GIBSON-TOPDOWN-PILOT-EXPORTED]

- 1502516.stdct-mgmt-02（CFP/autox→batch_gpux）Exit0，A40，walltime1分32秒；公开完整导航+安全权重，采集Edgemere episode200、Denmark episode3800，各8条同任务随机策略轨迹。组内起点/初始RGB/目标图一致性SHA通过，各8条不同轨迹；实际步数31–39、36–225，均真实提前结束，未填充到256步。不是标准确定性评估或等预算排名证据。
- 已导出16张静态单图、2张组图、coverage.csv、逐步XYZ/朝向/动作、原始0.1m覆盖mask及精细显示mask，打包logs/gibson_topdown_pilot_20261028/gibson_topdown_pilot.zip。无中间时序标记；总覆盖包含初始视野，新增覆盖扣初始，分母为当前高度可通行栅格，白色无效区不计。
- 初审发现原0.1m栅格初始覆盖为0。CPU pathfinder审计确认真实起点snap_point不变，但栅格起点落在边界外1–2像素；无跨楼层（grid_changed_steps均0）。仅导图改用0.025m，视野射线原点在必要时投到最近有效像素，最多0.0500米；路径位置不校正，原mask/轨迹保留，训练源码/奖励未动。证据map_audit.json、display_reconstruction.json。覆盖是二维navmesh视域代理，不是实际RGB可见表面积。
- audit_maps首次Magnum Vector3.tolist失败（only four-component swizzles are supported at most），改list；随后float32 JSON失败，显式default=float修复。rebuild_display第一次因scipy索引int32触发Numba TypingError，改int64后通过，原错误rebuild_display.log保留，成功日志rebuild_display_retry.log。其后render.py完成重绘打包。
- 两组overview人工视觉初审完成；Denmark可见绕行差异，Edgemere短轨迹差异小；未将重复路径自动标为冗余搜索，未调用Qwen。三个训练工作树HEAD与全部受保护源码SHA末次核对未变。
- 已执行复现：envs/sign-baseline/bin/python logs/gibson_topdown_pilot_20261028/rebuild_display.py，再render.py；CPU离线重建不需GPU。原collect_autox.pbs保留提交时版本，若未来重采须在新输出目录且先collect、再rebuild_display、最后render。

## 2026-10-28T14:48:08+08:00 — HABITAT-GS-PUBLICATION-RAW-CONFIG-FORMAT：保留原始配置字节并完成分域格式检查

- git diff --cached --check曾报告两份原生config_of_eval.yaml各7处空值冒号后的trailing whitespace。它们来自实际run_sim序列化输出，不是新代码／人工说明格式错误；为保留证据与原SHA不修改原文件。已独立逐字节核对发布件与两份服务器原配置一致。
- 已对相对95eef9b的其余所有提交内容执行git diff --check（仅排除上述两份明确的原始YAML），通过；完整发布清单仍验证这两份原文件的大小／SHA。资料提交d1f5aa5只含README及docs，未改运行源码、配置或权重；后续普通push并留回执。

## 2026-10-28T14:49:27+08:00 — HABITAT-GS-PUBLISHED：yiichu03分支发布完成并验证远端

- 已执行普通git push origin HEAD:refs/heads/experiment/habitat-gs-imagenav，目标有效URL为git@github.com:yiichu03/SIGN.git，成功新建远端分支；git ls-remote随后核对远端提交d1f5aa52df7de9004014cc3e91cef6ac1c84c1be完全一致。回执含实际命令／输出／时间／有效URL与已核验SHA，保存在logs/habitat_gs_publication_20261028/push_result.json。
- 已推送5个接入／下载／评估代码提交及1个资料提交。新增资料位于docs/experiments/habitat-gs-imagenav，23个内容文件约568KB加发布manifest；包含带真实时间／未完成标记的完整val快照，不能当作最终SR／SPL。两份原始配置尾空格按原字节保留，其余内容格式检查通过，详见前条RAW-CONFIG-FORMAT；全部发布hash／gzip／相对链接／体积／凭据模式检查通过。
- SIGN-habitat-gs仍HEAD95eef9bf497bc1d010c7a4b35030fdce4123dce7、干净；1502487仍R，GN-A40-023，核查walltime20分15秒。只设置origin同名分支跟踪与pushRemote，远端比运行分支多一个资料提交，不pull／切换／重启当前评估。旧Gibson与coverage工作树及依赖origin均未改。
- 已用git worktree remove移除本轮创建且已提交／干净的临时SIGN-habitat-gs-publication，避免留下重复工作树；资料保存在本地Git对象和远端，构建器仍位于专属logs目录。根STATUS／RUNBOOK更新；这条最终回执追加在发布快照之后，不循环生成新的相同资料包。


## 2026-10-28T15:22:26+08:00 [QWEN-TOPDOWN-OFFLINE-ENGINEERING-IMPLEMENTED]

- 用户要求先实现Qwen工程并讨论同任务8episode采样风险。核对当前VectorEnv：按场景分配环境、seed+i，done后独立自动reset；8×256不是8条完整episode，改相同初始任务也不保证后续窗口条件可比。GRPO原论文同question多输出仅支持同条件组内比较动机，不能由此认定导航训练无风险。
- 已执行git worktree add -b phase2/qwen-topdown-judge SIGN-qwen-topdown-judge a7cc9e0；原三个训练目录与GS目录未动。新增核心src/qwen_topdown.py、CLI、默认关闭JSON配置和11项测试；独立于Habitat/PPO，无trainer/网络/measure修改。外置prompt、8图同请求、同task/start/goal/policy验证、默认拒绝不等步数、SHA冻结输入、严格输出合法性、未知null与并列保留、默认关闭不加载模型。训练采样和奖励映射仍待方案明确。
- 11项unittest通过，实际disabled CLI返回disabled且未创建回答目录。基于已采集两个Gibson组准备请求，显式allow-unequal-steps并写入诊断警示，不算公平效率排名。输入与生成器保存在logs/qwen_topdown_engineering_20261028。
- 已执行qsub smoke.pbs返回1502697.stdct-mgmt-02，CFP04-SF-109/autox→batch_gpux/A40/30min，当前Q/node_pool不足。只检查8图输入和图例JSON，不实施评分；当前尚无真实Qwen回答或GPU性能验证。源码SHA在source_manifest.json。
- 已读官方Qwen3.5-9B模型卡https://huggingface.co/Qwen/Qwen3.5-9B、DeepSeekMath论文https://arxiv.org/html/2402.03300v3；结合本地transformers5.17处理接口，无依赖升级或历史monkeypatch移植。


## 2026-10-28T15:24:57+08:00 [QWEN-TOPDOWN-FIRST-GPU-AND-STRICT-JSON-RETRY]

- 本地提交588d94f，新增4文件280行，工作树当时干净，未push。GPU1502697实际R后结束，Exit0、walltime1分50秒；八图2692输入token、107输出、生成9.7939s、峰值18.4096GiB，无截断。原始回答正确列C01–C08并解释图例，但包在Markdown代码块中，严格JSON判invalid_response，parse_error=Expecting value: line 1 column 1 (char 0)。Exit0不等同JSON合格，保留gpu_smoke_01/response.txt与audit.json。
- 当前transformers对旧images_kwargs位置给迁移提醒，改为processor_kwargs字典；新增编码图数量必须8的断言，以及CLI无效回答退出2，便于PBS检查。依旧不修剪原回答／自动修复JSON。
- 仅替换工程smoke prompt为明确首尾花括号、禁止代码围栏；v2请求另存group_02_v2，未覆盖首次输入。11测试重跑通过，已提交1502725.stdct-mgmt-02到同CFP/autox/A40作8图非评分连通性重试。推理模型缺少优化kernel采用reference实现，当前不安装或改环境。


## 2026-10-28T15:27:26+08:00 [QWEN-TOPDOWN-ENGINEERING-LOCAL-COMMITTED]

- 最终本地分支phase2/qwen-topdown-judge @ 53a98b83b1a7443b9fb2e0a9954d3fff529e10c6，工作树干净，未推送；累计仅新增4文件，无原训练代码差异。11测试最终通过，原训练src/exp_config/run_sim.py diff为空。implementation_result.json记录完成边界。
- 1502697确认八图工程链路已执行，首次严格输出无效的事实保留；1502725当前仍Q/node_pool不足，待运行确认更明确格式要求是否产生合法JSON，不把排队当完成。没有Qwen评分、奖励写入、PPO训练或分组采样改动。
- 采样判断：同任务8条对裁判比较合理，但在线将减少每批任务多样性；独立done自动reset会破坏后续窗口的同条件，强制256步重置则截断长episode；等全组完成会改变等待、batch大小和更新周期。后续应先固定policy离线验证；如在线分组，组间随机覆盖训练任务，组内核对起点/目标/策略及历史窗口，仅使用真实episode边界。组内归一化方差近0与unknown不应强行放大/补0。具体采样协议留待用户确定。


## 2026-10-28T16:20:12+08:00 [QWEN-TOPDOWN-ENGINEERING-PUSHED]

- 按用户要求，将Qwen工程分支普通push到yiichu03/SIGN。执行目录SIGN-qwen-topdown-judge，推送前确认工作树干净，有效origin push URL为git@github.com:yiichu03/SIGN.git；新增内容仅4个工程/测试文件，未添加权重、场景或运行数据。
- 已执行git push -u origin HEAD:refs/heads/phase2/qwen-topdown-judge，成功创建远端同名分支并设置跟踪；显式branch pushRemote=origin。git ls-remote确认远端SHA与本地53a98b83b1a7443b9fb2e0a9954d3fff529e10c6一致。
- 回执logs/qwen_topdown_engineering_20261028/push_result.json；本次仅发布既有代码，未改变训练目录或作业。


## 2026-10-28T19:04:39+08:00 [GIBSON-THREEWAY-TRAINING-METRICS-CHECK]

- 按用户要求只看训练。qstat确认三个Gibson作业1496716/1497416/1502352均R；未调用评估、提交/停止作业或修改训练代码/参数。基线指冻结visual_encoder的dac8609复现，原覆盖为6983c91，32步结算为a7cc9e0，均8×256/weight0.1（基线无bonus）。
- 已执行envs/sign-baseline/bin/python logs/gibson_train_threeway_20261028/analyze.py。顺序复制三组TensorBoard事件到snapshot_190105/events，每份按读取开始时字节数固定并记录SHA；原日志只读。末事件分别19:01:04/19:01:49/19:02:26，步数71964672/45021184/4536320，29/34/34条scalar均有限，未见NaN/Inf；bonus与0.1*新增面积/256最大误差<1.8e-8。
- 三组共同3536320–4536320步（最近1M）：SR80.591%/82.438%/79.539%，SPL43.735%/44.232%/44.056%，环境导航reward6.6822/6.8515/6.6462；32版相对基线SR-1.052pp、SPL+0.321pp。最近500k时SR81.14%/84.08%/82.44%，32版有回升，窗口敏感，不认定稳定优势。两覆盖同1M新增面积/步0.145014/0.144357m²，当前未见32版明显提高覆盖代理效率；基线无coverage测量，无法比较其面积。
- 基线与原覆盖共同40021184–45021184步最近5M：SR85.762%/84.283%（-1.479pp），SPL50.302%/46.686%（-3.616pp），导航reward7.3494/7.2043；最近1M差SR-2.826pp、SPL-4.804pp。30–35M/35–40M/40–45M三完整区间SR和SPL均落后。按相同步数两者均尚未跨50M augmentation阈值；不能拿基线最新72M直接与coverage45M作公平优劣对比。
- 解释边界：全部均为原生50-update完成episode滑动指标再按环境步区间取均值，样本相关，不是独立episode汇总或验证指标；只1个seed。reward始终为环境导航奖励，覆盖bonus独立记录；不能声称训练稳定性校验证明探索效率或泛化收益。
- CSV含全部原始scalar，comparison.json/summary.json含窗口/计数/有限性与事件清单；training_comparison.png/pdf已视觉检查，左列三组早期、右列基线/原coverage长期。图使用额外101-update平滑展示，表中数值按未额外平滑数据计算；qstat.txt留实际状态。

### 2026-10-28T19:07:31+08:00 — TENSORBOARD-STALE-SERVER-20261028

用户反馈再次无法查看TensorBoard。已执行本地ss／ps／curl：16006无监听，curl连接拒绝，没有活动的该端口SSH转发；VSCode动态SOCKS转发与16006不是同一入口。SSH到stdct-login-01后读取当前AGENTS／STATUS和RUNBOOK相关段落；6006由PID3487356占用，启动时间2026-10-26 21:01:54，完整命令及/data/logdir均指旧gibson_reproduction_20261026/scratch_personal_8env/tb；当前view_personal_tensorboard.sh已指gibson_frozen_encoder_20261026/train_personal_8env/tb。因此新脚本在旧服务存在时会有端口冲突，且当前本地入口本身未建立；未取得用户此前原始报错，不推断断线原因。

核对主机与/proc命令后仅SIGTERM旧网页PID3487356；6006释放。以Python Popen临时执行原脚本，首页HTTP200，/data/logdir严格匹配冻结编码器正式目录，scalars/tags共29项；finally终止本轮验证进程，ss再次确认6006无监听。验证临时stdout在登录节点/tmp/tensorboard_check_20261028.log；未改启动脚本、环境、训练源码或PBS作业。依照用户上一轮希望自己运行的偏好，没有留下网页服务或16006转发。RUNBOOK交互命令改用ssh -t以把终端Ctrl+C传到远端，追加旧logdir／孤立服务诊断；STATUS更新。

### 2026-10-28T19:19:31+08:00 — TENSORBOARD-LOCAL-URL-PORT-CORRECTED

用户自行启动后仍报告浏览器refused to connect。只读核查本地PID1638312、127.0.0.1:16006监听正常，curl经用户SSH隧道完整获取首页HTTP200；/data/logdir为冻结编码器正式目录，scalars/tags共29项。远端stdct-login-01 PID1069193在pts/34监听6006，启动19:17:27，命令匹配当前脚本。请求用户提供完整URL及所在电脑，用户明确回复当前电脑的http://127.0.0.1:6006/，据此确认本地浏览器端口错误，告知改用http://127.0.0.1:16006/，无需重启。未终止或修改用户SSH、TensorBoard及训练作业。CUA浏览器列表为空，未直接验证用户浏览器渲染。


## 2026-10-28T19:19:51+08:00 [GIBSON-THREEWAY-COVERAGE-EVAL-SUBMITTED]

- 用户要求提交PBS，对基线及两覆盖版本在相同训练节点比较SR/SPL/观测面积每步。查本地数据只有train与val，选完整Gibson val4200条/14场景；这是训练外保留验证集，不宣称新增独立test。已取最新共同编号ckpt.8，torch CPU读取extra_state.step三份均4608000，状态有限；复制为logs/gibson_threeway_coverage_eval_20261028/{baseline,coverage256,coverage32}.pth，SHA与来源记录manifest.json。
- 新建独立detached worktree SIGN-coverage-eval @a7cc9e0，仅软链接复用data；未修改三个训练的源码、HEAD、参数或作业。共用原生trainer.eval、策略动作/安全模型/奖励/真实done和mask；不按checkpoint训练config评估，统一外部配置。6环境/500步/seed100/hash0、全部原测量项保留，三组新增同一个原ObservedCoverage（0.1m/3m/90°）、weight0。不使用导图2.5cm与边界投影修正，保持训练统计口径。
- 外部recording_env.py只继承NavRLEnvX记录实际step与done信息，不改父step返回的obs/reward/done；新增info标量为面积/步，逐episode JSONL保存任务键、目标图SHA、起点、轨迹SHA、SR/SPL/reward/面积/实际动作数。原生TB和独立episode汇总相互核对；同时报mean(A_i/T_i)与sum(A_i)/sum(T_i)，A_i扣初始视野。跨模型核对相同4200任务和目标图/起点，无完整结果不写full_comparison.json。
- CPU preflight已执行并通过：三模型最终配置仅权重路径/输出元数据不同；源文件SHA/安全模型/任务SHA守卫通过；假环境末步、reward不变与episode reset计数检查通过；脚本AST通过。配置和检查日志preflight.json/log。
- 已执行qsub logs/gibson_threeway_coverage_eval_20261028/evaluate.pbs，返回1503479.stdct-mgmt-02，CFP04-SF-109/autox→batch_gpux，1A40/36CPU/240GB/4h。提交时Q/placement资源不足，scheduler_submitted.txt与submission.json留证。一个PBS内同GPU顺序跑4×28条（基线无覆盖control、三组有覆盖smoke），要求基线轨迹/指标完全一致后才跑3×4200正式评估；失败即停止留日志。
- 当前GPU检查和正式评估均未完成，不能声称已通过或公布SR/SPL/探索效率结论。外部run_all.py/runtime.json记录分阶段进度，完成后full_comparison.json保存结果；原三个训练及GS评估仍运行，未干预。


## 2026-10-28T19:22:59+08:00 [QWEN-BRANCH-DIFF-EXPLAINED-AND-IO-RETRY-VERIFIED]

- 用户询问Qwen分支相比SIGN原始代码及图片推理入口。只读核对phase2/qwen-topdown-judge@53a98b8，工作树干净、跟踪origin同名；相对作者dad87fe共66文件（主要为继承的实验资料/日志），相对settle32@a7cc9e0仅新增4文件284行，Qwen部分无trainer或网络计算修改。继承原encoder加载冻结、ObservedCoverage与interval结算及相关实验材料。
- Qwen核心src/qwen_topdown.py：prepare在30行封装并冻结8图+prompt+允许的元数据；run在122行，146/147加载processor与Qwen3.5-9B，153处理多图消息，164generate，167decode，168保存response.txt，176严格校验。CLI scripts/qwen_topdown.py，配置scripts/qwen_topdown_config.json默认关闭，tests/test_qwen_topdown.py验证边界。prompt、既有数据和PBS试跑证据在根logs，未随4个工程文件发布。
- 顺带核对先前排队的1502725已有成功结果：gpu_smoke_02/audit.json为valid，2713输入token/120输出token/8.2772秒生成/18.4105GiB、无截断，原response为合法JSON，C01–C08全部存在并给出图例。该检查只证实八图连通性与输出结构，不是裁判准确性或评分规则验证。首次围栏错误原始输出保留。

## 2026-10-28T19:31:27+08:00 — HABITAT-GS-FULL-EVAL-FINISHED-WITH-NONFINITE：1900条完成，辅助指标异常触发末尾检查

- 用户要求查看当前评估。已执行qstat -xf 1502487.stdct-mgmt-02，确认F、Exit_status=1、walltime04:55:21，19:23:16结束；原生evaluation.log明确1900/1900，19:23:00写出9项汇总。此次不是仍在运行；此前GitHub进度是14:47左右的冻结快照，没有自动更新发布包。
- 已只读读取TensorBoard精度值：success0.16684210300445557（317/1900），SPL0.0848187729716301，softSPL0.14181077480316162，view_match0.16394737362861633，平均碰撞129.02578735351562；reward NaN、distance_to_goal与distance_to_view均+Inf。主SR／SPL有限，但不能跳过附加异常并标记完全验证通过。
- native evaluator未抛Python运行异常或OOM／CUDA错误，父evaluate.py在子进程正常结束后第145行assert all(math.isfinite(v)...)失败，因此没有result.json。保留原quality gate、代码95eef9b和所有原始日志／事件；没有把NaN改零或过滤异常任务，也没有重提GPU任务。
- 初步只读源码检查：custom_habitat_simulator.geodesic_distance返回pathfinder的测地距离，DistanceToView叠加该值；environment.py使用previous_measure-current_measure，非有限距离可传播至奖励。这只是传播机制，不证明具体根因。此前1900条起点到目标CPU检查均可达；本轮未保存逐条轨迹／指标，因此无法确定异常发生在哪些场景／时刻或影响条数。不能将缺语义描述消息直接归因为根因。
- 审计JSON logs/habitat_gs_eval_20261028/result_audit.json保存全部原精度标量、1900完成证据、原始日志SHA和质量状态，非有限值用明确字符串编码，未伪造成功result.json。submission.json补完成状态；STATUS／RUNBOOK更新。源工作树干净、HEAD不变，本轮未push或启动新实验。后续需有针对性的逐任务诊断后再判断是否需要重评。


## 2026-10-28T19:35:14+08:00 [QWEN-INDEPENDENT-SINGLE-IMAGE-LATENCY-SUBMITTED]

- 用户明确更正：每张图独立打分，不做8图组内相对评分；每次8环境的图独立、尽量并行处理。此前八图同会话/同任务相对评分方案不再是当前方向，旧资料保留。单图分数使训练无需同任务重采样，保持8个独立任务采样即可。
- 新增src/qwen_single_image.py，SingleImageJudge常驻模型，每张图一个独立会话，batch维并行，严格{score:0–1或null}；旧接口留作历史，不把它作为当前训练方案。新增scripts/benchmark_qwen_single.py和5项测试，连同旧11项共16项通过；本地提交4754fed，尚未push。未改SIGN trainer/measure/采样/损失。
- 下载官方Qwen3.5-4B/2B/0.8B到models，固定HF revision与逐文件SHA/LFS校验，清单download_*.json，读取官方模型卡确认多模态支持。已用独立qwen35环境，不升级训练依赖。
- 已执行qsub logs/qwen_single_latency_20261028/benchmark.pbs，返回1503515.stdct-mgmt-02，CFP04-SF-109/autox→gpux/A40/2h；同节点依次9B/4B/2B/0.8B，8张同样静态Gibson图、相同任意测速prompt、每图262144像素上限、输出64token上限、关闭thinking/贪心；分别测first-call、常驻单张3次、独立batch8三次、串行8张、batch4两批。保存原始输入token/grid、原回答/解析错误、GPU显存与分阶段耗时；模型加载单列，不把排队算推理耗时。当前未有实际测速结果。
- 训练日志最近500次update实测均值：基线3.9944s/轮，原coverage6.5795s，settle32为8.8542s；每轮8×256，控制台每10轮打印，不是200s一轮。原始依据training_timing.json与脚本；后续按T_new=T_train+T_Qwen_batch8估算同步等待，实际在线绘图/IPC/共享GPU争用另计。


## 2026-10-28T19:42:13+08:00 [QWEN-SINGLE-IMAGE-FOUR-MODEL-LATENCY-COMPLETE]

- 1503515.stdct-mgmt-02成功完成，Exit0，A40 GN-A40-041、GPU-14857613-1d7f-578d-43dc-765443c206a4，PBS总walltime3分21秒。9B/4B/2B/0.8B四子进程均0，独立请求单张/8张串行/batch4两批/batch8三次全部完成；同图/同prompt/同262144像素上限/同输出64token/greedy/thinkingFalse。每条会话仅一张图，无跨batch行相对比较；无需同任务、同场景采样。
- 常驻单张中位耗时：9B0.52865s、4B0.53292s、2B0.40167s、0.8B0.45756s；8条独立请求批次全部完成中位：1.68173/1.59277/0.86862/0.89568s。串行8张4.49146/4.34080/3.36825/3.69003s，两批4张2.08151/2.05461/1.20753/1.26255s。数字是完整PNG读取/处理/H2D/生成/解码/严格解析；单张与batch8不含外部落盘审计，串行和batch4总体wall含JSON落盘，另有inference_sum供核对。
- 模型初始化67.8107/27.0702/19.5336/13.0997s，第一次调用5.0207/1.7629/1.4279/1.5139s，9B加载+首答72.8314s，2B20.9615s。冷启动包含import/CUDA/权重加载，NFS及系统缓存状态不同；训练接入应常驻模型，不每轮加载。峰值显存18.9296/9.8197/4.7910/2.2312GiB（Qwen单独运行，未与PPO共享GPU实测）。
- 严格JSON合格输出9B52/52、4B35/52、2B52/52、0.8B0/52；52为重复测速调用输出数，不是52个独立质量样本。4B部分加围栏，0.8B多数加围栏且C08输出{null}；保留原文、不自动修复或重试，不把失败当分数0。各模型实际生成token长度不同（例如9B约11、2B16、0.8B多数21），这是同prompt到答案的速度，不是固定token数的纯吞吐比较。评分准确性未验证。
- 同步加法估计T_new=T_train+T_batch8：当前原覆盖6.5795s/轮，9B约8.2613s（+25.6%），2B7.4482s（+13.2%）；基线3.9944→5.6761/4.8630，settle32 8.8542→10.5359/9.7228。用户举例200s/轮则变201.6817/200.8686s。这些估算不含在线画图、IPC与共享GPU资源争用；没有实际接入PPO或改奖励/采样。
- 证据comparison.json/csv、各模型逐调用JSON与log、prompt.txt、plan.json、training_timing.json、download_*.json及runtime/scheduler/completion记录。summarize.py已执行。画图初次因旧matplotlib无Axes.bar_label报AttributeError，改为ax.text标注，未升级环境；重试plot.py输出PNG/PDF，日志plot.log。
- 速度与本次格式表现支持优先用2B继续验证裁判、9B作对照；0.8B当前无速度优势且严格格式失败，不据此声称模型无视觉能力。新单图代码本地4754fed，16项测试通过，远端仍53a98b8，本轮没有推送授权动作或训练发布。


## 2026-10-28T19:47:03+08:00 [QWEN-SINGLE-IMAGE-CODE-PUSHED]

- 用户明确200s只是举例，后续成本判断以实际训练每轮测量为准，不把示例当实测。用户要求将当前topdown调用Qwen代码推送GitHub。
- 执行前确认SIGN-qwen-topdown-judge干净、phase2/qwen-topdown-judge比origin前进1提交；有效push URL为git@github.com:yiichu03/SIGN.git，pushRemote=origin。新增3文件134行，含独立单图调用模块、批量测速CLI及5个新测试；之前共16测试通过，代码未变未重复测速。
- 已执行git push -u origin HEAD:refs/heads/phase2/qwen-topdown-judge，普通快进53a98b8→4754fed6b95a70b6da179d48fc324ecbf613a15e成功；git ls-remote核对远端SHA完全一致。回执logs/qwen_single_latency_20261028/push_result.json。未发布模型权重或相机数据，未改动训练作业。

## 2026-10-28T19:49:02+08:00 — HABITAT-GS-NONFINITE-MEANING：距离查询失败标记与奖励传播机制澄清

- 用户询问NaN／Inf含义及是否仿真问题。已继续只读核对固定版本Habitat-GS原生PathFinder.cpp的findPathSetup／findPathInternal／MultiGoal findPath：距离先置infinity，投影失败、导航岛不连通、搜索失败可保持Inf并返回false。SIGN custom_habitat_simulator.geodesic_distance忽略该布尔结果，直接返回geodesic_distance。
- DistanceToView将测地距离加方向项；environment.NavRLEnvX按previous_measure-current_measure计算进度奖励。Inf-Inf可产生NaN，跨步累计正／负Inf也可产生NaN。已确认的是这种代码传播机制，与本次聚合现象相符；未记录第一处异常状态，不能宣称具体是哪种情况触发。
- 单个Inf可使整个距离均值Inf，单个NaN可使整体奖励均值NaN，因此这不表示全部1900条都坏了。此前1900条起点路径均可达，仍需定位运行后位置／NavMesh／场景与接口状态；暂不能归因于Habitat-GS本体或GS渲染。评估没有训练更新，奖励不回传更新checkpoint；SR／SPL有限不等于已证明完全不受导航异常影响，也不能仅凭辅助非有限值宣布主指标必然作废。
- 未改源码／守卫，未启动新GPU诊断或重评。RUNBOOK补充源代码机制，后续若诊断应捕获第一处find_path=false的episode、scene、agent／goal坐标与navmesh投影／连通性，而不是把Inf强制改成0或随意截断。

## 2026-10-28T19:56:41+08:00 — HABITAT-GS-VIDEOS-PLAN：成功／失败各三条视频与本地传输

- 用户希望确认数值异常与评估关系，并要求渲染几条成功／失败导航视频放同一文件夹，给出本地从e1538633@vanda.nus.edu.sg传输到/home/liuyi/projects/ceg5002的命令。已明确：奖励NaN不参与本轮策略更新／动作，但Success直接依赖距离阈值、SPL依赖Success，因此距离异常不能宣称对评估无影响；评估方法本身未改。
- 原1900条未保存录像、轨迹或逐条标签，无法事后恢复原始录像。本轮按相同公开权重、seed100/hash0、确定性动作、500步／128输入在少量val任务重新录制；计划3成功＋3失败，尽量不同场景，以实际Success指标分类，记录SPL／终止原因／非有限信息。它们是新录制样例，不冒称原1900条的精确逐帧回放或独立基准。
- 不改SIGN src／原评估器。外部采集脚本与PBS放logs/habitat_gs_videos_20261028；视频流式编码，只保留选中样例的6个MP4和一个manifest在SIGN-habitat-gs/results/habitat_gs_videos_20261028。视频显示实际128图放大后的当前视图与目标图，10fps回放，不改变策略输入；不保存逐帧PNG／重复资产。
- GPU经autox／A40提交；完成后校验视频可解码／帧数／标签与指标，最后提供用户在本地运行的rsync命令。现有训练和三方评估任务保持，不提前把提交视为视频完成。

## 2026-10-28T19:58:52+08:00 — HABITAT-GS-VIDEOS-SUBMITTED：A40录制成功／失败示例

- 外部record.py按val场景轮转、每场前4个episode候选确定性运行，优先每类选3个不同场景；两轮后允许同场景不同任务补足。分类以原Success值而非奖励／人工判断，保留原SPL／view_match。采用GymHabitatEnvX和原PPOTrainer建模／原公开权重加载，策略输入128不变，视频仅放大显示。500步全程，10fps，末帧停2秒；未选中任务不落盘帧／视频。
- Python语法编译、bash -n、字体文件可用及imageio自带ffmpeg检查通过。已执行qsub record.pbs，返回1503625.stdct-mgmt-02；qstat确认R。提交参数和两脚本SHA记录logs/habitat_gs_videos_20261028/submission.json，PBS原输出record.pbs.log。
- 仅新增独立支持脚本与输出目录，不修改原SIGN src／权重／1900条结果或其它GPU任务。若新录制遇非有限距离，只记录第一处位置、岛号、fresh path查询等诊断，不修改状态或替换距离。当前只证明提交成功，等实际6视频及解码验证后交付传输命令。

## 2026-10-28T20:07:36+08:00 — HABITAT-GS-VIDEOS-COMPLETE：六条完整导航视频已生成并验证

- 1503625在GN-A40-039运行6分47秒、Exit_status=0。确定性重跑16条val候选，选中3成功：scene59/ep0（475步、SPL0.08689896）、scene64/ep0（13步、SPL0.95323688）、interior_0651_841463/ep0（50步、SPL0.61433059）；3失败：scene56/ep0（500步）、scene57/ep0（147步）、scene58/ep0（500步），Success／SPL均0。原Success指标分类，非按奖励或人工视频印象。
- 同一文件夹SIGN-habitat-gs/results/habitat_gs_videos_20261028，只有6个H.264 MP4和manifest.json，总12301263字节。每视频左右当前视图／目标图，显示最终Success、SPL、ViewMatch以及逐步距离／碰撞；128输入仅放大显示，10fps、终帧20帧停留，无逐帧PNG／重复数据集。原1900任务未保存视频，本轮是新录制示例，不能冒称原任务逐帧重放。
- 已用imageio_ffmpeg逐帧解码全部1811帧，逐项核对768×544、10fps、帧数=动作步数+21、视频SHA与manifest、Success分类／失败SPL和无额外文件；validation.json记录实际结果。已实际查看/tmp/habitat_gs_video_review_20261028.png中的两个成功末帧和两个失败中途画面，标注／RGB内容正常。只在/tmp留视觉检查图，不放交付目录。
- 本轮16候选未观测非有限距离／奖励，不能据此解释或排除完整1900条的异常。说明澄清：reward NaN不参与本轮动作／训练更新，但原Success有距离阈值、SPL乘Success；若距离查询错误仍可影响评估，不能笼统断言完全无影响。未更改指标、距离或奖励处理。
- 已更新STATUS／RUNBOOK，submission.json补完成状态；提供用户在本地mkdir后rsync -avP从e1538633@vanda.nus.edu.sg的真实远端目录到/home/liuyi/projects/ceg5002/habitat_gs_videos_20261028/。没有从服务器擅自连接用户本地、没有再次推送GitHub；源工作树仍95eef9b且干净，原训练／其它评估不变。

### 2026-10-28T20:08:20+08:00 — SIGN-THREEWAY-TENSORBOARD-VIEWER

用户原SSH命令只见一条曲线，要求三组训练对比。只读确认三正式tb目录各有事件文件，1496716/1497416/1502352均R；旧6006网页进程1069193实际只传--logdir到冻结基线目录。已修改外部入口logs/gibson_reproduction_20261026/view_personal_tensorboard.sh，使用--logdir_spec挂三原位目录为baseline_frozen、coverage_rollout256、coverage_settle32；默认仍127.0.0.1:6006，SIGN_TENSORBOARD_PORT可供临时端口探针；检查目录存在、禁GPU，max_reload_threads=3并行读取。未移动/复制训练日志，未改训练源码、参数、分支或停止作业；现有6006用户网页进程亦未终止，需用户本地Ctrl+C后重跑原SSH命令才能使用新配置。

bash -n通过。首次临时探针50秒超时且预期run名未处理TensorBoard2.8追加的/.；修正探针名称映射并延长到180秒后，默认串行读取累计约100MB历史日志仍超时，只出现前两组。根据本地TensorBoard源码启用3个读取线程，再次探针成功：HTTP scalar tags及每组三组success数据均可读取，29/34/34类scalar，success和spl共有tag存在；显示名称均带/.。该验证在历史日志仍加载中完成，latest_returned_step仅HTTP当时加载进度，不能当作训练最新步数。证据viewer_validation.json和validate_viewer.py及probe日志在logs/tensorboard_threeway_20261028；临时进程已finally清理，原6006保留。

RUNBOOK更新入口为三组同页对照，STATUS增加使用说明。用户在Runs勾选三组、横轴Step，比较metrics/success/metrics/spl/reward；原reward仍导航奖励，coverage新增bonus仅learner/coverage_*且基线无该指标。新实验启动较晚，按共同Step区间比较；首次载入完整历史仍需等待刷新。


## 2026-10-28T20:08:39+08:00 [QWEN-ABC-TOKEN-PROBABILITIES-IMPLEMENTED-SUBMITTED]

- 用户要求基于最新yiichu03/SIGN phase2/qwen-topdown-judge，主要修改现有qwen_single_image.py，读取真实下一回答A/B/C logits，经T=1候选softmax算LOW/MEDIUM/HIGH概率和q=0.5*p_medium+p_high，给两组各8单图评分；保留生成式JSON/benchmark，禁止改PPO/trainer/采样/coverage。执行前核对本地与远端4754fed一致、工作树干净。
- 已在同一SingleImageJudge新增class_probabilities和GPU verify_readout，复用模型加载/独立batch/预处理；单独prompt文件和轻量score_qwen_single.py，输出CSV/JSON/原始logits/真实输入tokens、mask、grid、rendered chat及候选外概率质量candidate_mass。每行metadata验证正整数动作数/有限面积，计算并核对面积每动作，拒绝用百分比推面积；所有图片单独会话。CLI一次加载模型、按batch8处理，保存图片副本/SHA、prompt文本与内容SHA版本、manifest/代码/模型配置哈希。
- 本地提交1d959c81df5f84bc662fbed148730ca6e420d876，仅4文件（核心、CLI、prompt、原测试扩展），无训练代码变更。25单元测试全部通过（含原生成/benchmark依赖接口），git diff --check通过。
- 两组Gibson图与真实原始面积来源齐全。prepare_manifest.py读取16份display_map_data.npz，以new_valid_cells*meters_per_pixel²重新计算面积，对轨迹len(poses)-1核对action_count，再与旧CSV逐项一致性检查；不从coverage_percent推算。这里是0.025m显示重建的二维可通行视域代理，3m/90°、边界fog原点投影最多5cm，扣初始视域；与原生训练0.1m指标不同，明确写manifest与数据来源SHA。
- CPU tokenizer/proc实测：A32、B33、C34，各为单token且在真实assistant前缀后编码不合并；3个探针左pad数2/1/0，真实最后输入token位置均642，不用sum(mask)-1误取左pad位置。tokenizer_probe.json保存结果；GPU还需核对前向/首个generation raw logits与batch/solo概率。
- 已执行qsub logs/qwen_token_probabilities_20261028/score.pbs返回1503665.stdct-mgmt-02，CFP/autox→gpux/A40/30min，目前R于GN-A40-009。先验证三个真实探针再全16图，模型只加载一次；generate仅用于1token位置核对，不用于产生数值概率。实际GPU验证与结果待完成，未声称评分准确性验证。


## 2026-10-28T20:13:32+08:00 [QWEN-ABC-BF16-BATCH-CHECK-FAILED-FP32-RETRY]

- 首次GPU1503665在verify_readout阻止16图评分：RuntimeError: Batch/answer-position check exceeds tolerance: 0.029362147609890865, 0.0。batch与逐张三类概率最大相差0.02936，高于原0.01；直接forward与生成首步raw logits概率差0，输入非pad tokens与image_grid逐张匹配已通过。尚不能单凭这些结果把全部差异断言为精度原因；没有放宽阈值或生成虚假评分。
- 保留run_1503665/run.json失败状态、输入快照，完整原错误日志已复制score_1503665.pbs.log（防新作业同-o路径覆盖）。首次无scores.csv/json，因为GPU质量检查未通过。
- 新提交4cc7257保留旧SingleImageJudge默认dtype=auto与生成/benchmark行为，新评分CLI增加简单dtype参数并默认float32，验证阈值收紧到1e-4。verify现在保存batch/single原logits与概率、排列不变性和生成首token检查，先写verification.json再阻止不通过结果；不再仅有异常字符串。
- 25单测再次全部通过。重新提交score.pbs为1503691.stdct-mgmt-02，输出run_1503691（新jobID防覆盖），仍只加载一次9B，待FP32验证与16图结果。没有PPO或训练变更。

### 2026-10-28T20:22:44+08:00 — SIGN-THREEWAY-SENIOR-REPORT-EVIDENCE

用户询问三组SIGN实验可向学长简洁汇报的有价值内容。本轮只读复核已有19:01–19:02三组训练快照及2026-10-27完整两组val结果，未新增训练/评估或刷新旧快照。三长作业1496716/1497416/1502352均R；已有三组4.608M覆盖评估1503479仍R、runtime为full_baseline，全套结果未出，不将其smoke或部分baseline当作正式三组结论。

可引用事实：共同3.53632–4.53632M区间原生训练滑动指标均值，baseline/coverage256/coverage32 SR80.5912/82.4376/79.5392%，SPL43.7348/44.2318/44.0560%；两coverage新增面积/步0.145014/0.144357m²，基本相近，基线未记录该训练指标。更长共同40.021184–45.021184M，baseline/coverage256 SR85.7620/84.2830%（-1.4791pp），SPL50.3024/46.6861%（-3.6164pp）；早期小幅领先未形成持续收益。单种子、相邻训练窗口相关，不作显著性或因果证明。

较强的已完成验证证据：9.216M同阶段两模型，各4200val，SR78.3571/77.4762%（-0.8810pp），SPL51.9764/50.1014%（-1.8750pp）；此项没有coverage32，不混入三组早期train表。可向学长汇报已完成可控奖励及结算位置对照、原面积奖励尚无稳定收益、32步版本仍待较长训练及全量验证；不能声称探索面积增加或冗余下降导致SR下降。任务相关性/反馈时机为待检验解释。证据沿用logs/gibson_train_threeway_20261028/snapshot_190105/summary.json和logs/gibson_coverage_comparison_20261027/full_val_comparison.json。


## 2026-10-28T20:29:40+08:00 [BASELINE-1496716-STOPPED-TO-FREE-QWEN-GPU]

- 用户明确授权暂时停止SIGN基线，为当前Qwen腾空间；此新指令覆盖旧文档对1496716不停训保护。本轮仅停止基线1496716，未停两覆盖训练或三组评估；未自动重启其他训练。先告知原checkpoint无完整optimizer/rollout状态，之后只能权重初始化重启，不能等价恢复训练。
- 已执行preserve_baseline.py，确认latest.pth拷贝前后SHA一致，torch CPU state_dict全部有限；不可变副本baseline_stop_1496716/last_saved_checkpoint.pth，实际extra_state.step=74240000，SHA c3bf5d3e13a789f28b95c92b93ae7e31c4327f4a328bf59632f504b7b1eed73f。原SIGN/results/gibson_frozen_encoder_20261026/train_personal_8env的全部checkpoint/TensorBoard/日志保留，无删除。
- 已执行qdel 1496716.stdct-mgmt-02；最终F/Exit143，2026-10-28 20:28:36结束，walltime44:48:17。最后终端记录update36450/74649600环境步（20:28:21）；不将最后终端步数与已保存权重74240000混淆。scheduler_final与preservation.json留证。
- Qwen1503691随后在同一释放的GN-A40-045/0 GPU运行。为短任务回填，等待阶段曾qalter该Qwen walltime30→10分钟，不改数学与输入；实际R，完整验证与16图结果仍待完成。旧1497416/1502352和评估1503479均R。


## 2026-10-28T20:33:48+08:00 [QWEN-ABC-16-IMAGE-PROBABILITIES-COMPLETE-PUSHED]

- FP32重试1503691成功，F/Exit0、walltime1分03秒，GN-A40-045，实际torch.float32，9B模型只加载一次（初始化35.9047s），先3张真实探针核对，再2批各8张独立评分。16/16有效；每批评分forward及审计约5.28/5.31s，不能沿用此前BF16生成式JSON测速的延迟/显存结论。
- GPU验证：A32/B33/C34各单token，左padding数2/1/0，回答logits位置642（最后一个真实输入token之后的下一个token）。直接forward与生成首步raw logits归一化概率差0；生成首token分别C/A/A，与字母编码一致。batch vs solo最大概率差1.73672e-5，小于1e-4；逆序排列差0。这些结果结合原BF16差0.02936，支持该差异来自低精度数值变化；未放宽质量门槛。
- 候选外质量审计：16图A/B/C在全词表概率总和0.9961907–0.9979175。p_low/p_medium/p_high是ABC三个候选内T1 softmax；q=0.5*p_medium+p_high，是单图独立分数，不是组内rank，不声称校准后的成功率或人工真值。未生成JSON数值替代概率，generate仅在3图读出核验中执行1token。
- 运行check_results.py：逐图验证概率和=1、q公式、面积/动作比值、ID唯一、prompt SHA全一致，生成results_table.md/checked_summary.json。16图完整scores.csv/json、batch审计输入/token/mask/grid/rendered chat、原logits、候选质量、prompt.txt、manifest、images副本均在run_1503691。prompt版本cdd6f2fc782f6b9f9fa9ce2baaf953da476c8c467e5e7d3a29a8228af6a596ac。
- 得分范围：group01约0.6065–0.7271，group02约0.1980–0.6563；只作本prompt下观测，不认定评分准确性或训练收益。面积由原保存0.025m显示mask的有效新增格数×mpp²计算，与CSV和轨迹动作数核对，不是百分比反推；与训练0.1m统计口径不同，manifest保留定义和<=5cm fog边界投影说明。
- 最终仅改/新增4文件：src/qwen_single_image.py、scripts/score_qwen_single.py、scripts/prompts/qwen_single_coverage_abc.txt、tests/test_qwen_single_image.py；25测试通过。保留原生成式score和benchmark，旧加载默认auto；新概率CLI默认FP32，可显式选择dtype，统一预处理继续复用，无新配置系统/框架模块。PPO/trainer/采样/coverage源码未改。
- 已普通push 4cc7257d640ddb2216fd6b20b1fc929f465287e4至yiichu03/SIGN phase2/qwen-topdown-judge，ls-remote确认一致；无权重/场景/相机原序列上传。completion.json和push_result.json留证。
- 用户今后修改外置prompt（保留A=LOW/B=MEDIUM/C=HIGH、单字母约定），再qsub logs/qwen_token_probabilities_20261028/score.pbs即可。每job新输出run_JOBID、自动prompt内容SHA，不覆盖旧评分。也可qsub -v QWEN_PROMPT=/新prompt.txt指定外部路径。


## 2026-10-28T20:45:53+08:00 [QWEN-2B-ABC-SCORING-RESUBMITTED]

- 用户先要求下载8图与9B/2B分数；初查2B只有旧JSON测速分，故曾提交1503815补跑同ABC协议。用户随即要求先9B且不要补跑，已qdel当时仍Q的1503815成功，未有2B推理输出；现按用户最新明确指令重新提交。此段为实际发生后的补录，保留原先取消决定。
- 9B Denmark8图打包已完成，实际生成qwen9b_denmark_review.zip（350701 bytes），源为run_1503691真实概率输出；用户要求尽快直接下载后已提供scp/unzip，不再额外处理。输入图和对照CSV/json保存在review_9b_denmark与压缩包，旧结果未改。
- 本次执行前检查qstat无同类2B活跃任务，代码分支4cc7257与origin一致且干净；固定9B保存的prompt.txt内容SHA、原manifest SHA和score代码SHA逐项一致，2B模型已在本地。无需更改代码或重复已有25项单测。
- 已执行qsub logs/qwen_token_probabilities_20261028/score_2b_review.pbs，返回1503819.stdct-mgmt-02，CFP04-SF-109/autox→gpux/A40/10min；当前Q。复用同两组16图/metadata、同prompt/T1/FP32/batch8/verify，唯模型改为2B；保留25测试已通过的原调用框架。输出独立run_2b_1503819，尚未声称概率检查或评分完成。submission_2b_1503819.json及scheduler_2b_1503819.txt留证。

## 2026-10-28T20:54:16+08:00 — GIBSON-SINGLE-MULTI-FLOOR-AUDIT：当前验证场景包含单层及多层

- 用户询问Gibson场景单层／多层。已浏览官方GibsonEnv数据说明并只读获取https://raw.githubusercontent.com/StanfordVL/GibsonEnv/master/gibson/data/data.json，楼层字段实际为stats.floor。官方说明全数据库包含多层建筑，floor计数由相机高度聚类，含部分地下室／阁楼等高度层，不是严格建筑设计楼层标注。
- 本地任务实际为SIGN/data/datasets/imagenav/gibson/v1/val/val.json.gz统一文件（不是每场content子目录）。对照14场景得到9单层：Cantwell、Denmark、Eastville、Elmira、Eudora、Greigsville、Pablo、Ribera、Swormville；5多层：Edgemere2、Mosquito3、Sands3、Scioto5、Sisters2。只核对当前val，未据此声称72个train的完整分布。
- 另读全部4200条任务坐标，76条起终点Y差>1.5m；这只是坐标高度差事实，不等于已确认每条的建筑楼层标签。本地起点高度也呈Mosquito约0.1/-2.7m、Sands约-1.0/1.6m、Scioto约0.1/3.1m等多模态。Edgemere虽官方标2层，当前任务起点集中同一高度，说明场景楼层与单条episode是否跨层不能混为一谈。
- 已将方法与当前val分布补入RUNBOOK，未下载场景／创建额外数据副本，未改源码或启动实验。

## 2026-10-28T21:01:40+08:00 — GIBSON-TRAIN-VAL-FLOOR-TASK-PLAN：统计训练／验证起终点跨层候选

- 用户询问当前训练与验证任务的起点、目标有多少涉及多层。按当前上下文统计Gibson train645000／val4200，不混入Habitat-GS。先区分官方metadata标记的多层建筑内任务，与起终点跨高度层候选；任务JSON本身无level／楼层标签，不能把二者直接等同。
- 只读扫描现有全部原始episode，按scene对照官方stats.floor并统计|startY-goalY|多个阈值（0.5／1.0／1.5／2.0／2.5m），保留各场景计数、元数据缺失与非有限检查、原文件SHA。主表采用与前次一致>1.5m作跨层候选，辅以阈值敏感性；不宣称人工楼层真值或用端点统计断言整条路径不跨层。
- 支持脚本与机器可读结果集中logs/gibson_floor_audit_20261028，不另建总结文档，不修改任务／场景、训练源码或运行中作业。


## 2026-10-28T21:03:11+08:00 [QWEN-2B-ABC-SCORING-COMPLETE]

- 按用户状态查询，只读核对1503819.stdct-mgmt-02：F/Exit0，2026-10-28 20:49:41结束，用时57秒，GN-A40-022。run_2b_1503819为complete/16有效/16总数，FP32。
- 真实概率核验通过，A/B/C32/33/34，padding2/1/0；batch与solo最大概率差1.41729e-5<1e-4，排列差0，forward/生成首步raw logits差0。逐行重算概率和与q公式一致。
- 与9B保存结果按group/id核对，16张图片SHA、action_count、new_area_m2、new_area_m2_per_action全部一致，prompt内容SHA一致（cdd6f2fc782f…）；同协议模型对比输入就绪，不是旧JSON测速分。结果原scores.csv/json及batch审计未改；本次未额外打包或启动实验。

## 2026-10-28T21:04:18+08:00 — GIBSON-TRAIN-VAL-FLOOR-TASK-COUNTS：全部645000训练及4200验证端点统计完成

- 已实际执行logs/gibson_floor_audit_20261028/count_tasks.py，逐文件只读解析73个train gzip（含空入口）与1个val gzip，源文件大小／SHA保存在result.json；官方metadata URL／SHA／时间、逐场景楼层数／端点Y范围／各阈值计数均一并记录。没有下载场景或复制任务包。
- train645000条／72场景（39单层＋33多层）：348000条位于单层场景，297000条位于多层场景（46.0465116%）。|起点Y-目标Y|>1.5m为16584条（2.5711628%），全在多层场景，分布30场景。
- val4200条／14场景（9单层＋5多层）：2700条位于单层场景，1500条位于多层场景（35.7142857%）。>1.5m为76条（1.8095238%）：Mosquito8、Sands37、Scioto17、Sisters14，Edgemere0。全部训练／验证场景metadata齐全、端点Y有限、每条goal唯一；原任务无level／floor／start_floor／goal_floor字段。
- 阈值敏感性：>0.5m train32234／val150；>1.0m 25138／119；>1.5m 16584／76；>2.0m 11673／49；>2.5m 8127／41。不能把某个阈值等同人工建筑楼层真值；同层端点也不能排除途中上下楼。这里只统计完整库存，不是当前训练实际已采样轨迹的比例。
- 结果result.json、原输出audit.log与脚本放同一专属目录；根STATUS摘要／RUNBOOK方法已更新。未改任务／源代码／训练参数，未提交或停止GPU作业，未push。


## 2026-10-28T21:05:05+08:00 [QWEN-2B-DENMARK-REVIEW-PACKAGED]

- 按用户要求复用9B现成打包脚本，仅替换模型/来源job/输出名称，生成qwen2b_denmark_review.zip（350683 bytes，SHA256 964b14e4e0c484c2ad22f618950e8853a3b1f0a35d67d6aa88b57bef81144634）。包含同一组Denmark C01–C08的8 PNG、真实2B ABC概率/q的CSV/JSON、原prompt与logits输入审计、同格式index.html。逐图ID/图片SHA与9B包一致，zip完整性检查通过。没有重新推理或更改分数。


## 2026-10-28T21:27:33+08:00 [QWEN-2B-GIBSON-DIVERSE-SCENES-SUBMITTED]

- 用户要求在Gibson不同场景/不同任务上看Qwen2B打分，明确要求等PBS结束后直接打包并给下载命令。本次预先固定8个新场景（Cantwell/Eastville/Elmira/Eudora/Greigsville/Pablo/Ribera/Swormville）×2个不同任务，共16条；排除此前Edgemere/Denmark，只选官方库存单层场景以避免多层地图歧义，不声称覆盖多层情况。
- 选择在采集/评分前固定：每场景首个5–8m任务＋首个8–15m任务，若后一范围无候选则取5–15m中另一最长候选，端点|ΔY|<0.05m；不按成功、路径观感或Qwen分数筛选。首次prepare.py在Elmira无8–15m候选时AssertionError，已按可用性加入上述fallback规则，先前已写task.json.gz逐项核对相同payload后复用，没有删除失败现场。
- 复用旧Gibson pilot原生SIGN权重采集/渲染脚本，在独立logs/qwen_gibson_diverse_20261028保存全部输入、plan、case/task、XYZ/旋转/动作等；policy从只读SIGN-coverage-eval@a7cc9e0加载公开完整nav/safety checkpoint，原生随机采样，max256动作，真实提前结束则保留实际长度。两个原训练源码不动。
- 显示按之前0.025m fixed-floor视域重建（3m/90°，边界fog原点最近有效像素投影≤5cm），高度范围须<0.5m、全路径映射距离≤2像素；任何不通过均停止不产出伪数据。area从mask新增有效cells×mpp²计算，动作从轨迹核对，与CSV一致后构造两组8项manifest。render按各场景自己的底图范围，不再错误共用单场景bbox/同任务标签。
- 无评分框架开发；继续调用4cc7257的score_qwen_single.py，固定2B/FP32/原9B保存prompt cdd6f2fc782f/T1/独立batch8/verify；最终package.py检查16/16 valid、q公式、图片SHA和8场景/16任务后生成含16 PNG、CSV/JSON、prompt/概率审计与index.html的zip。
- 资产路径/所有脚本AST/四工作树保护SHA及HEAD检查通过。已执行qsub logs/qwen_gibson_diverse_20261028/run.pbs，返回1503973.stdct-mgmt-02，CFP04-SF-109/autox→gpux/A40/30min，目前R于GN-A40-020，尚待采集/评分完成。源工作树均保持，已有三组评估和两覆盖训练未干预。


## 2026-10-28T21:33:08+08:00 [QWEN-2B-GIBSON-DIVERSE-SCENES-COMPLETE-PACKAGED]

- 1503973.stdct-mgmt-02完成，F/Exit0、4分18秒，GN-A40-020。同PBS完成16个预定不同任务、8新Gibson场景采集→mask重建→静态图→metadata→2B FP32真实ABC logits评分→下载打包。全部任务与预先plan的scene/episode相符，实际44–256动作；没有按Qwen分数筛图或重抽样。
- 16/16有效，prompt版本cdd6f2fc782f6b9f9fa9ce2baaf953da476c8c467e5e7d3a29a8228af6a596ac，与之前相同。GPU候选token32/33/34，batch/solo最大概率差2.22639e-5<1e-4，排列差0、forward/生成首step raw logits差0。q范围0.396172–0.825963，不是组内相对排序，不把分布变化当作准确性或训练收益证明。
- 每图新面积由0.025m显示mask的有效新增cells×mpp²重算、扣初始，与CSV对照，动作数和轨迹长度核对。所有路径距底图有效格≤2像素、fog原点投影≤5cm通过；高度范围Eastville/4101约0.1535m、Pablo/800约0.0779m，其余0，未越0.5m初始高度切片范围检查。已查看Cantwell绕行及Elmira直接路径两张PNG，GT底图/轨迹/覆盖/比例尺/图例可读。
- 包qwen2b_gibson_diverse_review.zip已完成：16PNG、含scene/episode/action_count/new_area/efficiency/LOW-MEDIUM-HIGH/q/valid/prompt版本的CSV与JSON、prompt、概率/输入审计、map_audit/selection来源和index.html，761472 bytes，SHA256 eb3a039b6a94945f1e2e4a4518a893ce2bcf6b5b8b2268be50d2dd94015a506d。zip CRC/图片数/源图片SHA/16不同任务和q公式全部检查通过；完整结果与complete.json在logs/qwen_gibson_diverse_20261028。
- 作业末尾原工作树保护HEAD/SHA检查通过，没有修改训练源或Qwen评分代码，没有重新启动已停止基线。用户明确要求等完成后提供下载命令，本轮已等到成功产包再回应。


## 2026-10-28T23:01:51+08:00 [QWEN-RESULTS-PUBLICATION-PREPARED]

- 用户反馈原文：“我感觉评分还挺不错的”，并授权将当前代码、文档、这几次评分图片和结果发布到yiichu03，之后由用户思考下一步。此为整体主观反馈，未提供逐图人工真值，不转写为已验证准确率；当前任务只做资料发布，不启动PPO接入、训练或新评分。
- 核对SIGN-qwen-topdown-judge与origin/phase2/qwen-topdown-judge均4cc7257、工作树干净，有效origin push URL git@github.com:yiichu03/SIGN.git。代码已在GitHub；本轮新增docs/experiments/qwen-topdown证据包与README导航，保留原研究材料和历史。
- 已确认9B16图、2B同图16图、2B跨场景16图均complete/16valid/FP32，32张不同的top-down PNG可复用；计划合并重复图片，另保留4张overview及测速图、原始输入/输出/token-logit审计、prompt、metadata/来源、单测/GPU验证、失败现场和四根文档生成快照。测速的生成式JSON分、旧多图连通性与现有ABC概率评分分开说明，HM3D未评分开发素材不混入本Gibson评分结果。
- 不发布模型权重、场景、环境、第一人称RGB序列、checkpoint备份或凭据。根四文档继续为维护源，包内副本由构建脚本生成；已有发布WORKLOG必须保留原前缀。完成后再记录推送回执，不为了包含回执重复生成文档快照。


## 2026-10-28T23:09:38+08:00 [QWEN-RESULTS-PUBLICATION-VALIDATED]

- 工作目录SIGN-qwen-topdown-judge，分支phase2/qwen-topdown-judge；有效origin push URL与远端HEAD再次核对为yiichu03/SIGN／4cc7257，与本地一致。现有src/scripts/tests/训练配置保持该代码提交，新增内容仅README导航与docs/experiments/qwen-topdown证据资料。
- 已执行logs/qwen_publication_20261028/build_publication.py。第一次构建FileNotFoundError指向pilot group_01/C01/task.json.gz：旧pilot任务在group级共享，新增跨场景任务在case级；改为优先case再回退group，保留真实task原文。另修正压缩trajectory文件后缀为.json.gz。第二次校验AssertionError来自glob把2张overview算入16张案例图，改为C*.png，未改原图片或分数。失败原日志build.log／build_retry.log保留。
- build_final.log实际通过376文件／6342271 bytes；32张不同topdown、4张overview、48条概率结果逐项核对有效性、q公式、概率和、metadata与双模型同图SHA；两份16项相对manifest可用，全部文件SHA/大小、解压SHA、相对链接与凭据模式检查通过，原始证据不修改。published WORKLOG自动复制并要求追加前缀，不维护手工副本。
- 两份图文表可从GitHub直接查看原图、动作、面积/动作、LOW/MEDIUM/HIGH与q。所有历史生成式JSON测速、旧八图同会话连通性和BF16失败明确单列，避免冒充新FP32概率或准确率。该步骤没有运行新单测/GPU推理；资料保存此前25项单测和3次PBS真实概率验证，运行时代码本轮无变化。
- 当前进入最终快照、staged检查与普通push；尚未把待执行push写为已完成。完整原始工作与构建/检查输出在logs/qwen_publication_20261028，模型/场景/环境/大体积RGB与checkpoint均排除。


## 2026-10-28T23:10:55+08:00 [QWEN-PUBLICATION-STAGED-CHECK]

- 已执行git add README.md docs/experiments/qwen-topdown，staged378文件，范围均为README与本次资料包；所有源文件SHA与发布manifest逐个匹配，运行时代码及配置无差异。构建/独立check-only均通过。
- 全量git diff --cached --check返回2：原始CSV的CRLF被识别为trailing whitespace，PBS原文末尾空行与2份旧采集/绘图脚本空白行也有提示；完整输出logs/qwen_publication_20261028/staged_whitespace_raw.log。原始证据与脚本按字节保留，不为格式美化改变SHA；本轮生成的pilot_comparison.csv已显式使用LF。后续格式检查对原始evidence及这2个原脚本作精确排除，新生成文档/脚本/manifest继续检查。没有把全量格式检查记为通过。


## 2026-10-28T23:12:29+08:00 [QWEN-RESULTS-PUBLISHED]

- 已执行git commit与普通git push origin HEAD:refs/heads/phase2/qwen-topdown-judge，提交b1c24dc16038b10df919a1965d35880f4f143ee1（Publish Qwen topdown images, probability scores and experiment records），目标git@github.com:yiichu03/SIGN.git。git ls-remote再次核对远端SHA一致，Qwen工作树干净；src/scripts/tests/exp_config/run_sim.py对4cc7257无差异。没有操作upstream或其他训练工作树，没有重启/停止/提交新实验。
- 已发布README导航与docs/experiments/qwen-topdown：32不同PNG＋4overview，9B16／2B同图16／2B跨场景16完整概率结果，两张GitHub图文对照表、CSV/JSON、prompt、相对manifest、原始token/mask/logits、轨迹/mask来源、测速/验证/失败记录和根四文档生成副本。最终check-only通过376文件／6346566 bytes；新生成内容的staged格式检查通过，原证据CRLF等提示按上条原样保留。
- 构建最后一次曾在shell仍运行时过早启动检查，出现scripts/build_publication.py中间状态SHA不一致以及并发git检查exit135；等待该session完成后顺序重查，check-only和staged格式检查均Exit0，再提交；这是发布脚本调度次序问题，未改原证据。
- 发布根文档快照截止2026-10-28T23:11:07+08:00，本推送回执按约定只追加服务器WORKLOG并更新STATUS，不循环生成资料提交。回执JSON：logs/qwen_publication_20261028/push_result.json。用户接下来思考后续方向，本轮授权工作完成。


## 2026-10-28T23:34:34+08:00 [GIBSON-THREEWAY-FULL-EVAL-COMPLETE-READOUT]

- 用户询问已跑完三个方法的评估结果。本轮只读核对PBS1503479及现有原始记录，没有新提交评估/训练、改模型或push。qstat -xf确认F/Exit_status0、GN-A40-023、2026-10-28 22:22:35结束，walltime02:59:09；runtime.json为complete，三个full阶段各约3482/3510/3414秒。保存新scheduler_completed.txt供审计。
- full_comparison.json三份均4608000训练步、同4200 Gibson val任务（非另建test），6环境、确定性、max500、seed100/hash0与同public safety。逐行解析三组12600条JSONL，任务键无重复且精确等于manifest；每任务起点/目标图SHA相同，步数/面积/奖励/SR/SPL均有限，每条area/actions公式成立。独立重算全部汇总与既有报告误差<1e-10，results_readout_audit.json记录原报告SHA、成功数、动作总量及变化；原报告不覆盖。既有smoke无覆盖/有覆盖control轨迹与指标完全一致检查通过。
- 基线／coverage256／coverage32：SR76.3571429%（3207/4200）／76.0%（3192/4200）／75.3571429%（3165/4200）；SPL45.8821543%／46.3331582%／46.3769403%。平均动作155.549286／154.777143／147.583333，平均新增11.236886／11.228064／11.449986m²；全局sum(area)/sum(actions)0.0722400342／0.0725434265／0.0775831895m²/动作，mean(area_i/actions_i)0.180434756／0.181155871／0.185764675。面积扣初始、0.1m网格/3m/90°，保留训练原边界，非Qwen静态图2.5cm显示重建。
- 对基线：256版SR-0.3571pp／SPL+0.4510pp／全局效率+0.4200%；32版SR-1.0000pp／SPL+0.4948pp／全局效率+7.3964%／episode平均效率+2.9539%／平均新增面积+1.8964%／平均步数-5.1212%。据此认为32版存在更高观测面积/动作的方向性现象，但没有成功率改善；单种子单一早期检查点不证明稳定导航收益或确实减少无效重复。32是子片段结算间隔，PPO仍8×256收集/更新。
- 根STATUS已将此前待完成三组评估及汇报建议更新为完整结果，原WORKLOG历史不改。用户可从full_comparison.json与审计文件追溯；本轮未生成重复总结文档或发布快照。

## 2026-10-28T23:35:59+08:00 — TENSORBOARD-WALLTIME-HOVER-COMMON-STEP：网页最新点为28日，公共Step旧点可复现27日显示

- 用户运行既有SSH16006→6006命令，询问baseline及rollout256的新曲线为何标10.27，随后明确指曲线悬浮框Wall time。只读检查view_personal_tensorboard.sh和当前PID2504801：stdct-login-01 TensorBoard2.8.0，logdir_spec是三个当前正式训练tb目录、max_reload_threads3、reload_interval5；没有把数据固定到某日期。
- 已直接GET当前网页6006/data/logdir、/data/environment和三个run的metrics/success／metrics/spl／reward标量，共9个序列。各run三tag最新Step与日期一致：baseline74653696，SG2026-10-28T20:28:29；coverage25649979392，SG23:34:15；coverage32 8130560，SG23:29:29。事件文件mtime也在10月28日。HTTP请求返回1000个采样点，包含最新点，证明页面后端不是只加载到27日。
- 按coverage32末端8130560作公共横轴位置，取当前网页返回的最近点，baseline8103936为SG10月27日04:44:38、coverage2568103936为10月27日12:31:16、coverage32自身为10月28日23:29:29。这个公共Step比较能复现用户描述的日期组合；Wall time对应所选点，不是每run最新更新时间。用户实际悬浮Step仍待确认，因此这是有数据支持的解释，未冒称已看见其浏览器画面或认定前端无其它问题。
- 审计JSON logs/gibson_reproduction_20261026/tensorboard_walltime_audit_20261028.json保存服务器环境、9序列最新时间／步数与公共Step示例。已向用户异步询问具体Step；若其所指确为各自最大Step且仍显示27日，需要进一步对比浏览器数据与原始时间戳。
- 本轮没有修改viewer、重启TensorBoard、停止SSH或训练、移动／重命名日志；RUNBOOK补充判读方法。


## 2026-10-28T23:41:35+08:00 [GIBSON-THREEWAY-LATEST-8192K-EVAL-SUBMITTED]

- 用户授权评估最新共同训练步数。三组原路径盘点：baseline145份至ckpt.144、coverage256为97份至ckpt.96、coverage32为16份至ckpt.15；准备时共同最大ckpt.15。CPU实际torch读取三份extra_state.step均8192000、全部state_dict有限；在新批次logs/gibson_threeway_coverage_eval_latest_20261028复制独立baseline/coverage256/coverage32.pth，源文件与快照SHA再次核对一致，manifest记录来源与任务4200键。旧4.608M结果及权重不改。
- prepare.py、preflight.py、evaluate.py、recording_env.py、run_all.py、summarize.py从1503479批次逐字节复用，PBS仅修改job名称及新目录，无新评估框架/算法/训练改动。CPU prepare/preflight实际通过（preflight.json、prepare.log/preflight.log）；三个最终配置仅checkpoint/输出元数据不同，6环境/max500/seed100/hash0与原native策略/safety一致，coverage weight0仅测量，mpp0.1/3m/90°不采用Qwen显示重建。记录器终止步/reset/reward被动性检查通过，四工作树protected源码HEAD/SHA与权重/任务/safety SHA通过；bash -n通过。
- 已执行qsub /scratch/e1538633/liuyi/logs/gibson_threeway_coverage_eval_latest_20261028/evaluate.pbs，返回1504280.stdct-mgmt-02；submission.json保存完整命令/时间/回执。qstat确认R／CFP04-SF-109／autox→batch_gpux／GN-A40-038，1A40/36CPU/240GB/04:00:00。runtime当前control_baseline，尚待28条baseline无coverage/有coverage轨迹完全一致、三组smoke，之后顺序三组4200 full；最终要求任务集/目标图/起点相同、原生TB与逐条JSONL指标一致。不能把提交记为GPU验证或全量完成。
- 上次实际2:59:09据此估计本次开始后约3小时，非保证耗时。输出和每阶段日志独立保存，未改任何训练源码/分支/参数、没有新增训练或重启已停1496716；原1497416与1502352核对均R。Qwen/GS与原评估证据不受影响。STATUS、RUNBOOK及AGENTS的评估工作树稳定说明已更新，未因本轮提交自动push。


## 2026-10-29T02:00:04+08:00 [GIBSON-THREEWAY-8192K-PROGRESS-CHECK]

- 用户询问1504280是否结束；只读qstat -xf、runtime及各阶段日志/逐episode输出。qstat确认R／GN-A40-038、已用约2:17；runtime仍full_coverage32。control_baseline与三组smoke完成，smoke_comparison.json中coverage_passive_control_exact=true；full_baseline3194.53秒、full_coverage2563452.86秒完成，full_comparison.json尚不存在。
- 2026-10-29 01:59:30读取快照：baseline4200/4200、coverage2564200/4200、coverage32为2017/4200（约48%），记录键无重复、无不完整JSON行，第三组输出mtime继续推进至01:59:32。未计算或发布未完成第三组的SR/SPL；progress_readout.json保存当前计数。估计剩余约25–40分钟，非确定承诺，任务后半耗时可能变化。
- 未提交/停止/修改作业，没有改源码或原结果。STATUS更新当前进度，继续等待现有作业自然完成。


## 2026-10-29T02:04:01+08:00 [GIBSON-8192K-BASELINE-VS-COVERAGE256-READOUT]

- 用户要求先比较前两组（已完整baseline与coverage256）。本轮直接读取二者完整各4200条JSONL，核对任务键精确匹配manifest、无重复、同起点/goal SHA、数值有限及每条面积/步公式；逐组重算SR/SPL/步数/面积/两种效率/碰撞，并与native/eval_run0_/log.txt的末尾汇总显示一致。没有等待或混入未完成coverage32，没有改动原训练/评估/日志。
- 8.192M baseline／coverage256：SR0.785／0.792142857（3297／3327条成功），SPL0.489610984／0.469972819；平均动作147.099524／146.496190，平均新面积11.346095／11.385355m²；sum(new_area)/sum(actions)0.0771321004／0.0777177531，mean(new_area_i/actions_i)0.191016834／0.186614583，平均碰撞49.836667／57.390476。
- 覆盖256对基线：SR+0.714286pp，SPL-1.963816pp；平均动作-0.4102%、平均新面积+0.3460%、全局效率+0.7593%，但逐任务平均效率-2.3046%、碰撞+15.1571%。配对任务：双方成功2940、仅baseline成功357、仅coverage成功387、双方失败516，净多成功30条。不能把两个面积/步平均方式混成同一结论：全局是按动作数加权，逐任务平均每任务等权。
- 判断：此checkpoint下256版SR稍高，但SPL更低，覆盖效率没有跨口径一致改善；单种子单checkpoint，不声称稳定收益。新completed_two_method_comparison.json明确仅含已完整二者，原完整三组full_comparison.json仍由作业最终审计生成；STATUS更新两组结果摘要。没有新实验或push。


## 2026-10-29T02:32:11+08:00 [QWEN-HISTORY-WINDOW-IMPLEMENTED-SUBMITTED]

- 用户授权：现有32步导航评估1504280继续；新任务独立分支，仅Qwen3.5-2B离线历史窗口对照，跟进到结果打包/浏览验证/普通push。已读取当前AGENTS/STATUS，创建SIGN-qwen-history-window／phase2/qwen-history-window，基于已发布b1c24dc；原训练/Qwen工作树不切换。代码提交0d38369171528ae357557842eb824d7403cca54a，尚未push。
- 复用32条published pilot_2b/diverse_2b保存轨迹/2.5cm地图/pose/actions/heading/collision，不运行policy或sim采样。窗口使用统一终点，当前动作为(start,end]、红线pose[start:end+1]，历史真实动作为(0,start]；段前已见包括起始pose避免初始视野收益。重放原fog投影/3m/90°，初末mask须逐像素等于保存mask；legacy重新从窗口初视野计新面积，history扣全部前置累计。黄宽虚线衬红细线，完整/隐藏黄线的覆盖/统计/prompt/图例/视野比例相同。
- scripts/prepare_qwen_history.py生成去重片段/图片/mask/差异prompt/输入；evaluate_qwen_history.py只调用原SingleImageJudge，FP32/T1/ABC/q不变，class_probabilities与verify_readout不另造框架。核心仅增加prior_seen_area_m2/total_covered_area_m2成对有限性/总量校验并实际串入模型；legacy原3统计保持。全轨迹旧分数只在图/metadata/prompt完全一致且同2B配置/FP32/环境版本时复用，timing留空不编造重跑延迟。package_qwen_history.py保存逐对概率变化/空白人审/待审核线索、默认隐藏分数的无外部依赖HTML与ZIP。
- 首次单测因prepare.py的f-string缺引号SyntaxError失败，修正路径分段；第二次因测试sys.path把scripts置于src前而误导入CLI qwen_topdown.py，出现circular import，调整为src优先。失败原unit_tests_first.log与unit_tests_import.log保留。随后31项单测全部通过，AST/py_compile与git diff --check通过；新源码/旧五工作树源文件/发布输入SHA守卫通过。
- 已执行qsub logs/qwen_history_window_20261029/run.pbs，返回1505083.stdct-mgmt-02；CFP04-SF-109/autox，1A40/36CPU/240GB/20min。脚本依次输入守卫→CPU replay/render→同一个2B模型评分与batch/solo/排列/回答位置验证→报告/打包→源文件再次守卫，失败即停且保留原因。支撑目录submission.json/input_guard.json/check_inputs.py/run.pbs/单测日志，GPU结果尚待实际运行。
- 数据最长256动作，真实历史只可能出现在128窗口；本轮不能验证256带历史、更长episode/多层或在线PPO收益。准备浏览器验证工具仅放logs，不进入Git/ZIP；未启动新导航训练、未停止1504280或两训练，原结果保留。


## 2026-10-29T02:47:28+08:00 [GIBSON-8192K-FULL-COMPLETE-DURING-QWEN-HISTORY]

- 按用户要求未停止1504280；该作业自行完成，qstat确认为F/Exit0、walltime02:50:52。原full_comparison.json已由既有summarize完整核对3×4200任务/起点/目标与nativeTB，runtime complete。基线／coverage256／coverage32 SR0.785／0.792142857／0.774523810，SPL0.489610984／0.469972819／0.504324739，全局新面积/动作0.0771321004／0.0777177531／0.0794907531。这里仅更新完成状态，不新增评估或把这组数据当Qwen训练效果。

## 2026-10-29T02:47:28+08:00 [QWEN-HISTORY-FIRST-RUN-AND-VISUAL-REVISION]

- 首跑1505083 F/Exit0／00:02:23／GN-A40-039；32原轨迹初末重放mask逐像素相同，64窗口请求去重44片段（完整128为12、完整256为5、短段27），12段有真实前置历史且仅128；100图，32旧协议完整原图/原prompt/原metadata严格复用，68新FP32前向，单模型加载40.714s、整个评分阶段64.613s。legacy/history单图batch差4.5644e-5／1.2259e-5，排列差/forward生成首步raw差0；100有效。首包6868427 bytes与全部原audit保留，不视为最终交付包。
- 盲审网页说明补充区分legacy仅窗口初视野与history段前累计；报告将完整128/256与短段单列，记录类别变化和逐对q范围而非平均q判优。第一次派生重打包索引意外包含已有bundle_manifest.json形成自引用，bundle_check_first.log记录哈希不一致；已修正排除自身，新源码提交保留沿革。没有改概率或面积来解决校验。
- 逐像素/坐标检查再发现Swormville/3201的s128_e256，当前起终点均map[323,247]，X完全盖住绿色起点。实际128动作全部碰撞、92个位移<2cm，属于待审核碰撞受阻线索，未将其自动标重复搜索。改为同格时仅加大绿点形成X外绿环，原始位置/红黄线/覆盖/统计/prompt不动；变更图片必须重跑相应评分，不能把旧分数配给新图。原图/首跑/失败像素检查保留。
- 另补原pilot/diverse2B的batch原始token/统计/耗时副本供复用分数审计，CSV新增实际model_statistics_json，明确旧协议实际仅送三字段，历史另送prior/total；未新增Qwen调用框架。31项单测在修正后再通过。最终修正版代码0bb9a90daac3c9199c4f19245c7c93e7f85079fc；qsub新独立logs/qwen_history_window_20261029_revision2/run.pbs返回1505092.stdct-mgmt-02，仅2B、同CFP/autox/A40/20min与相同32原轨迹，无重采样。当前等作业完成再验证/发布。


## 2026-10-29T02:52:16+08:00 [QWEN-HISTORY-FINAL-VERIFIED]

- 修正版1505092完成，F/Exit0／2分51秒／GN-A40-038；运行代码0bb9a90daac3c9199c4f19245c7c93e7f85079fc。同一32源轨迹、同起终点128/256截取、64请求去重44片段，100输入，32原严格相同完整旧图复用，68新FP32前向。单次模型加载74.274s、评分100.652s；不同NFS冷启动造成与首跑加载时间不同，不能当作稳定延迟对比。两套实际padding分别5/0/5与13/0/13；batch/solo最大差1.66119e-5／1.22586e-5，排列与forward生成首步raw差0；100有效。
- 原始保存地图/mpp0.025、3m/90°、fog原点边界投影≤5cm不变，初末mask逐像素重放相同。完整128段12个有真实历史；完整256段5个均无历史，短段27个单列；所有64请求有明确start/end/actual/H及去重alias。CSV保留实际model_statistics_json（legacy三项，history另带prior与total），完整/隐藏黄线的metadata与prompt完全相同。原复用2B batch token/统计/秒数审计已纳入sources，无旧模型生成JSON数字替代新概率。
- 实际执行check_bundle.py解压最终ZIP：387文件SHA/CRC通过，100张PNG均1400×1120、所有当前段绿起点/终点X按原view投影一致（最大实色像素距离5.62px，含同点外环）；所有新面积/段前/总量从mask重算；12完整/隐藏黄线对的像素差只发生在地图绘图区、legend/标题/覆盖/统计不变；44个人审CSV所有human/reviewer/notes列为空。bundle_check.json/log与unpacked_final保存现场。
- 实际Chromium148.0.7778.96 file://断网浏览最终ZIP解压页，100 PNG全部解码，无外网请求或JS异常；默认100个score均display:none，显示/隐藏开关通过，128/256/短段/搜索筛选数量均正确；browser_check.json/log与盲态/显分截图保留，并实际查看Denmark的三栏旧协议/完整历史/隐藏黄线布局。AI视觉检查不是人工行为标签。
- 最终报告：128整体方案最高概率类变化6/12，q差范围-0.4236至-0.0490；仅黄线类变化0/12、q差-0.0407至+0.0379；256无历史协议仍1/5类变化（-0.0802至+0.0867），短段单列。这些只是输入敏感性，整体变化混合覆盖底色/面积基线/prompt/总量，不能据此证明理解历史、准确率提高或按均值q判优。待人审列重复搜索/必要返回/有效扩展/碰撞受阻线索，标签空白；无真实256前置历史、无训练/长episode/多层验证。
- 最终ZIP实际路径/scratch/e1538633/liuyi/logs/qwen_history_window_20261029_revision2/qwen2b_history_review.zip，6902967 bytes，SHA256 b667f514c41b1940bc2342d9a7df64772fe41bd32a61ecd12f526ff33cf3d734。所有轨迹/窗口/PNG/CSV/JSON/prompt与差异/原logits及审计/人审表/复现脚本齐全；两个PBS运行后源HEAD/SHA守卫均通过，没有运行9B、采样、导航训练或主动停止1504280。当前进入根文档生成快照、资料发布校验及普通push；未把待推送写为完成。


## 2026-10-29T02:56:14+08:00 [QWEN-HISTORY-RESULTS-PUBLISHED]

- 已提交并普通push到git@github.com:yiichu03/SIGN.git的phase2/qwen-history-window；最终提交006c8f12a2c63abffb3a21e119673e84d2869e53（Publish Qwen2B history-window controls, audits and offline review results），git ls-remote SHA与本地一致，工作树干净，已跟踪origin同名分支。初始运行代码0d38369、报告修正与绿点补跑0bb9a90及最终资料提交均保留正常历史，没有force/reset或修改原训练分支。
- 运行源码src/scripts/tests/exp_config/run_sim.py相对最终PBS运行commit0bb9a90无差异；412项本轮资料/README入提交，publication_manifest覆盖410文件11975913 bytes，独立check-only通过，源ZIP及包内manifest SHA一致。全量staged格式检查对原prompt unified diff的空白上下文和原qstat末尾空行给提示，保留原文/SHA；精确排除原audit/code/validation快照及该diff后，新生成文档格式检查通过，未声称全量原始证据格式通过。完整输出staged_whitespace.log保留。
- 最终ZIP仍为/scratch/e1538633/liuyi/logs/qwen_history_window_20261029_revision2/qwen2b_history_review.zip，6902967 bytes，SHA256 b667f514c41b1940bc2342d9a7df64772fe41bd32a61ecd12f526ff33cf3d734；没有把重复ZIP/模型/场景/环境/浏览器依赖推入Git。图片100输入及原轨迹/mask、完整概率与真实logits/耗时、prompt差异、窗口alias、原复用batch审计、空白人审表与复现脚本均在资料目录。原初跑/QA失败与修正留在对应server日志，最终VALIDATION/WORKLOG明确其区别。
- 发布四根文档快照截止2026-10-29T02:52:24+08:00；当前push回执只追加服务器WORKLOG并更新STATUS，不循环生成副本提交。浏览器检查/图片抽查仅AI工程核验，不代表人工标签。任务完成，下一步留给用户盲审；未进一步训练、重采样或跑9B。


## 2026-10-29T13:04:29+08:00 [QWEN-HISTORY-SOLID-SUBMITTED]

- 用户先要求黄线直接用实线、与红线只有颜色区别并微调prompt，随后明确要求修改后重新运行并打包下载。本轮在既有独立phase2/qwen-history-window继续，未触碰原训练目录或旧虚线数据。yellow原4.8pt虚线改为1.5pt实线，与red同宽同型，图例一致；同格端点绿环保持。完全重合会由红线覆盖黄线，为避免伪造路径不做错位/横向偏移，prompt作此说明，只评价当前红段，ABC/碰撞受阻等标准不改。
- prepare_qwen_history.py与package_qwen_history.py仅相关线型/prompt/说明修改，31项单测通过、diff格式检查通过，提交30ed53d1a969e830df9b98e1b67ccab0629aeb2e。旧虚线006c8f1／1505092的PNG/概率/ZIP/提示词原样保留，新增输入不挂用旧图分数。
- 新独立支撑logs/qwen_history_solid_20261029，刷新自身源码守卫为已批准新commit，原五工作树HEAD/SHA与旧发布376文件SHA仍核对不变；bash -n通过。已执行qsub /scratch/e1538633/liuyi/logs/qwen_history_solid_20261029/run.pbs，返回1506387.stdct-mgmt-02，CFP/autox、A40/36CPU/240GB/20min。同32原始记录/64请求/去重窗口/地图/覆盖面积、FP32/T1/ABC，不采样、不训练、不跑9B。复用原图完全相同的legacy完整段32分，其余68输入按新图/prompt新推理；GPU有效性、像素/解压浏览校验与最终打包尚待实际完成。


## 2026-10-29T13:09:19+08:00 [QWEN-HISTORY-SOLID-VERIFIED]

- 1506387.stdct-mgmt-02完成，F/Exit0／2分36秒／GN-A40-022；运行代码30ed53d1a969e830df9b98e1b67ccab0629aeb2e。100评分有效（32原图/原prompt/原统计完整legacy严格复用，68按新图/prompt重新FP32前向），单模型2B；源守卫开始与结尾均通过。batch/solo最大概率差legacy1.66119e-5／history2.10645e-5，排列及forward/生成首步raw差0，padding5/0/5与13/0/13。没有9B、采样、导航训练。
- 与此前1505092逐项核对，windows.segments、requests及100个输入的id/metadata完全相同；prompt从action_count段开始至末尾原文相同，只有路径描述/同宽实线/完全重合遮挡说明变化。style_audit.json和prompt_style.diff保留新旧SHA与逐行差异。旧虚线包、概率和图片不覆盖。
- 实际解压验证通过387项文件SHA/CRC，100 PNG均1400×1120、全部当前起终点对应坐标正确、覆盖mask面积重算和人审空白通过；12个完整/隐藏黄线对除地图内可见黄线外无像素差。对于同宽实线允许历史被当前红线完全遮挡，不偏移坐标或强制制造黄色像素；prompt已说明未见黄色不等于没有历史。
- Chromium148.0.7778.96在file://且断网时100图全部解码、44去重片段显示、默认分数隐藏/开关及128/256/短段/搜索筛选检查均通过，无JS异常或外网请求。报告继续区分完整128/256及短段；128整体协议改变最高概率类6/12，黄线额外改变1/12（q差-0.07273至+0.02816），只作敏感性描述，不以均值q判优，不自动填人审标签。
- 最终ZIP /scratch/e1538633/liuyi/logs/qwen_history_solid_20261029/qwen2b_history_review.zip，6901870 bytes，SHA256 17179a590ac4648072dc021d82b9473ee230cb57d753a3dd34c1c8c7068c83d6。全部PNG/CSV/JSON/原轨迹与窗口/实际model统计/prompt和原logits/空白人审/复现说明齐全。准备按现有流程生成根四文档副本并普通push新源码/实线版资料，尚未把push记为完成。


## 2026-10-29T13:12:49+08:00 [QWEN-HISTORY-SOLID-PUBLISHED]

- 已普通push当前实线源码与独立资料目录到yiichu03/SIGN的phase2/qwen-history-window，最终提交453179cd67c348576d974aa7bf38203044a7eef6，ls-remote与本地一致、工作树干净。src/scripts/tests/exp_config/run_sim.py相对PBS运行30ed53d无变化，未修改其他工作树或运行新训练。
- 新docs/experiments/qwen-history-solid与README导航共414文件入提交；publication_manifest覆盖412文件12036018 bytes，check-only全部SHA/大小/相对链接/凭据模式检查通过；旧qwen-history-window虚线资料未改。构建完成后重新stage全目录并按原始audit/code/validation及unified diff例外检查新生成文件格式通过。
- 最终下载ZIP /scratch/e1538633/liuyi/logs/qwen_history_solid_20261029/qwen2b_history_review.zip，6901870 bytes，SHA256 17179a590ac4648072dc021d82b9473ee230cb57d753a3dd34c1c8c7068c83d6，实际解压与Chromium断网100图浏览/盲态开关均通过。提供本地新目录qwen_history_solid下载命令，避免覆盖用户先前虚线盲审资料。
- 根文档快照截止2026-10-29T13:10:40+08:00，本推送回执只在服务器WORKLOG追加/STATUS更新，不循环生成资料提交。保留所有人审字段空白，等待用户查看实线版；本轮授权任务完成。


## 2026-10-29T13:36:18+08:00 [COVERAGE-TWO-TRAINING-20261029-READOUT]

- 用户要求检查当前运行的两个训练。qstat核实1497416／1502352均R，分别GN-A40-029与GN-A40-094、auto→batch_gpu，运行约55:21／23:55，预算仍168h；日志持续更新。读取当前AGENTS/STATUS/RUNBOOK，原训练源码/参数/目录/作业不动，没有评估或提交新任务。
- 复用原logs/gibson_train_threeway_20261028/analyze.py，SHA固定记录请求，sign-baseline环境CPU只读有限字节快照三个TensorBoard事件流（含已停止基线供同预算历史参考），导出CSV/PNG/PDF/comparison.json，执行Exit0；记录logs/gibson_two_coverage_training_20261029/snapshot_132741/analyze.log、source_report.json，实际数据目录logs/gibson_train_threeway_20261028/snapshot_132900。另生成readout.json，不另建会话总结文件。
- 事件快照截止256版68528128步/13:29:45、32版18835456步/13:30:49，34项scalar全部有限，两组所有bonus守恒误差≤1.79e-8。各自最近100万步均值：256 SR87.3428%／SPL49.5004%／0.180528m²每动作；32 SR85.4586%／SPL47.9761%／0.170127m²每动作，阶段不同不可简单排名。末点SR88.067%与90.087%只是原生50-update滑窗，不取单点当趋势结论。
- 共同16.835456–18.835456M最近2M：256／32 SR86.41225%／86.23282%，SPL48.34867%／49.29889%，新增面积/动作0.16718056／0.17057481，32的SR-0.1794pp、SPL+0.9502pp、覆盖效率+2.0303%；SR优势不稳定。共同最近1M SR85.129%／85.459%、SPL47.070%／47.976%；最近0.5M SR87.409%／88.501%、SPL47.475%／48.683%，反映32近期从低谷回升，不能将滑窗相关点视作独立样本。
- 256自己最近5M（63.528128–68.528128M）SR86.948%、SPL49.679%，历史基线同区间89.279%／54.778%，仍落后2.33/5.10pp。已实际查看曲线，当前总体趋平台、波动明显；32稍好的SPL/新面积是单种子训练趋势，不等于验证收益或证明冗余搜索减少。记录的reward仍是导航奖励，不含另外加给PPO的coverage bonus；coverage新面积由每rollout除2048动作计算，非episode效率均值。原两实验仍不包含Qwen奖励。

## 2026-10-29T13:36:18+08:00 [TENSORBOARD-INITIAL-LOAD-CAUGHT-UP]

- 用户补充现有SSH16006→远端6006命令看不到最新。读取脚本确认三组路径正确、max_reload_threads3、load_fast=false；ps/ss核实新服务PID1088282于13:26:55启动并监听127.0.0.1:6006，/data/environment与tags/runs一致、后端reload_interval5秒。一次尝试读取不存在的旧view_tensorboard.sh得到文件不存在，该文件不是用户正在用的入口，随后只围绕实际view_personal_tensorboard.sh/API诊断，没有改脚本或杀服务。
- 直接保存网页API原始scalars及末步/时间：首次baseline仅约19.82M/10月27日、coverage256约16.30M/10月27日、32约17.34M/当天11:26；13:31:52已推进至40.657M／33.855M／18.829M，说明后端正在首次从头读大文件，而非训练停更或仅悬浮框选旧点。证据tensorboard_http_readout.json、progress_second.json及6份HTTP原JSON。
- 继续核验至13:33:54，baseline74653696（最后事件10月28日20:28:29，原已停）、coverage25668610048（13:33:45）、32为18870272（13:33:38），三组均已追上审计事件快照。progress_third.json逐项caught_up=true，首次载入约7分钟。已告知用户原命令正确、保持连接并刷新127.0.0.1:16006，选两个coverage查看；无需重启训练或再开服务。用户本地页面状态不可直接读取，因此若API已最新仍显示旧范围，再刷新/清除局部缩放/核对所选run。根STATUS/RUNBOOK已更新诊断方法。


## 2026-10-29T13:46:03+08:00 [GIBSON-BASELINE-REFERENCE-INDEX]

- 用户先询问已停对照基线的步数、公开checkpoint完整验证分数，要求文档易索引；仅表示考虑再提交两版本评估，并明确先回答这两个问题。本轮只读核对与整理文档，没有新qsub/评估/训练或push。
- 当前对照基线1496716于2026-10-28 20:28:36停止，最终TensorBoard为74653696步/20:28:29；重核原事件文件60828746 bytes及SHA与已有完整只读快照一致。原BASELINE-1496716-STOPPED-TO-FREE-QWEN-GPU记录74649600是最后控制台20:28:21打印，较最终TB少4096步（2更新），不是checkpoint步数，也不改写原操作日志。保留模型CPU审计step74240000，重算last_saved_checkpoint.pth SHA与preservation.json的c3bf5d3e13a789f28b95c92b93ae7e31c4327f4a328bf59632f504b7b1eed73f一致；后续公平评估按权重step匹配。
- 公开完整SIGN checkpoint评估1494521原pretrained_full_result.json：Gibson val4200条/14场景，SR0.8600000143051147、SPL0.5300576090812683、ViewMatch0.8508333563804626，对应86.00%／53.01%／85.08%；原源码dad87fe、完整nav_model、6环境、20分34秒、Exit0，PYTHONHASHSEED原记录未显式固定。该结果与仅加载并冻结visual_encoder后训练其余模块的基线分开命名。
- STATUS顶部增加gibson-reference表，RUNBOOK顶部gibson-checkpoints提供权重/事件/原验证JSON与协议入口，AGENTS增加稳定导航；所有新相对链接与锚点核验，不另建重复上下文文档。机器可读核验记录logs/gibson_reproduction_20261026/baseline_reference_index_20261029.json，根WORKLOG仅追加，原发布副本不手改。


## 2026-10-29T13:56:14+08:00 [GIBSON-THREEWAY-18944K-EVAL-SUBMITTED]

- 用户明确授权把基线及两个覆盖版本验证放在一个PBS提交。本轮按此前共同训练步数对照的口径，已提前说明采用最新共同checkpoint；盘点baseline145份至ckpt.144、coverage256为134份至ckpt.133、coverage32为37份至ckpt.36，最新共同ckpt.36。准备后CPU实际三份extra_state.step均18944000，不用末训练TB数或文件名推测替代实际值；state_dict全部有限，复制三份独立权重，源与副本SHA再次一致。
- 新支撑logs/gibson_threeway_coverage_eval_20261029。prepare/preflight/evaluate/recording_env/run_all/summarize六脚本逐字节复用已成功8.192M批次，不改算法或复建框架，PBS仅名字及新目录变化。CPU preflight合并配置/6环境/max500/seed100/hash0/完整4200val/FOV与零权重测量/终止记录reset与reward被动性检查全部通过，源码HEAD/SHA、数据/安全模型和脚本哈希通过；bash -n通过。
- 已执行qsub /scratch/e1538633/liuyi/logs/gibson_threeway_coverage_eval_20261029/evaluate.pbs，返回1506785.stdct-mgmt-02；submission.json保存原命令/回执。qstat核对R、CFP04-SF-109／autox→batch_gpux、GN-A40-021／1A40／36CPU／240GB／4h。runtime为control_baseline，后续前置对照/smoke过关才依次跑baseline/coverage256/coverage32各4200，共12600正式episode，并要求相同任务/起点/目标图与原生TB对上。GPU前置与完整结果尚未完成，不把提交记为评估通过。
- 根据此前两完整作业约2:59和2:51估计本次开跑后约3h。新结果独立目录，原三组训练目录/代码/分支/参数及旧4.608M、8.192M原始结果不动；1497416／1502352核对均R，未重启已停止1496716，也未提交新导航训练或Qwen。STATUS顶部快速索引新增本轮pending行并更新Gibson当前任务，RUNBOOK追加命令/协议/进度入口；本轮未push。


## 2026-10-29T15:00:31+08:00 [QWEN128-REWARD-INTEGRATION-STARTED]

- 用户明确授权从已验证453179c新建独立训练分支、通过单测与40960步真实GPU短跑后直接提交全新正式训练，并安排4.608M/8.192M的4200条val评估。已读当前AGENTS/STATUS；已建立SIGN-qwen128-reward / phase2/qwen128-reward-beta01，原运行目录/作业与离线结果不动。
- 当前提取原离线绘图/面积函数，开发增量覆盖、真实reset前片段快照、严格身份账本及独立FP32 2B常驻worker；尚未完成集成验证，不声称已提交或通过。训练环境不升级，MRQ原导航目标与PPO混合奖励分离；关闭/零权重及评估不启动worker或采集。


## 2026-10-29T15:10:04+08:00 [QWEN128-CPU-PASSED-GPU-SHORT-SUBMITTED]

- 新独立源码提交81fedec，54项CPU单测全部通过（原39+新15）；真实已发布离线轨迹的增量mask/统计完全一致，覆盖初始视野/重复观察/历史跨rollout、终止/128/rollout边界、身份错误/重复回填拒绝、mask/nav_rewards隔离、禁用/零权重不启动worker、eval关闭采集及旧MRQ配置兼容。日志logs/qwen128_unittest_full.log。
- 已提交CFP04-SF-109/autox短测1507196.stdct-mgmt-02，GN-A40-098，1A40/36CPU240GB/1.5h。顺序原冻结基线8192步、新分支beta0同8192步、beta0.1正式逻辑40960步；全部从新初始化，输出SIGN-qwen128-reward/results/qwen128_reward_20261029，原训练目录仅复用原代码、模型和数据，输出在新树。当前仍运行，尚未声称GPU通过或提交正式训练。
- 完成训练环境/依赖原样使用，Qwen独立qwen35 FP32进程；额外快照和payload在auto-reset前形成，trainer移除后再做标量统计。源守卫覆盖六个既有/新工作树和公开模型/数据/prompt；不为新授权变更沿用原版源码拒绝规则。
- 一次从根目录用runpy导入新run_sim导致ModuleNotFoundError: src，已改为仓库工作目录运行单测；两次依赖路径探查用到了不存在的gym目录，随后定位habitat/utils/gym_definitions.py确认其只传habitat子树，已显式克隆Qwen环境配置到该子树，第三方依赖不改。


## 2026-10-29T15:24:43+08:00 [QWEN128-GPU-PROBABILITY-AND-ADDRESSING-CHECKS]

- 1507196仍在运行，当前进入40960步Qwen短测中段；同节点原基线/零权重各8192步已完成，全部训练标量逐位相同，checkpoint只有5项Qc参数有最大1.4901161e-8差异，其他参数逐位一致。第一次严格全checkpoint相等断言失败已保存zero_beta_checkpoint_check.json；不会声称全checkpoint逐位一致，也不改变Qc。计划在同一GPU追加原基线8192复跑核对该量级数值差异，最终结论以short_validation.json为准。
- Qwen常驻FP32实际读出首轮通过ABC答案位置/left padding/独立batch、solo和排列/生成首步logits核验：A32/B33/C34，batch/solo最大概率差9.02514e-6，排列及生成首步差0。原prompt SHA12081a916f12d7be09cf64bfcfc390bcfcdf2508fd5eda9f195943615027c404；未生成JSON数字代替概率。
- 额外CPU重放32原始轨迹全部44窗口，在线增量prior/final mask及面积统计完全等于已发布实线版；2.5cm墙体遮挡合成检查通过。八环境六轮随机真实reset/边界交汇账本检查12288 transition/446片段通过；首次附加测试用(r+bonus)-bonus逐位反推原浮点数产生舍入断言失败，已改为直接比较未修改nav缓冲快照，奖励差另用浮点误差界验证，未修改奖励实现。证据offline_online_geometry.json、addressing_validation.json及日志。
- 已实际查看Stilwell与Superior真实GPU输入，后者当前段60步、前置历史173步；黄红实线/起终点与深浅蓝沿用公共绘图。真实长历史输入将继续由保存位姿重放核对；未将自动评分或短跑SR当作训练收益。
- 两个未来checkpoint的watcher提交/重启无重复逻辑用模拟PBS回执验证通过（watcher_validation.json明确标注非真实提交）；正式训练和未来评估尚未qsub。现有1497416/1502352/1506785未改。


## 2026-10-29T15:35:10+08:00 [QWEN128-GPU-SHORT-PASSED-FORMAL-AND-EVALS-SUBMITTED]

- 1507196完整Exit0/27分17秒。原基线8192+beta0同8192+Qwen40960/20更新+原基线复跑8192均完成；Qwen1204片段中1176有效（97.6744%），23高度范围越固定楼层/5距navmesh超过5cm容差跳过bonus并记录原因，887真实terminal。所有模型/55项训练scalar有限，42项公开encoder状态逐位不变，visual_fc未加载公开值且正常更新，Qwen/零权重初始状态哈希完全一致。nav_rewards/masks不变，ID无重复，原始q范围0.13028–0.86958，mean0.53831，累计bonus8.88134。
- 原基线与beta0：98项checkpoint逐位一致，仅5项Qc有≤1.49e-8舍入差；同节点原基线自身复跑出现6项Qc≤2.98e-8差，其他模块仍逐位一致。全部29项原训练scalar逐位相同；Qc源码、超参数和运算选项均未改，不把微小数值差隐瞒为完整bitwise一致。证据short_validation.json及原始四组日志/checkpoint。
- 在线实际保存样图前置历史175/当前63步（r0000015_e7_reset65_s175_t238，窗口/实际长度以JSON为准）由记录位姿重新计算，prior/final mask/所有模型统计及PNG逐字节相同；整个短测最大段前历史230步，未声称完成1000步真实长历史GPU压力验证。已发布32轨迹44窗口和合成遮挡/八环境边界/真实milestone保存/评估配置检查均通过。
- 热身后短测中位每2048步：原基线7.54696秒、beta0 7.59720秒、Qwen59.24437秒；Qwen采图/评分平均每轮15.236/14.090秒，增量几何时间9.473秒是8环境CPU耗时之和，不能直接当额外墙钟。Qwen工作进程峰值9.362GiB，总GPU 5秒采样峰值24947MiB。初期频繁episode结束（每轮约60片段）是开销来源之一；当前仅验证工程正确性，不声称SR收益或完整预算速度恒定。
- 正式从新初始化提交个人auto作业1507268.stdct-mgmt-02，运行源码81fedec56b37921c350ce8064106c32788bb3e04，1A40/36CPU240GB/168h，300M算法上限；8×256/seed100/hash0/冻结公开visual_encoder/其余原初始化，Qwen128 beta0.1原始q、几何bonus0，独立results/qwen128_reward_20261029/train_personal_8env，TB开启，不加载短测权重。提交回执logs/qwen128_reward_20261029/submission.json。
- 评估最终采用预提交PBS依赖：CPU waiter1507269/1507271以after正式训练开始释放，只核对4.608M/8.192M不可变权重的真实step/SHA；GPU val1507270/1507272分别afterok对应waiter，当前H等待，尚无评估结果。每组4200val/14场景、原6环境/max500/seed100/hash0与原0.1m被动coverage协议，Qwen和Qwen轨迹采集关闭。相对于此前动态qsub草案，此方法直接保留实际GPU评估ID且避免计算节点提交依赖；草案调试留logs/.../debug，未对原工作树或旧结果做改动。


## 2026-10-29T15:42:48+08:00 [QWEN128-FORMAL-FIRST-UPDATES-VERIFIED]

- 正式1507268在GN-A40-098运行，独立2B worker已一次加载FP32并完成4轮Qwen结算；TensorBoard8192步、55项scalar全部有限，原reward与新增qwen指标分开。正式初始103项状态SHA与短测Qwen初始完全一致，确认全新初始化；实际qwen/effective_config.yaml已复制到支撑formal_effective_config.yaml，root/环境子树collect为True，beta0.1/128/256/8环境及geometry weight0生效。证据first_training_events.json、train_personal_8env_command.json与正式qwen原日志。
- 两CPU等待已启动并记录ready=false；两GPU评估H等待对应afterok，已有真实提交回执，不动态重提。原1497416/1502352继续R；旧1506785已自然结束，本轮未停止或变更它。
- 新建独立detached SIGN-qwen128-publication @81fedec，用于新证据/根四文档生成副本；不在运行树改源码或HEAD。准备发布branch phase2/qwen128-reward-beta01，尚未把push写为完成。


## 2026-10-29T15:50:18+08:00 [QWEN128-REWARD-PUBLISHED-AND-RUNNING]

- 已普通push独立分支phase2/qwen128-reward-beta01到git@github.com:yiichu03/SIGN.git，发布提交35b978fc6b3203e2922a05d1847f88fda98100aa，ls-remote与本地完全一致。生产源码81fedec包含12文件集成；独立publication树另提交49项README/证据/两组样图及npz/根四文档生成副本，运行目录HEAD及全部原工作树源哈希仍通过source_manifest守卫。发布树干净，未切换或修改训练目录、未force push，未上传新权重/场景/环境。
- 包内47项SHA/大小/全部相对链接/凭据模式通过；WORKLOG副本与发布时根源字节一致且保留旧453179c已发布前缀。非WORKLOG根快照的服务器证据链接生成显式服务器路径，避免GitHub死链；不是另行手工维护上下文。发布回执logs/qwen128_reward_20261029/push_result.json。
- 正式1507268持续写Qwen/TB，控制台已至少20480步/10更新，当前12轮Qwen结算；两CPU waiter状态15:48:53仍ready=false持续轮询，两GPU1507270/1507272仍H等待milestone，各有4200val协议与真实依赖回执。新6007 TB查看脚本已提供但未自动启动服务器；原6006服务和两原覆盖训练不动。旧三方法1506785 runtime.json为complete，属既有作业自然完成，结果未修改。
- 最后批次登录节点qstat -fx对1507196/1507268两次20秒超时，已保留scheduler_verified.json；其他作业状态正常返回，正式原生日志/TB/Qwen结算和计算节点wait_state仍持续更新，未把查询超时误判作业失败或重提。服务器WORKLOG/STATUS在push回执后再追加更新，不循环发布新资料提交。


## 2026-10-29T15:57:23+08:00 [PBS-GPUX-PREFERENCE-CONFIRMED]

- 用户澄清希望等待可执行的GPU实验优先放gpux以便更快开始。已核实当前两未来val1507270/1507272的queue均batch_gpux、project CFP04-SF-109、Hold_Types=d、afterok对应CPU等待任务；提交脚本本来使用autox。当前没有资源排队Q状态GPU任务可迁移，三训练均R；Qwen1507268为personal-e1538633/batch_gpu/GN-A40-098。
- 依赖需要等待真实4.608M/8.192M权重，不能通过换队列提前产生权重。保留现有作业/依赖，无qmove/qdel/qsub或预算改变。沿用已实测个人项目拒绝autox的许可限制；稳定记录用户偏好：在项目许可与既定预算内，可运行但排队的GPU任务优先autox→batch_gpux，已运行任务不为换队列停训重提。AGENTS/RUNBOOK与STATUS更新；未触发额外GitHub发布。


## 2026-10-29T16:03:52+08:00 [QWEN128-FORMAL-47104-PROGRESS-SNAPSHOT]

- 用户询问目前Qwen进展，以为本轮仍为短测，并要求同步最新代码/文档到yiichu03供外部分析。已先说明短测1507196已完成，正式1507268此前依用户“通过后直接提交正式训练”授权已启动；本轮只读分析和发布，不停止现有作业、不新提交训练或评估、不改变算法。
- qstat核实三训练R、两CPU waiter R、两未来GPU val H且已在gpux；正式源码仍81fedec，发布树干净35b978f，origin push URL为git@github.com:yiichu03/SIGN.git。运行目录仅未跟踪本地data软链接，保留。
- 新snapshot_progress.py有限字节复制正式TB/JSONL，再将指标统一截到完成23更新的47104步；55项scalar全部有限、1399/1431段有效97.7638%（25高度跨度/7 navmesh容差无效），无重复ID，nav_rewards/masks不变，bonus公式/总量守恒。q min/mean/max0.11497/0.54527/0.87636，累计bonus10.36529。原导航reward末点-0.57639、训练SR3.59922%/SPL2.80694%，同47104步已停冻结基线原始前缀SR3.20000%/SPL2.21177%、reward-0.73818。只作早期相关滑窗描述，未当独立验证收益。
- 热身后每2048步中位64.2636秒，最近10轮63.7929；正式ckpt目录为空，预期首次250更新=512000步，未错误宣称已有正式权重。所有原始事件前缀/逐段概率/图/统计/配置/SHA保存在logs/qwen128_reward_20261029/progress_20261029T160130，CPU分析Exit0，没有GPU或导航评估。
- 准备在独立SIGN-qwen128-publication从35b978f追加新快照、更新README和根四文档生成副本。扩展既有构建器--progress更新模式，先验证旧manifest全部SHA和WORKLOG前缀；不重复开发发布框架，生产src/scripts/tests/exp_config/run_sim.py保持81fedec原内容。尚未将本次push记为完成。


## 2026-10-29T16:06:37+08:00 [QWEN128-47104-PROGRESS-PUBLISHED]

- 最新训练快照/同阶段基线CSV/逐段概率及面积/实际配置/原始事件和曲线、四根文档生成副本已普通push yiichu03/SIGN的phase2/qwen128-reward-beta01，新提交33e30d28eecdcce557b0f453004a35de0bdebcbf，ls-remote SHA完全一致，独立发布树干净。代码已经是已验证最新81fedec，本轮新增的只是只读分析/资料更新工具和文档证据，无生产算法改动、无新qsub、现有训练继续。
- 新包59项SHA/大小、所有相对链接、既有WORKLOG严格前缀与根源字节一致、原/运行工作树source_manifest全部通过；旧短测证据保留、未上传新权重。发布新增19文件变更含不可变progress_20261029T160130，完整入口docs/experiments/qwen128-reward/README.md。服务器回执logs/qwen128_reward_20261029/push_progress_result.json，root STATUS再记录新提交，不循环刷新发布副本。


## 2026-10-29T16:13:30+08:00 [GIBSON-18944K-FULL-VAL-RESULTS-REVIEWED]

- 用户询问四个Qwen wait/H作业用途，以及此前三方法val是否完成/结果。本轮只读调度和已结束结果，未提交/停止/修改作业或发布GitHub。qstat确认1507269/1507271为R的CPU checkpoint等待，1507270/1507272为batch_gpux中afterok对应waiter的H导航val，分别4.608M/8.192M；评估时Qwen关闭、等待不占GPU，实际训练仅1507268，两旧覆盖训练继续R。
- 1506785已于2026-10-29 15:29:34结束，PBS F/Exit0/1:35:43，runtime.json complete、所有阶段及full summary完成。共同ckpt.36实际18944000步，3×4200val/14场景，原确定性6环境/max500/seed100/hash0、0.1m/3m/90°被动coverage weight0及公共safety。已有smoke/control保证coverage测量未改变基线轨迹/指标，full检查共同起点/目标图与完整任务集。
- 本轮独立逐条读出三组episode JSONL，分别4200条/4200唯一任务，SR与global效率重算等于full_comparison.json。基线/256/32成功3289/3322/3445，SR78.3095/79.0952/82.0238%，SPL51.6374/51.9819/51.7534%，global新m²/动作0.07591915/0.07661201/0.08271614，mean episode新m²/动作另为0.19071928/0.19458895/0.20008748；两种聚合严格区分。平均动作144.4576/145.9731/137.9917、平均碰撞44.3381/42.7290/50.4871。
- 32版相对基线SR+3.7143pp（多156成功），global覆盖效率+8.9529%，SPL+0.1160pp基本相同，平均碰撞+6.149（约+13.87%）；256版SR+0.7857pp、SPL+0.3445pp、global效率+0.9126%、碰撞-1.609。只作当前单种子同预算checkpoint验证观察，不等同所有训练阶段获益、冗余搜索直接测量或Qwen收益。STATUS顶部索引和Gibson当前进度纠正为已完成，RUNBOOK新增结果/聚合口径索引；旧提交记录与结果不覆盖。


## 2026-10-29T16:25:26+08:00 [GIBSON-300M-REMAINING-TIME-ESTIMATE]

- 用户询问两个覆盖训练若以300M步上限计算还需多久。本轮仅读原console固定字节前缀并解析时间/frames，未改源码/队列/时限或提交任务。新CPU estimate.py保存近12h时间步数CSV、源SHA/大小及1/3/6/12h吞吐与估计。快照2026-10-29 16:22:39，256最新72151040（24.05%）剩227848960，32最新20746240（6.92%）剩279253760。
- 近3h步速256352.50095、32186.88167，保持当前速度分别需179.5495h/7.4812天、415.0781h/17.2949天；近1/6h对照256194.10/173.02h，32429.70/395.02h，显示速度波动，未使用全程平均fps作未来保证。
- 代码/实际合并配置核实stop_step=50000000、MRQ=True、shift=True，trainer达阈值设置use_aug_flag=False；PPO.py只有MRQ块/其日志受该flag控制，RandomShift分支仍只检查shift=True。因而准确说法是50M后停止MRQ辅助训练，旧记录中“停止数据增强”的笼统说法应以本条澄清为准，原代码未更改。256已过50M、32尚未，不能将速度差直接归因于32步结算开销。
- 条件估计：32剩29253760步按186.88步/s约43.48h达到50M，之后250M若按256当前352.50步/s约197.01h，共240.49h/10.02天。该后段速度尚未在32验证；原RandomShift保持，不声称固定速度或自动续训。
- PBS当前剩256109.71h（11月3日06:04:59到期）、32141.14h（11月4日13:30:46到期），均不足300M；保持3h固定速度到期约211.37M/115.70M，32按上述MRQ停止后加速条件则约173.92M。详细机器可读证据logs/gibson_training_budget_20261029/estimate.json，STATUS/RUNBOOK更新，本轮未push。


## 2026-10-29T17:13:17+08:00 [QWEN-ABC-ABLATION-STARTED]

- 用户明确授权以33e30d2在独立工作树实施A Qwen128 beta.03、B Qwen256 beta.03、C同采集规则几何128对照，边界/冻结/短测通过后从fresh-init经autox提交正式与两个milestone4200val。已读AGENTS/STATUS，启动SIGN-qwen-ablation / phase2/qwen-beta003-geometry128，不改1507268/两旧coverage及原评估依赖。
- 原短测1204段/1176几何有效段复算sum(L*q)=22736.24026696853、sum(new_area)=2329.8712499999997m²，alpha=.03*sum(L*q)/sum(area)=0.2927574680399425。源segments SHA26180a9e26faa7024f0564193c66d46a8cbb31d1e2c1d99254aeb49b00d81bd7，与用户预期一致；接下来冻结到配置并保存逐段校准证据，不在新训练数据上重新拟合。
- 实测batch_gpux队列允许168h、每作业最多2GPU，max_run为每用户4个运行作业；已有两GPU val H为依赖等待、不分配GPU。正在核实项目权限/余额和server限制，尚未以队列规则冒充已查到项目余额。


## 2026-10-29T17:23:16+08:00 [QWEN-ABC-CPU-PASSED-SHORTS-SUBMITTED]

- 实现提交d2352f0基于33e30d2，运行新SIGN-qwen-ablation分支phase2/qwen-beta003-geometry128。新增A128/B256 beta.03配置和C128几何alpha.2927574680399425；显式MRQ target navigation独立于Qwen开关，原配置无字段时保持mixed；原奖励/其他损失和超参数/encoder逻辑未改。B支持256结算，C共用EpisodeCoverage/ledger，只加alpha*area/256，不调用worker/render，不写q/result字段，旧coverage权重0。
- 63项CPU单测全部通过，日志unit_tests_pass.log。包括旧39项、原15项及新增9项窗口256终止/跨rollout、物理面积不走概率范围、无效段跳过/错误原子失败、冻结校准、独立MRQ目标及C禁止worker/renderer与eval关闭采集。首轮因新测试改变RNG顺序暴露旧测试(r+bonus)-bonus逐位反推nav的舍入断言，已改为直接比较nav快照，不改奖励算法；失败原日志unit_tests.log保留。
- 按A/C优先顺序经CFP04-SF-109/autox各提交40960步独立fresh GPU短测：A1507600、C1507601、B1507602，均已R。每作业1A40/36CPU240GB/1.5h，接受且实际开始运行确认当前CFP/Express提交权限。队列max_run4为每用户Express队列运行作业数；已有两GPU评估H依赖保留，不占GPU。hpc project仍要求amgr login，未取得余额数值，不把接受短测等同已核实长期余额。查询快照gpux_queue_before.txt/project_query.txt/gpu_status_before.txt/jobs_before.txt。
- 源守卫覆盖新运行树及原六树、公开模型/数据/prompt/冻结calibration SHA；未切换或修改原1507268与两coverage目录/作业，未重提原任务。短测尚未完成，正式A/B/C尚未提交。


## 2026-10-29T17:40:10+08:00 [QWEN-ABC-SHORTS-PASSED-FORMALS-SUBMITTED]

- 三组各40960步/20更新已通过verify_case：A1507600、B1507602、C1507601，短测报告分别A/B/C有效率97.8459/97.8032/97.9832%，中位40.3921/35.3629/27.8671秒每2048步，累计bonus2.66236/2.74941/2.36669。模型/TB全有限、42项encoder不变、visual_fc更新、原nav_rewards/masks不变，ID唯一、边界/bonus逐段与总量守恒；A/B独立单图FP32读出核验通过，C无worker/PNG/q字段。实际B最长段239步，受真实terminal缩短；完整256与跨rollout边界由CPU构造回归覆盖，不人为修改终止。
- A首轮52张有效图/metadata/ID与旧已验证短测完全相同，A/C首轮55段（52有效）窗口/面积/有效性全部一致，证据first_input_parity.json/control_input_parity.json。三个103项初始化哈希也等于旧冻结实验初始状态，保留全新初始化与冻结编码器协议。校准集bonus总量匹配2.664403，不把新策略实际bonus总量差异当需重新拟合alpha的理由。
- 全部GPU短测通过后按A/C/B顺序正式qsub：A1507648、C1507650、B1507651，实际均R，CFP04-SF-109/autox、1A40/36CPU240GB/168h、300M cap，源码d2352f0不改；全新输出results/qwen_ablation_20261029/{case}/train，不加载短测权重。实际168h请求接受核实长期提交许可；项目余额数值仍未知，Express maxrun4和已有两H评估不占GPU已核实，不编造余额。
- 新六GPU val依赖回执已提交：A4.608M1507653（wait1507652）、A8.192M1507655（wait1507654）；C1507657（wait1507656）/1507660（wait1507659）；B1507662（wait1507661）/1507664（wait1507663）。GPU均H等待对应afterok，CPUwait以after训练开始启动，初查A/C的四CPU R，B两CPU Q，符合资源不足先A/C；旧1507270/1507272依赖保留，原1507268/1497416/1502352仍运行。
- 新评估复用旧recording_env与native evaluator，只按case/step定位输出，原4200val/14场景/6环境/max500/seed100/hash0/公共safety、0.1m被动coverage weight0；关闭Qwen及奖励轨迹采集。报告原生SR/SPL、两种覆盖效率、碰撞、动作、耗时；训练另外保存段长/bonus分位数和q分布。全部6个waiter路径/源SHA/损坏拒绝与精确milestone保存CPU检查通过，尚无新val结果。正式和短测配置/命令/回执位于logs/qwen_ablation_20261029。


## 2026-10-29T17:43:15+08:00 [QWEN-ABC-FORMAL-FIRST-UPDATES-VERIFIED]

- A1507648/B1507651/C1507650均R且已有原生TB更新，快照步数分别4096/6144/26624；标量均有限、formal103项初始状态SHA与各自short相同。A/B FP32常驻worker实际启动，C仍无worker。formal_effective_config.yaml已保存，包含运行时collect=True及独立navigation MRQ目标，来源相同全新初始化，不恢复short checkpoint。证据logs/qwen_ablation_20261029/first_formal_events.json及各case配置/日志。
- 正式三组168h与六4200val均已提交，旧作业/依赖不动；B两CPU等待暂Q、对应GPU val H，不影响当前B正式训练R。准备在SIGN-qwen-ablation-publication追加现有qwen128实验文档的ablations目录、根四文档生成副本与短测证据，运行源码固定d2352f0。


## 2026-10-29T17:47:32+08:00 [QWEN-ABC-ABLATIONS-PUBLISHED]

- 普通push成功：yiichu03/SIGN的phase2/qwen-beta003-geometry128发布提交ac6229895361d1551fad5710ddf1f53830d11e20，ls-remote完全一致。运行源码d2352f0保持不变；独立publication树干净，七个原/新运行工作树source guard及public模型/数据/prompt/冻结calibration全部通过，未切换或修改原训练目录、未重复提交原作业，未force push。
- 在现有docs/experiments/qwen128-reward追加ablations配置/校准引用/63项CPU与三40960步GPU短测/正式命令和真实配置/逐段概率或面积/bonus与段长分布/耗时/资源和依赖回执，并更新根四文档生成副本及README导航。新包124项SHA/大小、相对链接、WORKLOG旧前缀与根源字节一致、凭据模式检查通过，资料8.77MB，无新训练权重、场景或环境。
- 正式A1507648/B1507651/C1507650均R，首批TB有限/全新初始化已核验；六次GPU val分别A1507653/1507655、B1507662/1507664、C1507657/1507660均已提交依赖，当前无新val成绩；B两CPU waiter初查Q，其余等待R，旧1507270/1507272保留。CFP余额仍需amgr登录，未声称已取得余额数值；实际三个168h/autox申请均接受。回执logs/qwen_ablation_20261029/push_result.json，root文档在回执后仅追加/更新、不循环重发。

### 2026-10-30T02:49:56+08:00 — TENSORBOARD-REUSE-RUNNING-SERVER-20261030

用户粘贴原启动命令报Address already in use／6006 occupied并关闭SSH。本地16006无监听；远端stdct-login-01的PID1958700自02:15:26运行，完整命令与当前view_personal_tensorboard.sh的三组logdir_spec匹配，/data/logdir响应正确。无需杀现有服务或重复读大日志。

通过诊断SSH控制连接临时建立本地16007→远端6006，首页HTTP200，tags返回baseline_frozen/.=29、coverage_rollout256/.=34、coverage_settle32/.=34。首次检查脚本用不带/.的键做严格断言而失败（服务及数据响应正常）；按TensorBoard实际run后缀规范化后校验通过。已取消临时16007转发，不建立持久16006。保留现有服务、训练、脚本与环境，给用户ssh -N只转发的命令及本地16006地址；RUNBOOK补充已有服务和未启动服务的两种入口，STATUS更新。

### 2026-10-30T03:11:46+08:00 — TENSORBOARD-START-OR-REUSE-LIFECYCLE-20261030

用户执行仅转发ssh -N后出现channel open failed: connect failed: Connection refused。本地PID1984053确实监听16006；新诊断SSH在stdct-login-01，6006无监听，本账号已无TensorBoard进程；上一轮02:48核查的PID1958700现已退出，退出原因未从当前证据确定。未证实本轮为登录节点漂移，不能把该假设写成根因。原-N建议依赖已有网页持续运行，不能处理原网页退出。

修根logs/gibson_reproduction_20261026/view_personal_tensorboard.sh，保留原版为view_personal_tensorboard.before_reuse_20261030.sh，新增view_personal_tensorboard.py。沿用原三组logdir_spec、port环境变量、load_fast=false与max_reload_threads3；用原Python3.8环境监管TensorBoard。空闲端口启动；已有端口严格HTTP核对三组spec，匹配复用，不同服务不杀进程且明确报错。SIGINT／SIGTERM／SIGHUP停止会话，只清理本会话创建的子进程；新TB独立session避免终端先于监管器打断清理。

实际集成使用独立远端16016、不占用户16006或正式6006：bash -n与3.8语法通过，原环境真实启动首页HTTP200／logdir正确，第二会话复用后Ctrl+C保留原网页，owner接收SIGHUP后网页端口释放，模拟其他目录的HTTP服务被拒绝复用且保留；四项全部通过。证据tensorboard_launcher_checks_20261030.json；临时stdout /tmp/tb_owner_20261030.log、/tmp/tb_reuser_20261030.log。测试进程和端口均清理；用户当前-N未动，交由用户Ctrl+C并改用原统一ssh -t脚本命令。未改训练代码、环境或PBS作业。STATUS／RUNBOOK同步当前结论。


## 2026-10-31T00:56:14+08:00 [TRAINING-SIX-RUNS-READOUT-20261031]

- 目标：按用户要求查看当前训练指标。liuyi根执行qstat -u e1538633及CPU-only logs/training_readout_20261031/readout.py，保存固定字节事件/rollout快照、SHA、CSV、同预算曲线与readout.json；未新qsub/qalter/qdel，不修改运行仓库、环境或评估。六训练1497416/1502352/1507268/1507648/1507651/1507650均R，取样事件末时2026-10-31 00:51–00:53；其余Q/H为既有等待或评估依赖，本轮不将其计作训练、不分析新val结果。
- 各最新步数：覆盖256=115169280、覆盖32=43018240、Qwen128β.1=7084032、A=6844416、B=7290880、C=18020352。各自近1M训练SR/SPL依次86.8396/51.2376%、86.1802/48.6444%、84.6514/46.6729%、82.5211/45.3223%、83.8150/46.8524%、85.2516/49.5117%；近3h中位每2048步5.286/10.458/33.554/33.134/31.476/12.201秒。不同训练预算不直接排名；原50-update滑动统计重叠，本次追加的1M均值只作描述。
- 共同5844416–6844416步：基线/旧256/旧32/Qwenβ.1/A/B/C的SR82.4707/84.3577/82.3751/83.1522/82.5211/82.8658/80.6786%，SPL46.2664/46.4371/45.6014/46.0488/45.3223/46.0725/45.4556%。Qwenβ.1/B有小幅SR现象，SPL未超过基线，不称稳定收益；同步起伏明显，保留单种子限制。旧共同38.018–43.018M近5M，基线/256/32 SR86.2442/85.4666/84.9588、SPL51.0480/47.4920/47.6174%，32近1M反弹不能当持续胜出。
- 新A/B/C同阶段几何有效动作效率0.159412/0.160814/0.165142m²，不能与旧0.1m全动作统计或无训练面积的基线直接比较。共同阶段每rollout bonus A/B/C .1347298/.1399244/.3501336，C为A约2.60倍；冻结alpha只保证旧短测校准集总量相等，不保证后续策略/面积变化时一致，未擅改alpha或权重。
- 各自近1M的Qwenβ.1/A/B/C有效段比例92.669/92.849/93.179/92.729%；主要跳过episode_height_range_exceeds_fixed_floor，另有fog_origin_farther_than_5cm_from_navmesh；比短测约98%降低属需要跟进的观察，不称worker故障。四组截至各事件末步全部rollout顺序连续、nav_rewards/masks不变，混合奖励守恒最大差5.07e-5以内；旧coverage守恒差1.79e-8。所有29/34/34/55/67/67/57项scalar历史均有限，loss无NaN/Inf。
- CPU读取六组最近稳定编号checkpoint，SHA/extra_state.step/模型全有限，42项encoder状态均逐位等于公开权重；训练事件末步与checkpoint步数分开保存，证据checkpoint_check.json。采样不修改任何权重。完整证据logs/training_readout_20261031/snapshot_005043，脚本/采集日志/PBS状态/冻结检查在其父目录；STATUS加入最新索引、RUNBOOK追加只读操作方法，本轮不push资料。


## 2026-10-31T01:01:20+08:00 [GEOMETRY128-QWEN-LEGACY-AND-BASELINE-FINAL-CLARIFIED]

- 按用户追问核对C几何128定义、Qwen与旧两覆盖的相同步数训练比较及基线停止末点。只读src/config/geometry_c128.yaml、冻结calibration.json和上一批固定事件/CSV快照；未触碰运行代码、作业或模型，未新增评估、推送或导航训练。
- C是A128的纯几何对照：相同2.5cm/3m/90°、episode历史/有效性，128步或真实terminal切段，PPO仍256；段末alpha*new_area/256，alpha=.2927574680399425由旧1176有效段按.03*sum(L*q)/sum(area)冻结；无Qwen、无topdown渲染。A为.03*(L/256)*q。三新对照MRQ显式navigation目标；旧两覆盖还存在面积分辨率/权重/目标口径差异，不把跨系列结果当仅替换评分器的单变量实验。
- 补齐共同5844416–6844416步旧256/旧32的SR84.3577/82.3751%、SPL46.4371/45.6014%；Qwenβ.1/A/B分别83.1522/82.5211/82.8658%及46.0488/45.3223/46.0725%。该窗口β.1/B比旧32略高，三Qwen均未超过旧256的SR和SPL。进一步在相同结束步核对最近1/2/3/5M，保存comparison_followup.json：3M时β.1 SR83.0184高于旧25682.2614，但SPL45.1135低于45.3955；5M时β.1 SR79.5786/SPL43.4939低于旧25679.8807/43.6503。窗口敏感且单种子训练滑窗，不能宣称稳定全面收益。
- 基线1496716最终TB步74653696，最后可评估checkpoint74240000。停止前最终原生滑窗SR.8780822157859802/SPL.5513484477996826，即87.81/55.13%；最后1M滑窗均值87.8689/54.8217%，最后5M89.4169/55.6550%。这些是训练过程完成episode统计，不是额外完整训练集离线评估；不混用公开checkpoint val86.00/53.01%。STATUS快速索引新增基线训练SR/SPL行，当前比较补上旧两覆盖与窗口敏感性。


## 2026-10-31T01:32:12+08:00 [GITHUB-CODE-DOC-SYNC-AUDIT-20261031]

- 用户询问代码及文档是否已同步yiichu03。实际执行git ls-remote --heads git@github.com:yiichu03/SIGN.git核对七个研究分支，并逐个核对五训练树HEAD/status/有效push URL及运行HEAD到已发布tip的文件差异；五组均无src/config/tests/scripts等非资料差异，无未提交训练代码，未跟踪data仅资源软链接。远端基线dac8609、覆盖256 b39e362、覆盖32 a7cc9e0、Qwenβ.1 33e30d2、ABC ac62298，另离线topdown b1c24dc、历史453179c；因此已批准训练实现均已上传。
- 最新ABC发布树的AGENTS字节一致，STATUS/RUNBOOK/WORKLOG较根源滞后，发布STATUS日期2026-10-29、WORKLOG仍为当前源严格前缀。10月31日训练读数/曲线/比较窗口与新增基线训练SR/SPL索引、只读汇总脚本和最近TensorBoard运维文档尚未发布。当前请求为状态核对，未擅自push或将资料pull入运行目录；未改动作业/训练源码。保存审计logs/github_sync_audit_20261031/013212/audit.json，更新STATUS同步状态。


## 2026-10-31T01:49:55+08:00 [TRAINING-READOUT-PUBLICATION-PREPARED-20261031]

- 用户明确要求将最新资料补充同步yiichu03。选用已存在的独立SIGN-qwen-ablation-publication、基点ac6229895361d1551fad5710ddf1f53830d11e20，远端同名分支实际ls-remote一致、工作树干净、push URL为git@github.com:yiichu03/SIGN.git；准备普通push phase2/qwen-beta003-geometry128，不向upstream或main发布。六组比较集中放在原qwen128-reward/ablations/training_20261031，其他运行分支保持原提交，避免为资料切换训练目录。
- 本批次不重跑训练或评估：复用00:51–00:53固定快照readout.json/1–5M窗口JSON/曲线/七组所选CSV/四组rollout、checkpoint冻结审计和PBS状态，CSV/rollout确定性gzip；附只读汇总脚本和10月30日TensorBoard启动/复用/信号清理副本及当时检查。完整TB、权重、场景、环境不重复上传。新构建器logs/training_readout_20261031/publish_readout.py，旧发布构建器与旧证据不改。
- 原七工作树及模型/数据/prompt source_manifest guard已通过，运行源码/冻结校准均未变。根STATUS补资料入口、将旧启动状态明确标为10月29日记录，RUNBOOK补只读构建/核验方法；四文档从根源生成，WORKLOG仅追加。当前为准备记录，构建/解压SHA/指标复算/相对链接及普通push尚待实际完成，不把准备写成已发布。


## 2026-10-31T01:52:24+08:00 [TRAINING-READOUT-PUBLICATION-CHECKED-20261031]

- 独立publication增量构建与仓库根实际离线命令均通过：原manifest151项/40.07MB，24项原始输入的SHA与确定性gzip解压完全一致，56项1/2/3/5M区间SR/SPL从已发布CSV重新计算一致；四组rollout编号连续、nav_rewards/masks原样及混合bonus守恒核验通过。README/STATUS/RUNBOOK/AGENTS相对链接有效，原已发布WORKLOG前缀保留；新Python脚本AST与shell bash -n通过，未重跑训练单测或GPU实验。
- 包含新训练报告、七组CSV、四组rollout、基线停止记录、checkpoint审计、汇总/离线核验脚本、TensorBoard运维副本及检查。新目录无权重/场景/环境/相机数据，单文件小于20MiB，凭据模式扫描通过；运行实现与d2352f0无差异。六训练最新PBS核查仍R，旧依赖保留。本条与根文档重新生成进入本次资料快照，最终普通push和远端SHA复核仍待执行。


## 2026-10-31T01:54:29+08:00 [TRAINING-READOUT-PUBLICATION-PBS-WHITESPACE-FIX]

- 最终git diff --cached --check发现新归档的PBS jobs.txt原始输出有10行尾随空格，失败输出保留logs/training_readout_20261031/publication_whitespace_check_before.log。这是原始PBS文本格式，未修改或清理服务器证据。改将该文件确定性gzip归档为evidence/jobs.txt.gz，解压SHA/原字节数保持不变；生成器、输入清单与STATUS相对链接同步更新，原文本仅从本次未提交的生成目录移除。训练代码、作业、原证据不变。更新资料manifest后重新执行离线与暂存检查，再做普通push。
