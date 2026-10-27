"""Focused CPU checks for the rollout-area reward and its 2D view proxy."""
import copy
import json
import os
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest

import numpy as np
import quaternion
import torch

ROOT = Path('/scratch/e1538633/liuyi')
TREE = ROOT / 'SIGN-frozen-rollout-coverage'
HERE = Path(__file__).resolve().parent
os.chdir(str(TREE))
sys.path.insert(0, str(TREE))
import run_sim
from habitat.config import Config
from habitat.utils.gym_adapter import flatten_dict
from habitat_baselines.config.default import get_config
from src.metric import ObservedCoverage
from src.trainer import PPOTrainer
from src.utils import change_habitat_config

torch.set_num_threads(1)


class FakePathfinder:
    def __init__(self, grid):
        self.grid = grid
        self.calls = 0

    def get_bounds(self):
        return np.array([0., 0., 0.]), np.array([10., 3., 10.])

    def get_topdown_view(self, meters_per_pixel, height):
        self.calls += 1
        return self.grid.copy()


class FakeSim:
    def __init__(self, grid=None):
        self.pathfinder = FakePathfinder(np.ones((100, 100), np.uint8) if grid is None else grid)
        self.state = SimpleNamespace(position=np.array([5., 0., 5.]), rotation=quaternion.from_rotation_vector([0., 0., 0.]))

    def get_agent_state(self):
        return self.state

    def get_agent(self, index):
        return SimpleNamespace(state=self.state)


def measure(sim=None, **changes):
    values = dict(meters_per_pixel=0.1, visibility_dist=3.0, fov=90.0)
    values.update(changes)
    return ObservedCoverage(sim or FakeSim(), Config(values))


def bonus_trainer(delta, masks, weight=0.1, rewards=None):
    delta = np.asarray(delta, dtype=np.float64)
    H, N = delta.shape
    t = PPOTrainer.__new__(PPOTrainer)
    t._coverage_weight = weight
    t._coverage_delta_rows = delta.tolist()
    t.envs = SimpleNamespace(num_envs=N)
    t.rollouts = SimpleNamespace(current_rollout_step_idx=H, buffers={
        'masks': masks.clone(),
        'rewards': torch.zeros(H+1, N, 1) if rewards is None else rewards.clone(),
    })
    return t


