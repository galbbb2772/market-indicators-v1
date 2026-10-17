from __future__ import annotations

import unittest
from datetime import date

from shadow_replay_v24 import ReplayState, Snapshot, State, pressure, replay, step


class ShadowReplayV24Tests(unittest.TestCase):
    def test_pressure_is_max_route(self):
        x = Snapshot(date(2022,1,3), 70, 88.7229415743, 80, True, True)
        self.assertAlmostEqual(pressure(x), 88.7229415743)

    def test_2022_policy_route_arms_then_price_breakdown_triggers(self):
        armed = Snapshot(
            date(2022,1,3),
            route_a=0.0,
            route_b=88.7229415743,
            route_c=0.0,
            within_5pct_of_24m_high=True,
            high_formed_within_3m=True,
        )
        broke = Snapshot(
            date(2022,1,18),
            route_a=0.0,
            route_b=0.0,
            route_c=0.0,
            within_5pct_of_24m_high=False,
            high_formed_within_3m=True,
            t_score=70.0,
            drawdown_from_12m_high_pct=4.57,
        )
        out = replay([armed, broke])
        self.assertEqual(out.state, State.TRIGGERED)
        self.assertEqual(out.armed_at, date(2022,1,3))
        self.assertEqual(out.triggered_at, date(2022,1,18))
        self.assertEqual(out.trigger_reason, "PRICE_BREAKDOWN")

    def test_price_breakdown_cannot_trigger_without_armed(self):
        x = Snapshot(
            date(2022,1,18), 0, 0, 0, False, False,
            t_score=100.0,
            drawdown_from_12m_high_pct=20.0,
        )
        out = step(ReplayState(), x)
        self.assertEqual(out.state, State.IDLE)

    def test_accepted_early_breadth_is_direct_trigger(self):
        x = Snapshot(
            date(2021,10,15),
            route_a=0.0,
            route_b=0.0,
            route_c=86.0,
            within_5pct_of_24m_high=False,
            high_formed_within_3m=False,
            breadth_delta_3m=10.0,
        )
        out = step(ReplayState(), x)
        self.assertEqual(out.state, State.TRIGGERED)
        self.assertEqual(out.trigger_reason, "EARLY_BREADTH")

    def test_early_breadth_needs_route_c_not_other_route(self):
        x = Snapshot(
            date(2021,10,15),
            route_a=95.0,
            route_b=0.0,
            route_c=84.9,
            within_5pct_of_24m_high=False,
            high_formed_within_3m=False,
            breadth_delta_3m=30.0,
        )
        out = step(ReplayState(), x)
        self.assertEqual(out.state, State.IDLE)

    def test_arm_requires_top_location(self):
        x = Snapshot(date(2022,1,3), 0, 90, 0, False, True)
        self.assertEqual(step(ReplayState(), x).state, State.IDLE)

    def test_armed_window_expires_after_six_calendar_months(self):
        first = Snapshot(date(2022,1,3), 0, 90, 0, True, True)
        s = step(ReplayState(), first)
        self.assertEqual(s.armed_expires_at, date(2022,7,3))

        late_break = Snapshot(
            date(2022,7,5), 0, 0, 0, False, False,
            t_score=100.0,
            drawdown_from_12m_high_pct=30.0,
        )
        s = step(s, late_break)
        self.assertEqual(s.state, State.IDLE)


if __name__ == "__main__":
    unittest.main()
