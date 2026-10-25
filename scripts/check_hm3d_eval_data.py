#!/usr/bin/env python3
"""Check SIGN's HM3D ImageNav episodes and align Matterport scene paths."""

import argparse
import gzip
import json
from pathlib import Path


SPLITS = ("val_easy", "val_medium", "val_hard")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--data-root",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "data",
    )
    args = parser.parse_args()
    root = args.data_root
    episodes_root = root / "datasets/imagenav/hm3d/v1"
    scenes_root = root / "scene_datasets/hm3d"
    scene_paths = set()
    errors = []

    for split in SPLITS:
        split_dir = episodes_root / split
        index = split_dir / f"{split}.json.gz"
        contents = sorted((split_dir / "content").glob("*.json.gz"))
        if not index.is_file() or not contents:
            errors.append(f"{split}: missing index or content files")
            continue
        count = 0
        for path in contents:
            with gzip.open(path, "rt") as handle:
                episodes = json.load(handle)["episodes"]
            count += len(episodes)
            for episode in episodes:
                scene_id = episode["scene_id"]
                prefix = "hm3d/val/"
                if not scene_id.startswith(prefix):
                    errors.append(f"unexpected scene ID: {scene_id}")
                    continue
                scene_paths.add(Path(scene_id[len(prefix) :]))
        print(f"{split}: {len(contents)} content files, {count} episodes")

    missing = []
    for relative in sorted(scene_paths):
        source = scenes_root / "val" / relative
        target_dir = scenes_root / relative.parent
        required_files = (source, source.with_suffix(".navmesh"))
        absent = [path for path in required_files if not path.is_file()]
        if absent:
            missing.extend(map(str, absent))
            continue
        if not target_dir.exists():
            target_dir.symlink_to(Path("val") / relative.parent, target_is_directory=True)
        elif not (target_dir / relative.name).is_file():
            errors.append(f"path conflict: {target_dir}")

    print(f"Scenes referenced: {len(scene_paths)}; missing: {len(missing)}")
    for path in missing[:10]:
        print(f"MISSING {path}")
    if len(missing) > 10:
        print(f"... and {len(missing) - 10} more")
    for error in errors[:10]:
        print(f"ERROR {error}")
    if errors or missing:
        raise SystemExit(1)
    print("HM3D evaluation data is ready.")


if __name__ == "__main__":
    main()
