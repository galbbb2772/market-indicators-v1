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
        self.assertFalse(
            x["current_snapshot"]["counts_toward_prospective_validation"]
        )

    def test_no_historical_holdout_remains(self):
        self.assertFalse(
            self.x["evidence_governance"]["untouched_historical_holdout_remaining"]
        )
        self.assertIn(
            "2026-12",
            self.x["evidence_governance"]["next_valid_evidence"],
        )

if __name__=="__main__":
    unittest.main()
