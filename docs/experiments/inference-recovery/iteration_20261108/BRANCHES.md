# 分支与工作树盘点

盘点时间：2026-11-08T13:59:49+08:00。表中HEAD为本次资料提交前截面；当前资料分支随后会新增文档提交，运行代码仍固定f0e093c。

SIGN与SIGN-SRU是两个Git仓库。一个分支可承载多个超参数实验，detached工作树是固定提交快照，不额外算命名分支。SIGN目录当前检出冻结视觉分支；作者main仍保留。

## SIGN

本地19个命名分支，origin19个；32个工作树，其中16个detached。

|分支|用途|本地HEAD|origin HEAD|命名工作树|
|---|---|---|---|---|
|[experiment/habitat-gs-imagenav](https://github.com/yiichu03/SIGN/tree/experiment/habitat-gs-imagenav)|独立Habitat-GS适配及评估，当前非Gibson主线|`95eef9b`|[d1f5aa5](https://github.com/yiichu03/SIGN/tree/d1f5aa52df7de9004014cc3e91cef6ac1c84c1be)|`SIGN-habitat-gs`|
|[main](https://github.com/yiichu03/SIGN/tree/main)|作者基线，保持不动；跟踪upstream不改变默认push目标|`dad87fe`|[dad87fe](https://github.com/yiichu03/SIGN/tree/dad87fe225a4dc1073787d8d2cc83f67e61c0a9d)|当前无命名工作树|
|[phase1/imagenav-qwen-diagnostics](https://github.com/yiichu03/SIGN/tree/phase1/imagenav-qwen-diagnostics)|第一阶段轨迹采集与Qwen诊断归档|`f2b4bb4`|[f2b4bb4](https://github.com/yiichu03/SIGN/tree/f2b4bb4b18422ff0da9ada159a0456dc0c84a1e0)|当前无命名工作树|
|[phase2/continue-coverage256-20261103](https://github.com/yiichu03/SIGN/tree/phase2/continue-coverage256-20261103)|覆盖256 weights continuation，原预算续跑|`5a86720`|[5a86720](https://github.com/yiichu03/SIGN/tree/5a86720fdcaf69a842ce40a660e2598f3fc052a0)|`SIGN-continue-coverage256`|
|[phase2/continue-coverage32-20261103](https://github.com/yiichu03/SIGN/tree/phase2/continue-coverage32-20261103)|覆盖32 weights continuation，原预算续跑|`2e5efba`|[2e5efba](https://github.com/yiichu03/SIGN/tree/2e5efbaf6caa4962e458e898d6c107e06a59138b)|`SIGN-continue-coverage32`|
|[phase2/continue-qwen-ablation-20261103](https://github.com/yiichu03/SIGN/tree/phase2/continue-qwen-ablation-20261103)|A/B/C三组共用续跑代码；当前只有B训练仍R|`1256ca7`|[1256ca7](https://github.com/yiichu03/SIGN/tree/1256ca70497592d2df178e6f77d10c14380689d8)|`SIGN-continue-ablation`|
|[phase2/continue-qwen128-beta01-20261103](https://github.com/yiichu03/SIGN/tree/phase2/continue-qwen128-beta01-20261103)|Qwen128 beta0.1续跑|`bb59545`|[bb59545](https://github.com/yiichu03/SIGN/tree/bb59545f0c5663163e17cfe1dea37c441f09ccd2)|`SIGN-continue-qwen128`|
|[phase2/exploration-reward-try](https://github.com/yiichu03/SIGN/tree/phase2/exploration-reward-try)|原版阶段二起点，当前与main同提交|`dad87fe`|[dad87fe](https://github.com/yiichu03/SIGN/tree/dad87fe225a4dc1073787d8d2cc83f67e61c0a9d)|当前无命名工作树|
|[phase2/frozen-coverage-settle32](https://github.com/yiichu03/SIGN/tree/phase2/frozen-coverage-settle32)|覆盖32结算奖励，PPO rollout仍256|`a7cc9e0`|[a7cc9e0](https://github.com/yiichu03/SIGN/tree/a7cc9e09fe3c0a9abfa054307cfb80474217d1a2)|`SIGN-frozen-coverage-settle32`|
|[phase2/frozen-rollout-coverage](https://github.com/yiichu03/SIGN/tree/phase2/frozen-rollout-coverage)|覆盖256奖励；远端包含后续资料发布|`6983c91`|[b39e362](https://github.com/yiichu03/SIGN/tree/b39e3626aae31125f018a81b047a593da71e468b)|`SIGN-frozen-rollout-coverage`|
|[phase2/frozen-visual-encoder](https://github.com/yiichu03/SIGN/tree/phase2/frozen-visual-encoder)|仅加载冻结公开visual_encoder的训练基线|`dac8609`|[dac8609](https://github.com/yiichu03/SIGN/tree/dac8609ee1dc3e71ad317998a2f5086a1935e84b)|`SIGN`|
|[phase2/inference-coverage256-recovery](https://github.com/yiichu03/SIGN/tree/phase2/inference-coverage256-recovery)|切换到正确125.952M覆盖底座，旧规则完整验证|`96f7783`|[96f7783](https://github.com/yiichu03/SIGN/tree/96f7783a28ff1beaea86370516f6c1987d9aabac)|`SIGN-inference-coverage256`|
|[phase2/inference-recovery-active-view](https://github.com/yiichu03/SIGN/tree/phase2/inference-recovery-active-view)|早期主动扫描与Qwen问题排查|`1ec9a17`|[1ec9a17](https://github.com/yiichu03/SIGN/tree/1ec9a17d73deef954b5c2c8d9ad0d4b1fc03c873)|`SIGN-inference-active-view`|
|[phase2/inference-recovery-harness](https://github.com/yiichu03/SIGN/tree/phase2/inference-recovery-harness)|最早74.240M冻结基线上的推理恢复|`5e3b0d0`|[5e3b0d0](https://github.com/yiichu03/SIGN/tree/5e3b0d0799645affbbd32db81e0b0912f2cee1cb)|`SIGN-inference-harness`|
|[phase2/qwen-beta003-geometry128](https://github.com/yiichu03/SIGN/tree/phase2/qwen-beta003-geometry128)|A Qwen128、B Qwen256 beta0.03和C几何128共用源码|`d2352f0`|[f00c15c](https://github.com/yiichu03/SIGN/tree/f00c15cb22a3fdcd6a2a5187f1e47e537fbac1b8)|`SIGN-qwen-ablation`|
|[phase2/qwen-candidate-recovery](https://github.com/yiichu03/SIGN/tree/phase2/qwen-candidate-recovery)|当前推理框架开发与资料发布；f0e为已测运行版，下一轮先讨论|`294f651`|[294f651](https://github.com/yiichu03/SIGN/tree/294f651f6ed4cf9e3a7724d2d813da371b697039)|`SIGN-qwen-candidate-recovery`|
|[phase2/qwen-history-window](https://github.com/yiichu03/SIGN/tree/phase2/qwen-history-window)|128/256历史图离线对照，固线版本453179c|`453179c`|[453179c](https://github.com/yiichu03/SIGN/tree/453179cd67c348576d974aa7bf38203044a7eef6)|`SIGN-qwen-history-window`|
|[phase2/qwen-topdown-judge](https://github.com/yiichu03/SIGN/tree/phase2/qwen-topdown-judge)|独立单图top-down评分、2B/9B离线诊断|`b1c24dc`|[b1c24dc](https://github.com/yiichu03/SIGN/tree/b1c24dc16038b10df919a1965d35880f4f143ee1)|`SIGN-qwen-topdown-judge`|
|[phase2/qwen128-reward-beta01](https://github.com/yiichu03/SIGN/tree/phase2/qwen128-reward-beta01)|Qwen128 beta0.1辅助奖励原训练及资料|`81fedec`|[33e30d2](https://github.com/yiichu03/SIGN/tree/33e30d28eecdcce557b0f453004a35de0bdebcbf)|`SIGN-qwen128-reward`|

### 固定提交工作树

|目录|HEAD|用途|
|---|---|---|
|`SIGN-coverage-eval`|`a7cc9e0`|只读原生评估|
|`SIGN-coverage-publication`|`b39e362`|资料发布快照|
|`SIGN-qwen-ablation-publication`|`f00c15c`|资料发布快照|
|`SIGN-qwen-iter-consensus-probe`|`78da633`|迭代实验快照，不是新分支|
|`SIGN-qwen-iter-expanded01`|`8c52f61`|迭代实验快照，不是新分支|
|`SIGN-qwen-iter-expanded02`|`78da633`|迭代实验快照，不是新分支|
|`SIGN-qwen-iter-expanded03`|`f0e093c`|迭代实验快照，不是新分支|
|`SIGN-qwen-iter-expanded03_repeat`|`f0e093c`|迭代实验快照，不是新分支|
|`SIGN-qwen-iter-focused-regression`|`f0e093c`|迭代实验快照，不是新分支|
|`SIGN-qwen-iter-round01`|`f6b28a6`|迭代实验快照，不是新分支|
|`SIGN-qwen-iter-round02`|`f2e266a`|迭代实验快照，不是新分支|
|`SIGN-qwen-iter-round03`|`bf52ae7`|迭代实验快照，不是新分支|
|`SIGN-qwen-iter-round04`|`da9de3a`|迭代实验快照，不是新分支|
|`SIGN-qwen-iter-round05`|`efae277`|迭代实验快照，不是新分支|
|`SIGN-qwen-iter-round06`|`6d72ca7`|迭代实验快照，不是新分支|
|`SIGN-qwen128-publication`|`33e30d2`|资料发布快照|

## SIGN-SRU

本地3个命名分支，origin3个；2个工作树，其中0个detached。

|分支|用途|本地HEAD|origin HEAD|命名工作树|
|---|---|---|---|---|
|[docs/qwen-reward-review-20261013](https://github.com/yiichu03/SIGN-SRU/tree/docs/qwen-reward-review-20261013)|较早Qwen奖励研究文档归档|`663b0f9`|[663b0f9](https://github.com/yiichu03/SIGN-SRU/tree/663b0f98dfae45a3b7249ea460e839f3a4160f86)|当前无命名工作树|
|[main](https://github.com/yiichu03/SIGN-SRU/tree/main)|学长SRU基线，保持ba3bb4a|`ba3bb4a`|[ba3bb4a](https://github.com/yiichu03/SIGN-SRU/tree/ba3bb4aa171478dc58254d016d46e6fb72614ee7)|`SIGN-SRU`|
|[phase1/imagenav-qwen-diagnostics](https://github.com/yiichu03/SIGN-SRU/tree/phase1/imagenav-qwen-diagnostics)|SRU研究归档；根src仍为SRU，docs中的SIGN快照不能覆盖它|`dbf6d3c`|[dbf6d3c](https://github.com/yiichu03/SIGN-SRU/tree/dbf6d3cc437cd5c673648ceac6fa2ddad2ee1656)|`SIGN-SRU-reward-review`|

## 本地与远端差异

4个SIGN分支的本地/远端HEAD不同：Habitat-GS、frozen-rollout-coverage、qwen128-reward-beta01、qwen-beta003-geometry128。逐文件审计确认差异只在README/docs：运行目录保留源码提交，远端前进到资料提交；不要为同步文档把资料pull进运行目录。其他本地命名分支与origin在盘点时HEAD一致，没有origin-only分支。

默认push仅yiichu03/SIGN；SIGN-SRU仍使用自己的yiichu03/SIGN-SRU。SIGN upstream=Zichen-Yan/SIGN，只有用户明确要求才推学长仓库。当前main跟踪upstream/main不代表默认向upstream推送。habitat-lab等依赖不计入上述项目分支，也不随本次发布。

原始盘点、提交关系与32+2工作树源码守卫见[evidence](evidence/logs/github_discussion_update_20261108/branch_inventory.json)和[差异复核](evidence/logs/github_discussion_update_20261108/branch_relationship_audit.json)。本次不创建/切换/删除分支，不修改训练源码或预算。
