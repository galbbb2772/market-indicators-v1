from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
PATH=ROOT/"research"/"market_top_route_a_ng_decision_record.json"

class RouteANGDecisionRecordTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.x=json.loads(PATH.read_text(encoding="utf-8"))

    def test_legacy_route_a_remains_unresolved(self):
        self.assertEqual(self.x["original_route_a"]["status"],"UNRESOLVED")
        self.assertFalse(self.x["original_route_a"]["legacy_formula_recovered"])

    def test_ng1_and_ng2_are_not_promoted(self):
        self.assertEqual(self.x["ng1"]["status"],"CLOSED_NO_TOP_ROUTE_PROMOTION")
        self.assertEqual(self.x["ng2"]["status"],"REJECT_NG2_TOP_ROUTE")
        self.assertFalse(self.x["ng1"]["production_ready"])
        self.assertFalse(self.x["ng2"]["post_validation_tuning_allowed"])

    def test_ng3_is_prospective_only(self):
        x=self.x["ng3"]
        self.assertEqual(x["status"],"PROSPECTIVE_VALIDATION_PENDING")
        self.assertFalse(x["historical_validation_authorized"])
        self.assertEqual(x["prospective_start_effective_month"],"202612")
        self.assertEqual(
            x["evidence_protocol"],
            "market-top-route-a-ng3-evidence-protocol-2",
        )
        self.assertEqual(
            x[
                "promotion_review_minimum_complete_252_session_episodes_without_continuity_gaps"
            ],
            4,
        )
        self.assertIn(
            "one episode",
            x["continuity_gap_policy"]["rule"],
        )
        self.assertFalse(
            x["current_snapshot"]["counts_toward_prospective_validation"]
        )
        q=x["source_temporality"]
        self.assertEqual(
            q["effective_202612_tier"],
            "SOURCE_MONTH_STRADDLES_PREREGISTRATION",
        )
        self.assertFalse(
            q["effective_202612_all_source_months_fully_post_preregistration"]
        )
        self.assertEqual(
            q["first_fully_post_preregistration_source_effective_month"],
            "202701",
        )

    def test_no_historical_holdout_remains(self):
        self.assertFalse(
            self.x["evidence_governance"]["untouched_historical_holdout_remaining"]
        )
        self.assertIn(
            "2026-12",
            self.x["evidence_governance"]["next_valid_evidence"],
        )
        self.assertTrue(
            self.x["evidence_governance"][
                "monthly_evidence_gaps_must_be_explicit"
            ]
        )
        self.assertFalse(
            self.x["evidence_governance"][
                "silent_later_vintage_backfill_allowed"
            ]
        )
        self.assertTrue(
            self.x["evidence_governance"][
                "episode_count_inflation_from_missing_months_forbidden"
            ]
        )
        self.assertTrue(
            self.x["evidence_governance"][
                "promotion_review_uses_clean_episode_count"
            ]
        )

if __name__=="__main__":
    unittest.main()
