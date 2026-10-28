import sys,unittest,json,math,tempfile,copy
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from qwen_single_image import (conversations,parse_score,validate_metadata,
    probabilities_from_logits,response_positions,load_manifest)
class SingleImageTests(unittest.TestCase):
 def test_independent_batch_rows(self):
  rows=conversations(['a.png','b.png'],'judge this image')
  self.assertEqual(len(rows),2)
  for row,name in zip(rows,['a.png','b.png']):
   self.assertEqual(len(row),1);content=row[0]['content'];self.assertEqual(len(content),2)
   self.assertTrue(content[1]['image'].endswith(name));self.assertEqual(content[0]['text'],'judge this image')
 def test_single_allowed(self):self.assertEqual(len(conversations(['a.png'],'p')),1)
 def test_ties_and_unknown_not_relative(self):
  self.assertEqual(parse_score('{"score":null}'),{'score':None});self.assertEqual(parse_score('{"score":0.5}'),{'score':.5})
 def test_invalid_scores(self):
  for x in [True,-1,1.1,'0.5',float('nan')]:
   with self.assertRaises(ValueError):parse_score(json.dumps({'score':x}))
 def test_bad_json_and_truncation(self):
  for s in ['```json\n{"score":0.5}\n```','{"score":0.1,"score":0.3}','{"scores":[1,2]}']:
   with self.assertRaises(ValueError):parse_score(s)
  with self.assertRaises(ValueError):parse_score('{"score":0.5}',True)
 def test_probability_formula(self):
  p=probabilities_from_logits([math.log(1),math.log(2),math.log(3)])
  self.assertAlmostEqual(p['p_low'],1/6);self.assertAlmostEqual(p['p_medium'],2/6)
  self.assertAlmostEqual(p['p_high'],3/6);self.assertAlmostEqual(p['q'],2/3)
  self.assertAlmostEqual(sum(p[k] for k in ('p_low','p_medium','p_high')),1)
 def test_probability_stability_and_endpoints(self):
  for logits,expected in [([1000,0,0],0),([0,1000,0],.5),([0,0,1000],1),([0,0,0],.5)]:
   self.assertAlmostEqual(probabilities_from_logits(logits)['q'],expected)
 def test_invalid_logits(self):
  for values in [[0,1],[0,1,float('nan')],[float('inf'),0,0],[True,0,0],['1',0,0]]:
   with self.assertRaises(ValueError):probabilities_from_logits(values)
 def test_actual_answer_position_with_left_padding(self):
  self.assertEqual(response_positions([[0,0,1,1],[1,1,1,1]]),[3,3])
  for mask in [[1,1,0],[0,0,0],[],[0,1,0,1],[1,2,1]]:
   with self.assertRaises(ValueError):response_positions([mask])
 def test_metadata_ratio_computed_and_checked(self):
  source={'action_count':20,'new_area_m2':5}
  self.assertEqual(validate_metadata(source)['new_area_m2_per_action'],.25)
  self.assertNotIn('new_area_m2_per_action',source)
  with self.assertRaises(ValueError):validate_metadata(dict(source,new_area_m2_per_action=.5))
 def test_no_area_inference_from_percentages(self):
  with self.assertRaises(ValueError):validate_metadata({'action_count':10,'covered_percent':50})
 def test_bad_metadata(self):
  for count in [0,-1,True,1.5]:
   with self.assertRaises(ValueError):validate_metadata({'action_count':count,'new_area_m2':1})
  for area in [-1,True,float('nan'),float('inf'),'1']:
   with self.assertRaises(ValueError):validate_metadata({'action_count':10,'new_area_m2':area})
 def test_batch_metadata_stays_with_image(self):
  metadata=[{'image':'a.png','action_count':10,'new_area_m2':2},
            {'image':'b.png','action_count':20,'new_area_m2':9}]
  rows=conversations(['a.png','b.png'],'classify',metadata)
  for row,item in zip(rows,metadata):
   stats=json.loads(row[0]['content'][-1]['text'].split(': ',1)[1])
   self.assertEqual(stats['new_area_m2'],item['new_area_m2'])
   self.assertEqual(stats['action_count'],item['action_count'])
  with self.assertRaises(ValueError):conversations(['a.png','b.png'],'p',metadata[::-1])
  with self.assertRaises(ValueError):conversations(['a.png'],'p',metadata)
 def test_manifest_two_groups_and_missing_files(self):
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp);(root/'image.png').write_bytes(b'png')
   spec={'groups':[{'id':str(g),'items':[{'id':str(i),'image':'image.png','action_count':i+1,'new_area_m2':2} for i in range(8)]} for g in range(2)]}
   path=root/'manifest.json';path.write_text(json.dumps(spec));_,rows=load_manifest(path)
   self.assertEqual(len(rows),16);self.assertEqual([r['group_id'] for r in rows],['0']*8+['1']*8)
   bad=copy.deepcopy(spec);bad['groups'][0]['items'][1]['id']='0';path.write_text(json.dumps(bad))
   with self.assertRaises(ValueError):load_manifest(path)
   path.write_text(json.dumps(spec));(root/'image.png').unlink()
   with self.assertRaises(FileNotFoundError):load_manifest(path)
if __name__=='__main__':unittest.main()
