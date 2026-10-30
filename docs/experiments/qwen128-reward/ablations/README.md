# A/B/C：Qwen beta0.03与匹配几何128对照

基于用户指定SIGN **33e30d2**，独立`SIGN-qwen-ablation` / `phase2/qwen-beta003-geometry128`。运行源码 **d2352f0**；生产目录保持该提交，资料通过独立publication树发布。原1507268、两旧coverage训练及既有1507270/1507272评估依赖保留，未修改或重复提交。

## 最新训练记录

[2026-10-31六组训练对照、曲线和原始统计](training_20261031/README.md)。下面保留2026-10-29的启动/短测及评估提交记录；不以这些历史状态代替最新作业状态。

## 实际正式配置与作业

三组均8环境×PPO rollout256、seed100/hash0，从全新初始化开始，只从公开checkpoint加载并冻结visual_encoder，其余参数原初始化。CFP04-SF-109 / autox→batch_gpux，1A40/36CPU240GB/168h；300M是算法上限，不承诺168h完成。按A/C/B顺序提交，B可因资源不足排队，不改变其他运行作业。

| 组 | 结算窗口 | 系数 | 正式训练job ID |
|---|---:|---|---|
| A | 128 | beta0.03 | 1507648.stdct-mgmt-02 |
| B | 256 | beta0.03 | 1507651.stdct-mgmt-02 |
| C | 128 | alpha0.2927574680399425 | 1507650.stdct-mgmt-02 |

- A：Qwen3.5-2B，128步/真实terminal切段，bonus=.03*(L/256)*raw_q；B同式，结算窗口256。原始q=.5*p_medium+p_high，不居中，不作组内相对评分；FP32独立单图batch≤8、ABC softmax T1，既有常驻进程/SingleImageJudge/prompt保持。
- C：几何128，复用A的0.025m/3m/90°增量覆盖、完整episode历史、初始视野扣除和有效性规则，bonus=alpha*segment_new_area_m2/256，只写段末；Qwen enabled=False/beta0，不启动worker、不绘制topdown或记录q。SIGN原导航RGB观察仍照常。
- 三组均显式`mrq_reward_target: navigation`，MRQ预测独立nav_rewards，与Qwen开关解耦；GAE/PPO/critic用混合rewards。无此字段的旧配置仍mixed。旧coverage bonus权重0，PPO/其他MRQ损失/RandomShift/Qc/冻结逻辑及其他超参数保持。
- 窗口只决定结算点，真实mask/GRU不改；rollout仍256，每rollout只统一评分/回填一次。真实reset前快照/身份核对及无效段跳过、worker异常硬报错沿用已验证逻辑。
- A/B图和prompt直接复用已验证实线历史版：黄历史/红当前1.5pt实线、深蓝累计/浅蓝新增、2.5cm/3m/90°；[prompt](../../qwen-history-solid/prompts/history.txt)。评估/部署关闭Qwen与奖励轨迹采集。

配置加载在原`exp_config/ppo_imagenav_gibson.yaml,policy,reward,sensors`之后追加`,qwen_reward,qwen_a128` / `,qwen_reward,qwen_b256` / `,qwen_reward,geometry_c128`。实际命令/合并配置见[evidence](evidence/)，初始化及全部原字段检查见config_audit.json。

## 冻结的几何校准

[校准JSON](calibration/calibration.json)与[1176条有效段明细](calibration/segments.csv)来自已结束40960步短测1507196：总1204段，sum(L*q)=22736.24026696853，sum(new_area)=2329.87125m²。

**alpha=.03*sum(L*q)/sum(new_area)=0.2927574680399425**。原始逐段记录SHA256为`26180a9e26faa7024f0564193c66d46a8cbb31d1e2c1d99254aeb49b00d81bd7`。在此校准集上两种bonus总量均为2.6644031562853745。alpha在新训练前冻结；不在新训练或val数据上重拟合，不声称新策略的实际奖励总量必然相等，也不将m²伪装成概率。

## 验证

63项CPU回归通过：128/256真实终止和rollout边界、完整256和跨rollout历史、原子错误处理、导航奖励/mask隔离、独立MRQ开关、C不启动worker/render/无q字段、冻结校准。真实milestone保存函数的准确step/SHA/拒绝覆盖及全部六个CPU等待路径通过。原验证输入与A首轮52张有效图片/metadata/ID逐项相同；A/C首轮55片段、其中52有效的统计/有效性/窗口完全相同。三组103项初始状态哈希等于原冻结基线初始化。

GPU各40960步/20更新短测：A1507600、C1507601、B1507602。三组均通过、42项encoder状态与公开权重逐位不变，visual_fc从原初始化更新，所有模型与训练scalar有限，原导航奖励/masks不变，ID无重复，奖励公式及总量守恒。A/B真实FP32答案token/padding/batch/solo检查通过；C没有worker、topdown PNG、概率字段。短测训练SR/SPL/碰撞、全scalar/逐段logits/bonus/片段长度/时耗见[evidence](evidence/)，仅验证工程，不按短测训练指标判断学习收益。

| 组 | 有效片段 | 每2048动作中位秒 | 实际总bonus | 段长P50/P90/max | bonus P50/P90/max |
|---|---:|---:|---:|---|---|
| A | 97.846% | 40.392 | 2.662362 | 26/75/128 | 0.001569/0.005116/0.012053 |
| B | 97.803% | 35.363 | 2.749409 | 28/88/239 | 0.001827/0.006558/0.020261 |
| C | 97.983% | 27.867 | 2.366688 | 26/77/128 | 0.000585/0.006251/0.021848 |

节点不同、初期episode频繁结束，以上耗时是实际预算参考。B CPU测试包含完整256步片段；真实短测的片段可能被episode终止缩短，最大长度以表为准，不人为延长真实episode或修改终止mask。

