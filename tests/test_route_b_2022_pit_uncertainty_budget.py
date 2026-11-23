from __future__ import annotations

import json
import math
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "research" / "route_b_2022_pit_uncertainty_budget.json"


class RouteB2022PITUncertaintyBudgetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads(PATH.read_text(encoding="utf-8"))

    def test_baseline_is_a_narrow_pass(self):
        x = self.data["baseline"]
        self.assertGreater(x["route_b"], x["threshold"])
        self.assertLess(x["margin"], 0.5)

    def test_failure_boundaries_reproduce_threshold(self):
        b = self.data["baseline"]
        f = self.data["single_input_failure_boundaries"]

        for v, p, s in (
            (f["valuation"], b["policy_shock"], b["size_weakness"]),
            (b["valuation"], f["policy_shock"], b["size_weakness"]),
            (b["valuation"], b["policy_shock"], f["size_weakness"]),
        ):
            score = (v * p * s) ** (1.0 / 3.0)
            self.assertAlmostEqual(score, b["threshold"], places=9)

    def test_joint_stress_is_ordered(self):
        j = self.data["equal_proportional_joint_stress"]
        self.assertGreater(j["one_input_drop_pct"], j["two_inputs_each_drop_pct"])
        self.assertGreater(j["two_inputs_each_drop_pct"], j["three_inputs_each_drop_pct"])
        self.assertGreater(j["three_inputs_each_drop_pct"], 0)

    def test_observed_vintage_pass_is_not_called_wide_margin(self):
        self.assertEqual(
            self.data["interpretation"]["classification"],
            "NARROW_BUT_OBSERVED_VINTAGE_ROBUST_PASS",
        )
        self.assertTrue(self.data["interpretation"]["no_parameter_tuning"])


if __name__ == "__main__":
    unittest.main()
