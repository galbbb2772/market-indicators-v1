"""Independent price-outcome audit of archived MASTER TOP V2.1.8 anchors.

No score is reconstructed. Never relabel these sparse archived anchors as a
complete historical backtest or as post-freeze prospective predictions.
This evaluator fetches ETF SPY price history from Yahoo Finance (with
Stooq source-specific fallback), evaluates 12-calendar-month forward
close-to-close drawdown, and separately reports 63/126/252-session outcomes.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import math
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import quote

import numpy as np
import pandas as pd
import requests

SCHEMA = "master-top-v218-anchor-price-audit-v1"
FREEZE_DATE = "2026-10-17"
THRESHOLD = 55.0
ARCHIVED_ANCHORS = (
    ("1999-11-29", 76.90, "REPORTED_HISTORICAL_ANCHOR", -13.43, "2000-03-24"),
    ("2006-06-29", 44.40, "REPORTED_NEGATIVE_CONTROL", None, None),
    ("2018-10-05", 66.06, "REPORTED_HISTORICAL_ANCHOR", -18.52, "2018-09-20"),
    ("2021-12-15", 69.42, "REPORTED_HISTORICAL_ANCHOR", -25.43, "2022-01-03"),
    ("2026-09-10", 60.88, "PRE_FREEZE_SEED", None, None),
    ("2026-10-09", 99.33, "PRE_FREEZE_SEED_SAME_EPISODE", None, None),
)


def query_yahoo(symbol: str = "SPY") -> pd.DataFrame:
    start = int(datetime(1998, 1, 1, tzinfo=timezone.utc).timestamp())
    end = int((datetime.now(timezone.utc) + timedelta(days=2)).timestamp())
    tail = (f"/v8/finance/chart/{quote(symbol, safe='')}?period1={start}"
            f"&period2={end}&interval=1d&events=history&includeAdjustedClose=true")
    errors: list[str] = []
    for hostname in ("query1.finance.yahoo.com", "query2.finance.yahoo.com"):
        try:
            response = requests.get(f"https://{hostname}{tail}", timeout=45,
                                    headers={"User-Agent": "Mozilla/5.0"})
            response.raise_for_status()
            data = response.json()["chart"]["result"][0]
            stamps = data.get("timestamp") or []
            raw = (data.get("indicators", {}).get("quote") or [{}])[0].get("close") or []
            adj = (data.get("indicators", {}).get("adjclose") or [{}])[0].get("adjclose")
            if len(stamps) != len(raw):
                raise ValueError("timestamp-close length mismatch")
            if adj is not None and len(adj) != len(stamps):
                adj = None
            df = pd.DataFrame({
                "date": pd.to_datetime(stamps, unit="s", utc=True).tz_convert(None).normalize(),
                "close": pd.to_numeric(raw, errors="coerce"),
                "adjusted_close": pd.to_numeric(adj, errors="coerce") if adj is not None else np.nan,
            })
            return validate_price_data(df, provider="Yahoo Finance chart", adjusted_available=adj is not None)
        except (requests.RequestException, ValueError, TypeError, KeyError, IndexError) as exc:
            errors.append(f"{hostname}: {type(exc).__name__}")
    raise RuntimeError("Yahoo historical price unavailable; " + "; ".join(errors))


def query_stooq() -> pd.DataFrame:
    endpoint = "https://stooq.com/q/d/l/?s=spy.us&i=d&d1=19980101&d2=" + datetime.now(timezone.utc).strftime("%Y%m%d")
    response = requests.get(endpoint, timeout=45, headers={"User-Agent": "Mozilla/5.0"})
    response.raise_for_status()
    csv = pd.read_csv(io.StringIO(response.text))
    needed = {"Date", "Close"}
    if not needed.issubset(csv.columns):
        raise RuntimeError("Stooq did not return a dated price CSV")
    df = pd.DataFrame({
        "date": pd.to_datetime(csv["Date"], errors="coerce"),
        "close": pd.to_numeric(csv["Close"], errors="coerce"),
        "adjusted_close": np.nan,
    })
    return validate_price_data(df, provider="Stooq SPY.US daily CSV", adjusted_available=False)


def validate_price_data(df: pd.DataFrame, provider: str, adjusted_available: bool) -> pd.DataFrame:
    # Strong source/coverage gates prevent pretending 2024-only data can audit 1999.
    if df.empty or df["date"].isna().any() or df["close"].isna().any() or (df["close"] <= 0).any():
        raise ValueError(f"{provider} returned empty or invalid price series")
    if df["date"].duplicated().any():
        raise ValueError(f"{provider} returned duplicate dates")
    df = df.sort_values("date").reset_index(drop=True).copy()
    if df["date"].iloc[0] > pd.Timestamp("1999-11-29"):
        raise ValueError(f"{provider} historical coverage starts after the 1999 anchor")
    if df["date"].iloc[-1] < pd.Timestamp("2026-09-10"):
        raise ValueError(f"{provider} recent coverage is insufficient for 2026 seed censoring")
    if len(df) < 5000:
        raise ValueError(f"{provider} unexpectedly sparse complete-history series")
    if adjusted_available:
        df.loc[df["adjusted_close"].isna() | (df["adjusted_close"] <= 0), "adjusted_close"] = np.nan
    df.attrs["provider"] = provider
    df.attrs["adjusted_available"] = adjusted_available
    return df


def price_series_digest(df: pd.DataFrame, field: str) -> str:
    obj = [(d.strftime("%Y-%m-%d"), format(float(v), ".8g"))
           for d, v in zip(df["date"], df[field]) if np.isfinite(v)]
    return hashlib.sha256(json.dumps(obj, separators=(",", ":")).encode()).hexdigest()


def forward_mdd(closes: pd.Series, signal: str, horizon: str) -> dict:
    """Window includes signal-date close. No future values enter the frozen score."""
    stamps = pd.Timestamp(signal)
    if stamps not in closes.index:
        raise ValueError(f"Missing exact anchor close on {signal}")
    t0 = closes.index.get_loc(stamps)
    if not isinstance(t0, (int, np.integer)):
        raise ValueError("Nonunique price index")
    if horizon == "12m":
        requested_end = stamps + pd.DateOffset(months=12)
        window = closes.loc[(closes.index >= stamps) & (closes.index <= requested_end)]
        matured = bool(closes.index.max() >= requested_end)
    else:
        periods = int(horizon)
        window = closes.iloc[t0: t0 + periods + 1]
        matured = bool(len(window) == periods + 1)
        requested_end = window.index[-1] if matured else pd.NaT

    if len(window) < 2:
        raise ValueError("Not enough future prices to evaluate drawdown")
    peak = window.cummax()
    dd = 100 * (window / peak - 1)
    low_date = dd.idxmin()
    value = round(float(dd.min()), 4)
    return {
        "requested_horizon": horizon,
        "matured": matured,
        "observed_sessions": len(window)-1,
        "effective_end_date": window.index[-1].date().isoformat(),
        "planned_end_date": str(requested_end.date()) if pd.notna(requested_end) else None,
        "mdd_pct": value if matured else None,
        "censored_mdd_to_date_pct": value if not matured else None,
        "lowest_drawdown_date": low_date.date().isoformat() if matured else None,
    }


def outcome_class(mdd_pct: float | None) -> str:
    if mdd_pct is None:
        return "CENSORED"
    if mdd_pct <= -20:
        return "MAJOR_BEAR"
    if mdd_pct <= -15:
        return "SEVERE_NEAR_MISS"
    if mdd_pct <= -10:
        return "CORRECTION"
    return "FALSE_POSITIVE"


def evaluate(df: pd.DataFrame) -> dict:
    # The archived outcomes are from a prior source/definition. Do not treat
    # discrepancy as an error that authorizes changing the frozen threshold.
    provider = df.attrs.get("provider", "unknown")
    sources = ["close"]
    if df["adjusted_close"].notna().sum() > 5000:
        sources.append("adjusted_close")
    evaluated = []
    for field in sources:
        closes = pd.Series(df[field].to_numpy(), index=pd.DatetimeIndex(df["date"])).dropna()
        for date, reported_route, provenance, archived_mdd, reference_top in ARCHIVED_ANCHORS:
            twelve = forward_mdd(closes, date, "12m")
            e = {
                "anchor_date": date,
                "reported_frozen_route": reported_route,
                "reported_score_provenance": provenance,
                "reported_trigger": bool(reported_route >= THRESHOLD),
                "price_provider": provider,
                "price_field": field,
                "price_series_sha256": price_series_digest(df, field),
                "evaluation_definition": "12-calendar-month close-to-close running-peak MDD",
                "forward_12m": twelve,
                "forward_63_session": forward_mdd(closes, date, "63"),
                "forward_126_session": forward_mdd(closes, date, "126"),
                "forward_252_session": forward_mdd(closes, date, "252"),
                "outcome_class_12m": outcome_class(twelve["mdd_pct"]),
                "previously_reported_mdd_pct": archived_mdd,
                "difference_vs_reported_pp": (
                    round(twelve["mdd_pct"]-archived_mdd, 4)
                    if twelve["mdd_pct"] is not None and archived_mdd is not None else None
                ),
                "reference_peak_date": reference_top,
                "calendar_days_before_reference_top": (
                    (pd.Timestamp(reference_top)-pd.Timestamp(date)).days if reference_top else None
                ),
                "post_freeze_new_signal": False,
                "score_recomputed_here": False,
            }
            evaluated.append(e)

    matured_alert = [x for x in evaluated if x["price_field"] == "close"
                     and x["reported_score_provenance"] == "REPORTED_HISTORICAL_ANCHOR"
                     and x["forward_12m"]["matured"] and x["reported_trigger"]]
    return {
        "schema": SCHEMA,
        "evaluated_utc": datetime.now(timezone.utc).isoformat(),
        "frozen_model": "MASTER-TOP-V2.1.8-FROZEN",
        "freeze_date": FREEZE_DATE,
        "route_threshold_unchanged": THRESHOLD,
        "source": provider,
        "source_first": df["date"].min().date().isoformat(),
        "source_last": df["date"].max().date().isoformat(),
        "raw_daily_price_rows": len(df),
        "price_field_variants": sources,
        "anchor_count_in_frozen_evidence": len(ARCHIVED_ANCHORS),
        "matured_reported_alert_anchors": len(matured_alert),
        "matured_reported_alerts_outcome": [
            {"date": x["anchor_date"], "class": x["outcome_class_12m"],
             "computed_mdd_pct": x["forward_12m"]["mdd_pct"]}
            for x in matured_alert
        ],
        "results": evaluated,
        "evidence_status": "SPARSE_PRESELECTED_ANCHOR_OUTCOME_AUDIT_NOT_FULL_BACKTEST",
        "does_not_establish": [
            "historical recall / sensitivity",
            "full false-positive rate",
            "frozen formula re-evaluation across all historical dates",
            "PIT market breadth completeness",
            "post-freeze prospective efficacy",
        ],
        "notes": [
            "SPY ETF is an outcome benchmark, not the frozen scorer's required ^GSPC input.",
            "Adjustments may revise earlier levels; adjusted close outcomes are not point-in-time signal inputs.",
            "Two 2026 seeds are a shared existing episode and are not independent signals.",
            "An incomplete future 12-month window is censored, NEVER labeled a successful warning.",
            "Outcomes are forward path evaluations and can legitimately use future prices; no future market data were used to compute signals.",
        ],
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", default="research/out/master_top_v218_anchor_outcomes.json")
    ap.add_argument("--provider", choices=["auto","yahoo","stooq"], default="auto")
    args = ap.parse_args()
    errors = []
    funcs = {"yahoo": query_yahoo, "stooq": query_stooq}
    order = ("yahoo", "stooq") if args.provider == "auto" else (args.provider,)
    for name in order:
        try:
            df = funcs[name]()
            break
        except Exception as exc:
            errors.append(f"{name}: {type(exc).__name__}: {exc}")
    else:
        raise RuntimeError("No valid full-span source: " + " | ".join(errors))
    report = evaluate(df)
    path = Path(args.output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, ensure_ascii=False)+"\n", encoding="utf-8")
    print(json.dumps({
        "source": report["source"], "date_range": [report["source_first"],report["source_last"]],
        "price_fields": report["price_field_variants"],
        "anchor_outcomes": report["matured_reported_alerts_outcome"],
        "raw_benchmark": [
            {"date": x["anchor_date"], "reported_score": x["reported_frozen_route"],
             "twelve_month_mdd_pct": x["forward_12m"]["mdd_pct"],
             "twelve_month_class": x["outcome_class_12m"],
             "63_sessions_mdd_pct": x["forward_63_session"]["mdd_pct"],
             "126_sessions_mdd_pct": x["forward_126_session"]["mdd_pct"],
             "252_sessions_mdd_pct": x["forward_252_session"]["mdd_pct"],
             "censored": not x["forward_12m"]["matured"]}
            for x in report["results"] if x["price_field"] == "close"
        ],
        "historical_mdd_differences_pp": [
            {"date":x["anchor_date"],"difference_pp":x["difference_vs_reported_pp"]}
            for x in report["results"] if x["price_field"] == "close"
               and x["difference_vs_reported_pp"] is not None
        ],
        "status": report["evidence_status"],"output":str(path)
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
