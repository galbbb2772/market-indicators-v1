from __future__ import annotations
import json, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
PATH=ROOT/"research"/"market_top_route_a_ng3_preregistration.json"

class NG3PreregistrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.x=json.loads(PATH.read_text(encoding="utf-8"))

    def test_prospective_only_boundary(self):
        self.assertEqual(self.x["status"],"PREREGISTERED_PROSPECTIVE_ONLY")
        self.assertEqual(self.x["prospective"]["first_countable_effective_month"],"202612")
        self.assertEqual(self.x["prospective"]["validation_status"],"PROSPECTIVE_VALIDATION_PENDING")

    def test_phase_gate_is_frozen(self):
        self.assertEqual(self.x["phase_gate"]["minimum_effective_history_months"],120)
        self.assertEqual(self.x["phase_gate"]["minimum_financial_lead_gap_raw"],10.0)
        self.assertEqual(self.x["state_gate"]["route_threshold"],85.0)

    def test_lead_gap_is_gate_not_multiplier(self):
        self.assertEqual(self.x["formula"]["route_a_ng3_score"],"route_a_ng1")

    def test_no_historical_validation_or_retune_claim(self):
        self.assertFalse(self.x["post_preregistration_tuning_allowed"])
        self.assertFalse(self.x["legacy_recovery"])
        self.assertEqual(self.x["production_effect"],"none")

if __name__=="__main__":
    unittest.main()
