from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "research" / "t_v24r_source_invariance.json"


class TV24RSourceInvarianceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads(PATH.read_text(encoding="utf-8"))

    def test_formula_was_not_changed(self):
        self.assertTrue(self.data["frozen_formula_unchanged"])
        self.assertEqual(self.data["status"], "PASS_WITH_COVERAGE_LIMIT")

    def test_all_six_snapshot_dates_match(self):
        s = self.data["snapshot_invariance"]
        self.assertTrue(s["all_six_event_dates_equal"])
        expected = {
            "1998": "1998-08-04",
            "2000": "2000-04-14",
            "2007": "2007-11-09",
            "2011": "2011-06-10",
            "2018": "2018-10-11",
            "2022": "2022-01-20",
        }
        self.assertEqual(s["event_dates"], expected)
        self.assertLess(s["max_close_abs_diff_usd"], 1e-6)

    def test_index_crosscheck_dates_match(self):
        for event in ("2011", "2018", "2022"):
            self.assertTrue(self.data["index_crosscheck"][event]["date_match"])

    def test_official_fred_2022_points_are_locked(self):
        p = self.data["index_crosscheck"]["2022"]["official_fred_points"]
        self.assertEqual(p["2022-01-03"], 4796.56)
        self.assertEqual(p["2022-01-18"], 4577.11)
        self.assertEqual(p["2022-01-19"], 4532.76)
        self.assertEqual(p["2022-01-20"], 4482.73)

    def test_unresolved_provider_coverage_stays_visible(self):
        c = self.data["coverage"]
        self.assertEqual(
            c["unresolved_provider_independence_events"],
            ["1998", "2000", "2007"],
        )


if __name__ == "__main__":
    unittest.main()
