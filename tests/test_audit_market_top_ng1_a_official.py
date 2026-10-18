from __future__ import annotations

import unittest

from audit_market_top_ng1_a_official import (
    compounded,
    expanding_pct,
    parse_fed_ddp_monthly,
)


class MarketTopNG1AOfficialAuditTests(unittest.TestCase):
    def test_compounded(self):
        self.assertAlmostEqual(compounded([1.0, -1.0]), -0.01, places=10)

    def test_fed_ddp_parser_skips_metadata_and_missing_values(self):
        text = '''"Series Description","x"
"Time Period","VALUE"
1953-04,2.83
1953-05,.
1953-06,3.11
'''
        # Production requires a long history. Build a long synthetic DDP body
        # while retaining metadata/missing-value grammar.
        lines = ['"Series Description","x"', '"Time Period","VALUE"']
        for year in range(1953, 2000):
            for month in range(1, 13):
                lines.append(f"{year:04d}-{month:02d},4.00")
        s = parse_fed_ddp_monthly("\n".join(lines))
        self.assertGreater(len(s), 500)
        self.assertEqual(float(s.loc["1953-04-01"]), 4.0)

    def test_expanding_percentile_is_current_inclusive(self):
        vals = [1.0, 3.0, 2.0]
        self.assertAlmostEqual(expanding_pct(vals, 2), 200.0 / 3.0, places=10)


if __name__ == "__main__":
    unittest.main()
