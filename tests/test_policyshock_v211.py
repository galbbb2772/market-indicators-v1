from __future__ import annotations

import math
import unittest

from policyshock_v211 import (
    ARMED_THRESHOLD,
    compute_policy_shock,
    policy_shock,
    rate_shock,
    route_b,
    taper_shock,
)


class PolicyShockV211Tests(unittest.TestCase):
    def test_rate_shock_frozen_mapping(self):
        self.assertAlmostEqual(rate_shock(0.73, 0.25), 63.3333333333, places=8)
        self.assertEqual(rate_shock(0.35, 0.25), 0.0)   # +10 bp
        self.assertEqual(rate_shock(0.95, 0.25), 100.0) # +70 bp

    def test_taper_shock_2022_strict_pit(self):
        # Released observations available for the 2022-01-03 strict-PIT test.
        t = taper_shock(8.757460, 8.447981, 8.078544)
        self.assertAlmostEqual(t, 90.9715481444, places=8)

    def test_2022_strict_pit_golden(self):
        out = compute_policy_shock(
            dgs2_latest_pct=0.73,
            dgs2_6m_ago_pct=0.25,
            walcl_now=8.757460,
            walcl_13w_ago=8.447981,
            walcl_26w_ago=8.078544,
        )
        self.assertAlmostEqual(out.rate_shock, 63.3333333333, places=8)
        self.assertAlmostEqual(out.taper_shock, 90.9715481444, places=8)
        self.assertAlmostEqual(out.policy_shock, 74.3886192578, places=8)

        rb = route_b(97.9, out.policy_shock, 95.9)
        self.assertAlmostEqual(rb, 88.7229415743, places=8)
        self.assertGreater(rb, ARMED_THRESHOLD)

    def test_pure_rate_shock_cannot_arm_route_b(self):
        p = policy_shock(100.0, 0.0)
        self.assertEqual(p, 60.0)
        rb = route_b(100.0, p, 100.0)
        self.assertAlmostEqual(rb, 84.3432665302, places=8)
        self.assertLess(rb, ARMED_THRESHOLD)

    def test_2005_negative_control_upper_bound(self):
        rb = route_b(100.0, 48.0, 100.0)
        self.assertLess(rb, ARMED_THRESHOLD)

    def test_2011_extreme_taper_still_below_arm(self):
        p = policy_shock(28.3, 100.0)
        rb = route_b(100.0, p, 100.0)
        self.assertLess(rb, ARMED_THRESHOLD)

    def test_continuing_qt_is_not_taper(self):
        # Previously contracting balance sheet => no expansion gate.
        self.assertEqual(taper_shock(7.0, 7.2, 7.5), 0.0)

    def test_pre_walcl_history_is_zero_taper(self):
        self.assertEqual(taper_shock(None, None, None, series_started=False), 0.0)

    def test_data_outage_is_not_zero_risk(self):
        self.assertIsNone(taper_shock(None, 8.0, 7.8, series_started=True))
        self.assertIsNone(rate_shock(None, 0.25))
        self.assertIsNone(policy_shock(None, 50.0))
        self.assertIsNone(route_b(98.0, None, 96.0))


if __name__ == "__main__":
    unittest.main()
