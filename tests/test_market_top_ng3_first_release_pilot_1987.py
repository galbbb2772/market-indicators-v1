from __future__ import annotations

import unittest

from validate_market_top_ng3_first_release_pilot_1987 import validate


class MarketTopNG3FirstReleasePilot1987Tests(unittest.TestCase):
    def test_frozen_source_engineering_contract(self):
        x = validate()
        self.assertEqual(x["status"], "PASS")
        self.assertTrue(all(x["checks"].values()))

    def test_january_revision_case(self):
        x = validate()["derived"]["1987-01"]
        self.assertEqual(x["pre_revision"]["finished_goods_mom_pct"], 0.6)
        self.assertEqual(x["pre_revision"]["intermediate_materials_mom_pct"], 0.9)
        self.assertEqual(x["four_month_revision"]["finished_goods_mom_pct"], 0.4)
        self.assertEqual(x["four_month_revision"]["intermediate_materials_mom_pct"], 0.9)
        self.assertAlmostEqual(x["revision_delta_pp"]["finished_goods"], -0.2)
        self.assertEqual(x["revision_delta_pp"]["intermediate_materials"], 0.0)

    def test_may_revision_case(self):
        x = validate()["derived"]["1987-05"]
        self.assertEqual(x["first_published"]["finished_goods_mom_pct"], 0.3)
        self.assertEqual(x["first_published"]["intermediate_materials_mom_pct"], 0.5)
        self.assertEqual(x["period_finalized"]["finished_goods_mom_pct"], -0.1)
        self.assertEqual(x["period_finalized"]["intermediate_materials_mom_pct"], 0.5)
        self.assertEqual(x["revision_delta_pp"]["finished_goods"], -0.4)
        self.assertEqual(x["revision_delta_pp"]["intermediate_materials"], 0.0)

    def test_may_level_implied_rounding(self):
        implied = validate()["derived"]["1987-05"]["first_publication_level_implied"]
        self.assertEqual(round(implied["finished_goods_mom_pct"], 1), 0.3)
        self.assertEqual(round(implied["intermediate_materials_mom_pct"], 1), 0.5)


if __name__ == "__main__":
    unittest.main()
