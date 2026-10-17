from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "research" / "t_v24_recovery_fingerprints.json"


class TRecoveryContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads(PATH.read_text(encoding="utf-8"))
        cls.rows = {x["event"]: x for x in cls.data["top_month_fingerprints"]}

    def test_original_formula_is_explicitly_unresolved(self):
        self.assertEqual(self.data["status"], "ORIGINAL_FORMULA_NOT_RECOVERED")

    def test_archived_top_month_fingerprints(self):
        expected = {
            "1998": (73.8, 0),
            "2000": (47.5, 2),
            "2007": (48.0, 1),
            "2011": (38.3, 3),
            "2018": (39.7, 1),
            "2022": (83.8, 0),
        }
        got = {
            k: (self.rows[k]["top_month_t"], self.rows[k]["first_t_ge_70_delay_months"])
            for k in expected
        }
        self.assertEqual(got, expected)

    def test_no_surrogate_may_silently_reuse_original_name(self):
        a = self.data["recovery_acceptance"]
        self.assertTrue(a["exact_formula_required_for_original_name"])
        self.assertTrue(a["surrogate_must_receive_new_version_name"])
        self.assertEqual(a["must_reproduce_top_month_scores_tolerance"], 0.25)
        self.assertTrue(a["must_reproduce_first_crossing_delays_exactly"])


if __name__ == "__main__":
    unittest.main()
