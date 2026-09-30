import sys,unittest
from pathlib import Path
from unittest.mock import Mock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from macro_sources import _month_rows,treasury_spread,bls_unrate
from macro_integrity import (source_compatible,missing_internal_months,merge_same_source,refetch_anchor)

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
    def test_old_fred_data_cannot_mix_with_treasury_proxy(self):
        prior={'source':'FRED','observations':[['2026-01',888]]}
        new={'source':'US_TREASURY_DIRECT','observations':[['2026-01',0.8]],'failed_years':[]}
        merged=merge_same_source('T10Y3M',prior,new,expected_first='2026-01')
        self.assertEqual(merged['observations'],[['2026-01',0.8]])
        self.assertTrue(merged['source_mismatch_old_cache_discarded'])
        self.assertIsNone(refetch_anchor('T10Y3M',prior))
    def test_compatible_macro_cache_merges_and_backfills_internal_gap(self):
        prior={'source':'US_BLS_DIRECT','observations':[['1948-01',3.4],['1948-03',3.7]]}
        self.assertEqual(refetch_anchor('UNRATE',prior),'1948-02')
        new={'source':'US_BLS_DIRECT','observations':[['1948-02',3.5]],'failed_years':[]}
        combined=merge_same_source('UNRATE',prior,new,expected_first='1948-01')
        self.assertEqual(combined['observations'],[['1948-01',3.4],['1948-02',3.5],['1948-03',3.7]])
        self.assertEqual(combined['missing_month_count'],0)
        self.assertEqual(combined['status'],'refreshed')
    def test_gap_detection_and_partial_status(self):
        new={'source':'US_BLS_DIRECT','observations':[['1948-01',3.1],['1948-04',4.1]],'failed_years':[]}
        result=merge_same_source('UNRATE',{},new,expected_first='1948-01')
        self.assertEqual(result['missing_month_count'],2)
        self.assertEqual(result['first_missing_month'],'1948-02')
        self.assertEqual(result['status'],'partial')
    def test_failed_bls_decade_recovers_two_short_chunks(self):
        import requests
        calls=[]
        def get(url,params,timeout):
            calls.append((params['startyear'],params['endyear']))
            if params['endyear']-params['startyear']>=9:raise requests.Timeout('failed whole decade')
            y=params['startyear']
            return Mock(json=lambda:{'status':'REQUEST_SUCCEEDED','Results':{'series':[{'data':[
                {'year':str(y),'period':'M01','value':'4.0'}]}]}})
        out=bls_unrate(Mock(get=get),last_month=None,first_year=2000,current_year=2009)
        self.assertEqual(calls,[(2000,2009),(2000,2004),(2005,2009)])
        self.assertEqual(len(out['observations']),2)
        self.assertEqual(out['completeness'],'full_requested_range')

if __name__=='__main__':unittest.main()
