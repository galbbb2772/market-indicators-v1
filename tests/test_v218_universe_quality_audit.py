"""No-PIT-claims QA tests for historical archived universe discontinuities."""
from __future__ import annotations
import pandas as pd
import pytest

from research.v218_universe_quality_audit import (
    source_qa, DEPENDENCY_RADIUS_SESSIONS, REPORT_CLASS
)


def frames(size=600):
    dates = pd.bdate_range("2020-01-02", periods=size)
    issues = [100] * 5 + [200] * (size - 5)
    breadth = pd.DataFrame({
        "date": dates, "issues": issues,
        "adv": [40]*size, "dec": [40]*size, "unch": [10]*size,
        "nh": [5]*size, "nl": [10]*size,
    })
    scores = pd.DataFrame({
        "date":dates,
        "issues":issues,
        "route_archive_breadth_proxy": [0.0]*size,
        "trigger": [False]*size,
    })
    return breadth, scores


def test_exact_252_plus_20_dependency_radius_and_signal_quarantine():
    assert DEPENDENCY_RADIUS_SESSIONS == 271
    b,s = frames()
    # 2020 session #5 jumps from 100 to 200 and then stays level.
    s.loc[5+271,"trigger"] = True
    s.loc[5+272,"trigger"] = True
    s.loc[s.trigger,"route_archive_breadth_proxy"] = 67.44
    daily, qa = source_qa(b,s)
    assert qa["break_day_count"] == 1
    assert qa["candidate_trigger_day_count"] == 2
    assert qa["candidate_trigger_days_with_possible_lookback_issue"] == 1
    assert bool(daily.loc[5+271,"may_depend_on_jump_in_frozen_252_plus_20_window"])
    assert not bool(daily.loc[5+272,"may_depend_on_jump_in_frozen_252_plus_20_window"])
    assert qa["pit_certified_triggers"] == 0
    assert not qa["this_source_passes_pit_validation"]
    assert not qa["source_jump_proves_wrong_stock_prices"]
    assert qa["classification"] == REPORT_CLASS


def test_no_anomaly_when_universe_is_stable():
    b,s=frames()
    b.issues=200
    s.issues=200
    daily,qa=source_qa(b,s)
    assert qa["break_day_count"] == 0
    assert qa["market_sessions_flagged_for_source_review"] == 0
    assert not daily["may_depend_on_jump_in_frozen_252_plus_20_window"].any()


def test_illegal_counts_fail_closed():
    b,s=frames()
    b.loc[20,"nh"]=250
    with pytest.raises(ValueError,match="exceed"):
        source_qa(b,s)


def test_mismatched_archive_and_replay_universe_fails():
    b,s=frames()
    s.loc[100,"issues"]=9999
    with pytest.raises(ValueError,match="universe counts disagree"):
        source_qa(b,s)


def test_missing_scored_market_date_fails():
    b,s=frames()
    b=b.iloc[:-1]
    with pytest.raises(ValueError,match="Missing QA source day"):
        source_qa(b,s)


def test_this_is_not_a_trade_parameter():
    b,s=frames()
    with pytest.raises(ValueError,match="NOT a trading parameter"):
        source_qa(b,s,break_ratio=1.5)
