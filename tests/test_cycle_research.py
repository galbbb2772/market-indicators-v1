import sys,unittest
from pathlib import Path
from datetime import date,timedelta
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from cycle_research import pearson_lag,weekly_sector_relative,walkforward_up_probability,cycle_report,_prior_state

class CycleTests(unittest.TestCase):
    def bars(self,n,drift=.0003):
        d=date(2000,1,3);rows=[];price=100.0
        for i in range(n):
            price*=1+drift+.004*((i%11)-5)/5
            rows.append([(d+timedelta(days=i)).isoformat(),price,price*1.005,price*.995,price,1000])
        return rows
    def test_weekly_windows_do_not_overlap(self):
        a=self.bars(27);b=self.bars(27,drift=.0004)
        out=weekly_sector_relative(a,b)
        self.assertEqual(len(out),5)
        self.assertEqual(out[0][0],a[5][0])
        self.assertEqual(out[1][0],a[10][0])
    def test_autocorrelation_refuses_short_history(self):
        self.assertIsNone(pearson_lag([float(i) for i in range(18)],13))
    def test_no_unfinished_forward_outcomes(self):
        a=self.bars(230)
        r=walkforward_up_probability(a,20)
        self.assertEqual(r['status'],'insufficient_oos_samples')
        self.assertEqual(r['n'],0)
    def test_past_state_is_prefix_invariant(self):
        a=self.bars(250)
        x=[r[4] for r in a]
        self.assertEqual(_prior_state(x,225),_prior_state(x+[1e6]*100,225))
    def test_walkforward_requires_observed_training(self):
        a=self.bars(540)
        f=walkforward_up_probability(a,5)
        self.assertIn(f['status'],('insufficient_oos_samples','exploratory_walkforward_not_a_live_forecast'))
        self.assertTrue(f['n']>=0)
    def test_sparse_news_never_claims_periodicity(self):
        a=self.bars(540)
        report=cycle_report({'SPY':{'bars':a,'boxes':[]},'XLK':{'group':'sector','bars':a}},[])
        self.assertEqual(report['news_status'],'insufficient_for_cycle_tests')
        self.assertIs(report['cycle_proof'],False)

if __name__=='__main__':unittest.main()
