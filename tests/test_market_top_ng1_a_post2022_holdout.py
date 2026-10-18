from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "research" / "market_top_ng1_a_post2022_holdout.json"


class MarketTopNG1APost2022HoldoutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads(PATH.read_text(encoding="utf-8"))

    def test_holdout_is_complete_and_untuned(self):
        self.assertEqual(
            self.data["status"],
            "ARMED_EPISODES_WITH_COMPLETE_OUTCOMES",
        )
        self.assertEqual(self.data["holdout"]["start_effective_month"], "2023-01")
        self.assertEqual(self.data["holdout"]["end_effective_month"], "2026-07")
        self.assertEqual(self.data["holdout"]["monthly_states"], 43)
        self.assertFalse(
            self.data["frozen_parameters"]["changed_after_preregistration"]
        )

    def test_every_episode_has_252_session_outcome(self):
        episodes = self.data["armed_episodes"]
        self.assertEqual(len(episodes), 2)
        for episode in episodes:
            self.assertIn("h252", episode["outcomes"])
            self.assertIn("end_date", episode["outcomes"]["h252"])

    def test_2025_07_is_clear_false_top(self):
        x = self.data["armed_episodes"][0]
        self.assertEqual(x["start"], "2025-07")
        self.assertEqual(x["interpretation"], "CLEAR_TOP_FALSE_POSITIVE")
        self.assertGreater(x["outcomes"]["h252"]["forward_return_pct"], 15)
        self.assertGreater(
            x["outcomes"]["h252"]["worst_return_from_anchor_pct"],
            -2,
        )

    def test_2025_09_is_correction_not_major_top(self):
        x = self.data["armed_episodes"][1]
        self.assertEqual(x["start"], "2025-09")
        self.assertEqual(x["interpretation"], "CORRECTION_RISK_NOT_MAJOR_TOP")
        self.assertLess(
            x["outcomes"]["h126"]["max_peak_to_trough_dd_pct"],
            -8,
        )
        self.assertGreater(x["outcomes"]["h252"]["forward_return_pct"], 10)

    def test_holdout_does_not_promote_candidate(self):
        x = self.data["research_conclusion"]
        self.assertEqual(x["major_top_confirmed_count"], 0)
        self.assertFalse(x["legacy_route_a_recovered"])
        self.assertFalse(x["production_ready"])
        self.assertFalse(x["parameters_retuned"])


if __name__ == "__main__":
    unittest.main()
