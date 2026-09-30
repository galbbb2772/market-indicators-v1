import sys, unittest
from pathlib import Path
from unittest.mock import Mock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from macro_sources import _month_rows, treasury_spread, bls_unrate

class MacroSourcesTests(unittest.TestCase):
    def test_last_real_daily_monthly_sample(self):
        self.assertEqual(_month_rows([('2026-01-01',1),('2026-01-17',2),('2026-02-01',3)]),
                         [['2026-01',2.0],['2026-02',3.0]])
    def test_treasury_actual_csv_headers_and_provenance(self):
        r=Mock(headers={'Content-Type':'text/csv'},text='Date,"1 Mo","3 Mo","10 Yr"\n09/27/2026,3.1,3.5,4.1\n09/29/2026,3.2,3.6,4.2\n')
        out=treasury_spread(Mock(get=Mock(return_value=r)),last_month='2026-08',initial_year=2026,current_year=2026)
        self.assertEqual(out['observations'][-1],['2026-09',0.6])
        self.assertIn('proxy',out['definition'])
        self.assertFalse(out['point_in_time'])
    def test_bls_ignores_annual_m13(self):
        r=Mock(json=lambda:{'status':'REQUEST_SUCCEEDED','Results':{'series':[{'data':[
            {'year':'2026','period':'M01','value':'4.1'},
            {'year':'2026','period':'M13','value':'4.3'}]}]}})
        out=bls_unrate(Mock(get=Mock(return_value=r)),last_month='2026-01',first_year=2026,current_year=2026)
        self.assertEqual(out['observations'],[['2026-01',4.1]])
    def test_failed_treasury_year_is_explicitly_partial(self):
        import requests
        def fake_get(url,**kwargs):
            if '/2026/' in url:raise requests.Timeout('simulated outage')
            return Mock(headers={'Content-Type':'text/csv'},text='Date,"3 Mo","10 Yr"\n09/01/2025,3.5,4.0\n')
        out=treasury_spread(Mock(get=fake_get),last_month='2026-01',initial_year=2025,current_year=2026)
        self.assertEqual(out['observations'],[['2025-09',0.5]])
        self.assertEqual(out['completeness'],'partial_year_fetch')

if __name__=='__main__':unittest.main()
