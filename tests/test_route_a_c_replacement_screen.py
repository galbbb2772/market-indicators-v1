from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "research" / "route_a_c_replacement_screen.json"


class RouteACReplacementScreenTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads(PATH.read_text(encoding="utf-8"))

    def test_all_tested_replacements_are_rejected(self):
        for x in self.data["route_a_candidates"]:
            self.assertEqual(x["decision"], "REJECTED")
        for x in self.data["route_c_candidates"]:
            self.assertEqual(x["decision"], "REJECTED")

    def test_c3_was_preregistered(self):
        c3 = next(x for x in self.data["route_c_candidates"] if x["id"].startswith("C3_"))
        self.assertTrue(c3["preregistered_before_validation"])
        self.assertFalse(c3["accepted_2021_10_reproduction"])

    def test_original_routes_stay_unresolved(self):
        self.assertEqual(self.data["conclusion"]["route_a"], "UNRESOLVED")
        self.assertEqual(self.data["conclusion"]["route_c"], "UNRESOLVED")
        self.assertFalse(self.data["rules"]["posthoc_threshold_tuning"] if "posthoc_threshold_tuning" in self.data["rules"] else False)


if __name__ == "__main__":
    unittest.main()
