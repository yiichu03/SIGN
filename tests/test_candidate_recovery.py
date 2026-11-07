import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
sys.path.insert(0,str(Path(__file__).resolve().parent))
from src.recovery_affordance import candidate_image, reversed_prompt, semantic_probabilities, select_candidate, LABELS
from src.inference_recovery import RecoveryHarness
from test_inference_recovery import settings


def item(p, inverse=None):
    return dict(probabilities=p,reversed_probabilities=p[::-1] if inverse is None else inverse)


class CandidatePolicyTests(unittest.TestCase):
    def test_semantic_order_is_preserved_when_labels_reverse(self):
        self.assertEqual(semantic_probabilities([.1,.3,.6]),semantic_probabilities([.6,.3,.1],True))

    def test_unknown_and_identical_views_fall_back_to_either_rule(self):
        for fallback in ['A','B']:
            label,detail=select_candidate(item([.2,.6,.2]),item([.2,.6,.2]),fallback)
            self.assertEqual(label,fallback);self.assertEqual(detail['source'],'rule_fallback')

    def test_relative_evidence_can_select_below_half_open_probability(self):
        label,detail=select_candidate(item([.12,.39,.49]),item([.6,.2,.2]),'B')
        self.assertEqual(label,'A');self.assertEqual(detail['source'],'vlm');self.assertTrue(detail['differs_from_rule'])

    def test_label_order_disagreement_falls_back(self):
        label,detail=select_candidate(item([.1,.1,.8],[.1,.1,.8]),item([.8,.1,.1],[.8,.1,.1]),'B')
        self.assertEqual(label,'B');self.assertEqual(detail['source'],'rule_fallback')

    def test_less_blocked_alone_is_not_open_evidence(self):
        label,detail=select_candidate(item([.6,.3,.1]),item([.9,.09,.01]),'B')
        self.assertEqual(label,'B');self.assertEqual(detail['source'],'rule_fallback')

    def test_uncertain_winner_does_not_become_a_supported_action(self):
        label,detail=select_candidate(item([.1,.6,.3]),item([.6,.3,.1]),'B')
        self.assertEqual(label,'B');self.assertEqual(detail['source'],'rule_fallback')

    def test_swapping_candidates_reverses_supported_direction(self):
        clear,blocked=item([.1,.1,.8]),item([.8,.1,.1])
        self.assertEqual(select_candidate(clear,blocked,'B')[0],'A')
        self.assertEqual(select_candidate(blocked,clear,'A')[0],'B')

    def test_invalid_probability_or_gap_is_rejected(self):
        for values in [[float('nan'),0,1],[.4,.4,.4],[-.1,.1,1],[1,0]]:
            with self.assertRaises(ValueError):semantic_probabilities(values)
        with self.assertRaises(ValueError):select_candidate(item([.1,.1,.8]),item([.8,.1,.1]),'A',0)

    def test_prompt_reversal_requires_exactly_one_label_definition(self):
        value=reversed_prompt('prefix\n'+LABELS+'\nsuffix')
        self.assertIn('A: OPEN\nB: UNCERTAIN\nC: BLOCKED',value)
        for invalid in ['missing',LABELS+'\n'+LABELS]:
            with self.assertRaises(ValueError):reversed_prompt(invalid)

    def test_rendering_has_no_side_or_filename_condition(self):
        with tempfile.TemporaryDirectory() as folder:
            image=np.full((64,64,3),90,dtype=np.uint8);folder=Path(folder)
            left=candidate_image(image,image,folder/'left.png')
            right=candidate_image(image,image,folder/'right.png')
            self.assertEqual(left['image_sha256'],right['image_sha256'])
            self.assertEqual(left['image_sha256'],hashlib.sha256((folder/'left.png').read_bytes()).hexdigest())


class CandidateClient:
    made=0
    bad_id=False
    uncertain=False
    rows=[]
    def __init__(self,cfg,output):type(self).made+=1
    def score(self,request,rows):
        type(self).rows=rows
        values=[]
        for row in rows:
            p=[.2,.6,.2] if self.uncertain else [.1,.1,.8] if row['side']=='right' else [.8,.1,.1]
            values.append(dict(id='wrong' if self.bad_id else row['id'],**item(p)))
        return dict(seconds=.1,results=values)
    def close(self):pass


class CandidateHarnessTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        self.frame=np.full((64,64,3),90,dtype=np.uint8)
        CandidateClient.made=0;CandidateClient.bad_id=False;CandidateClient.uncertain=False;CandidateClient.rows=[]

    def harness(self,mode='qwen',n=1,**opts):
        config=dict(mode=mode,active_survey=True,survey_turn_steps=1,turn_steps=1,forward_steps=1,
            candidate_affordance=True,candidate_support_gap=.05,cooldown=0)
        config.update(opts)
        return RecoveryHarness(settings(**config),n,self.root/mode,CandidateClient)

    def step(self,h,masks=None,actions=None):
        n=len(h.states)
        return h.step([self.frame]*n,[self.frame]*n,
            np.asarray([[.8,0.]]*n if actions is None else actions,dtype=np.float32),
            np.ones(n,dtype=bool) if masks is None else masks,[('scene',str(i)) for i in range(n)])

    def test_independent_candidate_ids_metadata_and_model_disagreement(self):
        h=self.harness(n=2)
        for _ in range(9):actual=self.step(h)
        np.testing.assert_array_equal(actual,[[-1.,-1.],[-1.,-1.]])
        self.assertEqual(len(CandidateClient.rows),4)
        self.assertEqual([row['side'] for row in CandidateClient.rows],['left','right','left','right'])
        self.assertEqual(len({row['id'] for row in CandidateClient.rows}),4)
        for row in CandidateClient.rows:
            self.assertEqual(row['image_sha256'],hashlib.sha256(Path(row['image']).read_bytes()).hexdigest())
        for state in h.states:
            self.assertEqual((state.vlm_selections,state.fallback_selections,state.vlm_rule_disagreements),(1,0,1))

    def test_uncertain_model_uses_alternating_rule_without_forced_vlm(self):
        CandidateClient.uncertain=True;h=self.harness()
        for _ in range(40):self.step(h)
        events=[json.loads(line) for line in (h.output/'events.jsonl').read_text().splitlines()]
        self.assertEqual([e['choice'] for e in events],['A','B'])
        self.assertTrue(all(e['model']['source']=='rule_fallback' for e in events))
        self.assertEqual((h.states[0].vlm_selections,h.states[0].fallback_selections),(0,2))
        self.assertLessEqual(h.states[0].overrides,h.max_override_steps)

    def test_bad_candidate_id_stops_instead_of_assigning_another_environment(self):
        CandidateClient.bad_id=True;h=self.harness(n=2)
        with self.assertRaisesRegex(RuntimeError,'ID/order mismatch'):
            for _ in range(9):self.step(h)

    def test_matched_rule_renders_candidates_without_worker(self):
        h=self.harness(mode='rule')
        for _ in range(10):self.step(h)
        self.assertEqual(CandidateClient.made,0)
        event=json.loads((h.output/'events.jsonl').read_text().splitlines()[0])
        self.assertEqual([x['side'] for x in event['candidates']],['left','right'])
        self.assertEqual(h.states[0].vlm_selections,0)

    def test_zero_intervention_keeps_actions_masks_and_worker_untouched(self):
        h=self.harness(max_interventions=0);masks=np.ones(1,dtype=bool)
        for _ in range(20):
            np.testing.assert_array_equal(self.step(h,masks=masks),np.asarray([[.8,0.]],dtype=np.float32))
        self.assertTrue(masks[0]);self.assertEqual(CandidateClient.made,0)

    def test_policy_stop_cancels_survey_before_any_candidate_request(self):
        h=self.harness()
        for _ in range(5):self.step(h)
        np.testing.assert_array_equal(self.step(h,actions=[[-1.,0.]]),[[-1.,0.]])
        self.assertIsNone(h.states[0].survey);self.assertEqual(CandidateClient.made,0)

    def test_real_reset_discards_old_survey_and_candidate_ids(self):
        h=self.harness()
        for _ in range(5):self.step(h)
        self.step(h,masks=np.zeros(1,dtype=bool))
        self.assertEqual(h.states[0].attempts,0);self.assertIsNone(h.states[0].survey)
        self.assertEqual(CandidateClient.made,0)


if __name__=='__main__':unittest.main()
