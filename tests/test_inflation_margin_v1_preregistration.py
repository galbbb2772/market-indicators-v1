from __future__ import annotations

import json
import unittest
from pathlib import Path

import screen_inflation_margin_v1 as im

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "research" / "market_top_inflation_margin_v1_preregistration.json"


class InflationMarginV1PreregistrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads(PATH.read_text(encoding="utf-8"))

    def test_route_is_separate_and_research_only(self):
        self.assertTrue(self.data["research_only"])
        self.assertTrue(self.data["separate_route"])
        self.assertFalse(self.data["modifies_policyshock"])
        self.assertEqual(self.data["production_effect"], "none")

    def test_formula_and_threshold_are_frozen(self):
        self.assertEqual(
            self.data["formula"]["route_im_v1_1"],
            "cbrt(InflationScore*ULCScore*MarginCompressionScore)",
        )
        self.assertEqual(self.data["state_gate"]["route_threshold"], 85)
        self.assertEqual(im.THRESHOLD, 85.0)

    def test_source_semantics_are_frozen(self):
        src = self.data["sources"]
        self.assertEqual(src["cpi_series"], "CPIAUCSL")
        self.assertEqual(src["unit_labor_cost_yoy"], "PRS85006111")
        self.assertEqual(src["unit_profit_yoy"], "PRS88003191")
        self.assertEqual(im.CPI_ID, "CPIAUCSL")
        self.assertEqual(im.ULC_ID, "PRS85006111")
        self.assertEqual(im.UNIT_PROFIT_ID, "PRS88003191")

    def test_lags_are_frozen(self):
        pit = self.data["point_in_time"]
        self.assertEqual(pit["cpi_effective_lag_months"], 1)
        self.assertEqual(
            pit["quarterly_effective_lag_months_from_quarter_start"], 5
        )
        self.assertEqual(pit["warmup_years"], 10)
        self.assertFalse(pit["event_specific_lags"])

    def test_validation_windows_match_code(self):
        self.assertEqual(
            [tuple(x) for x in self.data["validation_positive_windows"]],
            im.POSITIVE_WINDOWS,
        )
        self.assertEqual(
            [tuple(x) for x in self.data["validation_negative_windows"]],
            im.NEGATIVE_WINDOWS,
        )

    def test_no_post_screen_tuning(self):
        self.assertFalse(self.data["post_screen_tuning_allowed"])


if __name__ == "__main__":
    unittest.main()
