#!/usr/bin/env python3
"""Prepare the approved white-background figures and aligned v2 review sheets."""

import argparse
import json
from pathlib import Path

from prepare_qwen_review import build_prompt


NEW_CONDITIONS = ("image_only", "image_json")
TITLES = {
    "image_only": "仅 PNG",
    "json_only": "仅 waypoint JSON（复用 v1）",
    "image_json": "PNG + waypoint JSON",
}


def find_cases(root, expected_count):
    cases = [folder for split in ("val_easy", "val_medium", "val_hard")
             for folder in sorted((root / split).glob("episode_*"))
             if (folder / "waypoints.json").exists()]
    if len(cases) != expected_count:
        raise RuntimeError(f"Expected {expected_count} episodes; found {len(cases)}")
    return cases


def build_prompt2(payload, modality):
    introduction = (
        "你只会看到一张完整 ImageNav episode 的俯视轨迹图。"
        if modality == "image_only" else
        "你会看到一张完整 ImageNav episode 的俯视轨迹图和对应的 waypoint JSON。"
    )
    introduction += (
        "图中彩色轨迹按 step 连续渐变，具体时间对应底部色条；"
        "START 是首个已记录位置（step 1），END 是最后记录位置。"
        "数字是 step，小箭头表示该位置的朝向，细灰线仅连接数字标签与对应位置。"
        "纯白背景未显示场景墙体或障碍物。"
    )
    if modality == "image_json":
        introduction += (
            "waypoint 是每次动作执行后的位置、朝向和动作；"
            "map_row/map_col 是原始俯视图像素坐标。"
            "图中轨迹由这些坐标等比例缩放和平移绘制，未旋转；"
            "map_col 向右增加，map_row 向下增加。"
        )
    # Keep the original four questions and JSON serialization exactly unchanged.
    return introduction + "\n" + build_prompt(payload, modality).split("\n", 1)[1]


def write_review2(folder):
    payload = json.loads((folder / "waypoints.json").read_text(encoding="utf-8"))
    rows, sections = [], []
    for modality, title in TITLES.items():
        suffix = "" if modality == "json_only" else "2"
        request = f"request_{modality}{suffix}.txt"
        response_file = f"response_{modality}{suffix}.txt"
        timing_file = f"timing_{modality}{suffix}.json"
        complete = (folder / response_file).exists() and (folder / timing_file).exists()
        if complete:
            timing = json.loads((folder / timing_file).read_text(encoding="utf-8"))
            latency = f"{timing['inference_seconds']:.2f} s"
            response = (folder / response_file).read_text(encoding="utf-8")
            response_link = f"[原始输出]({response_file})"
        else:
            latency, response, response_link = "待运行", "（待运行 Qwen）", "待运行"
        if modality == "json_only":
            latency += "（原运行）"
        rows.append(f"| {title} | {latency} | [输入]({request}) | {response_link} |")
        inputs = f"[{request}]({request})"
        if modality != "json_only":
            inputs += "、[trajectory2.png](trajectory2.png)"
        sections.append(
            f"### {title}\n\n实际输入：{inputs}；推理耗时：{latency}\n\n"
            f"```text\n{response}\n```\n"
        )
    report = (
        f"# {folder.parent.name} / {folder.name} — v2 审核\n\n"
        f"- Habitat episode ID：`{payload['episode_id']}`\n"
        f"- 场景：`{payload['scene_id']}`\n"
        "- 模型：`Qwen/Qwen3.5-9B`\n"
        "- v2：纯白背景、连续 step 渐变、稀疏 step 标签与朝向；未显示墙体或障碍物。\n"
        "- 本次重新推理仅 PNG、PNG + waypoint JSON；纯 JSON 的输入、输出和耗时沿用 v1。\n"
        "- [原版审核 review.md](review.md)；[完整轨迹数据](waypoints.json)\n\n"
        "## v2 模型输入图片\n\n"
        "![纯白底渐变轨迹](trajectory2.png)\n\n"
        "| 输入条件 | 推理耗时 | 实际文本输入 | 模型原始输出 |\n"
        "| --- | ---: | --- | --- |\n" + "\n".join(rows)
        + "\n\n## 三组原始回答\n\n" + "\n".join(sections)
    )
    if (folder / "trajectory.gif").exists():
        report += (
            "\n## 人工审核动画\n\n"
            "沿用原动画，仅供人工查看；未发送给 Qwen。\n\n"
            "![人工审核动态轨迹](trajectory.gif)\n"
        )
    report += (
        "\n## 人工复核\n\n"
        "| 输入条件 | 冗余探索判断是否合理 | 重复路径判断是否合理 | 我认为的大致 step 区间及依据 |\n"
        "| --- | --- | --- | --- |\n"
        "| 仅 PNG |  |  |  |\n"
        "| 仅 waypoint JSON（复用 v1） |  |  |  |\n"
        "| PNG + waypoint JSON |  |  |  |\n\n综合备注：\n"
    )
    (folder / "review2.md").write_text(report, encoding="utf-8")


def write_index2(root, cases):
    lines = [
        "# 纯白底轨迹 v2：60 条 episode，三种输入条件", "",
        "仅 PNG、PNG + waypoint JSON 使用 trajectory2.png 重新推理；纯 JSON 复用 v1。",
        "easy、medium、hard 各 20 条，序列编号与原版一致。每条两项新推理完成后自动更新审核表。", "",
        "| 难度 | 序列 | v2 新推理完成数 | 新版审核 | 原版审核 |",
        "| --- | --- | ---: | --- | --- |",
    ]
    for folder in cases:
        complete = sum((folder / f"response_{mode}2.txt").exists()
                       and (folder / f"timing_{mode}2.json").exists()
                       for mode in NEW_CONDITIONS)
        relative = folder.relative_to(root).as_posix()
        lines.append(f"| {folder.parent.name} | {folder.name} | {complete}/2 | "
                     f"[review2.md]({relative}/review2.md) | [review.md]({relative}/review.md) |")
    (root / "index2.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    parser.add_argument("--expected-count", type=int, default=60)
    args = parser.parse_args()
    root = args.root.resolve()
    cases = find_cases(root, args.expected_count)
    from preview_trajectory_layouts import white_gradient

    for folder in cases:
        for original in ("request_json_only.txt", "response_json_only.txt", "timing_json_only.json"):
            if not (folder / original).is_file():
                raise FileNotFoundError(folder / original)
        output = folder / "trajectory2.png"
        if not output.exists():
            white_gradient(folder, output)
        payload = json.loads((folder / "waypoints.json").read_text(encoding="utf-8"))
        for mode in NEW_CONDITIONS:
            request = folder / f"request_{mode}2.txt"
            if not request.exists():
                request.write_text(build_prompt2(payload, mode), encoding="utf-8")
        if not (folder / "review2.md").exists():
            write_review2(folder)
        print(folder.relative_to(root), flush=True)
    write_index2(root, cases)
    print(f"Prepared {len(cases)} v2 cases", flush=True)


if __name__ == "__main__":
    main()
