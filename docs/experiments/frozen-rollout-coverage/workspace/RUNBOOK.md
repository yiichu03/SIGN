# liuyi 运行与复现手册

本文件维护目前适用的操作方法；当前任务和阻塞见 [STATUS.md](STATUS.md)，执行结果及 debug 过程追加到 [WORKLOG.md](WORKLOG.md)。下面的命令是操作模板，列出不表示本次执行。

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

- GPU 推理和采集使用 PBS 计算节点；长任务按用户要求使用 `auto`／`autox`。现有 A40 作业常用 `autox`、项目 `CFP04-SF-109`。
- 如项目被拒，先查实际错误与预算；既有授权备选为 `CFP02-CF-006`、`personal-e1538633`。
- 2026-10-26 实测个人项目拒绝 autox（Express queue not allowed），须使用 auto。用户已授权共享 CFP 与个人预算；个人年度默认 1000 GPUhr／10000 CPUhr 不等于当前余额。hpc project 查询需要 amgr 登录，未登录时不能声称已核对余额。
- 集群手册：`~/liuyi/Vanda Cluster User Guide 05Jun25.pdf`。不要在日志记录访问凭据。

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

首次成功证据：作业1494770，分支24b4c02，结果目录 `SIGN-habitat-gs/results/habitat_gs_20261026/job_1494770/`。probe.json／probe.png验证真实GS渲染和动作；eval/eval_run0_/config_of_eval.yaml是实际合并配置，log.txt与eval/tb保存原trainer汇总，result.json从TensorBoard提取精度完整的指标。原trainer不保存逐条指标或轨迹，本轮未增加采集；只能报告10条汇总，不能恢复失败原因。成功率10%、SPL5.3543%仅说明该权重在这个小样本的表现。

只下载scene56时，原官方val.scene_dataset_config.json会打印其他18个场景navmesh不存在以及无语义描述文件的消息；本次不使用这些场景或语义传感器，scene56导航／RGB／depth实际运行通过。保留原配置和日志，不为消除消息下载其余资产。Gym对NumPy2的通用提示也保留；本次CPU、GPU探针和10条实际评估均通过，但不代表覆盖Gym全部功能。

## 当前 Gibson 原版复现

SIGN 当前 phase2 @ dad87fe 保持作者源码，不迁入 phase1 兼容补丁、不 monkeypatch。先现有 checkpoint 评估，再独立从零训练；数据与结果均位于 SIGN/data、SIGN/results，准备脚本在根 logs/gibson_reproduction_20261026/。

场景下载已发现可直接访问的 Meta 文件服务器：

