from __future__ import annotations
import json, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
PATH=ROOT/"research"/"market_top_route_a_ng2_failure_diagnostic.json"

class NG2FailureDiagnosticEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.x=json.loads(PATH.read_text(encoding="utf-8"))

    def test_ng2_rejection_remains_locked(self):
        self.assertEqual(self.x["ng2_decision_locked"],"REJECT_NG2_TOP_ROUTE")
        self.assertFalse(self.x["formula_changed"])
        self.assertEqual(self.x["counts"]["ng2_armed_months"],0)

    def test_early_sample_percentile_artifact_is_visible(self):
        self.assertTrue(self.x["early_sample_artifact"]["present"])
        self.assertEqual(self.x["maxima"]["max_route_ng2"]["effective_month"],"195311")
        self.assertEqual(self.x["maxima"]["max_route_ng2"]["financial_lead_gap_score"],100.0)

    def test_2007_is_not_misrepresented_as_ng2_pass(self):
        x=self.x["hypothesis_generation_cases"]["2007-11"]
        self.assertGreater(x["route_a_ng1"],85)
        self.assertLess(x["route_a_ng2"],85)

    def test_no_unused_historical_holdout_is_claimed(self):
        self.assertFalse(self.x["conclusion"]["historical_validation_remaining"])

if __name__=="__main__":
    unittest.main()
