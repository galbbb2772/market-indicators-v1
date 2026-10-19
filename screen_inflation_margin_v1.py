from __future__ import annotations

import argparse
import io
import json
import math
import urllib.parse
from datetime import datetime, timezone

import pandas as pd

from audit_market_top_ng1_a_independent import get

CPI_ID = "CPIAUCSL"
ULC_ID = "PRS85006111"
UNIT_PROFIT_ID = "A466RD3Q052SBEA"

THRESHOLD = 85.0
WARMUP_MONTHS = 120
OUTCOME_SESSIONS = 252

TRAINING_WINDOWS = [
    ("1965-12", "1966-06"),
    ("1972-10", "1973-03"),
]
POSITIVE_WINDOWS = [
    ("1968-08", "1969-02"),
    ("1980-08", "1981-02"),
]
NEGATIVE_WINDOWS = [
    ("1987-06", "1987-10"),
    ("1998-06", "1998-10"),
    ("2000-01", "2000-04"),
    ("2007-06", "2007-10"),
    ("2018-08", "2018-12"),
]


def expanding_pct(values: list[float], i: int) -> float:
    v = float(values[i])
    hist = values[: i + 1]
    return 100.0 * sum(float(x) <= v for x in hist) / len(hist)


def period(s: str) -> pd.Period:
    return pd.Period(s, freq="M")


def fetch_fred_series(series_id: str) -> pd.Series:
    url = (
        "https://fred.stlouisfed.org/graph/fredgraph.csv?id="
        + urllib.parse.quote(series_id)
    )
    r = get(url)
    df = pd.read_csv(io.StringIO(r.text), dtype=str)
    if df.empty or "DATE" not in df.columns or series_id not in df.columns:
        raise ValueError(f"unexpected FRED payload for {series_id}")
    idx = pd.to_datetime(df["DATE"], errors="coerce")
    vals = pd.to_numeric(
        df[series_id].astype(str).str.strip().replace({".": None, "": None}),
        errors="coerce",
    )
    s = pd.Series(vals.to_numpy(), index=idx, name=series_id).dropna().sort_index()
    s = s[~s.index.duplicated(keep="last")]
    if len(s) < 100:
        raise ValueError(f"{series_id} history too short: {len(s)}")
    return s


def build_cpi_rows(s: pd.Series) -> list[dict]:
    s = s.copy()
    yoy = (s / s.shift(12) - 1.0) * 100.0
    rows = []
    for dt, val in yoy.dropna().items():
        source = pd.Period(pd.Timestamp(dt), freq="M")
        rows.append(
            {
                "source_month": str(source),
                "effective_month": str(source + 1),
                "cpi_yoy": float(val),
            }
        )
    vals = [x["cpi_yoy"] for x in rows]
    for i, row in enumerate(rows):
        row["inflation_score"] = expanding_pct(vals, i)
    return rows


def build_ulc_rows(s: pd.Series) -> list[dict]:
    rows = []
    for dt, val in s.dropna().items():
        source = pd.Period(pd.Timestamp(dt), freq="M")
        rows.append(
            {
                "source_month": str(source),
                "effective_month": str(source + 5),
                "ulc_yoy": float(val),
            }
        )
    vals = [x["ulc_yoy"] for x in rows]
    for i, row in enumerate(rows):
        row["ulc_score"] = expanding_pct(vals, i)
    return rows


def build_margin_rows(s: pd.Series) -> list[dict]:
    yoy = (s / s.shift(4) - 1.0) * 100.0
    rows = []
    for dt, val in yoy.dropna().items():
        source = pd.Period(pd.Timestamp(dt), freq="M")
        raw = -float(val)
        rows.append(
            {
                "source_month": str(source),
                "effective_month": str(source + 5),
                "unit_profit_yoy": float(val),
                "margin_compression_raw": raw,
            }
        )
    vals = [x["margin_compression_raw"] for x in rows]
    for i, row in enumerate(rows):
        row["margin_compression_score"] = expanding_pct(vals, i)
    return rows


def asof_row(rows: list[dict], month: pd.Period) -> dict | None:
    best = None
    for row in rows:
        eff = period(row["effective_month"])
        if eff <= month:
            best = row
        else:
            break
    return best


