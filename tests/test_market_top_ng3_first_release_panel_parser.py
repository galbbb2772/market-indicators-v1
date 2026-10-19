from __future__ import annotations

import unittest

from research.build_market_top_ng3_first_release_panel_1986_1988 import (\n    parse_first_values,\n    resolve_first_publication,\n)


class MarketTopNG3FirstReleasePanelParserTests(unittest.TestCase):
    def parse(self, text: str, year: int, month: int):
        return parse_first_values(text + " Table A.", year, month)

    def test_1986_may_noun_drop(self):
        x = self.parse(
            "Price Movements May 1986 "
            "The Producer Price Index for Finished Goods increased 0.6 percent "
            "on a seasonally adjusted basis from April to May. "
            "The index for Intermediate Materials, Supplies and Components "
            "continued to fall, although its 0.2-percent drop in May was much "
            "smaller than in any other month so far this year.",
            1986,
            5,
        )
        self.assertEqual(x["finished_goods_mom_sa_pct"], 0.6)
        self.assertEqual(x["intermediate_goods_mom_sa_pct"], -0.2)

    def test_1987_july_lead_statement_without_month_after_match(self):
        x = self.parse(
            "Price Movements July 1987 "
            "The Producer Price Index for Finished Goods moved up 0.2 percent "
            "seasonally adjusted from June to July. "
            "Prices received by producers of intermediate goods climbed "
            "0.8 percent, even more than the advances recorded in other recent months.",
            1987,
            7,
        )
        self.assertEqual(x["finished_goods_mom_sa_pct"], 0.2)
        self.assertEqual(x["intermediate_goods_mom_sa_pct"], 0.8)

    def test_1987_november_zero_finished_goods(self):
        x = self.parse(
            "Price Movements November 1987 "
            "The Producer Price Index for Finished Goods showed no change after "
            "seasonal adjustment from October to November. The index fell 0.2 percent "
            "in October after registering small increases in most other recent months. "
            "The index for intermediate goods increased 0.4 percent following rises "
            "of 0.1 and 0.5 percent in September and October.",
            1987,
            11,
        )
        self.assertEqual(x["finished_goods_mom_sa_pct"], 0.0)
        self.assertEqual(x["intermediate_goods_mom_sa_pct"], 0.4)

    def test_1988_september_rejects_year_over_year_intermediate(self):
        x = self.parse(
            "Price Movements September 1988 "
            "The Producer Price Index for Finished Goods moved up 0.4 percent "
            "seasonally adjusted from August to September. "
            "Prices received by domestic producers of intermediate goods also were "
            "up 0.4 percent in September, the same as the month before. "
            "Over the 12 months ended in September 1988, the Finished Goods Price "
            "Index moved up 2.7 percent. The Intermediate Goods Price Index advanced "
            "5.8 percent from September 1987 to September 1988.",
            1988,
            9,
        )
        self.assertEqual(x["finished_goods_mom_sa_pct"], 0.4)
        self.assertEqual(x["intermediate_goods_mom_sa_pct"], 0.4)

    def test_1988_november_intermediate_advanced(self):
        x = self.parse(
            "Price Movements November 1988 "
            "The Producer Price Index for Finished Goods moved up 0.3 percent from "
            "October to November seasonally adjusted. "
            "The index for intermediate goods, which had also shown no change in "
            "October after rising 0.4 percent in September, advanced 0.5 percent "
            "in November.",
            1988,
            11,
        )
        self.assertEqual(x["finished_goods_mom_sa_pct"], 0.3)
        self.assertEqual(x["intermediate_goods_mom_sa_pct"], 0.5)


if __name__ == "__main__":
    unittest.main()
    def test_complete_table_row_is_primary_on_cross_path_conflict(self):
        x = resolve_first_publication(
            {
                "finished_goods_mom_sa_pct": 0.5,
                "intermediate_goods_mom_sa_pct": 1.3,
            },
            {
                "finished_goods_mom_sa_pct": -0.2,
                "intermediate_goods_mom_sa_pct": 0.8,
            },
        )
        self.assertEqual(x["status"], "TABLE_A_PRIMARY_NARRATIVE_CONFLICT")
        self.assertEqual(x["finished_goods_mom_sa_pct"], -0.2)
        self.assertEqual(x["intermediate_goods_mom_sa_pct"], 0.8)
        self.assertEqual(x["primary_source_path"], "TABLE_A_CURRENT_MONTH_ROW")
        self.assertTrue(x["fg_conflict"])
        self.assertTrue(x["im_conflict"])

    def test_narrative_is_fallback_when_table_row_incomplete(self):
        x = resolve_first_publication(
            {
                "finished_goods_mom_sa_pct": 0.3,
                "intermediate_goods_mom_sa_pct": 0.5,
            },
            {"status": "ROW_NUMERIC_COLUMNS_INCOMPLETE"},
        )
        self.assertEqual(x["status"], "NARRATIVE_RECOVERED")
        self.assertEqual(x["finished_goods_mom_sa_pct"], 0.3)
        self.assertEqual(x["intermediate_goods_mom_sa_pct"], 0.5)


