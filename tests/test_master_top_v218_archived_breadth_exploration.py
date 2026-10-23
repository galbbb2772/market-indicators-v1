"""Deterministic guardrail tests for non-PIT archived breadth exploration."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from research.master_top_v218_archived_breadth_exploration import (
    archived_hl, replay, anomaly_summary, THRESHOLD, STATUS,
)
from master_top_v218 import hl_persistence_score


def inputs(periods=1100, nh=0, nl=200):
    days=pd.bdate_range("2019-01-02",periods=periods)
    bs=pd.DataFrame({
        "date":days,"issues":16000,
        "nh":nh,"nl":nl,
    })
    bs["hl_balance"]=np.where(nh+nl>0,(nh-nl)/(nh+nl),np.nan)
    bs["hl_persist_score"]=[
        hl_persistence_score(bs["hl_balance"].iloc[max(0,i-19):i+1].to_numpy())
        for i in range(len(bs))
    ]
    gs=pd.DataFrame({
        "date":days,
        "policy":100.0,"top_ratio":1.0,
        "route_upper_bound_if_hl100":100.0,
        "gspc_close":100.0,
    })
    return bs,gs


def test_archived_hl_restores_frozen_hl_without_imputation():
    b,_=inputs()
    x=archived_hl(b)
    assert pd.isna(x.frozen_hl.iloc[0])
    assert x.frozen_hl.iloc[19]==100.0
    assert (x.frozen_hl.dropna()==100).all()


def test_unverified_aggregate_episodes_locked_126_sessions():
    b,g=inputs()
    d,episodes=replay(b,g)
    assert d.proxy_trigger.sum() >= 1000
    assert len(episodes) >= 2
    assert episodes[0]["status"] == "UNVERIFIED_ARCHIVE_UNIVERSE_PROXY"
    # A lock is 126 market trading sessions, not 126 repeated rows.
    t0=pd.Timestamp(episodes[0]["start_date"])
    t1=pd.Timestamp(episodes[1]["start_date"])
    assert ((g.date>t0)&(g.date<=t1)).sum()>=126
    assert THRESHOLD==55 and STATUS.startswith("EXPLORATORY_")


def test_archive_replay_rejects_wrong_HL_metadata():
    b,_=inputs()
    b.loc[100,"hl_balance"]=0.25
    with pytest.raises(ValueError,match="reproducible from counts"):
        archived_hl(b)


def test_archive_replay_rejects_inconsistent_persistence():
    b,_=inputs()
    b.loc[50,"hl_persist_score"]=25.0
    with pytest.raises(ValueError,match="persistence inconsistent"):
        archived_hl(b)


def test_proxy_route_must_not_exceed_frozen_possible_bound():
    b,g=inputs()
    g["route_upper_bound_if_hl100"]=50.0
    with pytest.raises(ValueError,match="exceeds frozen upper bound"):
        replay(b,g)


def test_full_unknown_HL_is_not_turned_into_zero():
    b,g=inputs(nh=0,nl=0)
    # No finite H/L observation should be counted as a score.
    # Lack of 250 valid H/L dates must fail closed.
    with pytest.raises(ValueError,match="Too few|persistence inconsistent"):
        archived_hl(b)


def test_universe_shock_flag_is_not_same_as_delisting_evidence():
    b,_=inputs()
    b.loc[5,"issues"]=4000
    stats=anomaly_summary(b)
    assert stats["count_large_daily_universe_shifts"]==0  # before 2020
    ix=b.index[b.date>=pd.Timestamp("2020-01-01")][0]
    b.loc[ix,"issues"]=4000
    stats=anomaly_summary(b)
    assert stats["count_large_daily_universe_shifts"]>=1
    assert "does NOT prove delisting" in stats["definition"]
