#!/usr/bin/env python3
"""Fetch pinned GS ImageNav assets in place, with verified reuse and resumption."""
import argparse
import gzip
import hashlib
import json
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

REPO = "RukawaY/gs_scenes"
REVISION = "ea6453855938dd3d4395c4c449fedefb7e6603b7"


def curl(url, destination=None, resume=False):
    args = ["curl", "--fail", "--location", "--silent", "--show-error",
            "--retry", "3", "--connect-timeout", "30", "--max-time", "900", url]
    if resume:
        args += ["--continue-at", "-"]
    if destination is not None:
        subprocess.run(args + ["--output", str(destination)], check=True)
    else:
        return subprocess.check_output(args)


def tree(parent, recursive=False):
    suffix = "/" + parent if parent else ""
    url = f"https://huggingface.co/api/datasets/{REPO}/tree/{REVISION}{suffix}?limit=1000"
    if recursive:
        url += "&recursive=true"
    entries = json.loads(curl(url))
    if len(entries) >= 1000:
        raise RuntimeError(f"Directory requires pagination; refusing incomplete metadata: {parent}")
    return {item["path"]: item for item in entries if item["type"] == "file"}


def digests(path):
    sha = hashlib.sha256()
    blob = hashlib.sha1(f"blob {path.stat().st_size}\0".encode())
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8 * 1024 * 1024), b""):
            sha.update(chunk)
            blob.update(chunk)
    return sha.hexdigest(), blob.hexdigest()


def verify(path, meta):
    if path.stat().st_size != meta["size"]:
        raise RuntimeError(f"Size mismatch; preserving file for inspection: {path}")
    sha, blob = digests(path)
    expected = meta.get("lfs", {}).get("oid", meta["oid"])
    if (sha if "lfs" in meta else blob) != expected:
        raise RuntimeError(f"Hash mismatch; preserving file for inspection: {path}")
    return sha, expected


