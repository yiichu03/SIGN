# 恢复框架的正确底座：覆盖256125.952M

用户于2026-11-08纠正：推理恢复应叠加于覆盖256的高SR checkpoint，而非冻结视觉基线74.240M。此前74.240M pilot/full明确作为补充实验，不能冒称覆盖256叠加结果。尚未启动的错误底座Qwen1530921已取消，原源代码、输入和回执保留。原规则1530887已运行一小时多，保留完成记录；不停止其他训练，几何1281511410已按随后用户明确授权停止腾出GPUx。

## 模型与对照身份

- 导航模型：coverage256训练125,952,000步，原ckpt.245.pth；使用已保存独立副本logs/gibson_coverage_latest_eval_20261103/checkpoints/coverage256.pth。
- SHA256：988c9ecc5b0c704e9a4780f636739aec17cbd323d613f0fbdde4699296886c2c。
- 原完整4200验证：SR87.571429%、SPL53.299601%；相对公开完整模型86.00/53.01%仅作已有验证参考。此checkpoint按已有val高SR选择，不是新独立测试模型。
- 每个新任务清单必须显式绑定checkpoint及其原完整native参考目录；核对真实加载step、模型文件SHA、参考checkpoint SHA/step和4200条结果，错配直接失败。每份新结果保存checkpoint路径/SHA/step及参考信息，不再用“SIGN基线”省略模型身份。

## 完整规则验证

使用独立SIGN-inference-coverage256 / phase2/inference-coverage256-recovery，从1ec9a17建立，只修改评估的模型/参考身份绑定和调度。src/trainer.py、policy、网络、恢复检测阈值及动作脚本不变。scripts/run_rule_recovery.py先在固定34开发任务上核对native/off/零干预逐条相等，再在相同4200任务上重新跑off和rule。Full off必须逐任务复现原coverage256完整参考，包含success/SPL/view_match/reward/collisions/steps严格容差门，不因模型错配放宽检查。

同6env/seed100/hash0/max500/原目标图与动作/真实masks与GRU。评估加载全部已训练导航权重，几何bonus0，无Qwen。规则沿用旧不扫描版本：16步视觉/实际动作证据触发，转90度+0.8m，每次10动作、最多两次20动作计入500。两组在同一PBS顺序运行（1A40/36CPU240GB/3h上限），配对比较SR/SPL、覆盖、碰撞、救回/误伤及无直接干预变化，人审字段留空。

## Qwen诊断与确认

相同125.952M覆盖256导航模型，复用已提交主动观察版本：12步采左右前RGB，2B FP32真实ABC读出，保留C，不改原置信度/概率算法。先34开发及两份预先固定prompt诊断；若仍全C，保留证据和解释停止后续，否则新280任务四组off/scan-only/scan-rule/scan-qwen。扫描与真正模型选择动作分开，最多34步计原500。不能把强制扫描或AB率当Qwen收益；不自动提交Qwen4200。

输出根logs/sign_inference_coverage256_20261108/{rule_full,qwen_active}，每批有独立tasks/source_manifest/submission。两套旧运行树固定不动，新运行树提交后固定，不pull后续资料。此次无导航训练、9B或ZIP。
