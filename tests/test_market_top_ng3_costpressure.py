from __future__ import annotations

import json
import unittest
from pathlib import Path

import screen_market_top_ng3_costpressure as ng3

ROOT = Path(__file__).resolve().parents[1]
PREREG = ROOT / "research" / "market_top_ng3_costpressure_preregistration.json"


class MarketTopNG3CostPressureContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads(PREREG.read_text(encoding="utf-8"))

    def test_preregistration_status(self):
        self.assertEqual(
            self.data["status"],
            "PREREGISTERED_NOT_VALIDATED",
        )
        self.assertTrue(self.data["research_only"])
        self.assertFalse(self.data["post_result_tuning_allowed"])

    def test_sources_are_frozen(self):
        self.assertEqual(self.data["sources"]["cpi"], "CUUR0000SA0")
        self.assertEqual(
            self.data["sources"]["finished_ppi"],
            "WPUFD49207",
        )
        self.assertEqual(
            self.data["sources"]["intermediate_ppi"],
            "WPUID61",
        )
        self.assertEqual(ng3.SERIES["cpi"], "CUUR0000SA0")
        self.assertEqual(ng3.SERIES["finished"], "WPUFD49207")
        self.assertEqual(ng3.SERIES["intermediate"], "WPUID61")

    def test_lag_warmup_threshold_frozen(self):
        self.assertEqual(self.data["pit"]["effective_lag_months"], 6)
        self.assertEqual(ng3.EFFECTIVE_LAG_MONTHS, 6)
        self.assertEqual(self.data["warmup_valid_source_months"], 120)
        self.assertEqual(ng3.WARMUP_VALID_SOURCE_MONTHS, 120)
        self.assertEqual(self.data["threshold"], 85)
        self.assertEqual(ng3.THRESHOLD, 85.0)

    def test_formula_contract(self):
        t = self.data["transforms"]
        self.assertEqual(
            t["costpressure_ng3"],
            "cbrt(InflationLevelScore*FinishedGapScore*IntermediateGapScore)",
        )
        self.assertEqual(
            t["producer_gap_baseline"],
            "sqrt(FinishedGapScore*IntermediateGapScore)",
        )

    def test_screen_windows_frozen(self):
        expected = [
            ["1957-01", "1967-12"],
            ["1975-01", "1986-12"],
            ["1988-01", "2006-12"],
        ]
        self.assertEqual(self.data["screen_windows"], expected)
        self.assertEqual(
            [[str(a), str(b)] for a, b in ng3.SCREEN_WINDOWS],
            expected,
        )

    def test_hypothesis_windows_excluded(self):
        expected = [
            ["1968-01", "1974-12"],
            ["1987-01", "1987-12"],
        ]
        self.assertEqual(
            self.data["hypothesis_generation_exclusions"],
            expected,
        )

    def test_structural_gate_frozen(self):
        a = self.data["structural_acceptance"]
        self.assertEqual(a["min_complete_episodes"], 3)
        self.assertEqual(a["min_major_top_hits"], 2)
        self.assertEqual(a["max_clear_top_false_positives"], 1)
        self.assertEqual(a["min_major_top_fraction"], 0.5)

    def test_margin_does_not_enter_score(self):
        self.assertFalse(self.data["margin_confirm_in_score"])
        self.assertEqual(
            self.data["margin_missing_semantics"],
            "MARGIN_NOT_COMPARABLE",
        )


if __name__ == "__main__":
    unittest.main()
