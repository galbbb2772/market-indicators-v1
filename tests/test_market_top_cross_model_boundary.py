from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "research" / "market_top_cross_model_boundary.json"


class MarketTopCrossModelBoundaryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads(PATH.read_text(encoding="utf-8"))

    def test_models_remain_independent(self):
        r = self.data["non_equivalence_rules"]
        self.assertTrue(r["do_not_max_across_models"])
        self.assertTrue(r["do_not_average_scores"])
        self.assertTrue(r["independent_research_routes"])

    def test_route_b_is_live_but_not_full_legacy_pressure(self):
        x = self.data["models"]["route_b_shadow"]
        self.assertEqual(x["current_data_status"], "LIVE_DRY_RUN_VALIDATED")
        self.assertEqual(x["asof"], "2026-10-16")
        self.assertFalse(x["full_legacy_pressure_authoritative"])

    def test_master_top_repository_value_is_seed_only(self):
        x = self.data["models"]["master_top_v218"]
        self.assertEqual(x["latest_repository_payload_status"], "SEED_SNAPSHOT_ONLY")
        self.assertEqual(x["seed_asof"], "2026-10-09")
        self.assertTrue(x["seed_triggered"])

    def test_seed_and_live_must_not_be_called_same_day_comparison(self):
        self.assertTrue(
            self.data["non_equivalence_rules"]["do_not_compare_seed_to_live_as_same_day"]
        )


if __name__ == "__main__":
    unittest.main()
