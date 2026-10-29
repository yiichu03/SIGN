"""Training reward invariants; no model or GPU required."""
import copy
import gzip
import json
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import numpy as np
import torch
import run_sim
from habitat.config import read_write
from habitat_baselines.config.default import get_config
from src.qwen_geometry import EpisodeCoverage, GeometryError, render
from src.qwen_rollout import SegmentCollector, SegmentLedger, PAYLOAD_KEY
from src.custom_rollout_storage import CostRolloutStorage
from src.trainer import PPOTrainer
from src.utils import change_habitat_config
from src.algo.PPO import DA_PPO
from gym import spaces

ROOT=Path(__file__).resolve().parents[1]
torch.set_num_threads(1)

class LedgerTests(unittest.TestCase):
    def build(self, episodes=(1,127,128,129,255,256), H=256):
        c=SegmentCollector(128,H);c.env_id=0;c.reset('scene','ep0',None,'invalid_fixture')
        ledger=SegmentLedger(1,H,128);masks=torch.ones(H+1,1,1,dtype=torch.bool)
        for t in range(H):
            done=t+1 in episodes
            payload=c.step((0,0),0.,[0,0,0],done)
            # Use synthetic valid snapshots only for reward ledger tests.
            for s in payload[1]:s['valid_geometry']=True
            infos=[{PAYLOAD_KEY:copy.deepcopy(payload),'scalar':1.}]
            ledger.collect(t,[done],infos)
            self.assertNotIn(PAYLOAD_KEY,infos[0]);self.assertEqual(infos[0]['scalar'],1.)
            masks[t+1]=not done
            if done:c.reset('scene',f'ep{c.reset_index+1}',None,'invalid_fixture')
        return c,ledger,masks
    def test_terminal_128_rollout_boundaries_and_formula(self):
        _,l,m=self.build();nav=torch.randn(257,1,1,dtype=torch.float64);r=nav.clone();mb=m.clone()
        results=[dict(id=s['segment_id'],q=.75,valid=True) for s in l.pending]
        bonus=l.add(r,m,results,.1)
        self.assertAlmostEqual(sum(bonus),.075)
        expected=torch.zeros_like(r)
        for s,b in zip(l.pending,bonus):expected[s['end_row'],0,0]+=b
        torch.testing.assert_close(r-nav,expected,atol=1e-15,rtol=0)
        self.assertTrue(torch.equal(m,mb));self.assertTrue(torch.equal(nav,r-expected))
        self.assertEqual([(s['global_start'],s['global_end']) for s in l.pending],
                         [(0,1),(1,127),(127,128),(128,129),(129,255),(255,256)])
        with self.assertRaisesRegex(RuntimeError,'already scored'):l.add(r,m,results,.1)
    def test_cross_rollout_history_not_reset(self):
        c,l,m=self.build(episodes=())
        l.add(torch.zeros(257,1,1),m,[dict(id=s['segment_id'],q=.4,valid=True) for s in l.pending],.1)
        l.advance()
        for t in range(256):
            payload=c.step((0,0),0.,[0,0,0],False)
            l.collect(t,[False],[{PAYLOAD_KEY:payload}])
        self.assertEqual([(s['start'],s['end']) for s in l.pending],[(256,384),(384,512)])
        self.assertEqual({s['reset_index'] for s in l.pending},{0})
        l.validate(m)
    def test_wrong_response_ids_are_atomic_failure(self):
        _,l,m=self.build(episodes=());r=torch.ones(257,1,1);before=r.clone()
        with self.assertRaisesRegex(RuntimeError,'ID mismatch'):l.add(r,m,[dict(id='wrong',q=.5,valid=True)]*2,.1)
        self.assertTrue(torch.equal(r,before))
    def test_invalid_q_is_atomic_failure(self):
        for q in (None,float('nan'),-1,1.1,True):
            _,l,m=self.build(episodes=());r=torch.zeros(257,1,1)
            rows=[dict(id=s['segment_id'],q=q,valid=True) for s in l.pending]
            with self.assertRaises(RuntimeError):l.add(r,m,rows,.1)
            self.assertEqual(float(r.sum()),0.)
    def test_mask_disagreement_fails(self):
        _,l,m=self.build();m[1]=True
        with self.assertRaisesRegex(RuntimeError,'real mask'):l.validate(m)
    def test_invalid_geometry_skips_without_fake_q(self):
        _,l,m=self.build(episodes=())
        for s in l.pending:s['valid_geometry']=False
        r=torch.randn(257,1,1);before=r.clone();self.assertEqual(l.add(r,m,[],.1),[])
        self.assertTrue(torch.equal(r,before))
    def test_zero_beta_bitwise_identity(self):
        _,l,m=self.build();r=torch.randn(257,1,1);before=r.clone()
        l.add(r,m,[dict(id=s['segment_id'],q=.9,valid=True) for s in l.pending],0.)
        self.assertTrue(torch.equal(r,before))
    def test_payload_is_independent_before_reset(self):
        c,l,m=self.build(episodes=());s=copy.deepcopy(l.pending[-1]);c.reset('newscene','new',None,'bad')
        self.assertEqual(s['episode_id'],'ep0');self.assertEqual(s['end'],256)
        from habitat.utils.gym_adapter import flatten_dict
        info=flatten_dict({PAYLOAD_KEY:((0,0,'ep',1,1),({'grid':np.ones((3,3))},))})
        self.assertIn(PAYLOAD_KEY,info)
    def test_identity_and_missing_payload_errors(self):
        for payload in [None,((1,0,'ep',1,1),()),((0,1,'ep',1,1),())]:
            l=SegmentLedger(1)
            with self.assertRaises(RuntimeError):l.collect(0,[False],[{} if payload is None else {PAYLOAD_KEY:payload}])

