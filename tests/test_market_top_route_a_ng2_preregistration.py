from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "research" / "market_top_route_a_ng2_preregistration.json"


class RouteANG2PreregistrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.x = json.loads(PATH.read_text(encoding="utf-8"))

    def test_formula_is_frozen_before_validation(self):
        self.assertEqual(self.x["status"], "PREREGISTERED_NOT_VALIDATED")
        self.assertEqual(
            self.x["formula"]["route_a_ng2"],
            "sqrt(route_a_ng1*financial_lead_gap_score)",
        )
        self.assertEqual(self.x["state_gate"]["route_threshold"], 85)

    def test_holdout_and_outcome_rules_are_frozen(self):
        v = self.x["validation"]
        self.assertEqual(v["first_holdout"], "pre-1993")
        self.assertEqual(v["end_month"], "1992-12")
        self.assertEqual(v["horizon_sessions"], 252)
        self.assertEqual(v["minimum_evaluable_episodes"], 2)
        self.assertEqual(v["minimum_major_top_share"], 0.5)
        self.assertEqual(v["maximum_clear_false_share"], 0.25)

    def test_no_retuning_or_production_effect(self):
        self.assertFalse(self.x["post_validation_tuning_allowed"])
        self.assertEqual(self.x["production_effect"], "none")
        self.assertFalse(self.x["legacy_recovery"])


if __name__ == "__main__":
    unittest.main()
