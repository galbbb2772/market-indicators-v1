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
        self.assertEqual(self.x["status"],"FROZEN_BEFORE_PROSPECTIVE_START_SUPERSEDES_V1")
        self.assertEqual(self.x["schema_version"],"market-top-route-a-ng3-evidence-protocol-2")
        self.assertEqual(self.x["supersedes"],"market-top-route-a-ng3-evidence-protocol-1")
        self.assertEqual(self.x["prospective_start_effective_month"],"202612")

    def test_episode_definition_is_contiguous_monthly_armed(self):
        e=self.x["episode_definition"]
        self.assertIn("consecutive",e["same_episode"])
        self.assertIn("IDLE",e["close"])
        self.assertTrue(e["overlapping_outcome_windows_allowed"])
        self.assertIn("one episode",e["missing_month_bridge"])
        self.assertIn("may not be used as evidence",e["missing_month_conservative_bias"])

    def test_outcome_horizons_and_classification_are_frozen(self):
        o=self.x["outcome_tracking"]
        self.assertEqual(o["horizons_sessions"],[63,126,252])
        self.assertIn("-15",o["final_252_classification"]["major_top"])
        self.assertIn("-7.5",o["final_252_classification"]["clear_false"])

    def test_monthly_prospective_signal_is_first_successful_snapshot_locked(self):
        x=self.x["monthly_signal_immutability"]
        self.assertIn("first successful snapshot",x["lock_rule"])
        self.assertIn("must not overwrite",x["later_revisions"])
        self.assertIn("no monthly snapshot is frozen",x["failure_behavior"])

    def test_prospective_source_bytes_must_be_fingerprinted(self):
        p=self.x["source_provenance"]
        self.assertIn("SHA-256",p["snapshot_requirement"])
        self.assertIn("source_provenance_at_start",p["episode_start_requirement"])

    def test_completed_horizon_evidence_is_immutable(self):
        rule=self.x["outcome_tracking"]["completed_horizon_immutability"]
        self.assertIn("complete=true",rule)
        self.assertIn("frozen",rule)

    def test_no_automatic_promotion(self):
        p=self.x["promotion_review"]
        self.assertEqual(p["minimum_complete_252_session_episodes"],4)
        self.assertEqual(p["minimum_complete_252_session_episodes_without_continuity_gaps"],4)
        self.assertIn("excluded",p["continuity_gap_rule"])
        self.assertFalse(p["automatic_promotion"])
        self.assertIsNone(p["action_signal"])

if __name__=="__main__":
    unittest.main()