def fetch(name, meta, root, verify_only):
    path = root / name
    source = f"https://huggingface.co/datasets/{REPO}/resolve/{REVISION}/{name}"
    existed = path.exists()
    if not existed:
        if verify_only:
            raise FileNotFoundError(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        candidate = path.with_name(path.name + ".part")
        # A complete .part may survive an interruption before its final rename.
        if not candidate.exists() or candidate.stat().st_size != meta["size"]:
            if candidate.exists() and candidate.stat().st_size > meta["size"]:
                raise RuntimeError(f"Oversized partial file; preserving: {candidate}")
            curl(source, candidate, resume=candidate.exists())
        sha, expected = verify(candidate, meta)
        candidate.rename(path)
    else:
        sha, expected = verify(path, meta)
    return {"path": name, "bytes": meta["size"], "sha256": sha,
            "upstream_hash": expected, "url": source, "reused": existed}


def check_episodes(root, splits, scenes=None):
    summary = {}
    for split in splits:
        paths = ([root / f"episodes/imagenav/{split}/content/{scene}.json.gz" for scene in scenes]
                 if scenes else sorted((root / f"episodes/imagenav/{split}/content").glob("*.json.gz")))
        count = 0
        for path in paths:
            scene = path.name.removesuffix(".json.gz")
            with gzip.open(path, "rt") as f:
                episodes = json.load(f)["episodes"]
            expected = f"gs_scenes/{split}/{scene}/{scene}.gs.ply"
            if not episodes or any(ep["scene_id"] != expected for ep in episodes):
                raise RuntimeError(f"Unexpected or empty episode scene references: {path}")
            if len({ep["episode_id"] for ep in episodes}) != len(episodes):
                raise RuntimeError(f"Duplicate episode IDs in {path}")
            for ext in ("gs.ply", "navmesh"):
                if not (root / split / scene / f"{scene}.{ext}").is_file():
                    raise FileNotFoundError(f"Missing {ext} for {path}")
            count += len(episodes)
        summary[split] = {"scenes": len(paths), "episodes": count}
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    selection = parser.add_mutually_exclusive_group()
    selection.add_argument("--scene")
    selection.add_argument("--all-scenes", action="store_true", help="Both train and val ImageNav splits")
    parser.add_argument("--split", choices=["train", "val"], default="val")
    parser.add_argument("--root", type=Path, default=Path("data/scene_datasets/gs_scenes"))
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=4, choices=range(1, 9))
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--plan-only", action="store_true", help="List totals without changing data or manifest")
    mode.add_argument("--verify-only", action="store_true", help="Recheck files without downloading")
    args = parser.parse_args()
    if args.scene is None:
        args.scene = "scene56"
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
    if args.all_scenes:
        for split in ("train", "val"):
            entries.update({name: meta for name, meta in tree(split, recursive=True).items()
                            if name.endswith((".gs.ply", ".navmesh"))})
        entries.update(tree("episodes/imagenav", recursive=True))
        entries.update({name: meta for name, meta in tree("").items()
                        if name in ("train.scene_dataset_config.json", "val.scene_dataset_config.json")})
        entries.update({name: meta for name, meta in tree("configs").items()
                        if name in ("configs/ddppo_imagenav_gs_train.yaml", "configs/ddppo_imagenav_gs_eval.yaml")})
        names = sorted(entries)
        if len(names) != 393:
            raise RuntimeError(f"Unexpected pinned ImageNav file count: {len(names)}")
    else:
        for parent in sorted({str(Path(name).parent) for name in names}):
            entries.update({name: meta for name, meta in tree(parent).items() if name in names})
    missing = set(names) - entries.keys()
    if missing:
        raise RuntimeError(f"Missing official metadata: {sorted(missing)}")

    manifest = {"repo": REPO, "revision": REVISION,
                "scene": "all" if args.all_scenes else args.scene,
                "split": "train,val" if args.all_scenes else args.split,
                "root": str(args.root.resolve()), "files": []}
    if args.manifest.exists():
        previous = json.loads(args.manifest.read_text())
        if any(previous.get(k) != manifest[k] for k in ("repo", "revision", "scene", "split", "root")):
            raise RuntimeError("Use a distinct manifest for a different data selection")
    total = sum(entries[name]["size"] for name in names)
    present = sum((args.root / name).is_file() for name in names)
    print(f"Selection: {len(names)} files, {total} bytes; {present} already present", flush=True)
    if args.plan_only:
        return
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = [pool.submit(fetch, name, entries[name], args.root, args.verify_only) for name in names]
        try:
            for future in as_completed(futures):
                record = future.result()
                manifest["files"].append(record)
                print(f"Verified {len(manifest['files'])}/{len(names)} {record['path']}: "
                      f"{record['bytes']} bytes ({'reused' if record['reused'] else 'downloaded'})", flush=True)
        except BaseException:
            for future in futures:
                future.cancel()
            raise
    manifest["files"].sort(key=lambda item: item["path"])
    summary = check_episodes(args.root, ("train", "val") if args.all_scenes else (args.split,),
                             None if args.all_scenes else [args.scene])
    if args.all_scenes and summary != {"train": {"scenes": 110, "episodes": 110000},
                                      "val": {"scenes": 19, "episodes": 1900}}:
        raise RuntimeError(f"Official inventory mismatch: {summary}")
    manifest["summary"] = summary
    manifest["episode_count"] = sum(item["episodes"] for item in summary.values())
    manifest["total_bytes"] = total
    manifest["verified_at_utc"] = datetime.now(timezone.utc).isoformat()
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.manifest.with_name(args.manifest.name + ".part")
    temporary.write_text(json.dumps(manifest, indent=2) + "\n")
    temporary.replace(args.manifest)
    print(f"Verified official episode inventory: {summary}; no episode regeneration.")


if __name__ == "__main__":
    main()
