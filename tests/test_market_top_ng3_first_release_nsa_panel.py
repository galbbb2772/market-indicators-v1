from __future__ import annotations

import unittest

from research.build_market_top_ng3_first_release_nsa_panel_1986_1988 import (
    parse_table1_aggregate,
)


SAMPLE = """Table 1. Producer price indexes and percent changes by stage of processing
(1967=100)
Finished goods                                      100.000 291.8 295.0 296.3 2.6 0.4 0.4 0.7 0.3
   Finished consumer goods                           75.548 286.2 290.3 292.0 2.8 .6 .5 .9 .3
Intermediate materials, supplies and components.    100.000 307.0 310.9 312.7 2.0 .6 .3 .3 .5
   Materials and components for manufacturing        49.995 297.8 301.3 303.2 2.6 .6 .3 .5 .6
Table 2. Producer price indexes and percent changes for selected commodity groupings by stage of processing
"""


class MarketTopNG3FirstReleaseNSAPanelTests(unittest.TestCase):
    def test_finished_goods_aggregate(self):
        x = parse_table1_aggregate(SAMPLE, "finished_goods")
        self.assertEqual(x["status"], "PARSED")
        self.assertEqual(x["relative_importance"], 100.0)
        self.assertEqual(x["january_level_nsa"], 291.8)
        self.assertEqual(x["previous_month_level_nsa"], 295.0)
        self.assertEqual(x["current_month_level_nsa"], 296.3)
        self.assertEqual(x["yoy_nsa_pct"], 2.6)
        self.assertEqual(x["mom_nsa_pct"], 0.4)

    def test_intermediate_goods_aggregate(self):
        x = parse_table1_aggregate(SAMPLE, "intermediate_goods")
        self.assertEqual(x["status"], "PARSED")
        self.assertEqual(x["relative_importance"], 100.0)
        self.assertEqual(x["january_level_nsa"], 307.0)
        self.assertEqual(x["previous_month_level_nsa"], 310.9)
        self.assertEqual(x["current_month_level_nsa"], 312.7)
        self.assertEqual(x["yoy_nsa_pct"], 2.0)
        self.assertEqual(x["mom_nsa_pct"], 0.6)

    def test_does_not_take_subcomponent_row(self):
        x = parse_table1_aggregate(SAMPLE, "finished_goods")
        self.assertNotEqual(x["current_month_level_nsa"], 292.0)

    def test_invalid_label_fails_closed(self):
        with self.assertRaises(ValueError):
            parse_table1_aggregate(SAMPLE, "unknown")


if __name__ == "__main__":
    unittest.main()
