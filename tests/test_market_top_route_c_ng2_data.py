from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CURRENT = ROOT / "docs" / "data" / "market_top_route_c_ng2_current.json"
HISTORY = ROOT / "docs" / "data" / "market_top_route_c_ng2_history.json"


class RouteCNG2DataContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.current = json.loads(CURRENT.read_text(encoding="utf-8"))
        cls.history = json.loads(HISTORY.read_text(encoding="utf-8"))

    def test_seed_is_not_prospective_evidence(self):
        x = self.current
        self.assertEqual(x["effective_month"], "202609")
        self.assertEqual(
            x["evidence_phase"],
            "RETROSPECTIVE_HYPOTHESIS_DIAGNOSTIC",
        )
        self.assertFalse(x["counts_toward_prospective_validation"])
        self.assertEqual(x["prospective_start_effective_month"], "202701")

    def test_seed_state_and_governance(self):
        x = self.current
        self.assertAlmostEqual(x["route_c_ng2_score"], 54.79340632381436)
        self.assertEqual(x["state"], "IDLE")
        self.assertTrue(x["gates"]["handoff_ge_40pct"])
        self.assertFalse(x["gates"]["route_ge_85"])
        self.assertFalse(x["governance"]["historical_validation_authorized"])
        self.assertFalse(x["governance"]["production_promotion_authorized"])
        self.assertFalse(x["governance"]["post_preregistration_tuning_allowed"])

    def test_history_has_unique_effective_month(self):
        rows = self.history["history"]
        months = [x["effective_month"] for x in rows]
        self.assertEqual(len(months), len(set(months)))
        self.assertIn("202609", months)


if __name__ == "__main__":
    unittest.main()
