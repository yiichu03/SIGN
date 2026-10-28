import base64
import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from qwen_topdown import prepare, verify, parse_response, run

class JudgeBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.ids = ['C%02d' % i for i in range(1, 9)]
        png = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jRZkAAAAASUVORK5CYII=')
        (self.root/'image.png').write_bytes(png);(self.root/'prompt.txt').write_text('test')
        task = dict(scene_id='s',episode_id='e',start_position=[0,0,0],start_rotation=[0,0,0,1],goal_sha256='g',policy_sha256='p')
        self.spec = {'group_id':'test', 'candidates':[dict(id=i,task=copy.deepcopy(task),steps=256,window_start_step=0,image='image.png') for i in self.ids]}
    def bundle(self, override=False):
        (self.root/'manifest.json').write_text(json.dumps(self.spec))
        return prepare(self.root/'manifest.json',self.root/'prompt.txt',self.root/'request',override)
    def response(self):
        return {'scores':[dict(id=i,score=.5) for i in self.ids]}
    def test_same_task_sealed_eight_image_request(self):
        bundle=self.bundle();r=verify(bundle)
        self.assertEqual(sum(c['type']=='image' for c in r['messages'][0]['content']),8)
        self.assertTrue(r['equal_steps'])
    def test_mixed_task_rejected(self):
        self.spec['candidates'][3]['task']['goal_sha256']='other'
        with self.assertRaises(ValueError):self.bundle()
    def test_budget_mismatch_explicit_diagnostic_only(self):
        self.spec['candidates'][2]['steps']=20
        with self.assertRaises(ValueError):self.bundle()
        r=verify(self.bundle(True));self.assertFalse(r['equal_steps']);self.assertFalse(r['reward_integration'])
    def test_continuation_window_rejected(self):
        self.spec['candidates'][0]['window_start_step']=256
        with self.assertRaises(ValueError):self.bundle()
    def test_tampered_image_rejected(self):
        b=self.bundle();(b/'images/C01.png').write_bytes(b'changed')
        with self.assertRaises(ValueError):verify(b)
    def test_duplicate_candidate_rejected(self):
        self.spec['candidates'][1]['id']='C01'
        with self.assertRaises(ValueError):self.bundle()
    def test_ties_and_unknown_preserved(self):
        r=self.response();r['scores'][0]['score']=None
        self.assertEqual(parse_response(json.dumps(r),self.ids),r)
    def test_invalid_scores_and_ids_rejected(self):
        for value in [True,1.2,-.1,'0.5',float('nan')]:
            r=self.response();r['scores'][0]['score']=value
            with self.assertRaises(ValueError):parse_response(json.dumps(r),self.ids)
        r=self.response();r['scores'][0]['id']='C02'
        with self.assertRaises(ValueError):parse_response(json.dumps(r),self.ids)
    def test_json_repair_is_not_silent(self):
        for raw in ['```json\n{}\n```','{"scores":[],"scores":[]}','{"x":NaN}']:
            with self.assertRaises(ValueError):parse_response(raw,self.ids)
    def test_truncation_rejected_even_valid_prefix(self):
        with self.assertRaises(ValueError):parse_response(json.dumps(self.response()),self.ids,truncated=True)
    def test_disabled_has_no_model_or_filesystem_dependency(self):
        self.assertEqual(run('/does/not/exist','/does/not/exist',{'enabled':False}),{'status':'disabled'})
        self.assertNotIn('transformers',sys.modules)

if __name__=='__main__':unittest.main()
