from __future__ import annotations

import json
import unittest
from pathlib import Path

import screen_route_c_ng2_pre1993 as ng2

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "research" / "market_top_route_c_ng2_preregistration.json"


class RouteCNG2PreregistrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads(PATH.read_text(encoding="utf-8"))

    def test_research_boundary(self):
        self.assertTrue(self.data["research_only"])
        self.assertEqual(self.data["production_effect"], "none")
        self.assertEqual(
            self.data["legacy_route_c_status"], "UNRESOLVED"
        )
        self.assertFalse(
            self.data["post_validation_tuning_allowed"]
        )

    def test_frozen_gates_match_code(self):
        g = self.data["ng2_gates"]
        self.assertEqual(g["route_c_ng1_min"], ng2.ROUTE_MIN)
        self.assertEqual(g["valuation_min"], ng2.VALUATION_MIN)
        self.assertEqual(
            g["concentration_breadth_min"],
            ng2.CONCENTRATION_MIN,
        )
        self.assertEqual(
            g["spread_shock_score_max"], ng2.SPREAD_MAX
        )

    def test_holdout_and_warmup_match_code(self):
        h = self.data["holdout"]
        self.assertEqual(h["start"], str(ng2.HOLDOUT_START))
        self.assertEqual(h["end"], str(ng2.HOLDOUT_END))
        self.assertEqual(
            self.data["point_in_time"][
                "common_history_warmup_months"
            ],
            ng2.WARMUP_MONTHS,
        )

    def test_positive_windows_match_code(self):
        expected = [
            tuple(x)
            for x in self.data["holdout"]["positive_windows"]
        ]
        self.assertEqual(expected, ng2.POSITIVE_WINDOWS)

    def test_post1993_is_training_only(self):
        self.assertEqual(
            self.data["training_boundary"],
            "ALL_1993_2022_NG1_C_EPISODES_CONSUMED",
        )


if __name__ == "__main__":
    unittest.main()
