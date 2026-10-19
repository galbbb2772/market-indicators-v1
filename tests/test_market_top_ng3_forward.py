from __future__ import annotations

import unittest
from datetime import datetime, timezone

import pandas as pd

from market_top_ng3_forward import (
    add_months,
    completed_month_ym,
    merge_pinned_with_extension,
)


class NG3ForwardUnitTests(unittest.TestCase):
    def test_completed_month_never_uses_partial_current_month(self):
        now=datetime(2026,10,19,tzinfo=timezone.utc)
        self.assertEqual(completed_month_ym(now),"202609")

    def test_month_arithmetic(self):
        self.assertEqual(add_months("202612",-2),"202610")
        self.assertEqual(add_months("202612",-1),"202611")

    def test_credit_extension_preserves_pinned_history(self):
        base=pd.Series(
            [4.0,4.1,4.2],
            index=pd.to_datetime(["2025-12-01","2026-01-01","2026-02-01"]),
        )
        ext=pd.Series(
            [4.1,4.2,4.3,4.4],
            index=pd.to_datetime(
                ["2026-01-01","2026-02-01","2026-03-01","2026-04-01"]
            ),
        )
        out=merge_pinned_with_extension(base,ext)
        self.assertEqual(float(out.loc[pd.Timestamp("2025-12-01")]),4.0)
        self.assertEqual(float(out.loc[pd.Timestamp("2026-04-01")]),4.4)

    def test_credit_extension_fails_on_overlap_mismatch(self):
        base=pd.Series(
            [4.1,4.2],
            index=pd.to_datetime(["2026-01-01","2026-02-01"]),
        )
        ext=pd.Series(
            [4.1,9.9,4.3],
            index=pd.to_datetime(
                ["2026-01-01","2026-02-01","2026-03-01"]
            ),
        )
        with self.assertRaises(ValueError):
            merge_pinned_with_extension(base,ext)


if __name__=="__main__":
    unittest.main()
