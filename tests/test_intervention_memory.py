import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
import numpy as np
TREE = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(TREE), str(TREE/'src'), str(TREE/'scripts')]
from src.inference_recovery import RecoveryHarness, State
from src.recovery_gate import gate_request, current_shadow, validate_gate_request, select_gate, GATE_LABELS
from recovery_worker import agent_score
from test_inference_recovery import settings


class GateClient:
    rows = []
    choice = 'blocked'
    shadow = 'blocked'
    made = 0
    bad_id = False
    error = None
    def __init__(self, cfg, output):
        type(self).made += 1
    def score(self, request, rows):
        type(self).rows.extend(copy.deepcopy(rows))
        if self.error:raise RuntimeError(self.error)
        values = []
        for row in rows:
            word = self.shadow if ':without_history' in row['id'] else self.choice
            values.append(dict(id='wrong' if self.bad_id else row['id'], valid=True, candidate_mass=.99,
                probabilities=[.9 if x == word else .05 for x in GATE_LABELS]))
        return dict(results=values, seconds=.1)
    def close(self):pass


class InterventionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name);self.serial = 0
        self.rgb = np.random.RandomState(6).randint(0, 256, (64, 64, 3)).astype('uint8')
        GateClient.rows = [];GateClient.made = 0;GateClient.choice = GateClient.shadow = 'blocked'
        GateClient.bad_id = False;GateClient.error = None
    def harness(self, n=1, **changes):
        self.serial += 1
        cfg = dict(mode='rule', agent_variant='legacy', active_survey=True, survey_turn_steps=6,
            turn_steps=6, forward_steps=8, window=16, cooldown=64, candidate_affordance=True,
            candidate_protocol='agent', intervention_gate='history', gate_shadow=True)
        cfg.update(changes)
        return RecoveryHarness(settings(**cfg), n, self.root/str(self.serial), GateClient)
    def step(self, h, action=(.8, 0), reset=False, keys=None, rgb=None):
        n = len(h.states);mask = np.array([not reset]*n);original = mask.copy()
        actions = np.tile(np.asarray(action, dtype=np.float32), (n, 1))
        out = h.step([self.rgb if rgb is None else rgb]*n, [self.rgb]*n, actions, mask,
            keys or [('scene', str(i)) for i in range(n)])
        np.testing.assert_equal(mask, original)
        for i in range(n):np.testing.assert_equal(h.states[i].last_action, out[i])
        return out
    def records(self, h, name):
        f = h.output/name
        return [json.loads(x) for x in f.read_text().splitlines()] if f.exists() else []
    def test_history_exact_steps_actions_and_independent_images(self):
        h = self.harness()
        for _ in range(17):self.step(h)
        r = GateClient.rows[0];validate_gate_request(r);c = json.loads(r['context'])
        self.assertEqual(c['image_steps'], [0,5,11,16]);self.assertEqual(len(c['actual_executed_actions']),16)
        self.assertEqual([x['step'] for x in c['actual_executed_actions']],list(range(16)))
        for im in r['images']:self.assertEqual(hashlib.sha256(Path(im['image']).read_bytes()).hexdigest(),im['image_sha256'])
        self.assertNotIn('goal',r['context']);self.assertNotIn('evidence',r['context']);self.assertNotIn('collision',r['context'])
    def test_current_and_history_identical_action_metadata(self):
        h = self.harness()
        for _ in range(17):self.step(h)
        r, shadow = GateClient.rows
        self.assertEqual(shadow,current_shadow(r))
        left, right = map(lambda x:json.loads(x['context']), (r,shadow))
        left.pop('image_steps');right.pop('image_steps');self.assertEqual(left,right)
        self.assertEqual(shadow['images'],r['images'][-1:])
    def test_current_mode_sends_one_image_and_no_shadow(self):
        h = self.harness(intervention_gate='current')
        for _ in range(17):self.step(h)
        self.assertEqual(len(GateClient.rows),1);self.assertEqual(len(GateClient.rows[0]['images']),1)
        validate_gate_request(GateClient.rows[0])
    def test_progress_veto_before_any_scan_and_consumes_budget(self):
        GateClient.choice='progress';h=self.harness()
        for _ in range(200):np.testing.assert_equal(self.step(h),np.array([[.8,0]],np.float32))
        s=h.states[0];self.assertEqual(s.attempts,2);self.assertEqual(s.overrides,0)
        self.assertEqual(s.gate_vetoes,2);self.assertEqual(s.gate_history_changes,2)
        self.assertEqual([x['step'] for x in self.records(h,'gate_events.jsonl')],[16,80])
        self.assertFalse(self.records(h,'surveys.jsonl'))
    def test_blocked_and_unknown_preserve_rule_actions_exactly(self):
        for word in ('blocked','unknown'):
            GateClient.choice=word;gate=self.harness();rule=self.harness(intervention_gate='disabled')
            for _ in range(200):np.testing.assert_equal(self.step(gate),self.step(rule))
            self.assertEqual(gate.states[0].action_digest.hexdigest(),rule.states[0].action_digest.hexdigest())
            self.assertEqual(gate.states[0].overrides,76)
    def test_shadow_never_changes_executed_decision(self):
        GateClient.choice='blocked';GateClient.shadow='progress';h=self.harness()
        for _ in range(17):out=self.step(h)
        np.testing.assert_equal(out,[[-1,1]]);self.assertEqual(h.states[0].gate_history_changes,1)
    def test_fixed_left_including_second_recovery_no_worker(self):
        h=self.harness(intervention_gate='disabled',fixed_recovery_choice='left')
        for _ in range(200):self.step(h)
        self.assertEqual([r['choice'] for r in self.records(h,'events.jsonl')],['A','A'])
        self.assertEqual(h.states[0].overrides,76);self.assertEqual(GateClient.made,0)
    def test_scan_only_keeps_actual_scan_and_no_forward_or_worker(self):
        h=self.harness(mode='scan',intervention_gate='disabled')
        for _ in range(200):self.step(h)
        s=h.states[0];self.assertEqual(s.survey_overrides,48);self.assertEqual(s.recovery_overrides,0)
        self.assertEqual([r['choice'] for r in self.records(h,'events.jsonl')],['C','C'])
        self.assertEqual(GateClient.made,0)
    def test_stop_precedes_gate_and_mid_scan_cancels(self):
        h=self.harness()
        for _ in range(16):self.step(h)
        np.testing.assert_equal(self.step(h,action=(-1,0)),[[-1,0]])
        self.assertEqual(GateClient.made,0)
        h=self.harness()
        for _ in range(17):self.step(h)
        calls=len(GateClient.rows);np.testing.assert_equal(self.step(h,action=(-1,0)),[[-1,0]])
        self.assertIsNone(h.states[0].survey);self.assertFalse(h.states[0].actions)
        self.assertEqual(calls,len(GateClient.rows))
    def test_reset_and_pause_do_not_mix_environments(self):
        h=self.harness(n=2)
        for _ in range(17):self.step(h)
        self.assertEqual(len({r['id'] for r in GateClient.rows}),4)
        h.pause([0]);self.step(h,reset=True,keys=[('new','2')])
        s=h.states[0];self.assertEqual(s.attempts,0);self.assertEqual(s.gate_calls,0)
        self.assertEqual(len(s.images),1);self.assertEqual(len(s.commands),0)
    def test_zero_budget_no_worker_and_exact_actions(self):
        h=self.harness(max_interventions=0)
        for _ in range(60):np.testing.assert_equal(self.step(h),np.array([[.8,0]],np.float32))
        self.assertEqual(GateClient.made,0)
    def test_blank_evidence_preserves_rule_without_calling_model(self):
        h=self.harness()
        for _ in range(17):out=self.step(h,rgb=np.zeros_like(self.rgb))
        np.testing.assert_equal(out,[[-1,1]]);self.assertEqual(GateClient.made,0)
        r=self.records(h,'gate_events.jsonl')[0];self.assertEqual(r['gate_reason'],'invalid_model_evidence')
    def test_id_mismatch_is_fatal(self):
        GateClient.bad_id=True;h=self.harness()
        for _ in range(16):self.step(h)
        with self.assertRaisesRegex(RuntimeError,'mismatch'):self.step(h)
    def test_worker_failure_records_technical_error(self):
        GateClient.error='test worker timeout';h=self.harness()
        for _ in range(17):out=self.step(h)
        np.testing.assert_equal(out,[[-1,1]]);self.assertEqual(h.technical_errors,1)
        self.assertTrue(self.records(h,'technical_errors.jsonl'))
    def test_probability_integrity_no_extra_confidence_threshold(self):
        self.assertEqual(select_gate(dict(probabilities=[.34,.33,.33],candidate_mass=.8)),('progress','model_argmax'))
        for value in [None,{},dict(probabilities=[.5,.5,0],candidate_mass=.9),dict(probabilities=[1,0,0],candidate_mass=.09),
                dict(probabilities=[float('nan'),0,1],candidate_mass=.9)]:self.assertEqual(select_gate(value)[0],'unknown')
    def test_request_roles_time_and_command_binding_checked(self):
        h=self.harness()
        for _ in range(17):self.step(h)
        original=GateClient.rows[0]
        for change in ('roles','times','commands'):
            r=copy.deepcopy(original);c=json.loads(r['context'])
            if change=='roles':r['images'].reverse()
            elif change=='times':c['image_steps'][0]+=1
            else:c['actual_executed_actions'][0]['commanded_angular_velocity_deg_s']=99
            r['context']=json.dumps(c)
            with self.assertRaises(RuntimeError):validate_gate_request(r)
    def test_worker_batches_current_and_history_independently(self):
        h=self.harness()
        for _ in range(17):self.step(h)
        requests=GateClient.rows
        class Judge:
            prompt=''
            def choice_probabilities(self,rows,labels):
                return [dict(valid=True,probabilities=[.8,.1,.1] if len(r['images'])==4 else [.1,.1,.8],
                    logits=[1.,0.,0.],candidate_mass=.99,labels=list(labels)) for r in rows],{}
        results=agent_score(Judge(),requests,{'intervention_gate':'same prompt'},self.root,0,set(),False)
        self.assertEqual([r['id'] for r in results],[r['id'] for r in requests])
        self.assertEqual([select_gate(v)[0] for v in results],['progress','unknown'])
        self.assertEqual(results[0]['prompt_version'],results[1]['prompt_version'])


if __name__=='__main__':unittest.main()
