from __future__ import annotations

import unittest

import pandas as pd

from t_v24r import (
    DRAWDOWN_GUARD_PCT,
    T_THRESHOLD,
    dd_score,
    ma_score,
    previous_10_completed_month_ma,
    price_breakdown_gate,
    t_v24r,
)


class TV24RTests(unittest.TestCase):
    def test_preregistered_drawdown_mapping(self):
        self.assertEqual(float(dd_score(1.0)), 0.0)
        self.assertAlmostEqual(float(dd_score(4.0)), 50.0, places=8)
        self.assertEqual(float(dd_score(7.0)), 100.0)

    def test_preregistered_ma_mapping(self):
        self.assertEqual(float(ma_score(100.0, 100.0)), 0.0)
        self.assertAlmostEqual(float(ma_score(98.0, 100.0)), 50.0, places=8)
        self.assertEqual(float(ma_score(96.0, 100.0)), 100.0)

    def test_2022_spy_research_fingerprints(self):
        ma = 437.071
        t_0118 = float(t_v24r(4.442, 456.48999, ma))
        t_0119 = float(t_v24r(5.434, 451.75, ma))
        t_0120 = float(t_v24r(6.481, 446.75, ma))

        self.assertLess(t_0118, T_THRESHOLD)
        self.assertLess(t_0119, T_THRESHOLD)
        self.assertGreater(t_0120, T_THRESHOLD)

        self.assertFalse(bool(price_breakdown_gate(t_0118, 4.442)))
        self.assertFalse(bool(price_breakdown_gate(t_0119, 5.434)))
        self.assertTrue(bool(price_breakdown_gate(t_0120, 6.481)))

    def test_ma_uses_only_completed_prior_months(self):
        idx = pd.to_datetime([
            "2021-03-31","2021-04-30","2021-05-31","2021-06-30","2021-07-30",
            "2021-08-31","2021-09-30","2021-10-29","2021-11-30","2021-12-31",
            "2022-01-03","2022-01-31","2022-02-01",
        ])
        vals = [1,2,3,4,5,6,7,8,9,10,100,200,300]
        s = pd.Series(vals, index=idx, dtype=float)
        ma = previous_10_completed_month_ma(s)

        # January must use Mar-Dec only, not either January observation.
        self.assertAlmostEqual(float(ma.loc["2022-01-03"]), 5.5)
        self.assertAlmostEqual(float(ma.loc["2022-01-31"]), 5.5)

        # February may use January's completed month-end close (=200).
        expected_feb = sum([2,3,4,5,6,7,8,9,10,200]) / 10
        self.assertAlmostEqual(float(ma.loc["2022-02-01"]), expected_feb)

    def test_shallow_drawdown_cannot_confirm_by_itself(self):
        t = float(t_v24r(DRAWDOWN_GUARD_PCT, 100.0, 100.0))
        self.assertLess(t, T_THRESHOLD)


if __name__ == "__main__":
    unittest.main()
