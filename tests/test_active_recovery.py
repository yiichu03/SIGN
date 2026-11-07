import json
from pathlib import Path
import sys
import tempfile
import unittest
import numpy as np
from PIL import Image
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'src'))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from inference_recovery import RecoveryHarness, survey_actions, physical, is_stop
from test_inference_recovery import settings, FakeClient


class ActiveRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.frame = np.full((64,64,3), 90, dtype=np.uint8)
        FakeClient.made = 0; FakeClient.bad_id = False; FakeClient.probabilities = [.8,.1,.1]

    def harness(self, mode='qwen', n=1, **opts):
        value=dict(mode=mode, active_survey=True, survey_turn_steps=1, turn_steps=1, forward_steps=1)
        value.update(opts)
        return RecoveryHarness(settings(**value), n, self.root/mode, FakeClient)

    def step(self, h, value=90, masks=None, actions=None, keys=None):
        n=len(h.states)
        return h.step([np.full_like(self.frame,value)]*n, [self.frame]*n,
            np.asarray(actions if actions is not None else [[.8,0.]]*n, dtype=np.float32),
            np.ones(n,dtype=bool) if masks is None else masks,
            [('scene',str(i)) for i in range(n)] if keys is None else keys)

    def trigger(self,h):
        for _ in range(5):result=self.step(h)
        return result

    def complete_survey(self,h):
        self.step(h,30)  # after first left command, before second action
        self.step(h,40)
        self.step(h,60)  # after two right commands
        return self.step(h,90)  # after recentering; selection uses this actual RGB

    def test_survey_returns_to_heading_without_forward_or_stop(self):
        a=survey_actions(3)
        self.assertEqual(len(a),12)
        self.assertEqual(sum(physical(x)[1] for x in a),0)
        self.assertTrue(all(physical(x)[0]==0 and not is_stop(x) for x in a))

    def test_real_frame_boundaries_and_selected_action_counts(self):
        h=self.harness();self.trigger(h)
        self.assertEqual(FakeClient.made,0)
        self.complete_survey(h);self.step(h)
        s=h.states[0]
        self.assertEqual(s.attempts,1)
        self.assertEqual((s.survey_overrides,s.recovery_overrides,s.overrides),(4,2,6))
        self.assertEqual(s.completed_surveys,1)
        row=json.loads((h.output/'events.jsonl').read_text().splitlines()[0])
        self.assertEqual(row['view_steps'],{'left':5,'right':7,'forward':8})
        self.assertEqual(row['decision_step'],8)
        self.assertEqual(row['step'],4)
        for name,value in [('left',30),('right',60),('forward',90)]:
            self.assertEqual(np.asarray(Image.open(row['view_files'][name]['path']))[0,0,0],value)
        self.assertEqual(row['commanded_view_yaw'],15)

    def test_scan_only_never_loads_model_or_counts_scan_as_recovery(self):
        h=self.harness(mode='scan');self.trigger(h);self.complete_survey(h)
        s=h.states[0]
        self.assertEqual(FakeClient.made,0)
        self.assertEqual((s.survey_overrides,s.recovery_overrides),(4,0))
        self.assertEqual(s.selections,dict(A=0,B=0,C=1))

    def test_qwen_keeps_real_C_option_after_observation(self):
        FakeClient.probabilities=[.05,.05,.9]
        h=self.harness();self.trigger(h);actual=self.complete_survey(h)
        np.testing.assert_allclose(actual,[[.8,0.]])
        self.assertEqual(h.states[0].recovery_overrides,0)
        self.assertEqual(h.states[0].survey_overrides,4)

    def test_original_stop_cancels_incomplete_survey(self):
        h=self.harness();self.trigger(h)
        actual=self.step(h,actions=[[-1.,0.]])
        np.testing.assert_equal(actual,[[-1.,0.]])
        self.assertIsNone(h.states[0].survey)
        self.assertFalse(h.states[0].actions)
        self.assertEqual(FakeClient.made,0)

    def test_policy_stop_at_survey_boundary_does_not_query_model(self):
        h=self.harness();self.trigger(h)
        for _ in range(3):self.step(h)
        self.step(h,actions=[[-1.,0.]])
        self.assertEqual(FakeClient.made,0)
        self.assertIsNone(h.states[0].survey)

    def test_reset_drops_old_view_snapshots(self):
        h=self.harness();self.trigger(h);self.step(h,30)
        self.assertIn('left',h.states[0].survey['views'])
        self.step(h,masks=[False],keys=[('next','0')])
        self.assertIsNone(h.states[0].survey)
        self.assertEqual(h.states[0].attempts,0)
        self.assertEqual(len(h.states[0].commands),0)

    def test_terminal_budget_does_not_complete_unexecuted_survey(self):
        h=self.harness();self.trigger(h);self.step(h)
        row=h.finish(0,('scene','0'))
        self.assertEqual(row['survey_steps'],2)
        self.assertEqual(row['completed_surveys'],0)
        self.assertEqual(FakeClient.made,0)

    def test_pause_while_surveying_preserves_remaining_environment(self):
        h=self.harness(n=2);self.trigger(h)
        s=h.states[1];h.pause([0]);self.step(h,30,keys=[('scene','1')])
        self.assertIs(h.states[0],s)
        self.assertEqual(s.survey['view_steps']['left'],5)
        self.assertEqual(s.key,('scene','1'))

    def test_cap_includes_survey_and_recovery(self):
        h=self.harness(mode='rule')
        for _ in range(100):self.step(h)
        s=h.states[0]
        self.assertEqual(s.attempts,2)
        self.assertEqual(s.overrides,12)
        self.assertEqual((s.survey_overrides,s.recovery_overrides),(8,4))
        self.assertEqual(s.selections,dict(A=1,B=1,C=0))
        self.assertEqual(h.max_override_steps,12)

    def test_zero_intervention_active_mode_is_exact_and_lazy(self):
        h=self.harness(max_interventions=0)
        for _ in range(20):
            np.testing.assert_allclose(self.step(h),[[.8,0.]])
        self.assertEqual(h.events,0)
        self.assertEqual(FakeClient.made,0)

    def test_invalid_survey_configuration(self):
        with self.assertRaises(ValueError):self.harness(survey_turn_steps=0)
        for k in [0,-1,1.5]:
            with self.assertRaises(ValueError):survey_actions(k)


if __name__=='__main__':unittest.main()
