from __future__ import annotations

import argparse
import json
import math
import urllib.parse
from datetime import datetime, timezone

import pandas as pd

from audit_market_top_ng1_a_independent import (
    BAA_URL,
    FF12_URL,
    FF25_URL,
    FF3_URL,
    GS10_URL,
    compounded,
    credit_snapshot_series,
    expanding_pct,
    parse_ff3,
    parse_portfolio_block,
    unzip_csv,
)

THRESHOLD = 85.0
HOLDOUT_START = pd.Period("1963-01", freq="M")
HOLDOUT_END = pd.Period("1992-12", freq="M")
WARMUP_MONTHS = 120
OUTCOME_SESSIONS = 252


def ym_period(ym: str) -> pd.Period:
    return pd.Period(f"{ym[:4]}-{ym[4:6]}", freq="M")


def period_ym(p: pd.Period) -> str:
    return f"{p.year:04d}{p.month:02d}"


def build_ff_rows() -> dict[str, dict]:
    ff25_text = unzip_csv(FF25_URL)
    ff12_text = unzip_csv(FF12_URL)
    ff3_text = unzip_csv(FF3_URL)

    _, r25 = parse_portfolio_block(
        ff25_text, "Average Value Weighted Returns -- Monthly", 25
    )
    h12, r12 = parse_portfolio_block(
        ff12_text, "Average Value Weighted Returns -- Monthly", 12
    )
    ff3 = parse_ff3(ff3_text)

    money_i = h12.index("Money")
    ff3_map = {ym: (i, mkt, smb) for i, (ym, mkt, smb) in enumerate(ff3)}
    r12_map = {ym: (i, vals) for i, (ym, vals) in enumerate(r12)}

    rows: list[dict] = []
    for i in range(5, len(r25)):
        ym, _ = r25[i]
        if ym not in ff3_map or ym not in r12_map:
            continue
        fi, _, _ = ff3_map[ym]
        qi, _ = r12_map[ym]
        if fi < 5 or qi < 5:
            continue

        p6 = [
            compounded([r25[k][1][j] for k in range(i - 5, i + 1)])
            for j in range(25)
        ]
        mkt6 = compounded([ff3[k][1] for k in range(fi - 5, fi + 1)])
        money6 = compounded(
            [r12[k][1][money_i] for k in range(qi - 5, qi + 1)]
        )

        rows.append(
            {
                "ym": ym,
                "portfolio_exhaustion_raw": (
                    1.0 - sum(x > mkt6 for x in p6) / 25.0
                ),
                "size_weakness_raw": -compounded(
                    [ff3[k][2] for k in range(fi - 5, fi + 1)]
                ),
                "finance_weakness_raw": -(money6 - mkt6),
            }
        )

    for raw_name, score_name in (
        ("portfolio_exhaustion_raw", "portfolio_exhaustion_score"),
        ("size_weakness_raw", "size_weakness_score"),
        ("finance_weakness_raw", "finance_weakness_score"),
    ):
        vals = [x[raw_name] for x in rows]
        for i, row in enumerate(rows):
            row[score_name] = expanding_pct(vals, i)

    return {x["ym"]: x for x in rows}


def build_credit_rows() -> dict[str, dict]:
    baa = credit_snapshot_series(BAA_URL, "BAA")
    gs10 = credit_snapshot_series(GS10_URL, "GS10")
    common = sorted(set(baa.index) & set(gs10.index))
    levels = [
        (d.strftime("%Y%m"), float(baa.loc[d] - gs10.loc[d]))
        for d in common
    ]

    rows: list[dict] = []
    for i in range(6, len(levels)):
        raw = max(
            levels[i][1] - levels[i - 3][1],
            levels[i][1] - levels[i - 6][1],
        )
        rows.append(
            {
                "ym": levels[i][0],
                "spread_shock_raw": raw,
            }
        )

    vals = [x["spread_shock_raw"] for x in rows]
    for i, row in enumerate(rows):
        row["spread_shock_score"] = expanding_pct(vals, i)

    return {x["ym"]: x for x in rows}


