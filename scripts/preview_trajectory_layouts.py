#!/usr/bin/env python3
"""Compare full-episode visual layouts without changing any Qwen input files."""

import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
from matplotlib.colors import Normalize
from matplotlib.patches import Patch
from matplotlib.offsetbox import AnnotationBbox, OffsetImage
import numpy as np
from PIL import Image
from scipy.ndimage import rotate
from habitat.utils.visualizations import maps


COLORS = ["#6423b9", "#0f55d7", "#008741", "#eb8c00", "#d2232d"]


def read_case(folder):
    payload = json.loads((folder / "waypoints.json").read_text())
    points = payload["waypoints"]
    xy = np.array([[p["map_col"], p["map_row"]] for p in points], dtype=float)
    steps = np.array([p["step"] for p in points])
    image = np.asarray(Image.open(folder / "trajectory.png").convert("RGB"))
    lo, hi = xy.min(axis=0), xy.max(axis=0)
    margin = max(20., max(hi - lo) * .10)
    # A single crop/scale is shared by all panels of this episode.
    bounds = (lo[0] - margin, hi[0] + margin, lo[1] - margin, hi[1] + margin)
    return points, xy, steps, image, bounds


def axes_style(ax, bounds):
    x0, x1, y0, y1 = bounds
    ax.set(xlim=(x0, x1), ylim=(y1, y0), aspect="equal")
    ax.set_xticks([])
    ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_visible(False)


def path(ax, xy, steps, maximum, width=2.5, color=None):
    if len(xy) < 2:
        return
    boundaries = np.linspace(0, maximum, 6).astype(int)[1:]
    colors = color or [COLORS[min(4, int(np.searchsorted(boundaries, s)))] for s in steps[1:]]
    segments = np.stack([xy[:-1], xy[1:]], axis=1)
    ax.add_collection(LineCollection(segments, colors=colors, linewidths=width,
                                     capstyle="round", joinstyle="round", zorder=3))


def heading(ax, point, zoom=.115):
    sprite = rotate(maps.AGENT_SPRITE, point["heading_rad"] * 180 / np.pi)
    ax.add_artist(AnnotationBbox(OffsetImage(sprite, zoom=zoom),
                  (point["map_col"], point["map_row"]), frameon=False, zorder=6))


def endpoints(ax, xy):
    ax.scatter(*xy[0], s=45, c="#151515", marker="o", zorder=7)
    ax.scatter(*xy[-1], s=65, facecolors="white", edgecolors="#151515",
               linewidths=1.5, marker="s", zorder=7)


def legend(fig, maximum, y=.065):
    edges = np.linspace(0, maximum, 6).astype(int)
    handles = [Patch(color=color, label=f"{edges[i] + 1}–{edges[i+1]}")
               for i, color in enumerate(COLORS)]
    fig.legend(handles=handles, title="STEP INTERVAL", loc="lower center",
               bbox_to_anchor=(.5, y), ncol=5, frameon=False, fontsize=11,
               title_fontsize=10, handlelength=2)


def focus(folder, output):
    points, xy, steps, original, bounds = read_case(folder)
    n = len(points)
    fig = plt.figure(figsize=(11, 6.8), dpi=130, facecolor="white")
    fig.text(.055, .95, "A  |  Focused trajectory + scene context", fontsize=19, weight="bold")
    fig.text(.055, .912, f"{folder.parent.name}/{folder.name}  ·  {n} steps", color="#555555", fontsize=11)
    ax = fig.add_axes([.055, .25, .69, .58])
    # Draw the exact saved coordinates on a clean canvas. The context panel
    # retains the existing map geometry without filtering or inpainting.
    axes_style(ax, bounds)
    path(ax, xy, steps, n)
    indices = sorted(set([0] + [max(0, int(i * n / 5) - 1) for i in range(1, 6)]))
    for i in indices:
        heading(ax, points[i], .15)
    endpoints(ax, xy)
    # Put labels into two clear lanes, outside the colored route.
    by_height = sorted(indices, key=lambda i: xy[i, 1])
    middle = len(by_height) // 2
    for members, lane in ((by_height[:middle], 1.09), (by_height[middle:], -.12)):
        group = sorted(members, key=lambda i: xy[i, 0])
        for fraction, i in zip(np.linspace(.12, .88, len(group)), group):
            text = str(steps[i])
            if i == 0:
                text += " START"
            if i == n - 1:
                text += " END"
            ax.annotate(text, xy=xy[i], xytext=(fraction, lane),
                        textcoords="axes fraction", ha="center", va="center",
                        fontsize=12, weight="bold", color="#202020",
                        arrowprops=dict(arrowstyle="-", color="#7c7c7c", lw=.8),
                        annotation_clip=False,
                        bbox=dict(facecolor="white", edgecolor="none", pad=2))
    inset = fig.add_axes([.78, .38, .2, .37])
    inset.imshow(Image.fromarray(original).convert("L"), cmap="gray", vmin=0, vmax=255)
    axes_style(inset, bounds)
    inset.set_title("Scene context\n(same crop, grayscale)", fontsize=10)
    inset.axis("off")
    legend(fig, n, .055)
    fig.text(.5, .025, "Arrows: saved heading. Labels: saved steps. First recorded pose is step 1.",
             ha="center", color="#555555", fontsize=10)
    fig.savefig(output, facecolor="white")
    plt.close(fig)


