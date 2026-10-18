from __future__ import annotations

import unittest

from audit_market_top_ng1_a_official import expanding_pct, compounded


class MarketTopNG1AOfficialAuditTests(unittest.TestCase):
    def test_compounded(self):
        self.assertAlmostEqual(compounded([1.0, -1.0]), -0.01, places=10)

    def test_expanding_percentile_is_current_inclusive(self):
        vals = [1.0, 3.0, 2.0]
        self.assertAlmostEqual(expanding_pct(vals, 2), 200.0 / 3.0, places=10)


if __name__ == "__main__":
    unittest.main()
