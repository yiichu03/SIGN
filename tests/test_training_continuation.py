import copy
import hashlib
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace as NS
import unittest

import torch
from src.training_continuation import restore_training, continuation_pending, add_learner_state


class Agent(torch.nn.Module):
    def __init__(self):
        super().__init__()
        self.actor_critic = torch.nn.Module()
        self.actor_critic.net = torch.nn.Module()
        self.actor_critic.net.visual_encoder = torch.nn.Linear(2, 2)
        self.actor_critic.net.visual_encoder.requires_grad_(False)
        self.actor_critic.net.visual_encoder.eval()
        self.actor_critic.head = torch.nn.Linear(2, 1)
        self.actor_critic.Qc = torch.nn.Linear(2, 1)
        self.optimizer = torch.optim.Adam([p for p in self.parameters() if p.requires_grad], lr=.003)
        self.actor_critic.Qc_opt = torch.optim.Adam(self.actor_critic.Qc.parameters(), lr=.0001)
        self.use_aug_flag = True


class ContinuationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.folder = Path(self.tmp.name)
        self.agent = Agent()
        self.config = NS(habitat_baselines=NS(num_environments=8,total_num_steps=300000000,
            checkpoint_folder=str(self.folder/'ckpts'),rl=NS(ppo=NS(num_steps=256),
            data_augmentation=NS(stop_step=50000000))))
        self.trainer = NS(agent=self.agent, actor_critic=self.agent.actor_critic,config=self.config,
            num_steps_done=0,num_updates_done=0)
        self.trainer.percent_done = lambda:self.trainer.num_steps_done/300000000
        self.original = copy.deepcopy(self.agent.state_dict())

    def checkpoint(self, step=8192000, extra=None):
        checkpoint=dict(state_dict=copy.deepcopy(self.original),extra_state=dict(step=step,wall_time=123.))
        checkpoint['state_dict']['actor_critic.head.weight'] += 1
        if extra: checkpoint.update(extra)
        path=self.folder/'input.pth';torch.save(checkpoint,path)
        self.config.training_continuation=NS(checkpoint=str(path),sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
            allow_legacy_weights=True,stop_after_steps=4096)
        return checkpoint,path

    def test_legacy_restores_all_weights_global_counters_and_freeze(self):
        checkpoint,_=self.checkpoint();restore_training(self.trainer)
        for k,v in self.agent.state_dict().items():self.assertTrue(torch.equal(v,checkpoint['state_dict'][k]))
        self.assertEqual(self.trainer.num_steps_done,8192000)
        self.assertEqual(self.trainer.num_updates_done,4000)
        self.assertEqual(self.trainer._continuation_previous_walltime,123.)
        self.assertFalse(self.agent.optimizer.state)
        self.assertFalse(self.agent.actor_critic.Qc_opt.state)
        self.assertFalse(self.agent.actor_critic.net.visual_encoder.training)
        self.assertTrue(all(not p.requires_grad for p in self.agent.actor_critic.net.visual_encoder.parameters()))
        receipt=json.loads((self.folder/'continuation.json').read_text())
        self.assertEqual(receipt['mode'],'legacy_weights_optimizer_reset')
        self.assertFalse(receipt['exact_trajectory_resume'])

    def test_bad_sha_does_not_change_model(self):
        self.checkpoint();self.config.training_continuation.sha256='bad'
        with self.assertRaisesRegex(RuntimeError,'SHA'):restore_training(self.trainer)
        for k,v in self.agent.state_dict().items():self.assertTrue(torch.equal(v,self.original[k]))

    def test_invalid_step_and_nonfinite_are_rejected(self):
        for step in [0,8192001,300000000,True]:
            self.checkpoint(step)
            with self.assertRaisesRegex(RuntimeError,'step'):restore_training(self.trainer)
        checkpoint,path=self.checkpoint();checkpoint['state_dict']['actor_critic.head.weight'].fill_(float('nan'))
        torch.save(checkpoint,path);self.config.training_continuation.sha256=hashlib.sha256(path.read_bytes()).hexdigest()
        with self.assertRaisesRegex(RuntimeError,'Non-finite'):restore_training(self.trainer)

    def test_legacy_requires_explicit_opt_in(self):
        self.checkpoint();self.config.training_continuation.allow_legacy_weights=False
        with self.assertRaisesRegex(RuntimeError,'opt-in'):restore_training(self.trainer)

    def test_encoder_change_and_wrong_keys_are_rejected(self):
        for change in ['encoder','keys']:
            checkpoint,path=self.checkpoint()
            if change=='encoder':checkpoint['state_dict']['actor_critic.net.visual_encoder.weight']+=1
            else:checkpoint['state_dict'].pop('actor_critic.head.weight')
            torch.save(checkpoint,path);self.config.training_continuation.sha256=hashlib.sha256(path.read_bytes()).hexdigest()
            with self.assertRaises(RuntimeError):restore_training(self.trainer)

    def test_mrq_cutoff_and_short_limit_keep_global_300m_cap(self):
        self.checkpoint(125952000);restore_training(self.trainer)
        self.assertFalse(self.agent.use_aug_flag)
        self.assertTrue(continuation_pending(self.trainer))
        self.trainer.num_steps_done+=4096
        self.assertFalse(continuation_pending(self.trainer))
        self.assertEqual(self.config.habitat_baselines.total_num_steps,300000000)
        self.config.training_continuation.stop_after_steps=0
        self.assertTrue(continuation_pending(self.trainer))

    def test_future_optimizer_and_qc_state_round_trip(self):
        self.checkpoint();restore_training(self.trainer)
        x=torch.ones(3,2)
        self.agent.actor_critic.head(x).sum().backward();self.agent.optimizer.step()
        self.agent.actor_critic.Qc_opt.zero_grad();self.agent.actor_critic.Qc(x).sum().backward();self.agent.actor_critic.Qc_opt.step()
        checkpoint={'state_dict':copy.deepcopy(self.agent.state_dict()),'extra_state':{'step':8192000,'wall_time':124.}}
        add_learner_state(self.trainer,checkpoint)
        path=self.folder/'future.pth';torch.save(checkpoint,path)
        self.agent.optimizer.state.clear();self.agent.actor_critic.Qc_opt.state.clear()
        self.config.training_continuation.checkpoint=str(path);self.config.training_continuation.sha256=hashlib.sha256(path.read_bytes()).hexdigest()
        restore_training(self.trainer)
        self.assertTrue(self.agent.optimizer.state);self.assertTrue(self.agent.actor_critic.Qc_opt.state)
        for state in self.agent.optimizer.state.values():self.assertEqual(state['step'].item(),1)
        self.assertEqual(json.loads((self.folder/'continuation.json').read_text())['mode'],'learner_state')

    def test_disabled_leaves_original_behavior(self):
        restore_training(self.trainer);self.assertTrue(continuation_pending(self.trainer))
        checkpoint={};add_learner_state(self.trainer,checkpoint)
        self.assertEqual(checkpoint,{})


if __name__=='__main__':
    torch.set_num_threads(1)
    unittest.main()
