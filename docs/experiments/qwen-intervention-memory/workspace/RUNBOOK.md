# liuyi 运行与复现手册

本文件维护目前适用的操作方法；当前任务和阻塞见 [STATUS.md](STATUS.md)，执行结果及 debug 过程追加到 [WORKLOG.md](WORKLOG.md)。下面的命令是操作模板，列出不表示本次执行。

<a id="gibson-checkpoints"></a>
## Gibson对照基线与公开checkpoint：证据索引

常用停止步数及公开验证分数统一查 [STATUS顶部快速索引](STATUS.md#gibson-reference)。当前“对照基线”是冻结视觉实验1496716；更早的完全从零任务1495073单独归档。

- **停止基线的最后权重**：preservation.json（服务器：`/scratch/e1538633/liuyi/logs/qwen_token_probabilities_20261028/baseline_stop_1496716/preservation.json`）记录实际extra_state.step、源文件、保留副本与SHA；用于新评估时读取这里的checkpoint步数，不能拿TensorBoard末步代替。已保留的不可变副本为 last_saved_checkpoint.pth（服务器：`/scratch/e1538633/liuyi/logs/qwen_token_probabilities_20261028/baseline_stop_1496716/last_saved_checkpoint.pth`），原训练的checkpoint／TB／控制台日志仍在SIGN/results/gibson_frozen_encoder_20261026/train_personal_8env。
- **最终训练记录**：只读事件审计（服务器：`/scratch/e1538633/liuyi/logs/gibson_train_threeway_20261028/snapshot_132900/comparison.json`）的runs.baseline包含最终step与时间，events包含原文件SHA。控制台末条在原日志（服务器：`/scratch/e1538633/liuyi/SIGN/results/gibson_frozen_encoder_20261026/train_personal_8env/train_run0_/log.txt`）。停止操作原文见WORKLOG的BASELINE-1496716-STOPPED-TO-FREE-QWEN-GPU。
- **公开完整模型评估**：pretrained_full_result.json（服务器：`/scratch/e1538633/liuyi/logs/gibson_reproduction_20261026/pretrained_full_result.json`）保存Gibson完整val任务数、SR/SPL/View Match、源commit、checkpoint与实际耗时，作业1494521。加载SIGN/ckpt/nav_model.pth完整导航策略，沿用原safety模型，6环境／500步；原记录PYTHONHASHSEED未显式固定，后续hash0对照需保留这一协议差异。
- **本次核验记录**：baseline_reference_index_20261029.json（服务器：`/scratch/e1538633/liuyi/logs/gibson_reproduction_20261026/baseline_reference_index_20261029.json`）汇总三种步数、checkpoint SHA和公开原结果；此次只整理记录，没有提交新评估。

## 工作目录与环境

统一启动入口：

```bash
codex -C /scratch/e1538633/liuyi
```

当前 SIGN 检出 `phase2/exploration-reward-try`，与创建时 origin/main 相同；SIGN-SRU 目录检出作者基线 main，研究工作树检出 `phase1/imagenav-qwen-diagnostics`。两个仓库均已将第一阶段工作推送到同名 phase1，具体提交见 STATUS。

**以下采集、Qwen 和历史发布命令来自 SIGN phase1。当前 phase2 不含这些新增脚本，运行前须核对代码分支与工作目录。** 只读查看归档源码可从根目录执行：

```bash
git -C SIGN show phase1/imagenav-qwen-diagnostics:src/trajectory_diagnostic.py
git -C SIGN show phase1/imagenav-qwen-diagnostics:scripts/qwen_pairwise_diagnostic.py
```

需要实际运行第一阶段工具时，先保存当前阶段二工作再选择 phase1，或为 phase1 新建独立工作树并核对脚本中的绝对 SIGN 路径；不得把阶段一快照直接覆盖阶段二代码。

| 用途 | 路径／本地已记录版本 |
|---|---|
| SIGN Python | `/scratch/e1538633/liuyi/envs/sign/bin/python`；Python 3.8.20、torch 1.11.0+cu113、Habitat-Sim 0.2.2 |
| Qwen Python | `/scratch/e1538633/liuyi/envs/qwen35/bin/python`；Python 3.11.16、torch 2.6.0+cu124、transformers 5.17.0 |
| Qwen 模型 | `/scratch/e1538633/liuyi/models/Qwen3.5-9B` |
| 仿真依赖源码 | `/scratch/e1538633/liuyi/habitat-lab`，提交 `1f7cfbdd` |
| SIGN 权重 | `SIGN/ckpt/nav_model.pth`、`SIGN/ckpt/safety_model.pth` |

依赖要求见 SIGN 的 requirements.txt；constraints-hm3d.txt 保存在 phase1（当前 phase2 未包含）。不要将两套 Python 环境混用。SIGN-SRU 的 DeFM、DINO 和数据路径需按所选配置另查，不能据此假定已就绪。

SIGN 内相对路径命令均从 `/scratch/e1538633/liuyi/SIGN` 运行；SIGN-SRU 命令从其自身仓库运行。新窗口统一入口不改变这些要求。

## 集群约定

- GPU 推理和采集使用 PBS 计算节点；长任务按用户要求使用 `auto`／`autox`。现有 A40 作业常用 `autox`、项目 `CFP04-SF-109`。 2026-10-29用户明确希望可运行却在资源排队的GPU任务优先使用autox→batch_gpux；个人项目仅auto限制和既定预算继续有效，已运行作业不重提。
- 如项目被拒，先查实际错误与预算；既有授权备选为 `CFP02-CF-006`、`personal-e1538633`。
- 2026-10-26 实测个人项目拒绝 autox（Express queue not allowed），须使用 auto。用户已授权共享 CFP 与个人预算；个人年度默认 1000 GPUhr／10000 CPUhr 不等于当前余额。hpc project 查询需要 amgr 登录，未登录时不能声称已核对余额。
- 集群手册：`~/liuyi/Vanda Cluster User Guide 05Jun25.pdf`。不要在日志记录访问凭据。

存储检查优先用 `hpc s`，核对个人 `/scratch/e1538633` 的用量与配额；`df -h /scratch` 只反映共享文件系统余量。Vanda的hpc命令读取管理员维护的 `/home/svu/vanda/quotas/e1538633.scratch.txt` 快照，应同时看修改时间；系统通用 `quota -s -f /scratch` 在当前NFS上报Cannot connect to RPC quota service，不能据此认定无配额。大型目录du需设置超时，避免为查容量长时间扫描。

## Habitat-GS ImageNav 实验入口

这是用户新授权的独立仿真方向；`SIGN-habitat-gs/` 检出 `experiment/habitat-gs-imagenav`，来自 SIGN origin/main @ dad87fe。已有 Gibson 作业继续使用原 `SIGN/` 与 `envs/sign-baseline`，不要切换那个工作树。GS 适配器为 `src/dataset.py` 的 `HabitatGSImageNav-v1`，将场景配置路径补入内存 episode，供原 DroneEnv 初始化／reset 使用；不改原始任务文件、策略、奖励或连续控制。

固定来源：[官方代码](https://github.com/zju3dv/habitat-gs) @ cb01b2fdf850ce3cab28ad00461a68ac7719f23f；[论文](https://arxiv.org/abs/2604.12626)；[官方数据](https://huggingface.co/datasets/RukawaY/gs_scenes) @ ea6453855938dd3d4395c4c449fedefb7e6603b7。第三方源码位于 `habitat-gs/`，默认 push 关闭。只需静态场景、navmesh 和 ImageNav 任务；avatar／SMPL／VLN 均不属于当前验证范围。

新环境使用 Python3.10，以兼容旧 Habitat-Lab 的 Hydra1.2，同时满足 Habitat-GS 的 Python 要求。依赖选择为 torch2.5.1+cu121、NumPy2.0.2，明确区别于 Gibson 的 torch2.0.1／NumPy1 环境。安装与 GPU 通过状态以 STATUS 为准；环境目录存在不代表已验证。

资源只保留一份：`SIGN/data/scene_datasets/gs_scenes/`；新工作树的 data 是 `../SIGN/data` 软链接。下面从 `SIGN-habitat-gs/` 执行的下载器会复核既有文件，缺失时按固定 revision 获取，校验 LFS SHA256 或 Git blob SHA1；不创建 HF 全量缓存或覆盖哈希不一致的文件：

```bash
python3 scripts/habitat_gs/prepare_data.py \
  --manifest ../manifests/habitat_gs_20261026.json
```

默认只下载 scene56 的 GS／navmesh、100条官方 val episode、val 空入口及两份官方配置，约111.4MB；没有从任务再生成新数据。数据文件中的 `scene_id` 为 `gs_scenes/val/scene56/scene56.gs.ply`，由原 loader 与 `scenes_dir=data/scene_datasets` 拼接。

完整静态ImageNav下载（从工作区根目录提交）：

```bash
qsub -o /scratch/e1538633/liuyi/logs/habitat_gs_20261028/download.pbs.log \
  SIGN-habitat-gs/scripts/habitat_gs/download.pbs
```

`download.pbs`使用auto／4CPU／8GB／4h，固定数据revision；`prepare_data.py --all-scenes`选train+val的393个必需文件（26.70GB），4并发，验证已有文件后复用，缺失文件使用原位.part续传并在哈希通过后改名，无HF第二缓存。最终完整清单为 `manifests/habitat_gs_imagenav_20261028.json`；旧scene56清单保留作历史证据。提交时使用新的日志名并先查已有作业，不能重复运行下载器。完成后可从SIGN-habitat-gs运行下列命令；plan-only不写数据／清单，verify-only不下载：

```bash
python3 scripts/habitat_gs/prepare_data.py --all-scenes --plan-only \
  --manifest ../manifests/habitat_gs_imagenav_20261028.json
python3 scripts/habitat_gs/prepare_data.py --all-scenes --verify-only \
  --manifest ../manifests/habitat_gs_imagenav_20261028.json
```

最终清单仅在全部官方size与LFS SHA256／Git blob SHA1、原始任务场景引用／ID唯一性／GS及navmesh存在性和train110000／val1900条数通过后原子写入；没有清单不代表未下载，重跑时重新验证已完成文件并复用。哈希不符文件保留现场并失败退出。

2026-10-28全量下载已完成：1502380 Exit0／19分48秒，393文件全过哈希，实际任务train110000／val1900，129个navmesh配置引用可解析，无残余part或额外文件；无需重新提交上述下载作业。数据逻辑大小26.70GB，当前NFS上的du块统计为21G。hpc s读取的配额快照可能晚于命令执行时间更新，报告下载后容量时须看快照修改时间。

安装模板（工作目录 liuyi；这些命令不代表每次都需重装）：

```bash
module load Miniconda3/24.7.1-0
conda create -y -p /scratch/e1538633/liuyi/envs/sign-habitat-gs python=3.10 pip
export PYTHONNOUSERSITE=1
envs/sign-habitat-gs/bin/python -m pip install --no-cache-dir \
  torch==2.5.1 torchvision==0.20.1 --index-url https://download.pytorch.org/whl/cu121
envs/sign-habitat-gs/bin/python -m pip install --no-cache-dir \
  -r SIGN-habitat-gs/scripts/habitat_gs/requirements.txt
envs/sign-habitat-gs/bin/python -m pip install --no-cache-dir --no-build-isolation \
  smplx==0.1.28 chumpy==0.70
```

沿用原 `habitat-lab @1f7cfbdd` 的只读源码，通过明确的 PYTHONPATH 导入，不对该依赖做 editable 安装／源码升级。`scripts/habitat_gs/build.pbs` 在auto CPU队列编译并执行新版Sim的CPU探针，随后 `smoke.pbs` 在autox A40做真实渲染／连续动作／策略前向和原run_sim.py的10条评估。后者默认复用已安装环境；仅显式 `GS_REBUILD=1` 时在GPU节点重编译。两个入口均禁用user site，显式加载git/2.40.0。

新Sim相机配置要求Magnum.Vector3：实验分支在create_sim_config中显式转换position／orientation，CPU探针覆盖真实传感器配置转换路径；不使用运行时monkeypatch。Python3.10环境去掉policy.py中未使用的nis导入。

原生构建使用 GCC11.3／CUDA12.2，全局 CUDA architecture=86（A40），上游 GS rasterizer 仍固定生成70/75/80/86/90 fatbin；EGL=ON、GUI=OFF、Bullet=OFF。GLM头文件复用 `/app1/ebapps/arches/flat-avx2/software/GLM/0.9.9.8-GCCcore-11.3.0/include`，通过CPATH提供；不另下载。OpenEXR的FetchContent自动取Imath v3.1.9（实测SHA d690a3fcff4e877ead5ae56c7e964595ade8a35e），留在habitat-gs/build下供增量构建复用。缺Git、缺GLM的原始错误及修正见WORKLOG。

CPU构建输出在根 `logs/habitat_gs_20261026/build_<PBS_ID>/`，GPU探针、包快照和评估结果在 `SIGN-habitat-gs/results/habitat_gs_20261026/job_<PBS_ID>/`。PBS输出统一放根 `logs/habitat_gs_20261026/`。提交前检查已有任务，选择新的日志文件名，不能重复提交或覆盖旧错误；以下仅为模板，当前任务ID见STATUS。

```bash
qsub -o /scratch/e1538633/liuyi/logs/habitat_gs_20261026/build_next.pbs.log \
  SIGN-habitat-gs/scripts/habitat_gs/build.pbs
# 确认构建Exit_status=0且cpu_probe.json通过后再提交GPU：
qsub -o /scratch/e1538633/liuyi/logs/habitat_gs_20261026/smoke_next.pbs.log \
  SIGN-habitat-gs/scripts/habitat_gs/smoke.pbs
```

协议边界：保留 SIGN 的128×128 RGB／目标图、连续线／角速度、500步上限、1米 success、view_match 与原奖励；固定 `PYTHONHASHSEED=0`，因为原 ImageGoalSensorV2 用 episode_id 的 Python hash 选择目标朝向。官方 GS 示例为256×256、离散动作、1000步。因此这是已有 Gibson checkpoint 在 GS scene56 上的迁移诊断，不能直接与官方 DDPPO 指标或完整19场景基准混称。probe 会核对目标渲染保留智能体姿态，并保存一张当前视图／目标图对照；不默认录制大量 RGB。

完整公开权重评估入口（19个val场景／1900条，沿用原版eval的6并行）：

```bash
qsub -v GS_SOURCE_COMMIT=$(git -C SIGN-habitat-gs rev-parse HEAD) \
  -o /scratch/e1538633/liuyi/logs/habitat_gs_eval_20261028/full_val.pbs.log \
  SIGN-habitat-gs/scripts/habitat_gs/evaluate.pbs
```

模板提交前核对现有作业并更换日志名，实际ID见STATUS。evaluate.pbs使用autox／CFP04-SF-109／A40／6h；只执行evaluate.py外部入口，原run_sim.py和trainer不改。输入守卫检查提交源码、公开导航／安全权重SHA、全部1900条任务唯一性、19个navmesh可达及测地距离；可先在已配置GS环境中执行 `python scripts/habitat_gs/evaluate.py --preflight-only`，该模式不初始化GPU渲染器、不写运行目录。

完整配置仍为 `ppo_imagenav_gibson,policy,reward,sensors,eval,ppo_imagenav_habitat_gs`，CLI显式覆盖content_scenes=['*']、num_environments=6、test_episode_count=1900、split=val、eval_ckpt_path_dir=ckpt/nav_model.pth。保留公开SafeNavNetPolicy／safety_model.pth、seed100／hash0、500步、连续动作、128输入、1m与原成功／SPL定义；未使用冻结视觉／coverage实验的权重或源码。此为完整GS val上的SIGN协议迁移评估，不与官方离散动作DDPPO协议混称。

输出集中 `SIGN-habitat-gs/results/habitat_gs_full_val_20261028/job_<PBS_ID>/`：inputs.json保存源码／权重哈希和任务集合摘要，evaluation.log保存原评估stdout，eval/保留原合并配置与TensorBoard；全部1900/1900完成且汇总指标有限后才生成result.json。仍不保存逐条轨迹或视频。

完整评估1502487的已知异常：原trainer达到1900/1900并写出SR／SPL后，距离汇总Inf、奖励NaN导致外部evaluate.py的全指标有限性断言失败（PBS Exit1），没有生成result.json。此时先保留原始TensorBoard／控制台／配置，区分任务完成与质量门未通过；审计输出result_audit.json将非有限值明确编码成字符串，不能当0或删除异常任务后称完整结果。原trainer没有逐条指标，不能从汇总反推出异常数量／场景；不要仅为得到Exit0放宽守卫或盲目重跑。已核对原生PathFinder.cpp：findPathSetup先把geodesicDistance置Inf；当前位置／目标投影失败、导航岛不连通或路径搜索失败时可保留Inf。SIGN geodesic_distance未检查find_path布尔返回值，直接把距离交给DistanceToView；NavRLEnvX使用previous_measure-current_measure，故Inf-Inf或累计正负Inf可产生NaN。这是代码可确认的传播条件，不证明本轮具体触发点；不能直接归因于GS渲染器。

成功／失败视频：1503625已完成3成功＋3失败，目录 `SIGN-habitat-gs/results/habitat_gs_videos_20261028/`（6 MP4＋manifest，约12.30MB）。外部录制脚本／PBS／配置／筛选过程／验证位于 `logs/habitat_gs_videos_20261028/`，不改src；单环境重跑相同公开权重、确定性动作、500步／128输入／seed100/hash0。视频为768×544双栏当前RGB＋目标图，10fps（每秒10个动作）、终帧停2秒；画面仅放大原128输入。原1900条没有录像，不能称这些为其原始录像，也不能从目的性挑选样例估计SR。成功／失败以原Success分类。

用户在本地执行（远端文件已生成，无需先启动服务器训练）：

```bash
mkdir -p /home/liuyi/projects/ceg5002/habitat_gs_videos_20261028
rsync -avP \
  e1538633@vanda.nus.edu.sg:/scratch/e1538633/liuyi/SIGN-habitat-gs/results/habitat_gs_videos_20261028/ \
  /home/liuyi/projects/ceg5002/habitat_gs_videos_20261028/
```

首次成功证据：作业1494770，分支24b4c02，结果目录 `SIGN-habitat-gs/results/habitat_gs_20261026/job_1494770/`。probe.json／probe.png验证真实GS渲染和动作；eval/eval_run0_/config_of_eval.yaml是实际合并配置，log.txt与eval/tb保存原trainer汇总，result.json从TensorBoard提取精度完整的指标。原trainer不保存逐条指标或轨迹，本轮未增加采集；只能报告10条汇总，不能恢复失败原因。成功率10%、SPL5.3543%仅说明该权重在这个小样本的表现。

早期仅下载scene56时，原官方val.scene_dataset_config.json会打印其他18个场景navmesh不存在以及无语义描述文件的消息；本次不使用这些场景或语义传感器，scene56导航／RGB／depth实际运行通过。保留原配置和日志，不为消除消息下载其余资产。Gym对NumPy2的通用提示也保留；本次CPU、GPU探针和10条实际评估均通过，但不代表覆盖Gym全部功能。

## 当前 Gibson 原版复现

SIGN 当前 phase2 @ dad87fe 保持作者源码，不迁入 phase1 兼容补丁、不 monkeypatch。先现有 checkpoint 评估，再独立从零训练；数据与结果均位于 SIGN/data、SIGN/results，准备脚本在根 logs/gibson_reproduction_20261026/。

场景下载已发现可直接访问的 Meta 文件服务器：

- [gibson_habitat.zip](https://dl.fbaipublicfiles.com/habitat/data/scene_datasets/gibson_habitat.zip)：1468698464 字节，88 个 glb 和 88 个 navmesh，包含当前 SIGN 所需全部 72 train + 14 val 场景。官方 [MD5 清单](https://github.com/StanfordVL/GibsonEnv/wiki/Checksum-Values-for-Data.md) 为 `35f274a781eba9ed1b77feba50d040da`。
- [gibson_habitat_trainval.zip](https://dl.fbaipublicfiles.com/habitat/data/scene_datasets/gibson_habitat_trainval.zip)：10833075327 字节，492 对场景文件。当前 86 场景与小包的文件大小和 CRC 一致，无需为本次复现下载全包。

直链来源包括 [社区下载脚本](https://github.com/WGW101/habitat_sim2real/blob/62fcdd3ed5a5030b099bcd1ed847989344441805/script/download_gibson.sh) 和 [AudibleLight 下载脚本](https://github.com/AudibleLight/AudibleLight/blob/main/scripts/download_data/download_gibson.py)。后者对小包场景数的注释不准确，以实测压缩包目录为准；不要直接运行其清理选项，会删除本任务需要的 navmesh。公开直链可访问不代表免除数据使用协议，Gibson 官方仍将下载入口指向许可表单。

Gibson包含单层与多层场景，不能把scene等同一层。2026-10-28将当前14个val场景与[官方metadata](https://raw.githubusercontent.com/StanfordVL/GibsonEnv/master/gibson/data/data.json)对照：9个floor=1，5个floor>1（Edgemere2、Mosquito3、Sands3、Scioto5、Sisters2）。官方floor按相机高度聚类定义，可包含地下室／阁楼等扫描高度层，不能直接当严格建筑楼层图。当前4200条val任务有76条起终点Y差>1.5m；此高度阈值只是跨高度筛查，不是已人工确认76条跨建筑楼层。单个任务是否跨层与场景楼层总数须分开检查，topdown也需考虑高度切片。 全量任务审计 `logs/gibson_floor_audit_20261028/result.json`／count_tasks.py：train72场景（39单层／33多层），多层场景任务297000/645000（46.0465%），|ΔY|>1.5m候选16584（2.5712%）；val14场景（9／5），多层场景任务1500/4200（35.7143%），候选76（1.8095%）。所有场景metadata齐全、端点Y有限，原任务均无明确floor字段；两组跨高度候选全部位于多层场景。不同阈值计数保存在同一JSON，不能把这一筛查当精确楼层标签或整条路径是否跨层。

数据必须同时准备两层：`data/datasets/imagenav/gibson/v1/{train,val}/` 是 episode 起点／目标等任务信息；`data/scene_datasets/gibson/{Scene}.glb` 与同名 `.navmesh` 是实际场景。已有 HM3D v0.2 的 100 个 val 场景不能替代 Gibson。任务清单 manifests/gibson_reproduction_20261026.json 记录 train 645000 条、val 4200 条及哈希；公开来源 HEAD 与远程 ZIP 目录核对保存在 logs/gibson_reproduction_20261026/public_*json。

原 envs/sign 的 torch 1.11 不支持原策略的 `Normal.mode`，确定性评估会报 AttributeError。为保持源码原样，另建 envs/sign-baseline，使用 torch 2.0.1+cu117／torchvision 0.15.2+cu117 与 Habitat-Sim 0.2.2；环境完成与验证状态见 STATUS，不能仅凭目录存在认定可用。

从根目录进行输入检查（提交 GPU 任务前执行；会在缺场景时退出）：

```bash
envs/sign-baseline/bin/python logs/gibson_reproduction_20261026/check_inputs.py --split val
envs/sign-baseline/bin/python logs/gibson_reproduction_20261026/check_inputs.py --split train
```

PBS 文件分别为 pretrained_eval_smoke、pretrained_eval_full、scratch_train_smoke、scratch_train_full、trained_eval_full。共享 CFP 使用 autox，个人项目仅可使用 auto；当前短训练已改用 CFP／autox；均为1×A40，调度器将8 CPU／64GB申请规范为36 CPU／240GB主存。当前五项已提交，实际 job ID／状态见 STATUS 与 submitted_experiments.json，检查已有任务后再决定是否重提。

执行关系：现有 checkpoint smoke 成功后跑完整评估；CFP短训练独立执行40960步（20次4×512 rollout），验证更新、checkpoint和曲线。正式300M步训练依赖短训练与完整评估均成功，训练后模型评估再依赖正式训练成功。scratch_smoke 与 scratch_full 输出目录独立，完整训练从零初始化，不承接 smoke checkpoint。所有 launcher 均调用原 `run_sim.py`，不使用 `--overwrite`。

正式训练开始前调用外部 training_preflight.py：检查短训练实际事件／权重，取最后10次更新的中位步速，计算300M步时长并加15%裕度与15分钟启动时间。若超过168h，保存 training_preflight_result.json 后退出，等待据实调整运行方案；不会自动缩短目标或改算法。此估计是短时投影，MRQ在50M停用可能加速、场景混合也会改变速度。

2026-10-26训练并发短测已通过：同一GN-A40-045／A40按4×512→8×256→4×512运行，各40960步、20次更新，最后10次更新中位吞吐分别298.91、335.48、295.03步/秒，8环境加速12.2%–13.7%。后续预算内训练可通过CLI `habitat_baselines.num_environments 8 habitat_baselines.rl.ppo.num_steps 256` 采用论文并行度；每批仍2048步，但循环长度和场景分配变化，不声称学习过程完全相同。使用独立输出目录，保留TensorBoard，num_checkpoints=-1／checkpoint_interval=10使短测40960末步确实落盘。新旧节点速度差距另含节点／运行条件，不能归于8环境；当前300M早期速度线性外推248.4h仍不保证168h内完成。原始命令、GPU采样、曲线和对比图见 train_parallel_benchmark/。

README 命令的完整训练配置：4 环境×512 rollout，300M 环境步；评估 6 环境、每 episode 最多 500 步、全部 4200 条。论文写 8×256，首次先保留仓库命令的合并结果，明确区分配置差异。保存的 train_merged.yaml／eval_merged.yaml 是配置探针；实际运行另保存 config_of_train.yaml／config_of_eval.yaml。

已批准并实施的冻结视觉实验：SIGN当前phase2/frozen-visual-encoder @ dac8609，仅trainer.py增加14行。新个人作业1496716使用logs/gibson_frozen_encoder_20261026/train_personal.pbs，auto／personal-e1538633、8×256、A40、168h、原300M上限。先执行4096步GPU smoke并检查42个encoder状态项与公开权重逐位一致，再从独立fresh目录train_personal_8env开始长训练；不承接旧任务或smoke的后端权重。source_manifest.json校验本实验44个跟踪文件，check_inputs不使用旧原版源码哈希表。CPU验证已通过实际初始化与原生DA_PPO更新；1496716的2次GPU更新已通过，42个encoder状态项逐位不变，正式长训练已运行。结果以gpu_smoke_validation.json与submission.json为准。

原任务1495073按批准停止，实际TensorBoard5785600步，唯一保留ckpts/final.pth为5632000步；中间12份权重已删除，归档JSON为logs/gibson_reproduction_20261026/stopped_scratch_run/result.json，原事件／配置／控制台日志及导出曲线保留。此前parameter_update_audit引用的旧中间checkpoint已按授权精简，审计JSON仍可读。查看网页仍使用同一个view_personal_tensorboard.sh SSH命令，其当前脚本已扩展为三组正式训练的同页对照；已有网页进程需用户重启连接才能读取新配置。

最新用户选择为仅加载并冻结actor_critic.net.visual_encoder（包含其归一化buffer），不加载或冻结visual_fc，其他模块保持原初始化。当前待审encoder_only_proposed.patch仅涉及SIGN/src/trainer.py两处，复用已存在的ddppo.pretrained_encoder／pretrained_weights／train_encoder配置，默认False／原路径／True时不改变原行为。新实验拟以CLI开启预训练encoder、指定ckpt/nav_model.pth、关闭train_encoder；冻结在优化器构造前完成，原PPO自动过滤requires_grad=False参数，并在每次agent.train后将encoder恢复eval。visual_fc仍训练，MRQ仍可更新它；上一轮“完整视觉固定后MRQ仅训自身头”的推断不适用于本轮只冻CNN的方案。用户明确要求审核后才实施／停旧训练／清理，随后用户已明确批准，patch已按原样实施并本地提交dac8609，新任务1496716已通过GPU校验运行；原待审文件保留作为决策证据。

预训练冻结视觉方案（仅审查，尚未接入原trainer）：公开ckpt/nav_model.pth可按actor_critic.net.visual_encoder.与actor_critic.net.visual_fc.前缀剥离后严格加载到对应子模块，42＋2项完全匹配。当前两张RGB先按通道拼接为6通道，只有一个EarlyFuseCNNEncoder，goal_visual_encoder=None。可路由Fast系列为fast_resnet7/9/9_fixup/18/18_fixup/50；Habitat系列为resnet18/resnet50/se_resnet50。更多SE／ResNeXt虽有函数定义，并非当前名称路由均可达。SimpleCNN分支调用参数与当前依赖签名不符；clip／clip_feat只有遗留forward分支、没有构造路径，不当作可直接启用编码器。

自定义SIGN trainer直接继承BaseRLTrainer，未调用Habitat通用PPOTrainer加载／冻结逻辑，单设ddppo.pretrained_encoder=True或train_encoder=False不会生效。冻结视觉须明确是否包含visual_fc，并固定RunningMeanAndVar的_mean/_var/_count；requires_grad=False仅固定参数，每次agent.train()后还要维持冻结模块eval。CPU审查中直接执行归一化1024张小合成输入，var／count在仅冻结梯度时仍变化；预训练count约2.878e9，小批量2的变化可能因float32精度被掩盖。完整冻结视觉后MRQ无法再优化CNN／投影，只训练自身头，其开关需要另作明确实验决定。完整冻结与后端更新CPU验证见frozen_encoder_review/cpu_review.json；不把它当完整PPO或收敛验证。

原版SIGN当前使用可训练fast_resnet9视觉编码器，未冻结、未加载导航预训练权重；PPO／RandomShift及前50M的MRQ辅助训练会更新视觉表征，GRU、动作头、普通价值头同时训练。MRQ目标网络通过EMA更新，安全Qc使用独立优化器；cost_critic虽被构造并输出数值，当前DA_PPO未将cost-value loss加入total_loss，不能笼统声称所有已定义参数都更新。个人训练512000→4096000步checkpoint审计验证视觉编码器39/39组weight／bias改变、cost_critic不变，证据parameter_update_audit.json。

基础 pipeline：episode 提供起点和目标视角，Habitat-Sim 渲染当前 RGB 与目标图，EarlyFuseCNN／fast_resnet9 编码，再结合上一步动作送入两层 GRU；策略输出连续角速度与线速度，训练采样动作、评估选分布 mode。环境返回距离与朝向塑形奖励，收集 rollout 后 DA_PPO 更新策略与价值网络，并更新辅助表征／安全 Qc。主奖励为 `-0.01 + previous_distance_to_view - current_distance_to_view + 2.5 * view_match`，最后一项在成功触发时加入；不能把已定义但未选中的 ZERReward 当作本次实际奖励。

个人正式长训练使用 `logs/gibson_reproduction_20261026/scratch_train_personal_8env.pbs`，明确指定personal-e1538633／auto、168小时、1×A40、8×256、原300M总步数上限；不再调用旧完整耗时拦截。每250次更新保存checkpoint（512000环境步），每次更新写TensorBoard；输出 `SIGN/results/gibson_reproduction_20261026/scratch_personal_8env`。该作业是从零新训练，不加载测速checkpoint；超过PBS时限会终止，latest.pth仍不是优化器级可续训状态。当前提交状态以personal_training_submission.json和STATUS为准，不重复qsub。

仅在已确认TensorBoard仍运行且登录节点匹配时，可用下方ssh -N复用现有服务。-N不会启动网页；原网页退出后会出现channel open failed: connect failed: Connection refused，此时应Ctrl+C退出-N并使用后面的统一启动／复用命令。旧脚本重复启动会报Address already in use；2026-10-30已修为自动复用相同服务。2026-10-30已核验stdct-login-01:6006的三组服务PID1958700正常；用户本地执行：

```bash
ssh -N -o ExitOnForwardFailure=yes -o ServerAliveInterval=30 -o ServerAliveCountMax=3 \
  -L 127.0.0.1:16006:127.0.0.1:6006 e1538633@vanda.nus.edu.sg
```

保持终端连接，浏览器用http://127.0.0.1:16006/。-N不会启动远端新进程，也不打印TensorBoard启动信息；Ctrl+C只关闭这条转发，保留已有网页服务。该方式要求SSH连接落在网页服务所在登录节点；节点不同时先核对hostname，不能因另一节点6006无响应而误杀现有服务。

日常使用以下统一命令：脚本在同一SSH登录节点自动启动或复用相同三组日志的TensorBoard。空闲端口自动启动；已有服务时严格核对/data/logdir，一致则复用并保持SSH连接，其他服务则报明确错误且不终止占用者。新启动服务由view_personal_tensorboard.py监管，SSH的SIGHUP／Ctrl+C会清理本会话启动的网页；复用服务退出会话时保留。

```bash
ssh -t -o ExitOnForwardFailure=yes -o ServerAliveInterval=30 -o ServerAliveCountMax=3 -L 127.0.0.1:16006:127.0.0.1:6006 \
  e1538633@vanda.nus.edu.sg \
  'bash /scratch/e1538633/liuyi/logs/gibson_reproduction_20261026/view_personal_tensorboard.sh'
```

保持终端连接，在本地浏览器打开 http://127.0.0.1:16006 。训练排队时暂无曲线，开始更新后显示reward、metrics/success、metrics/spl、learner/*、perf/fps。Ctrl+C结束网页和SSH转发，不停止PBS训练。view_personal_tensorboard.sh现通过--logdir_spec同时加载三个独立正式训练tb目录：baseline_frozen（原冻结基线）、coverage_rollout256（原片段末结算覆盖奖励）、coverage_settle32（32步结算覆盖奖励）；日志原地保存。默认监听远端127.0.0.1:6006，SIGN_TENSORBOARD_PORT可覆盖端口。脚本改动后须在本地旧SSH终端Ctrl+C，再执行上方原命令；已有TensorBoard进程不会自动切换配置。浏览器刷新后在Runs勾选三组、横轴选择Step，查看metrics/success、metrics/spl和reward；两种coverage均weight0.1，reward仍只含导航奖励。首次载入累计日志可能需要数分钟；脚本启用max_reload_threads=3让三组并行读取，TensorBoard2.8的显示名称可能带/.后缀。2026-10-26晚重新启动转发并实测29条scalar可读，随后按用户要求关闭网页进程和转发，由用户自行运行；当前连接状态见STATUS。命令开头是ssh，不是sh；应在运行浏览器的本地电脑执行。Python3.8弃用警告及TensorFlow installation not found在本次环境不阻止scalar展示；等待出现TensorBoard 2.8.0 at http://127.0.0.1:6006/后再访问。若本地16006已被当前连接占用，直接访问已有入口，不重复启动。

2026-10-28排查补充：本地没有16006监听即转发未运行；远端6006可能残留旧logdir网页进程，不能仅凭6006有响应判断当前实验。已核对并清理旧scratch目录的PID3487356，当前脚本的冻结编码器正式目录通过首页HTTP200及29条scalar检查，验证后关闭。交互命令使用ssh -t，使Ctrl+C发送到远端网页进程；先等TensorBoard就绪再打开浏览器。遇端口占用先核对ss与/data/logdir，不盲目重复启动或杀其他训练进程。

TensorBoard悬浮框的Wall time是该行所选Step的数据写入时间，不是该run最新更新时间。三组按Step对齐且训练进度不同：例如2026-10-28核查时settle32约8.1M，悬浮该位置会选中baseline／rollout256在10月27日的约8.1M历史点，而两者真正最新点已在10月28日的74.65M／约50M。先核对悬浮框Step、取消局部缩放并查看各曲线自己的末端；不能仅凭日期认定日志停更。当前网页后端可用 `/data/plugin/scalars/scalars?run=...&tag=metrics/success` 核查原始wall_time／step，日期按秒时间戳转换到本地时区；这与目录名日期无关。若最新Step本身仍显示旧日期，再对比该点的HTTP时间戳与浏览器状态，不先重启训练或移动日志。2026-10-28核查证据 `logs/gibson_reproduction_20261026/tensorboard_walltime_audit_20261028.json`。

训练 TensorBoard 在对应 model-dir/tb，每次更新写入 reward、metrics/success、metrics/spl、metrics/view_match、learner/*、perf/fps；log_interval仅限制终端输出频率。现有scratch_smoke已验证29条序列×20点，网页服务没有常驻。查看／导出模板从 liuyi 根目录运行：

```bash
envs/sign-baseline/bin/tensorboard --logdir SIGN/results/gibson_reproduction_20261026 --host 127.0.0.1 --port 6006
envs/sign-baseline/bin/python logs/gibson_reproduction_20261026/export_curves.py \
  --logdir SIGN/results/gibson_reproduction_20261026/scratch_full/tb \
  --output SIGN/results/gibson_reproduction_20261026/scratch_full/curves
```

导出器只读取实际事件，输出 scalars.csv 和 training_curves.png；没有训练事件时明确退出，不生成模拟曲线。当前原版 checkpoint 不保存优化器／完整配置，也未实现断点续训；latest.pth 不是可无缝恢复训练的状态。完整任务须结合 smoke 实测速率判断能否在队列 168 小时上限内跑完，不能把重启当作继续训练。

原训练is_done仅按总步数／更新次数判断，没有reward平台期自动停止。论文V-A.4明确从零训练300M步，不能把该数值直接称为占位上限。若改用预算内观察／人工提前结束，应记录为提前停止实验，并同时查看固定验证任务上的SR／SPL，避免仅凭训练reward短期变平判断收敛。默认num_checkpoints=100绑定总进度；提前终止前应确认近期checkpoint已落盘。可用CLI num_checkpoints=-1与checkpoint_interval按固定更新间隔保存（尚未执行此新实验）。

原 should_checkpoint 用严格大于进度阈值，且循环结束不强制保存最后权重，所以 latest.pth 可能早于训练结束步数。用 TensorBoard 最大 step 核对训练完成，用 checkpoint extra_state.step 标明被评估模型的实际步数；不把二者写成同一个数字。

评估默认已经有6个独立环境进程，OMP/MKL=1限制每个进程的数值计算线程，并非整个作业只使用一个CPU。当前 VectorEnv 按场景划分环境；Gibson val有14场景，先比较6与14环境，不盲目超过场景数。独立并发对照放在 logs/gibson_reproduction_20261026/parallel_benchmark/，使用相同280条任务、同一checkpoint和固定Python哈希种子，记录启动／评估耗时、GPU采样和结果；实际结论以results.json为准。2026-10-26四组均通过：6×1冷缓存211秒／热缓存176秒、14×1为116秒、14×2为138秒；建议后续提速评估采用14环境、每进程1线程，保持原6环境完整结果作基线。热缓存循环加速1.52倍，含启动1.43倍；不能把首次冷缓存比较的1.82倍当纯并发收益。14环境完整4200条耗时尚未实测。

ImageGoalSensorV2 的 uniform目标朝向使用 Python hash(episode_id)，所以 habitat.seed 本身不足以保证不同Python启动的目标图相同。严格比较模型或并发设置时，在启动Python前统一设置 PYTHONHASHSEED（本次对照为0）。原README完整评估未显式固定这一变量，须标注其边界；若后续改用固定hash种子，需要对应的参考模型评估，不将旧未固定hash的结果当成完全配对任务。

## HM3D v0.2 数据与评估

场景为 HM3D **v0.2 validation scenes**；`data/datasets/imagenav/hm3d/v1/` 是任务数据布局。已有 val_easy／val_medium／val_hard，数据检查应覆盖任务引用的 100 个场景及 navmesh。

Habitat-Sim 0.2.2 的下载器不支持 v0.2，使用已有新版官方工具。下载模板从 SIGN 根目录运行，凭据交互读取而不保存：

```bash
cd /scratch/e1538633/liuyi/SIGN
read -r -p 'Matterport API token ID: ' MATTERPORT_TOKEN_ID
read -r -s -p 'Matterport API token secret: ' MATTERPORT_TOKEN_SECRET
echo
/usr/bin/python /scratch/e1538633/liuyi/downloads/habitat_datasets_download_v02.py \
  --username "$MATTERPORT_TOKEN_ID" --password "$MATTERPORT_TOKEN_SECRET" \
  --uids hm3d_val_habitat_v0.2 hm3d_val_configs_v0.2 --data-path "$PWD/data"
unset MATTERPORT_TOKEN_ID MATTERPORT_TOKEN_SECRET
/scratch/e1538633/liuyi/envs/sign/bin/python scripts/check_hm3d_eval_data.py
```

数据检查脚本核对场景／navmesh，并建立 `hm3d/<scene>` 到 `hm3d/val/<scene>` 的路径链接；预期完成提示为 `HM3D evaluation data is ready.`。

以下评估模板在 GPU 计算节点从 SIGN 根目录运行：

```bash
module load Miniconda3/24.7.1-0
source "$(conda info --base)/etc/profile.d/conda.sh"
conda activate /scratch/e1538633/liuyi/envs/sign
python -c 'import torch, habitat, habitat_sim; print(torch.__version__, habitat_sim.__version__, torch.cuda.is_available())'
python run_sim.py \
  --exp-config exp_config/ppo_imagenav_hm3d.yaml,policy,reward,sensors,eval \
  --run-type eval --model-dir results/hm3d_eval \
  habitat_baselines.eval_ckpt_path_dir ckpt/nav_model.pth \
  habitat_baselines.eval.split val_easy \
  habitat_baselines.num_environments 1 \
  habitat_baselines.test_episode_count 10
```

完整评估移除 test_episode_count，并按任务选三个 split。包含 checkpoint 的模型目录不能使用 `--overwrite`。

配置按命令行顺序合并；现有 `...,policy,...` 组合将基础 PPO `num_steps=64` 覆盖为 **512**。以保存的最终配置为准。固定 rollout 不保证完整同任务组，评估也不证明训练行为。

## 轨迹采集与 Qwen 诊断入口

- `src/trainer.py` 在设置 SIGN_TRACE_DIR 时导出轨迹；`src/trajectory_diagnostic.py` 保存 waypoint 与可视化。动作顺序为 `[angular_velocity, linear_velocity]`，值是归一化命令。waypoint 为动作后姿态，RGB 为相应动作前观测；像素不是米。
- 单组八次执行：`scripts/run_group8_collection.py`、`collect_group8.pbs`。固定 checkpoint，一个环境设置 evals_per_ep=8；SIGN_EVAL_SAMPLE_ACTIONS=1 使用原分布随机采样，每次重置环境与循环状态。采集清单核对同起点、目标图与初始 RGB 的哈希。
- 独立 p12 评分：`scripts/score_group8_p12.py`、`score_group8_p12.pbs`。batch8 是八个独立请求，不是完整八条直接比较。
- 成对事实与输入：`scripts/prepare_pairwise_diagnostic.py`。25 步事实窗口与几何候选匹配是候选证据，不是冗余标签，可能包含受困或漏掉相邻窗口回访。
- 成对 prepare／freeze／run／summarize／diagnose：`scripts/qwen_pairwise_diagnostic.py`。已完成的 64 请求不得重跑覆盖；新实验独立版本化。辅助提取不修复原 JSON，重新汇总保留人工栏。
- 历史人工动画：`scripts/render_trajectory_gifs.py`；不需重跑 ImageNav。白底轨迹图不显示墙体或目标，不能据图推断唯一通路；GIF 主要供人审，Qwen 的实际输入以保存的请求为准。
- 历史 v2 和 followup 模板、动作说明修正、分块 prefill 核对、OOM 与 masked_scatter 排查，见 WORKLOG 中导入的完整研究记录及 `SIGN/results/qwen_diagnostic/graded60/` 原日志。其“已提交”等语句是当时状态。

只做已有成对结果的可读字段辅助检查，从 SIGN 根目录运行：

```bash
/scratch/e1538633/liuyi/envs/sign/bin/python scripts/qwen_pairwise_diagnostic.py diagnose
```

## Git、资料构建与发布

| 仓库 | 既有远端与职责 |
|---|---|
| SIGN | origin fetch：`https://github.com/yiichu03/SIGN.git`，push：`git@github.com:yiichu03/SIGN.git`；upstream：`git@github.com:Zichen-Yan/SIGN.git` |
| SIGN-SRU | origin：`git@github.com:yiichu03/SIGN-SRU.git`；SRU 算法实现 |
| SIGN-SRU-reward-review | 与 SIGN-SRU 共享 Git 数据，当前分支 phase1/imagenav-qwen-diagnostics；原 docs/qwen-reward-review-20261013 保留 |
| habitat-lab | origin：`https://github.com/facebookresearch/habitat-lab.git`；第三方依赖，默认不推送 |

默认 push 均面向 yiichu03：SIGN 与 SIGN-SRU 的仓库本地配置为 `remote.pushDefault=origin`、`push.default=current`，现有分支另显式设置 `branch.<name>.pushRemote=origin`。研究工作树共享 SIGN-SRU 的配置。常规默认推送使用 origin 的同名分支；没有配置全分支或镜像推送。

SIGN main 保留跟踪 `upstream/main`，用于取上游更新；推送目标独立设为 origin。只有用户明确要求推送到学长仓库时才考虑 upstream，并另外核对目标与实际写权限。普通“push／同步 GitHub”不代表向 upstream 发布。

SIGN 当前 phase2 跟踪 origin 同名分支，两个 phase1 也分别跟踪各仓库 origin 的同名分支。首次归档时 HTTPS push 缺少非交互凭据，已切换 SIGN 的 push URL 为验证成功的 SSH；fetch URL 和 owner 不变。

Habitat 的本地 `push.default=nothing` 保留官方 fetch 地址，关闭不指定目标的默认推送；它不属于常规项目发布范围。不要为了默认 owner 一致而把依赖 remote 改成不存在的 fork。

本地核对推送配置（示例从 liuyi 根目录执行，不产生推送）：

```bash
git -C SIGN remote -v
git -C SIGN config --get remote.pushDefault
git -C SIGN config --get push.default
git -C SIGN for-each-ref --format='%(refname:short) | push_remote=%(push:remotename) | push_target=%(push:short)' refs/heads
git -C SIGN-SRU remote -v
git -C SIGN-SRU config --get remote.pushDefault
```

当前树没有独立 SRU-Predictor 检出；旧记录说其远端可访问，不代表此处有运行代码。

从根目录检查本地变更：

```bash
git -C SIGN status --short --branch
git -C SIGN-SRU status --short --branch
git -C SIGN-SRU-reward-review status --short --branch
```

历史资料发布器归档在 SIGN phase1，内部仍锁定原 docs/qwen-reward-review-20261013 研究分支。当前研究工作树检出 phase1，直接运行会被分支保护拒绝；未来复用时先明确发布目的并核对工作树／代码路径，不绕过检查。下面是旧流程的模板，不是当前 phase2 可直接运行的命令。

本地构建预览从选定的 phase1 SIGN 根目录运行，不 fetch、不写发布文件、不提交：

```bash
/scratch/e1538633/liuyi/envs/sign/bin/python scripts/publish_relative_diagnostic.py --check-only
```

一键同步从 liuyi 根目录运行：

```bash
bash SIGN/scripts/sync_research_github.sh --check-only
bash SIGN/scripts/sync_research_github.sh
```

前一命令仍检查干净工作树、分支、remote 和远端历史；后一命令会构建、提交并普通 push，只在当前任务需要发布时使用。无变化不产生空提交。证据变化、缺失、远端超前或分歧时停止，不能 force／reset／clean 修复。最新阻塞见 STATUS。

发布范围：实际 SIGN 代码与选定证据；四份根文档生成到相对诊断包的 `workspace/`，保持同名，服务器根文件为维护源。旧 `code/AGENTS.md`、`code/docs/qwen_offline_diagnostic.md`、`code/docs/hm3d_v02_eval.md` 作为历史说明原样保留，不再要求本地有同名文件。发布后的 WORKLOG 仅允许追加。独立检出资料包的读者从包内 README 进入 workspace 副本；文中服务器绝对路径仅供定位本地资源。

根目录尚未纳入 Git；在下一次成功发布前，新增根文档修改只在本地。发布时排除权重、场景、RGB、环境与凭据；每次核对已有归档清单与人工证据，不把同步当作重新运行实验。

修改发布相关逻辑后的 CPU 检查，从 SIGN 根目录运行：

```bash
/scratch/e1538633/liuyi/envs/sign/bin/python scripts/test_research_publication.py
```

## 固定rollout覆盖奖励实验

独立工作目录 `/scratch/e1538633/liuyi/SIGN-frozen-rollout-coverage`，分支phase2/frozen-rollout-coverage，基于dac8609，仅新增ObservedCoverage、rollout末奖励结算与rollout_coverage.yaml。当前／目标RGB共用原冻结ResNet9，覆盖统计不输入Actor；初始视域不计增益，episode内seen覆盖持续跨rollout，换episode才清空，重叠楼层计XZ并集。新观测范围3m、网格0.1m、FOV90°（匹配RGB）、weight0.1是本次实验设定；这是navmesh可行走区二维视域代理，不是真实RGB表面积。

采样每步只保留delta_m2，满H=256后按各环境真实done独立分段、只给片段末步加weight*gain/H，然后按原逻辑计算returns和更新，不等待各环境同步、不改变mask。`reward`仍只记录环境导航奖励；新增标量为`learner/coverage_bonus_sum`、`learner/coverage_bonus_per_step`、`learner/coverage_new_area_m2`。无coverage配置或weight0时不改buffer奖励。

实际提交命令（已执行，勿重复提交）：

```bash
qsub /scratch/e1538633/liuyi/logs/gibson_rollout_coverage_20261027/train_personal.pbs
```

作业1497416使用personal-e1538633／auto、A40／36CPU／240GB、168h，继承原seed100、hash0、8×256、300M上限、冻结encoder初始化及PPO/MRQ/RandomShift/Qc；从头初始化非encoder，不承接短跑或旧策略。仅在原`--exp-config exp_config/ppo_imagenav_gibson.yaml,policy,reward,sensors`末追加`,rollout_coverage`；其余训练参数见脚本。输出独立目录`SIGN-frozen-rollout-coverage/results/gibson_rollout_coverage_20261027/train_personal_8env`，TensorBoard位于其tb子目录。

评估继续原`...,policy,reward,sensors,eval`，不追加coverage配置；6环境、500步、全部4200条Gibson val，原安全权重／指标不变。完整配置差异审计config_audit.json只允许新measure与输出目录差异。GPU短跑同节点三组各20更新，零权重公共指标与baseline一致、正权重bonus守恒且encoder42项不变；本节点统计开销约30.3%额外时间，不能用单一Adrian场景0.304ms冒充总体开销。GPU相机方向／遮挡图camera_coverage_alignment.png及全部原始结果位于logs/gibson_rollout_coverage_20261027。旧作业1496716与原SIGN目录受哈希守卫保护，本实验不对其切分支／改文件／停作业。


### 覆盖奖励收益的同阶段核对（2026-10-27）

证据入口`logs/gibson_coverage_comparison_20261027/`。`analyze_training.py [独立输出目录]`只读两训练TensorBoard，导出原始CSV、JSON及PNG/PDF；原生指标为50-update完成episode滑动均值，额外100万步平均只作描述，不把相邻点当独立样本。比较模型时从固定编号ckpt读取extra_state.step，复制到证据目录并核对SHA，不能只按文件名或latest判断训练预算相同。当前两份ckpt.17均9216000步。

本轮`baseline.pbs`／`coverage.pbs`已分别提交为1498509／1498510且完成，不重复qsub；外部`evaluate_checkpoint.py`复用原生eval配置（无coverage YAML）、固定hash0／seed100、6环境／500步／全部4200val、独立输出。`summarize_eval.py`核对实际配置并产生full_val_comparison.json；允许差异为权重路径、输出路径及严格对应的cmd_trailing_opts副本。该原生evaluator不保存逐episode结果，完整汇总可比较SR/SPL，不能恢复成对成败或计算成对显著性。一次seed／时点不代表最终收敛。


### Habitat-GS 分支发布

SIGN-habitat-gs有完整评估作业时保持其HEAD与源码。使用新建的临时detached工作树 `SIGN-habitat-gs-publication` 生成 `docs/experiments/habitat-gs-imagenav/`，发布后删除这个已提交且干净的临时工作树；不复用或修改coverage发布工作树。普通push的目标为 `git@github.com:yiichu03/SIGN.git` 的 `experiment/habitat-gs-imagenav`；与运行目录相比允许仅多资料及README导航提交，不pull进运行目录。 本地运行分支可跟踪origin同名分支但保持原HEAD；后续发布须从远端最新资料提交保留已发布WORKLOG前缀，不为消除落后状态而修改运行目录。

构建器 `logs/habitat_gs_publication_20261028/build_publication.py` 锁定本轮运行代码95eef9b；选取已完成的10条pilot证据、原始数据哈希清单、完整评估输入／实际配置／提交记录及明确标注未完成的日志截面，再生成根四文档副本与发布SHA清单。构建器只生成／检查，不commit或push。后续发布先选择新的明确基点，核对已发布WORKLOG的前缀关系，不绕过锁定检查。不得将活动任务部分日志命名成完整结果；最终result.json存在且验证前不发布完整SR／SPL。

发布前验证所有资料哈希、gzip解压哈希、相对链接、体积与凭据模式；与运行代码相比仅README及docs变化。代码原历史包含作者公开权重，本次不新增／更新权重、场景、环境、原始相机序列。四文档仍由根维护源生成副本，推送回执追加至根WORKLOG，不能为包含回执而循环生成重复快照。

### 阶段二覆盖奖励资料发布（2026-10-27）

旧phase1资料发布器锁定旧SRU研究分支及历史证据，本次不调用或修改它。新资料位于SIGN的`docs/experiments/frozen-rollout-coverage/`，通过独立detached工作树SIGN-coverage-publication构建，并普通push HEAD到origin/phase2/frozen-rollout-coverage；有效push URL必须为git@github.com:yiichu03/SIGN.git。构建脚本`logs/gibson_coverage_comparison_20261027/build_publication.py`仅锁定本轮base6983c91，选取已完成的不可变验证结果、最新完整scalar导出、两版曲线、实际配置、测试和命令，生成四根文档副本与SHA清单；不启动作业、不提交或push。未来资料更新应先选择新快照与明确base，不绕过锁定检查。

本轮已执行`git worktree add --detach /scratch/e1538633/liuyi/SIGN-coverage-publication 6983c91e20493ff25ff32c24df02b968cc34f701`。构建/检查命令为`python3 logs/gibson_coverage_comparison_20261027/build_publication.py`和同命令追加`--check-only`。只允许新增资料包和根README导航；src、exp_config与run_sim.py相对运行时代码必须零差异。scalar CSV和原生控制台日志用确定性gzip打包，验证解压SHA；不上传checkpoint、场景、环境或原始相机数据。工作区WORKLOG发布副本必须保留已有完整前缀。有效远端SHA核对后普通push，不force、不改训练工作树HEAD。

资料发布后，远端coverage分支会比运行中的SIGN-frozen-rollout-coverage本地代码提交多资料提交；不为消除这项差异而pull进运行目录。实际训练源码由6983c91及source_manifest固定；原SIGN仍dac8609。根四文档为维护源，包内副本截至manifest的生成时间；最终推送回执留在根WORKLOG。

## 32步覆盖结算对照（2026-10-28）

独立工作树 `SIGN-frozen-coverage-settle32/`，分支 `phase2/frozen-coverage-settle32`，运行代码 `a7cc9e09fe3c0a9abfa054307cfb80474217d1a2`。新增 `habitat.task.observed_coverage.settlement_interval` 为非负整数；默认0与原coverage边界一致，本次CLI32在rollout步32/64/…/256增加结算边界，真实episode边界额外保留。完整256步采完后统一加bonus，分母仍256；真实mask、GAE跨结算边界传播、覆盖历史和encoder冻结逻辑保持。采样8×256、weight0.1、seed100/hash0、300M上限、168h预算、personal-e1538633/auto/1A40/36CPU/240GB均继承原对照；从公共encoder初始化，其他模块从头初始化，不从短跑checkpoint续接。原1496716/1497416及其训练目录受保护。

支持目录 `logs/gibson_coverage_settle32_20261028/`：`source_manifest.json`固定本分支源文件，`protected_worktrees_before.json`保存两原源树，`check_inputs.py`检查两边和数据。`preflight.json`记录8项新CPU测试、9项原回归、10组旧实现精确兼容及最终配置差异；原评估配置字节一致（不追加coverage配置、6环境/500步/4200val）。

GPU短跑脚本 `short_checks.pbs` 调用 `run_short_checks.py`，同节点interval0/32各40960步；须有 `short_summary.json` 的passed=true才能启动正式脚本。正式 `train_personal.pbs` 的原命令末尾仅追加 `habitat.task.observed_coverage.settlement_interval 32`；输出 `SIGN-frozen-coverage-settle32/results/gibson_coverage_settle32_20261028/train_personal_8env`，TensorBoard在tb子目录。脚本拒绝已有checkpoint目录，禁止重复提交；实际作业ID与状态以本目录提交登记和STATUS为准。

训练日志 `reward` 仍是导航reward；新奖励总和/每步均值和新增面积仍由原 `learner/coverage_*` 记录，面积/环境步可将每rollout面积除以2048。对照应按相同训练步数比较，不能以各自最新单点或短跑表现声称收益。

本轮短跑1502328已通过（Exit0、两组各40960步、42项encoder状态不变、奖励守恒）；正式1502352已提交，勿重复qsub。代码a7cc9e0已push到yiichu03/SIGN的phase2/frozen-coverage-settle32，实验说明见该分支docs/experiments/coverage-settlement/README.md。


### Gibson静态topdown小样本（2026-10-28）

目录`logs/gibson_topdown_pilot_20261028`：公开完整SIGN权重、同任务重复随机采样，原始XYZ/朝向保存在各C*/trajectory.json。CPU重画顺序：在sign-baseline环境运行`rebuild_display.py`，再`render.py`。前者重建0.025m高度切片与视域（3m/90°），仅fog原点允许≤2像素边界投影；原轨迹与0.1m训练口径mask不变。后者生成18PNG、CSV、manifest和zip。采集需PBS GPU，历史collect_autox.pbs保留原提交内容，新采集使用新目录并按collect→rebuild_display→render顺序。组内步数不等，覆盖总量不能直接作效率排名；这套图不是训练奖励数值。


### Qwen静态八图裁判工程入口（2026-10-28）

工作树`SIGN-qwen-topdown-judge`、分支`phase2/qwen-topdown-judge`，基于settle32提交a7cc9e0；仅离线裁判，不改trainer/measure/采样。核心`src/qwen_topdown.py`不依赖Habitat，模型在enabled=true的run调用内延迟导入，使用独立envs/qwen35。默认配置`scripts/qwen_topdown_config.json`为enabled=false，只有run的`--enable`开启真实推理；它不是run_sim.py的训练开关。

从该工作树执行：

```bash
python3 scripts/qwen_topdown.py prepare --manifest /绝对路径/input.json --prompt /绝对路径/prompt.txt --out /新的请求目录
python3 scripts/qwen_topdown.py verify --request /请求目录
python scripts/qwen_topdown.py run --request /请求目录 --out /新的回答目录 --config scripts/qwen_topdown_config.json --enable
```

最后一条须PBS GPU及qwen35环境。外置manifest为group_id与8个candidates，每条含id、image、正整数steps、window_start_step=0、task。task包含scene_id、episode_id、start_position、start_rotation、goal_sha256、policy_sha256，8条必须相同；可附covered_percent/new_percent/new_m2，其他数值不会拼入请求。prompt完全外置，当前不固化评分角度。prepare冻结图片副本、实际消息、原manifest及SHA；默认拒绝不等步数，`--allow-unequal-steps`仅允许带醒目标记的离线诊断。初版只接受episode初始窗口，不能把训练中各自不同历史的第256–512步误当同条件。

8张图是一个多图请求。配置上限每图262144像素、输入6000token、输出2048token、固定seed100、贪心生成；不带成功/人工分数。run保留原始文本、实际chat/token/grid、输出tokens、耗时/显存和错误；截断、非法JSON/非有限/重复ID/越界分数均不当有效score。relative_scores_v1只约束scores:[{id,score}]结构，允许并列和null；不定义排序公式、不将unknown补0。json_object模式用于无评分工程检查。未来训练接入须另外确定组边界、历史可比性、奖励映射、超时和失败策略。

本次Gibson适配与测试输入生成器`logs/qwen_topdown_engineering_20261028/prepare_pilot.py`，实际smoke.pbs只对Denmark组做图例连通性检查。两个Gibson组步数不等，已显式标记，仅验证工程链路；评分开发可优先使用HM3D matched_prefix。测试命令：`python3 -m unittest discover -s tests -p test_qwen_topdown.py -v`。


三组训练日志比较入口（2026-10-28）：在liuyi根、sign-baseline环境运行`python logs/gibson_train_threeway_20261028/analyze.py`。每次生成独立snapshot_HHMMSS，固定字节快照三组事件并保存SHA；导出全部scalar CSV、相同步数窗口JSON及PNG/PDF，不加载模型或启动评估。三组比较由最新较短32步实验截断，基线/原coverage另按较长共同步数比较；表中为原生50-update滑动统计的区间平均，不把相邻日志点作独立样本。


### 三组同阶段SR/SPL/覆盖评估（2026-10-28）

支持目录`logs/gibson_threeway_coverage_eval_20261028`，独立detached `SIGN-coverage-eval @a7cc9e0`。三份不可变ckpt.8快照均4608000步，manifest.json含来源/SHA、4200 val任务键及源文件守卫。提交过的evaluate.pbs为CFP/autox/A40/4h，实际1503479，勿重复提交。程序顺序：28条baseline无coverage control→三组各28条有coverage smoke→summarize.py smoke验证基线轨迹/指标原样、三组起点与目标图相同→三组各4200 full→summarize.py full。6环境、500步、seed100/hash0，原生eval和公共safety模型。原代码/训练作业不改；ObservedCoverage仅统一测量（weight0），mpp0.1/radius3/fov90，保留原栅格边界行为。

外部RecordingNavEnv在真实done时保存完整episode数值，默认新增面积扣初始视野。输出同时有mean(A_i/T_i)与sum(A_i)/sum(T_i)，避免混淆episode平均和每动作总体均值。JSONL与native TB逐项核对；same-step/任务集合/起点/目标图SHA不通过即拒绝完整结果。进度看runtime.json与evaluate.pbs.log，各阶段日志为control_baseline.log/smoke_*.log/full_*.log；只有全部模型完整结束才产生full_comparison.json。preflight.py会写独立测试与配置输出，不在已用目录盲目重跑；恢复失败先保留现场并创建新attempt目录。


### 当前Qwen模式：单图独立评分与速度比较（2026-10-28）

用户已将方案改为单图独立评分，8环境8请求无需相同场景/任务；旧src/qwen_topdown.py八图同会话仅为历史接口。当前src/qwen_single_image.py的SingleImageJudge在独立qwen35进程常驻模型，score(images)将1–8图片分别组成独立会话，batch并行，输出单个score或null，不做组内归一化。每轮仅传图片，不能每轮重新构造模型。评分逻辑尚未接PPO。

测速入口`scripts/benchmark_qwen_single.py --model-dir /模型目录 --prompt /prompt.txt --images /图1 … /图8 --out /全新输出目录 --repeats 3`，须PBS GPU。官方Qwen3.5-9B/4B/2B/0.8B均在models；小模型revision与官方LFS/SHA逐文件清单位于logs/qwen_single_latency_20261028/download_*.json。已完成PBS1503515，勿重复提交已有输出目录。支持目录benchmark.pbs、run_all.py、plan.json固定同节点实验，summarize.py汇总，plot.py生成图表。

速度结论以comparison.json为准：常驻独立batch8约9B1.68s、2B0.87s，包含PNG读取/processor/H2D/generate/decode/parse，不含模型初始化、在线轨迹画图、IPC或PPO同GPU争用。冷启动另列。严格JSON失败单列，原始文本不覆盖不修复；输出token数随模型不同，不能将数字解释为固定token纯算力比较。当前训练每update收8×256步；training_timing.py从终端最新500update的实际timestamp差计算每轮时间，控制台每10次update打印。同步奖励接入初估T_new=T_train+T_batch8，不能把单图耗时乘8当并行耗时，也不能自动假定与PPO完全重叠。


### 当前单图A/B/C真实概率评分（2026-10-28）

代码phase2/qwen-topdown-judge@4cc7257；核心SingleImageJudge.class_probabilities复用旧模型/独立batch/processor，读取最后真实输入token位置预测下一个回答token的raw logits。标签固定A32=LOW、B33=MEDIUM、C34=HIGH，T1仅在3候选softmax，q=0.5*p_medium+p_high；另记录全词表candidate_mass。score()生成JSON和旧benchmark保留默认auto精度，新scripts/score_qwen_single.py默认FP32，以避免已实测BF16批次形状产生的0.029概率变化。FP32探针batch/solo差1.74e-5，质量门槛1e-4，排列差/forward与首步生成raw logits差0；验证只生成1token，正式16图不生成文本数值。

入口需要两组各8项manifest：groups:[{id,items:[{id,image,action_count,new_area_m2,new_area_m2_per_action?}]}]。action_count正整数，面积有限非负且必填，比例由程序计算/核对；缺m²不能从百分比补。现成输入logs/qwen_token_probabilities_20261028/manifest.json，面积从display_map_data.npz新增有效格数×0.025²重算，与旧CSV及trajectory实际动作核对；保留2.5cm显示重建/边界<=5cm/3m/90°口径，不冒充训练0.1m测量。

用户改scripts/prompts/qwen_single_coverage_abc.txt后，直接从liuyi执行`qsub logs/qwen_token_probabilities_20261028/score.pbs`。可用`qsub -v QWEN_PROMPT=/绝对路径/prompt.txt logs/qwen_token_probabilities_20261028/score.pbs`指定另一个prompt；不要改A/B/C映射或要求JSON数值。PBS在qwen35、GPU中执行score_qwen_single.py --manifest … --prompt … --out … --batch-size 8 --verify，默认9B、FP32、一次加载。--dtype auto/bfloat16可显式试验，但严格batch质量检查可能失败，不能静默提高阈值。

新job输出logs/qwen_token_probabilities_20261028/run_JOBID，保留scores.csv/json、manifest/prompt文本与SHA、图片副本、每批原logits/概率/输入token/attention_mask/grid/rendered chat、verification与run状态。prompt_version是内容SHA，不是人工标签；q是3候选条件分数，不是校准成功率。首次失败1503665和最终成功1503691均保留。完整16图结果在run_1503691，检查脚本check_results.py可核对q/概率和/metadata；旧输出不可覆盖。

基线1496716现已按用户新授权停止为该Qwen释放GPU；权重74240000步、TB与全部历史记录保留，最后终端74649600步。原checkpoint无优化器级状态，不自动重提或宣称能等价恢复。两覆盖训练/三组评估不受此停止影响。


### Qwen图片与结果发布（2026-10-28）

GitHub目标yiichu03/SIGN、phase2/qwen-topdown-judge；资料入口docs/experiments/qwen-topdown/README.md，reports/pilot_9b_2b.md为16图双模型对照，reports/diverse_2b.md为8场景16任务的2B评分。images去重保存32张图及4张overview，evidence保存输入/结果/真实logits/验证/测速与失败审计，manifests使用相对图片路径；原审计中的服务器路径保留原文。公开面积是2.5cm显示重建口径，不等同0.1m训练reward。

本轮构建已执行`python3 logs/qwen_publication_20261028/build_publication.py`（运行代码HEAD4cc7257）；原始证据只读复制、轨迹JSON确定性gzip，根四文档自动快照，WORKLOG前缀不可改。构建器归档在包内scripts/build_publication.py；可从liuyi执行`python3 SIGN-qwen-topdown-judge/docs/experiments/qwen-topdown/scripts/build_publication.py --check-only`重验SHA/大小/可移植manifest/相对链接与运行时代码差异。未来更新先创建独立证据目录并复核源commit，再调整构建入口，不覆盖旧结果。

发布包不含模型、场景、环境或第一人称RGB序列；不提交zip重复图。发布前核对origin有效push URL与分支、git diff --cached --check；只普通push同名分支并比对ls-remote SHA。根文档快照截止提交前，push回执追加在服务器WORKLOG，不为包含回执循环生成提交。


### 最新共同checkpoint三组评估（2026-10-28，8.192M）

1504280的新批次在`logs/gibson_threeway_coverage_eval_latest_20261028`；prepare/preflight/evaluate/recording_env/run_all/summarize六脚本与已完成1503479逐字节相同，PBS仅换名称与输出目录。prepare选择三训练目录共同存在的最大ckpt编号，并CPU核对extra_state.step一致、参数有限，另存不可变快照与SHA；本次ckpt.15／8192000。不能依据单组最新步数混配，也不要直接重跑已使用目录。

已执行`qsub /scratch/e1538633/liuyi/logs/gibson_threeway_coverage_eval_latest_20261028/evaluate.pbs`，CFP04-SF-109/autox、1A40/36CPU/240GB/4h；勿重复提交。`qstat -f 1504280.stdct-mgmt-02`看调度，批次runtime.json和evaluate.pbs.log看阶段；只有control与smoke通过后才全量，full_comparison.json仅在三组4200全部结束并匹配任务/目标图/起点及原生TB时生成。预计约3h为依据上次2:59:09的估计。旧4.608M结果继续在原目录，两个训练与冻结基线状态不受评估影响。


### Qwen2B历史窗口离线对照与交付（2026-10-29）

工作树SIGN-qwen-history-window、分支phase2/qwen-history-window。核心SingleImageJudge不变，src/qwen_single_image.py仅增加prior_seen_area_m2／total_covered_area_m2的校验与实际输入；三个脚本prepare_qwen_history.py／evaluate_qwen_history.py／package_qwen_history.py分别做保存位姿重放导图、单模型FP32独立ABC评分、盲审报告/ZIP。31项单测命令`python3 -m unittest discover -s tests -p 'test_qwen*.py' -v`。脚本入口/参数见归档README；准备OUT必须全新，勿重跑已使用的PBS输出目录。

来源为b1c24dc已发布docs/experiments/qwen-topdown中的pilot_2b/diverse_2b的32条原始轨迹/2.5cm栅格/3m/90°。当前动作为(start,end]，红线路径含两端，历史为此前真实动作；段前覆盖包含共享起始观测，不计起点收益。旧协议仅扣本窗口起始视野，历史版扣全部段前已见；总覆盖=深蓝+浅蓝，并实际传入模型。隐藏黄线对照与完整历史的覆盖/统计/prompt完全相同。宽黄虚线衬红细线，起终点同格使用同点大绿圈＋X，不能修改坐标来美化。

原1505083虽概率检查通过，QA发现绿点被X遮挡，保留首跑并仅2B补跑。最终1505092、运行代码0bb9a90，支撑logs/qwen_history_window_20261029_revision2；run.pbs／input_guard／submission／scheduler／原log均在此。最终包qwen2b_history_review.zip，浏览打开index.html（默认隐藏分数），人工表human_review.csv为空；4项待审类型仅自动线索，不是真值。REPORT.md区分完整128、完整256、短段、整体历史与仅黄线；256全部无历史，不能拿来验证历史能力。

`check_bundle.py`实际解压ZIP重算SHA/面积、核对100图当前起终点投影和仅黄线像素差，`browser_check.py`用Chromium离线file://检查100图解码、默认隐藏/显示开关与筛选，无外网请求。结果bundle_check.json／browser_check.json。浏览器依赖在logs专属目录，不进入Git/ZIP。根四文档由publish.py生成副本到docs/experiments/qwen-history-window/workspace，服务器根为维护源；发布前运行该脚本--check-only并核对origin=yiichu03/SIGN、分支与运行源码无差异。ZIP不重复进Git，图片/报告/原始输入/概率审计直接入资料目录。


### 当前历史图线型更新（2026-10-29，用户指定）

黄历史线与红当前线统一为1.5pt实线，只以颜色区分；不再使用此前虚线版的粗黄衬线。红线在上层，完全重合的黄线可能不可见，prompt明确不能把未见黄线当作无历史；不偏移真实轨迹。主代码prepare_qwen_history.py的history_prompt/render和package_qwen_history.py生成说明相应更新，ABC规则及数值统计不动。旧1505092虚线结果/图片/文档不可改，新的2B测评与最终ZIP在logs/qwen_history_solid_20261029；应按各版本原图/prompt/SHA对应评分，不复用不匹配结果。


### TensorBoard新启动时历史尚未读完（2026-10-29实测）

当前2.8.0、load_fast=false、logdir_spec三组/3读取线程，新进程13:26:55启动后约7分钟才把大事件文件读到末尾。初次API虽已有三组/tag，末步仍可能是10月27日：本次baseline约19.8M、coverage256约16.3M，随后推进到40.7M/33.9M；13:33:54才追到74.654M/68.610M，32版追到18.870M、事件13:33。网页有响应或首次曲线出现不代表全历史已载完。

用户原SSH命令无需改，浏览器打开http://127.0.0.1:16006/。保持连接，等后端读取追上再刷新/Reload；在Runs勾选coverage_rollout256/.与coverage_settle32/.，baseline_frozen/.已按授权停止，后续无新点正常。若仍显示旧范围，取消局部缩放/恢复完整Step横轴。反复结束SSH重启会重复全量初读。诊断先用/data/environment核对真实目录，再用/data/plugin/scalars/scalars?run=…&tag=metrics/success比较末步/时间与文件；若末步持续追赶则是初读，若API已最新而浏览器旧则再查页面刷新/缩放/所选run。不要因网页旧日期重启训练或移动日志。


### 2026-10-29最新共同步数三方法验证（18.944M）

单一PBS1506785.stdct-mgmt-02，支撑目录logs/gibson_threeway_coverage_eval_20261029；已执行`qsub /scratch/e1538633/liuyi/logs/gibson_threeway_coverage_eval_20261029/evaluate.pbs`，勿重复提交。同CFP04-SF-109/autox/A40/36CPU/240GB/4h，复用1504280的六份脚本逐字节一致，仅PBS名称/新输出目录改变。准备时三组最大共同ckpt.36，CPU核对extra_state.step均18944000、参数有限，并逐份保存独立副本及SHA。

前置28条无覆盖baseline control＋三组28条smoke，要求baseline真实轨迹/原生指标被动性与任务/起点/目标一致后，顺序baseline→coverage256→coverage32各4200完整val，再汇总。原协议6环境/max500/seed100/hash0、同public safety、原观测与导航奖励；新增覆盖只统一测量，weight0、mpp0.1/3m/90°。输出runtime.json、逐阶段log、native TensorBoard与episodes JSONL；只有三组完整且质量检查通过才生成full_comparison.json，两种面积/动作聚合口径分开。

状态查`qstat -f 1506785.stdct-mgmt-02`与本批次runtime.json/evaluate.pbs.log；估计约3h从启动计，不保证精确时间。原4.608M与8.192M目录保持，当前训练工作树/源码/参数与已停止基线均未改动。

## Qwen128 / beta0.1 训练奖励（2026-10-29新授权）

独立开发入口 `SIGN-qwen128-reward` / `phase2/qwen128-reward-beta01`，基点453179c；实际运行提交与作业状态见STATUS的Qwen128项。用户已明确要求完成验证后直接提交正式训练，不因旧离线分支“无导航训练”的历史范围再次询问授权。原训练/评估目录不切换、不修改；不重启已停止基线。

配置在原冻结训练 `--exp-config exp_config/ppo_imagenav_gibson.yaml,policy,reward,sensors` 后追加 `,qwen_reward`。原初始化/超参数保持，8环境×256步，seed100/hash0，仅加载并冻结公开visual_encoder；`qwen_reward.enabled=True,beta=0.1,settlement_interval=128`，原几何coverage权重0。正式300M为上限，个人auto/1A40/36CPU240GB/168h沿用既有预算，不能声称168h完成300M。正式从全新初始化启动，不从短测checkpoint恢复。

每个环境在rollout内第128/256个动作及真实终止时结算当前片段（终止落在边界只结算一次）。bonus=beta×实际段长/256×原始q，在段末写入；不减0.5、无组内均值，不改变masks/GRU。原`reward`、`metrics/success`等仍为导航指标；新增`learner/qwen_*`与`qwen/rollouts.jsonl`单独记录bonus/q/面积/有效率/开销。`nav_rewards`原样保存环境奖励，只有启用正权重Qwen时MRQ使用该目标；GAE/PPO/critic使用混合rewards，旧coverage配置的MRQ路径不改。

`environment.py`在VectorEnv自动reset前产生独立快照；payload外层tuple保留穿过HabGymWrapper的展平，trainer先pop再提取标量。身份含env/reset编号/episode/rollout/窗口及全局步，严格账本拒绝错误、遗漏与重复回填。历史仅在真实reset清空，覆盖和完整episode位姿在线增量维护。`src/qwen_geometry.py`提取原离线绘图和面积函数：2.5cm网格/3m/90°，黄历史和红当前均1.5pt实线，深蓝为段前已见、浅蓝为真正新增。固定初始楼层；空图、非有限姿态、越界、距navmesh超过原离线2.01像素容差或episode高度范围≥0.5m时记录几何无效原因并跳过bonus，不用零分冒充Qwen结果。

`src/qwen_reward.py`启动独立`envs/qwen35/bin/python scripts/qwen_reward_worker.py`，一次加载FP32 Qwen3.5-2B，复用class_probabilities；每图独立会话，batch≤8、ABC token softmax/T1、q=.5p_medium+p_high。训练环境sign-baseline不升级。关闭或beta0不启动worker和轨迹收集；run_type非train及eval路径均关闭。worker异常、超时、请求/片段ID错配明确报错，不静默填零。原prompt直接读取`docs/experiments/qwen-history-solid/prompts/history.txt`，不要在运行中修改它。每段保存统计/窗口/概率/logits/SHA，PNG仅定期或诊断抽样，tmp只删除本请求生成的临时图。

支撑 `logs/qwen128_reward_20261029/`：`run_training.py short`顺序跑原基线8192、beta0对照8192和Qwen40960；`verify_short.py`核对真实checkpoint、全部scalar、实际长历史图/mask/统计逐位重放及原导航奖励/mask不变。若Qc出现GPU舍入差，另跑未修改基线对照，保留误差证据，不为追求逐位相同改变Qc。`short.pbs`和`formal.pbs`分别为诊断与正式入口；已有作业不要重复qsub。`source_manifest.json`约束运行源码及原工作树、公开权重、数据和prompt。

正式每250更新保存512k步checkpoint，并在4.608M/8.192M额外保存不可变`milestone_STEP.pth`及SHA侧车。提前提交两组独立CPU `watch.pbs`及GPU `evaluate.pbs`；waiter以PBS after训练开始为依赖，仅等待/核对对应侧车与checkpoint SHA，退出0后由GPU作业的afterok依赖释放评估，不依赖计算节点动态qsub。CPU等待不占GPU；保存真实两组提交回执及val_STEP/wait_state.json。评估复用未改动`SIGN-coverage-eval`原生evaluator，Qwen及Qwen轨迹采集关闭；4200val/14场景、确定性6环境/max500/seed100/hash0，额外原0.1m/3m/90°被动coverage统计、reward weight0，输出SR/SPL及两种面积/动作聚合。0.1m是既有共同评估口径，与Qwen输入图0.025m分开记录。val_STEP/wait_state.json与val_STEP/submission.json提供实际排队ID，侧车出现前不虚构评估ID。

Qwen短测与正式运行区分：1507196中Qwen部分固定40960步、输出short_qwen_40960；1507268为独立fresh-init正式任务、输出train_personal_8env、168h/300M cap。正式每250更新/512000步首存，初期ckpts为空并非训练未启动。只读进展快照入口`envs/sign-baseline/bin/python logs/qwen128_reward_20261029/snapshot_progress.py`，保存有限字节事件/逐段记录/CSV/PNG与实际统计，早期基线仅读取相同步数前缀；不加载GPU或改训练。输出新progress_时间戳目录，避免覆盖旧证据。

三方法共同18.944M的完整结果：`logs/gibson_threeway_coverage_eval_20261029/full_comparison.json`，1506785于2026-10-29 15:29:34 Exit0；各4200val、ckpt.36，原始逐episode保存在full_baseline/episodes、full_coverage256/episodes、full_coverage32/episodes，原生TensorBoard在各full_CASE/native/tb。主覆盖效率统一为sum(new_area_m2)/sum(actual_actions)；结果另含mean(new_area_m2/actions)，两者不得混用。三组确定性6环境/max500/seed100/hash0、共同任务/起点/目标及公开safety、原0.1m/3m/90°被动coverage weight0。该结果是几何覆盖两方案与冻结基线；2026-10-29记录该结果时，Qwen模型尚未到其4.608M/8.192M评估点，后续状态以各批次记录为准。

训练剩余时间估计：运行CPU只读`python3 logs/gibson_training_budget_20261029/estimate.py`，从原console的frames/时间差计算最近1/3/6/12h速度，主报3h，剩余时间=(300M-current_step)/recent_fps；同时单列PBS截止时间和剩余预算。50M原停止条件是use_aug_flag=False，它只门控MRQ辅助更新；PPO中RandomShift仍按shift配置执行，不能将该条件说成关闭所有数据增强。32版未到50M时，可另报假设后段达到256当前速度的条件估计，不将其当实测保证。

## A/B/C beta0.03与几何128匹配对照

独立SIGN-qwen-ablation/phase2/qwen-beta003-geometry128从33e30d2建立，运行提交d2352f0。原exp-config末追加`,qwen_reward,qwen_a128`（A）、`,qwen_reward,qwen_b256`（B）、`,qwen_reward,geometry_c128`（C）；A/B beta.03、128/256结算，PPO仍256；C关闭Qwen、alpha.2927574680399425、新面积/256末步奖励，共用2.5cm/3m/90°采集/历史/无效规则，不渲染不写概率。三组显式mrq_reward_target=navigation，独立于Qwen enabled；旧配置无字段仍mixed。其余初始化与算法沿用冻结基线。

支撑logs/qwen_ablation_20261029，run_case.py按case/stage启动fresh目录，verify_case.py验收真实40960步，formal_submission.json记录已提交的A1507648/C1507650/B1507651和六次val。已有作业不重复qsub。每组168h/300M cap，CFP/autox→gpux，资源不足优先A/C；正式输出SIGN-qwen-ablation/results/qwen_ablation_20261029/{A,B,C}/train，TB其tb。每250更新512k常规保存、4.608M/8.192M准确保存milestone，CPUwait核对step/SHA，原协议4200val通过afterok释放。新waiter的PBS查询设15秒timeout，超时继续按checkpoint轮询，避免查询故障阻塞权重就绪检查；旧waiter不改。

冻结校准docs/experiments/qwen128-reward/ablations/calibration来自旧1507196短测有效1176段；alpha=.03*sum(L*q)/sum(area)=.2927574680399425，原始记录SHA26180a9e26faa7024f0564193c66d46a8cbb31d1e2c1d99254aeb49b00d81bd7。calibrate_geometry_control.py可只读复算至全新输出，禁止用新训练或val数据重拟合此对照。正式训练报告原reward、原SR/SPL/碰撞以及独立qwen_或geometry_ bonus与exploration段长/bonus分布；未来val用原0.1m被动统计，与训练2.5cm口径分开。


### 六组训练指标只读汇总（2026-10-31）

在liuyi根运行`envs/sign-baseline/bin/python logs/training_readout_20261031/readout.py`。只读取六组既有训练和已停止基线的TensorBoard，创建独立snapshot_HHMMSS，保存固定字节事件/rollout JSONL及SHA、所选CSV、readout.json和同预算PNG；不加载GPU/模型/模拟器，不提交作业。报告各自近1M、共同步数近1M、旧方法近5M与近3h实际更新耗时；先核对时间和训练预算再比较。SR/SPL是重叠的原生50-update滑动统计，不能把相邻点当独立样本。旧0.1m覆盖与新0.025m有效段面积不得跨口径排名；校准alpha只匹配最初短测，后续C和Qwen bonus总量可能分化。


六组训练资料发布入口：`logs/training_readout_20261031/publish_readout.py --tree SIGN-qwen-ablation-publication`用于基于ac62298的单次增量构建；完成构建后仅用同命令加`--check-only`核验。它更新既有qwen128-reward包的ablations/training_20261031、四根文档生成副本及SHA清单，只允许README/docs差异；旧快照不覆盖、WORKLOG保留前缀。所选CSV与rollout确定性gzip、输入SHA和56项1/2/3/5M窗口指标可离线复核，完整TB/权重不上传。发布到yiichu03/SIGN的phase2/qwen-beta003-geometry128，运行目录d2352f0保持不动；未来更新创建新日期证据和明确基点，不重复构建本快照。


## 2026-11-03：意外中断后的权重继续训练

10月31日六正式训练Exit143；旧checkpoint只有state_dict和extra_state，无优化器/RNG/环境状态。本批次按用户授权从最新稳定编号权重继承全部103项状态，保留encoder42项冻结、全局steps/updates与300M算法上限；PPO/Qc优化器、episode/GRU/覆盖历史和随机状态重新初始化。它是明确带断点边界的weights continuation，不是无缝恢复。旧输出只读；四SIGN-continue-*独立分支和输出负责续跑。原先人工停止的基线不自动重启。

支持目录logs/training_continuation_20261103包含plan.json（原job/源checkpoint SHA/步数/剩余预算）、previous_jobs.json、checkpoint_audit.json、四提交commits.json/source_manifest.json。原exp-config末尾新增`,continuation`，通过training_continuation.checkpoint及sha256显式校验；默认无路径时原行为不变。首次旧checkpoint须allow_legacy_weights=True，之后新checkpoint额外保存PPO/Qc learner_state；仍不保存模拟器/RNG，后续也不声称轨迹精确恢复。

短测1511108通过autox/CFP，六组各4096步；通过stop_after_steps结束，不改变原300M分母/学习率进度。verify_short.py核对原配置差异白名单、103项初始状态/42冻结项、累计步数、原reward/真实mask、Qwen local ledger及概率和bonus、后续optimizer保存。正式入口`python3 logs/training_continuation_20261103/submit_formal.py`仅在此短测F/Exit0及六组报告passed后提交；一旦有formal_submission.json拒绝盲目重提，先检查实际job。每组正式walltime=原168h−旧PBS实用时长−1h恢复验证保守预留，300M是累计上限；1h为预留而非声称实际用量。

正式输出在plan中各tree的`results/continuation_20261103/CASE/train`；TensorBoard子目录tb、ckpts及continuation.json。旧数据不混写。Qwen ledger本地从rollout0开始，新环境的episode历史也从头；continuation.json中的qwen_local_rollout_offset将本地rollout映射到累计训练步，即global_step=(offset+local_rollout+1)*2048。比较曲线应标出中断和optimizer/episode重置，不能将这个阶段当原连续训练。

续跑TensorBoard脚本默认6008，当前推荐SIGN_TENSORBOARD_PORT=6009与本地16009独立入口，复用既有启动/复用/信号清理实现；未启动或资源排队的run目录可暂不存在，出现事件后自动读取，原6006/6007入口保留。用户本地命令：

```bash
ssh -t -o ExitOnForwardFailure=yes -o ServerAliveInterval=30 -o ServerAliveCountMax=3 \
  -L 127.0.0.1:16009:127.0.0.1:6009 e1538633@vanda.nus.edu.sg \
  'SIGN_TENSORBOARD_PORT=6009 bash /scratch/e1538633/liuyi/logs/training_continuation_20261103/view_tensorboard.sh'
```

本地浏览器http://127.0.0.1:16009，需保持SSH连接。服务按当前SSH所在登录节点启动/核验复用；本批次没有代用户启动TensorBoard服务。


10月31日中断前指标的只读复核：从liuyi执行`envs/sign-baseline/bin/python logs/training_stop_20261031/extract.py`，每次生成独立readout_实际时间戳。工具只读原六停止训练目录；核对10月31日00:53固定快照的字节SHA前缀，按TFRecord边界提取停止前追加尾段并解析末点与最后1M原生滑窗均值。report.json另存实际事件时间、PBS退出时间、checkpoint步数、未落盘差额、reward/loss/碰撞/覆盖/bonus与来源SHA；不会读取SIGN-continue-*或启动模型/评估/作业。原生末点、区间均值与完整验证成绩分开使用，源文件缺失或前缀变化即拒绝拼接。


11月3日原训练同步数比较：`envs/sign-baseline/bin/python logs/matched_training_20261103/compare.py`只读拼接10月31日00:53归档selected CSV与中断前新增尾段CSV；七组旧CSV前缀的SHA对已发布输入清单校验，重合step必须同值。旧三方法统一截断到coverage32终点48,377,856，全部Qwen/覆盖/基线统一截断到A终点8,536,064；组内SR/SPL step数组必须完全相同。输出每组近1M/5M均值、源SHA/区间/点数、CSV与PNG/PDF，曲线101-update平滑仅展示，不参与均值。基线与两覆盖或Qwen不可拿各自末点混比，也不把重置optimizer后的继续训练拼成原连续轨迹。


## 2026-11-03：最新覆盖权重完整val及评估后的训练恢复

支持目录`logs/gibson_coverage_latest_eval_20261103`。manifest.json固定选择时最新正式checkpoint步数/源路径/SHA；复制权重只存服务器，不发布。guard.py复核原七树与四continue树的HEAD/源码、模型/数据、评估脚本和输入SHA，评估前后均调用。运行期间勿编辑受保护脚本；后续训练出现新checkpoint不替换正在评估的快照。

每组4200条/14场景、6环境/max500/seed100/hash0，与此前原生SIGN-coverage-eval协议相同；被动覆盖0.1m/3m/90°、weight0、无Qwen。evaluate.py复用已验证录数器，检查4200唯一任务集及所有指标有限，交叉核对native TB与逐episode SR/SPL；summarize.py另核对两组目标/起点完全相同，报告训练步数不同。结果是各组result.json和总summary.json；全局面积/总动作与逐episode面积/动作均值分别保存。

有效提交回执以priority_submission.json为准：1511395覆盖256→1511396覆盖32（afterany），均CFP/autox各2h/1A40/36CPU240GB。evaluate.pbs文件本身保留首次personal/auto默认值，**实际共享提交通过-q autox -P CFP04-SF-109覆盖**，应读回执/qstat有效参数，不能仅看PBS头推断。原个人1511374/1511375/1511376未运行已取消。hpc project当前要求amgr登录，不能据这些提交声称已知精确剩余额度。

状态查询（已执行同类核验；以下供后续查询）：

```bash
qstat -fx 1511395 1511396 1511409 1511410 1511411
```

1511409为CPU afterany:1511396，finish_priority.py只释放1511147/1511148的临时u挂起，重试/超时并写released_training_holds.json；不修改其他作业，已用mock验证目标集合及F状态跳过。1511410为C恢复GPU作业，也afterany:1511396，resume_C.py校验旧C已F和22,528,000步checkpoint SHA，命令与此前C完全相同、仅改--model-dir。独立新输出`SIGN-continue-ablation/results/continuation_20261103/C/train_after_latest_eval`，TensorBoard是其tb；viewer脚本已于11月3日修正C为此新路径，建议使用独立6009/本地16009启动，旧6008进程保留；只看最新续跑阶段，排队组无事件时暂不显示。不得把新事件写进旧C目录。C剩余126:41:13=127:34:33−00:53:20；旧权重无optimizer，明确记录再次重置。1511411仅afterok两评估成功才运行CPU汇总；评估失败不阻塞训练恢复。

若清理CPU作业失败，先检查其日志/released_training_holds.json及两个评估均已F，再对照priority_submission.json手动执行`qrls -h u 1511147 1511148`（仅故障恢复参考，当前未执行）。不要因H(d)等待而手动绕过评估。恢复GPU排队不是恢复已完成；依赖/运行结果须用qstat复核。

完成记录：11月3日两GPU评估、CPU清理及汇总均Exit0，C1511410已03:51开始R，临时挂起解除回执已实际产生。完整成绩summary.json与逐组result.json；results_review.json为09:36从8400条原JSONL独立复算7项指标/唯一任务/目标与初始位置/有限性及作业状态的审计，并保存输入SHA和相较18.944M各自旧成绩的变化。报告探索效率时标明全局sum(area)/sum(actions)或逐episode比值均值，不能互换；两组训练步数125.952M/48.128M不同，不能据当前结果作同步数算法优劣或冗余探索因果判断。查看结果不需要重新运行summarize.py或提交PBS。


## 2026-11-03：最终冻结基线74.240M完整验证

支持目录`logs/gibson_baseline_final_eval_20261103`。从1496716停训备份复制不可变baseline.pth，真实extra_state.step=74240000、SHA与preservation.json一致；checkpoint_audit.json保存103项有限性/42项公开encoder相同的CPU核验。不要以训练末步74,653,696替代评估权重步数。

evaluate.py仅在最新两覆盖的已验证脚本中将允许case改为baseline，原native evaluator、recording_env.py、eval_protocol.json保持同协议；guard.py/source_manifest.json固定原11树与资产、备份输入以及已完成两覆盖结果/逐episode记录的SHA。4200val/14场景、6环境/max500/seed100/hash0、同public safety、0.1m/3m/90°被动coverage weight0、无Qwen，输出baseline/result.json、episodes及native/tb。源脚本/数据守卫在前后调用，完整有限性/任务集及native-TB SR/SPL交叉核对通过才写结果。

实际已提交（以下为历史执行记录，勿重复qsub）：

```bash
qsub -o /scratch/e1538633/liuyi/logs/gibson_baseline_final_eval_20261103/baseline/evaluate.pbs.log \
  -v EVAL_CASE=baseline /scratch/e1538633/liuyi/logs/gibson_baseline_final_eval_20261103/evaluate.pbs
```

作业1515117，CFP04-SF-109/auto→batch_gpu、1A40/36CPU240GB/2h；GPUx四个训练已占满每用户4个上限，故本次使用独立普通GPU队列，保留现有训练。CPU汇总1515118 afterok:1515117，仅核对最终基线与此前两覆盖4200任务/目标图/起点后写本目录comparison.json，旧summary/result不修改。不同训练步数74.240/125.952/48.128M须显式标注。PBS状态查询用`qstat -fx -F json 1515117 1515118`；列举个人活跃作业优先qselect -u e1538633取得ID再qstat -f -F json，当前qstat -u与-f/-F混用可能返回普通表格，不能直接作JSON解析。


## 2026-11-05：当前六组续跑指标只读入口

运行`envs/sign-baseline/bin/python logs/training_readout_20261105/continuation_readout.py`，复用旧固定字节快照/TFRecord尾裁剪/JSONL尾裁剪逻辑，新增实际已运行的coverage32和B，C仍用train_after_latest_eval。它只读取六组实际TB/ledger，写独立snapshot_HHMMSS，核对有限性、连续ID、nav_rewards/masks与奖励守恒；不加载GPU/模型、不改训练/作业、不打包。

累计步数按continuation offset映射，日志均值按(lower,end]选窗口，原生50-update重叠点不当独立样本。三Qwen共同预算取A/B/qwen01最新步数最小值；固定原始baseline/两coverage/C参考需覆盖该终点，超过参考范围应选择有证据的续跑区间，不绕过断言。当前snapshot_004537另保存matched_windows.json，逐项核对1M/2M/3M的SR-SPL步数数组一致与七个CSV SHA。

六组顺序读文件，批次captured_at只是开始时间，后来组的事件可能晚于它。按每组实际快照时间或event_readout_at检查新鲜度；不能把相对批次起点的负时间差当时钟或停训异常。本批readout.json保留batch_start_minus_event_seconds并按冻结事件mtime记录年龄；旧脚本的四组/两排队假设仅作历史，不用于当前总览。

## 2026-11-03：续跑阶段训练指标只读检查

从liuyi执行`envs/sign-baseline/bin/python logs/training_readout_20261103/continuation_readout.py`。每次写独立snapshot_HHMMSS；只读四正在运行的continue输出，C固定使用train_after_latest_eval，排队两组引用已固定10月31日末段报告，不把无TB当0或拼入已终止第一轮C。TensorBoard固定字节前缀裁到完整TFRecord、ledger裁到完整JSONL并保存SHA；分别提取最新/近1M/前1M日志均值和最近3h实际秒/2048步。原生50-update滑窗点相互关联，不视为独立统计样本。

Qwen/几何ledger必须用continuation.json的qwen_local_rollout_offset映射累计步数：global_step=(offset+local_rollout_id+1)*2048；按TB快照终点截取，检查连续ID、nav_rewards/masks及bonus守恒。0.1m旧覆盖/全部动作与0.025m有效动作面积口径分开，C无worker/render。脚本不加载模型、不调用GPU、不改PBS或源文件。

共同预算参考只取两运行Qwen都已达到的终点及最近1M，历史基线/两旧覆盖/C从已有固定CSV读取；均值前逐项核对SR/SPL step相同。明确标记Qwen已重置optimizer/episodes、参考区间仍为原训练，不能把该表称纯奖励控制实验或与原连续训练等价。当前脚本要求两Qwen本轮已运行至少2M、共同预算仍落在10月31日固定历史CSV范围内，超出时应更换明确来源，不绕过断言或盲目拼接。作者默认步数依据本地原始dad87fe的Gibson YAML读取，3e8为全部环境累计；当前8×256每轮2048，原300M累计cap继续有效。


<a id="tensorboard-full-history"></a>
## TensorBoard全部训练历史入口

同一个view_tensorboard.sh支持`SIGN_TENSORBOARD_HISTORY=1`，读取plan.json复用六组原训练路径，再加冻结基线原始历史、六续跑路径和C已停止第一轮续跑，共14个有明确阶段名的run。原始七组从最初训练步数开始；新阶段使用真实累计step，不修改原事件或合并重置前后数据。`original`、`continue_latest`、`C_geometry128/continue_1_stopped`分别显示，checkpoint回退导致的重叠步数保留阶段归属。两排队组当前没有新续跑事件，但原历史曲线正常存在。

在本地执行以下命令，再打开http://127.0.0.1:16200，保持SSH终端连接：

```bash
ssh -t -o ExitOnForwardFailure=yes -o ServerAliveInterval=30 -o ServerAliveCountMax=3 \
  -L 127.0.0.1:16200:127.0.0.1:6200 e1538633@vanda.nus.edu.sg \
  'SIGN_TENSORBOARD_HISTORY=1 SIGN_TENSORBOARD_PORT=6200 bash /scratch/e1538633/liuyi/logs/training_continuation_20261103/view_tensorboard.sh'
```

横轴选Step，按方法勾选original和continue阶段，主要看metrics/success、metrics/spl；reward仍是导航奖励。

11月3日实测：全历史首次读取可超过15分钟，网页就绪不代表14组事件已全部载入。初版original排在continued之前，后端先出现原训练，续训虽然已有更新文件却稍后才在Runs出现；已改为续训优先、保留相同14个命名路径，复用校验忽略顺序。修改仅在下次启动新网页进程时生效，已有会话可以继续等待和刷新，不需要为查看首次加载反复重启。网页Runs筛选框输入continue_latest并勾选已有条目，横轴用Step。coverage32/B若仍Q且tb无事件，不会产生continue曲线；有原训练历史不等于已开始续跑。证据logs/training_continuation_20261103/full_history_load_diagnosis_20261103.json。

首次加载完整历史可能需要几分钟。该入口独立6200，与仅续跑的6009及已有6006/6007不冲突；6009会话无需停止。路径/语法核验及当时端口探针见logs/training_continuation_20261103/full_history_viewer_20261103.json；这不代表已经代用户启动或完成HTTP加载测试。默认不设置HISTORY时原六续跑模式保持不变。


## 2026-11-03：按用户要求将两排队训练移至auto

23:03已执行`qmove auto 1511147.stdct-mgmt-02`、`qmove auto 1511148.stdct-mgmt-02`，原覆盖32和B Qwen256β.03从batch_gpux转为auto→batch_gpu，不重复qsub。移动前必须确认实际仍Q；已R的任务不为换队列停止或重提。移动后核对原作业ID、CFP04-SF-109项目、输出路径、依赖、1A40/36CPU240GB和walltime99:28:14/127:34:32不变。当前Q原因从GPUx每用户4运行上限变为普通GPU资源node_pool等待。回执logs/training_continuation_20261103/auto_queue_move_20261103.json包含前后状态及实际qmove命令；不要因默认autox偏好把这两任务改回或另行提交副本。


同预算结论的窗口敏感性复核：logs/training_readout_20261103/qwen_matched_advantage_220651.json固定使用snapshot_220651的A/qwen01 selected CSV和旧baseline/coverage256/coverage32/C固定CSV，以共同step12,910,592为终点，分别选(lower,end]内1M/2M/3M记录，先确认各方法SR/SPL的step数组相同，再算原生日志点均值与百分点差。输入处理前后SHA不变，不能对原生50-update重叠统计做独立样本显著性推断。8.192M验证从各原result.json核对索引一致，和12.911M训练均值分别解释；不要用局部训练优势替代尚无结果的后期验证，也不要忽略optimizer/episode重置及旧/新MRQ/几何规则差异。


<a id="sign-failure-diagnosis"></a>
## SIGN导航失败分析：可核实结束方式与待归因原因

11月4日初次静态CPU审计结果在logs/sign_failure_audit_20261104/snapshot_001350（随后另获Goal授权完成下述全量诊断）。analysis.json保存三组每条episode摘要输入SHA、同native evaluator源文件SHA、分场景及终止桶统计，failed_episodes_for_review.csv为1865条模型-episode失败记录，人工主因/次因/备注均留空；未改记录器、重采样或实施Agent。不能把推断的end_bucket当人工病因标签。

对当前val只筛success=0：steps<500在已核对native continuous STOP/task/get_done链及10000000秒时间上限下，推断为STOP失败；steps=500仅标到限边界，终步也可能STOP，原info/JSONL没保存原因flag。训练上限1000步另算，不与val混用。单次失败的碰撞、轨迹重复、目标未找到可共存，主因标签必须定规则、保留unknown，贡献标签可多选，不强行归一成100%互斥原因。

全量诊断已于11月4日完成采集/分析：支持目录`logs/sign_failure_replay_20261104`，GPU1518132/1518133/1518134、CPU1518137均Exit0。独立wrapper在auto-reset前写全部12600逐步NPZ，失败1865条及每模型42成功对照保存完整视频，共1991视频829982帧。控制smoke1518125验证28条原生结果与完整轨迹/4274帧完全一致；全量另核对11原字段与固定源/权重/目标/起点。索引见STATUS当前Goal和analysis/index.html，不重复qsub已完成采集。

每个NPZ在`full/<case>/diagnostic/traces/<Scene>/<episode>.npz`；case为baseline/coverage256/coverage32。position_xyz单位m、rotation_xyzw；metrics列名在metric_fields；所有逐步数组T+1，第0行为reset状态，command[t]从pose[t-1]执行到pose[t]，第0行动作占位。normalized与物理command均按linear/angular排列，不按Gym平坦向量顺序猜测；STOP核验使用native FP32缩放，避免阈值1.5deg/s附近名义FP64舍入的误报。初始collisions=None只在本地trace行记0，不改info。视频frame0是初始观测、左目标/右RGB，全部T+1帧/10fps；H264/JPEG有损，目标PNG保留原RGB SHA，不能用审查视频逐像素重建Actor输入或GRU状态。

`analysis/analysis.json`为原规则下全量阶段、严格/base/宽松敏感性与成功对照；`episodes.csv/json`含12600条，`failed_episodes.csv`为1865模型×任务失败，`paired_tasks.csv`为4200共同任务、`common_failures.csv`为257三者共同失败。人工主因空，AI笔记17个目的性案例不当比例估计或人工真值。源码事实/未验证Agent假设在code_evidence.json，13单元测试在test_analysis.py。要重算统计仅CPU执行（需原依赖，输出必须新目录）：

```bash
envs/sign-baseline/bin/python logs/sign_failure_replay_20261104/analyze.py --out /scratch/e1538633/liuyi/logs/sign_failure_replay_20261104/analysis_recomputed_NEW
envs/sign-baseline/bin/python -m unittest discover -s logs/sign_failure_replay_20261104 -p test_analysis.py
```

上两命令为复现参考，不自动重跑；重算含1991视频解码检查，较长CPU任务按analyze.pbs资源提交。现有report.py/package.py针对固定analysis目录；首次已生成的ZIP不覆盖，保留结果后另建输出批次。evaluate.py有已存在native输出保护，原PBS/路径/权重/manifest均为历史固定输入，不能当待执行新实验。

0.1m/3m/90°覆盖是XZ地面视域代理，粗栅格位置无效会使fog从起点退出；新增面积0不能直接当0新RGB信息。只审计高度变化≤mpp且保存地图一致的投影，其他中间高度图未知；没有逐步is_navigable，不能由2D格判断真实navmesh不可达。保留原指标，不将该补充质量审计伪装成预注册病因标签。GT目标距离/位姿/地图只作诊断与固定轨迹oracle停止上界，未来Agent输入需另定允许观测；原q效率评分不等于到达概率。

停止判据见src/custom_action.py：实际线速度<0.025m/s且角速度绝对值<1.5deg/s即STOP，不能把低速静止简单当无终止的观察动作。Success为STOP且距离<1m；ViewMatch0.5仍为SR成功。失败ViewAngle固定180默认值，不用它推断朝向主因；Qwen geometry_reason也只表示地图奖励统计是否合法。原native policy.act直接给动作，USL_correction定义尚未接在该评估调用链，不能先归因于它过度干预。

基线最终完整val后处理恢复：1515117导航评估Exit0/00:53:18，1515118 CPU汇总Exit1只因PATH缺git。11月4日在登录节点以`envs/sign-baseline/bin/python logs/gibson_baseline_final_eval_20261103/summarize.py`运行原脚本（已执行，勿重复生成当新实验），源SHA/4200任务/目标图/起点核验通过，comparison.json已生成；未修改PBS/guard、未重跑导航GPU，旧失败作业状态保留。其他CPU节点的PATH部署问题尚未改代码修复，后续新作业需显式准备git再调用守卫。


### 全量失败报告：原始文件保留，ZIP按需生成

2026-11-04打包1518613 Exit0，两个ZIP CRC和实际解压后的269本地链接曾核验通过；历史大小/SHA在logs/sign_failure_replay_20261104/package_results.json。**2026-11-05用户要求清理两个ZIP，已删除共1591855136字节，清理回执logs/sign_failure_replay_20261104/zip_cleanup_20261105T004126.json；旧scp下载命令当前不再适用。**

服务器上analysis/index.html、73案例图/精选完整视频、17AI笔记、摘要CSV/JSON、空白人审、源码和full/全部12600 trace与1991视频均保留，根目录为`logs/sign_failure_replay_20261104/`。查看报告或分析原始数据无需先打包。

用户明确需要下载/打包时，再核对原文件与标注、守卫和输出，按既有package.py/package.pbs生成分发包；长CPU操作走PBS。保留旧打包/清理回执，另记本次生成状态，不根据旧下载链接自动补包；不为重新打包重跑GPU采集或导航训练。


<a id="coverage256-peak-eval-20261105"></a>
## 覆盖256训练峰值附近完整val（2026-11-05）

入口logs/gibson_coverage256_peak_eval_20261105，原生只读SIGN-coverage-eval @a7cc9e0不变；evaluate/recording复用11月3日完整验证字节。目标日志146,759,680无保存点，ckpt.39/40分别146,432,000/146,944,000，选择最近ckpt.40并复制到本批checkpoints/coverage256_146944000.pth，核对extra_state.step与SHA。不要从ckpt文件编号猜累计步数：续跑目录编号从0重新开始。

已执行qsub -o /scratch/e1538633/liuyi/logs/gibson_coverage256_peak_eval_20261105/coverage256/evaluate.pbs.log /scratch/e1538633/liuyi/logs/gibson_coverage256_peak_eval_20261105/evaluate.pbs，作业1520910。CFP04-SF-109/auto→batch_gpu/1A40/36CPU240GB/2h。GPUx用户4/4已满，普通GPU提交前2/4，因此原六训练不暂停。hpc project仍需amgr登录，未声称精确额度。

查状态参考（不要重复提交）：qstat -fx 1520910.stdct-mgmt-02。原生4200/14场景/6环境/max500/seed100/hash0，0.1m/3m/90°仅被动观测，weight0，无Qwen。任务结束同PBS内自动运行summarize.py，核对与11月3日baseline及coverage256完整val的任务、目标与起点，生成comparison.json；不同训练步数分开标注。提交时参数与输出以manifest.json/submission.json为准，running_status.json仅为当时运行快照；当前完成状态见completed_qstat.json与results_review.json。失败重试不得覆写已有native目录，应先留存错误与新建attempt输出。

本批已于11月5日02:14:08完成（1520910 F/Exit0，55分02秒），实际146944000步，SR86.35714%、SPL56.23546%，3627/4200。comparison.json自动核对通过后，results_review.json又按原始JSONL重算三组4200任务/目标图/起点、均值和源SHA，guard通过。相对125952000步SR−1.2143pp／SPL+2.9359pp；相对74240000冻结基线+1.3810／+1.8419pp。不同训练步数，且146759680精确峰值权重不可得；本轮未重跑GPU、打包或变更训练。

覆盖256候选选择的只读复核证据（11月5日）：logs/training_readout_20261105/coverage256_candidates_20261105T141223/checkpoint_candidates.json保存原训练/续跑完整事件字节前缀SHA、长度及304保存点的近1M/3M窗口；两份selected_scalars.csv固定抽取值。local_neighborhoods.json补保存点本身、前后25万步；recommendations.json列143360000/150528000等实际CPU读取extra_state.step和权重SHA。近1M/3M均为原生50-update滑窗日志的均值，并非独立episode采样；中心窗口含未来日志，仅作回顾上下文，不称当时可用信息。不得把旧目录与续跑目录同编号当同一步，亦不以训练滑窗峰值保证val峰值。本批仅推荐，未qsub。


<a id="coverage256-candidates-eval-20261105"></a>
## 覆盖256两个曲线候选完整val（2026-11-05）

支撑目录logs/gibson_coverage256_candidates_eval_20261105；固定副本143360000与150528000步，来源分别续跑目录ckpt.33和.47，原生SIGN-coverage-eval @a7cc9e0只读。evaluate.py沿用上批仅更改允许EVAL_CASE，recording_env.py/eval_protocol.json逐字节复用；脚本、协议与两权重由source_manifest冻结，训练树不切换或修改。

已执行两个qsub（勿重复提交）：143.360M作业1523189、150.528M作业1523190。命令完整参数见submission.json：同一evaluate.pbs，以-v EVAL_CASE=coverage143360000或coverage150528000选择固定输入，分别-o到各输出目录。CFP04-SF-109/auto→batch_gpu，每份1A40/36CPU240GB/2h，原协议4200/14场景/6env/max500/seed100/hash0。被动覆盖0.1m/3m/90°/weight0、无Qwen。GPU相互无依赖，允许并行，排队不停止现有六训练。提交后Q原因node_pool，不是个人4运行上限（普通GPU原2/4、GPUx4/4）。

CPU1523191已提交afterok:1523189:1523190，auto→batch_cpu/1CPU实际6GB/10min，含git模块以避免旧PATH问题。其H是正常依赖，不能qrls绕过真实checkpoint/result依赖。两份成功后自动生成comparison.json，核对五组各4200任务/目标/起点及源结果SHA；参考原125.952/146.944M覆盖及74.240M基线，不重跑参考组、不称同步数因果对照。

查状态参考：qstat -fx 1523189 1523190 1523191。submission_status.json/current_status.json为各自时点状态，完结后核验最终Exit_status和4200个唯一任务；不得覆写旧native结果、另建attempt后才能重试。单份实际运行参考上一批55分钟，排队另计。


<a id="training-readout-20261105-afternoon"></a>
## 11月5日下午：当前六组Qwen训练与同步数读取

当前CPU入口logs/training_readout_20261105/continuation_readout_v2.py，已执行snapshot_150755。训练/环境/队列不改；固定完整TFRecord字节前缀、JSONL末完整行与SHA，在内存解析protobuf，原始冻结事件/ledger及运行时代码保留。snapshot_150000旧CPU读取已主动中断，只有部分每组输出，没有有效总readout；attempt_status.json明确原因，勿引用为完成结果。旧script保持原样。

v2补读PLAN['C']['old_output']/tb完整几何128原日志，冻结historical_C_selected_scalars.csv至22,587,392步；旧10月31日snapshot_005043的C只有18,020,352步，不足当前共同19,486,720。参考可用性改按实际抽取数组范围核对，不根据旧meta或用C最新曲线替换历史步数。若未来共同步数超过22,587,392，当前v2会报范围断言，需先显式处理正确C阶段来源，不可悄悄跨reset拼接。

training_comparison.json按共同19,486,720和各自A/B/qwen01当前步数分别输出近1M/2M/3M，比较前确认每个SR/SPL step数组完全一致；所有正负结果保留。运行本入口只需sign-baseline CPU Python、PYTHONDONTWRITEBYTECODE=1、PYTHONNOUSERSITE=1、OMP/MKL/OPENBLAS线程1；GPU计算仍只在PBS。原生50-update窗口互相重叠，不当独立episode统计，Qwen训练reward日志仍只导航reward。validation.json保存15输入来源/断言与C完整范围。

截至本批，六训练均R；当前Qwen128 β.1短窗口SR恢复且胜旧coverage两指标，但3M未全面胜coverage32；A/B未显示稳定训练优势。具体数字与budget见STATUS新下午索引，凌晨snapshot_004537保留为历史，不能混称最新。


<a id="training-readout-20261107"></a>
## 11月7日最新读取：增量事件与共同预算超过原C末步的处理

当前CPU入口logs/training_readout_20261107/readout.py；已执行snapshot_130555。复用11月5日snapshot_150755的冻结CSV和完整事件边界，重新SHA验证原文件旧前缀未变，然后从已知TFRecord边界读新增字节，截掉最后不完整记录；在内存解析，不重新复制全部事件。记录每源旧prefix长度/SHA、新tail偏移/长度/SHA，导出当前CSV与近3M ledger；原始源保持原位。validation.json对导出1M/3M独立复算，保存之前/当前CSV SHA。此入口不依赖GPU。

新readout内共同与各自Qwen预算的1M/2M/3M比较先逐点核对SR/SPL step数组。当前共同29,427,712已超过原C末步22,587,392，因此只在整个比较窗位于C实际续跑时才显式加入C_continuation；本批26.428–29.428M满足。不悄悄替换C当前末点，不跨reset拼接，不再执行旧v2的原C范围断言。其余参考仍用原baseline/两coverage冻结CSV，若未来超出其范围同样须先补证据。

覆盖2561511146在11月5日21:45:20 walltime结束、Exit−29；TB172599296，最后ckpt.90实际172544000，元数据/参数有限性与SHA见coverage256_last_checkpoint.json。其余5任务仍R，原预算不自动延长或另起168h；当前剩余约14–42h。

两候选验证1523189/1523190及CPU1523191已全F/Exit0；自动comparison.json与11月7日results_review_20261107.json独立复核通过五组各4200 task/goal/start和汇总值。143.360M86.52/52.15%、150.528M86.33/51.77%，均未超125.952M87.57/53.30%；这四份coverage256完整val中SR最好125.952M、SPL最好146.944M56.24%。无需重复提交CPU汇总或GPU评估；旧Q/R/H状态文件只是历史回执。


<a id="qwen-selected-eval-20261107"></a>
## 三Qwen曲线选点完整val（2026-11-07）

支撑目录logs/qwen_three_checkpoint_eval_20261107，候选统计来自13:06冻结CSV，selection/candidates.json记录125保存点和来源SHA，selection/selected.json记录人工判断与窗口。选择β.1续跑ckpt.22=20480000、A ckpt.54=36352000、B ckpt.40=29696000；checkpoint_validation.json记录CPU实读step、103 key/shape兼容、有限性、42 encoder冻结项一致和独立副本SHA。切勿按文件编号猜跨目录累计步数。

已执行三次qsub，同一个evaluate.pbs，以-v EVAL_CASE选择固定输入、-q覆盖实际队列、-o独立日志：A1528937 -q autox，qwen011528938 -q auto，B1528939 -q auto。默认PBS头为autox，但后两份实际batch_gpu，必须看submission/current_status与实际qstat。CFP04-SF-109，各1A40/36CPU240GB/2h，三者相互无依赖，13:20均R；GPUx原3/4和普通GPU原2/4有名额，未停原五训练。

评估完全复用SIGN-coverage-eval @a7cc9e0原生导航；旧wrapper/eval_protocol逐字节一致，evaluate.py只改允许的case名称。加载完整已训练actor/critic状态，eval.use_ckpt_config=False使用原eval协议，不调用qwen35、不启动VLM worker或Qwen轨迹/图片收集。4200/14场景/6env/max500/seed100/hash0，原public safety；0.1m/3m/90°被动面积/weight0。三组选点预算不同，旧参考也不同，不当共同预算消融。

CPU1528940已afterok:1528937:1528938:1528939，实际1CPU/6GB/10min；其H只是正常依赖。成功后生成comparison.json与comparison.csv并核对七组4200 task/goals/starts：三新Qwen及既有baseline74.240M、cov256125.952/146.944M、cov3248.128M，不重复GPU参考组。新增支持脚本/参数/权重和11保护树/资产有SHA守卫，Python语法、bash -n及源守卫已过preflight。

查状态参考（不要重提）：qstat -fx 1528937 1528938 1528939 1528940。输出各case/result.json、episodes/*.jsonl与native/tb，汇总待真实结果完成；失败不能覆写已存在native目录，保留失败后另建attempt。


覆盖256125952000训练参考（11月7日核验）：logs/training_readout_20261107/coverage256_125952000_training_reference.json固定原始全段CSV SHA并核对恰有同一步事件。保存点事件2026-10-31T08:49:54+08:00，原生50-update窗口SR82.714057/SPL45.822394%；(124952000,125952000]489点均值86.305267/49.184248%，(122952000,125952000]1465点88.232246/50.713232%。不是完整训练集离线评估；完整4200val87.571429/53.299601%来自已有result.json。训练reward日志不含探索bonus。


<a id="coverage32-selected-eval-20261107"></a>
## 覆盖32三个选点完整val（2026-11-07）

支撑目录logs/gibson_coverage32_selected_eval_20261107。用11月7日13:06冻结CSV和已知事件边界增量补覆盖32至158801920，旧两段SHA验证、保存CSV和新字节偏移/长度/SHA于selection/candidates.json，共211保存点。选择76.288M续跑ckpt.54、125.952M ckpt.151、151.040M ckpt.200，具体理由/训练窗在selection/selected.json；中间点是相同步数参考，续跑历史不同不当纯算法因果对照。所有模型CPU实读step、103键形状/有限性和42 encoder相同验证见checkpoint_validation.json。

已实际qsub（勿重提）：125952000→1528994 -q autox，76288000→1528995 -q auto，151040000→1528996 -q auto。共同evaluate.pbs用-v EVAL_CASE=coverage32_<step>和各目录-o选择固定输入，完整命令在submission.json；CFP04-SF-109，每份1A40/36CPU240GB/2h。当前两GPU队列用户运行名额各4/4，三新Q明确为运行上限，保留五训练和三Qwen验证，不为加速新任务中止原作业或移动已R任务。

Native SIGN-coverage-eval @a7cc9e0、4200/14场景/6env/max500/seed100/hash0、原public safety；eval不用训练checkpoint配置，coverage bonus0，0.1m/3m/90°仅被动代理，不启Qwen。复用evaluator只改case断言、录数wrapper和protocol逐字节同既有完整val；输入/模型/11保护树/支持脚本有SHA守卫，Python compile/bash -n/guard通过preflight。

CPU1528997 afterok:1528994:1528995:1528996，1CPU/6GB/10min，H正常依赖不可解除绕过。三成功后自动生成comparison.json/CSV并核对七组4200 task/goal/start，与既有coverage3248.128M、coverage256125.952/146.944M及baseline74.240M对照。除125.952M参考以外各组预算不同，参考组不重复GPU评估。qstat -fx 1528994 1528995 1528996 1528997仅为查询参考，不能据旧Q状态自动重复qsub。失败留存输出后另建attempt，不能覆写native目录。


<a id="github-publication-20261107"></a>
## 11月7日资料增量发布流程

本批明确基点333b2aeb0903515c97a5b8a416bb3025a34518c3，独立SIGN-qwen-ablation-publication detached树，目标origin=git@github.com:yiichu03/SIGN.git的phase2/qwen-beta003-geometry128。四个continue-*源码分支已ls-remote核对与运行commit一致；资料提交不进入运行目录。已有worktree干净，旧manifest和WORKLOG前缀匹配后，使用logs/github_publication_20261107/publish_update.py构建新docs/experiments/qwen128-reward/ablations/progress_20261107，更新既有四根文档生成副本与导航。

先--capture-only冻结PBS截面/已完成新评估/代码远端SHA，之后--tree SIGN-qwen-ablation-publication在独立staging里构建并核验，成功后仅安装README/docs变化；--check-only为本地或GitHub克隆的离线CPU核验，不依赖模型和GPU。脚本检查来源SHA/gzip、WORKLOG旧前缀、相对链接、已完成4200任务结果重算/配对、文件大小、敏感凭据形状和运行代码不变；旧日期输入和代码快照保留原位。此前的旧publish_readout.py仅--check-only复核，不重新运行其固定日期构建。

新包含11月3日续跑/原训练尾段与共同预算、11月5/7日训练窗口、已完成完整val、新选点提交、全量失败诊断的报告/统计/选中案例图像和复现代码。65MB episodes JSON按文件确定性gzip，完整视频/RGB原始序列、checkpoint、TB二进制、场景/环境不上传。失败HTML生成明确去视频的资料版，原HTML另存.server.html，不能冒称相机证据全在GitHub。rootWORKLOG逐字节前缀保留、仅追加；其他根文档按映射转换本地证据链接或标记服务器来源。

构建后需git diff --check、git diff --cached --check，核对只有README/docs；普通push HEAD到origin上述分支，绝不force或修改本地运行HEAD。最后ls-remote核对SHA，回执追加服务器WORKLOG，不为包含推送回执循环生成新提交。


### 11月7日推送连接恢复（已实际验证）

本次agent转发无响应：ssh-add -l、默认SSH认证超时；最初push没有上传完成。HTTPS直接dry-run无凭据而退出128；给remote.origin.pushurl追加-c值不会取代原有多值push URL，因此第一次HTTPS尝试仍先等待SSH。没有改变永久Git/SSH配置。

现有本机id_ed25519通过关闭IdentityAgent独立认证为yiichu03，随后使用仅该命令生效的GIT_SSH_COMMAND完成普通push，最终f00c15c远端核对通过：

```bash
GIT_SSH_COMMAND='ssh -o IdentityAgent=none -o IdentitiesOnly=yes -o BatchMode=yes -o ConnectTimeout=20 -i /home/svu/e1538633/.ssh/id_ed25519' \
  git -C /scratch/e1538633/liuyi/SIGN-qwen-ablation-publication \
  push origin HEAD:refs/heads/phase2/qwen-beta003-geometry128
```

这仅是本机已有授权密钥的连接恢复，不复制密钥或更改默认推送仓库；后续先核对目标/HEAD。日志与回执在logs/github_publication_20261107。原CSV CRLF/原生YAML/源码快照空白按42个原字节SHA保留例外，其他暂存内容严格git diff --cached --check通过，不做全局忽略。


<a id="inference-recovery-20261107"></a>
## 推理恢复Harness：独立分支与验证入口

源码工作树SIGN-inference-harness / phase2/inference-recovery-harness，固定5e3b0d0（yiichu03远端一致），由453179c建立；大纲docs/experiments/inference-recovery/PLAN.md。原policy/网络/动作/传感器/训练方法保持，仅_eval_checkpoint接入RGB/实际动作历史监督。实际Gym动作排序角速在前，按命名字段映射canonical线/角并核对环境收到的动作SHA；真实reset/masks/GRU和500步预算不变。Qwen复用SingleImageJudge和常驻运输类，FP32/ABC/T1，A左/B右/C继续，禁止将旧ordinal q作为恢复质量或奖励。

支撑目录logs/sign_inference_harness_20261107，smoke28/pilot280清单tasks.json在看到新结果之前固定，pilot排除旧review与smoke。1530277环境注册Exit1、1530280部分集与旧全量严格比较Exit1的证据不覆盖；retry2源码/输入manifest固定，1530286先autox后因Q/node_pool用qmove auto，ID/项目/输出/2h不变。只动新验证，没有移动或停止原训练。相同任务的过滤子集与旧4200输出并不保证相同，本次28条goal/start同而3条SR不同，机制未作因果确认；技术门改为同子集原生参考/off/零干预精确比较，未放宽这项等价门。完整4200仍另核查旧参考。

CPU1530290以afterany等待验证作业，先检查Exit0/质量门/源版本/逐条数据/真实ABC softmax/图片SHA/实际动作反馈，再判断两组实际恢复均>0；通过才调用submit_revision.py --full（6h/1A40/CFP/autox），并为full附CPU报告依赖。失败、无实际干预、资源或源码guard拒绝时不自动重复GPU，只在pilot_dispatch.json及WORKLOG追加原因。调度四脚本SHA在orchestration_manifest.json，运行期间勿修改。它是技术/明显回归筛查，不是统计显著性证明。

查询（已提交作业，不要重复qsub）：

```bash
qstat -fx 1530286 1530290
cat /scratch/e1538633/liuyi/logs/sign_inference_harness_20261107/retry2/pilot_dispatch.json
# 自动完整评估实际提交后才有以下回执：
cat /scratch/e1538633/liuyi/logs/sign_inference_harness_20261107/retry2/full_submission.json
```

输出retry2/pilot/{smoke_native,smoke_off,smoke_disabled,smoke_rule,smoke_qwen,pilot_off,pilot_rule,pilot_qwen}，worker_probe核对不同尺寸RGB请求的padding/真实token/batch/solo/生成logits；pilot_review包含逐场景/配对救回误伤和人审空白字段。完整验证若提交位于retry2/full。0.1m/3m/90°仅被动录数，无探索bonus或导航训练。不打包ZIP。33原型/旧接口CPU测试及5自动调度门测试通过，GPU验证最终状态必须查actual回执，不能把提交当通过。


推理Harness排队更新（2026-11-07T22:52:04+08:00）：普通GPU等待超过四小时，1530286仍Q/node_pool；当时batch_gpu 67Q、GPUx仅1Q且本用户GPUx3/4，因此22:51实际qmove autox 1530286，保留ID/项目/2h预算/输出/CPU依赖，不停止原训练或重提。实际回执retry2/queue_move_to_autox_20261107T225140.json；当前状态看retry2/current_status.json，不据队列切换承诺立即获GPU。


<a id="inference-active-view-20261108"></a>
## 规则完整验证与Qwen主动视野诊断

规则完整4200是用户新授权独立1530887，不修改旧自动gate；SIGN-inference-harness固定5e3b0d0，输出logs/sign_inference_rule_full_20261107，旧无扫描规则每事件最多10动作、总20。evaluate.pbs后调用finish_rule.py，核对4200任务/目标/起点/动作SHA、native指标、配对救回/误伤及无直接干预变化；comparison.json不把所有变化因果归给恢复。

Qwen新源SIGN-inference-active-view固定1ec9a17，同名phase2/inference-recovery-active-view已push yiichu03。run_active_recovery.py执行34条同输入native/off/零次精确门→scan采图→FP32真实ABC离线两prompt/标签置换/合成镜像诊断→若非全C再新280四控制组，不自动全量。不能因全C去硬改标签/阈值或用扫描步数作为模型贡献。开发GT位姿仅audit_traces离线核对12动作无平移、左右/回中45/−45/0，不在controller输入；实际输入保留PNG/rawviews/prompt/SHA/logits。扫描12步加可选5恢复、两次34计原500，STOP保持。

1530921已提交autox/CFP04-SF-109，1A40/36CPU240GB/2h，source_manifest守护62文件/22资产/旧规则树及11原运行树，运行期间勿改工作树或batch脚本。新34/280任务于prepare_active_recovery.py一次性生成，不能重跑覆盖；datasets固定SHA，旧案例仅开发，确认排除旧smoke/pilot/review，不是独立新benchmark。

查询现有作业（仅查询，不重复提交）：

```bash
qstat -fx 1530887 1530921
cat /scratch/e1538633/liuyi/logs/sign_inference_rule_full_20261107/comparison.json
cat /scratch/e1538633/liuyi/logs/sign_inference_active_view_20261108/attempt1/diagnosis.json
cat /scratch/e1538633/liuyi/logs/sign_inference_active_view_20261108/attempt1/comparison.json
```

后两者按实际分支生成之一；尚未开始/未完成时文件不存在。四控制比较包含per_scene.csv与paired_tasks.csv（人审留空），须同时看Qwen相对scan-only/scan-rule的SR/SPL、扫描/选择步数/调用和耗时，不用单纯AB率评优。具体已执行命令见各submission.json；无导航训练/9B/ZIP。


<a id="inference-coverage256-correct-base-20261108"></a>
## 覆盖256上的恢复框架：底座纠正与核对

当前新源SIGN-inference-coverage256 @96f7783（phase2/inference-coverage256-recovery），继承1ec9a17的控制器/worker且字节不变，eval改为读tasks.checkpoint和tasks.reference，recovery_checkpoint.py核对实际step/模型SHA/cached checkpoint step/SHA/原完整4200身份。新结果存checkpoint路径/SHA/step，不用泛称SIGN基线隐藏模型。正确目标是logs/gibson_coverage_latest_eval_20261103/checkpoints/coverage256.pth，125952000步/SHA988c9ecc...，cached目录同批coverage256，原SR87.571429/SPL53.299601%。

两新作业已提交，不重复qsub：1531082=rule_full（3h，34精确门→fresh完整off严格复现cached→完整rule），1531083=qwen_active（2h，34→真实ABC→若非全C则280四组）。均CFP/autox/1A40，参数与命令在logs/sign_inference_coverage256_20261108/{rule_full,qwen_active}/submission.json，source_manifest固定66个源文件和资产/旧树；Q/R期间不改源码HEAD或脚本。以实际manifest文件数为准。输出comparison.json或Qwen诊断停止时diagnosis.json；不能把旧74.240M比较改名为覆盖256结果。

```bash
qstat -fx 1531082 1531083
cat /scratch/e1538633/liuyi/logs/sign_inference_coverage256_20261108/rule_full/comparison.json
cat /scratch/e1538633/liuyi/logs/sign_inference_coverage256_20261108/qwen_active/diagnosis.json
cat /scratch/e1538633/liuyi/logs/sign_inference_coverage256_20261108/qwen_active/comparison.json
```

错误底座尚Q的1530921已qdel，旧1ec9a17/attempt1保留；1530887原规则已运行较久，保留为74.240M补充。按用户随后授权已qdel几何1281511410，末完整ckpt.115/latest81.920M，控制台82.186240M，完整保留日志/learner_state；没有自动恢复作业。停止回执geometry128_stop.json记录剩余原预算背景，不把释放并发等同精确GPUh余额。


### 11月8日Qwen诊断：区别原始类别与控制器回退

1531083已Exit0，诊断写still_all_C_on_development后按门停止，280未运行。必须同时读offline/scores.json的probabilities、logits和selected_label：平衡prompt7次raw argmax均A（pA0.3953–0.4965），但旧min_probability0.5/min_margin0.1使最终choice全C；不能把该状态概括为模型原始全C。原旧11事件raw C则是另一实验。verify_readout的真实一token生成也回答A，数值读出通过。

置换/镜像summary的action_agreement=1.0使用门控后全C，属于退化一致，不是空间推理或原始方向判断稳健性验证；看raw概率/行动映射及人工复核。completed_review_20261108.json单独澄清，保留原不可变diagnosis、prompt、图和raw。查询本身不触发改门槛或新GPU实验。旧冻结基线full1530887结果也在原目录comparison.json，仅对应74.240M，不能当覆盖256125.952M；正确底座完整off/rule1531082仍以实际完成日志为准。


<a id="qwen-candidate-recovery-20261108"></a>
## Qwen候选通行性与规则回退：首轮执行入口

新独立SIGN-qwen-candidate-recovery固定e9e5c0f，phase2/qwen-candidate-recovery已push yiichu03；73源文件/52资产SHA与旧三源树+原11树守卫。导航底座仍coverage256125.952M，保留6env/max500/seed100/hash0/bonus0，Qwen2B FP32常驻复用原transport/worker/SingleImageJudge。候选图主RGB/目标背景同布局，不将side/ID/步数喂入模型；独立请求batch<=8，ABC是BLOCKED/UNCERTAIN/OPEN，加A/C标签反序，实际概率按语义映回s=p_open+0.5*p_unknown。两顺序相对差>=0.05且OPEN严格最高才选择，不足回退匹配交替规则，门预先冻结，不当脱困概率。

已提交1531403（CFP/autox，1A40/36CPU240GB/2h），请仅查不重复qsub。执行scripts/run_candidate_recovery.py：先diagnose_candidate_recovery复用旧7个真实scan，经同一worker做标准/反序/批单/输入换序/同图/空白/镜像，再34 native/off/零次精确，最后原策略/同扫描规则/Qwen三组各280。镜像只统计双方VLM支持方向，不让规则回退造成假一致；人工字段留空。即使全回退也允许如实跑三组零效果确认，不自动4200或搜prompt。反馈核验/记忆未纳本轮，后续另消融。

```bash
qstat -fx 1531403
cat /scratch/e1538633/liuyi/logs/sign_qwen_candidate_recovery_20261108/attempt1/offline/summary.json
cat /scratch/e1538633/liuyi/logs/sign_qwen_candidate_recovery_20261108/attempt1/technical_gate.json
cat /scratch/e1538633/liuyi/logs/sign_qwen_candidate_recovery_20261108/attempt1/comparison.json
```

实际qsub参数在attempt1/submission.json。未运行/技术失败时后续文件不存在，应查evaluate.pbs.log/offline.log及worker/worker.log，不能把退出或提交当完成。三组单份结果在confirm_{off,rule,qwen}/result.json，模型概率/图/prompt/审计在各native/recovery，VLM选择/回退/与默认不同分别计；回退动作不能算VLM贡献。source与受保护旧树运行期间不改HEAD；资料发布另用detached树。根日志只追加，不自动ZIP。


<a id="qwen-recovery-iteration-20261108"></a>
## 持续迭代Qwen恢复：开发分支与不可变运行快照

新授权允许在phase2/qwen-candidate-recovery提交迭代，作业从各提交的SIGN-qwen-iter-roundXX detached稀疏树运行，source_manifest锁快照/输入/旧源树，开发树HEAD不在运行保护集。submit_iteration.py一次性建立快照、数据链接、manifest并qsub，已提交批次重复调用直接拒绝；round01 f6b28a6/1531565和CPU1531568已结束、未通过额外收益门；round02 f2e266a/1531580已结束且收益门失败；round03 bf52ae7/1531597在空白对照失败；round04开发仍无额外SR收益；round05开发无额外SR收益；round06 6d72ca7/1531624已因prefix0未通过收益门；历史expanded_v2/expanded01=8c52f61/1531631已负向结束，CPU1531632入口错误也已留档纠正；当前固定版本与正式作业见本节末的新入口。不要编辑Q/R快照，也不把新提交pull进去。

一次性选择入口scripts/prepare_recovery_campaign.py已执行，tasks/selection固定develop24/confirm24/reserve24/safety28/general112，选自111原长受阻失败且排除旧开发；勿重跑覆盖。No/Unknown/Yes词概率仍复用class_probabilities，旧ABC默认不变；source word tokens实际No2665/Unknown13394/Yes9175，真实answer边界和读出由probe/worker/verification复核。score是局部视觉支持，不是导航成功概率。

```bash
qstat -fx 1531565 1531568
cat /scratch/e1538633/liuyi/logs/qwen_recovery_iteration_20261108/round01/probe/summary.json
cat /scratch/e1538633/liuyi/logs/qwen_recovery_iteration_20261108/round01/develop_comparison.json
cat /scratch/e1538633/liuyi/logs/qwen_recovery_iteration_20261108/round01/iteration_result.json
cat /scratch/e1538633/liuyi/logs/qwen_recovery_iteration_20261108/round01/dispatch.json
```

开发门通过才自动提交round01_repeat同commit重跑，再confirm/general/safety，独立确认也净正/安全无退才full三组4200；每阶段有CPU afterany（auto/1CPU6GB/15min，无GPU）。任何Exit非0、源/指标/模型/收益门失败只留requires_revision，不自动重复GPU；主agent根据真实错误提交下一轮。控制三个脚本SHA固定orchestration_manifest，不改有待运行依赖的脚本；新控制版本另留记录，勿悄悄覆盖。所有人工cause留空，GT pose仅事后prefix审计，所有scan/recovery计500，STOP/GRU/masks保留。


扩展诊断当前入口：logs/qwen_recovery_iteration_20261108/expanded_v2。原selection/preparation保留，diagnostic_amendment保存1env修订前后tasks SHA；Q/R期间不编辑tasks/selection/三控制脚本/manifest。61来自原24+所有额外37，develop_comparison.json的strata分别报告，不能将它称独立确认或把旧24结果拼接。读取expanded01/submission.json、probe/summary.json、develop_comparison.json、iteration_result.json和dispatch.json。确认/普通/安全也仅小样本诊断1env，full分支自动忽略该项、回原6env；正式4200不是单环境协议。原v1控制链与证据目录不动。


2026-11-08 v2控制入口纠错：CPU1531632调用了旧v1目录，旧三脚本/manifest已归档expanded_v2/control_history_v1；control_revision2保存新SHA，原v1未改。v2 PBS现在强制ITERATION_CONTROL_DIR，首次CPU qsub的-v必须加ITERATION_CONTROL_DIR=/scratch/e1538633/liuyi/logs/qwen_recovery_iteration_20261108/expanded_v2，后续dispatcher自动传自身HERE。全部作业F后CPU手动重审已成功写expanded01/dispatch.json负向回执，未重复GPU。后续控制文件Q/R固定。当前consensus_probe/1531646仅37已保存事件正反问概率；snapshot78da633，scripts/recovery_iteration.pbs stage=probe自动执行原probe --guard；原始输入/两prompt/正反logits/概率/批单和token验证在该目录probe中。离线结果不是导航收益，不能据此直接全量。


提交器revision3：v2 control_history_v2保留旧入口；现在--commit必须完整40位小写SHA，不能用HEAD，且先git cat-file确认所选版本有--profile、再创建snapshot/提交。原因是一次异步commit未等完使expanded02/1531654取旧78da，已在Q时取消无导航，不能复用该batch名。当前expanded03固定f0e093c/1531657，CPU1531662.stdct-mgmt-02显式CONTROL_DIR；三控制脚本manifest Q/R期间不可变。旧14Qwen+74恢复测试/原双问真实概率验证通过；此处为提交器修复时的历史状态，当前61与重复已通过、正式4200见下文。


留出前发布协议v2：expanded_v2/release_protocol_revision2.json是原始时间戳/条件/SHA证据。开发及同提交重复仍须净SR>=1与前缀支持>=1、安全不退；冻结后confirm/general/safety各不得净退，目标确认若中性可提交用户授权的full4200但不声称独立优势。旧自动程序仍执行原正向门，不改其flag/回执；若因中性停止，用单独审计引用预登记并重算所有原始结果后再人工full，不改旧文件。确认负向不可按v2放行，若调参该确认永久降开发。


<a id="qwen-recovery-frozen-full-20261108"></a>
## 固定Qwen恢复版本与正式4200：2026-11-08

12:52后完成复核：1532001/1532002均F0，三组各4200已结束；当前证据入口为expanded03_full/completed_review_20261108.json。SR/SPL原生87.5714/53.2996%、匹配扫描规则88.5952/53.7751%、Qwen88.6429/53.7772%。Qwen描述性5救回/3误伤净+2，但只有2救回/3误伤有真实模型决定前一致前缀；3救回无本episode模型改向，不能归给模型。旧汇总门True/回执保持，不用其True代替贡献审计。以下提交命令/当时状态为复现记录，不再等待或重提；未来读取原始JSONL及audit_traces复算，人工标签仍空。

行为f0e093c，SIGN-qwen-iter-expanded03运行源/资产保持；开发树phase2/qwen-candidate-recovery只前进资料。profile=src/config/inference_semantic_consensus_veto90.yaml，正反prompt= scripts/prompts/recovery_semantic_forward.txt / recovery_semantic_obstacle.txt；FP32真实No2665/Unknown13394/Yes9175，条件softmax/T1，不是校准成功概率。双问相对支持同向且差≥.05、候选词质量≥.1才选；两问都判默认open argmax则保持默认。实际24扫描+6转向+8前进，最多2次、76覆盖步仍计原500。

本次已执行：主1531657与同版重复1531732 F0，61条规则30/Qwen31、同1前缀救回且三组原始行逐条精确复现；冻结确认1531757 F0，24条9/9但SPL下降、普通112条103/103且逐条相同、安全28条27/27且0触发。原CPU1531758保留requires_revision/旧False。06:40预登记版本2允许成功数中性但不声称独立收益，audit_release_v2.py已重算全部raw/F0/goal/start/前缀，08:49写expanded03_confirmation/version2_release_audit.json后另行提交full；不得用新审计改写旧flag。

**已提交，勿重复执行**：1532001.stdct-mgmt-02，CFP04-SF-109/autox→batch_gpux，单A40/36CPU240GB/6h；CPU1532002 afterany/auto/无GPU。原生/匹配扫描规则/Qwen各4200、原6env/500/seed100/hash0，同coverage256125.952M权重SHA988c9ecc…；full忽略tasks内N1，仅off会严格核验旧4200位姿SHA。正式源、提交命令、输出和放行依据在logs/qwen_recovery_iteration_20261108/expanded_v2/expanded03_full/{source_manifest,submission,release_authorization}.json；full_{off,rule,qwen}/result.json及full_comparison.json完成后才可作全量判断。

只读状态参考：`qstat -fx 1532001 1532002`；CPU旧门与当前版本2依据分别是expanded03_confirmation/dispatch.json和version2_release_audit.json。任何失败保留原输出，不修改Q/R源或重新使用同batch提交。发布生成器logs/qwen_recovery_iteration_20261108/publish_iteration.py仅复制已完成轻证据、源SHA和根四文档生成副本到docs/experiments/inference-recovery/iteration_20261108；WORKLOG前缀保留，--check-only --tree <clone>可离线核验，不加载模型/提交作业。运行源码与资料提交区分；不上传权重/环境/完整相机序列、不自动ZIP。


<a id="training-readout-20261108"></a>
## 11月8日训练读取

入口logs/training_readout_20261108/readout.py是11月7日readout.py原字节副本，仅通过脚本所在目录将新输出隔离到新日期；已执行snapshot_130216。保持原PREVIOUS=11月5日冻结前缀，复核SHA后读完整TFRecord新增尾段和ledger；没有改运行目录/原始事件/队列/环境，不使用GPU。可在liuyi用PYTHONDONTWRITEBYTECODE=1、PYTHONNOUSERSITE=1和OMP/MKL/OPENBLAS_NUM_THREADS=1调用envs/sign-baseline/bin/python；每次新建snapshot_实际时间，不覆盖旧批次。

summary/validation.json补充独立CSV窗口与冻结基线末1M复算；readout.json保存共同32.829440M和各自预算1/2/3M，比较前逐点核对SR/SPL步数组。B最新38.180864M近3M优于两覆盖，但最新1M回落和对基线SPL不足一起报告；训练滑窗不当val或严格因果。末日志步数、PBS退出、checkpoint步数分开，原六预算不自动恢复或重计。


<a id="discussion-publication-20261108"></a>
## 文档讨论与分支盘点发布：11月8日

用户本轮明确只更新文档并push，下一批实验先沟通后再实施，可讨论多组并行；不执行qsub/停止作业/新训练。目标分支phase2/qwen-candidate-recovery，源基点294f651；运行源f0e和其他33工作树HEAD/源码保留。元数据与守卫在logs/github_discussion_update_20261108/{branch_inventory,branch_relationship_audit,protected_trees,training_sources}.json；prepare.py --check-guards只读核验全部34工作树，唯一允许资料分支HEAD前进，SRC仍相同。分支盘点含SIGN19/SRU3本地及origin远端，不将16 detached SIGN快照当命名分支。

复用logs/qwen_recovery_iteration_20261108/publish_iteration.py生成同一既有研究包，新增BRANCHES/CASES导航、完整3x4200原始episode结果/贡献审计、8条成败变化的16份仅commands/poses NPZ、5条前缀支持成败变化的候选RGB及人审目标图；目标图不曾喂给Qwen，其他完整相机序列不上传。同步13:56最新训练与13:02旧截面，近期/匹配参考CSV仅提取CORE原数值并注明来源SHA。--check-only --tree <clone>可离线重算全量指标和训练窗口，无模型/GPU/外网。根WORKLOG发布副本保持旧原字节前缀，只追加；新README/docs严格检查，原CSV等格式以逐文件原SHA例外保留，不全局忽略。普通push前核对origin=yiichu03/SIGN及分支，禁止force或更改原训练树。

<a id="qwen-memory-four-arm-20261108"></a>
## Qwen四组推理恢复：正式脚本待审，尚未提交4200

独立工作树`/scratch/e1538633/liuyi/SIGN-qwen-memory-four-arm`，分支`phase2/qwen-memory-four-arm`，基于1e7df23/f0e；共享RecoveryHarness/AgentSupport以agent_variant切换A目标仲裁、B同朝向4+4反馈、C动作后果记忆、D正常导航视觉工作记忆。统一coverage256125.952M ckpt.245，6env/seed100/hash0/max500，无PPO训练或几何bonus。保留16检测/24扫描/左右90°/最多76真实干预；STOP优先，KEEP/RETURN交回当前SIGN提议，不后退/重置GRU。prompt是scripts/prompts/recovery_agent.txt和recovery_feedback.txt。ORB只作外观对应，GT仅供独立离线QA，不能进入runtime记忆。

以下仅供用户审查后执行，不代表已提交：在代码已提交且无运行源修改时，用baseline环境运行`python scripts/prepare_memory_four_arm.py --output /scratch/e1538633/liuyi/logs/qwen_memory_four_arm_20261108/formal_review`，生成source_manifest、固定4200及独立工程集、prepared_commands.json/formal_commands.sh；preparer没有qsub动作。该目录首次准备后不要覆盖/重写；换代码须另用新输出，manifest严格绑定HEAD/运行文件/模型与输入SHA。正式命令按MEMORY_ARM=A/B/C/D以及off/rule/B_visual/C_rule/D_recent/D_random切换同一scripts/memory_four_arm.pbs，每组autox/CFP04-SF-109/单A40/36CPU240GB/6h上限。当前用户只授权准备，四组正式命令等待审查。

正式完成后，可用`python scripts/report_memory_four_arm.py --batch <batch> --split full --reference rule --arms A B C D --output <new-report-dir>`生成同任务配对CSV/JSON；另以`--reference A --arms B C D`检查新增模块。原始result/旧完整4200结果不改写，报告目录必须新建。SR/SPL、救回/误伤、首次实际动作差异及决定前位姿前缀分开；无模型动作变化的成功差异不算Qwen贡献。memory_hits/进入prompt/去记忆影子改变选择分开计数，外观命中不是人工地点真值或SR收益。

必要工程烟测仅用独立不可变快照和scripts/memory_four_arm_smoke.pbs，1h上限；6hash任务检查接口后，为补充真实触发分支增加6条旧full已触发任务，仍属工程集而非性能验证集。原开发61未用于本轮调参。详细代码、固定参数、原始诊断与结果见新研究包docs/experiments/qwen-memory-four-arm。四根文档发布副本由scripts/publish_memory_four_arm.py生成；WORKLOG原字节只追加，其余本地链接移为可发布路径或明确服务器路径。该脚本不git commit、不push、不qsub。

### Qwen四组正式启动与C/D门（2026-11-08）

用户已审核ffc177c并授权：A/B先正式4200，C/D先40真实触发任务在线检查。实际固定运行树SIGN-qwen-memory-formal-ffc177c detached，任务/103运行文件/权重及所有正式参数以logs/qwen_memory_formal_20261108/formal/source_manifest.json为准。A1532929、B1532930已提交，请勿重复qsub；资源各CFP/autox/1A40/36CPU240GB/6h。旧训练1511148不启停。正式C/D只有可靠自然检索、真实模型记忆输入、有效shadow改变选择且技术错误0、案例核验后才提交，不能靠放松参数或SR挑选放行。

诊断1532940独立输出memory_check_40，40任务selection为历史20双触发+20场景均衡hash单触发；外置control脚本SHA已冻结为control_manifest.json与source_manifest.assets。Python sys.setprofile仅导出既有memory before/after/commands及候选/留存历史，不替换运行方法/改RNG/改prompt；先regression_C对旧12工程任务核对所有动作/位姿SHA，再C40/D40。正式作业不加载该观测器。事后analyze_memory.py区分eligible、age_excluded、evicted、overwritten，与固定ORB拒绝原因和近位姿代理对应；GT只在离线QA中读取，不进入Agent。需要结合真实候选/历史图片复核，不能把近位姿代理当人工真值，不能据小诊断集SR作总体结论。

余额核对用amgr checkbalance project -n CFP04-SF-109及amgr report project -n CFP04-SF-109 -r；15006 token expired时请用户在本人服务器终端amgr login，不索要或记录密码。2026-11-08已登录重查成功，GPU记账单位按官方/home/svu/vanda/scripts/nushpc/pbs.proj除30转GPU小时，不能直接将raw gpu_hrs当实际GPU小时。PBS并发以qmgr -c 'print queue batch_gpux'核对当前max_run（本次每用户4）及自己的实际R作业数，不能用历史额度或队列空闲替代项目余额。

### 本批有效作业与统计修正

A/B首轮1532929/1532930因worker启动超时无效，只取消新验证、原partial输出留formal/且INVALIDATED.json标记。当前有效正式是A1532958/B1532959，使用formal_retry/source_manifest及full_A/B；外置launch_retry/evaluate.pbs先加载关闭原worker预热，再运行原ffc177c evaluator，算法/配置/prompt/600秒超时均未改。prewarm控制资产SHA在manifest；正式全四方案若后续获放行共用此manifest，不能拿旧formal_review混用。原tasks.json的formal_jobs_submitted=False是准备时快照，不为更新状态修改冻结文件；实际提交看submission_A/B.json与qstat。

C/D40统计最终C5可靠命中/5真实输入/0选择改变，D1/1/0，故正式均未提交。GPU1532940采集完成后外置统计因左右键大小写错误Exit1；保留旧脚本，CPU1533006用postprocess_v2只修side.lower()、同数据分析Exit0，没有重采样或模型重跑。具体原因与限制见logs/qwen_memory_formal_20261108/REPORT.md，近位姿仅离线代理。后续不能为追正结果循环放宽参数，不能把输入存在或概率变化当实际行为收益。


### A/B完整结果索引（2026-11-08）

有效1532958/1532959已F/Exit0、各4200：A/B SR均88.428571%，SPL53.715613/53.703237%；同权重匹配规则88.595238/53.775092%，原策略87.571429/53.299601%。原始formal_retry/full_A/B/result.json不改，完整独立审计见logs/qwen_memory_formal_20261108/completed_ab_review_20261108/{REPORT.md,summary.json,paired.csv}，复核代码review_ab_full_20261108.py。一次性输出目录已存在，不直接重复运行覆盖；需要重审先显式新输出目录。对off首次动作变化为扫描而非Qwen答复，首差异模型前缀不适于分解该整体效果；应以matched-rule比较A/B、以A比较B额外闭环。无模型动作差异的成功变化不归Qwen，原始人工原因保持空白。


### matched-scan与A的确切含义

“匹配扫描规则”中的匹配指与A对齐扫描协议/观察及动作预算；扫描24步后规则第1次LEFT、第2次RIGHT，不用候选RGB额外选向。SIGN基础策略本身仍用目标图/RGB并在扫描时照常更新GRU。A额外真实调用Qwen3.5-2B FP32，将GOAL/CURRENT/LEFT/RIGHT四图交给模型，取left/right/keep真实token条件概率argmax直接决定恢复；交替规则仅作日志默认方向，不否决有效模型输出。A155条仲裁全部model_argmax、无规则回退，与规则不同39次/32episode；“目标条件”说明目标图进入输入，不自动证明模型有效利用目标。

真实KEEP例Cantwell1782第174步：LEFT38.19%、RIGHT21.06%、KEEP40.75%，选择KEEP并交回SIGN；规则第1次会LEFT，首次实际动作差异及位姿前缀已对齐。原始请求/角色/概率/logits见logs/qwen_memory_formal_20261108/formal_retry/full_A/native/recovery/worker/request_000005_arbitration_0.json；两组该例均失败，仅用作调用生效证明。源码src/recovery_agent.py的_agent_requests/_agent_score/select_agent与src/inference_recovery.py的rule分支，均在固定ffc177c树内。


<a id="qwen-six-ablation"></a>
## E1–E6固定策略推理消融复现（2026-11-08）

开发/资料：SIGN-qwen-six-ablation、phase2/qwen-arbitration-six-ablation；固定运行树SIGN-qwen-six-runtime-e9396ac，源码e9396ac。manifest批次logs/qwen_six_ablation_20261108/runtime_e9396ac；所有运行读取同Coverage256125.952M/SHA988c9ecc5b0c704e9a4780f636739aec17cbd323d613f0fbdde4699296886c2c及全4200/6env/seed100/hash0/max500。原A/旧训练/旧结果不动。

已执行：prepare_six_ablation.py生成tasks/source_manifest/155原图输入与参考清单；prepare不提交作业。1533600为工程检查（autox/1A40/36CPU240GB，原6h已qalter2h）。该作业导航前预热worker，原A155复算、E1六映射930、E2三图155及E3纯CPU重算；再native/off/A/E1–E6各12真实任务。只有checks/check_summary.json passed才运行对应prepared_commands.json里的正式E1–E6命令，每组6h；GPUx调度器最多4R，剩余Q，不停止现有训练。

仅供复现：在固定树运行`python scripts/prepare_six_ablation.py --output /absolute/new_batch`，按其prepared_commands.json提交check；完成后核查source_commit/manifest/技术错误，再提交正式六组。运行目录和输出必须全新，不重复执行已有输出的命令。正式完成后用`python scripts/report_six_ablation.py --batch /absolute/new_batch --output /absolute/new_report`生成与原A/规则的配对报告；未完成组明确pending。

E1完整6调用块平衡每种标签/方向，各2次；最后不足6的尾块应报告实际频数，随机排序不保证每个短前缀最均匀（最初PLAN“最小偏差”表述过强）。映射算法本身未调整：SHA(seed100,block,permutation)排序，避免看到结果后改映射。正式只用一次预定映射，不用离线六次平均或挑最高。原始ABC logits和语义概率分开。E3 softmax阈值不是经过校准的正确率。

本批工程检查1533600已Exit0；正式E1–E6为1533627–1533632，运行源码e9396ac，初次提交状态见initial_job_states.json、命令和路径见formal_submissions.json。CPU1533635 afterany等待六组，H为正常依赖；完成后自动生成formal_review/summary.json、paired.csv和pbs_status.json。不手动解除依赖，不覆盖旧结果或重复提交。prepared_commands/tasks中的submitted=False是不可变准备快照，不等于未提交；receipt记录实际状态。正式原A160触发/155仲裁需分开，E1离线表面方向均衡但926/930选token A，不能视为语义收益。


<a id="qwen-intervention-memory"></a>
## P1–P4短时视觉/动作历史介入实验（2026-11-09）

开发/发布：SIGN-qwen-intervention-memory，phase2/qwen-intervention-memory；固定运行树SIGN-qwen-intervention-runtime-8a94adf，源码8a94adf8bfb0c893ff850c6daf0c321cd73a4fcb。原125.952M权重SHA988c9ecc5b0c704e9a4780f636739aec17cbd323d613f0fbdde4699296886c2c，Gibson4200/6env/seed100/hash0/max500，检测16、扫描24、90°恢复前进8、cooldown64、最多2次机会/76动作。

P1扫描后固定LEFT，P2扫描后交回SIGN，均不启动Qwen；P3/P4扫描前以相同实际16步动作和相同prompt判断progress/blocked/unknown，P3当前RGB、P4为t-16/-11/-5/t四图。仅progress取消干预，其余执行原交替规则；取消也耗一次机会并冷却64。P4另存不执行的当前图shadow。复用FP32模型与真实token softmax/T1，无GT输入，无新增导航训练。方案、prompt及技术门在正式GPU前冻结。

仅供新批次复现：在独立固定树执行`python scripts/prepare_intervention.py --output /absolute/new_batch`，按prepared_commands.json先提交check；只有checks/check_summary.json passed且源/资产SHA匹配，才运行`python scripts/submit_intervention.py --batch /absolute/new_batch`。check最多2h，四正式各1A40/36CPU240GB/6h/CFP/autox，CPU报告afterany依赖四组，独立输出full_P1–full_P4、formal_review。不重复执行已有目录；运行树不pull资料提交。

现有批次logs/qwen_intervention_memory_20261109/runtime_8a94adf已由外部launch_once.py等待服务恢复。检查launch_state.json、check_submission.json、formal_submissions.json及进程后再操作；不要启动第二个等待器。当前暂无提交成功回执，PBS连接失败并非额度耗尽证据。01:58失败原命令/返回码保存在check_submission_attempts.jsonl。账户解析曾失败、现已恢复；系统/PBS问题不通过改训练源码解决。138项CPU测试通过，真实GPU输入/概率/旧控制器回归仍待check，不能用CPU成功替代。

E1–E6完整结果现位于logs/qwen_six_ablation_20261108/runtime_e9396ac/formal_review，六组均F/Exit0；旧RUNBOOK“CPU汇总等待”仅为提交时状态。需要再次独立审计时使用全新报告目录，不覆盖原结果。


<a id="report-figures-cpu"></a>
## 已有导航记录导出报告配图（2026-11-09）

入口logs/report_figures_20261109/{export_training.py,export_cases.py}，发布脚本副本SIGN-qwen-intervention-memory/docs/experiments/report-figures-20261109/scripts。执行时设置OMP_NUM_THREADS=1、OPENBLAS_NUM_THREADS=1、MKL_NUM_THREADS=1，以envs/sign-baseline/bin/python运行，加--workspace /scratch/e1538633/liuyi --out /absolute/new_output；只读已存在TensorBoard/NPZ/视频/事件，不调用Habitat、Qwen或PBS。登录节点仅限此类轻量CPU后处理；新采集/模型推理仍用计算节点。

训练导出保留原/续训全部84,386日志点，主图原段截至125.952M并独立画续段，不跨重置平滑；原reward标签仅导航奖励。视频frame0=reset，动作t从obs[t-1]到obs[t]，取128×128右侧观测区，PNG保留解码图、单独labelled版加step。地图world X为列、Z为行、origin lower；只裁空白边缘，面积用原coverage_new_area_m2，初始视野不计收益；原0.1m/3m/90°不改统计口径。

E2 commands[k]从pose[k]到pose[k+1]；决策观测418对应第419个实际动作，6转到424、8前进到432。线速度归一化转物理为(a+1)*0.125m/s，角速度a*15deg/s，dt1s。不可把命令位移当实际位移，不把候选softmax称成功率。连续恢复后RGB不存在则记录缺口，保留原候选/概率和轨迹证据，不合成帧。图片/CSV/metadata与源SHA在新资料目录；ZIP按用户要求才生成。


<a id="public-sign-demo-20261109"></a>
## Public SIGN成功演示的CPU导出（2026-11-09）

发布入口SIGN-qwen-intervention-memory/docs/experiments/report-figures-20261109/demo_public_sign。只运行该目录export_demo.py，--source-dir指向该目录、--out指向全新目录；使用envs/sign-baseline/bin/python及OMP_NUM_THREADS=1/OPENBLAS_NUM_THREADS=1/MKL_NUM_THREADS=1、nice -n10。依赖Pillow/imageio/imageio-ffmpeg/numpy、Matplotlib字体和ffprobe，不导入Habitat或Torch、不启动模型/PBS。原original_record.py只作来源快照，不用于此次重跑。

源success_03_interior_0651_841463_ep0.mp4在SIGN-habitat-gs/results/habitat_gs_videos_20261028，SHA7af7612f…与原manifest一致。原768×544，RGB矩形(0,64,384,448)，goal(384,64,768,448)；71帧中0–50为真实观测，后20为旧停留。本次0–49每帧重复12次@30fps，50帧停留120输出帧，总720帧24秒；2.5倍是相对1秒仿真时间/动作。goal固定用第0帧裁图，保留H264压缩来源和128原输入说明；不能拿裁图文件SHA冒充原goal原始像素SHA。

metadata含公开nav/safety权重SHA、原95eef9b提交/1503625、Habitat-GS/scene/episode/50动作/success1/SPL.61433、原指标和task.info最短路径4.642218m；actual path为null，最终速度向量未保存。validation完整解码720帧/codec/24秒/终帧4秒、全部来源SHA/帧映射核验。此片不是Gibson也不是完整1900评估的原录像；不把示例成功当总体成绩。用户明确要推送此小型MP4/关键帧，原其他大视频和权重不发布。


<a id="local-checkpoints-20261109"></a>
## 本地下载/运行选定checkpoint（2026-11-09授权）

yiichu03/SIGN的phase2/qwen-intervention-memory下ckpt/README.md是下载和本地命令入口：公开nav_model.pth/safety_model.pth原本已被main及研究分支跟踪；新增coverage256_125952000.pth为原ckpt245/SHA988c9ecc…的字节级副本，7,396,455bytes，无优化器状态。用户本轮明确授权上传这些权重，覆盖常规“资料发布排除权重”的默认约定；只新增此选定模型，其他权重不自动发布。

在本地仓库根目录按README配置环境与数据，再`cd ckpt && sha256sum -c SHA256SUMS`核验。正常python run_sim.py eval，配置gibson,policy,reward,sensors,eval，保留公开safety，选择导航权重路径；1env/test_episode_count3/disk只作本地预览，完整4200原参考需6env/seed100/hash0/max500。无需PBS或Qwen，不添加reward/recovery配置。原生disk未专门保存terminal RGB，不能假称其最后帧就是STOP；要PPT终帧采用独立episode录制器。

本次CPU配置导入最初遇系统libstdc++缺GLIBCXX_3.4.30，使用现有envs/sign-baseline/lib/libstdc++.so.6的进程级LD_PRELOAD后通过，未升级依赖或修改shell全局。preflight.py/json/log与首次错误摘要在logs/checkpoint_publication_20261109；本地不同环境不直接照搬服务器绝对LD_PRELOAD路径。权重/源码下载可离线准备，但场景数据必须另有授权副本。
