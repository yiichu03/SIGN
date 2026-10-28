#!/usr/bin/env python3
"""Run the released SIGN policy on every official Habitat-GS val episode."""
import argparse
import hashlib
import json
import math
import os
import re
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

import habitat_sim
import numpy as np
import torch
import run_sim  # Register the original SIGN implementation and GS adapters.
from habitat_baselines.config.default import get_config
from src.dataset import HabitatGSImageNavDatasetV1
from src.utils import change_habitat_config

CONFIGS = [
    "exp_config/ppo_imagenav_gibson.yaml", "src/config/policy.yaml",
    "src/config/reward.yaml", "src/config/sensors.yaml", "src/config/eval.yaml",
    "exp_config/ppo_imagenav_habitat_gs.yaml",
]
OPTIONS = [
    "habitat_baselines.eval_ckpt_path_dir", "ckpt/nav_model.pth",
    "habitat_baselines.eval.split", "val",
    "habitat_baselines.num_environments", "6",
    "habitat_baselines.test_episode_count", "1900",
    "habitat.dataset.content_scenes", "['*']",
]
WEIGHTS = {
    "ckpt/nav_model.pth": "03fa71b514c8ee2fa272d6276499d51313a43b7d71bb31181c0150cc7c050d1a",
    "ckpt/safety_model.pth": "b84d291e84216defb730d07d03cb6f25e3555ae447eb1e69057f3427b3c7ec31",
}


