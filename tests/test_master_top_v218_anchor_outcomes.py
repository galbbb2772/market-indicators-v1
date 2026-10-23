"""Deterministic tests for historical price outcome accounting (not scorer tests)."""
from __future__ import annotations

import pandas as pd
import pytest

from research.master_top_v218_anchor_outcomes import (
    ARCHIVED_ANCHORS, FREEZE_DATE, THRESHOLD, forward_mdd,
    outcome_class, validate_price_data, evaluate,
)


def prices():
    return pd.Series([100.0, 110.0, 99.0, 95.0, 105.0],
        index=pd.bdate_range("2026-01-05", periods=5))


def test_forward_running_peak_not_only_entry_price():
    s = prices()
    out = forward_mdd(s, "2026-01-05", "3")
    assert out["matured"] is True
    assert out["mdd_pct"] == round(100*(95/110-1),4)
    assert out["observed_sessions"] == 3


def test_censored_does_not_become_classified():
    s = prices()
    t = forward_mdd(s, "2026-01-05", "12m")
    assert t["matured"] is False
    assert t["mdd_pct"] is None
    assert t["censored_mdd_to_date_pct"] is not None
    assert outcome_class(t["mdd_pct"]) == "CENSORED"


def test_boundary_classes_match_frozen_spec():
    assert outcome_class(-20.0) == "MAJOR_BEAR"
    assert outcome_class(-15.0) == "SEVERE_NEAR_MISS"
    assert outcome_class(-10.0) == "CORRECTION"
    assert outcome_class(-9.99) == "FALSE_POSITIVE"


def test_frozen_threshold_and_seed_are_not_revised():
    assert THRESHOLD == 55.0 and FREEZE_DATE == "2026-10-17"
    bydate = {x[0]:x for x in ARCHIVED_ANCHORS}
    assert bydate["2006-06-29"][1] < THRESHOLD
    assert bydate["2021-12-15"][1] >= THRESHOLD
    assert bydate["2026-09-10"][2] == "PRE_FREEZE_SEED"
    assert bydate["2026-10-09"][2] == "PRE_FREEZE_SEED_SAME_EPISODE"


def test_recent_only_data_cannot_audit_1999():
    dates = pd.bdate_range("2024-10-23", "2026-10-22")
    df = pd.DataFrame({"date":dates,"close":100.0,"adjusted_close":100.0})
    with pytest.raises(ValueError, match="1999 anchor"):
        validate_price_data(df,"Massive short history",True)


def test_duplicate_price_dates_are_fatal():
    df = pd.DataFrame({"date":[pd.Timestamp("1999-11-29")]*2, "close":[100.,101.],
                       "adjusted_close":[100.,101.]})
    with pytest.raises(ValueError, match="duplicate"):
        validate_price_data(df, "bad source", True)


def test_nontrading_signal_never_uses_future_price_as_entry():
    with pytest.raises(ValueError, match="Missing exact anchor"):
        forward_mdd(prices(), "2026-01-03", "12m")


def test_untriggered_negative_control_not_a_false_positive():
    dates = pd.bdate_range("1998-01-02", "2026-10-22")
    data = pd.DataFrame({"date":dates,"close":100.0,"adjusted_close":float("nan")})
    data.attrs["provider"] = "synthetic test only"
    report = evaluate(data)
    ctrl = next(x for x in report["results"] if x["anchor_date"]=="2006-06-29")
    assert ctrl["reported_trigger"] is False
    assert ctrl["forward_12m"]["matured"] is True
    assert ctrl["underlying_market_path_class_12m"] == "FALSE_POSITIVE"
    assert ctrl["outcome_class_12m"] == "NOT_APPLICABLE_NO_ALERT"
    seed = next(x for x in report["results"] if x["anchor_date"]=="2026-09-10")
    assert seed["outcome_class_12m"] == "CENSORED"
    assert report["matured_reported_alert_anchors"] == 3