def align_ng2_rows(ff: dict[str, dict], credit: dict[str, dict]) -> list[dict]:
    ff_effective = {
        ym_period(ym) + 2: row
        for ym, row in ff.items()
    }
    credit_effective = {
        ym_period(ym) + 1: row
        for ym, row in credit.items()
    }

    periods = sorted(set(ff_effective) & set(credit_effective))
    rows: list[dict] = []
    for p in periods:
        f = ff_effective[p]
        c = credit_effective[p]
        rows.append(
            {
                "effective_period": p,
                "effective_month": str(p),
                "ff_source_month": f["ym"],
                "credit_source_month": c["ym"],
                "spread_shock_score": float(c["spread_shock_score"]),
                "finance_weakness_score": float(f["finance_weakness_score"]),
                "size_weakness_score": float(f["size_weakness_score"]),
                "portfolio_exhaustion_score": float(
                    f["portfolio_exhaustion_score"]
                ),
            }
        )

    gaps = [
        x["finance_weakness_score"] - x["spread_shock_score"]
        for x in rows
    ]
    for i, row in enumerate(rows):
        row["financial_lead_gap_raw"] = float(gaps[i])
        row["financial_lead_score"] = float(expanding_pct(gaps, i))
        row["credit_lead_stress_ng2"] = (
            row["spread_shock_score"]
            * row["finance_weakness_score"]
            * row["financial_lead_score"]
        ) ** (1.0 / 3.0)
        row["breadth_stress_ng2"] = math.sqrt(
            row["size_weakness_score"]
            * row["portfolio_exhaustion_score"]
        )
        row["route_a_ng2"] = math.sqrt(
            row["credit_lead_stress_ng2"]
            * row["breadth_stress_ng2"]
        )
        row["aligned_history_months"] = i + 1

    return rows


def yahoo_daily(symbol: str, start: str, end: str) -> pd.Series:
    start_ts = int(pd.Timestamp(start, tz="UTC").timestamp())
    end_ts = int(pd.Timestamp(end, tz="UTC").timestamp())
    symbol_q = urllib.parse.quote(symbol, safe="")

    last = None
    for host in ("query1.finance.yahoo.com", "query2.finance.yahoo.com"):
        url = (
            f"https://{host}/v8/finance/chart/{symbol_q}"
            f"?period1={start_ts}&period2={end_ts}&interval=1d"
            "&events=history&includeAdjustedClose=false"
        )
        try:
            from audit_market_top_ng1_a_independent import get

            obj = get(url).json()["chart"]["result"][0]
            ts = obj["timestamp"]
            close = obj["indicators"]["quote"][0]["close"]
            s = pd.Series(
                pd.to_numeric(close, errors="coerce"),
                index=(
                    pd.to_datetime(ts, unit="s", utc=True)
                    .tz_convert(None)
                    .normalize()
                ),
                name=symbol,
            ).dropna().sort_index()
            if len(s) < 100:
                raise ValueError(f"{symbol} history too short")
            return s
        except Exception as exc:
            last = exc
    raise RuntimeError(f"Yahoo {symbol} fetch failed: {last!r}")


def month_end_close(s: pd.Series, p: pd.Period) -> tuple[pd.Timestamp, float]:
    start = p.start_time.normalize()
    end = p.end_time.normalize()
    x = s.loc[start:end]
    if x.empty:
        raise ValueError(f"no price observations for {p}")
    return pd.Timestamp(x.index[-1]), float(x.iloc[-1])


def top_location_gate(s: pd.Series, p: pd.Period) -> dict:
    asof, close = month_end_close(s, p)
    window = s.loc[asof - pd.DateOffset(months=24):asof]
    if window.empty:
        raise ValueError(f"empty 24m price window for {p}")
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


