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

    def test_wayback_exact_vintage_gap_is_explicit(self):
        v = self.data["vintage_robustness"]["wayback"]
        self.assertEqual(
            v["status"],
            "NO_PRE_CUTOFF_SNAPSHOT_WITH_202111",
        )
        self.assertTrue(v["archive_access_worked"])
        self.assertEqual(v["latest_usable_last_month"], "2021-02")

    def test_forward_freshness_and_release_hardening_are_recorded(self):
        f = self.data["forward_shadow"]["freshness"]
        self.assertEqual(f["status"], "PASS")
        self.assertLessEqual(f["market_lag_days"], f["limits"]["market_days"])
        self.assertLessEqual(f["dgs2_lag_days"], f["limits"]["dgs2_days"])
        self.assertGreaterEqual(f["walcl_lag_days"], 2)
        self.assertLessEqual(f["walcl_lag_days"], f["limits"]["walcl_days"])
        self.assertIn(
            "H.4.1 release-aware",
            self.data["forward_shadow"]["walcl_eod_semantics"],
        )

    def test_shiller_exact_vintage_gap_and_cross_vintage_pass_are_both_preserved(self):
        s = self.data["vintage_robustness"]["shiller_wayback"]
        self.assertFalse(s["exact_2022_01_03_valuation_vintage_recovered"])
        self.assertEqual(s["latest_usable_last_month"], "2021-09")
        self.assertGreater(s["route_b_with_official_2022_size"], 85)
        self.assertGreater(s["route_b_with_lower_current_size"], 85)

        b = self.data["vintage_robustness"]["failure_boundaries"]
        self.assertGreater(b["actual_policy_shock"], b[
            "critical_policy_shock_with_archived_valuation_and_lower_current_size"
        ])
        self.assertGreater(b["policy_margin"], 0)

    def test_policyshock_primary_source_pit_chain(self):
        p = self.data["policyshock_primary_source_pit"]
        self.assertEqual(p["status"], "PASS_PRIMARY_SOURCE_PIT_CHAIN")
        self.assertTrue(p["strict_live_verification_passed"])
        self.assertEqual(p["treasury"]["latest_2y_pct"], 0.73)
        self.assertEqual(p["treasury"]["anchor_2y_pct"], 0.25)
        self.assertIn(
            "NOT_ARCHIVED_JAN3_BYTES",
            p["treasury"]["evidence_level"],
        )
        self.assertEqual(
            p["h41"]["evidence_level"],
            "DATED_OFFICIAL_RELEASE_PAGES",
        )
        self.assertEqual(
            [x["total_assets_millions"] for x in p["h41"]["releases"]],
            [8078544.0, 8447981.0, 8757460.0],
        )
        self.assertAlmostEqual(
            p["policy_shock"],
            74.38861925775049,
            places=10,
        )
        c = p["conservative_cross_vintage_route_b"]
        self.assertTrue(c["pass"])
        self.assertGreater(c["route_b"], c["threshold"])
        self.assertGreater(c["policy_margin"], 0)

    def test_2022_dates_are_locked(self):
        x = self.data["frozen_conclusions"]
        self.assertEqual(x["2022_policy_arm_date"], "2022-01-03")
        self.assertEqual(x["2022_price_breakdown_v24r_date"], "2022-01-20")
        self.assertEqual(
            x["accepted_historical_2022_label_remains"],
            "2021-10 EARLY_BREADTH",
        )

    def test_scope_audit_separates_scoring_from_presentation(self):
        s = self.data["scope_audit"]
        self.assertEqual(s["production_scoring_effect"], "none")
        self.assertFalse(s["market_model_v2_core_modified"])
        self.assertFalse(s["production_market_model_current_json_modified"])
        self.assertIn("docs/index.html", s["presentation_effect_if_merged"])

    def test_pit_uncertainty_budget_is_narrow_pass(self):
        x = self.data["vintage_robustness"]["pit_uncertainty_budget"]
        self.assertEqual(x["status"], "PASS_BUT_NARROW_MARGIN")
        self.assertGreater(x["conservative_route_b"], x["threshold"])
        self.assertLess(x["score_margin"], 0.5)
        self.assertLess(x["three_inputs_equal_failure_drop_pct_each"], 0.5)
        self.assertGreater(x["one_input_failure_drop_pct"], 1.0)

    def test_2022_numerical_input_chain_is_closed(self):
        x = self.data["route_b_2022_evidence_closure"]
        self.assertEqual(
            x["status"],
            "NUMERICAL_INPUT_CHAIN_CLOSED_DELIVERY_TIMESTAMP_GAP",
        )
        self.assertTrue(x["route_b"]["pass"])
        self.assertGreater(x["route_b"]["score"], x["route_b"]["threshold"])
        self.assertEqual(
            x["size_weakness"]["content"],
            "OFFICIAL_DEC2021_FF_VINTAGE_RECOVERED",
        )
        self.assertEqual(x["size_weakness"]["crsp_database"], "202111")
        self.assertFalse(
            x["unresolved_delivery_provenance"][
                "exact_jan3_ff_archive_wayback_capture"
            ]
        )

    def test_route_a_and_c_remain_unresolved(self):
        by_component = {x["component"]: x for x in self.data["unresolved"]}
        self.assertEqual(by_component["Original Route_A"]["status"], "UNRESOLVED")
        self.assertEqual(by_component["Original Route_C"]["status"], "UNRESOLVED")
        self.assertTrue(self.data["frozen_conclusions"]["do_not_tune_failed_ac_candidates"])


if __name__ == "__main__":
    unittest.main()
