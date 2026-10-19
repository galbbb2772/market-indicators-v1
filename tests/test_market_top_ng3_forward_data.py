from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
CURRENT=ROOT/"docs"/"data"/"market_top_ng3_current.json"
HISTORY=ROOT/"docs"/"data"/"market_top_ng3_history.json"
EPISODES=ROOT/"docs"/"data"/"market_top_ng3_episodes.json"
MONTHLY=ROOT/"docs"/"data"/"market_top_ng3_monthly_snapshots.json"

class NG3ForwardDataContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.x=json.loads(CURRENT.read_text(encoding="utf-8"))
        cls.h=json.loads(HISTORY.read_text(encoding="utf-8"))
        cls.e=json.loads(EPISODES.read_text(encoding="utf-8"))
        cls.m=json.loads(MONTHLY.read_text(encoding="utf-8"))

    def test_seed_is_not_prospective_evidence(self):
        self.assertEqual(self.x["effective_month"],"202609")
        self.assertEqual(
            self.x["evidence_phase"],
            "RETROSPECTIVE_TRAINING_DIAGNOSTIC",
        )
        self.assertFalse(self.x["counts_toward_prospective_validation"])
        self.assertEqual(
            self.x["prospective_start_effective_month"],
            "202612",
        )

    def test_seed_score_and_gates_match_live_dry_run(self):
        self.assertAlmostEqual(
            self.x["route_a_ng3_score"],
            39.42423064841047,
            places=10,
        )
        self.assertAlmostEqual(
            self.x["components"]["financial_lead_gap_raw"],
            -7.4313425704730065,
            places=10,
        )
        self.assertFalse(self.x["gates"]["route_ge_85"])
        self.assertFalse(self.x["gates"]["lead_gap_ge_10"])
        self.assertTrue(self.x["gates"]["warmup_ge_120"])
        self.assertFalse(self.x["gates"]["phase_gate"])
        self.assertTrue(self.x["gates"]["top_location"]["passes"])
        self.assertEqual(self.x["state"],"IDLE")

    def test_fallback_provenance_is_visible(self):
        c=self.x["sources"]["credit"]
        self.assertIn("Pinned 1953+ credit history",c["source"])
        self.assertEqual(
            c["pinned_commit"],
            "71af02cba3493ffa15ac47f512dc346598f2e23f",
        )
        self.assertEqual(c["latest_month"],"202609")
        self.assertEqual(
            c["extension_manifest_taken_at_utc"],
            "2026-10-16T17:44:03+00:00",
        )

    def test_governance_is_fail_closed(self):
        g=self.x["governance"]
        self.assertFalse(g["historical_validation_authorized"])
        self.assertFalse(g["production_promotion_authorized"])
        self.assertFalse(g["post_preregistration_tuning_allowed"])
        self.assertEqual(self.x["production_effect"],"none")

    def test_monthly_snapshot_book_starts_empty_before_prospective_boundary(self):
        self.assertEqual(self.m["prospective_start_effective_month"],"202612")
        self.assertEqual(self.m["snapshots"],[])
        self.assertEqual(self.m["summary"]["frozen_prospective_months"],0)

    def test_episode_ledger_starts_empty_before_prospective_boundary(self):
        self.assertEqual(self.e["episodes"],[])
        s=self.e["summary"]
        self.assertEqual(s["prospective_episode_count"],0)
        self.assertEqual(s["complete_252_session_episodes"],0)
        self.assertFalse(s["review_eligible"])
        self.assertFalse(s["automatic_promotion"])
        self.assertIsNone(s["action_signal"])

    def test_history_seed_cannot_count_as_prospective(self):
        rows=self.h["history"]
        self.assertEqual(len(rows),1)
        self.assertFalse(rows[0]["counts_toward_prospective_validation"])
        self.assertEqual(
            rows[0]["evidence_phase"],
            "RETROSPECTIVE_TRAINING_DIAGNOSTIC",
        )

if __name__=="__main__":
    unittest.main()
