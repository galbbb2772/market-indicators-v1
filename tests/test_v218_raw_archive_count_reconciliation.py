"""Deterministic tests for raw-vs-archived count coverage sensitivity."""
import pandas as pd
import pytest
from research.v218_raw_archive_count_reconciliation import qa_results,SENSITIVITY_LAST_SESSION


def source():
    dates=pd.bdate_range("2020-01-02",periods=640)
    raw=[100]*640
    raw[40]=150
    raw[41]=100
    rec=pd.DataFrame({"date":dates,"raw_parquet_rows":raw,
                      "archived_issues":100,
                      "difference_raw_minus_archived":[v-100 for v in raw]})
    agg=pd.DataFrame({"date":dates,"issues":100})
    score=pd.DataFrame({"date":dates,"route_archive_breadth_proxy":66.0,"trigger":False})
    score.loc[40+271,"trigger"]=True
    score.loc[41+271+1,"trigger"]=True
    return rec,agg,score


def test_real_raw_only_break_exposes_first_of_two_signals():
    rec,b,s=source()
    d,r=qa_results(rec,b,s)
    assert SENSITIVITY_LAST_SESSION==271
    assert r["source_count_jump_days"]==2
    assert all(x["raw_only"] for x in r["source_count_jumps"])
    assert r["possible_alert_days"]==2
    assert r["possible_alert_days_in_source_review"]==1
    assert r["true_alarm_validity"]=="UNDETERMINED"
    assert r["stock_universe_PIT_verified"] is False
    assert r["frozen_formula_changed"] is False


def test_reconciliation_is_required_exactly():
    rec,b,s=source()
    rec.loc[20,"difference_raw_minus_archived"]=11
    with pytest.raises(ValueError,match="arithmetic"):
        qa_results(rec,b,s)


def test_raw_daily_and_aggregated_market_dates_must_match():
    rec,b,s=source()
    with pytest.raises(ValueError,match="calendars disagree"):
        qa_results(rec.iloc[:-1],b,s)


def test_trigger_date_must_be_in_original_raw_source():
    rec,b,s=source()
    s.loc[len(s)]=[pd.Timestamp("2028-01-01"),66.0,True]
    with pytest.raises(ValueError,match="lacks raw-source"):
        qa_results(rec,b,s)
