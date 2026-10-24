"""Validate MarketParquet's ANONYMOUS recent stock_daily sample against V2.1.8.

Read-only provider-contract audit. The original frozen scoring formula, 252
prior observations and 20-session persistence are NOT computed here.
Anonymous access is documented for roughly the latest seven trading days.
Only schema, universe-size fingerprints and data-quality receipts are stored;
the data vendor's licensed security-level price bars are not republished.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
from datetime import datetime, date, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import requests

SOURCE = "https://marketparquet.com/api/data/download/stock_daily/"
MIN_STOCKS = 1000
REQUIRED = ("symbol", "close")
ANCHOR_FROZEN = "CLOSE_252_INCLUSIVE_FROZEN"


def normalize_date(table: pd.DataFrame, requested: str) -> tuple[pd.Series, str]:
    """Canonical scorer requires a date column; vendor may instead supply timestamp."""
    if "date" in table.columns:
        raw = pd.to_datetime(table["date"], errors="coerce", utc=False)
        col = "date"
        # Date objects / naive date strings are already exchange-date labels.
        if isinstance(raw.dtype, pd.DatetimeTZDtype):
            day = raw.dt.tz_convert("America/New_York").dt.date
        else:
            day = raw.dt.date
    elif "timestamp" in table.columns:
        raw = pd.to_datetime(table["timestamp"], errors="coerce", utc=False)
        col = "timestamp"
        if isinstance(raw.dtype, pd.DatetimeTZDtype):
            day = raw.dt.tz_convert("America/New_York").dt.date
        else:
            # Per the vendor's public schema, naive timestamps represent
            # US/Eastern bar-open time, not a UTC epoch.
            day = raw.dt.date
    else:
        raise ValueError("Vendor file lacks date and timestamp; frozen input not normalizable")
    if len(day) != len(table) or day.isna().any():
        raise ValueError("Vendor trade-date field contains missing/unparseable timestamps")
    if (day.astype(str) != requested).any():
        raise ValueError("Vendor row trade dates disagree with requested market date")
    return day, col


def audit_table(table: pd.DataFrame, requested: str, blob_sha256: str, blob_bytes: int) -> tuple[dict, set[str]]:
    if not set(REQUIRED).issubset(table.columns):
        raise ValueError("Vendor schema missing symbol/close")
    if len(table) < MIN_STOCKS:
        raise ValueError(f"Vendor stock_daily sample insufficient: {len(table)}")
    _, date_field = normalize_date(table, requested)

    symbols = table["symbol"]
    if symbols.isna().any() or not symbols.map(lambda x: isinstance(x, str) and bool(x.strip())).all():
        raise ValueError("Vendor sample contains blank/nonstring symbol")
    if symbols.duplicated().any():
        raise ValueError("Duplicate symbols in same-day vendor stock sample")
    if "asset_type" in table.columns:
        types = set(table["asset_type"].dropna().astype(str).unique())
        if len(types) != 1 or next(iter(types)).lower() != "stock":
            raise ValueError(f"Unexpected vendor stock_daily asset type(s): {sorted(types)}")
    close = pd.to_numeric(table["close"], errors="coerce")
    if close.isna().any() or (close <= 0).any():
        raise ValueError("Missing/zero/negative frozen input stock closing prices")
    price_check = {}
    if {"high", "low"}.issubset(table.columns):
        hi = pd.to_numeric(table["high"], errors="coerce")
        lo = pd.to_numeric(table["low"], errors="coerce")
        if (hi.isna() | lo.isna()).any() or not ((lo > 0) & (lo <= close) & (close <= hi)).all():
            raise ValueError("MarketParquet sample has inconsistent OHLC bounds")
        price_check = {"ohlc_bounds_pass": True}

    names = sorted(set(map(str, symbols.tolist())))
    # Hash of sorted symbol names is a universe fingerprint without exposing
    # or redistributing vendor-supplied security-level market prices.
    digest = hashlib.sha256("\n".join(names).encode()).hexdigest()
    # Public symbol-list cross-check; this is NOT a complete dated ETF master.
    # Full PIT security-type certification must use comprehensive dated ref data.
    known_etfs = ("SPY", "QQQ", "TLT", "GLD", "IWM", "DIA", "IVV", "VOO")
    etf_overlap = sorted(set(names).intersection(known_etfs))
    out = {
        "date": requested,
        "rows": len(table),
        "unique_symbols": len(names),
        "columns": list(table.columns),
        "date_field_found": date_field,
        "canonical_frozen_date_column_present": "date" in table.columns,
        "needs_date_normalization": "date" not in table.columns,
        "stock_only_vendor_partition_validated": True if "asset_type" in table.columns else None,
        "verified_positive_closes": True,
        "known_etf_probe_symbols": list(known_etfs),
        "known_etf_symbols_present": etf_overlap,
        "known_etf_count_present": len(etf_overlap),
        "independent_common_stock_type_coverage_complete": False,
        "eligible_for_frozen_pit_stock_only_breadth": False,
        "stock_symbol_universe_sha256": digest,
        "downloaded_parquet_sha256": blob_sha256,
        "downloaded_bytes": blob_bytes,
        "status": "VALIDATED_SINGLE_DAY_STOCK_DAILY_SAMPLE",
        **price_check,
    }
    return out, set(names)


def download_one(session: requests.Session, requested: str) -> tuple[dict, set[str]]:
    try:
        date.fromisoformat(requested)
    except ValueError:
        raise ValueError("Invalid YYYY-MM-DD date") from None
    url = SOURCE + requested + ".parquet"
    try:
        r = session.get(url, timeout=60, headers={"User-Agent": "MarketTopFrozenSourceAudit/1.0"})
        if r.status_code in (401, 403):
            raise RuntimeError(f"MarketParquet anonymous sample not entitled ({r.status_code}) for {requested}")
        if r.status_code != 200:
            raise RuntimeError(f"MarketParquet sample returned HTTP {r.status_code} on {requested}")
        payload = r.content
    except requests.RequestException:
        raise RuntimeError(f"MarketParquet anonymous sample transport failed on {requested}") from None
    if len(payload) < 1024 or payload[:4] != b"PAR1" or payload[-4:] != b"PAR1":
        raise RuntimeError(f"MarketParquet {requested} did not return a valid Parquet envelope")
    try:
        df = pd.read_parquet(io.BytesIO(payload))
    except Exception:
        raise RuntimeError(f"MarketParquet {requested} Parquet contents cannot be parsed") from None
    return audit_table(df, requested, hashlib.sha256(payload).hexdigest(), len(payload))


def sample_audit(results: list[tuple[dict, set[str]]]) -> dict:
    if not results:
        raise ValueError("No vendor daily samples to audit")
    bydate = sorted(results, key=lambda p: p[0]["date"])
    dates = [p[0]["date"] for p in bydate]
    if len(set(dates)) != len(dates):
        raise ValueError("Duplicate sample dates")
    comparisons = []
    for (a, before), (b, after) in zip(bydate, bydate[1:]):
        comparisons.append({
            "date_from": a["date"],
            "date_to": b["date"],
            "overlap_symbols": len(before & after),
            "new_or_returned_symbols": len(after - before),
            "exited_or_missing_symbols": len(before - after),
            "jaccard": round(len(before & after) / len(before | after), 6),
        })
    return {
        "schema": "v218-marketparquet-anonymous-source-contract-v1",
        "audited_at_utc": datetime.now(timezone.utc).isoformat(),
        "provider": "MarketParquet anonymous stock_daily file download",
        "original_frozen_comparator_definition": ANCHOR_FROZEN,
        "audit_days": [x[0] for x in bydate],
        "cross_day_universe": comparisons,
        "ready_for_frozen_252_prior_sessions": False,
        "ready_for_frozen_20day_persistence": False,
        "ready_to_score_v218": False,
        "this_is_complete_historical_backtest": False,
        "notes": [
            "This is schema/source and real current-stock coverage validation, not a scored model run.",
            "Three adjacent days do not establish per-symbol 252 prior observations.",
            "Date-normalization requires an explicit real sample result; vendor timestamp != canonical date column.",
            "Stock-only partition avoids mixing ETF-inclusive grouped daily universe into frozen stock breadth.",
            "Historical and delisted ticker coverage not proven by an anonymous seven-day sample.",
            "No licensed raw vendor prices are retained in this public-repository audit artifact.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dates", nargs="+", required=True, help="Last-week available NYSE market dates")
    parser.add_argument("--output", default="research/out/v218_marketparquet_anonymous_source.json")
    args = parser.parse_args()
    session = requests.Session()
    rows = [download_one(session, d) for d in args.dates]
    report = sample_audit(rows)
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": "SCHEMA_VERIFIED_NO_FULL_HISTORICAL_SCORE",
        "per_day": [
            {"date": d["date"], "rows": d["rows"], "date_field_found": d["date_field_found"],
             "needs_date_normalization": d["needs_date_normalization"]}
            for d, _ in rows
        ],
        "cross_day": report["cross_day_universe"],
        "output": str(out)
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
