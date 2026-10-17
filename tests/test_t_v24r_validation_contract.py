from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "research" / "t_v24r_validation.json"


class TV24RValidationContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads(PATH.read_text(encoding="utf-8"))

    def test_model_identity_and_status(self):
        self.assertEqual(self.data["model"], "T_v2.4R")
        self.assertEqual(
            self.data["status"],
            "PREREGISTERED_FORMULA_VALIDATED_RESEARCH_ONLY",
        )
        self.assertTrue(self.data["frozen_after_preregistration"])

    def test_known_event_first_confirmations_are_frozen(self):
        expected = {
            "1998": "1998-08-04",
            "2000": "2000-04-14",
            "2007": "2007-11-09",
            "2011": "2011-06-10",
            "2018": "2018-10-11",
            "2022": "2022-01-20",
        }
        got = {
            k: v["first_breakdown"]
            for k, v in self.data["event_windows"].items()
        }
        self.assertEqual(got, expected)

    def test_2022_research_path_fingerprint(self):
        rows = {x["date"]: x for x in self.data["spy_2022"]}
        self.assertAlmostEqual(rows["2022-01-18"]["t_v24r"], 45.894, places=3)
        self.assertAlmostEqual(rows["2022-01-19"]["t_v24r"], 59.123, places=3)
        self.assertAlmostEqual(rows["2022-01-20"]["t_v24r"], 73.079, places=3)
        self.assertGreaterEqual(rows["2022-01-20"]["dd12_pct"], 4.5)

    def test_unconditional_frequency_is_not_hidden(self):
        self.assertEqual(self.data["unconditional"]["flagged_days"], 2218)
        self.assertAlmostEqual(
            self.data["unconditional"]["flagged_share_pct"],
            30.2,
            places=1,
        )
        self.assertIn(
            "not a standalone top signal",
            self.data["unconditional"]["note"],
        )


if __name__ == "__main__":
    unittest.main()
