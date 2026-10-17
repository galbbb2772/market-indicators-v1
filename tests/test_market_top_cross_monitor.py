from __future__ import annotations

import unittest

from market_top_cross_monitor import classify


def rb(asof="2026-10-16", score=65.58):
    return {
        "schema_version": "market-top-shadow-forward-1",
        "research_only": True,
        "asof": asof,
        "route_b": {"score": score},
        "policy_path": {"state": "IDLE"},
        "full_legacy_model": {"route_b": "RESOLVED"},
    }


def mt(
    asof="2026-10-16",
    score=60.0,
    *,
    research_status="frozen formula; post-freeze data only may accumulate prospective evidence",
    symbol="^GSPC",
):
    return {
        "version": "MASTER-TOP-V2.1.8-FROZEN",
        "formula_frozen": True,
        "prospective_evidence_start": "2026-10-17",
        "latest": {
            "asof": asof,
            "supplemental_route": score,
            "route_triggered": score >= 55,
            "research_status": research_status,
            "price_symbol": symbol,
            "breadth_source": "MarketParquet stock_daily reconstructed 52-week H/L; 252 prior sessions; 20-session persistence",
        }
    }


class MarketTopCrossMonitorTests(unittest.TestCase):
    def test_seed_master_top_is_not_comparable(self):
        x = classify(
            rb(),
            mt(
                asof="2026-10-09",
                score=99.33,
                research_status="seed snapshot only",
                symbol="SPY proxy seed",
            ),
            generated_at="2026-10-17T00:00:00+00:00",
        )
        self.assertFalse(x["comparable"])
        self.assertEqual(x["status"], "NOT_COMPARABLE")
        self.assertIn("MASTER_TOP_SEED_ONLY", x["reasons"])
        self.assertIn("ASOF_MISMATCH", x["reasons"])
        self.assertIsNone(x["comparison"])

    def test_same_day_both_high(self):
        x = classify(rb(score=90), mt(score=70))
        self.assertTrue(x["comparable"])
        self.assertEqual(x["comparison"]["label"], "BOTH_HIGH")
        self.assertIsNone(x["comparison"]["ensemble_score"])
        self.assertIsNone(x["comparison"]["action_signal"])

    def test_same_day_master_only(self):
        x = classify(rb(score=65), mt(score=70))
        self.assertEqual(x["comparison"]["label"], "MASTER_TOP_ONLY")

    def test_same_day_route_b_only(self):
        x = classify(rb(score=90), mt(score=40))
        self.assertEqual(x["comparison"]["label"], "ROUTE_B_ONLY")

    def test_same_day_both_low(self):
        x = classify(rb(score=65), mt(score=40))
        self.assertEqual(x["comparison"]["label"], "BOTH_LOW")

    def test_wrong_master_version_is_not_comparable(self):
        payload = mt()
        payload["version"] = "MASTER-TOP-OLD"
        x = classify(rb(), payload)
        self.assertFalse(x["comparable"])
        self.assertIn("MASTER_TOP_WRONG_VERSION", x["reasons"])

    def test_noncanonical_master_sources_are_not_live(self):
        payload = mt()
        payload["latest"]["price_symbol"] = "SPY"
        x = classify(rb(), payload)
        self.assertFalse(x["comparable"])
        self.assertIn("MASTER_TOP_NONCANONICAL_PRICE_SOURCE", x["reasons"])

        payload = mt()
        payload["latest"]["breadth_source"] = "manual proxy"
        x = classify(rb(), payload)
        self.assertFalse(x["comparable"])
        self.assertIn("MASTER_TOP_NONCANONICAL_BREADTH_SOURCE", x["reasons"])

    def test_wrong_route_b_schema_is_not_comparable(self):
        payload = rb()
        payload["schema_version"] = "unknown"
        x = classify(payload, mt())
        self.assertFalse(x["comparable"])
        self.assertIn("ROUTE_B_WRONG_SCHEMA", x["reasons"])

    def test_evidence_phase_marks_pre_and_post_freeze(self):
        pre = classify(
            rb(asof="2026-10-16"),
            mt(asof="2026-10-16"),
        )
        self.assertTrue(pre["comparable"])
        self.assertEqual(pre["evidence_phase"], "PRE_FREEZE_ASOF_DIAGNOSTIC")

        post = classify(
            rb(asof="2026-10-19"),
            mt(asof="2026-10-19"),
        )
        self.assertTrue(post["comparable"])
        self.assertEqual(post["evidence_phase"], "POST_FREEZE_PROSPECTIVE")
        self.assertEqual(
            post["comparison"]["evidence_phase"],
            "POST_FREEZE_PROSPECTIVE",
        )

    def test_asof_mismatch_blocks_comparison_even_when_both_live(self):
        x = classify(rb(asof="2026-10-16"), mt(asof="2026-10-15"))
        self.assertFalse(x["comparable"])
        self.assertIn("ASOF_MISMATCH", x["reasons"])
        self.assertIsNone(x["comparison"])


if __name__ == "__main__":
    unittest.main()