## 输出与指标

三组输出根：`/scratch/e1538633/liuyi/SIGN-qwen-ablation/results/qwen_ablation_20261029/{A,B,C}/train/`，TensorBoard在`tb/`、权重在`ckpts/`、片段审计在`qwen/segments.jsonl`、rollout审计在`qwen/rollouts.jsonl`，C沿用目录名称但无Qwen模型/概率。A/B worker常驻FP32，图片仅定期/诊断抽样；C不渲染图片。

原`reward`与`metrics/success/spl/collisions.count`仍是导航episode指标。A/B新增`learner/qwen_*`，C新增`learner/geometry_*`记录bonus/新面积/有效率/几何与结算耗时；A/B另有q分布。三组共有`learner/exploration_segment_length_*`与`exploration_bonus_*`记录P0/P50/P90/P100/均值、有效动作覆盖效率与terminal数量。几何CPU耗时是8环境累计，不能直接当额外墙钟。

## 4.608M / 8.192M 原协议验证安排

每250更新保存常规权重；准确4.608M/8.192M另存不可变milestone及step/SHA侧车。CPU等待job以训练开始为依赖，在CPU资源获批后运行，仅完成对应权重校验；GPU val通过afterok依赖释放，等待不占GPU。旧两组评估依赖保留。

| 组 | checkpoint步数 | CPU等待 | GPU val |
|---|---:|---|---|
| A | 4,608,000 | 1507652.stdct-mgmt-02 | 1507653.stdct-mgmt-02 |
| A | 8,192,000 | 1507654.stdct-mgmt-02 | 1507655.stdct-mgmt-02 |
| B | 4,608,000 | 1507661.stdct-mgmt-02 | 1507662.stdct-mgmt-02 |
| B | 8,192,000 | 1507663.stdct-mgmt-02 | 1507664.stdct-mgmt-02 |
| C | 4,608,000 | 1507656.stdct-mgmt-02 | 1507657.stdct-mgmt-02 |
| C | 8,192,000 | 1507659.stdct-mgmt-02 | 1507660.stdct-mgmt-02 |

每组每阶段4200条Gibson val/14场景，确定性6环境、max500、seed100/hash0、相同公开safety和原生SIGN evaluator；Qwen及其采集关闭。被动覆盖统计保留原评估0.1m/3m/90°、weight0，报告SR/SPL、sum(new_area)/sum(actions)、逐episode效率均值、碰撞、动作数、耗时。0.1m验证统计与训练奖励输入0.025m分开记录。结果将写`logs/qwen_ablation_20261029/{A,B,C}/val_STEP/result.json`；2026-10-29提交时尚无这三组正式模型的val结果，评估状态以提交回执和wait_state为准。

## 资源核验与复现

GPUx队列允许168h、每用户最多4个运行job；原两个H评估等待依赖时不分配GPU。三组短测被CFP/autox实际接受并运行，正式提交回执保留；共享项目余额查询仍需amgr登录，**未取得剩余额度数值**，不将提交许可当成余额确认。三组正式168h上限合计504GPUh、六次4h val上限24GPUh，是预算上界，非实际消耗。

从以下已执行命令/配置复核；相同输出目录不重复启动。GPU作业须通过提供的PBS脚本运行，训练环境未升级，原作业目录/输出不动。

### A

```bash
/scratch/e1538633/liuyi/envs/sign-baseline/bin/python run_sim.py --exp-config exp_config/ppo_imagenav_gibson.yaml,policy,reward,sensors,qwen_reward,qwen_a128 --run-type train --model-dir /scratch/e1538633/liuyi/SIGN-qwen-ablation/results/qwen_ablation_20261029/A/train habitat_baselines.num_environments 8 habitat_baselines.rl.ppo.num_steps 256 habitat_baselines.rl.ddppo.pretrained_encoder True habitat_baselines.rl.ddppo.pretrained_weights ckpt/nav_model.pth habitat_baselines.rl.ddppo.train_encoder False habitat_baselines.num_checkpoints -1 habitat_baselines.checkpoint_interval 250 habitat_baselines.log_interval 10
```

### B

```bash
/scratch/e1538633/liuyi/envs/sign-baseline/bin/python run_sim.py --exp-config exp_config/ppo_imagenav_gibson.yaml,policy,reward,sensors,qwen_reward,qwen_b256 --run-type train --model-dir /scratch/e1538633/liuyi/SIGN-qwen-ablation/results/qwen_ablation_20261029/B/train habitat_baselines.num_environments 8 habitat_baselines.rl.ppo.num_steps 256 habitat_baselines.rl.ddppo.pretrained_encoder True habitat_baselines.rl.ddppo.pretrained_weights ckpt/nav_model.pth habitat_baselines.rl.ddppo.train_encoder False habitat_baselines.num_checkpoints -1 habitat_baselines.checkpoint_interval 250 habitat_baselines.log_interval 10
```

### C

```bash
/scratch/e1538633/liuyi/envs/sign-baseline/bin/python run_sim.py --exp-config exp_config/ppo_imagenav_gibson.yaml,policy,reward,sensors,qwen_reward,geometry_c128 --run-type train --model-dir /scratch/e1538633/liuyi/SIGN-qwen-ablation/results/qwen_ablation_20261029/C/train habitat_baselines.num_environments 8 habitat_baselines.rl.ppo.num_steps 256 habitat_baselines.rl.ddppo.pretrained_encoder True habitat_baselines.rl.ddppo.pretrained_weights ckpt/nav_model.pth habitat_baselines.rl.ddppo.train_encoder False habitat_baselines.num_checkpoints -1 habitat_baselines.checkpoint_interval 250 habitat_baselines.log_interval 10
```