def build_monthly_states(
    cpi_rows: list[dict],
    ulc_rows: list[dict],
    margin_rows: list[dict],
) -> list[dict]:
    first = max(
        period(cpi_rows[0]["effective_month"]),
        period(ulc_rows[0]["effective_month"]),
        period(margin_rows[0]["effective_month"]),
    )
    last = min(
        period(cpi_rows[-1]["effective_month"]),
        period(ulc_rows[-1]["effective_month"]),
        period(margin_rows[-1]["effective_month"]),
    )

    out = []
    for i, m in enumerate(pd.period_range(first, last, freq="M")):
        c = asof_row(cpi_rows, m)
        u = asof_row(ulc_rows, m)
        g = asof_row(margin_rows, m)
        if c is None or u is None or g is None:
            continue
        route = (
            c["inflation_score"]
            * u["ulc_score"]
            * g["margin_compression_score"]
        ) ** (1.0 / 3.0)
        out.append(
            {
                "effective_month": str(m),
                "history_months": i + 1,
                "route_im_v1": float(route),
                "inflation_score": float(c["inflation_score"]),
                "ulc_score": float(u["ulc_score"]),
                "margin_compression_score": float(
                    g["margin_compression_score"]
                ),
                "raw": {
                    "cpi_yoy": float(c["cpi_yoy"]),
                    "ulc_yoy": float(u["ulc_yoy"]),
                    "unit_profit_yoy": float(g["unit_profit_yoy"]),
                    "margin_compression_raw": float(
                        g["margin_compression_raw"]
                    ),
                },
                "source_months": {
                    "cpi": c["source_month"],
                    "ulc": u["source_month"],
                    "unit_profit": g["source_month"],
                },
            }
        )
    return out


def fetch_sp500(start="1950-01-01", end="2026-10-19") -> pd.Series:
    p1 = int(pd.Timestamp(start, tz="UTC").timestamp())
    p2 = int((pd.Timestamp(end, tz="UTC") + pd.Timedelta(days=1)).timestamp())
    symbol = urllib.parse.quote("^GSPC", safe="")
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
                raise ValueError(f"^GSPC history too short: {len(s)}")
            return s
        except Exception as exc:
            last = exc
    raise RuntimeError(f"^GSPC fetch failed: {last!r}")


def month_gate(price: pd.Series, month: str) -> dict | None:
    p = period(month)
    start = p.start_time.normalize()
    end = p.end_time.normalize()
    x = price.loc[(price.index >= start) & (price.index <= end)]
    if x.empty:
        return None
    asof = pd.Timestamp(x.index[-1])
    close = float(x.iloc[-1])
    window = price.loc[
        (price.index >= asof - pd.DateOffset(months=24))
        & (price.index <= asof)
    ]
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


def in_window(month: str, window: tuple[str, str]) -> bool:
    m = period(month)
    return period(window[0]) <= m <= period(window[1])


def in_any(month: str, windows: list[tuple[str, str]]) -> bool:
    return any(in_window(month, w) for w in windows)


def collapse_episodes(rows: list[dict]) -> list[list[dict]]:
    armed = [x for x in rows if x["armed"]]
    episodes: list[list[dict]] = []
    for row in armed:
        if not episodes:
            episodes.append([row])
            continue
        prev = period(episodes[-1][-1]["effective_month"])
        cur = period(row["effective_month"])
        if cur.ordinal == prev.ordinal + 1:
            episodes[-1].append(row)
        else:
            episodes.append([row])
    return episodes


