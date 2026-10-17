from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "research" / "market_top_task2_decision_record.json"


class MarketTopTask2DecisionContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads(PATH.read_text(encoding="utf-8"))

    def test_core_task_pass_is_not_full_legacy_recovery(self):
        self.assertEqual(
            self.data["status"],
            "CORE_TASK_PASS_FORWARD_SHADOW_OPERATIONAL_WITH_LEGACY_PROVENANCE_GAPS",
        )
        self.assertTrue(self.data["frozen_conclusions"]["2022_policy_route_repaired"])
        self.assertFalse(self.data["frozen_conclusions"]["current_full_pressure_authoritative"])

    def test_forward_shadow_is_operational_but_not_full_pressure(self):
        f = self.data["forward_shadow"]
        self.assertEqual(f["status"], "LIVE_DRY_RUN_PASS")
        self.assertAlmostEqual(f["route_b"], 65.58104271810248, places=8)
        self.assertEqual(f["policy_path_state"], "IDLE")
        self.assertFalse(f["full_pressure_authoritative"])

    def test_2022_vintage_robustness(self):
        v = self.data["vintage_robustness"]
        self.assertFalse(v["exact_2022_01_03_monthly_vintage_recovered"])
        self.assertEqual(v["official_july_2022_archive"]["status"], "PASS")
        self.assertGreater(
            v["official_july_2022_archive"]["route_b"],
            v["official_july_2022_archive"]["threshold"],
        )
        self.assertTrue(
            v["cross_version_static_histories"]["all_sampled_variants_pass"]
        )

    def test_2022_dates_are_locked(self):
        x = self.data["frozen_conclusions"]
        self.assertEqual(x["2022_policy_arm_date"], "2022-01-03")
        self.assertEqual(x["2022_price_breakdown_v24r_date"], "2022-01-20")
        self.assertEqual(
            x["accepted_historical_2022_label_remains"],
            "2021-10 EARLY_BREADTH",
        )

    def test_route_a_and_c_remain_unresolved(self):
        by_component = {x["component"]: x for x in self.data["unresolved"]}
        self.assertEqual(by_component["Original Route_A"]["status"], "UNRESOLVED")
        self.assertEqual(by_component["Original Route_C"]["status"], "UNRESOLVED")
        self.assertTrue(self.data["frozen_conclusions"]["do_not_tune_failed_ac_candidates"])


if __name__ == "__main__":
    unittest.main()
