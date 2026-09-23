from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "docs" / "data" / "current.json"
START = pd.Timestamp("2016-01-01", tz="UTC")
HTTP = requests.Session()
HTTP.headers.update({"User-Agent": "Mozilla/5.0 MarketRegimeLab/1.2"})

INDEXES = {
    "sp500": {"symbol": "^GSPC", "name": "S&P 500"},
    "nasdaq": {"symbol": "^IXIC", "name": "Nasdaq Composite"},
    "dow": {"symbol": "^DJI", "name": "Dow Jones"},
}


def request_json(url: str, timeout: int = 12) -> dict:
    last = None
    variants = [url, url.replace("query1.finance.yahoo.com", "query2.finance.yahoo.com")]
    for base in variants:
        for wait in (0, 2):
            if wait:
                time.sleep(wait)
            try:
                r = HTTP.get(base, timeout=timeout)
                if r.ok:
                    return r.json()
                last = RuntimeError(f"HTTP {r.status_code}: {r.text[:120]}")
            except Exception as exc:
                last = exc
    raise last or RuntimeError("request failed")


def yahoo_index(symbol: str) -> pd.Series:
    p1 = int(START.timestamp())
    p2 = int(datetime.now(timezone.utc).timestamp()) + 86400
    sym = quote(symbol, safe="")
    url = (
        f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}"
        f"?period1={p1}&period2={p2}&interval=1d&events=history&includeAdjustedClose=true"
    )
    data = request_json(url)
    res = (data.get("chart") or {}).get("result")
    if not res:
        raise ValueError(str((data.get("chart") or {}).get("error")))
    obj = res[0]
    ts = obj.get("timestamp") or []
    q = ((obj.get("indicators") or {}).get("quote") or [{}])[0]
    adj = ((obj.get("indicators") or {}).get("adjclose") or [{}])[0].get("adjclose")
    close = adj if adj and len(adj) == len(ts) else q.get("close")
    if not ts or not close:
        raise ValueError("no index history")
    idx = pd.to_datetime(ts, unit="s", utc=True).tz_convert(None).normalize()
    s = pd.Series(pd.to_numeric(close, errors="coerce"), index=idx, dtype=float).dropna().sort_index()
    s = s[s.index >= pd.Timestamp("2016-01-01")]
    if s.empty:
        raise ValueError("empty index history")
    return s


def pct_from(s: pd.Series, n: int) -> float | None:
    if len(s) <= n or not s.iloc[-n-1]:
        return None
    return float((s.iloc[-1] / s.iloc[-n-1] - 1.0) * 100.0)


def main() -> None:
    payload = json.loads(OUT.read_text(encoding="utf-8"))
    errors = payload.setdefault("errors", {})
    series: dict[str, pd.Series] = {}

    for key, meta in INDEXES.items():
        try:
            series[key] = yahoo_index(meta["symbol"])
        except Exception as exc:
            errors[f"history_index:{meta['symbol']}"] = repr(exc)

    if not series:
        payload["index_market_history"] = {
            "status": "unavailable",
            "start": "2016-01-01",
            "symbols": INDEXES,
            "daily": [],
            "latest": {},
        }
        OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return

    all_dates = pd.DatetimeIndex([])
    for s in series.values():
        all_dates = all_dates.union(s.index)
    all_dates = all_dates.sort_values()

    aligned = {k: s.reindex(all_dates).ffill() for k, s in series.items()}
    daily = []
    for dt in all_dates:
        row = {"date": str(dt.date())}
        for key, s in aligned.items():
            v = s.loc[dt]
            if pd.notna(v):
                row[key] = round(float(v), 4)
        daily.append(row)

    latest = {}
    for key, s in series.items():
        start_value = float(s.iloc[0])
        latest[key] = {
            **INDEXES[key],
            "asof": str(s.index[-1].date()),
            "close": round(float(s.iloc[-1]), 4),
            "day_pct": round(pct_from(s, 1), 3) if pct_from(s, 1) is not None else None,
            "week_pct": round(pct_from(s, 5), 3) if pct_from(s, 5) is not None else None,
            "month_pct": round(pct_from(s, 20), 3) if pct_from(s, 20) is not None else None,
            "since_2016_pct": round(float((s.iloc[-1] / start_value - 1.0) * 100.0), 2),
        }

    payload["index_market_history"] = {
        "status": "ok",
        "start": str(all_dates.min().date()),
        "end": str(all_dates.max().date()),
        "symbols": INDEXES,
        "daily": daily,
        "latest": latest,
        "method": {
            "returns": "price return using daily close, rebased to the selected range in the browser",
            "correlation": "browser computes Pearson correlation between daily change in market score and same-day index return for the selected range",
        },
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"history updated: {len(daily)} dates, {len(series)} indexes")


if __name__ == "__main__":
    main()
