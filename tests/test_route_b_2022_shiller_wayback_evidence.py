from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "research" / "route_b_2022_shiller_wayback_audit.json"


class RouteB2022ShillerWaybackEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads(PATH.read_text(encoding="utf-8"))

    def test_exact_jan3_vintage_is_not_overclaimed(self):
        self.assertEqual(
            self.data["status"],
            "NO_PRE_CUTOFF_SHILLER_SNAPSHOT_WITH_202111",
        )
        self.assertFalse(self.data["exact_2022_01_03_valuation_vintage"])

    def test_real_pre_cutoff_snapshot_is_locked(self):
        x = self.data["latest_usable_snapshot"]
        self.assertEqual(x["timestamp"], "20211012122941")
        self.assertEqual(x["last_month"], "202109")
        self.assertAlmostEqual(x["cape"], 38.34227971263208, places=8)
        self.assertAlmostEqual(x["valuation"], 98.57904085257549, places=8)

    def test_both_observed_size_vintages_preserve_route_b_pass(self):
        s = self.data["route_b_sensitivity"]
        self.assertGreater(
            s["with_official_2022_size_weakness"]["route_b"],
            85.0,
        )
        self.assertGreater(
            s["with_current_conservative_size_weakness"]["route_b"],
            85.0,
        )

    def test_early_stop_is_proven_not_assumed(self):
        p = self.data["early_stop_proof"]
        self.assertTrue(p["proof_complete"])
        self.assertEqual(p["candidate_order"], "timestamp_descending")
        self.assertEqual(
            p["temporal_consistency_rule"],
            "workbook_last_month <= capture_month",
        )
        self.assertEqual(p["newest_usable_capture_month"], "202110")
        self.assertEqual(p["target_month"], "202111")
        self.assertFalse(
            p["older_candidates_can_legitimately_contain_target"]
        )


if __name__ == "__main__":
    unittest.main()
