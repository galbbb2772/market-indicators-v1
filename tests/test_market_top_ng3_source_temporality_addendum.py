from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
PATH=ROOT/"research"/"market_top_route_a_ng3_source_temporality_addendum.json"

class NG3SourceTemporalityAddendumTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.x=json.loads(PATH.read_text(encoding="utf-8"))

    def test_addendum_does_not_change_model_or_promotion_rule(self):
        self.assertFalse(self.x["model_rules_changed"])
        self.assertFalse(self.x["promotion_rule_changed"])
        self.assertEqual(
            self.x["original_first_countable_effective_month"],
            "202612",
        )

    def test_december_is_straddling_but_still_originally_countable(self):
        x=self.x["evidence_quality"]["effective_202612"]
        self.assertEqual(x["ff_source_month"],"202610")
        self.assertEqual(x["credit_source_month"],"202611")
        self.assertFalse(x["all_source_months_fully_post_preregistration"])
        self.assertTrue(x["remains_countable_under_original_preregistration"])
        self.assertEqual(
            x["tier"],
            "SOURCE_MONTH_STRADDLES_PREREGISTRATION",
        )

    def test_january_2027_is_first_full_source_month_evidence(self):
        x=self.x["evidence_quality"][
            "first_fully_post_preregistration_source_effective_month"
        ]
        self.assertEqual(x["effective_month"],"202701")
        self.assertEqual(x["ff_source_month"],"202611")
        self.assertEqual(x["credit_source_month"],"202612")

    def test_missing_months_cannot_be_silently_backfilled(self):
        x=self.x["monthly_gap_policy"]
        self.assertTrue(x["missing_months_explicit"])
        self.assertFalse(
            x["later_backfill_may_masquerade_as_first_available_vintage"]
        )

if __name__=="__main__":
    unittest.main()