def phases(folder, output):
    points, xy, steps, original, bounds = read_case(folder)
    n = len(points)
    fig, axes = plt.subplots(3, 2, figsize=(11, 9), dpi=130, facecolor="white")
    fig.subplots_adjust(left=.05, right=.97, bottom=.075, top=.87, hspace=.43, wspace=.14)
    fig.text(.05, .955, "B  |  Full episode + chronological views", fontsize=19, weight="bold")
    fig.text(.05, .917, f"{folder.parent.name}/{folder.name}  ·  {n} steps  ·  identical bounds and scale in every panel",
             color="#555555", fontsize=11)
    axes = axes.ravel()
    for ax in axes:
        axes_style(ax, bounds)
        ax.plot(xy[:, 0], xy[:, 1], color="#e0e0e0", lw=1.8, zorder=1)
    path(axes[0], xy, steps, n, width=2.3)
    endpoints(axes[0], xy)
    axes[0].set_title(f"Complete route | steps 1–{n}", loc="left", fontsize=12, weight="bold", pad=12)
    heading(axes[0], points[0])
    heading(axes[0], points[-1])
    edges = np.linspace(0, n, 6).astype(int)
    for section, ax in enumerate(axes[1:]):
        a, b = edges[section], edges[section+1]
        # Include the previous position to display the first transition.
        begin = max(0, a - 1)
        path(ax, xy[begin:b], steps[begin:b], n, width=2.8, color=COLORS[section])
        endpoints(ax, xy[a:b])
        for i in sorted(set([a, (a+b-1)//2, b-1])):
            heading(ax, points[i])
        ax.set_title(f"{section+1}.  steps {a+1}–{b}", loc="left", fontsize=12,
                     color=COLORS[section], weight="bold", pad=12)
    fig.text(.5, .035, "Grey: full-route reference. Color: current interval. Dot / square: interval start / end. Arrows: heading.",
             ha="center", color="#555555", fontsize=10)
    fig.savefig(output, facecolor="white")
    plt.close(fig)


def white_gradient(folder, output):
    payload = json.loads((folder / "waypoints.json").read_text())
    points = payload["waypoints"]
    xy = np.array([[p["map_col"], p["map_row"]] for p in points], dtype=float)
    steps = np.array([p["step"] for p in points])
    maximum = int(steps[-1])
    lo, hi = xy.min(axis=0), xy.max(axis=0)
    margin = max(12., max(hi - lo) * .07)
    bounds = (lo[0] - margin, hi[0] + margin, lo[1] - margin, hi[1] + margin)
    fig = plt.figure(figsize=(10, 6), dpi=140, facecolor="white")
    fig.text(.055, .945, f"{folder.parent.name} / {folder.name}  ·  {maximum} steps",
             fontsize=12, color="#333333")
    ax = fig.add_axes([.055, .22, .89, .63])
    axes_style(ax, bounds)
    norm = Normalize(vmin=0, vmax=maximum)
    segments = np.stack([xy[:-1], xy[1:]], axis=1)
    route = LineCollection(segments, cmap="turbo", norm=norm,
                           linewidths=2.5, capstyle="round", joinstyle="round")
    route.set_array(steps[1:])
    ax.add_collection(route)
    indices = sorted(set([0] + [max(0, int(i * len(points) / 5) - 1) for i in range(1, 6)]))
    for i in indices:
        heading(ax, points[i], .12)
    endpoints(ax, xy)
    by_height = sorted(indices, key=lambda i: xy[i, 1])
    middle = len(by_height) // 2
    for members, lane in ((by_height[:middle], 1.055), (by_height[middle:], -.075)):
        group = sorted(members, key=lambda i: xy[i, 0])
        for fraction, i in zip(np.linspace(.12, .88, len(group)), group):
            text = str(steps[i])
            if i == 0:
                text += " START"
            if i == len(points) - 1:
                text += " END"
            ax.annotate(text, xy=xy[i], xytext=(fraction, lane),
                        textcoords="axes fraction", ha="center", va="center",
                        fontsize=11, weight="bold", color="#252525",
                        arrowprops=dict(arrowstyle="-", color="#999999", lw=.65),
                        annotation_clip=False)
    color_ax = fig.add_axes([.16, .08, .68, .026])
    colorbar = fig.colorbar(route, cax=color_ax, orientation="horizontal")
    colorbar.set_ticks(np.linspace(0, maximum, 6))
    colorbar.outline.set_visible(False)
    colorbar.ax.tick_params(labelsize=10, length=3, color="#666666")
    colorbar.set_label("step", fontsize=10, labelpad=4)
    fig.savefig(output, facecolor="white")
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("episode_dir", type=Path)
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("--layout", choices=("all", "focus", "phases", "white_gradient"), default="all")
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    stem = f"{args.episode_dir.parent.name}_{args.episode_dir.name}"
    for name, renderer in (("focus", focus), ("phases", phases), ("white_gradient", white_gradient)):
        if args.layout not in ("all", name):
            continue
        output = args.output_dir / f"{stem}_{name}.png"
        renderer(args.episode_dir, output)
        print(output, flush=True)


if __name__ == "__main__":
    main()
