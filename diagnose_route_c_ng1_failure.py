from __future__ import annotations

import argparse
import json
import math
import statistics
import urllib.parse
from datetime import datetime, timezone

import pandas as pd

from audit_market_top_ng1_a_independent import (
    FF25_URL,
    FF3_URL,
    compounded,
    expanding_pct,
    get,
    parse_ff3,
    parse_portfolio_block,
    unzip_csv,
)
from diagnose_ng1_a_component_cases import all_credit_rows
from market_top_canonical_inputs import valuation_history
from update_market_top_shadow import fetch_shiller


SELECTED_MONTHS = [
    "1995-07",
    "1996-03",
    "1997-01",
    "1997-04",
    "1998-04",
    "1998-06",
    "1998-11",
    "1999-04",
    "1999-06",
    "2000-03",
    "2017-07",
    "2017-10",
    "2019-10",
    "2020-08",
    "2020-11",
    "2021-10",
    "2021-11",
    "2021-12",
]

KNOWN_EPISODES = [
    ("1995-07", "1995-07"),
    ("1996-03", "1996-04"),
    ("1997-01", "1997-01"),
    ("1997-04", "1997-04"),
    ("1998-04", "1998-06"),
    ("1998-11", "1999-04"),
    ("1999-06", "1999-06"),
    ("2000-03", "2000-03"),
    ("2017-07", "2017-10"),
    ("2019-10", "2019-10"),
    ("2020-08", "2020-08"),
    ("2020-11", "2020-11"),
    ("2021-10", "2021-12"),
]


def period(x: str) -> pd.Period:
    return pd.Period(x, freq="M")


def period_from_ym(ym: str) -> pd.Period:
    return pd.Period(f"{ym[:4]}-{ym[4:6]}", freq="M")


def build_ff25_concentration_rows() -> tuple[list[dict], dict]:
    ff25_text = unzip_csv(FF25_URL)
    ff3_text = unzip_csv(FF3_URL)

    headers, r25 = parse_portfolio_block(
        ff25_text, "Average Value Weighted Returns -- Monthly", 25
    )
    ff3 = parse_ff3(ff3_text)
    ff3_map = {ym: (i, mkt, smb) for i, (ym, mkt, smb) in enumerate(ff3)}

    big_growth_i = None
    for i, h in enumerate(headers):
        z = h.lower().replace(" ", "")
        if "big" in z and ("lobm" in z or "bm1" in z):
            big_growth_i = i
            break
    if big_growth_i is None:
        big_growth_i = 20

    rows = []
    for i in range(5, len(r25)):
        ym, vals = r25[i]
        if ym not in ff3_map:
            continue
        fi, _, _ = ff3_map[ym]
        if fi < 5:
            continue

        p6 = [
            compounded([r25[k][1][j] for k in range(i - 5, i + 1)])
            for j in range(25)
        ]
        mkt6 = compounded([ff3[k][1] for k in range(fi - 5, fi + 1)])
        med = float(statistics.median(p6))
        leader = float(max(p6))
        big = float(p6[big_growth_i])

        rows.append(
            {
                "source_month": str(period_from_ym(ym)),
                "effective_month": str(period_from_ym(ym) + 2),
                "market_6m": float(mkt6),
                "median_portfolio_6m": med,
                "leader_6m": leader,
                "big_growth_6m": big,
                "portfolio_exhaustion_raw": (
                    1.0 - sum(x > mkt6 for x in p6) / 25.0
                ),
                "leader_gap_raw": leader - med,
                "big_growth_gap_raw": big - med,
                "big_growth_is_leader": bool(
                    math.isclose(big, leader, rel_tol=0.0, abs_tol=1e-9)
                ),
                "big_growth_rank_desc": int(
                    1 + sum(x > big for x in p6)
                ),
            }
        )

    for raw_name, score_name in (
        ("portfolio_exhaustion_raw", "portfolio_exhaustion_score"),
        ("leader_gap_raw", "leader_gap_score"),
        ("big_growth_gap_raw", "big_growth_gap_score"),
    ):
        vals = [float(x[raw_name]) for x in rows]
        for i, row in enumerate(rows):
            row[score_name] = float(expanding_pct(vals, i))

    for i, row in enumerate(rows):
        row["concentration_breadth"] = (
            row["portfolio_exhaustion_score"]
            * row["leader_gap_score"]
            * row["big_growth_gap_score"]
        ) ** (1.0 / 3.0)

        if i >= 3:
            row["big_growth_gap_change_3m"] = (
                row["big_growth_gap_raw"]
                - rows[i - 3]["big_growth_gap_raw"]
            )
            row["exhaustion_change_3m"] = (
                row["portfolio_exhaustion_raw"]
                - rows[i - 3]["portfolio_exhaustion_raw"]
            )
        else:
            row["big_growth_gap_change_3m"] = None
            row["exhaustion_change_3m"] = None

        start = max(0, i - 5)
        hist = rows[start:i + 1]
        row["big_growth_gap_6m_mean"] = float(
            sum(x["big_growth_gap_raw"] for x in hist) / len(hist)
        )
        row["big_growth_leader_share_6m"] = float(
            sum(x["big_growth_is_leader"] for x in hist) / len(hist)
        )

    return rows, {
        "big_growth_header": headers[big_growth_i],
        "big_growth_index": big_growth_i,
        "ff25_last_source_month": rows[-1]["source_month"],
    }


