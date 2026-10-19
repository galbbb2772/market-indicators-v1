from __future__ import annotations

import unittest
from unittest.mock import patch

import pandas as pd

from market_top_ng3_forward import (
    classify_252,
    evaluate_horizon,
    update_episode_ledger,
)


def price_series():
    idx=pd.bdate_range("2026-12-31",periods=420)
    vals=pd.Series(100.0,index=idx,dtype=float)
    vals.iloc[80]=80.0
    vals.iloc[-1]=110.0
    vals.attrs["source"]="Yahoo Finance SPY unadjusted Close"
    vals.attrs["payload_sha256"]="c"*64
    vals.attrs["latest_date"]=idx[-1].date().isoformat()
    return vals


def snap(month,state="ARMED",count=True,anchor="2026-12-31"):
    return {
        "generated_at":"2026-12-31T23:00:00+00:00",
        "effective_month":month,
        "counts_toward_prospective_validation":count,
        "state":state,
        "source_months":{"fama_french":"202610","credit":"202611"},
        "source_temporality":{
            "preregistration_date":"2026-10-19",
            "tier":"SOURCE_MONTH_STRADDLES_PREREGISTRATION",
            "all_source_months_fully_post_preregistration":False,
            "detail":{},
        },
        "route_a_ng3_score":90.0,
        "components":{"financial_lead_gap_raw":15.0},
        "gates":{"top_location":{"asof":anchor,"close":100.0}},
    }


def empty_ledger():
    return {
        "schema_version":"market-top-route-a-ng3-episodes-1",
        "research_only":True,
        "production_effect":"none",
        "protocol":"market-top-route-a-ng3-evidence-protocol-2",
        "episodes":[],
        "summary":{},
    }


