from __future__ import annotations

import unittest
from datetime import datetime, timezone

import pandas as pd

from market_top_route_c_ng2_forward import (
    FIRST_PROSPECTIVE_EFFECTIVE_MONTH,
    HANDOFF_MIN,
    PREREGISTRATION_DATE,
    last_completed_month,
    leadership_handoff_share,
    median25,
    source_temporality,
)


class RouteCNG2ForwardTests(unittest.TestCase):
    def test_handoff_share(self):
        self.assertAlmostEqual(
            leadership_handoff_share(56.9605248470, 9.7867300268),
            0.8281839914,
            places=9,
        )
        self.assertEqual(
            leadership_handoff_share(11.8787949713, 11.8787949713),
            0.0,
        )
        self.assertEqual(leadership_handoff_share(0.0, 0.0), 0.0)

    def test_frozen_boundary_and_gate(self):
        self.assertEqual(PREREGISTRATION_DATE, "2026-10-19")
        self.assertEqual(FIRST_PROSPECTIVE_EFFECTIVE_MONTH, "202701")
        self.assertEqual(HANDOFF_MIN, 0.40)

    def test_last_completed_month(self):
        now = datetime(2026, 10, 19, 12, 0, tzinfo=timezone.utc)
        self.assertEqual(last_completed_month(now), "202609")

    def test_source_temporality(self):
        pre = source_temporality("202607", "202608")
        self.assertFalse(
            pre["all_source_months_fully_post_preregistration"]
        )
        post = source_temporality("202611", "202612")
        self.assertTrue(
            post["all_source_months_fully_post_preregistration"]
        )

    def test_median25(self):
        xs = [float(x) for x in range(25)]
        self.assertEqual(median25(xs), 12.0)


if __name__ == "__main__":
    unittest.main()
