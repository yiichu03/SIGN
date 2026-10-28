# SIGN 在 Habitat-GS 上的 ImageNav 进展

快照时间：**2026-10-28T14:46:52+08:00**。运行代码固定 **95eef9bf497bc1d010c7a4b35030fdce4123dce7**；本资料提交只增加说明、证据和文档快照。

## 已完成

- 独立环境：Python3.10、torch2.5.1+cu121、NumPy2.0.2、Habitat-GS0.3.3。第三方源码固定cb01b2fdf850ce3cab28ad00461a68ac7719f23f，Habitat-Lab固定1f7cfbdd。
- 已下载129场景静态ImageNav所需GS、navmesh、任务和配置：393文件，26,695,345,591字节。训练110场景／110000条，验证19场景／1900条；全部官方哈希和任务引用检查通过。[完整清单](evidence/data/imagenav_manifest.json)、[下载完成记录](evidence/data/download_submission.json)。
- A40实际GS渲染、目标图重渲染一致性及姿态保持、公开策略前向、连续移动／转向检查通过。[GPU探针](evidence/pilot/probe.json)、[CPU配置探针](evidence/pilot/cpu_sensor_probe.json)。

![左：当前视图；右：目标图](evidence/pilot/probe.png)

## 已完成的小样本评估

作业1494770正常退出；scene56的10条任务：**成功率10%（1/10），SPL5.3543%，view_match10%**。平均最终目标距离14.9221米，平均碰撞46.9次。[原精度结果](evidence/pilot/result.json)、[原生汇总](evidence/pilot/native_summary.log)、[实际配置](evidence/pilot/config_of_eval.yaml)。这是单场景小样本，不能代表完整评估。

## 完整验证集评估正在运行

作业 **1502487.stdct-mgmt-02**，GN-A40-023／A40，快照时 **176/1900**；**完整 SR／SPL 尚未产生**。不把进度或局部任务当成完整结果。

使用公开 `ckpt/nav_model.pth` 与 `ckpt/safety_model.pth`，哈希见[输入清单](evidence/full-val/inputs.json)。19个场景1900条任务CPU检查均可达，测地距离最大误差0.0。6并行、seed100／PYTHONHASHSEED=0、每任务1次，原生确定性评估。

[运行状态快照](evidence/full-val/runtime_status.json) · [实际合并配置](evidence/full-val/config_of_eval.yaml) · [提交记录](evidence/full-val/submission.json) · [进行中日志截面（gzip）](evidence/full-val/partial_evaluation.log.gz)

服务器后续结果位于 `SIGN-habitat-gs/results/habitat_gs_full_val_20261028/job_1502487/result.json`；仅1900/1900完成且指标有限后生成。原trainer不保存逐条指标／轨迹，不能据聚合值恢复每条失败原因。

## 原始 SIGN 的边界与复现

相对作者基线dad87fe，src仅增加GS数据元数据补齐、相机向量类型转换，并移除一个未使用的nis导入；trainer、网络计算、动作、奖励、指标不变。沿用SIGN的128×128输入、连续动作、500步上限和1m成功判定。与官方GS示例256×256、离散动作、1000步协议不同；本实验为公开SIGN权重在完整GS val上的迁移评估。

[单场景配置](../../../exp_config/ppo_imagenav_habitat_gs.yaml) · [数据下载器](../../../scripts/habitat_gs/prepare_data.py) · [编译PBS](../../../scripts/habitat_gs/build.pbs) · [完整评估PBS](../../../scripts/habitat_gs/evaluate.pbs) · [预检与汇总入口](../../../scripts/habitat_gs/evaluate.py)

服务器从工作区根目录提交的命令模板（先检查已有作业并换新日志名，不重复提交当前作业）：

```bash
qsub -v GS_SOURCE_COMMIT=95eef9bf497bc1d010c7a4b35030fdce4123dce7 \
  -o /scratch/e1538633/liuyi/logs/habitat_gs_eval_20261028/next_full_val.pbs.log \
  SIGN-habitat-gs/scripts/habitat_gs/evaluate.pbs
```

数据固定[官方HF revision ea645385](https://huggingface.co/datasets/RukawaY/gs_scenes/tree/ea6453855938dd3d4395c4c449fedefb7e6603b7)。环境与资源路径来自当前服务器，移机需按[运行手册](workspace/RUNBOOK.md)调整。数据和权重保留各自来源，本包不新增它们。

[STATUS](workspace/STATUS.md) · [RUNBOOK](workspace/RUNBOOK.md) · [WORKLOG](workspace/WORKLOG.md) · [AGENTS](workspace/AGENTS.md)是服务器根维护源的生成快照；不在GitHub手工双份维护。[发布SHA清单](publication_manifest.json)、[生成器](scripts/build_publication.py)。
