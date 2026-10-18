from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "research" / "market_top_ng1_a_extra_episode_cases.json"


class MarketTopNG1AExtraEpisodeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads(PATH.read_text(encoding="utf-8"))

    def test_1998_is_kept_as_clear_false_positive(self):
        x = self.data["episodes"]["1998-11_to_1999-03"]
        self.assertEqual(x["interpretation"], "CLEAR_TOP_FALSE_POSITIVE")
        self.assertGreater(x["h252"]["forward_return_pct"], 15)
        self.assertGreater(x["h252"]["worst_return_from_anchor_pct"], -3)

    def test_2012_is_correction_not_major_top(self):
        x = self.data["episodes"]["2012-02"]
        self.assertEqual(x["interpretation"], "CORRECTION_RISK_NOT_MAJOR_TOP")
        self.assertLess(x["h126"]["max_peak_to_trough_dd_pct"], -8)
        self.assertGreater(x["h252"]["forward_return_pct"], 10)

    def test_source_invariance_and_no_retuning(self):
        self.assertTrue(self.data["source_invariance"]["anchors_and_outcomes_match"])
        self.assertFalse(self.data["metric_protocol"]["parameters_retuned"])

    def test_candidate_is_not_promoted_to_legacy_or_production(self):
        x = self.data["research_conclusion"]
        self.assertFalse(x["legacy_route_a_recovered"])
        self.assertFalse(x["production_ready"])


if __name__ == "__main__":
    unittest.main()
