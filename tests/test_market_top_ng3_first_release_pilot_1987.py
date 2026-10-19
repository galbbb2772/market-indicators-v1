from __future__ import annotations

import unittest

from validate_market_top_ng3_first_release_pilot_1987 import validate


class MarketTopNG3FirstReleasePilot1987Tests(unittest.TestCase):
    def test_frozen_source_engineering_contract(self):
        x = validate()
        self.assertEqual(x["status"], "PASS")
        self.assertTrue(all(x["checks"].values()))

    def test_first_publication_and_finalized_values(self):
        x = validate()
        first = x["derived"]["first_published"]
        final = x["derived"]["period_finalized"]
        delta = x["derived"]["revision_delta_pp"]

        self.assertEqual(first["finished_goods_mom_pct"], 0.3)
        self.assertEqual(first["intermediate_materials_mom_pct"], 0.5)
        self.assertEqual(final["finished_goods_mom_pct"], -0.1)
        self.assertEqual(final["intermediate_materials_mom_pct"], 0.5)
        self.assertEqual(delta["finished_goods"], -0.4)
        self.assertEqual(delta["intermediate_materials"], 0.0)

    def test_first_publication_levels_still_reproduce_reported_rounding(self):
        x = validate()
        implied = x["derived"]["first_publication_level_implied"]
        self.assertEqual(round(implied["finished_goods_mom_pct"], 1), 0.3)
        self.assertEqual(round(implied["intermediate_materials_mom_pct"], 1), 0.5)


if __name__ == "__main__":
    unittest.main()