def build_valuation_rows() -> list[dict]:
    shiller, meta = fetch_shiller()
    shiller = shiller.sort_values("date").reset_index(drop=True)
    scores = valuation_history(shiller["cape"].tolist())
    out = []
    for i, row in shiller.iterrows():
        src = pd.Period(pd.Timestamp(row["date"]), freq="M")
        out.append(
            {
                "source_month": str(src),
                "effective_month": str(src + 1),
                "cape": float(row["cape"]),
                "valuation_score": float(scores[i]),
            }
        )
    return out


def asof_row(rows: list[dict], effective: pd.Period) -> dict | None:
    best = None
    for row in rows:
        if period(row["effective_month"]) <= effective:
            best = row
        else:
            break
    return best


def fetch_spy() -> pd.Series:
    p1 = int(pd.Timestamp("1993-01-01", tz="UTC").timestamp())
    p2 = int(pd.Timestamp("2026-10-20", tz="UTC").timestamp())
    symbol = urllib.parse.quote("SPY", safe="")
    last = None
    for host in ("query1.finance.yahoo.com", "query2.finance.yahoo.com"):
        url = (
            f"https://{host}/v8/finance/chart/{symbol}"
            f"?period1={p1}&period2={p2}&interval=1d"
            "&events=history&includeAdjustedClose=false"
        )
        try:
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
                dtype=float,
            ).dropna().sort_index()
            if len(s) < 5000:
                raise ValueError("SPY history too short")
            return s
        except Exception as exc:
            last = exc
    raise RuntimeError(f"SPY fetch failed: {last!r}")


def month_gate(price: pd.Series, month: str) -> dict | None:
    p = period(month)
    x = price.loc[p.start_time.normalize():p.end_time.normalize()]
    if x.empty:
        return None
    asof = pd.Timestamp(x.index[-1])
    close = float(x.iloc[-1])
    window = price.loc[asof - pd.DateOffset(months=24):asof]
    high = float(window.max())
    high_date = pd.Timestamp(window.idxmax())
    within = close >= 0.95 * high
    recent = high_date >= asof - pd.DateOffset(months=3)
    return {
        "asof": asof.date().isoformat(),
        "close": close,
        "high24": high,
        "high24_date": high_date.date().isoformat(),
        "passes": bool(within and recent),
    }


def classify_252(price: pd.Series, month: str) -> dict | None:
    gate = month_gate(price, month)
    if gate is None:
        return None
    anchor = pd.Timestamp(gate["asof"])
    signal = float(gate["close"])
    future = price.loc[price.index > anchor].iloc[:252]
    if len(future) < 252:
        return {"complete": False, "sessions": int(len(future))}
    rel = future / signal - 1.0
    return {
        "complete": True,
        "forward_252_pct": float(rel.iloc[-1] * 100.0),
        "worst_from_signal_pct": float(rel.min() * 100.0),
        "max_peak_to_trough_pct": float(
            ((future / future.cummax()) - 1.0).min() * 100.0
        ),
    }


def build_diagnostic() -> dict:
    ff_rows, ff_meta = build_ff25_concentration_rows()
    val_rows = build_valuation_rows()
    credit = all_credit_rows()
    price = fetch_spy()

    ff_map = {x["effective_month"]: x for x in ff_rows}

    states = {}
    for eff, f in ff_map.items():
        p = period(eff)
        if p < period("1993-01") or p > period("2022-12"):
            continue
        v = asof_row(val_rows, p)
        if v is None:
            continue
        cb = float(f["concentration_breadth"])
        route = math.sqrt(float(v["valuation_score"]) * cb)
        credit_source = str(p - 1).replace("-", "")
        c = credit.get(credit_source)
        gate = month_gate(price, eff)
        states[eff] = {
            **f,
            "valuation_source_month": v["source_month"],
            "cape": v["cape"],
            "valuation_score": v["valuation_score"],
            "route_c_ng1_reconstructed": float(route),
            "spread_shock_score": (
                None if c is None else float(c["spread_shock_score"])
            ),
            "spread_shock_raw": (
                None if c is None else float(c["spread_shock_raw"])
            ),
            "top_location": gate,
        }

    selected = {
        m: states.get(m)
        for m in SELECTED_MONTHS
        if m in states
    }

    episode_outcomes = []
    for start, end in KNOWN_EPISODES:
        x = states.get(start)
        if x is None:
            continue
        episode_outcomes.append(
            {
                "start": start,
                "end": end,
                "route_at_start": x["route_c_ng1_reconstructed"],
                "valuation_score": x["valuation_score"],
                "concentration_breadth": x["concentration_breadth"],
                "spread_shock_score": x["spread_shock_score"],
                "big_growth_rank_desc": x["big_growth_rank_desc"],
                "big_growth_leader_share_6m": x[
                    "big_growth_leader_share_6m"
                ],
                "big_growth_gap_change_3m": x[
                    "big_growth_gap_change_3m"
                ],
                "outcome_252": classify_252(price, start),
            }
        )

    return {
        "schema_version": "market-top-route-c-ng1-failure-diagnostic-1",
        "status": "HYPOTHESIS_GENERATION_ONLY",
        "research_only": True,
        "production_effect": "none",
        "legacy_route_c_status": "UNRESOLVED",
        "ng1_decision": "REJECT",
        "formula_changed": False,
        "purpose": (
            "Compare frozen Route_C_NG1 component structure across its "
            "true-target and false/additional ARMED episodes before any "
            "Route_C NG2 hypothesis is preregistered."
        ),
        "source_meta": ff_meta,
        "selected_months": selected,
        "episode_outcomes": episode_outcomes,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--output")
    args = ap.parse_args()

    x = build_diagnostic()
    print(json.dumps(x, indent=2))
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(x, f, indent=2)
            f.write("\n")


if __name__ == "__main__":
    main()
