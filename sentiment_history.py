from __future__ import annotations

import io
import json
import math
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

import numpy as np
import pandas as pd
import requests

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "docs" / "data" / "sentiment_history.json"
START = pd.Timestamp("1990-01-01", tz="UTC")
HTTP = requests.Session()
HTTP.headers.update({"User-Agent": "Mozilla/5.0 MarketRegimeLab/SentimentHistoryV1"})

YAHOO = {
    "SPY": "SPY",
    "RSP": "RSP",
    "IWM": "IWM",
    "HYG": "HYG",
    "LQD": "LQD",
    "VIX": "^VIX",
    "sp500": "^GSPC",
    "nasdaq": "^IXIC",
    "dow": "^DJI",
}
FRED_IDS = ["BAMLH0A0HYM2", "NFCI"]


def request_json(url: str, timeout: int = 15) -> dict:
    last = None
    for base in (url, url.replace("query1.finance.yahoo.com", "query2.finance.yahoo.com")):
        for wait in (0, 2):
            if wait:
                time.sleep(wait)
            try:
                r = HTTP.get(base, timeout=timeout)
                if r.ok:
                    return r.json()
                last = RuntimeError(f"HTTP {r.status_code}: {r.text[:160]}")
            except Exception as exc:
                last = exc
    raise last or RuntimeError("request failed")


def yahoo_close(symbol: str) -> pd.Series:
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
        raise ValueError("no Yahoo history")
    idx = pd.to_datetime(ts, unit="s", utc=True).tz_convert(None).normalize()
    s = pd.Series(pd.to_numeric(close, errors="coerce"), index=idx, dtype=float).dropna().sort_index()
    return s[~s.index.duplicated(keep="last")]


def fred_history(errors: dict[str, str]) -> dict[str, pd.Series]:
    try:
        url = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=" + ",".join(FRED_IDS) + "&cosd=1990-01-01"
        r = HTTP.get(url, timeout=15)
        r.raise_for_status()
        df = pd.read_csv(io.StringIO(r.text))
        date_col = df.columns[0]
        df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
        df = df.dropna(subset=[date_col]).set_index(date_col).sort_index()
        out = {}
        for sid in FRED_IDS:
            if sid in df.columns:
                s = pd.to_numeric(df[sid], errors="coerce").dropna()
                if not s.empty:
                    out[sid] = s.astype(float)
        return out
    except Exception as exc:
        errors["fred"] = repr(exc)
        return {}


