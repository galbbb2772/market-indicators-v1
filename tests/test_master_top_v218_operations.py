from datetime import datetime, timedelta, timezone

import pytest

import master_top_v218 as v218


def test_no_key_is_a_hard_error(monkeypatch):
    monkeypatch.delenv("MARKETPARQUET_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="MARKETPARQUET_API_KEY is not configured"):
        v218.main()


def test_fresh_score_is_accepted():
    today = datetime.now(timezone.utc).date()
    v218.ensure_score_fresh(str(today))


def test_stale_score_is_rejected():
    old = datetime.now(timezone.utc).date() - timedelta(days=7)
    with pytest.raises(RuntimeError, match="stale"):
        v218.ensure_score_fresh(str(old))


def test_future_dated_score_is_rejected():
    future = datetime.now(timezone.utc).date() + timedelta(days=1)
    with pytest.raises(RuntimeError, match="future"):
        v218.ensure_score_fresh(str(future))


def test_frozen_route_math_is_unchanged():
    assert 69.0 < v218.route_score(policy=75.72, hl_score=84.84, top_ratio=0.9995) < 70.0
