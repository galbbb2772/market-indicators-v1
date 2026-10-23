"""V2.1.8 frozen-policy/top historical eligibility audit, NOT a full-score backtest.

This deliberately uses the frozen 1M/6M US 2Y policy and S&P 500
60M top-location gates, but does NOT fill the unavailable 252-session
point-in-time all-US new-high/new-low breadth with a proxy or with zero.

Outputs *mathematically impossible* vs *conditionally possible* days.
It never asserts that conditionally possible days triggered the route.
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

from master_top_v218 import (
    TRIGGER_THRESHOLD, HL_GATE, TOP_ELIGIBLE, policy_score, top_proximity,
    route_score,
)

VERSION = "V218_HISTORICAL_PARTIAL_GATES_V1"
FRED_DGS2 = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=DGS2"
EVENTS = {
    "2000_bubble": ("1999-01-01", "2001-12-31"),
    "2005_2006_control": ("2005-01-01", "2006-12-31"),
    "2007_2009_crisis": ("2007-01-01", "2009-12-31"),
    "2017_control": ("2017-01-01", "2017-12-31"),
    "2018_drawdown": ("2018-01-01", "2019-03-31"),
    "2020_covid": ("2019-10-01", "2020-12-31"),
    "2021_2022_bear": ("2021-01-01", "2022-12-31"),
    "2023_control": ("2023-01-01", "2023-12-31"),
    "2025_tariff": ("2025-01-01", "2025-12-31"),
    "2026_prefreeze": ("2026-01-01", "2026-10-16"),
    "2026_postfreeze": ("2026-10-17", "2026-12-31"),
}
SCHEMA = "market-top-v218-two-gate-historical-eligibility-v1"


def sha256_series(series: pd.Series) -> str:
    records = [(x.strftime("%Y-%m-%d"), format(float(v), ".10g"))
               for x, v in series.items() if pd.notna(v)]
    return hashlib.sha256(json.dumps(records, separators=(",", ":")).encode()).hexdigest()


def fetch_gspc() -> pd.Series:
    start = datetime(1990, 1, 1, tzinfo=timezone.utc)
    end = datetime.now(timezone.utc) + timedelta(days=2)
    req = (f"/v8/finance/chart/{quote('^GSPC',safe='')}?"
           f"period1={int(start.timestamp())}&period2={int(end.timestamp())}"
           f"&interval=1d&events=history")
    for domain in ("query1.finance.yahoo.com", "query2.finance.yahoo.com"):
        try:
            r = requests.get("https://" + domain + req, timeout=60,
                             headers={"User-Agent": "Mozilla/5.0"})
            r.raise_for_status()
            obj = r.json()["chart"]["result"][0]
            timestamps = obj.get("timestamp") or []
            prices = (obj.get("indicators", {}).get("quote") or [{}])[0].get("close") or []
            if len(timestamps) != len(prices):
                raise ValueError("Yahoo S&P close series and timestamp length mismatch")
            idx = pd.to_datetime(timestamps, unit="s", utc=True).tz_convert(None).normalize()
            s = pd.Series(pd.to_numeric(prices, errors="coerce"), index=idx)
            s = s.dropna().sort_index()
            validate_price(s, "Yahoo ^GSPC")
            return s
        except (requests.RequestException, TypeError, ValueError, KeyError, IndexError):
            continue
    raise RuntimeError("No valid Yahoo ^GSPC history available; no proxy accepted")


def fetch_dgs2() -> pd.Series:
    response = requests.get(FRED_DGS2, timeout=60, headers={"User-Agent": "Mozilla/5.0"})
    response.raise_for_status()
    table = pd.read_csv(io.StringIO(response.text))
    date_col = "DATE" if "DATE" in table.columns else "observation_date"
    if "DGS2" not in table.columns or date_col not in table.columns:
        raise RuntimeError("FRED public graph CSV lacks DGS2/DATE")
    s = pd.Series(pd.to_numeric(table["DGS2"], errors="coerce").to_numpy(),
                  index=pd.to_datetime(table[date_col], errors="coerce")).dropna().sort_index()
    validate_rates(s)
    return s


def validate_price(series: pd.Series, name: str) -> None:
    if series.empty or series.index.has_duplicates or (series <= 0).any() or not series.index.is_monotonic_increasing:
        raise ValueError(f"{name}: nonpositive/duplicated/out-of-order market prices")
    if series.index[0] > pd.Timestamp("1995-01-01") or series.index[-1] < pd.Timestamp("2026-09-01"):
        raise ValueError(f"{name}: insufficient historical 60-month warm-up / recent coverage")
    if len(series) < 7000:
        raise ValueError(f"{name}: insufficient daily observations")


def validate_rates(series: pd.Series) -> None:
    if series.empty or series.index.has_duplicates or not series.index.is_monotonic_increasing:
        raise ValueError("FRED DGS2 date sequence invalid")
    if series.index[0] > pd.Timestamp("1999-01-01") or series.index[-1] < pd.Timestamp("2026-09-01"):
        raise ValueError("FRED DGS2 cannot support requested historical periods")
    if len(series) < 5000 or series.isna().any():
        raise ValueError("FRED DGS2 data malformed")


def asof_rate(series: pd.Series, target: pd.Timestamp, max_age_days: int = 7) -> tuple[float, str]:
    i = series.index.searchsorted(target, side="right") - 1
    if i < 0:
        raise ValueError("Missing historical 2Y rate prior to reference date")
    observation_date = series.index[i]
    if (target - observation_date).days > max_age_days:
        raise ValueError("Stale historical 2Y reference (>7 calendar days)")
    return float(series.iloc[i]), observation_date.date().isoformat()


def one_day(price_date: pd.Timestamp, p: float, high60: float, rates: pd.Series) -> dict:
    top_ratio = float(p/high60)
    r1 = r6 = policy = None
    output = {
        "date": price_date.date().isoformat(), "gspc_close": round(p, 6),
        "gspc_60m_high": round(high60, 6), "top_ratio": round(top_ratio, 8),
        "top_gate_pass": bool(top_ratio >= TOP_ELIGIBLE),
        "dgs2": None, "dgs2_1m": None, "dgs2_6m": None,
        "dgs2_obs": None, "dgs2_1m_obs": None, "dgs2_6m_obs": None,
        "delta_1m_bp": None, "delta_6m_bp": None,
        "policy": None, "route_upper_bound_if_hl100": None,
        "hl_min_for_threshold_if_gate_pass": None, "status": None,
    }
    # This negative result is rigorous even when policy data are unavailable.
    if top_ratio < TOP_ELIGIBLE:
        output["status"] = "TOP_GATE_IMPOSSIBLE"
    try:
        y, o = asof_rate(rates, price_date)
        y1, o1 = asof_rate(rates, price_date - pd.DateOffset(months=1))
        y6, o6 = asof_rate(rates, price_date - pd.DateOffset(months=6))
        d1, d6 = 100.0*(y-y1), 100.0*(y-y6)
        policy = policy_score(d6, d1)
        upper = route_score(policy, 100.0, top_ratio)
        output.update({
            "dgs2": round(y, 6), "dgs2_1m": round(y1, 6), "dgs2_6m": round(y6, 6),
            "dgs2_obs": o, "dgs2_1m_obs": o1, "dgs2_6m_obs": o6,
            "delta_1m_bp": round(d1, 6), "delta_6m_bp": round(d6, 6),
            "policy": round(policy, 8),
            "route_upper_bound_if_hl100": round(upper, 8),
        })
    except ValueError:
        if output["status"] is None:
            output["status"] = "RATE_DATA_UNAVAILABLE"
        return output
    if output["status"] == "TOP_GATE_IMPOSSIBLE":
        return output
    if upper + 1e-10 < TRIGGER_THRESHOLD:
        output["status"] = "POLICY_UPPER_BOUND_IMPOSSIBLE"
        return output
    required = max(float(HL_GATE), 100.0*(TRIGGER_THRESHOLD/upper)**2)
    output["hl_min_for_threshold_if_gate_pass"] = round(required, 6)
    output["status"] = "CONDITIONALLY_POSSIBLE_IF_MISSING_HL_SUFFICIENT"
    return output


def audit(price: pd.Series, rates: pd.Series) -> tuple[pd.DataFrame, dict]:
    validate_price(price, "^GSPC")
    validate_rates(rates)
    high = price.rolling(1260, min_periods=1260).max()
    rows = [one_day(d,float(p),float(high.loc[d]),rates)
            for d,p in price.items()
            if d>=pd.Timestamp("1999-01-01") and d<=pd.Timestamp("2026-10-22") and pd.notna(high.loc[d])]
    if not rows:
        raise RuntimeError("No eligible 60M S&P price sessions")
    frame = pd.DataFrame(rows)
    if frame["date"].iloc[0] > "2000-12-31" or frame["date"].iloc[-1] < "2026-09-01":
        raise RuntimeError("Insufficient coverage after S&P 60M warm-up")
    def summary_of(section: pd.DataFrame) -> dict:
        count = section["status"].value_counts()
        return {
            "sessions": len(section),
            "top_gate_impossible": int(count.get("TOP_GATE_IMPOSSIBLE",0)),
            "policy_upper_bound_impossible": int(count.get("POLICY_UPPER_BOUND_IMPOSSIBLE",0)),
            "rate_data_unavailable": int(count.get("RATE_DATA_UNAVAILABLE",0)),
            "conditionally_possible_with_unobserved_breadth": int(
                count.get("CONDITIONALLY_POSSIBLE_IF_MISSING_HL_SUFFICIENT",0)
            ),
            "max_frozen_policy": (round(float(section["policy"].max()),4)
                                  if section["policy"].notna().any() else None),
            "max_upper_bound": (round(float(section["route_upper_bound_if_hl100"].max()),4)
                                if section["route_upper_bound_if_hl100"].notna().any() else None),
        }
    buckets = {}
    for year, sub in frame.groupby(frame["date"].str[:4]):
        buckets[year] = summary_of(sub)
    windows = {}
    for name,(start,end) in EVENTS.items():
        f = frame.loc[(frame["date"]>=start)&(frame["date"]<=end)]
        s = summary_of(f)
        candidates = f.loc[f["status"]=="CONDITIONALLY_POSSIBLE_IF_MISSING_HL_SUFFICIENT"]
        s["first_conditional_date"] = str(candidates["date"].iloc[0]) if not candidates.empty else None
        s["last_conditional_date"] = str(candidates["date"].iloc[-1]) if not candidates.empty else None
        windows[name] = s
    overall = summary_of(frame)
    report = {
        "schema": SCHEMA, "version": VERSION,
        "computed_at_utc": datetime.now(timezone.utc).isoformat(),
        "frozen_threshold": TRIGGER_THRESHOLD, "frozen_hl_gate": HL_GATE,
        "frozen_top_gate": TOP_ELIGIBLE, "freeze_date": "2026-10-17",
        "breadth": "NOT_AVAILABLE_HL_IS_NOT_COMPUTED",
        "status": "UPPER_BOUND_AND_GATE_AUDIT_ONLY_NOT_FULL_V218_BACKTEST",
        "source_gspc": "Yahoo Finance ^GSPC daily close",
        "source_dgs2": "FRED public DGS2 CSV latest available vintage",
        "source_price_sha256": sha256_series(price),
        "source_rates_sha256": sha256_series(rates),
        "source_price_first": price.index[0].date().isoformat(),
        "source_price_last": price.index[-1].date().isoformat(),
        "source_rates_first": rates.index[0].date().isoformat(),
        "source_rates_last": rates.index[-1].date().isoformat(),
        "score_days_first": frame["date"].iloc[0],
        "score_days_last": frame["date"].iloc[-1],
        "total": overall, "by_year": buckets, "control_windows": windows,
        "rules": [
            "If TopRatio < 0.95, a V2.1.8 alarm is mathematically impossible.",
            "If frozen route score assuming HL=100 is <55, alarm is impossible.",
            "Otherwise missing actual 20D new-high/new-low HL means alarm is UNCONFIRMED.",
            "Candidate days do not imply actual triggers, episodes, hit-rate, or lead time.",
            "DGS2 historical observations are latest-vintage dates; original publication vintages not verified.",
            "Both Yahoo index closes and FRED rates are historical observations; publication-time/execution lag must be audited before PIT production.",
        ],
    }
    return frame, report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--outdir", default="research/out/v218_historical_gates")
    args = parser.parse_args()
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    price = fetch_gspc()
    rates = fetch_dgs2()
    frame, report = audit(price,rates)
    frame.to_csv(outdir/"all_days.csv",index=False)
    (outdir/"summary.json").write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print(json.dumps({
        "status": report["status"],"first":report["score_days_first"],
        "last":report["score_days_last"],"total":report["total"],
        "controls": {k:report["control_windows"][k] for k in
                     ("2005_2006_control","2017_control","2021_2022_bear","2023_control")},
        "output_dir":str(outdir)},ensure_ascii=False))


if __name__ == "__main__":
    main()
