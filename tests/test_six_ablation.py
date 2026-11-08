import collections
import json
from pathlib import Path
import random
import sys
import tempfile
from types import SimpleNamespace
import unittest
import numpy as np
TREE=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(TREE));sys.path.insert(0,str(TREE/'src'));sys.path.insert(0,str(TREE/'scripts'))
from src.recovery_options import balanced_option_map,action_probabilities,PERMUTATIONS
from src.recovery_agent import select_agent,save_rgb
from src.inference_recovery import RecoveryHarness,physical
from test_inference_recovery import settings
from recovery_worker import agent_score
from memory_four_arm import ARMS

class HybridClient:
    rows=[];word='left';made=0
    def __init__(self,cfg,output):type(self).made+=1
    def score(self,request,rows):
        values=[];self.rows.extend(rows)
        for row in rows:
            word=self.word;prob=[.9 if x==word else .05 for x in ['left','right','keep']]
            if row['task']=='balanced_arbitration':
                p=[prob[['LEFT','RIGHT','KEEP'].index(row['option_map'][x])] for x in 'ABC']
                value=dict(probabilities=p,action_probabilities=action_probabilities(p,row['option_map']),option_map=row['option_map'])
            else:value=dict(probabilities=prob)
            values.append(dict(value,id=row['id'],candidate_mass=.98,valid=True))
        return dict(results=values,seconds=.1)
    def close(self):pass

class SixTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.folder=Path(self.tmp.name);self.index=0
        self.frame=np.random.RandomState(3).randint(0,256,(64,64,3)).astype('uint8')
        HybridClient.rows=[];HybridClient.word='left';HybridClient.made=0
    def make(self,**changes):
        self.index+=1
        cfg=dict(mode='qwen',agent_variant='A',active_survey=True,candidate_affordance=True,candidate_protocol='agent',
            survey_turn_steps=6,turn_steps=6,forward_steps=8)
        cfg.update(changes)
        return RecoveryHarness(settings(**cfg),1,self.folder/str(self.index),HybridClient)
    def step(self,h,reset=False,key=('scene','1'),action=(.8,0),goal=None):
        mask=np.array([not reset]);before=mask.copy()
        value=h.step([self.frame],[self.frame if goal is None else goal],np.asarray([action],np.float32),mask,[key])
        np.testing.assert_equal(mask,before);return value[0]
    def test_six_permutations_balance_and_determinism_without_global_rng(self):
        py=random.getstate();npstate=np.random.get_state()
        for block in range(4):
            maps=[balanced_option_map(block*6+i) for i in range(6)]
            self.assertEqual(len({tuple(m.values()) for m in maps}),6)
            for option in 'ABC':self.assertEqual(collections.Counter(m[option] for m in maps),dict(LEFT=2,RIGHT=2,KEEP=2))
            self.assertEqual(maps,[balanced_option_map(block*6+i) for i in range(6)])
        self.assertEqual(py,random.getstate());np.testing.assert_equal(npstate[1],np.random.get_state()[1])
        self.assertEqual(npstate[2:],np.random.get_state()[2:])
    def test_invalid_map_and_index(self):
        for i in [-1,1.5,'2']:
            with self.assertRaises(ValueError):balanced_option_map(i)
        for mapping in [{'A':'LEFT','B':'LEFT','C':'KEEP'},{'A':'LEFT'}]:
            with self.assertRaises(ValueError):action_probabilities([.4,.3,.3],mapping)
        with self.assertRaises(ValueError):action_probabilities([float('nan'),0,1],balanced_option_map(0))
    def test_raw_option_a_can_mean_right_or_keep(self):
        for mapping,word in [({'A':'RIGHT','B':'KEEP','C':'LEFT'},'right'),({'A':'KEEP','B':'LEFT','C':'RIGHT'},'keep')]:
            value=dict(probabilities=[.9,.05,.05],action_probabilities=action_probabilities([.9,.05,.05],mapping),candidate_mass=.99)
            self.assertEqual(select_agent(value)[0],word)
    def test_mapping_counter_survives_real_episode_reset(self):
        h=self.make(option_mapping='balanced')
        for episode in range(6):
            self.step(h,reset=True,key=('s',str(episode)))
            for _ in range(28):self.step(h,key=('s',str(episode)))
        self.assertEqual([r['mapping_index'] for r in HybridClient.rows],list(range(6)))
        self.assertEqual(len({tuple(r['option_map'].values()) for r in HybridClient.rows}),6)
        for row in HybridClient.rows:
            self.assertEqual(row['task'],'balanced_arbitration')
            self.assertEqual(json.loads(row['context'])['option_to_action'],row['option_map'])
    def test_no_goal_request_three_views_even_when_goal_blank(self):
        h=self.make(include_goal=False)
        for _ in range(29):self.step(h,goal=np.zeros_like(self.frame))
        self.assertEqual(len(HybridClient.rows),1)
        row=HybridClient.rows[0];self.assertEqual(row['task'],'no_goal_arbitration')
        self.assertEqual([x['role'] for x in row['images']],['CURRENT','LEFT','RIGHT'])
        text=(TREE/'scripts/prompts/recovery_agent_no_goal.txt').read_text().lower()
        self.assertNotIn('goal',text);self.assertNotIn('target',text)
    def test_baseline_still_has_four_views_and_original_prompt(self):
        h=self.make()
        for _ in range(29):self.step(h)
        row=HybridClient.rows[0];self.assertEqual(row['task'],'arbitration')
        self.assertEqual([x['role'] for x in row['images']],['GOAL','CURRENT','LEFT','RIGHT'])
        self.assertNotIn('option_map',row);self.assertNotIn('option_to_action',row['context'])
    def test_confidence_gate_keeps_uncertain_argmax(self):
        value=dict(probabilities=[.45,.3,.25],candidate_mass=.99)
        self.assertEqual(select_agent(value)[0],'left')
        self.assertEqual(select_agent(value,minimum=.5,margin=.1),('keep','confidence_keep'))
        self.assertEqual(select_agent(dict(probabilities=[.6,.25,.15],candidate_mass=.99),minimum=.5,margin=.1)[0],'left')
    def test_confidence_gate_threshold_boundary(self):
        self.assertEqual(select_agent(dict(probabilities=[.5,.4,.1],candidate_mass=.99),minimum=.5,margin=.1),('left','model_argmax'))
        self.assertEqual(select_agent(dict(probabilities=[.5,.5,0],candidate_mass=.99),minimum=.5,margin=.1)[0],'keep')
    def test_e4_forward_four_steps_and_budget68(self):
        h=self.make(forward_steps=4,cooldown=6)
        for _ in range(130):self.step(h)
        self.assertEqual(h.max_override_steps,68);self.assertEqual(h.states[0].overrides,68)
        events=[json.loads(l) for l in (h.output/'events.jsonl').read_text().splitlines()]
        self.assertEqual(len(events[0]['planned_actions']),10)
        self.assertEqual(sum(physical(a)[0]>.1 for a in events[0]['planned_actions']),4)
    def test_e5_scan_recovery_angles_and_budget56(self):
        h=self.make(survey_turn_steps=4,turn_steps=4)
        for _ in range(21):self.step(h)
        row=HybridClient.rows[0]
        self.assertEqual(json.loads(row['context'])['candidate_angles_command_deg'],{'LEFT':60,'RIGHT':-60})
        self.assertEqual(h.max_override_steps,56)
        event=json.loads((h.output/'events.jsonl').read_text().splitlines()[0])
        self.assertEqual(event['survey_command_steps'],16);self.assertEqual(event['commanded_view_yaw'],60)
        self.assertEqual(sum(abs(physical(a)[1]) for a in event['planned_actions'][:4]),60)
        self.assertEqual(len(event['planned_actions']),12)
        text=(TREE/'scripts/prompts/recovery_agent_60.txt').read_text();self.assertIn('+60',text);self.assertNotIn('+90',text)
    def test_mismatched_scan_and_recovery_angle_fails(self):
        with self.assertRaises(ValueError):self.make(survey_turn_steps=4,turn_steps=6)
    def test_e6_triggers_at12_not16(self):
        h=self.make(window=12);old=self.make(window=16)
        for _ in range(12):self.step(h);self.step(old)
        self.assertEqual(h.events,0);self.step(h);self.step(old)
        self.assertEqual(h.events,1);self.assertEqual(old.events,0)
    def test_stop_priority_for_all_six(self):
        changes=[dict(option_mapping='balanced'),dict(include_goal=False),dict(agent_confidence_gate=True),dict(forward_steps=4),
            dict(survey_turn_steps=4,turn_steps=4),dict(window=12)]
        for cfg in changes:
            h=self.make(**cfg)
            for _ in range(h.cfg.window+2):self.step(h)
            before=len(HybridClient.rows);actual=self.step(h,action=(-1,0))
            np.testing.assert_equal(actual,[-1,0]);self.assertFalse(h.states[0].actions);self.assertIsNone(h.states[0].survey)
            self.assertEqual(before,len(HybridClient.rows))
    def test_single_factor_profile_keys(self):
        expected=dict(E1={'agent_variant','option_mapping'},E2={'agent_variant','include_goal'},E3={'agent_variant','agent_confidence_gate'},
            E4={'agent_variant','forward_steps'},E5={'agent_variant','survey_turn_steps','turn_steps','prompt'},E6={'agent_variant','window'})
        for arm,keys in expected.items():self.assertEqual(set(ARMS[arm][1]),keys)
    def test_worker_mapping_preserves_raw_logits(self):
        images=[save_rgb(role,self.frame,self.folder/(role+'.png')) for role in ['GOAL','CURRENT','LEFT','RIGHT']]
        mapping={'A':'RIGHT','B':'KEEP','C':'LEFT'}
        row=dict(id='r',task='balanced_arbitration',images=images,option_map=mapping,context=json.dumps(dict(option_to_action=mapping)))
        class Judge:
            prompt=''
            def choice_probabilities(self,rows,labels):
                return [dict(valid=True,probabilities=[.8,.15,.05],logits=[4.,2.,1.],labels=list(labels),candidate_mass=.99) for _ in rows],{}
        values=agent_score(Judge(),[row],{'balanced_arbitration':'prompt'},self.folder,0,set(),False)
        self.assertEqual(values[0]['probabilities'],[.8,.15,.05]);self.assertEqual(values[0]['logits'],[4.,2.,1.])
        self.assertEqual(values[0]['action_probabilities'],[.05,.8,.15]);self.assertEqual(select_agent(values[0])[0],'right')
        row['context']='{}'
        with self.assertRaisesRegex(RuntimeError,'mapping context'):agent_score(Judge(),[row],{'balanced_arbitration':'p'},self.folder,1,set(),False)

if __name__=='__main__':unittest.main()
