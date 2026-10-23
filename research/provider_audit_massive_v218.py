"""Read-only Massive source-universe audit for MASTER TOP V2.1.8.

This NEVER calculates a V2.1.8 score, updates its seed, or blends Massive
with MarketParquet. It investigates whether grouped daily bars can become
a well-classified, independently validated research feed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

import requests

BASE = "https://api.massive.com"
ELIGIBLE_TYPES = ("CS", "ADRC")
PAGE_LIMIT = 25
MIN_GROUPED_ROWS = 1000


def sha256_json(value: object) -> str:
    data = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def request_json(session: requests.Session, url: str, api_key: str, params: dict | None = None) -> dict:
    """Never include a credential-bearing URL or provider response in exceptions."""
    if urlparse(url).scheme != "https" or urlparse(url).hostname != "api.massive.com":
        raise RuntimeError("Untrusted pagination host")
    query = dict(params or {})
    query["apiKey"] = api_key
    try:
        response = session.get(url, params=query, timeout=60)
        if response.status_code != 200:
            raise RuntimeError(f"Massive returned HTTP {response.status_code}")
        payload = response.json()
    except requests.RequestException:
        raise RuntimeError("Massive connection failed (request details suppressed)") from None
    except ValueError:
        raise RuntimeError("Massive returned invalid JSON") from None
    if not isinstance(payload, dict) or payload.get("status") not in ("OK", "DELAYED"):
        raise RuntimeError("Massive returned an unsuccessful or malformed response")
    return payload


def audit_grouped(payload: dict, requested_date: str) -> tuple[dict, set[str]]:
    """Checks provider payload shape without treating an ETF-inclusive feed as common-stock breadth."""
    if payload.get("adjusted") is not True:
        raise RuntimeError("Massive grouped bars are not explicitly adjusted")
    rows = payload.get("results")
    if not isinstance(rows, list) or len(rows) < MIN_GROUPED_ROWS:
        raise RuntimeError("Insufficient Massive grouped market coverage")
    observed: set[str] = set()
    usable: list[tuple[str, float, float, float]] = []
    ny = ZoneInfo("America/New_York")
    for row in rows:
        if not isinstance(row, dict):
            raise RuntimeError("Malformed Massive grouped bar")
        ticker = row.get("T")
        if not isinstance(ticker, str) or not ticker or ticker in observed:
            raise RuntimeError("Missing or duplicated Massive grouped ticker")
        observed.add(ticker)
        try:
            close, high, low = (float(row[k]) for k in ("c", "h", "l"))
            stamp = datetime.fromtimestamp(float(row["t"]) / 1000, timezone.utc)
        except (ValueError, TypeError, OverflowError, KeyError, OSError):
            raise RuntimeError("Missing or invalid Massive OHLC or timestamp") from None
        if not (0 < low <= close <= high and stamp.astimezone(ny).date().isoformat() == requested_date):
            raise RuntimeError("Massive bar price range or market date mismatch")
        usable.append((ticker, close, high, low))
    fingerprint = sha256_json(sorted(usable))
    return {
        "date": requested_date,
        "grouped_rows": len(rows),
        "unique_tickers": len(observed),
        "adjusted": True,
        "includes_non_common_securities": True,
        "grouped_ohlc_sha256": fingerprint,
    }, observed


def reference_universe(
    session: requests.Session, key: str, date: str, security_type: str
) -> tuple[set[str], list[dict], int]:
    """Query the date-specific reference list to avoid ETF contamination and current-only survivor filters."""
    if security_type not in ELIGIBLE_TYPES:
        raise ValueError("Invalid security class")
    symbols: set[str] = set()
    metas: list[dict] = []
    url = BASE + "/v3/reference/tickers"
    params: dict | None = {"date": date, "type": security_type, "market": "stocks",
                           "active": "true", "limit": 1000, "sort": "ticker"}
    visited: set[str] = set()
    for page in range(1, PAGE_LIMIT + 1):
        if url in visited:
            raise RuntimeError("Reference pagination loop")
        visited.add(url)
        payload = request_json(session, url, key, params)
        rows = payload.get("results")
        if not isinstance(rows, list):
            raise RuntimeError("Malformed reference ticker list")
        for item in rows:
            if not isinstance(item, dict) or item.get("type") != security_type or item.get("market") != "stocks" or item.get("active") is not True:
                raise RuntimeError("Reference universe type/date contract violation")
            ticker = item.get("ticker")
            if not isinstance(ticker, str) or not ticker or ticker in symbols:
                raise RuntimeError("Duplicate or missing reference ticker")
            symbols.add(ticker)
            metas.append({"ticker": ticker, "type": security_type, "exchange": item.get("primary_exchange")})
        next_url = payload.get("next_url")
        if not next_url:
            # A full page without a continuation token cannot certify completeness.
            if len(rows) >= 1000:
                raise RuntimeError("Reference universe possibly truncated: full page without cursor")
            return symbols, metas, page
        if not isinstance(next_url, str):
            raise RuntimeError("Invalid reference pagination link")
        parsed = urlparse(next_url)
        if parsed.scheme != "https" or parsed.hostname != "api.massive.com" or parsed.path != "/v3/reference/tickers":
            raise RuntimeError("Untrusted reference pagination URL")
        url = next_url
        params = None
    raise RuntimeError("Reference pagination cap hit; refusing partial universe")


def run_audit(session: requests.Session, api_key: str, day: str) -> dict:
    try:
        date = datetime.strptime(day, "%Y-%m-%d").date()
    except ValueError:
        raise ValueError("Expected YYYY-MM-DD date") from None
    if date > datetime.now(ZoneInfo("America/New_York")).date():
        raise ValueError("Cannot query future date")
    grouped = request_json(session, BASE + f"/v2/aggs/grouped/locale/us/market/stocks/{day}",
                           api_key, {"adjusted": "true", "include_otc": "false"})
    summary, tickers = audit_grouped(grouped, day)
    lookup: dict[str, str] = {}
    combined_meta: list[dict] = []
    pages: dict[str, int] = {}
    for sec_type in ELIGIBLE_TYPES:
        symbols, meta, n_pages = reference_universe(session, api_key, day, sec_type)
        overlapping = set(lookup).intersection(symbols)
        if overlapping:
            raise RuntimeError("Cross-class reference ticker collision")
        lookup.update({s: sec_type for s in symbols})
        combined_meta.extend(meta)
        pages[sec_type] = n_pages
    retained = tickers.intersection(lookup)
    if len(retained) < 1000:
        raise RuntimeError("Too few date-qualified common-stock bars")
    types_on_day = {t: sum(lookup[k] == t for k in retained) for t in ELIGIBLE_TYPES}
    return {
        "schema": "market-top-v218-massive-source-audit-v1",
        "asof": day,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "provider": "Massive grouped daily + date-specific reference ticker types",
        "allowed_types": list(ELIGIBLE_TYPES),
        "classification": {
            "qualified_bars": len(retained),
            "qualified_counts": types_on_day,
            "excluded_or_unclassified_bars": len(tickers) - len(retained),
            "reference_pages": pages,
            "qualified_reference_sha256": sha256_json(sorted(combined_meta, key=lambda item: (item["ticker"], item["type"]))),
            "qualifying_bar_tickers_sha256": sha256_json(sorted(retained)),
        },
        "grouped": summary,
        "status": "PROVIDER_SOURCE_AUDIT_ONLY",
        "production_eligible": False,
        "frozen_score_comparable": False,
        "note": "ETF-inclusive grouped data cannot replace stock-only MarketParquet. "
                "Adjusted-price and symbol-universe definitions need cross-source validation. "
                "The frozen 252-prior-session + 20-session signal has NOT been calculated.",
    }


def previous_weekday() -> str:
    day = datetime.now(ZoneInfo("America/New_York")).date() - timedelta(days=1)
    while day.weekday() >= 5:
        day -= timedelta(days=1)
    return day.isoformat()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--date", default=previous_weekday())
    parser.add_argument("--output", default="research/out/master_top_massive_source_audit.json")
    args = parser.parse_args()
    key = os.getenv("MASSIVE_API_KEY", "").strip()
    if not key:
        raise SystemExit("MASSIVE_API_KEY is missing; unable to certify Massive source coverage")
    report = run_audit(requests.Session(), key, args.date)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"status": report["status"], "asof": report["asof"],
                      "raw_bars": report["grouped"]["grouped_rows"],
                      "qualifying_common_bars": report["classification"]["qualified_bars"],
                      "output": str(output)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
