"""Run: python -m unittest test_replay_v21.py"""
import unittest
from replay_v21 import replay, next_month

def make(n,start="2000-01",roll=0,build=95,memory=90,cape=95,status="OK"):
    result=[]
    for _ in range(n):
        result.append({"month":start,"data_status":status,"rollover":str(roll),
            "bubble_build":str(build),"lev_memory":str(memory),"cape_pct":str(cape),"top_ratio":"0.98"})
        start=next_month(start)
    return result

class StateTests(unittest.TestCase):
    def test_arm_confirm_reheat_reconfirm_reset(self):
        rows=make(2)+make(2,"2000-03",roll=30)+make(2,"2000-05",roll=5)
        rows+=make(1,"2000-07",roll=30)
        rows+=make(3,"2000-08",roll=40,build=50,memory=50,cape=50)
        out,ev=replay(rows)
        self.assertEqual([r["event"] for r in ev],
            ["ARM","CONFIRM","REHEAT_DOWNGRADE","RECONFIRM","RESET"])
        self.assertEqual(len(set(e["episode_id"] for e in ev)),1)
        self.assertEqual(out[-1]["state_v21"],"IDLE")
    def test_no_lookahead_partial_month(self):
        out,ev=replay(make(1)+make(1,"2000-02",status="PROVISIONAL_MONTH"))
        self.assertEqual(ev,[])
        self.assertEqual(out[-1]["state_v21"],"PROVISIONAL")
    def test_missing_data_pauses_streak(self):
        x=make(2);x[1]["cape_pct"]=""
        self.assertEqual(replay(x)[1],[])
    def test_gap_pauses_streak(self):
        self.assertEqual(replay(make(1)+make(1,"2000-03"))[1],[])
    def test_duplicates_rejected(self):
        with self.assertRaises(ValueError):
            replay(make(1)+make(1))

if __name__=="__main__":
    unittest.main()
