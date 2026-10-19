from __future__ import annotations

import argparse
import json
import math
import urllib.parse
from datetime import datetime, timezone

import pandas as pd

import diagnose_route_c_ng1_failure as diag


ROUTE_MIN = 85.0
VALUATION_MIN = 98.0
CONCENTRATION_MIN = 85.0
SPREAD_MAX = 50.0
WARMUP_MONTHS = 120
OUTCOME_SESSIONS = 252

HOLDOUT_START = pd.Period("1963-01", freq="M")
HOLDOUT_END = pd.Period("1992-12", freq="M")
POSITIVE_WINDOWS = [
    ("1968-09", "1969-01"),
    ("1972-11", "1973-02"),
]
PROXY_AGREEMENT_MIN = 0.95


def period(x: str) -> pd.Period:
    return pd.Period(x, freq="M")


def fetch_price(symbol: str, start: str, end: str) -> pd.Series:
    p1 = int(pd.Timestamp(start, tz="UTC").timestamp())
    p2 = int((pd.Timestamp(end, tz="UTC") + pd.Timedelta(days=1)).timestamp())
    q = urllib.parse.quote(symbol, safe="")
    last = None
    for host in ("query1.finance.yahoo.com", "query2.finance.yahoo.com"):
        url = (
            f"https://{host}/v8/finance/chart/{q}"
            f"?period1={p1}&period2={p2}&interval=1d"
            "&events=history&includeAdjustedClose=false"
        )
        try:
            obj = diag.get(url).json()["chart"]["result"][0]
            ts = obj["timestamp"]
            close = obj["indicators"]["quote"][0]["close"]
            s = pd.Series(
                pd.to_numeric(close, errors="coerce"),
                index=(
                    pd.to_datetime(ts, unit="s", utc=True)
                    .tz_convert(None)
                    .normalize()
                ),
                dtype=float,
                name=symbol,
            ).dropna().sort_index()
            if len(s) < 500:
                raise ValueError(f"{symbol} history too short: {len(s)}")
            return s
        except Exception as exc:
            last = exc
    raise RuntimeError(f"{symbol} fetch failed: {last!r}")


def month_gate(price: pd.Series, month: str) -> dict | None:
    p = period(month)
    x = price.loc[p.start_time.normalize():p.end_time.normalize()]
    if x.empty:
        return None
    asof = pd.Timestamp(x.index[-1])
    close = float(x.iloc[-1])
    window = price.loc[asof - pd.DateOffset(months=24):asof]
    if window.empty:
        return None
    high = float(window.max())
    high_date = pd.Timestamp(window.idxmax())
    within = close >= 0.95 * high
    recent = high_date >= asof - pd.DateOffset(months=3)
    return {
        "asof": asof.date().isoformat(),
        "close": close,
        "high24": high,
        "high24_date": high_date.date().isoformat(),
        "within_5pct": bool(within),
        "high_within_3m": bool(recent),
        "passes": bool(within and recent),
    }


def proxy_overlap_sanity() -> dict:
    spx = fetch_price("^GSPC", "1993-01-01", "2000-02-01")
    spy = fetch_price("SPY", "1993-01-01", "2000-02-01")
    rows = []
    for p in pd.period_range("1995-02", "1999-12", freq="M"):
        a = month_gate(spx, str(p))
        b = month_gate(spy, str(p))
        if a is None or b is None:
            continue
        rows.append(
            {
                "month": str(p),
                "sp500_gate": a["passes"],
                "spy_gate": b["passes"],
                "agree": a["passes"] == b["passes"],
            }
        )
    agreements = sum(x["agree"] for x in rows)
    rate = agreements / len(rows) if rows else 0.0
    return {
        "start": rows[0]["month"] if rows else None,
        "end": rows[-1]["month"] if rows else None,
        "months": len(rows),
        "agreements": agreements,
        "agreement_rate": rate,
        "passes": bool(rate >= PROXY_AGREEMENT_MIN),
        "disagreements": [x for x in rows if not x["agree"]],
    }


def in_window(month: str, w: tuple[str, str]) -> bool:
    m = period(month)
    return period(w[0]) <= m <= period(w[1])


def collapse_episodes(states: list[dict]) -> list[list[dict]]:
    armed = [x for x in states if x["armed"]]
    out: list[list[dict]] = []
    for row in armed:
        if not out:
            out.append([row])
            continue
        prev = period(out[-1][-1]["effective_month"])
        cur = period(row["effective_month"])
        if cur.ordinal == prev.ordinal + 1:
            out[-1].append(row)
        else:
            out.append([row])
    return out


