from __future__ import annotations

import unittest

from audit_shiller_wayback_202201 import (
    CUTOFF,
    ORIGINAL_URLS,
    TARGET_MONTH,
    _date_to_ym,
    expanding_percentile_current,
)


class ShillerWaybackAuditTests(unittest.TestCase):
    def test_cutoff_and_target_are_frozen(self):
        self.assertEqual(CUTOFF, "20220103235959")
        self.assertEqual(TARGET_MONTH, "202111")

    def test_both_http_and_https_yale_urls_are_queried(self):
        self.assertEqual(len(ORIGINAL_URLS), 2)
        self.assertTrue(any(x.startswith("http://") for x in ORIGINAL_URLS))
        self.assertTrue(any(x.startswith("https://") for x in ORIGINAL_URLS))

    def test_shiller_decimal_dates_parse_to_months(self):
        self.assertEqual(_date_to_ym(2021.11), "202111")
        self.assertEqual(_date_to_ym(1871.01), "187101")

    def test_expanding_percentile_is_current_inclusive(self):
        self.assertEqual(expanding_percentile_current([10, 20, 30]), 100.0)
        self.assertAlmostEqual(
            expanding_percentile_current([10, 30, 20]),
            2 / 3 * 100,
            places=12,
        )


if __name__ == "__main__":
    unittest.main()
