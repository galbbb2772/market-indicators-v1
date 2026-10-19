from __future__ import annotations
import json,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
PATH=ROOT/"research"/"market_top_route_a_ng3_evidence_protocol.json"

class NG3EvidenceProtocolTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.x=json.loads(PATH.read_text(encoding="utf-8"))

    def test_protocol_is_frozen_before_prospective_start(self):
        self.assertEqual(self.x["status"],"FROZEN_BEFORE_PROSPECTIVE_START")
        self.assertEqual(self.x["prospective_start_effective_month"],"202612")

    def test_episode_definition_is_contiguous_monthly_armed(self):
        e=self.x["episode_definition"]
        self.assertIn("consecutive",e["same_episode"])
        self.assertIn("IDLE",e["close"])
        self.assertTrue(e["overlapping_outcome_windows_allowed"])

    def test_outcome_horizons_and_classification_are_frozen(self):
        o=self.x["outcome_tracking"]
        self.assertEqual(o["horizons_sessions"],[63,126,252])
        self.assertIn("-15",o["final_252_classification"]["major_top"])
        self.assertIn("-7.5",o["final_252_classification"]["clear_false"])

    def test_completed_horizon_evidence_is_immutable(self):
        rule=self.x["outcome_tracking"]["completed_horizon_immutability"]
        self.assertIn("complete=true",rule)
        self.assertIn("frozen",rule)

    def test_no_automatic_promotion(self):
        p=self.x["promotion_review"]
        self.assertEqual(p["minimum_complete_252_session_episodes"],4)
        self.assertFalse(p["automatic_promotion"])
        self.assertIsNone(p["action_signal"])

if __name__=="__main__":
    unittest.main()