class GeometryTests(unittest.TestCase):
    def test_incremental_matches_original_offline_masks_and_stats(self):
        root=ROOT/'docs/experiments/qwen-history-solid'
        segments=json.loads((root/'windows.json').read_text())['segments']
        cases=[s for s in segments if s['history_action_count']>0][:3]
        self.assertEqual(len(cases),3)
        for s in cases:
            t=json.loads(gzip.decompress((root/'sources'/s['trajectory_id']/'trajectory.json.gz').read_bytes()))
            with np.load(root/s['masks']) as a:
                g=EpisodeCoverage(a['grid']);g.bounds=s['bounds']
                for i,pose in enumerate(t['poses'][:s['end']+1]):
                    g.observe(a['coords'][i],pose['heading_rad'],pose['position_xyz'])
                    if i==s['start']:g.cut()
                out=g.snapshot()
                self.assertTrue(out['valid_geometry'],out['geometry_reason'])
                self.assertTrue(np.array_equal(out['prior_seen'],a['prior_seen']))
                self.assertTrue(np.array_equal(out['final_seen'],a['final_seen']))
                self.assertEqual(out['metadata'],s['history_stats'])
    def test_initial_view_and_repeated_observation(self):
        g=EpisodeCoverage(np.ones((100,100),np.uint8));p=[0.,0.,0.]
        g.observe((50,50),0.,p)
        for _ in range(128):g.observe((50,50),0.,p)
        s=g.snapshot();self.assertEqual(s['metadata']['new_area_m2'],0.)
        g.cut();g.observe((50,50),1.,p);self.assertEqual(len(g.coords),130)
        self.assertEqual(g.snapshot()['start'],128)
        g2=EpisodeCoverage(np.ones((100,100),np.uint8));g2.observe((50,50),0.,p)
        self.assertEqual(len(g2.coords),1);self.assertEqual(g2.segment_start,0)
    def test_geometry_failure_reasons(self):
        with self.assertRaises(GeometryError):EpisodeCoverage(np.zeros((10,10)))
        g=EpisodeCoverage(np.ones((10,10)));g.observe((3,3),0.,[0,0,0]);g.observe((3,3),0.,[0,1,0])
        self.assertFalse(g.snapshot()['valid_geometry']);self.assertIn('height',g.reason)

class IntegrationTests(unittest.TestCase):
    def config(self):
        paths=['exp_config/ppo_imagenav_gibson.yaml']+['src/config/'+n+'.yaml' for n in ['policy','reward','sensors','qwen_reward']]
        return change_habitat_config(get_config(paths,[]))
    def test_disabled_and_zero_do_not_start_worker_or_collect(self):
        for enabled,beta in [(False,.1),(True,0.)]:
            cfg=self.config()
            with read_write(cfg):cfg.qwen_reward.enabled=enabled;cfg.qwen_reward.beta=beta
            obj=PPOTrainer(cfg)
            with patch('src.qwen_reward.subprocess.Popen',side_effect=AssertionError('worker forbidden')):
                with patch.object(obj,'_init_envs',side_effect=RuntimeError('stop')):
                    with self.assertRaisesRegex(RuntimeError,'stop'):obj._init_train()
            self.assertFalse(cfg.qwen_reward.collect);self.assertIsNone(obj._qwen_reward)
    def test_eval_disables_root_and_spawn_subtree(self):
        cfg=self.config();obj=PPOTrainer(cfg)
        with read_write(cfg):cfg.qwen_reward.collect=True
        with patch('src.trainer.construct_envs',return_value=None):obj._init_envs(is_eval=True)
        self.assertFalse(cfg.qwen_reward.enabled);self.assertFalse(cfg.habitat.qwen_reward.collect)
    def test_nav_buffer_separate_and_mrq_compatibility(self):
        storage=CostRolloutStorage(256,1,spaces.Dict({'x':spaces.Box(0,1,(2,),dtype=np.float32)}),spaces.Discrete(2),8)
        nav=torch.tensor([[2.]])
        storage.insert(rewards=nav);storage.buffers['rewards'][0,0,0]+=.05
        self.assertEqual(storage.buffers['nav_rewards'][0,0,0].item(),2.)
        self.assertNotEqual(storage.buffers['nav_rewards'].data_ptr(),storage.buffers['rewards'].data_ptr())
        obj=SimpleNamespace();DA_PPO.add_config(obj,self.config());self.assertTrue(obj.mrq_navigation_only)
        cfg=self.config()
        with read_write(cfg):cfg.qwen_reward.beta=0
        DA_PPO.add_config(obj,cfg);self.assertFalse(obj.mrq_navigation_only)
        DA_PPO.add_config(obj,SimpleNamespace());self.assertFalse(obj.mrq_navigation_only)

if __name__=='__main__':unittest.main()
