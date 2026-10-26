#!/usr/bin/env python3
"""Check the real SIGN config/weights, then GS rendering and continuous actions."""
import argparse
import hashlib
import json
import os
import sys
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

import numpy as np
import torch
import habitat_sim
import run_sim  # Register SIGN's unchanged policy, sensors, task and simulator.
from gym import spaces
from habitat.core.registry import registry
from habitat.core.simulator import SensorSuite
from habitat_baselines.config.default import get_config
from src.custom_habitat_simulator import HabitatSim
from src.dataset import HabitatGSImageNavDatasetV1
from src.policy import SafeNavNetPolicy
from src.utils import change_habitat_config

CONFIGS = [
    "exp_config/ppo_imagenav_gibson.yaml", "src/config/policy.yaml",
    "src/config/reward.yaml", "src/config/sensors.yaml", "src/config/eval.yaml",
    "exp_config/ppo_imagenav_habitat_gs.yaml",
]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gpu", action="store_true")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if os.environ.get("PYTHONHASHSEED") != "0":
        raise RuntimeError("Run with PYTHONHASHSEED=0 to fix ImageGoalSensorV2 goal headings")
    if args.output.exists():
        raise FileExistsError(f"Preserve previous evidence: {args.output}")
    torch.set_num_threads(1)
    cfg = change_habitat_config(get_config(CONFIGS))
    dataset = HabitatGSImageNavDatasetV1(cfg.habitat.dataset)
    assert len(dataset.episodes) == 100
    assert all(ep.scene_dataset_config == cfg.habitat.simulator.scene_dataset for ep in dataset.episodes)
    # Exercise the actual SIGN -> native simulator configuration path on CPU,
    # without constructing a renderer or a live Simulator.
    config_context = SimpleNamespace(habitat_config=cfg.habitat.simulator)
    config_context._get_agent_config = lambda index: HabitatSim._get_agent_config(config_context, index)
    agent_config = config_context._get_agent_config(0)
    sensors = [registry.get_sensor(cfg.habitat.simulator[name].type)(cfg.habitat.simulator[name])
               for name in agent_config.sensors]
    config_context.agent_sensors = [[sensor.uuid for sensor in sensors]]
    native_config = HabitatSim.create_sim_config(config_context, SensorSuite(sensors), 1)
    sensor_specs = [{"uuid": spec.uuid, "position": list(spec.position),
                     "resolution": list(spec.resolution)}
                    for spec in native_config.agents[0].sensor_specifications]
    nav = habitat_sim.PathFinder()
    navfile = ROOT / "data/scene_datasets/gs_scenes/val/scene56/scene56.navmesh"
    assert nav.load_nav_mesh(str(navfile))
    errors = []
    for ep in dataset.episodes:
        path = habitat_sim.ShortestPath()
        path.requested_start = ep.start_position
        path.requested_end = ep.goals[0].position
        assert nav.find_path(path) and np.isfinite(path.geodesic_distance)
        errors.append(abs(path.geodesic_distance - ep.info["geodesic_distance"]))
    assert max(errors) < 0.01
    obs_space = spaces.Dict({
        "rgb": spaces.Box(0, 255, (128, 128, 3), np.uint8),
        "depth": spaces.Box(0., 1., (256, 256, 1), np.float32),
        "imagegoal_sensor_v2": spaces.Box(0, 255, (128, 128, 3), np.uint8),
    })
    policy = SafeNavNetPolicy.from_config(cfg, obs_space, spaces.Box(-1., 1., (2,), np.float32))
    ckpt_path = ROOT / "ckpt/nav_model.pth"
    checkpoint = torch.load(ckpt_path, map_location="cpu", weights_only=False)
    prefix = "actor_critic."
    state = {k[len(prefix):]: v for k, v in checkpoint["state_dict"].items() if k.startswith(prefix)}
    assert state
    incompatible = policy.load_state_dict(state, strict=False)
    # The released nav checkpoint retains obsolete LPIPS and Qc.mlp tensors.
    # SIGN's trainer also loads the separate safety checkpoint into current Qc.
    assert all(k.startswith(("loss_fn.", "Qc.mlp.")) for k in incompatible.unexpected_keys), incompatible
    assert all(k.startswith("Qc.") for k in incompatible.missing_keys), incompatible
    safety_path = ROOT / "ckpt/safety_model.pth"
    safety = torch.load(safety_path, map_location="cpu", weights_only=False)
    safety_prefix = "actor_critic.Qc."
    safety_state = {k[len(safety_prefix):]: v for k, v in safety["state_dict"].items()}
    policy.Qc.load_state_dict(safety_state, strict=True)
    result = {
        "torch": torch.__version__, "numpy": np.__version__, "habitat_sim": habitat_sim.__version__,
        "habitat_sim_file": habitat_sim.__file__, "episodes": len(dataset.episodes),
        "sensor_specs": sensor_specs,
        "navigable_area": nav.navigable_area, "max_geodesic_error_m": max(errors),
        "checkpoint_sha256": hashlib.sha256(ckpt_path.read_bytes()).hexdigest(),
        "checkpoint_policy_tensors": len(state), "safety_checkpoint_loaded_strictly": True,
        "safety_checkpoint_sha256": hashlib.sha256(safety_path.read_bytes()).hexdigest(),
        "ignored_legacy_checkpoint_keys": incompatible.unexpected_keys,
        "goal_heading_protocol": "SIGN uniform sensor with PYTHONHASHSEED=0",
        "gpu_probe": False,
    }
    if args.gpu:
        assert torch.cuda.is_available() and habitat_sim.cuda_enabled
        assert habitat_sim.__version__ == "0.3.3"
        from PIL import Image
        from src.custom_habitat_env import DroneEnv
        env = DroneEnv(cfg.habitat, dataset)
        try:
            env.seed(cfg.habitat.seed)
            obs = env.reset()
            assert env.sim.pathfinder.is_loaded
            assert env.current_episode.scene_id.endswith(".gs.ply")
            assert env.sim.sim_config.sim_cfg.scene_dataset_config_file == cfg.habitat.simulator.scene_dataset
            for key in ("rgb", "depth", "imagegoal_sensor_v2"):
                assert np.isfinite(obs[key]).all(), key
            assert obs["rgb"].shape == (128, 128, 3)
            assert obs["imagegoal_sensor_v2"].shape == (128, 128, 3)
            assert float(obs["rgb"].std()) > 3 and float(obs["imagegoal_sensor_v2"].std()) > 3
            before = env.sim.get_agent_state()
            goal_sensor = env.task.sensor_suite.sensors["imagegoal_sensor_v2"]
            goal_view = goal_sensor.get_goal_views()[0]
            rendered_goal = env.sim.get_observations_at(env.current_episode.goals[0].position, goal_view)["rgb"]
            assert np.array_equal(rendered_goal, obs["imagegoal_sensor_v2"])
            after_goal = env.sim.get_agent_state()
            assert np.allclose(before.position, after_goal.position)
            assert abs(np.dot(before.rotation.components, after_goal.rotation.components)) > 0.99999
            preview = np.concatenate([obs["rgb"], obs["imagegoal_sensor_v2"]], axis=1)
            policy = policy.cuda().eval()
            hidden = torch.zeros(1, policy.num_recurrent_layers, cfg.habitat_baselines.rl.ppo.hidden_size, device="cuda")
            batch = {k: torch.as_tensor(v[None], device="cuda") for k, v in obs.items()}
            batch["cost"] = torch.zeros(1, 1, device="cuda")
            with torch.no_grad():
                _, action, _, _ = policy.act(batch, hidden, torch.zeros(1, 2, device="cuda"),
                                              torch.zeros(1, 1, device="cuda", dtype=torch.bool), deterministic=True)
            assert torch.isfinite(action).all() and action.shape == (1, 2)
            commanded = {"action": "continuous_control", "action_args": {
                "angular_velocity": 0.5, "linear_velocity": 0.5}}
            next_obs = env.step(commanded)
            after = env.sim.get_agent_state()
            assert np.isfinite(next_obs["rgb"]).all()
            assert abs(np.dot(before.rotation.components, after.rotation.components)) < 0.99999
            result.update({
                "gpu_probe": True, "gpu": torch.cuda.get_device_name(),
                "episode_id": env.current_episode.episode_id, "scene": env.current_episode.scene_id,
                "rgb_std": float(obs["rgb"].std()), "goal_std": float(obs["imagegoal_sensor_v2"].std()),
                "goal_image_matches_render": True, "goal_render_preserves_agent_pose": True,
                "policy_action": action.cpu().tolist(),
                "continuous_action_translation_m": float(np.linalg.norm(after.position-before.position)),
                "continuous_action_rotates": True, "metrics_after_action": env.get_metrics(),
            })
            args.output.parent.mkdir(parents=True, exist_ok=True)
            Image.fromarray(preview).save(args.output.with_suffix(".png"))
        finally:
            env.close()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, default=float) + "\n")
    print(json.dumps(result, indent=2, default=float))


if __name__ == "__main__":
    main()
