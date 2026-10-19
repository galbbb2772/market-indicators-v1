from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
PATH=ROOT/"research"/"market_top_route_a_ng2_pre1993_holdout.json"

class RouteANG2HoldoutEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.x=json.loads(PATH.read_text(encoding="utf-8"))

    def test_ng2_is_rejected_not_promoted(self):
        self.assertEqual(cls_decision := self.x["decision"], "REJECT_NG2_TOP_ROUTE")
        self.assertEqual(self.x["decision_metrics"]["evaluable_episodes"], 0)

    def test_holdout_was_pre1993_and_no_retune_is_allowed(self):
        self.assertEqual(self.x["sample"]["last_effective_month"], "199212")
        self.assertFalse(self.x["post_validation_tuning_allowed"])

    def test_research_only(self):
        self.assertTrue(self.x["research_only"])
        self.assertEqual(self.x["production_effect"], "none")

if __name__=="__main__":
    unittest.main()
