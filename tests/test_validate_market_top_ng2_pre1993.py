from __future__ import annotations

import unittest

import pandas as pd

from validate_market_top_ng2_pre1993 import (
    add_months,
    classify_outcome,
)


class RouteANG2HoldoutUnitTests(unittest.TestCase):
    def test_month_arithmetic(self):
        self.assertEqual(add_months("199212", 1), "199301")
        self.assertEqual(add_months("199301", -2), "199211")

    def test_major_top_classification_uses_anchor_loss(self):
        idx = pd.bdate_range("1987-01-02", periods=300)
        s = pd.Series(100.0, index=idx)
        anchor = idx[0]
        s.iloc[1:253] = 102.0
        s.iloc[100] = 80.0
        x = classify_outcome(s, anchor)
        self.assertEqual(x["classification"], "MAJOR_TOP")

    def test_later_peak_drawdown_does_not_rescue_clear_false(self):
        idx = pd.bdate_range("1985-01-02", periods=300)
        s = pd.Series(100.0, index=idx)
        anchor = idx[0]
        path = []
        for i in range(1, 253):
            if i < 180:
                path.append(100.0 + 0.15 * i)
            else:
                path.append(126.0 - 0.12 * (i - 180))
        s.iloc[1:253] = path
        x = classify_outcome(s, anchor)
        self.assertGreater(x["worst_return_from_anchor_pct"], -7.5)
        self.assertGreater(x["forward_return_pct"], 0.0)
        self.assertEqual(x["classification"], "CLEAR_FALSE")


if __name__ == "__main__":
    unittest.main()
