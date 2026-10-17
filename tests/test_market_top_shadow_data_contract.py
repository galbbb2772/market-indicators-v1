from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CURRENT = ROOT / "docs" / "data" / "market_top_shadow_current.json"
HISTORY = ROOT / "docs" / "data" / "market_top_shadow_history.json"


class MarketTopShadowDataContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.current = json.loads(CURRENT.read_text(encoding="utf-8"))
        cls.history = json.loads(HISTORY.read_text(encoding="utf-8"))

    def test_seed_snapshot_is_research_only(self):
        x = self.current
        self.assertTrue(x["research_only"])
        self.assertEqual(x["production_effect"], "none")
        self.assertFalse(x["full_legacy_model"]["pressure_authoritative"])
        self.assertEqual(x["full_legacy_model"]["route_a"], "UNRESOLVED")
        self.assertEqual(x["full_legacy_model"]["route_c"], "UNRESOLVED")

    def test_seed_route_b_and_price_state_match_live_dry_run(self):
        x = self.current
        self.assertEqual(x["asof"], "2026-10-16")
        self.assertAlmostEqual(x["route_b"]["score"], 65.58104271810248, places=8)
        self.assertFalse(x["route_b"]["pressure_pass"])
        self.assertTrue(x["route_b"]["top_location_gate"])
        self.assertAlmostEqual(
            x["price_confirmation"]["t_v24r"],
            13.775261410890886,
            places=8,
        )
        self.assertFalse(x["price_confirmation"]["price_breakdown_v24r"])
        self.assertEqual(x["policy_path"]["state"], "IDLE")

    def test_seed_sources_record_failover(self):
        s = self.current["sources"]
        self.assertEqual(
            s["dgs2"],
            "U.S. Treasury Daily Treasury Par Yield Curve Rates",
        )
        self.assertIn("static GitHub mirror", s["walcl"])
        self.assertEqual(s["fama_french"], "Ken French Data Library")

    def test_history_contains_unique_asof_rows(self):
        rows = self.history["history"]
        dates = [x["asof"] for x in rows]
        self.assertEqual(len(dates), len(set(dates)))
        self.assertIn("2026-10-16", dates)


if __name__ == "__main__":
    unittest.main()
