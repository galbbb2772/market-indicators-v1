from __future__ import annotations

import json
import unittest
from pathlib import Path

import market_top_route_c_ng3_forward as ng3

ROOT = Path(__file__).resolve().parents[1]
PREREG = ROOT / "research" / "market_top_route_c_ng3_preregistration.json"


class RouteCNG3PreregistrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads(PREREG.read_text(encoding="utf-8"))

    def test_prospective_only_boundary(self):
        self.assertEqual(
            self.data["status"],
            "PREREGISTERED_PROSPECTIVE_ONLY",
        )
        self.assertTrue(self.data["research_only"])
        self.assertEqual(self.data["production_effect"], "none")
        self.assertEqual(
            self.data["legacy_route_c_status"], "UNRESOLVED"
        )

    def test_formula_constants_match_code(self):
        self.assertEqual(
            self.data["point_in_time"]["valuation_context_months"],
            ng3.VALUATION_CONTEXT_MONTHS,
        )
        self.assertEqual(
            self.data["state_gate"]["route_threshold"],
            ng3.ROUTE_THRESHOLD,
        )
        self.assertEqual(
            self.data["phase_gate"]["minimum_concentration_breadth"],
            ng3.CONCENTRATION_MIN,
        )
        self.assertEqual(
            self.data["phase_gate"]["maximum_spread_shock_score"],
            ng3.SPREAD_MAX,
        )
        self.assertEqual(
            self.data["phase_gate"]["minimum_effective_history_months"],
            ng3.WARMUP_MONTHS,
        )

    def test_prospective_start_matches_code(self):
        self.assertEqual(
            self.data["prospective"]["first_countable_effective_month"],
            ng3.FIRST_PROSPECTIVE_EFFECTIVE_MONTH,
        )

    def test_no_post_preregistration_tuning(self):
        self.assertFalse(
            self.data["post_preregistration_tuning_allowed"]
        )

    def test_trailing_percentile(self):
        vals = list(range(1, 121))
        self.assertEqual(
            ng3.trailing_percentile_current(vals, 119, 120),
            100.0,
        )
        self.assertIsNone(
            ng3.trailing_percentile_current(vals, 118, 120)
        )


if __name__ == "__main__":
    unittest.main()
