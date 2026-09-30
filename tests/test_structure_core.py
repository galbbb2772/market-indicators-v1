import math
import sys
import unittest
from datetime import date, timedelta
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from structure_core import (validate_bars, detect_boxes, numbered_boxes, box_scores,
                            sector_activity, sector_activity_history, news_tension,
                            updown_stats, nonoverlap_forward_rates)


def make_bars(n=450, break_at=None):
    bars=[]
    for i in range(n):
        p=100+3.5*math.sin(i*math.pi/5)
        if break_at is not None and i>=break_at:
            p=145+3.5*math.sin(i*.2)
        d=(date(2020,1,1)+timedelta(days=i)).isoformat()
        bars.append([d,p,p+1,p-1,p,100000+i*100])
    return bars


class StructureTests(unittest.TestCase):
    def test_sanitization_and_sorted(self):
        b=make_bars(3)
        out=validate_bars([b[2],b[0],b[1],b[1]])
        self.assertEqual(len(out),3)
        self.assertEqual(out[0][0],b[0][0])

    def test_online_box_prefix_invariance(self):
        b=make_bars(170,break_at=120)
        a=detect_boxes(b[:100],20,.14)
        later=detect_boxes(b,20,.14)
        self.assertTrue(a)
        self.assertEqual(a[0]['detected_at'],later[0]['detected_at'])
        self.assertEqual(a[0]['upper'],later[0]['upper'])
        self.assertTrue(later[0]['end_at'])
        self.assertGreater(later[0]['break_at'],later[0]['detected_at'])
        self.assertTrue(numbered_boxes('TEST',b)[0]['next_session_only'])

    def test_no_future_data_when_detected(self):
        b=make_bars(80)
        earlier=detect_boxes(b,20,.14)
        modified=detect_boxes(b+make_bars(30,break_at=0)[20:],20,.14)
        self.assertEqual(earlier[0]['detected_at'],modified[0]['detected_at'])

    def test_monotonic_drift_filter(self):
        b=[]
        for i in range(70):
            p=110-i*.5
            b.append([(date(2020,1,1)+timedelta(days=i)).isoformat(),p,p+.2,p-.2,p,1000])
        self.assertEqual(detect_boxes(b,20,.14),[])

    def test_scores_bounded(self):
        s=box_scores(make_bars(100),0,40,95,105)
        self.assertTrue(all(0<=v<=10 for v in s.values()))

    def test_activity_is_not_news_attention(self):
        b=make_bars(120)
        a=sector_activity(b)
        self.assertEqual(a['status'],'ok')
        self.assertIsNone(a['news_attention'])
        self.assertEqual(len(sector_activity_history(b)),60)
        self.assertTrue(0<=a['activity']<=100)

    def test_recorded_news_only(self):
        b=make_bars(6)
        keys=('us_policy_event_sentiment','geopolitical_news_risk',
              'systemic_news_risk','ai_narrative_risk','negative_narrative_density')
        src={'history':[{'date':b[-1][0],
                         'reaction_adjusted':{k:20 for k in keys}}]}
        out=news_tension(src,{'sp500':b})
        self.assertEqual(len(out),1)
        self.assertEqual(out[0]['tension'],20)
        self.assertIn('sp500',out[0]['index_returns'])

    def test_forward_cutoff(self):
        b=make_bars(450)
        earlier=nonoverlap_forward_rates(b,b[300][0],20)
        later=nonoverlap_forward_rates(b,b[350][0],20)
        self.assertLessEqual(earlier['n'],later['n'])
        self.assertLessEqual(earlier['n'],6)

    def test_daily_return_descriptive(self):
        s=updown_stats(make_bars(100))
        self.assertEqual(s['n'],99)
        self.assertIsNotNone(s['up_median_pct'])
        self.assertIsNotNone(s['down_median_pct'])


if __name__ == '__main__':
    unittest.main()
