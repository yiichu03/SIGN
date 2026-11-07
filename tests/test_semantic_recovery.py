import inspect
from pathlib import Path
import sys
import tempfile
import unittest
import numpy as np
from PIL import Image
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
sys.path.insert(0,str(Path(__file__).resolve().parent))
from src.recovery_affordance import select_semantic_candidate,raw_candidate_image,decision_prefix_audit
from src.inference_recovery import RecoveryHarness
from qwen_single_image import SingleImageJudge
from test_candidate_recovery import CandidateClient
from test_inference_recovery import settings


class SemanticRecoveryTests(unittest.TestCase):
    def test_single_semantic_distribution_can_change_rule_direction(self):
        label,detail=select_semantic_candidate(dict(probabilities=[.8,.1,.1]),dict(probabilities=[.1,.1,.8]),'A')
        self.assertEqual(label,'B');self.assertTrue(detail['differs_from_rule'])

    def test_equal_support_is_rule_fallback(self):
        item=dict(probabilities=[.2,.6,.2])
        label,detail=select_semantic_candidate(item,item,'B')
        self.assertEqual(label,'B');self.assertEqual(detail['source'],'rule_fallback')

    def test_low_vocabulary_mass_is_not_a_supported_action(self):
        label,detail=select_semantic_candidate(dict(probabilities=[.8,.1,.1],candidate_mass=.9),
            dict(probabilities=[.1,.1,.8],candidate_mass=.01),'A')
        self.assertEqual(label,'A');self.assertEqual(detail['source'],'rule_fallback')

    def test_raw_view_has_no_goal_inset_and_preserves_complete_image(self):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/'image.png';raw_candidate_image(np.full((128,128,3),90,dtype=np.uint8),p)
            with Image.open(p) as im:
                self.assertEqual(im.size,(512,512));self.assertTrue((np.asarray(im)==90).all())

    def test_abc_api_defaults_are_preserved(self):
        self.assertEqual(inspect.signature(SingleImageJudge.class_probabilities).parameters['labels'].default,('A','B','C'))
        self.assertEqual(inspect.signature(SingleImageJudge.verify_readout).parameters['labels'].default,('A','B','C'))

    def test_invalid_semantic_label_sets_fail_before_model_forward(self):
        judge=object.__new__(SingleImageJudge)
        for labels in [('Yes','No'),('Yes','No','Yes'),('Yes','No','')]:
            with self.assertRaises(ValueError):judge.class_probabilities([],None,labels=labels)

    def test_90_degree_profile_has_bounded_actions_and_semantic_client(self):
        with tempfile.TemporaryDirectory() as folder:
            CandidateClient.uncertain=False;CandidateClient.bad_id=False
            cfg=settings(mode='qwen',active_survey=True,survey_turn_steps=6,turn_steps=6,forward_steps=4,
                candidate_affordance=True,candidate_protocol='semantic',candidate_raw_view=True)
            h=RecoveryHarness(cfg,1,Path(folder)/'run',CandidateClient)
            frame=np.full((64,64,3),90,dtype=np.uint8)
            for _ in range(29):actual=h.step([frame],[frame],np.array([[.8,0.]],dtype=np.float32),
                np.ones(1,dtype=bool),[('scene','1')])
            self.assertEqual(h.max_override_steps,68)
            np.testing.assert_array_equal(actual,[[-1.,-1.]])
            self.assertEqual(h.states[0].vlm_rule_disagreements,1)

    def test_prefix_match_requires_first_action_change_at_model_decision(self):
        base=np.zeros((4,2),dtype=np.float32);changed=base.copy();changed[2,1]=1
        poses=np.zeros((5,7),dtype=np.float32)
        self.assertEqual(decision_prefix_audit(base,poses,changed,poses,[2]),(2,True))
        self.assertEqual(decision_prefix_audit(base,poses,changed,poses,[3]),(2,False))
        moved=poses.copy();moved[1,0]=.01
        self.assertEqual(decision_prefix_audit(base,poses,changed,moved,[2]),(2,False))
        self.assertEqual(decision_prefix_audit(base,poses,base,poses,[2]),(None,False))


if __name__=='__main__':unittest.main()
