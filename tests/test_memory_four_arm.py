import hashlib
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from src.inference_recovery import RecoveryHarness
from src.recovery_agent import select_agent
from src.recovery_memory import VisualMatcher,EpisodeMemory,forward_observation,rule_memory_keep
from src.qwen_single_image import multi_image_conversations,choice_softmax
from test_inference_recovery import settings

class Client:
    made=0
    word='left'
    feedback='return'
    bad=False
    rows=[]
    def __init__(self,cfg,output):type(self).made+=1
    def score(self,request,rows):
        type(self).rows.extend(rows)
        values=[]
        for row in rows:
            labels=['continue','return'] if row['task']=='feedback' else ['left','right','keep']
            word=self.feedback if row['task']=='feedback' else self.word
            p=[.01]*len(labels);p[labels.index(word)]=1-.01*(len(labels)-1)
            values.append(dict(id='wrong' if self.bad else row['id'],probabilities=p,candidate_mass=.9,valid=True))
        return dict(results=values,seconds=.1)
    def close(self):pass

class FourArmTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.n=0
        self.frame=np.random.RandomState(2).randint(0,256,(64,64,3)).astype('uint8')
        Client.made=0;Client.rows=[];Client.word='left';Client.feedback='return';Client.bad=False
    def harness(self,arm='A',**opts):
        self.n+=1
        cfg=settings(mode='qwen',active_survey=True,candidate_affordance=True,candidate_protocol='agent',
            agent_variant=arm,survey_turn_steps=6,turn_steps=6,forward_steps=8,**opts)
        return RecoveryHarness(cfg,1,self.root/str(self.n),Client)
    def step(self,h,action=(.8,0),reset=False,key=('scene','0'),frame=None):
        return h.step([self.frame if frame is None else frame],[self.frame],np.array([action],np.float32),[not reset],[key])[0]
    def decision(self,h):
        for _ in range(29):self.step(h)
        return h.states[0]
    def test_valid_model_not_vetoed_by_rule(self):
        Client.word='right';h=self.harness();s=self.decision(h)
        self.assertEqual(s.earlier_choices,['B']);self.assertEqual(s.vlm_rule_disagreements,1)
        self.assertEqual([x['role'] for x in Client.rows[0]['images']],['GOAL','CURRENT','LEFT','RIGHT'])
        np.testing.assert_equal(s.last_action,[-1,-1])
    def test_keep_hands_back_current_policy_without_stop_or_gru_reset(self):
        Client.word='keep';h=self.harness();s=self.decision(h)
        np.testing.assert_allclose(s.last_action,[.8,0]);self.assertEqual(s.overrides,24)
        self.assertEqual(len(s.actions),0);self.assertEqual(s.cooldown_until,28+h.cfg.cooldown)
    def test_b_same_heading_and_actual_four_commands_then_return(self):
        h=self.harness('B');s=self.decision(h)
        for _ in range(10):self.step(h)
        rows=[r for r in Client.rows if r['task']=='feedback'];self.assertEqual(len(rows),1)
        self.assertEqual([x['role'] for x in rows[0]['images']],['BEFORE_FORWARD','AFTER_FORWARD'])
        ctx=json.loads(rows[0]['context']);self.assertEqual(len(ctx['actual_commands']),4)
        self.assertEqual(ctx['observation']['summed_yaw_command_deg'],0)
        self.assertEqual(s.overrides,34);np.testing.assert_allclose(s.last_action,[.8,0]);self.assertIsNone(s.probe)
    def test_b_continue_total_budget_and_no_second_feedback(self):
        Client.feedback='continue';h=self.harness('B');s=self.decision(h)
        for _ in range(15):self.step(h)
        self.assertEqual(s.overrides,38);self.assertEqual(s.feedback_calls,1)
    def test_stop_cancels_pending_feedback_without_call(self):
        h=self.harness('B');s=self.decision(h)
        for _ in range(9):self.step(h)
        self.step(h,(-1,0));self.assertIsNone(s.probe)
        self.assertFalse(any(r['task']=='feedback' for r in Client.rows))
    def test_episode_clear_and_disabled_has_no_memory_or_worker(self):
        h=self.harness('C');self.decision(h);old=h.states[0].memory
        self.step(h,reset=True,key=('new','1'));self.assertEqual(old.entries,[])
        h2=self.harness('D',max_interventions=0)
        for _ in range(50):self.step(h2)
        self.assertIsNone(h2.states[0].memory);self.assertIsNone(h2.client)
    def test_blank_safe_keep_never_queries(self):
        h=self.harness()
        for _ in range(29):self.step(h,frame=np.zeros_like(self.frame))
        self.assertEqual(Client.made,0);self.assertEqual(h.states[0].selections['C'],1)
    def test_id_mismatch_is_fatal(self):
        Client.bad=True
        with self.assertRaisesRegex(RuntimeError,'ID/order'):self.decision(self.harness())
    def test_ties_invalid_mass_and_binary_formula(self):
        self.assertEqual(select_agent(dict(probabilities=[.5,.5,0],candidate_mass=1))[0],'keep')
        self.assertEqual(select_agent(dict(probabilities=[.9,.05,.05],candidate_mass=.01))[0],'keep')
        self.assertEqual(select_agent(dict(probabilities=[.8,.2],candidate_mass=.9),True)[0],'continue')
        np.testing.assert_allclose(choice_softmax([0,0]),[.5,.5])
        with self.assertRaises(ValueError):choice_softmax([float('nan'),0])
    def test_multi_image_order_rows_and_context_isolation(self):
        rows=[dict(images=[dict(role=k,image=k+'.png') for k in ['GOAL','CURRENT','LEFT','RIGHT']],context='first'),
              dict(images=[dict(role='GOAL',image='other.png')],context='second')]
        msg=multi_image_conversations(rows,'prompt')
        self.assertEqual([Path(x['image']).name for x in msg[0][0]['content'] if x['type']=='image'],['GOAL.png','CURRENT.png','LEFT.png','RIGHT.png'])
        self.assertNotIn('first',str(msg[1]));self.assertNotIn('other.png',str(msg[0]))
        rows[0]['images'][1]['role']='GOAL'
        with self.assertRaises(ValueError):multi_image_conversations(rows,'p')
    def test_matcher_texture_identity_and_blank_negative(self):
        m=VisualMatcher();a=np.random.RandomState(4).randint(0,256,(160,160,3)).astype('uint8')
        self.assertTrue(m.match(m.view(a),m.view(a.copy()))['valid'])
        self.assertFalse(m.match(m.view(a),m.view(np.zeros_like(a)))['valid'])
        self.assertFalse(m.match(m.view(a),m.view(np.roll(a,80,axis=0)))['valid'])
    def test_outcome_memory_updates_capacity_real_commands_and_clear(self):
        mem=EpisodeMemory(SimpleNamespace(memory_capacity=2,memory_stride=4,memory_min_age=0),'outcome',('s','1'))
        for step in range(1,13):mem.observe(self.frame,[.6,0],self.frame,step,'sign')
        self.assertEqual(len(mem.entries),1);self.assertGreater(mem.stats['updates'],0)
        got=mem.retrieve({'LEFT':self.frame},20);self.assertEqual(len(got),1)
        choice,why=rule_memory_keep('A',got);self.assertEqual(choice,'C');self.assertTrue(why['changed'])
        self.assertFalse(forward_observation(self.frame,self.frame,[[-1,1]])['forward_only'])
        self.assertIsNone(forward_observation(self.frame,self.frame,[[-1,1]])['visual_mae'])
        mem.clear('test');self.assertEqual(len(mem.transitions),0);self.assertEqual(len(mem.entries),0)
    def test_d_no_match_is_exact_a_and_memory_has_no_privileged_fields(self):
        h=self.harness('D');s=self.decision(h)
        self.assertEqual(s.memory_hits,0);self.assertEqual(len(Client.rows[0]['images']),4)
        self.assertNotIn('distance',Client.rows[0]['context']);self.assertNotIn('position',Client.rows[0]['context'])

if __name__=='__main__':unittest.main()