def classify_252(price: pd.Series, gate: dict) -> dict:
    anchor = pd.Timestamp(gate["asof"])
    signal = float(gate["close"])
    future = price.loc[price.index > anchor].iloc[:OUTCOME_SESSIONS]
    if len(future) < OUTCOME_SESSIONS:
        return {
            "complete": False,
            "future_sessions": int(len(future)),
        }
    rel = future / signal - 1.0
    forward = float(rel.iloc[-1] * 100.0)
    worst = float(rel.min() * 100.0)
    path = pd.Series(
        [signal] + [float(x) for x in future.tolist()],
        dtype=float,
    )
    dd = path / path.cummax() - 1.0
    max_dd = float(dd.min() * 100.0)
    if worst <= -15.0:
        label = "MAJOR_TOP"
    elif worst > -7.5 and forward > 0.0:
        label = "CLEAR_FALSE"
    else:
        label = "CORRECTION_OR_AMBIGUOUS"
    return {
        "complete": True,
        "end_date": pd.Timestamp(future.index[-1]).date().isoformat(),
        "forward_return_252_pct": forward,
        "worst_return_from_anchor_pct": worst,
        "max_peak_to_trough_dd_pct": max_dd,
        "classification": label,
    }


def build_states() -> tuple[list[dict], pd.Series, dict]:
    ff_rows, ff_meta = diag.build_ff25_concentration_rows()
    val_rows = diag.build_valuation_rows()
    credit = diag.all_credit_rows()
    spx = fetch_price("^GSPC", "1950-01-01", "1994-02-01")

    ff_map = {x["effective_month"]: x for x in ff_rows}
    raw_states = []
    common_count = 0

    for eff in sorted(ff_map, key=period):
        p = period(eff)
        f = ff_map[eff]
        v = diag.asof_row(val_rows, p)
        credit_source = str(p - 1).replace("-", "")
        c = credit.get(credit_source)
        if v is None or c is None:
            continue

        common_count += 1
        if p < HOLDOUT_START or p > HOLDOUT_END:
            continue
        if common_count < WARMUP_MONTHS:
            continue

        gate = month_gate(spx, eff)
        if gate is None:
            continue

        route = math.sqrt(
            float(v["valuation_score"])
            * float(f["concentration_breadth"])
        )
        spread = float(c["spread_shock_score"])
        gap_change = f["big_growth_gap_change_3m"]

        phase = {
            "route_pass": bool(route >= ROUTE_MIN),
            "valuation_pass": bool(
                float(v["valuation_score"]) >= VALUATION_MIN
            ),
            "concentration_pass": bool(
                float(f["concentration_breadth"]) >= CONCENTRATION_MIN
            ),
            "spread_pass": bool(spread <= SPREAD_MAX),
            "big_growth_gap_change_pass": bool(
                gap_change is not None and float(gap_change) > 0.0
            ),
        }
        pressure_pass = all(phase.values())
        armed = bool(pressure_pass and gate["passes"])

        raw_states.append(
            {
                "effective_month": eff,
                "common_history_months": common_count,
                "route_c_ng1": float(route),
                "valuation_score": float(v["valuation_score"]),
                "cape": float(v["cape"]),
                "concentration_breadth": float(
                    f["concentration_breadth"]
                ),
                "portfolio_exhaustion_score": float(
                    f["portfolio_exhaustion_score"]
                ),
                "leader_gap_score": float(f["leader_gap_score"]),
                "big_growth_gap_score": float(
                    f["big_growth_gap_score"]
                ),
                "big_growth_gap_change_3m": (
                    None if gap_change is None else float(gap_change)
                ),
                "spread_shock_score": spread,
                "spread_shock_raw": float(c["spread_shock_raw"]),
                "phase_gates": phase,
                "pressure_pass": pressure_pass,
                "top_location": gate,
                "armed": armed,
                "source_months": {
                    "ff25": f["source_month"],
                    "valuation": v["source_month"],
                    "credit": str(p - 1),
                },
            }
        )

    return raw_states, spx, ff_meta


