"""Frozen-score mathematical-gate tests; H/L is never inferred from rates."""
from __future__ import annotations

import math

import numpy as np
import pandas as pd
import pytest

from research.master_top_v218_historical_gates import (
    one_day, asof_rate, EVENTS, SCHEMA, sha256_series, treasury_mirror_csv
)
from master_top_v218 import route_score, policy_score


DAY = pd.Timestamp("2022-01-03")


def mock_rates(start="2021-01-01", end="2022-01-03", base=1.0):
    s = pd.Series(float(base), index=pd.bdate_range(start,end))
    # Positive 1M and 6M rate shocks both saturate to score=100.
    s.loc[s.index>=pd.Timestamp("2021-07-01")] = 1.0
    s.loc[s.index>=pd.Timestamp("2022-01-03")] = 2.0
    return s


def test_known_breadth_one_hundred_matches_frozen_route_upper_bound():
    x = one_day(DAY, 100.0, 100.0, mock_rates())
    assert x["policy"] == 100.0
    assert x["status"] == "CONDITIONALLY_POSSIBLE_IF_MISSING_HL_SUFFICIENT"
    assert x["route_upper_bound_if_hl100"] == 100.0
    assert x["hl_min_for_threshold_if_gate_pass"] == 75.0
    assert x["route_upper_bound_if_hl100"] == route_score(100.0,100.0,1.0)


def test_top_gate_is_strict_even_with_high_policy():
    x=one_day(DAY, 94.0,100.0,mock_rates())
    assert x["status"] == "TOP_GATE_IMPOSSIBLE"
    assert x["route_upper_bound_if_hl100"] == 0.0


def test_partial_top_proximity_blocks_even_high_policy():
    # 96% top ratio -> top proximity 0.2, upper <= 44.7214.
    x=one_day(DAY,96.0,100.0,mock_rates())
    assert x["status"] == "POLICY_UPPER_BOUND_IMPOSSIBLE"
    assert x["route_upper_bound_if_hl100"] == pytest.approx(44.72135955,abs=1e-6)


def test_low_policy_blocks_regardless_of_unknown_hl():
    r=pd.Series(1.0,index=pd.bdate_range("2021-01-01","2022-01-03"))
    x=one_day(DAY,100.0,100.0,r)
    assert x["policy"] == 0.0
    assert x["status"] == "POLICY_UPPER_BOUND_IMPOSSIBLE"


def test_missing_historical_rates_fail_closed():
    r=pd.Series([1.0],index=[pd.Timestamp("2021-01-03")])
    x=one_day(DAY,100.0,100.0,r)
    assert x["status"] == "RATE_DATA_UNAVAILABLE"
    assert x["route_upper_bound_if_hl100"] is None
    blocked=one_day(DAY,90.0,100.0,r)
    assert blocked["status"] == "TOP_GATE_IMPOSSIBLE"


def test_lagged_asof_rates_never_take_future_values():
    r=pd.Series([1.0,3.0],index=[pd.Timestamp("2021-12-31"),pd.Timestamp("2022-01-04")])
    y,d=asof_rate(r,DAY)
    assert d == "2021-12-31" and y == 1.0


def test_old_dgs2_observation_cannot_be_used():
    r=pd.Series([1.0], index=[pd.Timestamp("2021-12-01")])
    with pytest.raises(ValueError,match="Stale"):
        asof_rate(r,DAY)


def test_provenance_and_controls_are_fixed():
    assert SCHEMA=="market-top-v218-two-gate-historical-eligibility-v1"
    assert "2005_2006_control" in EVENTS and "2021_2022_bear" in EVENTS
    assert "2017_control" in EVENTS and "2023_control" in EVENTS


def test_digest_changes_if_rate_changes():
    a=pd.Series([1.0],index=[DAY])
    b=pd.Series([1.1],index=[DAY])
    assert sha256_series(a)!=sha256_series(b)


def test_public_treasury_mirror_requires_independent_pin_checks(monkeypatch):
    import research.master_top_v218_historical_gates as h
    monkeypatch.setattr(h,"validate_rates",lambda s: None)
    csv=("date,2Y\n2006-06-29,5.21\n2022-01-03,0.78\n2026-10-21,4.81\n")
    s=treasury_mirror_csv(csv)
    assert s.attrs["provider"].startswith("US Treasury 2Y CMT")
    assert s.loc[pd.Timestamp("2026-10-21")]==4.81
    broken=csv.replace("2022-01-03,0.78","2022-01-03,1.78")
    with pytest.raises(RuntimeError,match="disagrees"):
        treasury_mirror_csv(broken)
