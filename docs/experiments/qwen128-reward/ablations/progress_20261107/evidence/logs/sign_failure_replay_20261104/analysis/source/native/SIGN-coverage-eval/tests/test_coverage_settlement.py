"""CPU checks for settlement timing, conservation, termination, and GAE.

Run from the repository root in the SIGN environment:
    python -m unittest discover -s tests -p 'test_coverage_settlement.py' -v
"""
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import numpy as np
import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import run_sim  # Register the native task and policy components.
from habitat_baselines.common.rollout_storage import RolloutStorage
from habitat_baselines.config.default import get_config
from src.trainer import PPOTrainer
from src.utils import change_habitat_config

torch.set_num_threads(1)


def trainer(delta, interval=32, weight=0.1, masks=None, rewards=None):
    delta = np.asarray(delta, dtype=np.float64)
    H, N = delta.shape
    obj = PPOTrainer.__new__(PPOTrainer)
    obj._coverage_weight = weight
    obj._coverage_settlement_interval = interval
    obj._coverage_delta_rows = delta.tolist()
    obj.envs = SimpleNamespace(num_envs=N)
    obj.rollouts = SimpleNamespace(current_rollout_step_idx=H, buffers={
        "masks": torch.ones(H + 1, N, 1, dtype=torch.bool) if masks is None else masks.clone(),
        "rewards": torch.zeros(H + 1, N, 1, dtype=torch.float64) if rewards is None else rewards.clone(),
    })
    return obj


