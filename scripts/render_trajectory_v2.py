#!/usr/bin/env python3
"""Create a clearer trajectory PNG from an existing ImageNav trace."""

import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from habitat.utils.visualizations import maps


FONT_PATH = "/usr/share/fonts/dejavu-sans-fonts/DejaVuSans-Bold.ttf"
TIME_COLORS = (
    (100, 35, 185),   # purple
    (15, 85, 215),    # blue
    (0, 135, 65),     # green
    (235, 140, 0),    # orange
    (210, 35, 45),    # red
)


def time_color(fraction):
    """Use five distinct time bins that match the labeled legend."""
    return TIME_COLORS[min(len(TIME_COLORS) - 1, int(fraction * len(TIME_COLORS)))]


def label(draw, image_size, anchor, text, font, occupied):
    """Place a high contrast step label near its marker."""
    x, y = anchor
    bounds = draw.textbbox((0, 0), text, font=font)
    width, height = bounds[2] - bounds[0] + 12, bounds[3] - bounds[1] + 10
    options = []
    for gap in (10, 35, 65, 95):
        options.extend(((gap, -height - gap), (gap, gap),
                        (-width - gap, -height - gap), (-width - gap, gap),
                        (gap, -height // 2), (-width - gap, -height // 2)))
    chosen = None
    for dx, dy in options:
        left = max(2, min(image_size[0] - width - 2, x + dx))
        top = max(2, min(image_size[1] - height - 2, y + dy))
        box = (left, top, left + width, top + height)
        if all(box[2] + 3 < other[0] or box[0] > other[2] + 3 or
               box[3] + 3 < other[1] or box[1] > other[3] + 3 for other in occupied):
            chosen = box
            break
    if chosen is None:
        chosen = box
    occupied.append(chosen)
    left, top, right, bottom = chosen
    target_x = left if x < left else right if x > right else x
    target_y = top if y < top else bottom if y > bottom else y
    draw.line((x, y, target_x, target_y), fill=(35, 35, 35), width=1)
    draw.rectangle(chosen, fill="white", outline=(15, 15, 15), width=2)
    draw.text((left + 6, top + 4 - bounds[1]), text, fill=(0, 0, 0), font=font)


def render(folder):
    payload = json.loads((folder / "waypoints.json").read_text(encoding="utf-8"))
    points = payload["waypoints"]
    original = Image.open(folder / "trajectory.png").convert("RGB")
    width, height = original.size
    # The original image already has a route. Filter its thin line and labels
    # away so the new temporal encoding has only one visible route.
    floor = original.convert("L").filter(ImageFilter.MedianFilter(size=15)).convert("RGB")
    canvas = Image.new("RGB", (width, height + 92), "white")
    canvas.paste(floor, (0, 0))
    draw = ImageDraw.Draw(canvas)
    total = len(points)

    for i in range(1, total):
        previous, current = points[i - 1], points[i]
        segment = (previous["map_col"], previous["map_row"],
                   current["map_col"], current["map_row"])
        draw.line(segment, fill=time_color(i / max(total - 1, 1)), width=4)

    font = ImageFont.truetype(FONT_PATH, 18)
    small_font = ImageFont.truetype(FONT_PATH, 15)
    key_indices = sorted(set(round(i * (total - 1) / 8) for i in range(9)))
    marked = np.asarray(canvas).copy()
    for index in key_indices:
        point = points[index]
        maps.draw_agent(marked, (point["map_row"], point["map_col"]),
                        point["heading_rad"], agent_radius_px=7)
    canvas = Image.fromarray(marked)
    draw = ImageDraw.Draw(canvas)
    occupied = []
    for index in key_indices:
        point = points[index]
        x, y = point["map_col"], point["map_row"]
        color = time_color(index / max(total - 1, 1))
        draw.ellipse((x - 8, y - 8, x + 8, y + 8), outline=color, width=3)

    first = points[0]
    start_x, start_y = first["map_col"], first["map_row"]
    original_pixels = np.asarray(original)
    green = ((original_pixels[:, :, 1] > 110) &
             (original_pixels[:, :, 1] > original_pixels[:, :, 0] * 1.4) &
             (original_pixels[:, :, 1] > original_pixels[:, :, 2] * 1.4))
    ys, xs = np.where(green)
    if len(xs):
        distances = (xs - start_x) ** 2 + (ys - start_y) ** 2
        nearby = distances < 18 ** 2
        if nearby.any():
            start_x = int(np.median(xs[nearby]))
            start_y = int(np.median(ys[nearby]))
    draw.ellipse((start_x - 7, start_y - 7, start_x + 7, start_y + 7),
                 fill=(0, 175, 0), outline="white", width=2)
    label(draw, (width, height), (start_x, start_y), "START 0", small_font, occupied)

    last = points[-1]
    end_x, end_y = last["map_col"], last["map_row"]
    draw.ellipse((end_x - 7, end_y - 7, end_x + 7, end_y + 7),
                 fill=(230, 30, 20), outline="white", width=2)
    label(draw, (width, height), (end_x, end_y), f"END {total}", small_font, occupied)
    for index in key_indices:
        if index == total - 1:
            continue
        point = points[index]
        label(draw, (width, height), (point["map_col"], point["map_row"]),
              str(point["step"]), font, occupied)

    # A dedicated legend keeps its numbers clear of the map and tells Qwen
    # exactly how the route color corresponds to time.
    draw.rectangle((0, height, width, height + 91), fill="white")
    draw.line((0, height, width, height), fill=(20, 20, 20), width=2)
    draw.text((15, height + 7), "TIME (step): purple → blue → green → orange → red", font=small_font, fill=(0, 0, 0))
    left, right = 25, width - 25
    for section, color in enumerate(TIME_COLORS):
        x0 = round(left + (right - left) * section / len(TIME_COLORS))
        x1 = round(left + (right - left) * (section + 1) / len(TIME_COLORS))
        draw.rectangle((x0, height + 35, x1, height + 52), fill=color)
    draw.rectangle((left, height + 35, right, height + 52), outline=(20, 20, 20), width=1)
    for section in range(len(TIME_COLORS) + 1):
        x = round(left + (right - left) * section / len(TIME_COLORS))
        value = round(total * section / len(TIME_COLORS))
        text = str(value)
        box = draw.textbbox((0, 0), text, font=small_font)
        draw.line((x, height + 53, x, height + 60), fill=(20, 20, 20), width=2)
        draw.text((x - (box[2] - box[0]) / 2, height + 64), text, font=small_font, fill=(0, 0, 0))

    output = folder / "trajectory_v2.png"
    canvas.save(output)
    print(output)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("episode_dir", type=Path)
    args = parser.parse_args()
    render(args.episode_dir.resolve())


if __name__ == "__main__":
    main()
