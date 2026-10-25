#!/usr/bin/env python3
"""Save the exact text input and a Markdown review sheet for one trajectory."""

import argparse
import json
from pathlib import Path


def build_prompt(payload, modality="image_json"):
    """Use the same four questions for all three input conditions."""
    introductions = {
        "image_only": (
            "你只会看到一张完整 ImageNav episode 的俯视轨迹图。图中 START 和 END 是起终点，"
            "蓝色靠近起点、橙色靠近终点；数字是 step，箭头表示朝向。"
        ),
        "json_only": (
            "你只会看到一条完整 ImageNav episode 的 waypoint JSON。waypoint 是每次动作执行后的"
            "位置、朝向和动作；map_row/map_col 是俯视图像素坐标。"
        ),
        "image_json": (
            "你会看到一张完整 ImageNav episode 的俯视轨迹图和对应的 waypoint JSON。"
            "图中 START 和 END 是起终点，蓝色靠近起点、橙色靠近终点；数字是 step，箭头表示朝向。"
            "waypoint 是每次动作执行后的位置、朝向和动作；map_row/map_col 是俯视图像素坐标。"
        ),
    }
    prompt = (
        introductions[modality] + "\n"
        "请区分冗余探索和重复路径。重复路径指再次经过已经走过的路段，包括反向经过；"
        "重复路径本身不一定是冗余探索。退出死胡同、去往新区域或改变观察方向可能是合理重访。"
        "现有材料不足时可以回答无法判断。\n"
        "请严格用中文回答四行：\n"
        "判断：有冗余探索行为 / 无冗余探索行为 / 无法判断冗余探索行为\n"
        "大致step区间：如果有则给出大致区间，否则写无或无法判断\n"
        "重复路径：有 / 无 / 无法判断\n"
        "依据：指出能支持上述判断的具体轨迹行为，简短回答。"
    )
    if modality != "image_only":
        prompt += "\n\nwaypoint JSON:\n" + json.dumps(
            payload, ensure_ascii=False, separators=(",", ":")
        )
    return prompt


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("episode_dir", type=Path)
    parser.add_argument("--model", default="Qwen/Qwen3.5-9B")
    parser.add_argument("--latency-seconds", type=float)
    args = parser.parse_args()

    folder = args.episode_dir
    payload = json.loads((folder / "waypoints.json").read_text(encoding="utf-8"))
    prompt = build_prompt(payload, "image_json")
    (folder / "request.txt").write_text(prompt, encoding="utf-8")

    response_path = folder / "response.txt"
    response = response_path.read_text(encoding="utf-8") if response_path.exists() else "（待运行 Qwen）"
    latency = f"{args.latency_seconds:.2f} s" if args.latency_seconds is not None else "待记录"
    report = f"""# Episode {payload['episode_id']} 审核

- 场景：`{payload['scene_id']}`
- 模型：`{args.model}`
- 推理耗时：{latency}
- 实际输入：[request.txt](request.txt)（完整提示词和 JSON）、[waypoints.json](waypoints.json)

## 俯视轨迹

![轨迹，带 step 和朝向](trajectory.png)

## 模型原始输出

```text
{response}
```

原始文件：[response.txt](response.txt)

## 人工复核

- 我的判断：□ 有冗余探索行为  □ 无冗余探索行为  □ 无法判断
- 是否有重复路径：□ 有  □ 无  □ 无法判断
- Qwen 判断是否合理：□ 是  □ 否  □ 部分合理
- 我认为的区间：
- 依据与备注：
"""
    (folder / "review.md").write_text(report, encoding="utf-8")
    print(folder / "review.md")


if __name__ == "__main__":
    main()