def git(*args):
    return subprocess.check_output(["git", *args], text=True).strip()


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def preflight():
    assert os.environ.get("PYTHONHASHSEED") == "0"
    assert habitat_sim.__version__ == "0.3.3" and habitat_sim.cuda_enabled
    commit = git("rev-parse", "HEAD")
    assert commit == os.environ.get("GS_SOURCE_COMMIT", commit), "Source changed after submission"
    assert not git("status", "--porcelain", "--untracked-files=no"), "Tracked worktree changes"
    differences = git("diff", "--name-only", "dad87fe", "--", "src").splitlines()
    assert set(differences) == {"src/dataset.py", "src/custom_habitat_simulator.py", "src/policy.py"}
    original_policy = subprocess.check_output(["git", "show", "dad87fe:src/policy.py"])
    assert Path("src/policy.py").read_bytes() == original_policy.replace(b"from nis import match\n", b"")
    for path, expected in WEIGHTS.items():
        assert sha256(path) == expected, f"Released checkpoint changed: {path}"
    cfg = change_habitat_config(get_config(CONFIGS, OPTIONS))
    assert cfg.habitat_baselines.trainer_name == "SIGN"
    assert cfg.habitat_baselines.rl.policy.name == "SafeNavNetPolicy"
    assert cfg.habitat_baselines.rl.policy.safety_model_path == "ckpt/safety_model.pth"
    assert cfg.habitat_baselines.eval.should_load_ckpt and not cfg.habitat_baselines.eval.use_ckpt_config
    assert cfg.habitat_baselines.eval.evals_per_ep == 1
    assert cfg.habitat_baselines.num_environments == 6
    assert cfg.habitat_baselines.test_episode_count == 1900
    assert cfg.habitat.seed == 100 and cfg.habitat.dataset.split == "val"
    assert cfg.habitat.environment.max_episode_steps == 500
    assert cfg.habitat.simulator.rgb_sensor.width == cfg.habitat.simulator.rgb_sensor.height == 128
    assert cfg.habitat.simulator.action_space_config == "continuous"
    assert cfg.habitat.task.success.success_distance == 1.0
    assert list(cfg.habitat.dataset.content_scenes) == ["*"]
    assert not cfg.habitat_baselines.video_option
    dataset = HabitatGSImageNavDatasetV1(cfg.habitat.dataset)
    counts = Counter(ep.scene_id for ep in dataset.episodes)
    keys = sorted((ep.scene_id, ep.episode_id) for ep in dataset.episodes)
    assert len(keys) == len(set(keys)) == 1900
    assert len(counts) == 19 and set(counts.values()) == {100}
    paths, max_error = {}, 0.0
    for ep in dataset.episodes:
        assert ep.scene_dataset_config == cfg.habitat.simulator.scene_dataset
        if ep.scene_id not in paths:
            assert Path(ep.scene_id).is_file()
            navmesh = Path(ep.scene_id.removesuffix(".gs.ply") + ".navmesh")
            paths[ep.scene_id] = habitat_sim.PathFinder()
            assert paths[ep.scene_id].load_nav_mesh(str(navmesh))
        path = habitat_sim.ShortestPath()
        path.requested_start, path.requested_end = ep.start_position, ep.goals[0].position
        assert paths[ep.scene_id].find_path(path) and np.isfinite(path.geodesic_distance)
        max_error = max(max_error, abs(path.geodesic_distance - ep.info["geodesic_distance"]))
    assert max_error < 0.01, max_error
    sources = git("ls-files", "src", "exp_config", "run_sim.py", "scripts/habitat_gs").splitlines()
    return {
        "source_commit": commit, "author_baseline": git("rev-parse", "dad87fe"),
        "source_differences": differences, "source_sha256": {p: sha256(p) for p in sources},
        "checkpoint_sha256": WEIGHTS, "configs": CONFIGS, "options": OPTIONS,
        "episodes": len(keys), "scenes": len(counts), "episodes_per_scene": dict(sorted(counts.items())),
        "episode_keys_sha256": hashlib.sha256(json.dumps(keys).encode()).hexdigest(),
        "max_geodesic_error_m": max_error,
        "habitat_sim": habitat_sim.__version__, "torch": torch.__version__, "numpy": np.__version__,
        "seed": 100, "pythonhashseed": 0, "parallel_environments": 6,
        "protocol": "Released SIGN; 128x128 RGB and goal; continuous actions; 500 steps; 1m success",
        "data_manifest_sha256": sha256(ROOT.parent / "manifests/habitat_gs_imagenav_20261028.json"),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preflight-only", action="store_true")
    parser.add_argument("--run-dir", type=Path)
    args = parser.parse_args()
    inputs = preflight()
    print(json.dumps({k: inputs[k] for k in (
        "source_commit", "source_differences", "checkpoint_sha256", "episodes", "scenes",
        "max_geodesic_error_m", "parallel_environments", "protocol")}, indent=2), flush=True)
    if args.preflight_only:
        return
    if args.run_dir is None:
        parser.error("--run-dir is required for evaluation")
    assert torch.cuda.is_available(), "Evaluation requires a PBS GPU node"
    args.run_dir.mkdir(parents=True, exist_ok=False)
    (args.run_dir / "inputs.json").write_text(json.dumps(inputs, indent=2) + "\n")
    command = [sys.executable, "run_sim.py", "--exp-config", ",".join(CONFIGS),
               "--run-type", "eval", "--model-dir", str(args.run_dir / "eval"), *OPTIONS]
    print(f"Evaluating 1900 episodes; output: {args.run_dir / 'evaluation.log'}", flush=True)
    started = time.monotonic()
    with (args.run_dir / "evaluation.log").open("x") as log:
        subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, check=True)
    elapsed = time.monotonic() - started
    output = (args.run_dir / "evaluation.log").read_text()
    assert re.search(r"\b1900/1900\b", output), "Missing full completion evidence"
    from tensorboard.backend.event_processing.event_accumulator import EventAccumulator
    events = EventAccumulator(str(args.run_dir / "eval/tb")).Reload()
    metrics = {tag: events.Scalars(tag)[-1].value for tag in events.Tags()["scalars"]}
    assert all(math.isfinite(v) for v in metrics.values())
    assert all(0 <= metrics[f"eval_metrics/{key}"] <= 1 for key in ("success", "spl"))
    result = {"episodes": 1900, "scenes": 19, "source_commit": inputs["source_commit"],
              "job_id": os.environ.get("PBS_JOBID"), "evaluation_elapsed_s": elapsed,
              "successes": round(metrics["eval_metrics/success"] * 1900), "metrics": metrics,
              "protocol": inputs["protocol"], "per_episode_metrics_saved": False}
    (args.run_dir / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2), flush=True)


if __name__ == "__main__":
    main()
