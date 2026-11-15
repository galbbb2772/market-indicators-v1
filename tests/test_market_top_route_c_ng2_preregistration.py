from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIAG = ROOT / "research" / "market_top_route_c_ng1_component_diagnostic.json"
PREREG = ROOT / "research" / "market_top_route_c_ng2_preregistration.json"


class RouteCNG2PreregistrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.diag = json.loads(DIAG.read_text(encoding="utf-8"))
        cls.pre = json.loads(PREREG.read_text(encoding="utf-8"))

    def test_ng1_diagnostic_cannot_be_called_validation(self):
        self.assertEqual(self.diag["status"], "HYPOTHESIS_GENERATION_ONLY")
        self.assertFalse(
            self.diag["conclusion"]["historical_validation_authorized"]
        )

    def test_ng2_is_prospective_only(self):
        self.assertEqual(
            self.pre["status"],
            "PREREGISTERED_PROSPECTIVE_ONLY",
        )
        self.assertFalse(self.pre["historical_validation_authorized"])
        self.assertFalse(self.pre["post_preregistration_tuning_allowed"])
        self.assertFalse(self.pre["legacy_route_c_recovery"])

    def test_formula_and_boundary_are_frozen(self):
        f = self.pre["frozen_formula"]
        self.assertEqual(f["route_c_ng2_score"], "Route_C_NG1")
        self.assertEqual(f["handoff_gate_min"], 0.40)
        self.assertEqual(f["route_threshold"], 85.0)
        self.assertEqual(f["effective_history_months_min"], 120)
        self.assertEqual(
            self.pre["prospective_boundary"]["first_countable_effective_month"],
            "2027-01",
        )

    def test_no_direct_trigger_is_authorized(self):
        self.assertFalse(self.pre["direct_trigger_authorized"])


if __name__ == "__main__":
    unittest.main()