class SettlementTests(unittest.TestCase):
    def test_early_gain_moves_to_step_32_without_changing_total(self):
        delta = np.zeros((256, 1)); delta[15, 0] = 4.0
        old, new = trainer(delta, 0), trainer(delta, 32)
        for obj in (old, new): obj._add_coverage_bonus()
        expected_old = torch.zeros(257, 1, 1, dtype=torch.float64)
        expected_new = expected_old.clone()
        expected_old[255] = expected_new[31] = 0.0015625
        torch.testing.assert_close(old.rollouts.buffers["rewards"], expected_old)
        torch.testing.assert_close(new.rollouts.buffers["rewards"], expected_new)
        self.assertEqual(float(expected_old.sum()), float(expected_new.sum()))

    def test_multiple_episodes_and_boundary_collisions(self):
        delta = np.tile([1.0, 10.0], (70, 1))
        masks = torch.ones(71, 2, 1, dtype=torch.bool)
        masks[[10, 40, 70], 0, 0] = False
        masks[[32, 33, 69], 1, 0] = False
        obj = trainer(delta, masks=masks)
        metrics = obj._add_coverage_bonus()
        expected = torch.zeros(71, 2, 1, dtype=torch.float64)
        for end, gain in [(9, 10), (31, 22), (39, 8), (63, 24), (69, 6)]:
            expected[end, 0, 0] = 0.1 * gain / 70
        for end, gain in [(31, 320), (32, 10), (63, 310), (68, 50), (69, 10)]:
            expected[end, 1, 0] = 0.1 * gain / 70
        torch.testing.assert_close(obj.rollouts.buffers["rewards"], expected)
        self.assertAlmostEqual(metrics["coverage_bonus_sum"], 1.1)
        self.assertTrue(torch.equal(obj.rollouts.buffers["masks"], masks))
        self.assertEqual(obj._coverage_delta_rows, [])

    def test_zero_and_large_interval_preserve_original_settlement(self):
        rng = np.random.default_rng(100)
        delta = rng.uniform(0, 3, (65, 8))
        masks = torch.ones(66, 8, 1, dtype=torch.bool)
        masks[7, 0] = False; masks[32, 2] = False; masks[60, 5] = False
        reference = trainer(delta, 0, masks=masks)
        metrics = reference._add_coverage_bonus()
        for interval in (65, 256, 512):
            obj = trainer(delta, interval, masks=masks)
            self.assertEqual(obj._add_coverage_bonus(), metrics)
            self.assertTrue(torch.equal(obj.rollouts.buffers["rewards"], reference.rollouts.buffers["rewards"]))

    def test_short_and_partial_rollouts(self):
        for H, expected_ends in [(1, [0]), (17, [16]), (32, [31]), (65, [31, 63, 64])]:
            obj = trainer(np.ones((H, 1)))
            metrics = obj._add_coverage_bonus()
            actual = torch.nonzero(obj.rollouts.buffers["rewards"][:, 0, 0]).flatten().tolist()
            self.assertEqual(actual, expected_ends)
            self.assertAlmostEqual(metrics["coverage_bonus_sum"], 0.1)
            self.assertTrue(obj.rollouts.buffers["masks"].all())

    def test_eight_environment_conservation_with_navigation_rewards(self):
        rng = np.random.default_rng(100)
        delta = rng.uniform(0, 3, (256, 8))
        masks = torch.as_tensor(rng.random((257, 8, 1)) > 0.04)
        rewards = torch.as_tensor(rng.normal(size=(257, 8, 1)))
        obj = trainer(delta, masks=masks, rewards=rewards)
        metrics = obj._add_coverage_bonus()
        gain = obj.rollouts.buffers["rewards"] - rewards
        self.assertAlmostEqual(float(gain.sum()), 0.1 * delta.sum() / 256)
        self.assertAlmostEqual(metrics["coverage_bonus_sum"], float(gain.sum()))
        self.assertAlmostEqual(metrics["coverage_bonus_per_step"], float(gain.sum()) / 2048)
        self.assertTrue(torch.equal(obj.rollouts.buffers["masks"], masks))
        self.assertTrue(torch.equal(obj.rollouts.buffers["rewards"][-1], rewards[-1]))

    def test_zero_weight_is_bitwise_identity(self):
        torch.manual_seed(100)
        rewards = torch.randn(257, 8, 1)
        obj = trainer(np.ones((256, 8)), weight=0, rewards=rewards)
        self.assertEqual(obj._add_coverage_bonus(), {})
        self.assertTrue(torch.equal(obj.rollouts.buffers["rewards"], rewards))
        self.assertTrue(obj.rollouts.buffers["masks"].all())
        self.assertEqual(obj._coverage_delta_rows, [])

    def test_settlement_does_not_terminate_gae(self):
        delta = np.zeros((256, 1)); delta[40, 0] = 4
        obj = trainer(delta)
        obj._add_coverage_bonus()
        obj.rollouts.buffers["value_preds"] = torch.zeros(257, 1, 1, dtype=torch.float64)
        obj.rollouts.buffers["returns"] = torch.zeros(257, 1, 1, dtype=torch.float64)
        RolloutStorage.compute_returns(obj.rollouts, torch.zeros(1, 1), True, 0.99, 0.95)
        # A reward at step 64 must still influence step 32 across the added boundary.
        expected = (0.1 * 4 / 256) * (0.99 * 0.95) ** 32
        self.assertAlmostEqual(float(obj.rollouts.buffers["returns"][31, 0, 0]), expected)
        self.assertTrue(obj.rollouts.buffers["masks"].all())

    def test_interval_validation_and_default(self):
        paths = ["exp_config/ppo_imagenav_gibson.yaml", "src/config/policy.yaml", "src/config/reward.yaml", "src/config/sensors.yaml", "src/config/rollout_coverage.yaml"]
        config = change_habitat_config(get_config(paths, []))
        for value in (None, 0, 32, 512, -1, 1.5, True, "32"):
            with self.subTest(value=value):
                cfg = config.clone(); cfg.defrost()
                if value is None:
                    del cfg.habitat.task.observed_coverage["settlement_interval"]
                else:
                    cfg.habitat.task.observed_coverage.settlement_interval = value
                cfg.freeze()
                obj = PPOTrainer.__new__(PPOTrainer); obj.config = cfg
                if value in (None, 0, 32, 512) and not isinstance(value, bool):
                    with patch.object(PPOTrainer, "_init_envs", side_effect=RuntimeError("stop before environments")):
                        with self.assertRaisesRegex(RuntimeError, "stop before environments"):
                            obj._init_train()
                    self.assertEqual(obj._coverage_settlement_interval, 0 if value is None else value)
                else:
                    with self.assertRaisesRegex(ValueError, "settlement_interval"):
                        obj._init_train()


if __name__ == "__main__":
    unittest.main()
