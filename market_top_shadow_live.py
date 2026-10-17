from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Optional

from policyshock_v211 import ARMED_THRESHOLD, route_b


@dataclass(frozen=True)
class ShadowLiveSnapshot:
    asof: str
    rate_shock: float
    taper_shock: float
    policy_shock: float
    spy_close: float
    spy_high12_close: float
    dd12_pct: float
    ma10m_prev: float
    t_v24r: float
    price_breakdown_v24r: bool
    cape_current: Optional[float]
    valuation_proxy_score: Optional[float]
    size_support_proxy_score: Optional[float]
    size_weakness_proxy_score: Optional[float]
    route_b_proxy: Optional[float]
    valuation_canonical_score: Optional[float]
    size_weakness_canonical_score: Optional[float]
    route_b_authoritative: Optional[float]
    route_b_status: str
    status: str
    note: str


def build_shadow_snapshot(
    *,
    asof: str,
    rate_shock: float,
    taper_shock: float,
    policy_shock: float,
    spy_close: float,
    spy_high12_close: float,
    dd12_pct: float,
    ma10m_prev: float,
    t_v24r: float,
    price_breakdown_v24r: bool,
    cape_current: Optional[float] = None,
    valuation_proxy_score: Optional[float] = None,
    size_support_proxy_score: Optional[float] = None,
    valuation_canonical_score: Optional[float] = None,
    size_weakness_canonical_score: Optional[float] = None,
) -> ShadowLiveSnapshot:
    size_weakness_proxy = (
        None if size_support_proxy_score is None
        else 100.0 - float(size_support_proxy_score)
    )

    rb_proxy = None
    if valuation_proxy_score is not None and size_weakness_proxy is not None:
        rb_proxy = route_b(
            float(valuation_proxy_score),
            float(policy_shock),
            float(size_weakness_proxy),
        )

    rb_authoritative = None
    if valuation_canonical_score is not None and size_weakness_canonical_score is not None:
        rb_authoritative = route_b(
            float(valuation_canonical_score),
            float(policy_shock),
            float(size_weakness_canonical_score),
        )

    if rb_authoritative is None:
        route_b_status = "UNRESOLVED"
        status = "INPUT_INCOMPLETE"
        note = (
            "PolicyShock and T_v2.4R are valid research-live components, "
            "but canonical Route_B inputs are incomplete. Proxy Route_B is "
            "diagnostic only and cannot change state."
        )
    else:
        route_b_status = "ARMED" if rb_authoritative >= ARMED_THRESHOLD else "NOT_ARMED"
        status = "ROUTE_B_RESOLVED"
        note = (
            "Canonical Policy Route_B is resolved. Full Market Top state still "
            "requires canonical Route_A and Route_C; this remains research-only."
        )

    return ShadowLiveSnapshot(
        asof=asof,
        rate_shock=float(rate_shock),
        taper_shock=float(taper_shock),
        policy_shock=float(policy_shock),
        spy_close=float(spy_close),
        spy_high12_close=float(spy_high12_close),
        dd12_pct=float(dd12_pct),
        ma10m_prev=float(ma10m_prev),
        t_v24r=float(t_v24r),
        price_breakdown_v24r=bool(price_breakdown_v24r),
        cape_current=None if cape_current is None else float(cape_current),
        valuation_proxy_score=None if valuation_proxy_score is None else float(valuation_proxy_score),
        size_support_proxy_score=None if size_support_proxy_score is None else float(size_support_proxy_score),
        size_weakness_proxy_score=size_weakness_proxy,
        route_b_proxy=rb_proxy,
        valuation_canonical_score=None if valuation_canonical_score is None else float(valuation_canonical_score),
        size_weakness_canonical_score=None if size_weakness_canonical_score is None else float(size_weakness_canonical_score),
        route_b_authoritative=rb_authoritative,
        route_b_status=route_b_status,
        status=status,
        note=note,
    )


def as_json_dict(snapshot: ShadowLiveSnapshot) -> dict:
    return asdict(snapshot)
