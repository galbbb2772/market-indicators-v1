from __future__ import annotations

import unittest
from unittest.mock import patch

import pandas as pd

from audit_shiller_wayback_202201 import (
    CUTOFF,
    ORIGINAL_URLS,
    TARGET_MONTH,
    _date_to_ym,
    expanding_percentile_current,
    parse_shiller_xls,
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

    def test_parser_never_uses_excess_cape_yield_as_cape(self):
        cols = [f"c{i}" for i in range(13)]
        cols[0] = "Date"
        cols[10] = "Excess CAPE Yield"
        cols[12] = "CAPE"

        rows = []
        for y in range(1920, 2022):
            for m in range(1, 13):
                vals = [0.0] * 13
                vals[0] = y + m / 100
                vals[10] = 0.03
                vals[12] = 20.0 + ((y - 1920) % 20)
                rows.append(vals)
        df = pd.DataFrame(rows, columns=cols)

        with patch("pandas.read_excel", return_value=df):
            parsed = parse_shiller_xls(b"fake workbook bytes")

        self.assertGreater(parsed[-1]["cape"], 5.0)
        self.assertNotAlmostEqual(parsed[-1]["cape"], 0.03, places=6)

    def test_parser_rejects_yield_scale_if_wrong_column_is_selected(self):
        cols = [f"c{i}" for i in range(13)]
        cols[0] = "Date"
        cols[12] = "Excess CAPE Yield"

        rows = []
        for y in range(1920, 2022):
            for m in range(1, 13):
                vals = [0.0] * 13
                vals[0] = y + m / 100
                vals[12] = 0.03
                rows.append(vals)
        df = pd.DataFrame(rows, columns=cols)

        with patch("pandas.read_excel", return_value=df):
            with self.assertRaisesRegex(ValueError, "CAPE scale is implausible"):
                parse_shiller_xls(b"fake workbook bytes")

    def test_expanding_percentile_is_current_inclusive(self):
        self.assertEqual(expanding_percentile_current([10, 20, 30]), 100.0)
        self.assertAlmostEqual(
            expanding_percentile_current([10, 30, 20]),
            2 / 3 * 100,
            places=12,
        )


if __name__ == "__main__":
    unittest.main()