- [gibson_habitat.zip](https://dl.fbaipublicfiles.com/habitat/data/scene_datasets/gibson_habitat.zip)：1468698464 字节，88 个 glb 和 88 个 navmesh，包含当前 SIGN 所需全部 72 train + 14 val 场景。官方 [MD5 清单](https://github.com/StanfordVL/GibsonEnv/wiki/Checksum-Values-for-Data.md) 为 `35f274a781eba9ed1b77feba50d040da`。
- [gibson_habitat_trainval.zip](https://dl.fbaipublicfiles.com/habitat/data/scene_datasets/gibson_habitat_trainval.zip)：10833075327 字节，492 对场景文件。当前 86 场景与小包的文件大小和 CRC 一致，无需为本次复现下载全包。

直链来源包括 [社区下载脚本](https://github.com/WGW101/habitat_sim2real/blob/62fcdd3ed5a5030b099bcd1ed847989344441805/script/download_gibson.sh) 和 [AudibleLight 下载脚本](https://github.com/AudibleLight/AudibleLight/blob/main/scripts/download_data/download_gibson.py)。后者对小包场景数的注释不准确，以实测压缩包目录为准；不要直接运行其清理选项，会删除本任务需要的 navmesh。公开直链可访问不代表免除数据使用协议，Gibson 官方仍将下载入口指向许可表单。

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

原任务1495073按批准停止，实际TensorBoard5785600步，唯一保留ckpts/final.pth为5632000步；中间12份权重已删除，归档JSON为logs/gibson_reproduction_20261026/stopped_scratch_run/result.json，原事件／配置／控制台日志及导出曲线保留。此前parameter_update_audit引用的旧中间checkpoint已按授权精简，审计JSON仍可读。查看网页仍使用同一个view_personal_tensorboard.sh SSH命令，其logdir已切换到新正式训练目录；已有网页进程需用户重启连接才能读取新路径。

最新用户选择为仅加载并冻结actor_critic.net.visual_encoder（包含其归一化buffer），不加载或冻结visual_fc，其他模块保持原初始化。当前待审encoder_only_proposed.patch仅涉及SIGN/src/trainer.py两处，复用已存在的ddppo.pretrained_encoder／pretrained_weights／train_encoder配置，默认False／原路径／True时不改变原行为。新实验拟以CLI开启预训练encoder、指定ckpt/nav_model.pth、关闭train_encoder；冻结在优化器构造前完成，原PPO自动过滤requires_grad=False参数，并在每次agent.train后将encoder恢复eval。visual_fc仍训练，MRQ仍可更新它；上一轮“完整视觉固定后MRQ仅训自身头”的推断不适用于本轮只冻CNN的方案。用户明确要求审核后才实施／停旧训练／清理，随后用户已明确批准，patch已按原样实施并本地提交dac8609，新任务1496716已通过GPU校验运行；原待审文件保留作为决策证据。

预训练冻结视觉方案（仅审查，尚未接入原trainer）：公开ckpt/nav_model.pth可按actor_critic.net.visual_encoder.与actor_critic.net.visual_fc.前缀剥离后严格加载到对应子模块，42＋2项完全匹配。当前两张RGB先按通道拼接为6通道，只有一个EarlyFuseCNNEncoder，goal_visual_encoder=None。可路由Fast系列为fast_resnet7/9/9_fixup/18/18_fixup/50；Habitat系列为resnet18/resnet50/se_resnet50。更多SE／ResNeXt虽有函数定义，并非当前名称路由均可达。SimpleCNN分支调用参数与当前依赖签名不符；clip／clip_feat只有遗留forward分支、没有构造路径，不当作可直接启用编码器。

自定义SIGN trainer直接继承BaseRLTrainer，未调用Habitat通用PPOTrainer加载／冻结逻辑，单设ddppo.pretrained_encoder=True或train_encoder=False不会生效。冻结视觉须明确是否包含visual_fc，并固定RunningMeanAndVar的_mean/_var/_count；requires_grad=False仅固定参数，每次agent.train()后还要维持冻结模块eval。CPU审查中直接执行归一化1024张小合成输入，var／count在仅冻结梯度时仍变化；预训练count约2.878e9，小批量2的变化可能因float32精度被掩盖。完整冻结视觉后MRQ无法再优化CNN／投影，只训练自身头，其开关需要另作明确实验决定。完整冻结与后端更新CPU验证见frozen_encoder_review/cpu_review.json；不把它当完整PPO或收敛验证。

原版SIGN当前使用可训练fast_resnet9视觉编码器，未冻结、未加载导航预训练权重；PPO／RandomShift及前50M的MRQ辅助训练会更新视觉表征，GRU、动作头、普通价值头同时训练。MRQ目标网络通过EMA更新，安全Qc使用独立优化器；cost_critic虽被构造并输出数值，当前DA_PPO未将cost-value loss加入total_loss，不能笼统声称所有已定义参数都更新。个人训练512000→4096000步checkpoint审计验证视觉编码器39/39组weight／bias改变、cost_critic不变，证据parameter_update_audit.json。

基础 pipeline：episode 提供起点和目标视角，Habitat-Sim 渲染当前 RGB 与目标图，EarlyFuseCNN／fast_resnet9 编码，再结合上一步动作送入两层 GRU；策略输出连续角速度与线速度，训练采样动作、评估选分布 mode。环境返回距离与朝向塑形奖励，收集 rollout 后 DA_PPO 更新策略与价值网络，并更新辅助表征／安全 Qc。主奖励为 `-0.01 + previous_distance_to_view - current_distance_to_view + 2.5 * view_match`，最后一项在成功触发时加入；不能把已定义但未选中的 ZERReward 当作本次实际奖励。

个人正式长训练使用 `logs/gibson_reproduction_20261026/scratch_train_personal_8env.pbs`，明确指定personal-e1538633／auto、168小时、1×A40、8×256、原300M总步数上限；不再调用旧完整耗时拦截。每250次更新保存checkpoint（512000环境步），每次更新写TensorBoard；输出 `SIGN/results/gibson_reproduction_20261026/scratch_personal_8env`。该作业是从零新训练，不加载测速checkpoint；超过PBS时限会终止，latest.pth仍不是优化器级可续训状态。当前提交状态以personal_training_submission.json和STATUS为准，不重复qsub。

从用户本地电脑终端执行以下命令，同时在SSH远端启动TensorBoard并转发端口；该方法保证网页和SSH转发落在同一登录节点，兼容vanda登录入口分配不同主机：

```bash
ssh -T -o ExitOnForwardFailure=yes -o ServerAliveInterval=30 -o ServerAliveCountMax=3 -L 127.0.0.1:16006:127.0.0.1:6006 \
  e1538633@vanda.nus.edu.sg \
  'bash /scratch/e1538633/liuyi/logs/gibson_reproduction_20261026/view_personal_tensorboard.sh'
```

保持终端连接，在本地浏览器打开 http://127.0.0.1:16006 。训练排队时暂无曲线，开始更新后显示reward、metrics/success、metrics/spl、learner/*、perf/fps。Ctrl+C结束网页和SSH转发，不停止PBS训练。view_personal_tensorboard.sh固定当前正式训练tb目录，仅监听远端127.0.0.1:6006；网页首页和/data/logdir已实测HTTP200。2026-10-26晚重新启动转发并实测29条scalar可读，随后按用户要求关闭网页进程和转发，由用户自行运行；当前连接状态见STATUS。命令开头是ssh，不是sh；应在运行浏览器的本地电脑执行。Python3.8弃用警告及TensorFlow installation not found在本次环境不阻止scalar展示；等待出现TensorBoard 2.8.0 at http://127.0.0.1:6006/后再访问。若本地16006已被当前连接占用，直接访问已有入口，不重复启动。

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


### 阶段二覆盖奖励资料发布（2026-10-27）

旧phase1资料发布器锁定旧SRU研究分支及历史证据，本次不调用或修改它。新资料位于SIGN的`docs/experiments/frozen-rollout-coverage/`，通过独立detached工作树SIGN-coverage-publication构建，并普通push HEAD到origin/phase2/frozen-rollout-coverage；有效push URL必须为git@github.com:yiichu03/SIGN.git。构建脚本`logs/gibson_coverage_comparison_20261027/build_publication.py`仅锁定本轮base6983c91，选取已完成的不可变验证结果、最新完整scalar导出、两版曲线、实际配置、测试和命令，生成四根文档副本与SHA清单；不启动作业、不提交或push。未来资料更新应先选择新快照与明确base，不绕过锁定检查。

本轮已执行`git worktree add --detach /scratch/e1538633/liuyi/SIGN-coverage-publication 6983c91e20493ff25ff32c24df02b968cc34f701`。构建/检查命令为`python3 logs/gibson_coverage_comparison_20261027/build_publication.py`和同命令追加`--check-only`。只允许新增资料包和根README导航；src、exp_config与run_sim.py相对运行时代码必须零差异。scalar CSV和原生控制台日志用确定性gzip打包，验证解压SHA；不上传checkpoint、场景、环境或原始相机数据。工作区WORKLOG发布副本必须保留已有完整前缀。有效远端SHA核对后普通push，不force、不改训练工作树HEAD。

资料发布后，远端coverage分支会比运行中的SIGN-frozen-rollout-coverage本地代码提交多资料提交；不为消除这项差异而pull进运行目录。实际训练源码由6983c91及source_manifest固定；原SIGN仍dac8609。根四文档为维护源，包内副本截至manifest的生成时间；最终推送回执留在根WORKLOG。