def classify_outcome(price: pd.Series, anchor_date: str, signal_close: float) -> dict:
    anchor = pd.Timestamp(anchor_date)
    future = price.loc[price.index > anchor].iloc[:OUTCOME_SESSIONS]
    if len(future) < OUTCOME_SESSIONS:
        return {
            "complete": False,
            "future_sessions": int(len(future)),
        }
    rel = future / signal_close - 1.0
    forward = float(rel.iloc[-1] * 100.0)
    worst = float(rel.min() * 100.0)
    path = pd.Series(
        [signal_close] + [float(x) for x in future.tolist()],
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


def window_hits(rows: list[dict], windows: list[tuple[str, str]]) -> dict:
    out = {}
    for a, b in windows:
        key = f"{a}_to_{b}"
        out[key] = [
            {
                "month": x["effective_month"],
                "route_im_v1": x["route_im_v1"],
            }
            for x in rows
            if x["armed"] and in_window(x["effective_month"], (a, b))
        ]
    return out


def evaluate() -> dict:
    cpi = fetch_fred_series(CPI_ID)
    ulc = fetch_fred_series(ULC_ID)
    profit = fetch_fred_series(UNIT_PROFIT_ID)

    states = build_monthly_states(
        build_cpi_rows(cpi),
        build_ulc_rows(ulc),
        build_margin_rows(profit),
    )
    price = fetch_sp500()

    evaluated = []
    for row in states:
        if row["history_months"] < WARMUP_MONTHS:
            continue
        gate = month_gate(price, row["effective_month"])
        if gate is None:
            continue
        x = dict(row)
        x["top_location"] = gate
        x["pressure_pass"] = bool(x["route_im_v1"] >= THRESHOLD)
        x["armed"] = bool(x["pressure_pass"] and gate["passes"])
        evaluated.append(x)

    positive = window_hits(evaluated, POSITIVE_WINDOWS)
    negative = window_hits(evaluated, NEGATIVE_WINDOWS)
    training = window_hits(evaluated, TRAINING_WINDOWS)

    episodes = []
    for ep in collapse_episodes(evaluated):
        first = ep[0]
        training_episode = any(
            in_any(x["effective_month"], TRAINING_WINDOWS) for x in ep
        )
        outcome = classify_outcome(
            price,
            first["top_location"]["asof"],
            first["top_location"]["close"],
        )
        episodes.append(
            {
                "start": first["effective_month"],
                "end": ep[-1]["effective_month"],
                "armed_months": len(ep),
                "training_overlap": bool(training_episode),
                "route_at_start": first["route_im_v1"],
                "max_route": max(x["route_im_v1"] for x in ep),
                "components_at_start": {
                    "inflation_score": first["inflation_score"],
                    "ulc_score": first["ulc_score"],
                    "margin_compression_score": first[
                        "margin_compression_score"
                    ],
                },
                "raw_at_start": first["raw"],
                "source_months_at_start": first["source_months"],
                "anchor": first["top_location"],
                "outcome_252": outcome,
            }
        )

    nontraining_complete = [
        x for x in episodes
        if not x["training_overlap"] and x["outcome_252"]["complete"]
    ]
    major = sum(
        x["outcome_252"]["classification"] == "MAJOR_TOP"
        for x in nontraining_complete
    )
    clear_false = sum(
        x["outcome_252"]["classification"] == "CLEAR_FALSE"
        for x in nontraining_complete
    )
    n = len(nontraining_complete)
    major_share = major / n if n else 0.0
    clear_false_share = clear_false / n if n else 0.0

    positive_ok = all(bool(v) for v in positive.values())
    negative_ok = all(not v for v in negative.values())
    pass_screen = (
        positive_ok
        and negative_ok
        and n >= 2
        and major_share >= 0.50
        and clear_false_share <= 0.25
    )

    top_rows = sorted(
        evaluated, key=lambda x: x["route_im_v1"], reverse=True
    )[:20]

    return {
        "schema_version": "market-top-inflation-margin-v1-screen-1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "research_only": True,
        "production_effect": "none",
        "preregistration": (
            "market-top-inflation-margin-v1-preregistration-1"
        ),
        "sample": {
            "first_effective_month": (
                evaluated[0]["effective_month"] if evaluated else None
            ),
            "last_effective_month": (
                evaluated[-1]["effective_month"] if evaluated else None
            ),
            "months": len(evaluated),
            "warmup_months": WARMUP_MONTHS,
        },
        "formula": {
            "route_im_v1": (
                "cbrt(inflation_score*ulc_score*margin_compression_score)"
            ),
            "threshold": THRESHOLD,
        },
        "training_window_hits": training,
        "validation_positive_window_hits": positive,
        "validation_negative_window_hits": negative,
        "episodes": episodes,
        "decision_metrics": {
            "positive_windows_all_hit": positive_ok,
            "negative_windows_all_clean": negative_ok,
            "complete_nontraining_episodes": n,
            "major_top_count": major,
            "clear_false_count": clear_false,
            "major_top_share": major_share,
            "clear_false_share": clear_false_share,
        },
        "decision": (
            "ACCEPT_SCREENING_CANDIDATE"
            if pass_screen
            else "REJECT"
        ),
        "top_route_months": [
            {
                "month": x["effective_month"],
                "route_im_v1": x["route_im_v1"],
                "armed": x["armed"],
                "top_location_pass": x["top_location"]["passes"],
                "inflation_score": x["inflation_score"],
                "ulc_score": x["ulc_score"],
                "margin_compression_score": x[
                    "margin_compression_score"
                ],
            }
            for x in top_rows
        ],
        "source_status": {
            "historical_vintage": "CURRENT_OFFICIAL_HISTORY_NOT_EXACT_VINTAGE",
            "cpi": CPI_ID,
            "unit_labor_cost": ULC_ID,
            "unit_profit": UNIT_PROFIT_ID,
            "price": "Yahoo Finance ^GSPC unadjusted close",
        },
        "post_screen_tuning_allowed": False,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output")
    args = ap.parse_args()

    result = evaluate()
    print(json.dumps(result, indent=2))
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2)
            f.write("\n")


if __name__ == "__main__":
    main()
