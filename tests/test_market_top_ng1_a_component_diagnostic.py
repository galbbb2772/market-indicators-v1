from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
PATH=ROOT/"research"/"market_top_ng1_a_component_diagnostic.json"


class NG1AComponentDiagnosticEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data=json.loads(PATH.read_text(encoding="utf-8"))

    def test_no_monotonic_reweighting_is_authorized(self):
        self.assertEqual(
            self.data["conclusions"]["monotonic_reweighting"],
            "REJECTED_AS_NG2_DIRECTION",
        )
        a=self.data["cases"]["1998-11"]
        b=self.data["cases"]["2007-11"]
        for key in (
            "spread_shock_score",
            "size_weakness_score",
            "portfolio_exhaustion_score",
        ):
            self.assertGreater(a[key],b[key])

    def test_known_cases_are_hypothesis_generation_only(self):
        self.assertTrue(self.data["hypothesis_generation_only"])
        self.assertIn(
            "may never be counted as independent validation",
            self.data["conclusions"]["validation_rule"],
        )

    def test_financial_lead_gap_fingerprint(self):
        self.assertGreater(self.data["cases"]["2007-11"]["finance_lead_gap"],10)
        for key in ("1998-11","2012-02","2025-07","2025-09"):
            self.assertLess(self.data["cases"][key]["finance_lead_gap"],10)


if __name__=="__main__":
    unittest.main()
