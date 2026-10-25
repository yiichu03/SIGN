#!/usr/bin/env python3
"""Render saved waypoint traces as GIFs for human review, without simulation."""

import argparse
import json
from math import ceil
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from habitat.utils.visualizations import maps


HEADER = 42
GIF_NAME = "trajectory.gif"
REVIEW_HEADING = "## 动态轨迹（人工审核）"


def render_episode(folder, max_frames):
    payload = json.loads((folder / "waypoints.json").read_text(encoding="utf-8"))
    points = payload["waypoints"]
    source = Image.open(folder / "trajectory.png").convert("RGB")
    width, height = source.size
    # The saved PNG contains the complete route. A median filter removes its
    # narrow colored lines and step labels while retaining the floor plan.
    floor_plan = source.convert("L").filter(ImageFilter.MedianFilter(size=15))
    pale_map = Image.blend(Image.new("RGB", source.size, "white"), floor_plan.convert("RGB"), 0.42)
    background = Image.new("RGBA", (width, height + HEADER), "white")
    background.paste(pale_map, (0, HEADER))
    trail = Image.new("RGBA", background.size, (0, 0, 0, 0))
    trail_draw = ImageDraw.Draw(trail)

    count = len(points)
    stride = max(1, ceil(count / max_frames))
    frame_steps = set(range(1, count + 1, stride)) | {count}
    start = points[0]
    collision_count = 0
    frames = []
    for i, point in enumerate(points):
        if i:
            previous = points[i - 1]
            fraction = i / max(count - 1, 1)
            if fraction < 0.5:
                shade = fraction * 2
                color = (int(20 + 150 * shade), int(70 - 50 * shade), int(240 - 20 * shade), 255)
            else:
                shade = (fraction - 0.5) * 2
                color = (int(170 + 75 * shade), int(20 + 70 * shade), int(220 - 200 * shade), 255)
            trail_draw.line(
                (previous["map_col"], previous["map_row"] + HEADER,
                 point["map_col"], point["map_row"] + HEADER),
                fill=color, width=4,
            )
        collision_count += bool(point["collision"])
        if i + 1 not in frame_steps:
            continue
        frame = Image.alpha_composite(background, trail).convert("RGB")
        draw = ImageDraw.Draw(frame)
        for j in range(max(1, i - 19), i + 1):
            previous, current = points[j - 1], points[j]
            draw.line(
                (previous["map_col"], previous["map_row"] + HEADER,
                 current["map_col"], current["map_row"] + HEADER),
                fill=(255, 145, 0), width=5,
            )
        draw.rectangle((0, 0, width, HEADER - 1), fill="white")
        draw.text((10, 8), f"Step {point['step']} / {count}    Collisions: {collision_count}", fill=(20, 20, 20))
        draw.rectangle((10, HEADER - 7, width - 10, HEADER - 3), fill=(225, 225, 225))
        draw.rectangle((10, HEADER - 7, 10 + int((width - 20) * (i + 1) / count), HEADER - 3), fill=(230, 90, 30))
        draw.ellipse(
            (start["map_col"] - 5, start["map_row"] + HEADER - 5,
             start["map_col"] + 5, start["map_row"] + HEADER + 5),
            fill=(0, 170, 0), outline="white", width=1,
        )
        marked = np.asarray(frame).copy()
        maps.draw_agent(
            marked, (point["map_row"] + HEADER, point["map_col"]),
            point["heading_rad"], agent_radius_px=8,
        )
        frame = Image.fromarray(marked)
        draw = ImageDraw.Draw(frame)
        ring = (220, 25, 25) if point["collision"] else (30, 80, 230)
        x, y = point["map_col"], point["map_row"] + HEADER
        draw.ellipse((x - 10, y - 10, x + 10, y + 10), outline=ring, width=2)
        if i == count - 1:
            draw.text((x + 12, y + 10), "END", fill=(220, 25, 25), stroke_width=2, stroke_fill="white")
        frames.append(frame.convert("P", palette=Image.Palette.ADAPTIVE, colors=96))

    duration = max(80, min(250, round(12000 / len(frames))))
    durations = [duration] * len(frames)
    durations[-1] = 1500
    output = folder / GIF_NAME
    frames[0].save(
        output, save_all=True, append_images=frames[1:], duration=durations,
        loop=0, optimize=True, disposal=2,
    )

    report_path = folder / "review.md"
    report = report_path.read_text(encoding="utf-8")
    report = report.replace("底图为淡化的完整俯视图，仅供定位。", "底图为淡化的俯视场景，仅供定位。")
    if REVIEW_HEADING not in report:
        insertion = (
            f"{REVIEW_HEADING}\n\n"
            "彩色轨迹逐步显现，橙色突出最近 20 步；蓝色圆环是当前位置，红色圆环表示本步碰撞。"
            "底图为淡化的俯视场景，仅供定位。\n\n"
            f"![按 step 播放的轨迹，包含朝向和碰撞标记]({GIF_NAME})\n\n"
        )
        report = report.replace("## 三组原始回答\n\n", insertion + "## 三组原始回答\n\n", 1)
    report = report.replace(
        "彩色轨迹逐步显现；蓝色圆环是当前位置，红色圆环表示本步碰撞。",
        "彩色轨迹逐步显现，橙色突出最近 20 步；蓝色圆环是当前位置，红色圆环表示本步碰撞。",
    )
    report_path.write_text(report, encoding="utf-8")
    print(f"{folder}: {len(frames)} frames -> {output.stat().st_size / 1024 / 1024:.1f} MiB", flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("target", type=Path, help="One episode directory or the graded batch root")
    parser.add_argument("--max-frames", type=int, default=180)
    args = parser.parse_args()
    target = args.target.resolve()
    if (target / "waypoints.json").exists():
        folders = [target]
    else:
        folders = sorted(target.glob("val_*/episode_*"))
    for folder in folders:
        render_episode(folder, args.max_frames)


if __name__ == "__main__":
    main()
