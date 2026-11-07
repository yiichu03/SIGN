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
from src.recovery_affordance import select_semantic_candidate,raw_candidate_image,decision_prefix_audit,select_directional
from src.inference_recovery import RecoveryHarness, yaw_aligned_change, detect
from qwen_single_image import SingleImageJudge
from test_candidate_recovery import CandidateClient
from test_inference_recovery import settings


class SemanticRecoveryTests(unittest.TestCase):
    def test_joint_directional_selection_preserves_unknown_and_format_gate(self):
        item=dict(probabilities=[.2,.6,.2],candidate_mass=.9)
        label,detail=select_directional(item,'A')
        self.assertEqual(label,'B');self.assertTrue(detail['differs_from_rule'])
        for p,mass in [([.2,.2,.6],1),([.45,.44,.11],1),([.1,.8,.1],.01)]:
            label,detail=select_directional(dict(probabilities=p,candidate_mass=mass),'A')
            self.assertEqual(label,'A');self.assertEqual(detail['source'],'rule_fallback')

    def test_directional_harness_sends_one_goal_collage_per_environment(self):
        class Client:
            rows=[]
            def __init__(self,cfg,out):pass
            def score(self,request,rows):
                type(self).rows=rows
                return dict(seconds=.1,results=[dict(id=r['id'],probabilities=[.1,.8,.1]) for r in rows])
            def close(self):pass
        with tempfile.TemporaryDirectory() as folder:
            cfg=settings(mode='qwen',active_survey=True,survey_turn_steps=1,turn_steps=1,forward_steps=1,
                candidate_affordance=True,candidate_protocol='directional',candidate_raw_view=True)
            h=RecoveryHarness(cfg,2,Path(folder)/'run',Client)
            frame=np.full((64,64,3),90,dtype=np.uint8)
            for _ in range(9):actual=h.step([frame]*2,[frame]*2,np.array([[.8,0.]]*2,dtype=np.float32),
                np.ones(2,dtype=bool),[('scene','1'),('scene','2')])
            self.assertEqual(len(Client.rows),2)
            self.assertEqual(len({r['id'] for r in Client.rows}),2)
            self.assertTrue(all('candidates' in r and 'side' not in r for r in Client.rows))
            np.testing.assert_array_equal(actual,[[-1.,-1.]]*2)
            self.assertTrue(all(s.vlm_rule_disagreements==1 for s in h.states))

    def test_yaw_alignment_cancels_known_rotation_not_scene_change(self):
        def panorama(degrees):
            yy, xx = np.mgrid[:32, :32]
            azimuth = np.arctan((xx-15.5)/16)-np.deg2rad(degrees)
            image = .5+.25*np.sin(3*azimuth)+.1*np.cos(2*azimuth)
            return np.repeat(image[:, :, None], 3, axis=2).astype(np.float32)
        frames = [panorama(i) for i in [0,10,0,10,0]]
        self.assertLess(yaw_aligned_change(frames[0],frames[1],10),.003)
        self.assertGreater(yaw_aligned_change(frames[0],frames[1],-10),.08)
        self.assertGreater(yaw_aligned_change(frames[0],frames[1]+.1,10),.09)
        cfg=settings(yaw_compensated=True)
        commands=[np.array([.8,w/15],dtype=np.float32) for w in [10,-10,10,-10]]
        self.assertIsNotNone(detect(frames,commands,cfg))
        cfg.yaw_compensated=False
        self.assertIsNone(detect(frames,commands,cfg))
        cfg.yaw_compensated=True
        self.assertIsNone(detect(frames,[np.array([-1,2/3])]*4,cfg))

    def test_yaw_alignment_rejects_insufficient_overlap(self):
        image=np.zeros((32,32,3),dtype=np.float32)
        self.assertEqual(yaw_aligned_change(image,image,120),1.)

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