def window_hits(states: list[dict]) -> dict:
    out = {}
    for a, b in POSITIVE_WINDOWS:
        out[f"{a}_to_{b}"] = [
            {
                "month": x["effective_month"],
                "route_c_ng1": x["route_c_ng1"],
                "valuation_score": x["valuation_score"],
                "concentration_breadth": x["concentration_breadth"],
                "spread_shock_score": x["spread_shock_score"],
                "big_growth_gap_change_3m": x[
                    "big_growth_gap_change_3m"
                ],
            }
            for x in states
            if x["armed"] and in_window(x["effective_month"], (a, b))
        ]
    return out


def evaluate() -> dict:
    proxy = proxy_overlap_sanity()
    states, spx, ff_meta = build_states()
    hits = window_hits(states)

    episodes = []
    for ep in collapse_episodes(states):
        first = ep[0]
        episodes.append(
            {
                "start": first["effective_month"],
                "end": ep[-1]["effective_month"],
                "armed_months": len(ep),
                "route_at_start": first["route_c_ng1"],
                "valuation_at_start": first["valuation_score"],
                "concentration_at_start": first[
                    "concentration_breadth"
                ],
                "spread_at_start": first["spread_shock_score"],
                "gap_change_at_start": first[
                    "big_growth_gap_change_3m"
                ],
                "anchor": first["top_location"],
                "outcome_252": classify_252(
                    spx, first["top_location"]
                ),
            }
        )

    complete = [
        x for x in episodes if x["outcome_252"]["complete"]
    ]
    major = sum(
        x["outcome_252"]["classification"] == "MAJOR_TOP"
        for x in complete
    )
    clear_false = sum(
        x["outcome_252"]["classification"] == "CLEAR_FALSE"
        for x in complete
    )
    n = len(complete)
    major_share = major / n if n else 0.0
    false_share = clear_false / n if n else 0.0
    positives_ok = all(bool(v) for v in hits.values())

    if n < 2:
        decision = "INSUFFICIENT_HOLDOUT_EVENTS"
    elif (
        proxy["passes"]
        and positives_ok
        and major_share >= 0.50
        and false_share <= 0.25
    ):
        decision = "ACCEPT_HOLDOUT_CANDIDATE"
    else:
        decision = "REJECT"

    near = sorted(
        states,
        key=lambda x: (
            sum(x["phase_gates"].values()),
            x["route_c_ng1"],
        ),
        reverse=True,
    )[:25]

    return {
        "schema_version": "market-top-route-c-ng2-pre1993-holdout-1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "research_only": True,
        "production_effect": "none",
        "legacy_route_c_status": "UNRESOLVED",
        "formula_version": "Route_C_NG2_PHASE_GATE",
        "preregistration": (
            "market-top-route-c-ng2-preregistration-1"
        ),
        "proxy_overlap": proxy,
        "sample": {
            "requested_start": str(HOLDOUT_START),
            "requested_end": str(HOLDOUT_END),
            "effective_start": (
                states[0]["effective_month"] if states else None
            ),
            "effective_end": (
                states[-1]["effective_month"] if states else None
            ),
            "monthly_states": len(states),
            "warmup_months": WARMUP_MONTHS,
        },
        "gates": {
            "route_c_ng1_min": ROUTE_MIN,
            "valuation_min": VALUATION_MIN,
            "concentration_breadth_min": CONCENTRATION_MIN,
            "spread_shock_score_max": SPREAD_MAX,
            "big_growth_gap_change_3m": ">0",
            "top_location_required": True,
        },
        "positive_window_hits": hits,
        "summary": {
            "armed_episodes": len(episodes),
            "complete_episodes": n,
            "major_top_count": major,
            "clear_false_count": clear_false,
            "major_top_share": major_share,
            "clear_false_share": false_share,
            "all_positive_windows_hit": positives_ok,
        },
        "episodes": episodes,
        "near_miss_states": [
            {
                "month": x["effective_month"],
                "route": x["route_c_ng1"],
                "valuation": x["valuation_score"],
                "concentration": x["concentration_breadth"],
                "spread": x["spread_shock_score"],
                "gap_change": x["big_growth_gap_change_3m"],
                "phase_pass_count": sum(
                    x["phase_gates"].values()
                ),
                "phase_gates": x["phase_gates"],
                "top_location": x["top_location"]["passes"],
                "armed": x["armed"],
            }
            for x in near
        ],
        "decision": decision,
        "source_meta": ff_meta,
        "post_validation_tuning_allowed": False,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--output")
    args = ap.parse_args()

    x = evaluate()
    print(json.dumps(x, indent=2))
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(x, f, indent=2)
            f.write("\n")


if __name__ == "__main__":
    main()
