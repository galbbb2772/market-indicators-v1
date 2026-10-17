from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MATRIX = ROOT / "research" / "v24_event_matrix.json"


class V24EventMatrixContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads(MATRIX.read_text(encoding="utf-8"))
        cls.by_id = {x["id"]: x for x in cls.data["events"]}

    def test_accepted_full_model_statuses_are_frozen(self):
        expected = {
            "1998": "NO",
            "2000": "YES",
            "2007": "YES",
            "2011": "NO",
            "2018": "NO",
            "2022": "YES",
        }
        self.assertEqual({k: self.by_id[k]["full_model_status"] for k in expected}, expected)

    def test_accepted_trigger_types_are_not_rewritten(self):
        self.assertEqual(self.by_id["2000"]["accepted_trigger_type"], "BREADTH_TO_PRICE")
        self.assertEqual(self.by_id["2007"]["accepted_trigger_type"], "PRICE")
        self.assertEqual(self.by_id["2022"]["accepted_trigger_type"], "EARLY_BREADTH")

    def test_2022_policy_shadow_is_additive_not_historical_relabel(self):
        x = self.by_id["2022"]
        self.assertEqual(x["accepted_trigger_type"], "EARLY_BREADTH")
        self.assertGreater(x["shadow_policy_result"]["route_b_strict_pit"], 85.0)
        self.assertEqual(x["shadow_policy_result"]["state"], "ARMED")
        self.assertEqual(
            x["shadow_policy_result"]["formal_price_trigger_date"],
            "UNRESOLVED_UNTIL_FROZEN_T_SCORE_IS_SUPPLIED",
        )

    def test_provenance_is_explicit(self):
        for x in self.data["events"]:
            self.assertIn(x["evidence_level"], {"accepted_historical_output", "mixed", "fresh_recompute"})


if __name__ == "__main__":
    unittest.main()
