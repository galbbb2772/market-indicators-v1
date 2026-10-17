from __future__ import annotations

import unittest

from market_top_shadow_live import build_shadow_snapshot


class MarketTopShadowLiveTests(unittest.TestCase):
    def test_missing_canonical_inputs_never_create_authoritative_route(self):
        x = build_shadow_snapshot(
            asof="2026-10-16",
            rate_shock=100.0,
            taper_shock=6.860616780107296,
            policy_shock=62.744246712042916,
            spy_close=763.25,
            spy_high12_close=779.09,
            dd12_pct=2.0331,
            ma10m_prev=720.884,
            t_v24r=13.774666666666668,
            price_breakdown_v24r=False,
            cape_current=40.54,
            valuation_proxy_score=47.22,
            size_support_proxy_score=6.42,
        )
        self.assertEqual(x.status, "INPUT_INCOMPLETE")
        self.assertIsNone(x.route_b_authoritative)
        self.assertAlmostEqual(x.size_weakness_proxy_score, 93.58, places=8)
        self.assertAlmostEqual(x.route_b_proxy, 65.20701368567535, places=8)

    def test_proxy_cannot_silently_change_state(self):
        x = build_shadow_snapshot(
            asof="2026-10-16",
            rate_shock=100.0,
            taper_shock=100.0,
            policy_shock=100.0,
            spy_close=1.0,
            spy_high12_close=2.0,
            dd12_pct=50.0,
            ma10m_prev=2.0,
            t_v24r=100.0,
            price_breakdown_v24r=True,
            valuation_proxy_score=100.0,
            size_support_proxy_score=0.0,
        )
        self.assertEqual(x.route_b_proxy, 100.0)
        self.assertIsNone(x.route_b_authoritative)
        self.assertEqual(x.status, "INPUT_INCOMPLETE")

    def test_authoritative_route_requires_both_canonical_inputs(self):
        x = build_shadow_snapshot(
            asof="2022-01-03",
            rate_shock=63.3333333333,
            taper_shock=90.9715481444,
            policy_shock=74.3886192578,
            spy_close=477.71,
            spy_high12_close=477.71,
            dd12_pct=0.0,
            ma10m_prev=437.071,
            t_v24r=0.0,
            price_breakdown_v24r=False,
            valuation_canonical_score=97.9,
            size_weakness_canonical_score=95.9,
        )
        self.assertEqual(x.status, "READY_FOR_SHADOW_STATE_MACHINE")
        self.assertGreater(x.route_b_authoritative, 85.0)


if __name__ == "__main__":
    unittest.main()
