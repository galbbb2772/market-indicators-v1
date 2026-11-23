from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


T_THRESHOLD = 70.0
DRAWDOWN_GUARD_PCT = 4.5

DD_FLOOR_PCT = 1.0
DD_FULL_PCT = 7.0
MA_FULL_GAP_PCT = 4.0

DD_WEIGHT = 0.80
MA_WEIGHT = 0.20


def _clip01(x):
    return np.clip(x, 0.0, 1.0)


def dd_score(dd12_pct):
    """0 at <=1% drawdown, 100 at >=7% drawdown."""
    return 100.0 * _clip01((dd12_pct - DD_FLOOR_PCT) / (DD_FULL_PCT - DD_FLOOR_PCT))


def ma_score(close, ma10m_prev):
    """0 at/above the prior-completed-month 10M MA, 100 at >=4% below."""
    gap_pct = 100.0 * np.maximum(0.0, (ma10m_prev - close) / ma10m_prev)
    return 100.0 * _clip01(gap_pct / MA_FULL_GAP_PCT)


def t_v24r(dd12_pct, close, ma10m_prev):
    """Preregistered T_v2.4R score. This is NOT the missing original V2.4 T."""
    return DD_WEIGHT * dd_score(dd12_pct) + MA_WEIGHT * ma_score(close, ma10m_prev)


def price_breakdown_gate(t_score, dd12_pct):
    return (t_score >= T_THRESHOLD) & (dd12_pct >= DRAWDOWN_GUARD_PCT)


def previous_10_completed_month_ma(close: pd.Series) -> pd.Series:
    """Daily series of the average of the 10 completed month-end closes.

    A day in month M can only use month-end closes from months strictly before M.
    """
    s = pd.Series(close, dtype=float).dropna().sort_index()
    if not isinstance(s.index, pd.DatetimeIndex):
        raise TypeError("close must use a DatetimeIndex")

    periods = s.index.to_period("M")
    month_end = s.groupby(periods).last()
    p_list = list(month_end.index)

    ma_by_period = {}
    for i, p in enumerate(p_list):
        if i >= 10:
            ma_by_period[p] = float(month_end.iloc[i - 10:i].mean())

    vals = [ma_by_period.get(p, np.nan) for p in periods]
    return pd.Series(vals, index=s.index, name="ma10m_prev", dtype=float)


def compute_t_v24r_series(close: pd.Series) -> pd.DataFrame:
    """Compute the PIT-safe daily T_v2.4R diagnostics from close prices."""
    s = pd.Series(close, dtype=float).dropna().sort_index()
    if not isinstance(s.index, pd.DatetimeIndex):
        raise TypeError("close must use a DatetimeIndex")

    high12 = s.rolling(252, min_periods=252).max()
    dd12 = 100.0 * (high12 - s) / high12
    ma10 = previous_10_completed_month_ma(s)
    gap = 100.0 * np.maximum(0.0, (ma10 - s) / ma10)
    dds = dd_score(dd12)
    mas = ma_score(s, ma10)
    score = DD_WEIGHT * dds + MA_WEIGHT * mas

    return pd.DataFrame(
        {
            "close": s,
            "high12_close": high12,
            "dd12_pct": dd12,
            "ma10m_prev": ma10,
            "ma_gap_pct": gap,
            "dd_score": dds,
            "ma_score": mas,
            "t_v24r": score,
            "price_breakdown_v24r": price_breakdown_gate(score, dd12),
        }
    )
