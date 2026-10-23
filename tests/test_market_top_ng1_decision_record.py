from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "research" / "market_top_ng1_decision_record.json"


class MarketTopNG1DecisionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads(PATH.read_text(encoding="utf-8"))

    def test_ng1_is_closed_without_top_route_promotion(self):
        self.assertEqual(
            self.data["status"],
            "NG1_CLOSED_NO_TOP_ROUTE_PROMOTION",
        )
        self.assertEqual(
            self.data["route_a_ng1"]["final_top_route_decision"],
            "DO_NOT_PROMOTE",
        )
        self.assertEqual(self.data["route_c_ng1"]["decision"], "REJECT")

    def test_episode_summary_preserves_false_signals(self):
        x = self.data["route_a_ng1"]["episode_summary"]
        self.assertEqual(x["evaluated"], 5)
        self.assertEqual(x["major_top_hits"], 1)
        self.assertEqual(x["clear_top_false_positives"], 2)
        self.assertEqual(x["correction_not_major_top"], 2)

    def test_ng1_is_retained_only_as_stress_diagnostic(self):
        self.assertEqual(
            self.data["route_a_ng1"]["retained_use"],
            "RESEARCH_CREDIT_BREADTH_STRESS_DIAGNOSTIC",
        )
        r = self.data["frozen_rules"]
        self.assertTrue(r["do_not_rename_ng1_as_legacy_route_a"])
        self.assertTrue(r["do_not_merge_ng1_into_pressure"])
        self.assertTrue(r["do_not_use_ng1_as_production_signal"])
        self.assertTrue(r["do_not_tune_ng1_after_holdout"])

    def test_legacy_routes_remain_unresolved(self):
        x = self.data["legacy_v24"]
        self.assertEqual(x["route_a"], "UNRESOLVED")
        self.assertEqual(x["route_c"], "UNRESOLVED")
        self.assertFalse(x["replaced_by_ng1"])


if __name__ == "__main__":
    unittest.main()
