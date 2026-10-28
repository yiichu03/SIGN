import sys,unittest,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from qwen_single_image import conversations,parse_score
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
if __name__=='__main__':unittest.main()
