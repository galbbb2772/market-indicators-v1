"""Operational guards only; no frozen V2.1.8 coefficients are modified."""
from datetime import datetime, timedelta, timezone

import pandas as pd
import pytest

from master_top_v218 import ensure_input_alignment, ensure_score_fresh, main


def source_series(start="2025-01-01", end="2026-10-23"):
    idx = pd.bdate_range(start, end)
    return pd.Series(4.0, index=idx)


def test_source_alignment_healthy_business_day_feed():
    rates = source_series()
    price = source_series()
    ensure_input_alignment(pd.Timestamp("2026-10-23"), price, rates)


def test_source_alignment_rejects_stale_sp500_even_if_breadth_is_current():
    rates = source_series()
    price = source_series(end="2026-10-12")
    with pytest.raises(RuntimeError, match="S&P 500 close is stale"):
        ensure_input_alignment(pd.Timestamp("2026-10-23"), price, rates)


def test_source_alignment_rejects_stale_current_treasury_even_if_price_is_current():
    price = source_series()
    rates = source_series(end="2026-10-12")
    with pytest.raises(RuntimeError, match="DGS2 current is stale"):
        ensure_input_alignment(pd.Timestamp("2026-10-23"), price, rates)


def test_source_alignment_rejects_missing_historical_rate_anchor():
    price = source_series()
    rates = source_series(start="2026-09-01")
    with pytest.raises(RuntimeError, match="DGS2 6M anchor"):
        ensure_input_alignment(pd.Timestamp("2026-10-23"), price, rates)


def test_missing_marketparquet_key_fails_closed(monkeypatch):
    monkeypatch.delenv("MARKETPARQUET_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="MARKETPARQUET_API_KEY is not configured"):
        main()


def test_stale_and_future_breadth_scores_fail_closed():
    utc_today = datetime.now(timezone.utc).date()
    ensure_score_fresh(str(utc_today - timedelta(days=1)))
    with pytest.raises(RuntimeError, match="stale"):
        ensure_score_fresh(str(utc_today - timedelta(days=6)))
    with pytest.raises(RuntimeError, match="future"):
        ensure_score_fresh(str(utc_today + timedelta(days=1)))
