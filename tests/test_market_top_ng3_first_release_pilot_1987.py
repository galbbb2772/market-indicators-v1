from __future__ import annotations

import unittest

from validate_market_top_ng3_first_release_pilot_1987 import validate


class MarketTopNG3FirstReleasePilot1987Tests(unittest.TestCase):
    def test_frozen_source_engineering_contract(self):
        x = validate()
        self.assertEqual(x["status"], "PASS")
        self.assertTrue(all(x["checks"].values()))

    def test_rounded_first_publication_changes(self):
        x = validate()
        self.assertEqual(round(x["derived"]["finished_goods_mom_pct"], 1), 0.3)
        self.assertEqual(round(x["derived"]["intermediate_materials_mom_pct"], 1), 0.5)


if __name__ == "__main__":
    unittest.main()