class CoverageTests(unittest.TestCase):
    def test_initial_view_repeat_and_reset(self):
        m = measure();m.reset_metric(None)
        self.assertGreater(m._count, 0)
        self.assertEqual(m.get_metric(), {'delta_m2':0.0,'new_area_m2':0.0})
        m.update_metric(None);self.assertEqual(m.get_metric()['delta_m2'],0.0)
        m.sim.state.rotation = quaternion.from_rotation_vector([0., np.pi, 0.])
        m.update_metric(None);self.assertGreater(m.get_metric()['delta_m2'],0.0)
        old_info = {'observed_coverage':m.get_metric()}
        terminal_delta = flatten_dict(old_info)['observed_coverage.delta_m2']
        m.update_metric(None);self.assertEqual(m.get_metric()['delta_m2'],0.0)
        m.reset_metric(None);self.assertEqual(m.get_metric()['new_area_m2'],0.0)
        self.assertEqual(flatten_dict(old_info)['observed_coverage.delta_m2'], terminal_delta)

    def test_four_headings_and_radius(self):
        for yaw, point in [(0.,(35,50)), (np.pi/2,(50,35)), (np.pi,(65,50)), (-np.pi/2,(50,65))]:
            m = measure();m.sim.state.rotation=quaternion.from_rotation_vector([0.,yaw,0.]);m.reset_metric(None)
            self.assertEqual(m._seen[point],1)
            opposite=(100-point[0],100-point[1]);self.assertEqual(m._seen[opposite],0)
            rows,cols=np.nonzero(m._seen)
            self.assertLessEqual(float(np.sqrt((rows-50)**2+(cols-50)**2).max()),32.)

    def test_wall_occlusion(self):
        grid=np.ones((100,100),np.uint8);grid[40,:]=0
        m=measure(FakeSim(grid));m.reset_metric(None)
        self.assertEqual(m._seen[45,50],1)
        self.assertFalse(m._seen[:40,:].any())
        self.assertFalse(m._seen[40,:].any())

    def test_height_uses_xz_union(self):
        m=measure();m.reset_metric(None);before=m._seen.copy();count=m._count
        m.sim.state.position[1]=1.0;m.update_metric(None)
        self.assertTrue(np.array_equal(m._seen,before))
        self.assertEqual(m._count,count);self.assertEqual(m.get_metric()['delta_m2'],0.)
        self.assertEqual(m.sim.pathfinder.calls,2)

    def test_rollout_boundary_does_not_reset_coverage(self):
        m=measure();m.reset_metric(None)
        m.sim.state.rotation=quaternion.from_rotation_vector([0.,np.pi,0.]);m.update_metric(None)
        delta=m.get_metric()['delta_m2'];count=m._count;seen=m._seen.copy()
        t=bonus_trainer([[delta]],torch.ones(2,1,1,dtype=torch.bool));t._add_coverage_bonus()
        m.update_metric(None)
        self.assertEqual(m._count,count);self.assertTrue(np.array_equal(m._seen,seen))
        self.assertEqual(m.get_metric()['delta_m2'],0.)
        self.assertEqual(m.sim.pathfinder.calls,1)

    def test_segments_masks_and_total(self):
        delta=np.array([[1,10],[2,20],[3,30],[4,40],[5,50]],dtype=float)
        masks=torch.ones(6,2,1,dtype=torch.bool)
        masks[2,0,0]=False;masks[4,0,0]=False
        masks[1,1,0]=False;masks[4,1,0]=False
        rewards=torch.randn(6,2,1);t=bonus_trainer(delta,masks,rewards=rewards)
        metrics=t._add_coverage_bonus();difference=t.rollouts.buffers['rewards']-rewards
        expected=torch.zeros_like(rewards);expected[1,0,0]=.06;expected[3,0,0]=.14;expected[4,0,0]=.1
        expected[0,1,0]=.2;expected[3,1,0]=1.8;expected[4,1,0]=1.
        torch.testing.assert_close(difference,expected,atol=3e-7,rtol=1e-5)
        self.assertAlmostEqual(float(difference.sum()),.1*float(delta.sum())/5,places=6)
        self.assertAlmostEqual(metrics['coverage_bonus_sum'],3.3)
        self.assertTrue(torch.equal(t.rollouts.buffers['masks'],masks))
        self.assertTrue(t.rollouts.buffers['masks'][-1].all())
        self.assertEqual(t._coverage_delta_rows,[])

    def test_weight_zero_exactly_unchanged(self):
        original=torch.randn(4,3,1)
        t=bonus_trainer(np.ones((3,3)),torch.ones(4,3,1,dtype=torch.bool),weight=0.,rewards=original)
        self.assertEqual(t._add_coverage_bonus(),{})
        self.assertTrue(torch.equal(original,t.rollouts.buffers['rewards']))
        self.assertEqual(t._coverage_delta_rows,[])

    def test_invalid_values_fail(self):
        for value in [0.,-1.,float('nan'),float('inf')]:
            with self.assertRaises(ValueError):measure(meters_per_pixel=value)
        for value in [0.,181.,float('nan')]:
            with self.assertRaises(ValueError):measure(fov=value)
        with self.assertRaises(RuntimeError):measure(FakeSim(np.zeros((100,100),np.uint8))).reset_metric(None)
        for bad in [float('nan'),float('inf'),-1.]:
            t=bonus_trainer([[bad]],torch.ones(2,1,1,dtype=torch.bool))
            with self.assertRaises(RuntimeError):t._add_coverage_bonus()
        t=bonus_trainer([[1.]],torch.ones(2,1,1,dtype=torch.bool));t._coverage_delta_rows=[]
        with self.assertRaises(RuntimeError):t._add_coverage_bonus()

    def test_config_only_adds_measure_and_matches_fov(self):
        paths=['exp_config/ppo_imagenav_gibson.yaml','src/config/policy.yaml','src/config/reward.yaml','src/config/sensors.yaml']
        opts=['habitat_baselines.num_environments','8','habitat_baselines.rl.ppo.num_steps','256',
              'habitat_baselines.rl.ddppo.pretrained_encoder','True',
              'habitat_baselines.rl.ddppo.pretrained_weights','ckpt/nav_model.pth',
              'habitat_baselines.rl.ddppo.train_encoder','False',
              'habitat_baselines.num_checkpoints','-1','habitat_baselines.checkpoint_interval','250',
              'habitat_baselines.log_interval','10']
        base=change_habitat_config(get_config(paths,opts));cfg=change_habitat_config(get_config(paths+['src/config/rollout_coverage.yaml'],opts))
        self.assertEqual(list(cfg.habitat.task.measurements),list(base.habitat.task.measurements)+['observed_coverage'])
        self.assertEqual(float(cfg.habitat.simulator.rgb_sensor.hfov),float(cfg.habitat.task.observed_coverage.fov))
        clean=cfg.clone();clean.defrost();del clean.habitat.task['observed_coverage'];clean.habitat.task.measurements=base.habitat.task.measurements
        self.assertEqual(str(clean),str(base))
        (HERE/'merged_train.yaml').write_text(str(cfg))
        evaluation=change_habitat_config(get_config(paths+['src/config/eval.yaml'],[]))
        (HERE/'merged_eval.yaml').write_text(str(evaluation))
        self.assertEqual(evaluation.habitat_baselines.num_environments,6)
        self.assertEqual(evaluation.habitat.environment.max_episode_steps,500)


if __name__=='__main__':
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(CoverageTests))
    (HERE/'unit_results.json').write_text(json.dumps({'tests':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'passed':result.wasSuccessful()},indent=2)+'\n')
    raise SystemExit(0 if result.wasSuccessful() else 1)