class NG3EpisodeLedgerTests(unittest.TestCase):
    def test_preprospective_snapshot_cannot_open_episode(self):
        with patch(
            "market_top_ng3_forward.load_episode_ledger",
            return_value=empty_ledger(),
        ):
            x=update_episode_ledger(
                snap("202611",state="ARMED",count=False),
                price_series(),
            )
        self.assertEqual(x["episodes"],[])
        self.assertEqual(x["summary"]["prospective_episode_count"],0)
        self.assertFalse(x["summary"]["review_eligible"])

    def test_contiguous_armed_months_are_one_episode_then_idle_closes(self):
        p=price_series()
        with patch(
            "market_top_ng3_forward.load_episode_ledger",
            return_value=empty_ledger(),
        ):
            first=update_episode_ledger(snap("202612"),p)
        self.assertEqual(len(first["episodes"]),1)
        self.assertEqual(first["episodes"][0]["episode_id"],"NG3-202612")
        self.assertFalse(
            first["episodes"][0]["source_temporality_at_start"][
                "all_source_months_fully_post_preregistration"
            ]
        )
        self.assertEqual(
            first["summary"][
                "straddling_or_pre_preregistration_source_episodes"
            ],
            1,
        )

        with patch(
            "market_top_ng3_forward.load_episode_ledger",
            return_value=first,
        ):
            second=update_episode_ledger(snap("202701"),p)
        self.assertEqual(len(second["episodes"]),1)
        self.assertEqual(
            second["episodes"][0]["last_armed_effective_month"],
            "202701",
        )

        with patch(
            "market_top_ng3_forward.load_episode_ledger",
            return_value=second,
        ):
            closed=update_episode_ledger(
                snap("202702",state="IDLE"),
                p,
            )
        self.assertEqual(
            closed["episodes"][0]["signal_status"],
            "CLOSED",
        )
        self.assertEqual(
            closed["episodes"][0]["closed_effective_month"],
            "202702",
        )

        with patch(
            "market_top_ng3_forward.load_episode_ledger",
            return_value=closed,
        ):
            reopened=update_episode_ledger(
                snap("202703",anchor="2027-03-31"),
                p,
            )
        self.assertEqual(len(reopened["episodes"]),2)
        self.assertEqual(reopened["episodes"][1]["episode_id"],"NG3-202703")

    def test_out_of_order_armed_month_fails_closed(self):
        p=price_series()
        with patch(
            "market_top_ng3_forward.load_episode_ledger",
            return_value=empty_ledger(),
        ):
            first=update_episode_ledger(snap("202702"),p)

        with patch(
            "market_top_ng3_forward.load_episode_ledger",
            return_value=first,
        ):
            with self.assertRaisesRegex(
                ValueError,
                "out-of-order prospective episode update",
            ):
                update_episode_ledger(snap("202701"),p)

    def test_out_of_order_idle_month_fails_closed(self):
        p=price_series()
        with patch(
            "market_top_ng3_forward.load_episode_ledger",
            return_value=empty_ledger(),
        ):
            first=update_episode_ledger(snap("202702"),p)

        with patch(
            "market_top_ng3_forward.load_episode_ledger",
            return_value=first,
        ):
            with self.assertRaisesRegex(
                ValueError,
                "out-of-order prospective episode update",
            ):
                update_episode_ledger(
                    snap("202701",state="IDLE"),
                    p,
                )

    def test_stale_armed_month_after_closed_later_episode_fails_closed(self):
        p=price_series()
        with patch(
            "market_top_ng3_forward.load_episode_ledger",
            return_value=empty_ledger(),
        ):
            armed=update_episode_ledger(snap("202612"),p)

        with patch(
            "market_top_ng3_forward.load_episode_ledger",
            return_value=armed,
        ):
            closed=update_episode_ledger(
                snap("202701",state="IDLE"),
                p,
            )

        with patch(
            "market_top_ng3_forward.load_episode_ledger",
            return_value=closed,
        ):
            with self.assertRaisesRegex(
                ValueError,
                "out-of-order prospective episode update",
            ):
                update_episode_ledger(
                    snap("202612",state="ARMED"),
                    p,
                )

    def test_missing_month_between_armed_states_does_not_split_episode(self):
        p=price_series()
        with patch(
            "market_top_ng3_forward.load_episode_ledger",
            return_value=empty_ledger(),
        ):
            first=update_episode_ledger(snap("202612"),p)

        # 2027-01 is missing entirely; the next observed month is ARMED.
        with patch(
            "market_top_ng3_forward.load_episode_ledger",
            return_value=first,
        ):
            bridged=update_episode_ledger(snap("202702"),p)

        self.assertEqual(len(bridged["episodes"]),1)
        ep=bridged["episodes"][0]
        self.assertEqual(ep["episode_id"],"NG3-202612")
        self.assertEqual(ep["last_armed_effective_month"],"202702")
        self.assertTrue(ep["continuity_evidence_gap"])
        self.assertEqual(ep["missing_effective_months"],["202701"])
        self.assertEqual(
            bridged["summary"]["episodes_with_continuity_gaps"],
            1,
        )

    def test_gap_tainted_complete_episode_cannot_count_toward_review(self):
        p=price_series()
        episodes=[]
        for i,month in enumerate(("202612","202702","202704","202706")):
            episodes.append({
                "episode_id":f"NG3-{month}",
                "signal_status":"CLOSED",
                "start_effective_month":month,
                "last_armed_effective_month":month,
                "closed_effective_month":month,
                "closed_reason":"TEST",
                "anchor_date":"2026-12-31",
                "anchor_close":100.0,
                "source_months_at_start":{},
                "start_score":90.0,
                "start_financial_lead_gap_raw":15.0,
                "continuity_evidence_gap": i == 0,
                "missing_effective_months":["202701"] if i == 0 else [],
                "outcomes":{},
                "classification_252":None,
            })
        ledger=empty_ledger()
        ledger["episodes"]=episodes
        with patch(
            "market_top_ng3_forward.load_episode_ledger",
            return_value=ledger,
        ):
            x=update_episode_ledger(
                snap("202708",state="IDLE"),
                p,
            )
        self.assertEqual(
            x["summary"]["complete_252_session_episodes"],
            4,
        )
        self.assertEqual(
            x["summary"][
                "complete_252_session_episodes_without_continuity_gaps"
            ],
            3,
        )
        self.assertFalse(x["summary"]["review_eligible"])

    def test_252_classification_is_anchor_based(self):
        p=price_series()
        m=evaluate_horizon(
            p,
            anchor_date="2026-12-31",
            anchor_close=100.0,
            sessions=252,
        )
        self.assertTrue(m["complete"])
        self.assertLessEqual(m["worst_return_from_anchor_pct"],-15.0)
        self.assertEqual(classify_252(m),"MAJOR_TOP")

    def test_completed_horizon_carries_price_payload_provenance(self):
        p=price_series()
        m=evaluate_horizon(
            p,
            anchor_date="2026-12-31",
            anchor_close=100.0,
            sessions=252,
        )
        self.assertTrue(m["complete"])
        self.assertEqual(
            m["price_source"],
            "Yahoo Finance SPY unadjusted Close",
        )
        self.assertEqual(m["price_payload_sha256"],"c"*64)
        self.assertEqual(
            m["price_latest_date"],
            p.index[-1].date().isoformat(),
        )

    def test_outcome_ledger_uses_current_observation_time_not_frozen_signal_time(self):
        p=price_series()
        with patch(
            "market_top_ng3_forward.load_episode_ledger",
            return_value=empty_ledger(),
        ):
            x=update_episode_ledger(
                snap("202612"),
                p,
                observed_at="2027-01-15T03:00:00+00:00",
            )
        self.assertEqual(
            x["generated_at"],
            "2027-01-15T03:00:00+00:00",
        )

    def test_completed_horizon_metrics_are_never_recomputed(self):
        p=price_series()
        frozen_63={
            "sessions_required":63,
            "sessions_observed":63,
            "complete":True,
            "asof":"2027-03-30",
            "forward_return_pct":12.345,
            "worst_return_from_anchor_pct":-3.21,
            "max_peak_to_trough_dd_pct":-4.56,
        }
        ledger=empty_ledger()
        ledger["episodes"]=[{
            "episode_id":"NG3-202612",
            "signal_status":"CLOSED",
            "start_effective_month":"202612",
            "last_armed_effective_month":"202612",
            "closed_effective_month":"202701",
            "closed_reason":"FIRST_COMPLETED_IDLE_MONTH",
            "anchor_date":"2026-12-31",
            "anchor_close":100.0,
            "source_months_at_start":{},
            "start_score":90.0,
            "start_financial_lead_gap_raw":15.0,
            "outcomes":{"63":dict(frozen_63)},
            "classification_252":None,
        }]
        with patch(
            "market_top_ng3_forward.load_episode_ledger",
            return_value=ledger,
        ):
            x=update_episode_ledger(
                snap("202702",state="IDLE"),
                p,
            )
        self.assertEqual(
            x["episodes"][0]["outcomes"]["63"],
            frozen_63,
        )

    def test_no_automatic_promotion_even_when_review_eligible(self):
        p=price_series()
        episodes=[]
        for i,month in enumerate(("202612","202702","202704","202706")):
            episodes.append({
                "episode_id":f"NG3-{month}",
                "signal_status":"CLOSED",
                "start_effective_month":month,
                "last_armed_effective_month":month,
                "closed_effective_month":month,
                "closed_reason":"TEST",
                "anchor_date":"2026-12-31",
                "anchor_close":100.0,
                "source_months_at_start":{},
                "start_score":90.0,
                "start_financial_lead_gap_raw":15.0,
                "outcomes":{},
                "classification_252":None,
            })
        ledger=empty_ledger()
        ledger["episodes"]=episodes
        with patch(
            "market_top_ng3_forward.load_episode_ledger",
            return_value=ledger,
        ):
            x=update_episode_ledger(
                snap("202708",state="IDLE"),
                p,
            )
        self.assertTrue(x["summary"]["review_eligible"])
        self.assertFalse(x["summary"]["automatic_promotion"])
        self.assertIsNone(x["summary"]["action_signal"])


if __name__=="__main__":
    unittest.main()
