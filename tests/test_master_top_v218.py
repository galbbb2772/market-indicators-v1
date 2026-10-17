import math
import sys

import pandas as pd
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from master_top_v218 import (
    append_hilo_ledger,
    hl_persistence_score,
    live_hl_from_ledger,
    policy_score,
    rate_shock_1m,
    rate_shock_6m,
    reconstruct_hilo,
    route_score,
    top_proximity,
)


def test_rate_components():
    assert math.isclose(rate_shock_6m(54), 73.3333333333, rel_tol=1e-9)
    assert math.isclose(rate_shock_1m(18), 90.0, rel_tol=1e-9)
    assert math.isclose(policy_score(54, 18), math.sqrt(73.3333333333 * 90), rel_tol=1e-8)


def test_top_proximity_continuous():
    assert top_proximity(0.95) == 0
    assert math.isclose(top_proximity(0.975), 0.5, rel_tol=1e-12)
    assert top_proximity(1.0) == 1


def test_control_2006_is_below_trigger():
    s = route_score(policy=100.0, hl_score=97.4679434481, top_ratio=0.9601)
    assert 44.0 < s < 45.0
    assert s < 55.0


def test_2021_12_15_major_bear_warning_survives():
    s = route_score(policy=75.72, hl_score=84.84, top_ratio=0.9995)
    assert 69.0 < s < 70.0
    assert s >= 55.0


def test_2026_09_10_live_signal_survives():
    s = route_score(policy=100.0, hl_score=76.49, top_ratio=0.9742)
    assert 60.0 < s < 62.0
    assert s >= 55.0


def test_hl_persistence_definition():
    vals = [-0.30] * 15 + [0.10] * 5
    score = hl_persistence_score(vals)
    mean = sum(vals) / 20
    neg_frac = 15 / 20
    expected = 100 * math.sqrt(min(1, max(0, -mean / 0.30)) * neg_frac)
    assert math.isclose(score, expected, rel_tol=1e-12)


def test_reconstruct_hilo_requires_252_prior_sessions_and_uses_intraday_extremes():
    dates = pd.bdate_range("2025-01-01", periods=253)
    rows = []
    for symbol in ("AAA", "BBB"):
        for i, dt in enumerate(dates):
            rows.append({
                "date": dt,
                "symbol": symbol,
                "high": float(i + 2),
                "low": float(i + 1),
            })
    out = reconstruct_hilo(pd.DataFrame(rows))
    assert int(out.iloc[-2]["hilo_eligible"]) == 0
    assert int(out.iloc[-1]["hilo_eligible"]) == 2
    assert int(out.iloc[-1]["new_highs"]) == 2
    assert int(out.iloc[-1]["new_lows"]) == 0


def test_live_source_epoch_requires_full_20_session_warmup(tmp_path):
    ledger_path = tmp_path / "ledger.csv"
    obs = {
        "source_epoch": "test_epoch",
        "universe": 5000,
        "new_highs": 100,
        "new_lows": 300,
        "hl_balance": -0.5,
        "update_modes": {"delayed": 5000},
        "exchanges": {"NYSE": 1600, "NASDAQ": 3200, "AMEX": 200},
    }
    ledger = None
    dates = pd.bdate_range("2026-10-19", periods=20)
    for i, dt in enumerate(dates):
        row = dict(obs)
        row["hl_balance"] = -0.5 if i < 15 else 0.1
        ledger = append_hilo_ledger(ledger_path, str(dt.date()), row)

    score19, warm19 = live_hl_from_ledger(ledger.iloc[:-1], "test_epoch")
    assert warm19 == 19
    assert math.isnan(score19)

    score20, warm20 = live_hl_from_ledger(ledger, "test_epoch")
    assert warm20 == 20
    assert not math.isnan(score20)
    expected = hl_persistence_score([-0.5] * 15 + [0.1] * 5)
    assert math.isclose(score20, expected, rel_tol=1e-12)
