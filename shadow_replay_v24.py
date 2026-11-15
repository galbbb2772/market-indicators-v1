from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import Enum
import calendar
from typing import Optional


PRESSURE_THRESHOLD = 85.0
PRICE_T_THRESHOLD = 70.0
PRICE_DRAWDOWN_THRESHOLD_PCT = 4.5
EARLY_BREADTH_DELTA_THRESHOLD = 10.0
ARMED_MAX_MONTHS = 6


class State(str, Enum):
    IDLE = "IDLE"
    ARMED = "ARMED"
    TRIGGERED = "TRIGGERED"


@dataclass(frozen=True)
class Snapshot:
    asof: date
    route_a: float
    route_b: float
    route_c: float
    within_5pct_of_24m_high: bool
    high_formed_within_3m: bool
    breadth_delta_3m: Optional[float] = None
    t_score: Optional[float] = None
    drawdown_from_12m_high_pct: Optional[float] = None


@dataclass
class ReplayState:
    state: State = State.IDLE
    armed_at: Optional[date] = None
    armed_expires_at: Optional[date] = None
    triggered_at: Optional[date] = None
    trigger_reason: Optional[str] = None


def pressure(x: Snapshot) -> float:
    return max(float(x.route_a), float(x.route_b), float(x.route_c))


def _add_months(d: date, months: int) -> date:
    month0 = d.month - 1 + months
    year = d.year + month0 // 12
    month = month0 % 12 + 1
    day = min(d.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def early_breadth_trigger(x: Snapshot) -> bool:
    """Accepted V2.4 behavior: direct early trigger, independent of ARMED."""
    return (
        pressure(x) >= PRESSURE_THRESHOLD
        and x.route_c >= PRESSURE_THRESHOLD
        and x.breadth_delta_3m is not None
        and x.breadth_delta_3m >= EARLY_BREADTH_DELTA_THRESHOLD
    )


def can_arm(x: Snapshot) -> bool:
    return (
        pressure(x) >= PRESSURE_THRESHOLD
        and x.within_5pct_of_24m_high
        and x.high_formed_within_3m
    )


def price_breakdown_trigger(x: Snapshot) -> bool:
    return (
        x.t_score is not None
        and x.drawdown_from_12m_high_pct is not None
        and x.t_score >= PRICE_T_THRESHOLD
        and x.drawdown_from_12m_high_pct >= PRICE_DRAWDOWN_THRESHOLD_PCT
    )


def step(state: ReplayState, x: Snapshot) -> ReplayState:
    if state.state == State.TRIGGERED:
        return state

    if early_breadth_trigger(x):
        return ReplayState(
            state=State.TRIGGERED,
            triggered_at=x.asof,
            trigger_reason="EARLY_BREADTH",
        )

    if (
        state.state == State.ARMED
        and state.armed_expires_at is not None
        and x.asof > state.armed_expires_at
    ):
        state = ReplayState()

    if state.state == State.ARMED and price_breakdown_trigger(x):
        return ReplayState(
            state=State.TRIGGERED,
            armed_at=state.armed_at,
            armed_expires_at=state.armed_expires_at,
            triggered_at=x.asof,
            trigger_reason="PRICE_BREAKDOWN",
        )

    if state.state == State.IDLE and can_arm(x):
        return ReplayState(
            state=State.ARMED,
            armed_at=x.asof,
            armed_expires_at=_add_months(x.asof, ARMED_MAX_MONTHS),
        )

    return state


def replay(rows: list[Snapshot]) -> ReplayState:
    s = ReplayState()
    for row in sorted(rows, key=lambda z: z.asof):
        s = step(s, row)
    return s