def max_peak_to_trough_dd_pct(signal_close: float, future: pd.Series) -> float:
    vals = pd.Series(
        [signal_close] + [float(x) for x in future.tolist()],
        dtype=float,
    )
    peak = vals.cummax()
    dd = vals / peak - 1.0
    return float(dd.min() * 100.0)


def classify_episode(price: pd.Series, state: dict) -> dict:
    p = state["effective_period"]
    anchor_date, signal_close = month_end_close(price, p)
    future = price.loc[price.index > anchor_date].iloc[:OUTCOME_SESSIONS]
    if len(future) < OUTCOME_SESSIONS:
        return {
            "complete": False,
            "anchor_date": anchor_date.date().isoformat(),
            "signal_close": signal_close,
            "future_sessions": int(len(future)),
        }

    rel = future / signal_close - 1.0
    worst = float(rel.min() * 100.0)
    forward = float(rel.iloc[-1] * 100.0)
    max_dd = max_peak_to_trough_dd_pct(signal_close, future)

    if worst <= -20.0:
        label = "MAJOR_TOP_HIT"
    elif worst <= -10.0:
        label = "CORRECTION_RISK_NOT_MAJOR_TOP"
    else:
        label = "CLEAR_TOP_FALSE_POSITIVE"

    return {
        "complete": True,
        "anchor_date": anchor_date.date().isoformat(),
        "signal_close": signal_close,
        "h252_end_date": pd.Timestamp(future.index[-1]).date().isoformat(),
        "forward_return_pct": forward,
        "worst_return_from_anchor_pct": worst,
        "max_peak_to_trough_dd_pct": max_dd,
        "classification": label,
    }


def collapse_episodes(states: list[dict]) -> list[list[dict]]:
    armed = [x for x in states if x["armed"]]
    episodes: list[list[dict]] = []
    for row in armed:
        if not episodes:
            episodes.append([row])
            continue
        prev = episodes[-1][-1]["effective_period"]
        cur = row["effective_period"]
        if cur.ordinal == prev.ordinal + 1:
            episodes[-1].append(row)
        else:
            episodes.append([row])
    return episodes


def overlap_proxy_sanity() -> dict:
    spx = yahoo_daily("^GSPC", "1993-01-01", "2000-02-01")
    spy = yahoo_daily("SPY", "1993-01-01", "2000-02-01")

    rows = []
    for p in pd.period_range("1995-02", "1999-12", freq="M"):
        try:
            a = top_location_gate(spx, p)
            b = top_location_gate(spy, p)
        except ValueError:
            continue
        rows.append(
            {
                "month": str(p),
                "sp500_gate": a["passes"],
                "spy_gate": b["passes"],
                "agree": a["passes"] == b["passes"],
            }
        )
    agree = sum(x["agree"] for x in rows)
    return {
        "start": rows[0]["month"] if rows else None,
        "end": rows[-1]["month"] if rows else None,
        "months": len(rows),
        "agreements": agree,
        "agreement_rate": (agree / len(rows)) if rows else None,
        "disagreements": [x for x in rows if not x["agree"]],
    }


