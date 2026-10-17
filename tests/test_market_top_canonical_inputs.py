from __future__ import annotations

import unittest

from market_top_canonical_inputs import (
    compounded_return_pct,
    expanding_percentile_current,
    size_block_from_smb_6m,
    size_weakness_history,
    valuation_history,
)
from policyshock_v211 import route_b


class CanonicalRouteBInputTests(unittest.TestCase):
    def test_expanding_percentile_is_current_inclusive(self):
        self.assertEqual(expanding_percentile_current([1, 2, 3, 4]), 100.0)
        self.assertAlmostEqual(expanding_percentile_current([1, 3, 2]), 2 / 3 * 100, places=12)

    def test_smb_block_is_negative_compounded_smb(self):
        smb = [-1.0, -1.0, -1.0, -1.0, -1.0, -1.0]
        self.assertGreater(size_block_from_smb_6m(smb), 0.0)
        self.assertAlmostEqual(
            size_block_from_smb_6m(smb),
            -compounded_return_pct(smb),
            places=12,
        )

    def test_size_history_only_starts_after_six_months(self):
        out = size_weakness_history([1, 2, 3, 4, 5, 6, 7])
        self.assertEqual(out[:5], [None] * 5)
        self.assertIsNotNone(out[5])
        self.assertIsNotNone(out[6])

    def test_valuation_history_is_expanding(self):
        got = valuation_history([10, 20, 15])\n        self.assertEqual(got[:2], [100.0, 100.0])\n        self.assertAlmostEqual(got[2], 2/3*100, places=12)

    def test_2022_conservative_publication_lag_route_b(self):
        rb = route_b(
            98.58072146658782,
            74.3886192578,
            84.73684210526316,
        )
        self.assertAlmostEqual(rb, 85.3342917569589, places=8)
        self.assertGreater(rb, 85.0)

    def test_current_2026_policy_route_is_not_armed(self):
        rb = route_b(
            98.9136649514008,
            62.744246712042916,
            45.4469507101086,
        )
        self.assertAlmostEqual(rb, 65.58104271810248, places=8)
        self.assertLess(rb, 85.0)


if __name__ == "__main__":
    unittest.main()
