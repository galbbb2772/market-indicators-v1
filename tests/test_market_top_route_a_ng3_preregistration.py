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
        self.assertEqual(
            self.x["prospective"]["source_temporality_for_first_countable"],
            "SOURCE_MONTH_STRADDLES_PREREGISTRATION",
        )
        self.assertFalse(
            self.x["prospective"][
                "first_countable_all_source_months_fully_post_preregistration"
            ]
        )
        self.assertTrue(
            self.x["prospective"][
                "first_countable_signal_unknown_at_preregistration"
            ]
        )
        self.assertEqual(
            self.x["prospective"][
                "first_fully_post_preregistration_source_effective_month"
            ],
            "202701",
        )
        self.assertFalse(
            self.x["prospective"]["clarification_model_change"]
        )

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
