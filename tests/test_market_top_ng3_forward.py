from __future__ import annotations

import unittest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pandas as pd

from market_top_ng3_forward import (
    add_months,
    completed_month_ym,
    merge_pinned_with_extension,
    select_completed_state,
    source_temporality,
    write_outputs,
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

    def test_december_2026_source_month_straddles_preregistration(self):
        x=source_temporality("202610","202611")
        self.assertFalse(
            x["all_source_months_fully_post_preregistration"]
        )
        self.assertEqual(
            x["tier"],
            "SOURCE_MONTH_STRADDLES_PREREGISTRATION",
        )
        self.assertEqual(
            x["detail"]["fama_french"]["relation"],
            "STRADDLES_PREREGISTRATION_DATE",
        )
        self.assertEqual(
            x["detail"]["credit"]["relation"],
            "FULLY_POST_PREREGISTRATION",
        )

    def test_january_2027_sources_are_fully_post_preregistration(self):
        x=source_temporality("202611","202612")
        self.assertTrue(
            x["all_source_months_fully_post_preregistration"]
        )
        self.assertEqual(
            x["tier"],
            "FULL_SOURCE_MONTHS_POST_PREREGISTRATION",
        )

    def test_completed_state_must_match_latest_completed_month(self):
        states=[
            {"effective_month":"202608"},
            {"effective_month":"202609"},
        ]
        x=select_completed_state(states,"202609")
        self.assertEqual(x["effective_month"],"202609")
        with self.assertRaises(ValueError):
            select_completed_state(states,"202610")

    def test_evidence_files_are_not_partially_written_when_ledger_fails(self):
        snapshot={
            "generated_at":"2027-01-02T03:00:00+00:00",
            "effective_month":"202612",
            "evidence_phase":"PROSPECTIVE",
            "counts_toward_prospective_validation":True,
            "route_a_ng3_score":90.0,
            "components":{"financial_lead_gap_raw":15.0},
            "gates":{
                "phase_gate":True,
                "top_location":{"passes":True},
            },
            "state":"ARMED",
        }
        price=pd.Series(
            [100.0],
            index=pd.to_datetime(["2027-01-02"]),
            dtype=float,
        )
        book={"snapshots":[],"summary":{}}
        current=MagicMock()
        monthly=MagicMock()
        history=MagicMock()
        episodes=MagicMock()

        with (
            patch(
                "market_top_ng3_forward.freeze_monthly_signal_snapshot",
                return_value=(snapshot,book,True),
            ),
            patch(
                "market_top_ng3_forward.load_history",
                return_value=[],
            ),
            patch(
                "market_top_ng3_forward.update_episode_ledger",
                side_effect=ValueError("fail closed"),
            ),
            patch("market_top_ng3_forward.OUT_CURRENT",current),
            patch("market_top_ng3_forward.OUT_MONTHLY",monthly),
            patch("market_top_ng3_forward.OUT_HISTORY",history),
            patch("market_top_ng3_forward.OUT_EPISODES",episodes),
        ):
            with self.assertRaisesRegex(ValueError,"fail closed"):
                write_outputs(snapshot,price)

        current.write_text.assert_not_called()
        monthly.write_text.assert_not_called()
        history.write_text.assert_not_called()
        episodes.write_text.assert_not_called()
        current.parent.mkdir.assert_not_called()

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