def run_screen() -> dict:
    ff = build_ff_rows()
    credit = build_credit_rows()
    aligned = align_ng2_rows(ff, credit)

    spx = yahoo_daily("^GSPC", "1960-01-01", "1995-02-01")

    states: list[dict] = []
    for row in aligned:
        p = row["effective_period"]
        if p < HOLDOUT_START or p > HOLDOUT_END:
            continue
        if row["aligned_history_months"] < WARMUP_MONTHS:
            continue
        gate = top_location_gate(spx, p)
        x = dict(row)
        x["top_location"] = gate
        x["pressure_pass"] = bool(x["route_a_ng2"] >= THRESHOLD)
        x["armed"] = bool(x["pressure_pass"] and gate["passes"])
        states.append(x)

    episodes = collapse_episodes(states)
    evaluated = []
    for ep in episodes:
        first = ep[0]
        outcome = classify_episode(spx, first)
        evaluated.append(
            {
                "start": first["effective_month"],
                "end": ep[-1]["effective_month"],
                "armed_months": len(ep),
                "route_at_start": first["route_a_ng2"],
                "components_at_start": {
                    "spread_shock_score": first["spread_shock_score"],
                    "finance_weakness_score": first["finance_weakness_score"],
                    "financial_lead_gap_raw": first["financial_lead_gap_raw"],
                    "financial_lead_score": first["financial_lead_score"],
                    "size_weakness_score": first["size_weakness_score"],
                    "portfolio_exhaustion_score": first[
                        "portfolio_exhaustion_score"
                    ],
                    "credit_lead_stress_ng2": first[
                        "credit_lead_stress_ng2"
                    ],
                    "breadth_stress_ng2": first["breadth_stress_ng2"],
                },
                "source_months_at_start": {
                    "fama_french": first["ff_source_month"],
                    "credit_spread": first["credit_source_month"],
                },
                "top_location_at_start": first["top_location"],
                "outcome": outcome,
            }
        )

    complete = [x for x in evaluated if x["outcome"]["complete"]]
    major = sum(
        x["outcome"].get("classification") == "MAJOR_TOP_HIT"
        for x in complete
    )
    false = sum(
        x["outcome"].get("classification") == "CLEAR_TOP_FALSE_POSITIVE"
        for x in complete
    )
    correction = sum(
        x["outcome"].get("classification")
        == "CORRECTION_RISK_NOT_MAJOR_TOP"
        for x in complete
    )

    if len(complete) < 2:
        decision = "INSUFFICIENT_HOLDOUT_EVENTS"
    elif (
        major >= 1
        and false == 0
        and major / len(complete) >= 0.5
    ):
        decision = "ACCEPT_HOLDOUT_CANDIDATE"
    else:
        decision = "REJECT"

    proxy = overlap_proxy_sanity()

    serial_states = []
    for x in states:
        y = dict(x)
        y.pop("effective_period", None)
        serial_states.append(y)

    return {
        "schema_version": "market-top-ng2-a-pre1993-holdout-1",
        "status": "COMPLETE",
        "decision": decision,
        "research_only": True,
        "production_effect": "none",
        "formula_version": "Route_A_NG2",
        "preregistration": (
            "research/market_top_ng2_a_preregistration.json"
        ),
        "holdout": {
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
        "decision_rule": {
            "min_armed_episodes": 2,
            "min_major_top_hits": 1,
            "max_clear_top_false_positives": 0,
            "min_major_top_hit_fraction": 0.5,
        },
        "summary": {
            "armed_episodes": len(evaluated),
            "complete_episodes": len(complete),
            "major_top_hits": major,
            "correction_risk_not_major_top": correction,
            "clear_top_false_positives": false,
            "major_top_hit_fraction": (
                major / len(complete) if complete else None
            ),
        },
        "episodes": evaluated,
        "proxy_overlap_sanity": proxy,
        "monthly_states": serial_states,
        "sources": {
            "fama_french_25": FF25_URL,
            "fama_french_12": FF12_URL,
            "fama_french_3": FF3_URL,
            "baa": BAA_URL,
            "gs10": GS10_URL,
            "holdout_price": "Yahoo Finance ^GSPC unadjusted close",
            "overlap_price": "Yahoo Finance SPY unadjusted close",
        },
        "governance": {
            "ng1_retuned": False,
            "ng2_post_result_tuning_allowed": False,
            "legacy_route_a_recovered": False,
            "production_pressure_inclusion_authorized": False,
        },
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output")
    args = ap.parse_args()

    result = run_screen()
    print(json.dumps(result, indent=2))

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2)
            f.write("\n")


if __name__ == "__main__":
    main()
