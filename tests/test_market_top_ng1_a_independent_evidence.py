from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "research" / "market_top_ng1_a_independent_audit.json"


class MarketTopNG1AIndependentEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads(PATH.read_text(encoding="utf-8"))

    def test_independent_replay_passes_with_margin(self):
        x = self.data["scores"]
        self.assertGreater(x["route_a_ng1"], x["threshold"])
        self.assertGreater(x["margin"], 1.0)

    def test_credit_target_parity_is_locked(self):
        x = self.data["parity"]
        self.assertTrue(x["independent_credit_vs_first_screen_target"])
        self.assertEqual(x["baa_200710_expected"], 6.48)
        self.assertEqual(x["gs10_200710_expected"], 4.53)
        self.assertAlmostEqual(
            x["spread_shock_score_expected"],
            75.80893682588598,
            places=10,
        )

    def test_promotion_is_limited(self):
        x = self.data["interpretation"]
        self.assertEqual(x["promotion"], "SOURCE_VALIDATED_SCREENING_CANDIDATE")
        self.assertFalse(x["legacy_route_a_recovered"])
        self.assertFalse(x["production_ready"])
        self.assertFalse(x["prospective_validated"])
        self.assertFalse(x["parameters_changed"])


if __name__ == "__main__":
    unittest.main()
