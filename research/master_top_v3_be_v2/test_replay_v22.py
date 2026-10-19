import unittest
from replay_v22 import research_replay

def r(month, **kwargs):
    data=dict(month=month,data_status="OK",bubble_build=96,lev_memory=95,
              cape_pct=97,rollover=25,top_ratio=.98)
    data.update(kwargs)
    return data

class V22Regression(unittest.TestCase):
    def test_provisional_never_active(self):
        rows=[r("2025-01"),r("2025-02"),r("2025-03"),
              r("2025-04",data_status="PROVISIONAL_MONTH")]
        states,events=research_replay(rows)
        self.assertTrue(states[2]["v22_active_confirmation"])
        self.assertFalse(states[-1]["v22_active_confirmation"])
        self.assertFalse(states[-1]["v22_verified_month"])
    def test_reheat_downgrade(self):
        x=[r("2025-01"),r("2025-02"),r("2025-03"),
           r("2025-04",rollover=5),r("2025-05",rollover=5)]
        states,ev=research_replay(x)
        self.assertEqual(states[-1]["v22_display_state"],"ARMED_REHEATED")
        self.assertFalse(states[-1]["v22_active_confirmation"])
        self.assertEqual(len({e["episode_id"] for e in ev}),1)
    def test_missing_history_does_not_pit_certify(self):
        states,_=research_replay([r("2025-01"),r("2025-02",cape_pct="")])
        self.assertEqual(states[-1]["v22_display_state"],"UNVERIFIED_DATA")
        self.assertFalse(states[-1]["v22_publication_vintage_verified"])
if __name__=="__main__": unittest.main()
