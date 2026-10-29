# Qwen2B同宽实线历史窗口：交付与验证

最终作业1506387（CFP/autox/A40），运行代码30ed53d；按用户要求将黄色历史路径与红色当前路径统一为1.5pt实线，只以颜色区分，prompt相应微调并说明完全重合时红线覆盖黄线。此前1505092虚线版资料原封保留在qwen-history-window目录。轨迹/窗口/覆盖统计、FP32/T1/ABC/q及人工标签规则不变。

- [完整报告：128／256、整体历史与黄线对照](REPORT.md)
- [离线审阅页](index.html)：下载ZIP解压后在本地打开；默认隐藏模型分数，可切换显示。
- [评分CSV](scores.csv) · [结果JSON](results.json) · [空白人审CSV](human_review.csv) · [窗口清单](window_list.csv)
- [原始窗口与输入映射](windows.json) · [prompt最小差异](prompts/history.diff) · [复现说明](README.md)
- [实际浏览器验证](validation/browser_check.json) · [像素/面积/哈希验证](validation/bundle_check.json)

64次请求去重44片段：完整128步12段有真实历史；完整256步5段全部无前置历史；短段27个单列。100张实际输入，32张严格复用发布2B旧分数、68张新FP32概率读出。旧分数只有图片SHA/promptSHA/实际metadata一致且同模型配置/FP32/版本时复用。

本数据不能检验256步历史能力；无历史段的分数变化也不代表模型理解历史。报告只描述输入敏感性，不用平均q判优，没有人工真值、准确率或PPO收益结论。重复搜索、必要返回、有效扩展、碰撞受阻仅列待人审线索，标签保持空白。

根四文档的生成快照在workspace，服务器根文件继续作为维护源。原实验/失败/补跑的操作沿革见workspace/WORKLOG.md；原始评分审计在scores，复用的原批次输入/耗时在sources/*_2b_batch_*.json。绘图源均保持原2.5cm/3m/90°，不与导航训练0.1m口径混用。

ZIP实际路径：/scratch/e1538633/liuyi/logs/qwen_history_solid_20261029/qwen2b_history_review.zip；6901870 bytes，SHA256 17179a590ac4648072dc021d82b9473ee230cb57d753a3dd34c1c8c7068c83d6。ZIP通过CRC、全部文件SHA和实际Chromium file://断网浏览，100图片解码、默认隐藏/开关、筛选与空白人审检查通过。
