"""Deterministic scope and lookahead tests for the free academic early-history probe."""
import pandas as pd
import pytest

from research.v218_2000_2018_finsaber_public_backtest import raw_breadth,combine,REPORT_CLASS


def small_prices():
    ds=pd.bdate_range("2000-01-03",periods=280)
    rows=[]
    for i,d in enumerate(ds):
        rows.append({"date":d,"symbol":"RISING","price":100+i})
        rows.append({"date":d,"symbol":"FALLING","price":1000-i})
    return pd.DataFrame(rows)


def test_252_prior_closes_exactly_and_no_first_observation():
    out=raw_breadth(small_prices())
    assert out.iloc[0].issues==2
    assert out.iloc[0].mature==0
    assert out.iloc[251].mature==0
    assert out.iloc[252].mature==2
    assert out.iloc[252].nh==1 and out.iloc[252].nl==1


def test_present_day_price_excluded_from_prior_window():
    x=small_prices()
    old=raw_breadth(x)
    x.loc[(x.symbol=="RISING")&(x.date==pd.bdate_range("2000-01-03",periods=280)[252]),"price"]=100_000
    new=raw_breadth(x)
    assert old.iloc[251].nh==new.iloc[251].nh
    assert old.iloc[252].nh==new.iloc[252].nh


def test_zero_policy_cannot_create_a_signal_even_with_negative_breadth():
    out=raw_breadth(small_prices())
    gates=pd.DataFrame({"date":out.date,"gspc_close":1000.0,"policy":0.0,
        "top_ratio":1.0,"route_upper_bound_if_hl100":0.0})
    scored,ep=combine(out,gates,min_required_gspc_sessions=200)
    assert not scored.proxy_alert_day.any()
    assert not ep


def test_55_frozen_and_period_lock_are_separate_from_source_scope():
    assert "NOT_ALL_US_PIT" in REPORT_CLASS
    assert "PROXY" in REPORT_CLASS


def test_scope_separate_from_user_frozen_2019_dataset():
    from research import v218_2000_2018_finsaber_public_backtest as module
    assert module.END=="2018-12-31"
    assert "FINSABER" in module.DATA_URL or "finsaber" in module.DATA_URL
