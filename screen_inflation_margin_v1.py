from __future__ import annotations

import argparse
import io
import json
import math
import time
import urllib.parse
from datetime import datetime, timezone

import pandas as pd
import requests

from audit_market_top_ng1_a_independent import get

CPI_ID = "CPIAUCSL"
ULC_ID = "PRS85006111"
UNIT_PROFIT_ID = "PRS88003191"

CPI_SNAPSHOT_COMMIT = "45fddf72d8c03167e68d3de6b76482d27ddc8874"
CPI_SNAPSHOT_URL = (
    "https://raw.githubusercontent.com/danielmiessler/Substrate/"
    + CPI_SNAPSHOT_COMMIT
    + "/Data/US-Inflation/CPI-US-Monthly-1947-2025.csv"
)
BLS_API_URL = "https://api.bls.gov/publicAPI/v2/timeseries/data/"
BLS_FALLBACK_COMMIT = "d2f959bb311fb8e7a58289604a0e01e3b81f5708"
BLS_FALLBACK_URL = (
    "https://raw.githubusercontent.com/rmmomin/ai-adoption-labor-trends/"
    + BLS_FALLBACK_COMMIT
    + "/data/qilp_update/bls_responses.json"
)

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


def fetch_cpi_snapshot() -> pd.Series:
    r = get(CPI_SNAPSHOT_URL)
    df = pd.read_csv(io.StringIO(r.text), dtype=str)
    date_col = next(
        (x for x in ("observation_date", "DATE", "date") if x in df.columns),
        None,
    )
    if df.empty or date_col is None or CPI_ID not in df.columns:
        raise ValueError("unexpected pinned CPI snapshot")
    idx = pd.to_datetime(df[date_col], errors="coerce")
    vals = pd.to_numeric(
        df[CPI_ID].astype(str).str.strip().replace({".": None, "": None}),
        errors="coerce",
    )
    out = pd.Series(
        vals.to_numpy(), index=idx, name=CPI_ID
    ).dropna().sort_index()
    out = out[~out.index.duplicated(keep="last")]
    if len(out) < 500 or out.index.min() > pd.Timestamp("1948-01-01"):
        raise ValueError("pinned CPI snapshot coverage is insufficient")
    out.attrs["source"] = (
        "danielmiessler/Substrate@" + CPI_SNAPSHOT_COMMIT
    )
    return out


def _bls_quarter_date(year: str, period_code: str) -> pd.Timestamp | None:
    months = {"Q01": 1, "Q02": 4, "Q03": 7, "Q04": 10}
    month = months.get(period_code)
    if month is None:
        return None
    return pd.Timestamp(year=int(year), month=month, day=1)


def _series_from_bls_blocks(blocks: list[dict], series_id: str) -> pd.Series:
    pairs: dict[pd.Timestamp, float] = {}
    for block in blocks:
        if block.get("seriesID") != series_id:
            continue
        for row in block.get("data") or []:
            dt = _bls_quarter_date(str(row.get("year")), str(row.get("period")))
            if dt is None:
                continue
            try:
                pairs[dt] = float(row.get("value"))
            except (TypeError, ValueError):
                continue
    if not pairs:
        raise ValueError(f"no BLS rows parsed for {series_id}")
    return pd.Series(pairs, name=series_id, dtype=float).sort_index()


def _walk_series_blocks(obj) -> list[dict]:
    out: list[dict] = []
    if isinstance(obj, dict):
        if "seriesID" in obj and "data" in obj:
            out.append(obj)
        for value in obj.values():
            out.extend(_walk_series_blocks(value))
    elif isinstance(obj, list):
        for value in obj:
            out.extend(_walk_series_blocks(value))
    return out


def _fetch_bls_fallback(series_ids: list[str]) -> dict[str, pd.Series]:
    r = get(BLS_FALLBACK_URL)
    obj = r.json()
    blocks = _walk_series_blocks(obj)
    return {
        sid: _series_from_bls_blocks(blocks, sid)
        for sid in series_ids
    }


def fetch_bls_quarterly_yoy(series_ids: list[str]) -> tuple[dict[str, pd.Series], str]:
    session = requests.Session()
    session.headers.update(
        {"User-Agent": "market-top-inflation-margin-v1.1/1.0"}
    )
    collected: dict[str, list[dict]] = {sid: [] for sid in series_ids}
    try:
        for start in (1948, 1968, 1988, 2008):
            end = min(start + 19, 2026)
            payload = {
                "seriesid": series_ids,
                "startyear": str(start),
                "endyear": str(end),
            }
            last = None
            for delay in (0, 2, 5):
                if delay:
                    time.sleep(delay)
                try:
                    resp = session.post(
                        BLS_API_URL, json=payload, timeout=45
                    )
                    resp.raise_for_status()
                    obj = resp.json()
                    if obj.get("status") != "REQUEST_SUCCEEDED":
                        raise RuntimeError(
                            f"BLS status={obj.get('status')} "
                            f"message={obj.get('message')}"
                        )
                    blocks = (obj.get("Results") or {}).get("series") or []
                    for block in blocks:
                        sid = block.get("seriesID")
                        if sid in collected:
                            collected[sid].append(block)
                    last = None
                    break
                except Exception as exc:
                    last = exc
            if last is not None:
                raise RuntimeError(
                    f"BLS API chunk {start}-{end} failed: {last!r}"
                )

        parsed = {
            sid: _series_from_bls_blocks(collected[sid], sid)
            for sid in series_ids
        }
        for sid, series in parsed.items():
            if len(series) < 100:
                raise ValueError(
                    f"BLS API {sid} history too short: {len(series)}"
                )
        return parsed, "BLS public API"
    except Exception as api_exc:
        parsed = _fetch_bls_fallback(series_ids)
        for sid, series in parsed.items():
            if len(series) < 100:
                raise ValueError(
                    f"BLS fallback {sid} history too short: {len(series)}"
                ) from api_exc
        return (
            parsed,
            "pinned rmmomin/ai-adoption-labor-trends BLS snapshot "
            + BLS_FALLBACK_COMMIT,
        )

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
    rows = []
    for dt, val in s.dropna().items():
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
    cpi = fetch_cpi_snapshot()
    bls, bls_provider = fetch_bls_quarterly_yoy(
        [ULC_ID, UNIT_PROFIT_ID]
    )
    ulc = bls[ULC_ID]
    profit = bls[UNIT_PROFIT_ID]

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
        "schema_version": "market-top-inflation-margin-v1.1-screen-1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "research_only": True,
        "production_effect": "none",
        "preregistration": (
            "market-top-inflation-margin-v1.1-preregistration-1"
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
            "historical_vintage": "CURRENT_HISTORY_NOT_EXACT_VINTAGE",
            "cpi": CPI_ID,
            "cpi_provider": cpi.attrs.get("source"),
            "unit_labor_cost": ULC_ID,
            "unit_profit": UNIT_PROFIT_ID,
            "bls_provider": bls_provider,
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
