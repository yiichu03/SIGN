# Checkpoints for local SIGN inference

本目录的模型可以直接下载，不需要访问 NUS 服务器。公开模型原本就已随仓库上传；2026-11-09 按用户要求补充我们训练的 Coverage256 权重，保留原始文件字节，不做精度转换或重新序列化。

|文件|来源|大小|用途|
|---|---|---:|---|
|[nav_model.pth](nav_model.pth)|作者公开完整 SIGN 导航权重|17,289,707 bytes|Public SIGN 演示或原模型评估|
|[safety_model.pth](safety_model.pth)|作者公开安全模型|16,399 bytes|沿用原 `policy.yaml` 的安全模型加载设置|
|[coverage256_125952000.pth](coverage256_125952000.pth)|本项目 Coverage256，125.952M，原 `ckpt.245.pth`|7,396,455 bytes|当前推理恢复实验的固定导航底座，也可单独运行|

Coverage256 在 Gibson 完整 4,200 条验证中，原策略 **SR 87.571429% / SPL 53.299601%**；不含推理恢复或 Qwen。它是加载并冻结公开 visual encoder、训练其余模块并添加覆盖奖励所得，不是 Public SIGN。权重含 103 个 `state_dict` 键与累计步数，无完整优化器/环境状态，适用于推理，不能宣称无缝恢复训练。

[CPU 校验记录](validation.json) 核对了步数、参数有限性及 42 个冻结 encoder 张量。[manifest.json](manifest.json) 保存身份、训练步数、指标和 SHA256；[SHA256SUMS](SHA256SUMS) 可直接核验：

```bash
cd ckpt
sha256sum -c SHA256SUMS
cd ..
```

## 本地运行

先按仓库 [README](../README.md) 配置 SIGN / Habitat 环境和数据。导航不需要 Qwen 环境，也不需要 PBS；仍需要能运行 Habitat-Sim 的本地 GPU/驱动，以及对应场景 `.glb` / `.navmesh` 和 episode 数据。checkpoint 不包含场景。

以下从仓库根目录执行，仅检查 **3 条 Gibson val**，不重新训练，不启用 Qwen 或恢复控制。它是本地快速检查，不是 4,200 条完整成绩复现。输出请使用新的目录。

```bash
PYTHONHASHSEED=0 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 \
python run_sim.py \
  --exp-config exp_config/ppo_imagenav_gibson.yaml,policy,reward,sensors,eval \
  --run-type eval \
  --model-dir results/local_public_sign_3ep \
  habitat_baselines.eval_ckpt_path_dir ckpt/nav_model.pth \
  habitat_baselines.rl.policy.safety_model_path ckpt/safety_model.pth \
  habitat_baselines.eval.use_ckpt_config False \
  habitat_baselines.eval.split val \
  habitat.seed 100 \
  habitat_baselines.num_environments 1 \
  habitat_baselines.test_episode_count 3 \
  habitat.environment.max_episode_steps 500 \
  habitat_baselines.video_option "['disk']"
```

运行我们训练的 Coverage256 时，只将上面的两处替换为：

```text
--model-dir results/local_coverage256_3ep
habitat_baselines.eval_ckpt_path_dir ckpt/coverage256_125952000.pth
```

**保留 `policy.yaml` 和 `safety_model.pth` 加载逻辑**，与已完成验证保持一致。不添加 `rollout_coverage`、Qwen reward 或 recovery 配置；评估不需要计算训练附加奖励。当前默认组合不会启动 Qwen。

日志在所选 `results/.../eval_run*/`，原生预览视频在 `results/.../video/`。原生视频导出受 vector-env auto-reset 逻辑影响，没有专门保存最终 terminal RGB；它适合先检查本地运行。若要制作“完整到达并 STOP”的 PPT 成片，需要使用 auto-reset 前取帧的单 episode 录制器，不能拿 reset 后画面当终帧。

若本地准备的是 **HM3D v0.2**，将配置文件换成 `exp_config/ppo_imagenav_hm3d.yaml`、split 换为 `val_easy`（或 medium/hard），并使用不同输出目录；不要把 HM3D 示例称为 Gibson 验证。本次没有在本地新跑这些命令，仅完成 CPU 配置合并、checkpoint 步数/参数/有限性/SHA 检查。

服务器验证环境为旧版 SIGN / Habitat 依赖；不要直接在 Qwen 的新版 PyTorch 环境里运行导航。完整正式复现还需保持 6env、seed100/hash0/max500 和原任务集；上述 1env/3ep 只用于本地跑通与预览。
