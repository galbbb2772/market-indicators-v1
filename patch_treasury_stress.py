from __future__ import annotations

import io
import json
import time
from pathlib import Path

import numpy as np
import pandas as pd
import requests

ROOT = Path(__file__).resolve().parent
DATA_PATH = ROOT / "docs" / "data" / "current.json"
HTTP = requests.Session()
HTTP.headers.update({"User-Agent":"Mozilla/5.0 MarketRegimeLab/1.0"})


def fetch_fred(series_id: str) -> pd.Series:
    url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}&cosd=2018-01-01"
    last = None
    for attempt in range(3):
        try:
            r = HTTP.get(url, timeout=(5, 12))
            r.raise_for_status()
            df = pd.read_csv(io.StringIO(r.text))
            if len(df.columns) < 2:
                raise ValueError(f"FRED {series_id}: unexpected columns")
            date_col = df.columns[0]
            value_col = series_id if series_id in df.columns else df.columns[1]
            dates = pd.to_datetime(df[date_col], errors="coerce")
            vals = pd.to_numeric(df[value_col], errors="coerce")
            s = pd.Series(vals.values, index=dates, dtype=float).dropna().sort_index()
            if s.empty:
                raise ValueError(f"FRED {series_id}: no usable values")
            return s
        except Exception as exc:
            last = exc
            if attempt < 2:
                time.sleep(1.5 * (attempt + 1))
    raise last or RuntimeError(f"FRED {series_id} request failed")


def percentile(s: pd.Series, window: int = 756) -> pd.Series:
    s = pd.to_numeric(s, errors="coerce").astype(float)
    def f(a):
        a = a[np.isfinite(a)]
        if len(a) < 20:
            return np.nan
        return 100.0 * np.mean(a <= a[-1])
    return s.rolling(window, min_periods=60).apply(f, raw=True)


def main() -> None:
    data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    errors = {}
    fetched = {}
    for sid in ("WTREGEN", "DGS1MO", "DGS3MO"):
        try:
            fetched[sid] = fetch_fred(sid)
        except Exception as exc:
            errors[sid] = repr(exc)

    if not fetched:
        raise RuntimeError("Treasury stress inputs unavailable: " + json.dumps(errors))

    idx = pd.DatetimeIndex([])
    for s in fetched.values():
        idx = idx.union(pd.DatetimeIndex(s.index))
    idx = idx.sort_values()
    tga = fetched.get("WTREGEN", pd.Series(index=idx, dtype=float)).reindex(idx).ffill()
    m1 = fetched.get("DGS1MO", pd.Series(index=idx, dtype=float)).reindex(idx).ffill()
    m3 = fetched.get("DGS3MO", pd.Series(index=idx, dtype=float)).reindex(idx).ffill()

    weighted_parts = []
    weights = []
    if tga.notna().sum() >= 60:
        # Low Treasury General Account cash = less operating buffer.
        weighted_parts.append((100.0 - percentile(tga)) * 1.00)
        weights.append(1.00)
        # Rapid four-week TGA drawdown is a separate deterioration signal.
        draw = -(tga.pct_change(20) * 100.0)
        weighted_parts.append(percentile(draw) * 0.55)
        weights.append(0.55)
    if m1.notna().sum() >= 60 and m3.notna().sum() >= 60:
        # Near-term bill dislocation: 1M yield unusually above 3M.
        spread = (m1 - m3).clip(lower=0)
        weighted_parts.append(percentile(spread) * 0.85)
        weights.append(0.85)

    if not weighted_parts:
        raise RuntimeError("Treasury stress calculation has insufficient history: " + json.dumps(errors))

    aligned = pd.concat(weighted_parts, axis=1).sort_index().ffill()
    values = aligned.to_numpy(dtype=float)
    valid = np.isfinite(values)
    w = np.array(weights, dtype=float)
    num = np.nansum(values, axis=1)
    den = np.sum(valid * w, axis=1)
    stress = pd.Series(np.where(den > 0, num / den, np.nan), index=aligned.index).clip(0,100).dropna()
    if stress.empty:
        raise RuntimeError("Treasury stress calculation empty")

    d1 = stress.diff(); d2 = d1.diff()
    last_tga = float(tga.dropna().iloc[-1]) if not tga.dropna().empty else None
    spread_series = (m1 - m3).dropna()
    last_spread = float(spread_series.iloc[-1]) if not spread_series.empty else None

    for item in data.get("indicators", []):
        if item.get("id") != "treasury_short_default":
            continue
        item["score"] = round(float(stress.iloc[-1]), 2)
        item["raw"] = round(last_tga, 2) if last_tga is not None else None
        item["raw_unit"] = "USD billions TGA; context funding-stress proxy"
        item["d1"] = round(float(d1.dropna().iloc[-1]), 2) if not d1.dropna().empty else None
        item["d2"] = round(float(d2.dropna().iloc[-1]), 2) if not d2.dropna().empty else None
        item["asof"] = str(stress.index[-1].date())
        item["history"] = [{"date":str(i.date()),"score":round(float(v),2)} for i,v in stress.tail(180).items()]
        item["quality"] = "official_macro_proxy_context"
        item["source_note"] = (
            "FRED WTREGEN + DGS1MO/DGS3MO. Treasury cash/funding-stress proxy, NOT a literal default probability. "
            "Archive/context only; no Market Model V2 vote."
        )
        item["context_detail"] = {
            "tga_latest": round(last_tga,2) if last_tga is not None else None,
            "one_month_minus_three_month_pct_points": round(last_spread,4) if last_spread is not None else None,
            "source_errors": errors,
        }
        break

    model = data.get("market_model_v2")
    if isinstance(model, dict):
        model["treasury_short_stress_status"] = {
            "connected": True,
            "feeds_market_model": False,
            "source": "FRED WTREGEN,DGS1MO,DGS3MO",
            "available_inputs": sorted(fetched),
            "errors": errors,
            "interpretation": "funding/cash stress proxy, not default probability"
        }
    DATA_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print("Treasury short stress:", round(float(stress.iloc[-1]),2), "TGA", last_tga, "1m-3m", last_spread, "errors", errors)


if __name__ == "__main__":
    main()
