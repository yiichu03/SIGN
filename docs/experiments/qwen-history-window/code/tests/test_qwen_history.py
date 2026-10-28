import json
import sys
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'src'), str(ROOT/'scripts')]
from prepare_qwen_history import windows, area_stats, history_prompt
from qwen_single_image import conversations, validate_metadata


class HistoryTests(unittest.TestCase):
    def test_short_duplicate_requests_share_one_segment(self):
        result = windows(35)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0], dict(start=0, end=35, action_count=35,
            history_action_count=0, requested_windows=[128,256], short_for=[128,256]))

    def test_same_endpoint_true_history_and_no_history256(self):
        a, b = windows(256)
        self.assertEqual((a['start'], a['end'], a['action_count'], a['history_action_count']),
                         (128,256,128,128))
        self.assertEqual((b['start'], b['end'], b['history_action_count']), (0,256,0))
        self.assertEqual(b['short_for'], [])

    def test_longer_real_record_can_support_256_history(self):
        a, b = windows(400)
        self.assertEqual((a['end'], b['end']), (400,400))
        self.assertEqual((a['history_action_count'], b['history_action_count']), (272,144))
        for bad in [0,-1,True,1.5]:
            with self.assertRaises(ValueError):
                windows(bad)

    def test_new_area_excludes_all_prior_not_just_window_initial(self):
        valid = np.array([[1,1,1,1,0]], bool)
        prior = np.array([[1,1,1,0,0]], bool)
        final = np.array([[1,1,1,1,1]], bool)
        s = area_stats(prior, final, valid, .1, 128)
        self.assertAlmostEqual(s['new_area_m2'], .01)
        self.assertAlmostEqual(s['total_covered_area_m2'], .04)
        self.assertAlmostEqual(s['prior_seen_area_m2'], .03)
        self.assertAlmostEqual(s['new_area_m2_per_action'], .01/128)
        self.assertEqual(area_stats(final,final,valid,.1,128)['new_area_m2'], 0)
        with self.assertRaises(ValueError):
            area_stats(final,prior,valid,.1,128)

    def test_same_history_stats_reach_model_with_and_without_yellow(self):
        stats = dict(action_count=128, new_area_m2=2.,
                     prior_seen_area_m2=10., total_covered_area_m2=12.)
        rows = conversations(['history.png','hidden.png'],'history prompt',[stats,stats])
        texts = [r[0]['content'][-1]['text'] for r in rows]
        self.assertEqual(texts[0],texts[1])
        self.assertIn('"total_covered_area_m2": 12.0',texts[0])
        self.assertNotIn('hidden.png',str(rows[0]))
        for change in [dict(total_covered_area_m2=11), dict(prior_seen_area_m2=-1),
                       dict(total_covered_area_m2=float('nan'))]:
            with self.assertRaises(ValueError):
                validate_metadata(dict(stats,**change))

    def test_legacy_metadata_and_rubric_are_unchanged(self):
        prompt = (ROOT/'scripts/prompts/qwen_single_coverage_abc.txt').read_text()
        new = history_prompt(prompt)
        marker = '请独立判断三类质量：'
        self.assertEqual(prompt[prompt.index(marker):], new[new.index(marker):])
        self.assertIn('碰撞、受阻摆动和脱困不自动算重复搜索', new)
        stats = json.loads(conversations(['a.png'],'old',[dict(action_count=2,new_area_m2=1)])[0][0]['content'][-1]['text'].split(': ',1)[1])
        self.assertEqual(stats,dict(action_count=2,new_area_m2=1.,new_area_m2_per_action=.5))


if __name__ == '__main__':
    unittest.main()
