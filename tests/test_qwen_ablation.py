"""256 boundaries, physical area control, MRQ independence and frozen calibration."""
import copy,hashlib,json,sys,tempfile
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import numpy as np
import torch
import run_sim
from habitat.config import read_write
from habitat_baselines.config.default import get_config
from src.utils import change_habitat_config
from src.trainer import PPOTrainer
from src.algo.PPO import DA_PPO
from src.qwen_reward import QwenRolloutReward
from src.qwen_rollout import PAYLOAD_KEY
import test_qwen_reward as reward_fixtures
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from calibrate_geometry_control import calibrate

def config(name):
    return change_habitat_config(get_config(['exp_config/ppo_imagenav_gibson.yaml']+
        ['src/config/'+n+'.yaml' for n in ['policy','reward','sensors','qwen_reward',name]],[]))

class AblationTests(unittest.TestCase):
    def ledger(self,interval=128,episodes=()):return reward_fixtures.LedgerTests().build(episodes=episodes,interval=interval)
    def test_256_no_128_cut_and_multiple_terminals(self):
        for ends,expected in [((),[(0,256)]),((2,128,129,255,256),[(0,2),(2,128),(128,129),(129,255),(255,256)])]:
            _,l,m=self.ledger(256,ends)
            self.assertEqual([(s['global_start'],s['global_end']) for s in l.pending],expected)
            r=torch.zeros(257,1,1,dtype=torch.float64);mb=m.clone()
            l.add(r,m,[dict(id=s['segment_id'],q=.7,valid=True) for s in l.pending],.03)
            self.assertAlmostEqual(float(r.sum()),.021);self.assertTrue(m.equal(mb))
    def test_256_history_persists_across_rollouts(self):
        c,l,m=self.ledger(256)
        l.add(torch.zeros(257,1,1),m,[dict(id=s['segment_id'],q=.7,valid=True) for s in l.pending],.03);l.advance()
        for row in range(256):l.collect(row,[False],[{PAYLOAD_KEY:c.step((0,0),0.,[0,0,0],False)}])
        self.assertEqual([(s['start'],s['end']) for s in l.pending],[(256,512)])
    def test_geometry_area_not_probability_and_no_centering(self):
        _,l,m=self.ledger(128,(10,128,140));mb=m.clone();r=torch.zeros(257,1,1,dtype=torch.float64)
        for i,s in enumerate(l.pending):s['metadata']=dict(new_area_m2=float(i+2)*7.)
        alpha=.2927574680399425;expected=torch.zeros_like(r)
        for s in l.pending:expected[s['end_row'],0,0]=alpha*s['metadata']['new_area_m2']/256
        b=l.add_geometry(r,m,alpha)
        self.assertTrue(torch.equal(r,expected));self.assertAlmostEqual(sum(b),float(expected.sum()))
        self.assertTrue(m.equal(mb));self.assertGreater(float(r.sum()),0.)
        with self.assertRaisesRegex(RuntimeError,'already scored'):l.add_geometry(r,m,alpha)
    def test_bad_area_atomic_failure_and_invalid_skip(self):
        _,l,m=self.ledger();r=torch.zeros(257,1,1)
        l.pending[0]['metadata']={'new_area_m2':1.};l.pending[1]['metadata']={'new_area_m2':float('nan')}
        with self.assertRaisesRegex(RuntimeError,'area'):l.add_geometry(r,m,.3)
        self.assertEqual(float(r.sum()),0)
        l.pending[1]['valid_geometry']=False
        self.assertEqual(len(l.add_geometry(r,m,.3)),1)
    def test_frozen_calibration_exact_budget_match(self):
        source=ROOT/'docs/experiments/qwen128-reward/evidence/segments.jsonl'
        result,_=calibrate(source);saved=json.loads((ROOT/'docs/experiments/qwen128-reward/ablations/calibration/calibration.json').read_text())
        self.assertEqual(result['source_sha256'],saved['source_sha256'])
        self.assertAlmostEqual(result['alpha'],.2927574680399425,places=15)
        self.assertEqual(result['qwen_bonus_sum'],result['geometry_bonus_sum'])
        self.assertEqual(saved['valid_segments'],1176)
    def test_all_three_mrq_navigation_independent_of_qwen(self):
        for name in ['qwen_a128','qwen_b256','geometry_c128']:
            cfg=config(name);obj=SimpleNamespace();DA_PPO.add_config(obj,cfg);self.assertTrue(obj.mrq_navigation_only)
            with read_write(cfg):cfg.qwen_reward.enabled=False;cfg.qwen_reward.beta=0.
            DA_PPO.add_config(obj,cfg);self.assertTrue(obj.mrq_navigation_only)
            with read_write(cfg):cfg.habitat_baselines.rl.data_augmentation.mrq_reward_target='mixed'
            DA_PPO.add_config(obj,cfg);self.assertFalse(obj.mrq_navigation_only)
    def test_trainer_accepts_128_256_and_rejects_overlap(self):
        for name in ['qwen_a128','qwen_b256','geometry_c128']:
            cfg=config(name)
            with read_write(cfg):cfg.habitat_baselines.rl.ppo.num_steps=256
            obj=PPOTrainer(cfg)
            with patch.object(obj,'_init_envs',side_effect=RuntimeError('before env')):
                with self.assertRaisesRegex(RuntimeError,'before env'):obj._init_train()
            self.assertTrue(cfg.qwen_reward.collect)
        for interval in [True,0,32,128.0]:
            cfg=config('qwen_a128')
            with read_write(cfg):cfg.qwen_reward.settlement_interval=interval;cfg.habitat_baselines.rl.ppo.num_steps=256
            with self.assertRaises(ValueError):PPOTrainer(cfg)._init_train()
        cfg=config('geometry_c128')
        with read_write(cfg):cfg.qwen_reward.enabled=True
        with self.assertRaisesRegex(ValueError,'disable Qwen'):PPOTrainer(cfg)._init_train()
    def test_geometry_controller_no_worker_render_or_fake_q(self):
        cfg=config('geometry_c128').qwen_reward
        _,l,m=self.ledger(128,(20,128,200));r=torch.zeros(257,1,1);nav=r.clone();mb=m.clone()
        for s in l.pending:s['metadata']={'action_count':s['action_count'],'new_area_m2':4.}
        expected = float(cfg.geometry_alpha)*4.*len(l.pending)/256
        with tempfile.TemporaryDirectory() as tmp:
            with patch('src.qwen_reward.QwenClient',side_effect=AssertionError('worker')):
                with patch('src.qwen_reward.render',side_effect=AssertionError('render')):
                    controller=QwenRolloutReward(cfg,1,256,tmp);controller.ledger=l;values=controller.settle(r,m,nav)
            self.assertIsNone(controller.client);self.assertTrue(m.equal(mb));self.assertEqual(float(nav.sum()),0.)
            self.assertAlmostEqual(float(r.sum()),expected,places=6)
            self.assertFalse(list(Path(tmp).rglob('*.png')));self.assertFalse((Path(tmp)/'worker.log').exists())
            rows=[json.loads(x) for x in (Path(tmp)/'segments.jsonl').read_text().splitlines()]
            self.assertEqual(len(rows),4)
            self.assertTrue(all('result' not in row and 'q' not in row and row['reward_source']=='geometry' for row in rows))
            self.assertIn('geometry_bonus_sum',values);self.assertNotIn('qwen_q_mean',values)
    def test_geometry_eval_does_not_collect(self):
        cfg=config('geometry_c128');obj=PPOTrainer(cfg)
        with read_write(cfg):cfg.qwen_reward.collect=True
        with patch('src.trainer.construct_envs',return_value=None):obj._init_envs(is_eval=True)
        self.assertFalse(cfg.habitat.qwen_reward.collect)

if __name__=='__main__':unittest.main()
