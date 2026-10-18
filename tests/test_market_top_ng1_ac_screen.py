from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "research" / "market_top_ng1_ac_screen.json"


class MarketTopNG1ACScreenTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads(PATH.read_text(encoding="utf-8"))

    def test_c_is_rejected(self):
        c = self.data["route_c_ng1"]
        self.assertEqual(c["decision"], "REJECT")
        self.assertEqual(
            c["failed_negative_window"]["window"],
            "1998-06_to_1998-10",
        )
        self.assertTrue(c["failed_negative_window"]["hits"])

    def test_a_only_passes_screening(self):
        a = self.data["route_a_ng1"]
        self.assertEqual(a["decision"], "ACCEPT_SCREENING_CANDIDATE")
        self.assertGreater(a["primary_positive"]["hit"]["score"], 85)
        self.assertEqual(a["additional_episode_count"], 2)
        self.assertEqual(a["preregistered_max_additional_episodes"], 2)

    def test_a_negative_controls_are_clean(self):
        a = self.data["route_a_ng1"]
        self.assertTrue(all(not hits for hits in a["negative_windows"].values()))

    def test_no_legacy_promotion_or_posthoc_tuning(self):
        self.assertTrue(self.data["no_posthoc_tuning"])
        self.assertEqual(self.data["legacy_v24_route_a_status"], "UNRESOLVED")
        self.assertEqual(self.data["legacy_v24_route_c_status"], "UNRESOLVED")


if __name__ == "__main__":
    unittest.main()
