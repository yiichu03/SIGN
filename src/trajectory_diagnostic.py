"""Small, offline ImageNav trajectory export for visual inspection."""

import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from habitat.utils.visualizations import maps


def save_observation(folder, observations, step, save_goal=False):
    """Save raw pre-action observations; step 0 is the initial view."""
    folder = Path(folder)
    frames = folder / "rgb"
    frames.mkdir(parents=True, exist_ok=True)
    Image.fromarray(np.asarray(observations['rgb']).astype(np.uint8)).save(
        frames / f"step_{step:04d}.png")
    if save_goal:
        goal = observations['imagegoal_sensor_v2']
        if isinstance(goal, dict):
            goal = goal['goal_image']
        Image.fromarray(np.asarray(goal).astype(np.uint8)).save(folder / 'goal.png')


def waypoint(step, action, info):
    """Record the executed action and the resulting pose before env auto-reset."""
    row, col = info["top_down_map.agent_map_coord"]
    return {
        "step": step,
        "map_row": int(row),
        "map_col": int(col),
        "heading_rad": float(info["top_down_map.agent_angle"]),
        "action": np.asarray(action).reshape(-1).astype(float).tolist(),
        "collision": bool(info.get("collisions.is_collision", False)),
    }


def save_episode(output_dir, episode_index, episode, start, waypoints, info):
    """Write one complete trace as JSON plus a labelled top-down PNG."""
    folder = Path(output_dir) / f"episode_{episode_index:03d}"
    folder.mkdir(parents=True, exist_ok=True)
    payload = {
        "scene_id": episode.scene_id,
        "episode_id": episode.episode_id,
        "coordinate_system": "Habitat top_down_map pixels: row increases downward, col increases rightward",
        "heading_unit": "radians (Habitat top_down_map.agent_angle)",
        "action_order": "[angular_velocity, linear_velocity], normalized SIGN commands",
        "start": start,
        "waypoints": waypoints,
    }
    (folder / "waypoints.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    base = maps.colorize_topdown_map(
        info["top_down_map.map"].copy(), info.get("top_down_map.fog_of_war_mask")
    )
    picture = Image.fromarray(base).convert("RGB")
    draw = ImageDraw.Draw(picture)
    total = len(waypoints)
    # Blue at the start, orange at the end. Every waypoint remains in JSON.
    for index in range(1, total):
        previous, current = waypoints[index - 1], waypoints[index]
        fraction = index / max(total - 1, 1)
        color = (int(30 + 225 * fraction), int(105 + 55 * fraction), int(235 - 185 * fraction))
        draw.line(
            (previous["map_col"], previous["map_row"], current["map_col"], current["map_row"]),
            fill=color,
            width=3,
        )
    for index in sorted(set([0, total - 1] + list(range(0, total, max(1, total // 8))))):
        point = waypoints[index]
        row, col = point["map_row"], point["map_col"]
        marked = np.asarray(picture).copy()
        maps.draw_agent(marked, (row, col), point["heading_rad"], agent_radius_px=6)
        picture = Image.fromarray(marked)
        draw = ImageDraw.Draw(picture)
        draw.text((col + 7, row - 7), str(point["step"]), fill=(0, 0, 0), stroke_width=2, stroke_fill=(255, 255, 255))

    source_pixels = np.argwhere(info["top_down_map.map"] == maps.MAP_SOURCE_POINT_INDICATOR)
    if len(source_pixels):
        start_row, start_col = np.median(source_pixels, axis=0).astype(int)
    else:
        start_row, start_col = waypoints[0]["map_row"], waypoints[0]["map_col"]
    end_row, end_col = waypoints[-1]["map_row"], waypoints[-1]["map_col"]
    for label, row, col, color in (
        ("START (0)", start_row, start_col, (0, 180, 0)),
        (f"END ({total})", end_row, end_col, (220, 25, 25)),
    ):
        draw.ellipse((col - 6, row - 6, col + 6, row + 6), fill=color, outline=(255, 255, 255), width=2)
        draw.text((col + 8, row + 5), label, fill=color, stroke_width=2, stroke_fill=(255, 255, 255))
    picture.save(folder / "trajectory.png")
    return folder
