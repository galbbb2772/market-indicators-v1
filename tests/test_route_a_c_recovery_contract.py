from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "research" / "route_a_c_recovery_status.json"


class RouteACRecoveryContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads(PATH.read_text(encoding="utf-8"))

    def test_outer_architecture_is_preserved(self):
        self.assertEqual(cls := self.data["route_a"]["structural_formula"], "sqrt(Credit * Breadth)")
        self.assertEqual(self.data["route_c"]["structural_formula"], "sqrt(Valuation * ConcentrationBreadth)")

    def test_unresolved_routes_cannot_change_state(self):
        live = self.data["live_contract"]
        self.assertFalse(live["route_a_can_change_state"])
        self.assertFalse(live["route_c_can_change_state"])
        self.assertFalse(live["full_pressure_authoritative"])
        self.assertEqual(live["overall_state"], "PARTIAL_ROUTE_COVERAGE")

    def test_current_resolved_components_are_preserved(self):
        live = self.data["live_contract"]
        self.assertAlmostEqual(live["route_b_current_authoritative"], 65.58104271810248, places=8)
        self.assertEqual(live["route_b_state"], "NOT_ARMED")
        self.assertFalse(live["price_breakdown_current"])


if __name__ == "__main__":
    unittest.main()
