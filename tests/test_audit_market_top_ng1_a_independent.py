from __future__ import annotations

import unittest

from audit_market_top_ng1_a_independent import (
    compounded,
    expanding_pct,
    parse_monthly_snapshot,
)


class MarketTopNG1AIndependentAuditTests(unittest.TestCase):
    def test_compounded(self):
        self.assertAlmostEqual(compounded([1.0, -1.0]), -0.01, places=10)

    def test_expanding_percentile_is_current_inclusive(self):
        vals = [1.0, 3.0, 2.0]
        self.assertAlmostEqual(expanding_pct(vals, 2), 200.0 / 3.0, places=10)

    def test_monthly_snapshot_parser_ignores_missing_values(self):
        lines = ["observation_date,BAA"]
        for year in range(1953, 2000):
            for month in range(1, 13):
                value = "." if (year == 1960 and month == 2) else "4.00"
                lines.append(f"{year:04d}-{month:02d}-01,{value}")
        s = parse_monthly_snapshot("\n".join(lines), "BAA")
        self.assertGreater(len(s), 500)
        self.assertNotIn("1960-02-01", s.index.astype(str).tolist())
        self.assertEqual(float(s.loc["1953-04-01"]), 4.0)


if __name__ == "__main__":
    unittest.main()
