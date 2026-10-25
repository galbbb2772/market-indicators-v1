"""Frozen V2.1.8 NH/NL count uncertainty must be treated as sensitivity only."""
import pandas as pd
import pytest

from research.v218_2021_hilo_256_sensitivity import (
    audit,compute,RAW_UNVERIFIED_COUNTS,THRESHOLD,
)


def fixture():
    dates=pd.bdate_range("2021-10-01","2022-02-01")
    b=pd.DataFrame({"date":dates,"nh":0,"nl":200})
    g=pd.DataFrame({"date":dates,"policy":100.0,"top_ratio":1.0})
    return b,g


def test_original_frozen_policy_and_threshold_are_not_changed():
    b,g=fixture()
    z=compute(b,g,False)
    assert THRESHOLD==55.0
    assert z["hl"].dropna().iloc[-1]==100.0
    assert z["route"].dropna().iloc[-1]==100.0


def test_input_changes_only_three_existing_original_dates():
    b,g=fixture()
    original=compute(b,g,False)
    altered=compute(b,g,True)
    q=original.merge(altered,on="date",suffixes=("_before","_after"))
    rows=q.loc[(q.nh_before!=q.nh_after)|(q.nl_before!=q.nl_after)]
    assert list(rows.date.dt.strftime("%Y-%m-%d"))==sorted(RAW_UNVERIFIED_COUNTS)


def test_uncertified_recount_never_becomes_a_validated_model():
    b,g=fixture()
    window,report=audit(b,g)
    assert report["status"]=="UNVERIFIED_UNIVERSE_NHNL_INPUT_STRESS_ONLY"
    assert report["data_provider_PIT_proven"] is False
    assert report["frozen_formula_changed"] is False
    assert len(window)>10


def test_missing_historical_date_is_a_hard_error():
    b,g=fixture()
    b=b.loc[b.date!=pd.Timestamp("2021-12-28")]
    with pytest.raises(ValueError,match="Missing original daily breadth"):
        compute(b,g,True)
