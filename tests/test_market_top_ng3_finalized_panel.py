from __future__ import annotations

import unittest

from research.build_market_top_ng3_finalized_panel_1986_1988 import (
    add_months,
    consensus,
)


class MarketTopNG3FinalizedPanelTests(unittest.TestCase):
    def test_add_months_crosses_year(self):
        self.assertEqual(add_months(1988, 10, 4), (1989, 2))
        self.assertEqual(add_months(1988, 12, 7), (1989, 7))

    def test_consensus_rejects_single_ocr_outlier(self):
        x = consensus([
            ("1986-05", -0.7),
            ("1986-06", -0.7),
            ("1986-07", -7.0),
            ("1986-08", -0.7),
        ])
        self.assertEqual(x["status"], "CONSENSUS")
        self.assertEqual(x["value"], -0.7)
        self.assertEqual(x["support"], 3)

    def test_consensus_requires_two_matching_vintages(self):
        x = consensus([
            ("1988-11", 0.4),
            ("1988-12", 0.5),
        ])
        self.assertEqual(x["status"], "NO_CONSENSUS")
        self.assertIsNone(x["value"])


if __name__ == "__main__":
    unittest.main()
