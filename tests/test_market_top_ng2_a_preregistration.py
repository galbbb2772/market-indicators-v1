from __future__ import annotations

import json
import unittest
from pathlib import Path

import screen_market_top_ng2_a_pre1993 as ng2

ROOT = Path(__file__).resolve().parents[1]
PREREG = ROOT / "research" / "market_top_ng2_a_preregistration.json"


class MarketTopNG2APreregistrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads(PREREG.read_text(encoding="utf-8"))

    def test_status_and_boundary(self):
        self.assertEqual(
            self.data["status"],
            "PREREGISTERED_NOT_VALIDATED",
        )
        self.assertTrue(self.data["research_only"])
        self.assertFalse(self.data["legacy_recovery"])
        self.assertFalse(
            self.data["production_pressure_inclusion_authorized"]
        )
        self.assertFalse(self.data["post_validation_tuning_allowed"])

    def test_formula_is_frozen(self):
        f = self.data["formula"]
        self.assertEqual(
            f["financial_lead_gap_raw"],
            "FinanceWeaknessScore-SpreadShockScore",
        )
        self.assertEqual(
            f["credit_lead_stress_ng2"],
            "cbrt(SpreadShockScore*FinanceWeaknessScore*FinancialLeadScore)",
        )
        self.assertEqual(
            f["route_a_ng2"],
            "sqrt(CreditLeadStress_NG2*BreadthStress_NG2)",
        )
        self.assertEqual(self.data["thresholds"]["route"], 85)
        self.assertEqual(ng2.THRESHOLD, 85.0)

    def test_pit_lags_are_frozen(self):
        pit = self.data["point_in_time"]
        self.assertEqual(pit["fama_french_effective_lag_months"], 2)
        self.assertEqual(pit["credit_spread_effective_lag_months"], 1)
        self.assertEqual(pit["percentiles"], "expanding_current_inclusive")
        self.assertFalse(pit["event_specific_lags"])

    def test_holdout_is_pre1993_and_untouched(self):
        h = self.data["holdout"]
        self.assertEqual(h["evaluation_start"], "1963-01")
        self.assertEqual(h["evaluation_end"], "1992-12")
        self.assertEqual(h["percentile_warmup_months"], 120)
        self.assertEqual(ng2.WARMUP_MONTHS, 120)
        self.assertEqual(ng2.OUTCOME_SESSIONS, 252)

    def test_decision_rule_is_frozen(self):
        a = self.data["holdout"]["accept_if"]
        self.assertEqual(a["min_armed_episodes"], 2)
        self.assertEqual(a["min_major_top_hits"], 1)
        self.assertEqual(a["max_clear_top_false_positives"], 0)
        self.assertEqual(a["min_major_top_hit_fraction"], 0.5)

    def test_training_cases_cannot_validate_ng2(self):
        self.assertEqual(
            self.data["hypothesis_generation_cases"],
            ["1998-11", "2007-11", "2012-02", "2025-07", "2025-09"],
        )
        self.assertLess(
            pd_period("1992-12"),
            pd_period("1998-11"),
        )


def pd_period(x: str):
    import pandas as pd

    return pd.Period(x, freq="M")


if __name__ == "__main__":
    unittest.main()
