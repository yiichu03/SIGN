#!/usr/bin/env python3
"""Fetch a pinned official GS ImageNav scene without a second asset cache."""
import argparse
import gzip
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

REPO = "RukawaY/gs_scenes"
REVISION = "ea6453855938dd3d4395c4c449fedefb7e6603b7"


def curl(url, destination=None):
    args = ["curl", "--fail", "--location", "--silent", "--show-error",
            "--retry", "3", "--connect-timeout", "30", "--max-time", "900", url]
    if destination is not None:
        subprocess.run(args + ["--output", str(destination)], check=True)
    else:
        return subprocess.check_output(args)


def digests(path):
    sha = hashlib.sha256()
    blob = hashlib.sha1(f"blob {path.stat().st_size}\0".encode())
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8 * 1024 * 1024), b""):
            sha.update(chunk)
            blob.update(chunk)
    return sha.hexdigest(), blob.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scene", default="scene56")
    parser.add_argument("--split", choices=["train", "val"], default="val")
    parser.add_argument("--root", type=Path, default=Path("data/scene_datasets/gs_scenes"))
    parser.add_argument("--manifest", type=Path, required=True)
    args = parser.parse_args()
    if not args.scene.replace("_", "").isalnum():
        parser.error("scene must be a simple scene name")
    names = [
        f"{args.split}.scene_dataset_config.json",
        f"{args.split}/{args.scene}/{args.scene}.gs.ply",
        f"{args.split}/{args.scene}/{args.scene}.navmesh",
        f"episodes/imagenav/{args.split}/{args.split}.json.gz",
        f"episodes/imagenav/{args.split}/content/{args.scene}.json.gz",
        "configs/ddppo_imagenav_gs_eval.yaml",
    ]
    entries = {}
    for parent in sorted({str(Path(name).parent) for name in names}):
        suffix = "" if parent == "." else "/" + parent
        url = f"https://huggingface.co/api/datasets/{REPO}/tree/{REVISION}{suffix}?limit=1000"
        for item in json.loads(curl(url)):
            if item["path"] in names:
                entries[item["path"]] = item
    missing = set(names) - entries.keys()
    if missing:
        raise RuntimeError(f"Missing official metadata: {sorted(missing)}")

    manifest = {"repo": REPO, "revision": REVISION, "scene": args.scene,
                "split": args.split, "root": str(args.root.resolve()), "files": []}
    if args.manifest.exists():
        previous = json.loads(args.manifest.read_text())
        if any(previous.get(k) != manifest[k] for k in ("repo", "revision", "scene", "split", "root")):
            raise RuntimeError("Use a distinct manifest for a different data selection")
    for name in names:
        meta = entries[name]
        path = args.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        source = f"https://huggingface.co/datasets/{REPO}/resolve/{REVISION}/{name}"
        existed = path.exists()
        candidate = path if existed else path.with_name(path.name + ".part")
        if not existed:
            curl(source, candidate)
        sha, blob = digests(candidate)
        expected = meta.get("lfs", {}).get("oid", meta["oid"])
        actual = sha if "lfs" in meta else blob
        if candidate.stat().st_size != meta["size"] or actual != expected:
            raise RuntimeError(f"Integrity mismatch; preserving file for inspection: {candidate}")
        if not existed:
            candidate.rename(path)
        manifest["files"].append({"path": name, "bytes": meta["size"], "sha256": sha,
                                  "upstream_hash": expected, "url": source})
        print(f"Verified {name}: {meta['size']} bytes", flush=True)
    episode_path = args.root / names[4]
    with gzip.open(episode_path, "rt") as f:
        episodes = json.load(f)["episodes"]
    expected_scene = f"gs_scenes/{args.split}/{args.scene}/{args.scene}.gs.ply"
    if not episodes or any(ep["scene_id"] != expected_scene for ep in episodes):
        raise RuntimeError("Unexpected or empty episode scene references")
    manifest["episode_count"] = len(episodes)
    manifest["verified_at_utc"] = datetime.now(timezone.utc).isoformat()
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"Verified {len(episodes)} official episodes; no episode regeneration.")


if __name__ == "__main__":
    main()
