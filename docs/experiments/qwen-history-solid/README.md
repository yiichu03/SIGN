# 复现与审计

先用浏览器打开本目录index.html；无需服务器或网络，默认不显示分数。手工标签在human_review.csv，所有人工列为空。
原始轨迹在sources/*/trajectory.json.gz（poses[0]为初始观测，动作记录在poses[1:]），含逐步XYZ/朝向/action/collision。
windows.json记录64次请求到去重片段/100张输入的映射；window_list.csv为便于阅读的清单。
当前动作为(start,end]，当前红线路径含两端pose；历史动作为(0,start]。段前累计已见含pose[start]，避免把起点视野重复发奖。
总覆盖=深蓝+浅蓝=段前已见+本段真正新增。mask来自原2.5cm固定楼层栅格、3m/90°视域，原fog原点≤5cm边界投影不变。
初末重放mask须与已发布原NPZ逐像素相同；不修改原轨迹、不从覆盖百分比推算平方米。不同场景各用原图范围，相互对照保持相同1400×1120画布、地图范围与2m比例尺。
完整历史/隐藏黄线仅路径可见性不同，覆盖、统计、prompt与图例相同；黄红均为1.5pt实线，仅以颜色区分，完全重合处红线覆盖黄线，不偏移真实路径。
当前起终点映射到同一格时放大绿色起点，保留终点叉外的绿色圆环；位置没有移动。
legacy从当前起点重置可见集合，新增仅扣当前起点视野；history扣全部段前已见。两者统计语义不同，不能把差分当纯黄线因果。
CSV中的面积字段包含审计量；model_statistics_json是实际送入模型的统计：旧协议三项，历史版另加段前与总覆盖面积。

Git分支phase2/qwen-history-window；运行时代码和提交见audit/provenance.json及code/。
在仓库根、已配置的Habitat CPU环境运行（OUT必须全新）：

    python scripts/prepare_qwen_history.py --source docs/experiments/qwen-topdown --prompt scripts/prompts/qwen_single_coverage_abc.txt --out /new/OUT

在PBS GPU的qwen35环境运行，仅Qwen3.5-2B、FP32，模型只加载一次：

    python scripts/evaluate_qwen_history.py --data /new/OUT --model-dir /path/to/Qwen3.5-2B
    python scripts/package_qwen_history.py --data /new/OUT --zip /new/qwen2b_history_review.zip

复用原SingleImageJudge，temperature=1，q=0.5*p_medium+p_high。模型/环境版本、推理耗时、概率、原logits、padding、token IDs、实际chat统计在scores/。
seconds为批次共享耗时，不是单图独立延迟；复用的旧分数seconds留空，原批次输入与耗时在sources/*_2b_batch_*.json，加载耗时在sources/*_2b_run.json。
只在PNG SHA、prompt SHA、三个统计完全相同，并核对相同2B配置/FP32/版本后复用旧分数。失败会保存scores/run.json错误及partial_results.json，不以零分填充。
本次数据未给出人审真值；输入敏感性和q变化不是准确率，不用平均q判优，不证明导航训练收益。
