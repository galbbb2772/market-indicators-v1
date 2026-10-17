from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SHILLER = ROOT / "research" / "route_b_2022_shiller_wayback_audit.json"
LATTICE = ROOT / "research" / "route_b_2022_vintage_robustness_lattice.json"


class RouteB2022VintageRobustnessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.shiller = json.loads(SHILLER.read_text(encoding="utf-8"))
        cls.lattice = json.loads(LATTICE.read_text(encoding="utf-8"))

    def test_shiller_exact_november_vintage_is_not_overclaimed(self):
        self.assertFalse(self.shiller["exact_2022_01_03_valuation_vintage"])
        self.assertEqual(
            self.shiller["status"],
            "NO_PRE_CUTOFF_SHILLER_SNAPSHOT_WITH_202111",
        )

    def test_latest_real_pre_cutoff_shiller_snapshot_is_locked(self):
        x = self.shiller["latest_usable_snapshot"]
        self.assertEqual(x["timestamp"], "20211012122941")
        self.assertEqual(x["last_month"], "202109")
        self.assertAlmostEqual(x["cape"], 38.34227971263208, places=8)
        self.assertAlmostEqual(x["valuation"], 98.57904085257549, places=8)

    def test_archived_valuation_passes_with_both_size_vintages(self):
        x = self.shiller["route_b_sensitivity"]
        self.assertGreater(
            x["with_official_2022_size_weakness"]["route_b"],
            85,
        )
        self.assertGreater(
            x["with_current_conservative_size_weakness"]["route_b"],
            85,
        )

    def test_every_vintage_lattice_scenario_passes(self):
        self.assertTrue(
            all(x["route_b"] >= self.lattice["threshold"]
                for x in self.lattice["scenarios"])
        )

    def test_policy_margin_is_positive_in_most_conservative_cross_vintage_case(self):
        b = self.lattice["failure_boundaries"]
        self.assertGreater(b["actual_policy_shock_margin"], 0)
        self.assertLess(
            b["policy_shock_with_archived_valuation_and_lower_current_size"],
            self.lattice["policy_shock"],
        )


if __name__ == "__main__":
    unittest.main()
