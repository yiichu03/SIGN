import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'src'))
from inference_recovery import RecoveryHarness, physical, is_stop, recovery_actions, choose, thumbnail


def settings(**kwargs):
    value = dict(mode='rule', window=4, min_forward_fraction=.75, median_change_threshold=.01,
        endpoint_change_threshold=.025, cooldown=6, max_interventions=2, turn_steps=2,
        forward_steps=2, min_probability=.5, min_margin=.1)
    value.update(kwargs)
    return SimpleNamespace(**value)


class FakeClient:
    probabilities = [.8, .1, .1]
    bad_id = False
    made = 0
    def __init__(self, cfg, output):
        type(self).made += 1
    def score(self, request, rows):
        return dict(seconds=.1, results=[dict(id='wrong' if self.bad_id else r['id'], probabilities=self.probabilities,
            logits=[1., 0., 0.]) for r in rows])
    def close(self):
        pass


class RecoveryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.counter = 0
        self.frame = np.full((64, 64, 3), 90, dtype=np.uint8)
        FakeClient.made = 0
        FakeClient.bad_id = False
        FakeClient.probabilities = [.8, .1, .1]

    def harness(self, n=1, **opts):
        self.counter += 1
        return RecoveryHarness(settings(**opts), n, self.root/str(self.counter), FakeClient)

    def step(self, h, rgb=None, actions=None, masks=None, keys=None):
        n = len(h.states)
        return h.step([self.frame]*n if rgb is None else rgb, [self.frame]*n,
            np.asarray([[.8, 0.]]*n if actions is None else actions, dtype=np.float32),
            np.ones(n, dtype=bool) if masks is None else masks,
            [('scene', str(i)) for i in range(n)] if keys is None else keys)

    def warm(self, h, steps=5):
        return [self.step(h) for _ in range(steps)]

    def test_action_scaling_and_stop(self):
        self.assertEqual(physical([0, 0]), (.125, 0))
        self.assertFalse(is_stop([0, 0]))
        self.assertTrue(is_stop([-1, 0]))
        for side in ['A', 'B']:
            actions = recovery_actions(side, 6, 4)
            self.assertEqual(len(actions), 10)
            self.assertTrue(all(not is_stop(a) for a in actions))
            self.assertTrue(all(physical(a)[0] >= 0 for a in actions))
            self.assertEqual(physical(actions[0])[1], 15 if side == 'A' else -15)

    def test_stagnation_triggers_only_after_full_action_window(self):
        h = self.harness()
        result = self.warm(h, 4)
        self.assertEqual(h.events, 0)
        actual = self.step(h)
        self.assertEqual(h.events, 1)
        np.testing.assert_equal(actual, [[-1., 1.]])
        self.assertEqual(h.states[0].attempts, 1)

    def test_stationary_turning_does_not_trigger(self):
        h = self.harness()
        for _ in range(20):
            self.step(h, actions=[[-1., 1.]])
        self.assertEqual(h.events, 0)

    def test_visual_progress_does_not_trigger(self):
        h = self.harness()
        for i in range(20):
            self.step(h, rgb=[np.full_like(self.frame, (i*25)%255)])
        self.assertEqual(h.events, 0)

    def test_policy_stop_is_never_overridden(self):
        h = self.harness();self.warm(h)
        actual = self.step(h, actions=[[-1., 0.]])
        np.testing.assert_equal(actual, [[-1., 0.]])
        self.assertEqual(len(h.states[0].actions), 0)

    def test_true_reset_clears_all_history_and_actions(self):
        h = self.harness();self.warm(h)
        actual = self.step(h, masks=[False], keys=[('new', '0')])
        np.testing.assert_allclose(actual, [[.8, 0.]])
        self.assertEqual(h.states[0].attempts, 0)
        self.assertEqual(len(h.states[0].commands), 0)
        self.assertEqual(h.states[0].step, 1)

    def test_episode_change_without_mask_fails(self):
        h = self.harness();self.step(h)
        with self.assertRaisesRegex(RuntimeError, 'reset'):
            self.step(h, keys=[('other', '0')])

    def test_zero_interventions_is_exact_and_never_loads_worker(self):
        h = self.harness(mode='qwen', max_interventions=0)
        original = np.array([[1.3, -.12]], dtype=np.float32)
        masks = np.array([True])
        for _ in range(40):
            actual = self.step(h, actions=original, masks=masks)
            np.testing.assert_equal(actual, original)
            np.testing.assert_equal(masks, [True])
        self.assertEqual(FakeClient.made, 0)

    def test_per_environment_independence(self):
        h = self.harness(n=2)
        for i in range(5):
            self.step(h, rgb=[self.frame, np.full_like(self.frame, i*30)])
        self.assertEqual(h.states[0].attempts, 1)
        self.assertEqual(h.states[1].attempts, 0)

    def test_pause_preserves_matching_remaining_state(self):
        h = self.harness(n=3);self.step(h)
        saved = h.states[2]
        h.pause([1, 0])
        self.assertEqual(h.states, [saved])
        self.step(h, keys=[('scene', '2')])
        self.assertEqual(saved.step, 2)

    def test_cooldown_cap_and_fixed_recovery_budget(self):
        h = self.harness();self.warm(h)
        for _ in range(100):
            self.step(h)
        state = h.states[0]
        self.assertEqual(state.attempts, 2)
        self.assertEqual(state.overrides, 8)
        rows = [json.loads(s) for s in (h.output/'events.jsonl').read_text().splitlines()]
        self.assertEqual([r['choice'] for r in rows], ['A', 'B'])
        self.assertGreaterEqual(rows[1]['step']-rows[0]['step'], 10)
        self.assertTrue((h.output/'outcomes.jsonl').exists())

    def test_worker_loaded_once_for_multiple_events(self):
        h = self.harness(mode='qwen')
        for _ in range(60):self.step(h)
        self.assertEqual(FakeClient.made, 1)
        self.assertEqual(h.states[0].attempts, 2)

    def test_worker_ids_must_match(self):
        h = self.harness(mode='qwen');FakeClient.bad_id=True
        with self.assertRaisesRegex(RuntimeError, 'ID/order'):
            self.warm(h)

    def test_ambiguous_model_response_rejects_intervention(self):
        h = self.harness(mode='qwen');FakeClient.probabilities=[.4, .35, .25]
        actual = self.warm(h)[-1]
        np.testing.assert_allclose(actual, [[.8, 0.]])
        self.assertEqual(h.states[0].rejected, 1)

    def test_model_choice_and_invalid_probabilities(self):
        self.assertEqual(choose([.05,.9,.05]), 'B')
        self.assertEqual(choose([.1,.1,.8]), 'C')
        for p in [[1.,1.,0.], [float('nan'),0,1],[-.1,.2,.9], [1,0]]:
            with self.assertRaises(ValueError):choose(p)

    def test_finish_once_and_real_reset_before_next_episode(self):
        h = self.harness();self.step(h)
        self.assertEqual(h.finish(0, ('scene','0'))['steps'], 1)
        with self.assertRaises(RuntimeError):h.finish(0, ('scene','0'))
        with self.assertRaises(RuntimeError):self.step(h)
        self.step(h, masks=[False])
        self.assertFalse(h.states[0].finished)

    def test_invalid_inputs_fail_without_silent_nan(self):
        for a in [[float('nan'), 0], [0,0,0]]:
            with self.assertRaises(ValueError):physical(a)
        with self.assertRaises(ValueError):thumbnail(np.zeros((2,2,3)))
        with self.assertRaises(ValueError):self.harness(window=0)
        h = self.harness()
        with self.assertRaises(ValueError):self.step(h, masks=[2])

    def test_gym_angular_first_mapping_and_executed_feedback(self):
        h = RecoveryHarness(settings(), 1, self.root/'angular_first', FakeClient,
            action_names=['angular_velocity','linear_velocity'])
        for _ in range(5):
            result = self.step(h, actions=[[0., .8]])
        np.testing.assert_equal(result, [[1., -1.]])
        np.testing.assert_equal(h.states[0].last_action, [-1., 1.])
        self.assertEqual(h.states[0].attempts, 1)

    def test_angular_first_zero_intervention_roundtrip_is_exact(self):
        h = RecoveryHarness(settings(max_interventions=0), 1, self.root/'angular_zero', FakeClient,
            action_names=['angular_velocity','linear_velocity'])
        action = np.array([[-.31, 1.4]], dtype=np.float32)
        for _ in range(12):np.testing.assert_array_equal(self.step(h, actions=action), action)


if __name__ == '__main__':
    unittest.main()
