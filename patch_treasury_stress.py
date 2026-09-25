from __future__ import annotations

import io
import json
from pathlib import Path

import numpy as np
import pandas as pd
import requests

ROOT = Path(__file__).resolve().parent
DATA_PATH = ROOT / "docs" / "data" / "current.json"
URL = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=WTREGEN,DGS1MO,DGS3MO&cosd=2015-01-01"


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
    r = requests.get(URL, headers={"User-Agent":"Mozilla/5.0 MarketRegimeLab/1.0"}, timeout=15)
    r.raise_for_status()
    df = pd.read_csv(io.StringIO(r.text))
    date_col = df.columns[0]
    df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
    df = df.dropna(subset=[date_col]).set_index(date_col).sort_index()
    for c in ("WTREGEN","DGS1MO","DGS3MO"):
        if c in df:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    idx = df.index
    tga = df.get("WTREGEN", pd.Series(index=idx, dtype=float)).reindex(idx).ffill()
    m1 = df.get("DGS1MO", pd.Series(index=idx, dtype=float)).reindex(idx).ffill()
    m3 = df.get("DGS3MO", pd.Series(index=idx, dtype=float)).reindex(idx).ffill()

    parts=[]
    if tga.notna().sum() >= 60:
        # Low Treasury cash = less operating buffer; higher score means higher stress.
        parts.append(100.0 - percentile(tga))
        # Rapid four-week cash drawdown is a separate deterioration signal.
        draw = -(tga.pct_change(20) * 100.0)
        parts.append(percentile(draw) * 0.55)
    if m1.notna().sum() >= 60 and m3.notna().sum() >= 60:
        # Near-term bill dislocation: 1M yield unusually above 3M.
        spread = (m1 - m3).clip(lower=0)
        parts.append(percentile(spread) * 0.85)
    if not parts:
        raise RuntimeError("Treasury stress inputs unavailable")

    aligned = pd.concat(parts, axis=1).sort_index().ffill()
    # Normalize by the active component weights rather than treating missing components as zero.
    weights = []
    if tga.notna().sum() >= 60:
        weights.extend([1.0, 0.55])
    if m1.notna().sum() >= 60 and m3.notna().sum() >= 60:
        weights.append(0.85)
    w = np.array(weights, dtype=float)
    values = aligned.to_numpy(dtype=float)
    valid = np.isfinite(values)
    num = np.nansum(values, axis=1)
    den = np.sum(valid * w, axis=1)
    # parts already include their weights above; first TGA percentile is weight 1.
    stress = pd.Series(np.where(den > 0, num / den, np.nan), index=aligned.index).clip(0,100).dropna()
    if stress.empty:
        raise RuntimeError("Treasury stress calculation empty")

    d1=stress.diff(); d2=d1.diff()
    last_tga=float(tga.dropna().iloc[-1]) if not tga.dropna().empty else None
    last_spread=float((m1-m3).dropna().iloc[-1]) if not (m1-m3).dropna().empty else None
    for item in data.get("indicators",[]):
        if item.get("id") != "treasury_short_default":
            continue
        item["score"] = round(float(stress.iloc[-1]),2)
        item["raw"] = round(last_tga,2) if last_tga is not None else None
        item["raw_unit"] = "USD billions TGA; context funding-stress proxy"
        item["d1"] = round(float(d1.dropna().iloc[-1]),2) if not d1.dropna().empty else None
        item["d2"] = round(float(d2.dropna().iloc[-1]),2) if not d2.dropna().empty else None
        item["asof"] = str(stress.index[-1].date())
        item["history"] = [{"date":str(i.date()),"score":round(float(v),2)} for i,v in stress.tail(180).items()]
        item["quality"] = "official_macro_proxy_context"
        item["source_note"] = (
            "FRED WTREGEN + DGS1MO/DGS3MO. This is a Treasury cash/funding-stress proxy, NOT a literal default probability. "
            "Archive/context only; no Market Model V2 vote."
        )
        item["context_detail"] = {
            "tga_latest": round(last_tga,2) if last_tga is not None else None,
            "one_month_minus_three_month_pct_points": round(last_spread,4) if last_spread is not None else None,
        }
        break

    model=data.get("market_model_v2")
    if isinstance(model,dict):
        model["treasury_short_stress_status"]={
            "connected":True,
            "feeds_market_model":False,
            "source":"FRED WTREGEN,DGS1MO,DGS3MO",
            "interpretation":"funding/cash stress proxy, not default probability"
        }
    DATA_PATH.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding="utf-8")
    print("Treasury short stress:",round(float(stress.iloc[-1]),2),"TGA",last_tga,"1m-3m",last_spread)


if __name__ == "__main__":
    main()
