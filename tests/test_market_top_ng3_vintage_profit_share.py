from __future__ import annotations

import math
import unittest

from audit_market_top_ng3_vintage_profit_share import HISTORICAL_VINTAGES


class MarketTopNG3VintageProfitShareTests(unittest.TestCase):
    def test_1976_q1_frozen_historical_ratio(self):
        x = HISTORICAL_VINTAGES["1976Q1_in_Apr1976_SCB"]
        share = x["unit_profit"] / x["price_per_unit"]
        self.assertTrue(math.isclose(share, 0.10108024691358025, rel_tol=0, abs_tol=1e-15))

    def test_1987_q4_frozen_historical_ratio(self):
        x = HISTORICAL_VINTAGES["1987Q4_in_Mar1988_SCB"]
        share = x["unit_profit"] / x["price_per_unit"]
        self.assertTrue(math.isclose(share, 0.09617097061442564, rel_tol=0, abs_tol=1e-15))

    def test_concepts_are_not_silently_relabelled(self):
        for x in HISTORICAL_VINTAGES.values():
            self.assertIn("iva", x["concept"].lower())
            self.assertIn("capital consumption", x["concept"])


if __name__ == "__main__":
    unittest.main()