def rolling_percentile(s: pd.Series, window: int = 756) -> pd.Series:
    s = pd.Series(s).dropna().astype(float).sort_index()
    minp = min(60, max(10, window // 10))

    def f(a: np.ndarray) -> float:
        if len(a) == 0 or not np.isfinite(a[-1]):
            return np.nan
        return 100.0 * float(np.mean(a <= a[-1]))

    return s.rolling(window, min_periods=minp).apply(f, raw=True)


def score(s: pd.Series, high: bool = True, window: int = 756) -> pd.Series:
    p = rolling_percentile(s, window)
    return p if high else 100.0 - p


def align(*series: pd.Series) -> list[pd.Series]:
    idx = pd.DatetimeIndex([])
    for s in series:
        idx = idx.union(pd.DatetimeIndex(s.index))
    idx = idx.sort_values()
    return [pd.Series(s).reindex(idx).ffill() for s in series]


def avg(*series: pd.Series) -> pd.Series:
    if not series:
        return pd.Series(dtype=float)
    aligned = align(*series)
    return pd.concat(aligned, axis=1).mean(axis=1, skipna=True)


def inv(s: pd.Series) -> pd.Series:
    return 100.0 - pd.Series(s)


def pct(s: pd.Series, n: int) -> pd.Series:
    return pd.Series(s).pct_change(n) * 100.0


def classify_euphoria(v: float) -> str:
    if not np.isfinite(v):
        return "数据不足"
    if v >= 80:
        return "狂热"
    if v >= 60:
        return "乐观"
    if v >= 30:
        return "中性"
    return "低迷"


def cycle_stats(s: pd.Series) -> dict:
    s = pd.Series(s).dropna().astype(float).sort_index()
    if s.empty:
        return {}
    labels = s.map(classify_euphoria)
    groups = (labels != labels.shift()).cumsum()
    episodes = []
    for _, block in labels.groupby(groups):
        if block.empty:
            continue
        episodes.append({
            "label": str(block.iloc[0]),
            "start": str(block.index[0].date()),
            "end": str(block.index[-1].date()),
            "trading_days": int(len(block)),
        })
    out = {"bands": {}, "current_episode": episodes[-1] if episodes else None}
    for label in ("低迷", "中性", "乐观", "狂热"):
        vals = np.array([x["trading_days"] for x in episodes if x["label"] == label], dtype=float)
        if len(vals):
            out["bands"][label] = {
                "episodes": int(len(vals)),
                "median_trading_days": round(float(np.median(vals)), 2),
                "p25": round(float(np.quantile(vals, 0.25)), 2),
                "p75": round(float(np.quantile(vals, 0.75)), 2),
                "max_trading_days": int(np.max(vals)),
            }
    return out


def first_valid_date(s: pd.Series) -> str | None:
    x = pd.Series(s).dropna()
    return str(x.index[0].date()) if not x.empty else None


def last_value(s: pd.Series) -> float | None:
    x = pd.Series(s).dropna()
    return round(float(x.iloc[-1]), 2) if not x.empty else None


def main() -> None:
    errors: dict[str, str] = {}
    market: dict[str, pd.Series] = {}
    for key, symbol in YAHOO.items():
        try:
            market[key] = yahoo_close(symbol)
        except Exception as exc:
            errors[f"yahoo:{symbol}"] = repr(exc)

    fred = fred_history(errors)

    required = ["SPY", "VIX"]
    missing = [x for x in required if x not in market]
    if missing:
        raise RuntimeError("missing critical market series: " + ",".join(missing))

    spy = market["SPY"]
    vix = market["VIX"]

    # Existing Market Regime Lab formulas, reconstructed over the longest available history.
    support_parts = [score(spy / spy.rolling(n).mean() - 1.0) for n in (20, 50, 200)]
    if "RSP" in market:
        rsp, spya = align(market["RSP"], spy)
        support_parts.append(score(pct(rsp, 20) - pct(spya, 20)))
    market_support = avg(*support_parts)

    money_parts = [market_support, score(pct(spy, 20))]
    if "IWM" in market:
        money_parts.append(score(pct(market["IWM"], 20)))
    money_making_effect = avg(*money_parts)

    credit_parts = []
    if "BAMLH0A0HYM2" in fred:
        credit_parts.append(score(fred["BAMLH0A0HYM2"]))
    if "HYG" in market and "LQD" in market:
        hyg, lqd = align(market["HYG"], market["LQD"])
        credit_parts.append(score(hyg / lqd, high=False))
    credit_pressure = avg(*credit_parts) if credit_parts else pd.Series(dtype=float)
    market_fear = avg(score(vix), credit_pressure) if not credit_pressure.empty else score(vix)

    dd20 = -(spy / spy.rolling(20).max() - 1.0) * 100.0
    largecap_panic = avg(score(vix), score(dd20))

    liq_parts = []
    if "NFCI" in fred:
        liq_parts.append(score(fred["NFCI"]))
    if "BAMLH0A0HYM2" in fred:
        liq_parts.append(score(fred["BAMLH0A0HYM2"]))
    if "HYG" in market and "LQD" in market:
        hyg, lqd = align(market["HYG"], market["LQD"])
        liq_parts.append(score(hyg / lqd, high=False))
    liquidity_risk = avg(*liq_parts) if liq_parts else market_fear

    high_yield = score(fred["BAMLH0A0HYM2"]) if "BAMLH0A0HYM2" in fred else credit_pressure
    institutional_panic = avg(high_yield, liquidity_risk, market_fear)

    market_optimism = avg(market_support, money_making_effect, inv(market_fear)).clip(0, 100)
    market_pessimism = avg(market_fear, largecap_panic, institutional_panic).clip(0, 100)

    # Existing market_bias is (optimism + (100-pessimism))/2. Its inverse is a clean total-negative pressure view.
    total_negative = avg(market_pessimism, inv(market_optimism)).clip(0, 100)

    dist20 = (spy / spy.rolling(20).mean() - 1.0) * 100.0
    market_overextension = score(dist20.abs())
    market_euphoria = avg(market_optimism, inv(market_pessimism), market_overextension, money_making_effect).clip(0, 100)

    metrics = {
        "optimism": market_optimism,
        "pessimism": market_pessimism,
        "total_negative": total_negative,
        "euphoria": market_euphoria,
    }

    all_dates = pd.DatetimeIndex([])
    for s in metrics.values():
        all_dates = all_dates.union(pd.DatetimeIndex(pd.Series(s).dropna().index))
    if all_dates.empty:
        raise RuntimeError("no reconstructed sentiment history")
    start_date = all_dates.min()
    end_date = max(pd.Series(s).dropna().index[-1] for s in metrics.values() if not pd.Series(s).dropna().empty)
    all_dates = pd.date_range(start_date, end_date, freq="D")

    aligned_metrics = {k: pd.Series(v).reindex(all_dates).ffill() for k, v in metrics.items()}
    index_map = {k: market[k].reindex(all_dates).ffill() for k in ("sp500", "nasdaq", "dow") if k in market}

    daily = []
    for dt in all_dates:
        if index_map and not any(dt in market[k].index for k in index_map):
            continue
        row = {"date": str(dt.date())}
        for k, s in aligned_metrics.items():
            v = s.loc[dt]
            if pd.notna(v):
                row[k] = round(float(v), 3)
        for k, s in index_map.items():
            v = s.loc[dt]
            if pd.notna(v):
                row[k] = round(float(v), 4)
        daily.append(row)

    latest_e = pd.Series(market_euphoria).dropna()
    latest_e_val = float(latest_e.iloc[-1]) if not latest_e.empty else math.nan
    e_hist_pct = 100.0 * float(np.mean(latest_e <= latest_e_val)) if not latest_e.empty else math.nan

    payload = {
        "version": "SENTIMENT-HISTORY-V1-2026-10-01",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "meta": {
            "description": "Historical reconstruction of the existing Market Regime Lab optimism/pessimism family plus a total-negative view and euphoria composite.",
            "warning": "Historical values are reconstructed from currently available market/FRED data and are not point-in-time archived model outputs. Use for regime/cycle research, not as a claim of historical real-time signals.",
            "requested_start": str(START.date()),
            "series_start": {k: first_valid_date(v) for k, v in metrics.items()},
            "series_end": {k: str(pd.Series(v).dropna().index[-1].date()) if not pd.Series(v).dropna().empty else None for k, v in metrics.items()},
            "data_sources": {
                "market": "Yahoo Finance daily closes via chart API",
                "credit": "FRED BAMLH0A0HYM2",
                "financial_conditions": "FRED NFCI",
            },
            "formula": {
                "optimism": "mean(market_support, money_making_effect, 100-market_fear)",
                "pessimism": "mean(market_fear, largecap_panic, institutional_panic)",
                "total_negative": "mean(market_pessimism, 100-market_optimism) = 100-market_bias",
                "euphoria": "mean(market_optimism, 100-market_pessimism, market_overextension, money_making_effect)",
            },
        },
        "latest": {
            "date": str(latest_e.index[-1].date()) if not latest_e.empty else None,
            "optimism": last_value(market_optimism),
            "pessimism": last_value(market_pessimism),
            "total_negative": last_value(total_negative),
            "euphoria": round(latest_e_val, 2) if np.isfinite(latest_e_val) else None,
            "euphoria_band": classify_euphoria(latest_e_val),
            "euphoria_historical_percentile": round(e_hist_pct, 2) if np.isfinite(e_hist_pct) else None,
        },
        "cycle_stats": cycle_stats(market_euphoria),
        "daily": daily,
        "errors": errors,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print("sentiment history updated:", len(daily), "rows; starts", payload["meta"]["series_start"], "; errors", len(errors))


if __name__ == "__main__":
    main()
