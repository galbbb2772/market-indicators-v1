from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CURRENT = ROOT / "docs" / "data" / "market_top_cross_monitor_current.json"


class MarketTopCrossMonitorDataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads(CURRENT.read_text(encoding="utf-8"))

    def test_schema_and_provenance_are_current(self):
        self.assertEqual(
            self.data["schema_version"],
            "market-top-cross-monitor-2",
        )
        self.assertIsNone(self.data["evidence_phase"])
        p = self.data["input_provenance"]
        self.assertEqual(
            p["route_b_schema_version"],
            "market-top-shadow-forward-1",
        )
        self.assertEqual(
            p["master_top_version"],
            "MASTER-TOP-V2.1.8-FROZEN",
        )
        self.assertTrue(p["master_top_formula_frozen"])
        self.assertEqual(p["route_b_age_days_at_monitor"], 1)
        self.assertEqual(p["max_monitor_input_age_days"], 5)

    def test_seed_is_not_comparable(self):
        self.assertFalse(self.data["comparable"])
        self.assertEqual(self.data["status"], "NOT_COMPARABLE")
        self.assertIsNone(self.data["comparison"])

    def test_seed_records_why_not_comparable(self):
        reasons = set(self.data["reasons"])
        self.assertIn("MASTER_TOP_SEED_ONLY", reasons)
        self.assertIn("ASOF_MISMATCH", reasons)

    def test_no_ensemble_or_action_is_materialized(self):
        self.assertNotIn("ensemble_score", self.data)
        self.assertNotIn("action_signal", self.data)
        self.assertTrue(self.data["research_only"])
        self.assertEqual(self.data["production_effect"], "none")


if __name__ == "__main__":
    unittest.main()
