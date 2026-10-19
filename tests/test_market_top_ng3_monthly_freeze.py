from __future__ import annotations

import unittest
from unittest.mock import patch

from market_top_ng3_forward import freeze_monthly_signal_snapshot


def book():
    return {
        "schema_version":"market-top-route-a-ng3-monthly-snapshots-1",
        "research_only":True,
        "production_effect":"none",
        "prospective_start_effective_month":"202612",
        "snapshots":[],
        "summary":{
            "frozen_prospective_months":0,
            "first_frozen_effective_month":None,
            "latest_frozen_effective_month":None,
            "missing_effective_months":[],
            "evidence_gaps_present":False,
            "fully_post_preregistration_source_months":0,
            "straddling_or_pre_preregistration_source_months":0,
        },
    }


def snapshot(month="202612",score=90.0,count=True,hash_value="a"*64):
    return {
        "schema_version":"market-top-route-a-ng3-forward-1",
        "generated_at":"2027-01-02T03:00:00+00:00",
        "research_only":True,
        "production_effect":"none",
        "validation_status":"PROSPECTIVE_VALIDATION_PENDING",
        "effective_month":month,
        "evidence_phase":"PROSPECTIVE" if count else "RETROSPECTIVE_TRAINING_DIAGNOSTIC",
        "counts_toward_prospective_validation":count,
        "route_a_ng3_score":score,
        "components":{"financial_lead_gap_raw":15.0},
        "gates":{"phase_gate":True,"top_location":{"passes":True}},
        "state":"ARMED",
        "source_months":{"fama_french":"202610","credit":"202611"},
        "source_temporality":{
            "preregistration_date":"2026-10-19",
            "tier":"SOURCE_MONTH_STRADDLES_PREREGISTRATION",
            "all_source_months_fully_post_preregistration":False,
            "detail":{},
        },
        "sources":{"fama_french":{"ff3_provenance":{"zip_sha256":hash_value}}},
    }


class NG3MonthlySnapshotFreezeTests(unittest.TestCase):
    def test_preprospective_month_is_not_frozen(self):
        x=snapshot(month="202611",count=False)
        with patch(
            "market_top_ng3_forward.load_monthly_snapshot_book",
            return_value=book(),
        ):
            canonical,b,created=freeze_monthly_signal_snapshot(x)
        self.assertIs(canonical,x)
        self.assertFalse(created)
        self.assertEqual(b["snapshots"],[])

    def test_first_prospective_snapshot_is_frozen(self):
        x=snapshot()
        with patch(
            "market_top_ng3_forward.load_monthly_snapshot_book",
            return_value=book(),
        ):
            canonical,b,created=freeze_monthly_signal_snapshot(x)
        self.assertTrue(created)
        self.assertEqual(canonical["route_a_ng3_score"],90.0)
        self.assertEqual(
            canonical["evidence_lock"]["mode"],
            "FIRST_SUCCESSFUL_POST_MONTH_CLOSE_SNAPSHOT",
        )
        self.assertTrue(
            canonical["evidence_lock"]["immutable_signal_fields"]
        )
        self.assertEqual(len(b["snapshots"]),1)

    def test_missing_prospective_month_is_explicit_gap(self):
        jan=snapshot(month="202701",score=88.0,count=True)
        jan["source_months"]={"fama_french":"202611","credit":"202612"}
        jan["source_temporality"]={
            "preregistration_date":"2026-10-19",
            "tier":"FULL_SOURCE_MONTHS_POST_PREREGISTRATION",
            "all_source_months_fully_post_preregistration":True,
            "detail":{},
        }
        with patch(
            "market_top_ng3_forward.load_monthly_snapshot_book",
            return_value=book(),
        ):
            _,b,created=freeze_monthly_signal_snapshot(jan)
        self.assertTrue(created)
        self.assertEqual(
            b["summary"]["missing_effective_months"],
            ["202612"],
        )
        self.assertTrue(b["summary"]["evidence_gaps_present"])
        self.assertEqual(
            b["summary"]["fully_post_preregistration_source_months"],
            1,
        )

    def test_later_same_month_revision_cannot_overwrite_frozen_signal(self):
        original=snapshot(score=90.0,hash_value="a"*64)
        with patch(
            "market_top_ng3_forward.load_monthly_snapshot_book",
            return_value=book(),
        ):
            frozen,b,_=freeze_monthly_signal_snapshot(original)

        revised=snapshot(score=55.0,hash_value="b"*64)
        revised["generated_at"]="2027-01-03T03:00:00+00:00"
        with patch(
            "market_top_ng3_forward.load_monthly_snapshot_book",
            return_value=b,
        ):
            canonical,b2,created=freeze_monthly_signal_snapshot(revised)

        self.assertFalse(created)
        self.assertEqual(canonical["route_a_ng3_score"],90.0)
        self.assertEqual(
            canonical["sources"]["fama_french"]["ff3_provenance"]["zip_sha256"],
            "a"*64,
        )
        self.assertEqual(len(b2["snapshots"]),1)

if __name__=="__main__":
    unittest.main()
