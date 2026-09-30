"""Offline tests: latest-first BLS, adaptive repair, and documented structural absence."""
import sys,unittest
from pathlib import Path
from unittest.mock import Mock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from macro_sources import bls_unrate
from macro_integrity import merge_same_source,refetch_anchor


def response(rows):
    data=[{'year':str(int(month[:4])),'period':'M'+month[5:7],'value':str(value)}
          for month,value in rows]
    return Mock(json=lambda:{'status':'REQUEST_SUCCEEDED','Results':{'series':[{'data':data}]}})


class BLSRecentBackfillTests(unittest.TestCase):
    def test_recent_is_requested_before_1948_archive(self):
        calls=[]
        def get(url,params,timeout):
            y,z=params['startyear'],params['endyear'];calls.append((y,z))
            if (y,z)==(2023,2026):return response([('2023-01',3.4),('2026-08',4.2)])
            return response([(f'{y}-01',4)])
        r=bls_unrate(Mock(get=get),first_year=1948,current_year=2026)
        self.assertEqual(calls[0],(2023,2026))
        self.assertEqual(calls[1],(1948,1957))
        self.assertIn(['2026-08',4.2],r['observations'])
        self.assertEqual(r['source'],'US_BLS_DIRECT')
        self.assertEqual(r['completeness'],'partial_month_coverage')
        self.assertLessEqual(r['request_count'],23)

    def test_recent_segment_split_recovers_newest_month(self):
        import requests
        calls=[]
        def get(url,params,timeout):
            y,z=params['startyear'],params['endyear'];calls.append((y,z))
            if (y,z)==(2023,2026):raise requests.Timeout('simulated timeout')
            if (y,z)==(2025,2026):return response([('2026-08',4.3)])
            return response([(f'{y}-01',4.1)])
        r=bls_unrate(Mock(get=get),first_year=2023,current_year=2026)
        self.assertEqual(calls[:3],[(2023,2026),(2023,2024),(2025,2026)])
        self.assertIn(['2026-08',4.3],r['observations'])
        self.assertTrue(r['request_errors'])
        self.assertEqual(r['completeness'],'partial_month_coverage')

    def test_complete_recent_with_official_absence_is_complete(self):
        months=[(f'{y:04d}-{mo:02d}',4.0) for y in (2025,2026)
                for mo in range(1,13) if (y==2025 or mo<=8)
                and (y,mo)!=(2025,10)]
        calls=[]
        def get(url,params,timeout):
            y,z=params['startyear'],params['endyear'];calls.append((y,z))
            return response([(month,value) for month,value in months if y<=int(month[:4])<=z])
        r=bls_unrate(Mock(get=get),last_month='2026-01',first_year=2025,current_year=2026)
        self.assertEqual(r['completeness'],'full_expected_month_coverage')
        self.assertEqual(r['observations'][-1][0],'2026-08')
        self.assertEqual(r['missing_requested_month_count'],0)
        self.assertEqual(r['official_unavailable_months'],['2025-10'])
        self.assertNotIn('2025-10',[month for month,_ in r['observations']])
        self.assertEqual(calls,[(2025,2026)])

    def test_source_safe_cache_knows_structural_absence(self):
        source={'source':'US_BLS_DIRECT','observations':[['2025-09',4.4],['2025-11',4.6]],
                'failed_years':[]}
        combined=merge_same_source('UNRATE',{},source,expected_first='2025-09')
        self.assertEqual(combined['status'],'refreshed')
        self.assertEqual(combined['missing_month_count'],0)
        self.assertEqual(combined['official_unavailable_months'],['2025-10'])
        self.assertEqual(refetch_anchor('UNRATE',combined),'2025-11')

if __name__=='__main__':unittest.main()
