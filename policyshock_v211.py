from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

ARMED_THRESHOLD = 85.0
RATE_WEIGHT = 0.60
TAPER_WEIGHT = 0.40

RATE_FLOOR_BP = 10.0
RATE_SPAN_BP = 60.0
PREV_EXPANSION_FULL = 0.03
DECEL_FULL = 0.01


@dataclass(frozen=True)
class PolicyShockResult:
    rate_shock: Optional[float]
    taper_shock: Optional[float]
    policy_shock: Optional[float]


def _clip01(x: float) -> float:
    return max(0.0, min(1.0, float(x)))


def rate_shock(
    dgs2_latest_pct: Optional[float],
    dgs2_6m_ago_pct: Optional[float],
) -> Optional[float]:
    """Frozen V2.1.1 rate shock.

    Inputs are Treasury yields in percentage points (e.g. 0.73 means 0.73%).
    The caller MUST supply publication-time-safe observations only.
    """
    if dgs2_latest_pct is None or dgs2_6m_ago_pct is None:
        return None
    delta_bp = (float(dgs2_latest_pct) - float(dgs2_6m_ago_pct)) * 100.0
    return 100.0 * _clip01((delta_bp - RATE_FLOOR_BP) / RATE_SPAN_BP)


def taper_shock(
    walcl_now: Optional[float],
    walcl_13w_ago: Optional[float],
    walcl_26w_ago: Optional[float],
    *,
    series_started: bool = True,
) -> Optional[float]:
    """Frozen V2.1.1 QE->taper shock.

    WALCL values may use any consistent unit.
    The caller MUST supply publication-time-safe released observations only.

    If the historical WALCL series did not yet exist, return 0 by construction.
    If it should exist but an input is missing, return None rather than treating
    a data outage as zero risk.
    """
    if not series_started:
        return 0.0
    if walcl_now is None or walcl_13w_ago is None or walcl_26w_ago is None:
        return None

    l0 = float(walcl_now)
    l13 = float(walcl_13w_ago)
    l26 = float(walcl_26w_ago)
    if l0 <= 0 or l13 <= 0 or l26 <= 0:
        raise ValueError("WALCL levels must be positive")

    g_prev = l13 / l26 - 1.0
    g_cur = l0 / l13 - 1.0

    expansion_gate = _clip01(g_prev / PREV_EXPANSION_FULL)
    decel_gate = _clip01((g_prev - g_cur) / DECEL_FULL)
    return 100.0 * expansion_gate * decel_gate


def policy_shock(
    rate: Optional[float],
    taper: Optional[float],
) -> Optional[float]:
    if rate is None or taper is None:
        return None
    return RATE_WEIGHT * float(rate) + TAPER_WEIGHT * float(taper)


def route_b(
    valuation: Optional[float],
    policy: Optional[float],
    size_weakness: Optional[float],
) -> Optional[float]:
    if valuation is None or policy is None or size_weakness is None:
        return None
    vals = [float(valuation), float(policy), float(size_weakness)]
    if any(v < 0 for v in vals):
        raise ValueError("Route_B inputs must be non-negative")
    return (vals[0] * vals[1] * vals[2]) ** (1.0 / 3.0)


def compute_policy_shock(
    *,
    dgs2_latest_pct: Optional[float],
    dgs2_6m_ago_pct: Optional[float],
    walcl_now: Optional[float],
    walcl_13w_ago: Optional[float],
    walcl_26w_ago: Optional[float],
    walcl_series_started: bool = True,
) -> PolicyShockResult:
    r = rate_shock(dgs2_latest_pct, dgs2_6m_ago_pct)
    t = taper_shock(
        walcl_now,
        walcl_13w_ago,
        walcl_26w_ago,
        series_started=walcl_series_started,
    )
    return PolicyShockResult(r, t, policy_shock(r, t))
