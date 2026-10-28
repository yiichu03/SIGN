# Gibson跨场景：2B独立概率评分

8个此前未展示的场景×2个不同任务，共16条。任务在采集前固定；官方库存标为单层，端点高度差<0.05m。先选5–8m和8–15m距离区间；后者无候选时选另一较长任务。没有按成功或Qwen分数筛图。公开SIGN权重原生随机动作采样，每条最多256步，提前终止保留实际步数。

[完整CSV](../evidence/probability/diverse_2b/scores.csv) · [JSON与原logits](../evidence/probability/diverse_2b/scores.json) · [选择计划](../evidence/collection/diverse/plan.json) · [Prompt](../prompts/coverage_abc_v1.txt)

| 图片（点击放大） | 场景/任务 | 动作 | 新增m² | m²/动作 | LOW | MEDIUM | HIGH | q |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| <a href="../images/diverse/group_01/C01.png"><img src="../images/diverse/group_01/C01.png" width="230"></a> | Cantwell / 1703 | 250 | 18.6275 | 0.0745 | 0.2122 | 0.2478 | 0.5400 | 0.6639 |
| <a href="../images/diverse/group_01/C02.png"><img src="../images/diverse/group_01/C02.png" width="230"></a> | Eastville / 4101 | 165 | 27.3256 | 0.1656 | 0.1258 | 0.2510 | 0.6232 | 0.7487 |
| <a href="../images/diverse/group_01/C03.png"><img src="../images/diverse/group_01/C03.png" width="230"></a> | Elmira / 2900 | 44 | 7.0763 | 0.1608 | 0.1082 | 0.2120 | 0.6798 | 0.7858 |
| <a href="../images/diverse/group_01/C04.png"><img src="../images/diverse/group_01/C04.png" width="230"></a> | Eudora / 2000 | 256 | 9.5625 | 0.0374 | 0.2340 | 0.2508 | 0.5152 | 0.6406 |
| <a href="../images/diverse/group_01/C05.png"><img src="../images/diverse/group_01/C05.png" width="230"></a> | Greigsville / 2600 | 44 | 10.5325 | 0.2394 | 0.0847 | 0.2068 | 0.7085 | 0.8119 |
| <a href="../images/diverse/group_01/C06.png"><img src="../images/diverse/group_01/C06.png" width="230"></a> | Pablo / 804 | 152 | 12.4100 | 0.0816 | 0.2231 | 0.2142 | 0.5627 | 0.6698 |
| <a href="../images/diverse/group_01/C07.png"><img src="../images/diverse/group_01/C07.png" width="230"></a> | Ribera / 1100 | 44 | 15.1169 | 0.3436 | 0.1041 | 0.2332 | 0.6627 | 0.7793 |
| <a href="../images/diverse/group_01/C08.png"><img src="../images/diverse/group_01/C08.png" width="230"></a> | Swormville / 3201 | 256 | 1.3250 | 0.0052 | 0.2123 | 0.1702 | 0.6175 | 0.7026 |
| <a href="../images/diverse/group_02/C01.png"><img src="../images/diverse/group_02/C01.png" width="230"></a> | Cantwell / 1700 | 72 | 9.8963 | 0.1374 | 0.1168 | 0.2386 | 0.6447 | 0.7640 |
| <a href="../images/diverse/group_02/C02.png"><img src="../images/diverse/group_02/C02.png" width="230"></a> | Eastville / 4102 | 77 | 15.8613 | 0.2060 | 0.0998 | 0.2200 | 0.6801 | 0.7901 |
| <a href="../images/diverse/group_02/C03.png"><img src="../images/diverse/group_02/C03.png" width="230"></a> | Elmira / 2954 | 141 | 12.0456 | 0.0854 | 0.1828 | 0.2779 | 0.5393 | 0.6782 |
| <a href="../images/diverse/group_02/C04.png"><img src="../images/diverse/group_02/C04.png" width="230"></a> | Eudora / 2054 | 256 | 1.4038 | 0.0055 | 0.4772 | 0.2532 | 0.2696 | 0.3962 |
| <a href="../images/diverse/group_02/C05.png"><img src="../images/diverse/group_02/C05.png" width="230"></a> | Greigsville / 2643 | 146 | 21.1381 | 0.1448 | 0.0802 | 0.1877 | 0.7321 | 0.8260 |
| <a href="../images/diverse/group_02/C06.png"><img src="../images/diverse/group_02/C06.png" width="230"></a> | Pablo / 800 | 256 | 15.6719 | 0.0612 | 0.1414 | 0.2473 | 0.6113 | 0.7350 |
| <a href="../images/diverse/group_02/C07.png"><img src="../images/diverse/group_02/C07.png" width="230"></a> | Ribera / 1114 | 256 | 18.0450 | 0.0705 | 0.2741 | 0.2800 | 0.4459 | 0.5859 |
| <a href="../images/diverse/group_02/C08.png"><img src="../images/diverse/group_02/C08.png" width="230"></a> | Swormville / 3200 | 66 | 11.9813 | 0.1815 | 0.1112 | 0.2139 | 0.6749 | 0.7819 |
