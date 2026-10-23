"""Source-contract tests: no actual stock bar or user credential is required."""
from __future__ import annotations

import hashlib

import pandas as pd
import pytest

from research.master_top_v218_marketparquet_public_sample import (
    audit_table, normalize_date, sample_audit, ANCHOR_FROZEN,
)


def stock_table(n=1001, stamp="2026-10-22", date_key="timestamp"):
    return pd.DataFrame({
        date_key: [pd.Timestamp(stamp)] * n,
        "symbol": [f"S{i:05d}" for i in range(n)],
        "asset_type": ["Stock"] * n,
        "close": [10.0] * n,
        "high": [10.5] * n,
        "low": [9.5] * n,
    })


def test_real_schema_timestamp_can_be_normalized_without_changing_frozen_comparator():
    t=stock_table()
    date, field=normalize_date(t,"2026-10-22")
    assert field=="timestamp" and date.astype(str).eq("2026-10-22").all()
    info, names=audit_table(t,"2026-10-22","0"*64,1234)
    assert info["rows"] == 1001
    assert info["canonical_frozen_date_column_present"] is False
    assert info["needs_date_normalization"] is True
    assert info["ohlc_bounds_pass"] is True


def test_supported_canonical_date_column_needs_no_normalization():
    t=stock_table(date_key="date")
    info,_=audit_table(t,"2026-10-22","0"*64,1234)
    assert info["date_field_found"] == "date"
    assert info["needs_date_normalization"] is False


def test_wrong_session_timestamp_is_hard_error():
    t=stock_table(stamp="2026-10-21")
    with pytest.raises(ValueError,match="trade dates disagree"):
        audit_table(t,"2026-10-22","0"*64,1234)


def test_duplicate_symbol_fails():
    t=stock_table()
    t.loc[10,"symbol"]=t.loc[11,"symbol"]
    with pytest.raises(ValueError,match="Duplicate"):
        audit_table(t,"2026-10-22","0"*64,1234)


def test_wrong_asset_class_cannot_mix_etf():
    t=stock_table()
    t.loc[10,"asset_type"]="ETF"
    with pytest.raises(ValueError,match="asset type"):
        audit_table(t,"2026-10-22","0"*64,1234)


def test_nonpositive_and_invalid_ohlc_fail_closed():
    t=stock_table()
    t.loc[10,"close"]=-1.0
    with pytest.raises(ValueError,match="closing"):
        audit_table(t,"2026-10-22","0"*64,1234)
    t=stock_table()
    t.loc[10,"high"]=8.0
    with pytest.raises(ValueError,match="OHLC"):
        audit_table(t,"2026-10-22","0"*64,1234)


def test_vendor_partition_without_asset_type_is_explicitly_unverified():
    t=stock_table().drop(columns=["asset_type"])
    x,_=audit_table(t,"2026-10-22","0"*64,1234)
    assert x["stock_only_vendor_partition_validated"] is None


def test_daily_universe_comparison_does_not_create_fake_scores():
    a,one=audit_table(stock_table(stamp="2026-10-21"),"2026-10-21","1"*64,1234)
    b,two=audit_table(stock_table(),"2026-10-22","2"*64,1234)
    summary=sample_audit([(b,two),(a,one)])
    assert summary["original_frozen_comparator_definition"] == "CLOSE_252_INCLUSIVE_FROZEN"
    assert summary["ready_to_score_v218"] is False
    assert summary["ready_for_frozen_252_prior_sessions"] is False
    assert summary["cross_day_universe"][0]["overlap_symbols"] == 1001
    assert summary["cross_day_universe"][0]["jaccard"] == 1.0
