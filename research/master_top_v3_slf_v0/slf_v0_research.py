#!/usr/bin/env python3
"""
MASTER TOP V3 — SLF V0 research implementation
Systemic Liquidity / Fragility（系统性流动性与金融脆弱性路线）

Implements the frozen preregistration in MASTER_TOP_V3_SLF_PREREG_V0.md.
This script is research-only. It must not retune formulae or thresholds after results.
"""
from __future__ import annotations
import io, json, math, hashlib
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd
import requests

OUT = Path(__file__).resolve().parent / "output"
OUT.mkdir(parents=True, exist_ok=True)

UA = "market-top-research/SLF-v0 (public-source reproducibility)"
FSI_URL = "https://www.financialresearch.gov/financial-stress-index/data/files/ofr-fsi.csv"
FSI_MIRROR_URL = "https://www.diawonds.com/ofr/"
NYPD_URL = "https://data.financialresearch.gov/v1/series/timeseries"
STOOQ_URL = "https://stooq.com/q/d/l/?s=%5Espx&i=d"

THRESHOLDS = [70.0, 80.0, 90.0]
VARIANTS = ["slf_raw", "slf90", "slf95"]
EPISODE_LOCK = 126

EVENT_WINDOWS = [
    ("RISK_2007", "2007-01-01", "2008-03-31", "risk"),
    ("RISK_2011", "2011-01-01", "2011-12-31", "risk"),
    ("RISK_2015_16", "2015-01-01", "2016-06-30", "risk"),
    ("RISK_2018_Q4", "2018-01-01", "2019-03-31", "risk"),
    ("RISK_2020", "2019-07-01", "2020-12-31", "risk"),
    ("RISK_2022", "2021-01-01", "2022-12-31", "risk"),
    ("CONTROL_2003_04", "2003-01-01", "2004-12-31", "control"),
    ("CONTROL_2005_06", "2005-01-01", "2006-12-31", "control"),
    ("CONTROL_2013_14", "2013-01-01", "2014-12-31", "control"),
    ("CONTROL_2017", "2017-01-01", "2017-12-31", "control"),
    ("CONTROL_2019_EX_REPO", "2019-01-01", "2019-08-31", "control"),
]

def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()

def get_bytes(url: str, params=None) -> bytes:
    r = requests.get(url, params=params, headers={"User-Agent": UA, "Accept": "*/*"}, timeout=60)
    r.raise_for_status()
    return r.content

def pick_col(cols: Iterable[str], *needles: str) -> str:
    clist = list(cols)
    low = {c: str(c).strip().lower().replace("_", " ") for c in clist}
    for c, v in low.items():
        if all(n.lower() in v for n in needles):
            return c
    raise KeyError(f"Could not find column containing {needles}; columns={clist}")

def load_fsi():
    source_url = FSI_URL
    source_role = "official_ofr_csv"
    try:
        raw = get_bytes(FSI_URL)
        df = pd.read_csv(io.BytesIO(raw))
    except Exception as official_error:
        # Frozen pre-score fallback: retrospective mirror only. Exact raw bytes are hashed.
        source_url = FSI_MIRROR_URL
        source_role = "diawonds_retrospective_mirror_of_ofr"
        raw = get_bytes(FSI_MIRROR_URL)
        tables = pd.read_html(io.BytesIO(raw))
        candidates = []
        for t in tables:
            cols = [str(c).strip().lower() for c in t.columns]
            if any("fund" in c for c in cols) and any("safe" in c for c in cols):
                candidates.append(t)
        if not candidates:
            raise RuntimeError(f"No OFR-like table in mirror; official_error={official_error}")
        df = max(candidates, key=len)
    date_col = pick_col(df.columns, "date")
    funding_col = pick_col(df.columns, "fund")
    try:
        safe_col = pick_col(df.columns, "safe")
    except KeyError:
        safe_col = pick_col(df.columns, "flight")
    out = df[[date_col, funding_col, safe_col]].copy()
    out.columns = ["source_date", "funding", "safe_assets"]
    # Mirror uses day-first dates; ISO official data remains correctly parsed with dayfirst=False fallback.
    parsed = pd.to_datetime(out["source_date"], errors="coerce")
    if parsed.notna().mean() < 0.95:
        parsed = pd.to_datetime(out["source_date"], errors="coerce", dayfirst=True)
    out["source_date"] = parsed
    out["funding"] = pd.to_numeric(out["funding"], errors="coerce")
    out["safe_assets"] = pd.to_numeric(out["safe_assets"], errors="coerce")
    out = out.dropna(subset=["source_date"]).sort_values("source_date")
    # Conservative rule frozen in data contract: observation t -> effective t+3 US business-day proxy.
    out["date"] = out["source_date"] + pd.offsets.BDay(3)
    meta = {"date_col": str(date_col), "funding_col": str(funding_col), "safe_col": str(safe_col),
            "columns": [str(c) for c in df.columns], "source_url": source_url, "source_role": source_role}
    return out, raw, meta

def load_nypd_series(mnemonic: str):
    raw = get_bytes(NYPD_URL, {"mnemonic": mnemonic})
    arr = json.loads(raw.decode("utf-8"))
    df = pd.DataFrame(arr, columns=["source_date", mnemonic])
    df["source_date"] = pd.to_datetime(df["source_date"], errors="coerce")
    df[mnemonic] = pd.to_numeric(df[mnemonic], errors="coerce")
    return df.dropna(subset=["source_date"]).sort_values("source_date"), raw

def load_fails():
    d_m = "NYPD-PD_AFtD_TOT-A"
    r_m = "NYPD-PD_AFtR_TOT-A"
    d, raw_d = load_nypd_series(d_m)
    r, raw_r = load_nypd_series(r_m)
    x = d.merge(r, on="source_date", how="outer").sort_values("source_date")
    x["fails_deliver"] = x[d_m]
    x["fails_receive"] = x[r_m]
    x["fails_total"] = x["fails_deliver"] + x["fails_receive"]
    x["log_fails"] = np.log1p(x["fails_total"].clip(lower=0))
    x["med52"] = x["log_fails"].rolling(52, min_periods=52).median()
    x["settlement_raw"] = (x["log_fails"] - x["med52"]).clip(lower=0)
    # PDF example: release Thursday for week ended previous Wednesday; next-session rule => +9 calendar days.
    x["date"] = x["source_date"] + pd.to_timedelta(9, unit="D")
    x["date"] = x["date"] + pd.offsets.BDay(0)
    return x[["source_date","date","fails_deliver","fails_receive","fails_total","settlement_raw"]], raw_d, raw_r

def load_spx():
    raw = get_bytes(STOOQ_URL)
    df = pd.read_csv(io.BytesIO(raw))
    date_col = pick_col(df.columns, "date")
    close_col = pick_col(df.columns, "close")
    x = df[[date_col, close_col]].copy()
    x.columns = ["source_date", "price"]
    x["source_date"] = pd.to_datetime(x["source_date"], errors="coerce")
    x["price"] = pd.to_numeric(x["price"], errors="coerce")
    x = x.dropna(subset=["source_date","price"]).sort_values("source_date")
    x["hh_60m"] = x["price"].rolling(1260, min_periods=1260).max()
    x["top_ratio"] = x["price"] / x["hh_60m"]
    x["top_prox90"] = ((x["top_ratio"] - 0.90) / 0.10).clip(0, 1)
    x["top_prox95"] = ((x["top_ratio"] - 0.95) / 0.05).clip(0, 1)
    x["date"] = x["source_date"] + pd.offsets.BDay(1)
    return x, raw

def strict_expanding_pct(s: pd.Series, min_obs: int) -> pd.Series:
    vals = s.to_numpy(dtype=float)
    out = np.full(len(vals), np.nan)
    hist = []
    for i, v in enumerate(vals):
        if np.isfinite(v):
            if len(hist) >= min_obs:
                a = np.asarray(hist, dtype=float)
                out[i] = 100.0 * float(np.sum(a < v)) / float(len(a))
            hist.append(v)
    return pd.Series(out, index=s.index)

def build_scores(fsi: pd.DataFrame, fails: pd.DataFrame, spx: pd.DataFrame):
    f = fsi.copy()
    f["funding_positive"] = f["funding"].clip(lower=0)
    f["safe_positive"] = f["safe_assets"].clip(lower=0)
    f["funding_pct"] = strict_expanding_pct(f["funding_positive"], 252)
    f["safe_pct"] = strict_expanding_pct(f["safe_positive"], 252)

    w = fails.copy()
    w["settlement_pct"] = strict_expanding_pct(w["settlement_raw"], 52)

    start = max(f["date"].min(), w["date"].min(), spx["date"].min())
    end = min(f["date"].max(), w["date"].max(), spx["date"].max())
    cal = pd.DataFrame({"date": pd.bdate_range(start, end)})

    # Daily OFR FSI values are used only on/after effective date; limited forward-fill.
    fd = cal.merge(f[["date","funding","safe_assets","funding_pct","safe_pct"]], on="date", how="left")
    for c in ["funding","safe_assets","funding_pct","safe_pct"]:
        fd[c] = fd[c].ffill(limit=3)

    # Weekly settlement stress held to next release. Limit ~10 calendar days => 7 business rows.
    fd = fd.merge(w[["date","fails_total","settlement_raw","settlement_pct"]], on="date", how="left")
    for c in ["fails_total","settlement_raw","settlement_pct"]:
        fd[c] = fd[c].ffill(limit=7)

    fd = fd.merge(spx[["date","price","top_ratio","top_prox90","top_prox95"]], on="date", how="left")
    for c in ["price","top_ratio","top_prox90","top_prox95"]:
        fd[c] = fd[c].ffill(limit=3)

    fd["confirmation_pct"] = fd[["settlement_pct","safe_pct"]].max(axis=1, skipna=False)
    fd["slf_raw"] = np.sqrt(fd["funding_pct"] * fd["confirmation_pct"])
    fd["slf90"] = fd["slf_raw"] * np.sqrt(fd["top_prox90"])
    fd["slf95"] = fd["slf_raw"] * np.sqrt(fd["top_prox95"])
    return fd

def future_drawdown(scores: pd.DataFrame, idx: int, horizon: int):
    px = scores["price"].to_numpy(dtype=float)
    if idx >= len(px) or not np.isfinite(px[idx]):
        return np.nan
    j = min(len(px), idx + horizon + 1)
    fut = px[idx:j]
    fut = fut[np.isfinite(fut)]
    if len(fut) < 2:
        return np.nan
    return 100.0 * (np.min(fut) / px[idx] - 1.0)

def episodes(scores: pd.DataFrame):
    rows=[]
    for variant in VARIANTS:
        a=scores[variant].to_numpy(dtype=float)
        for thr in THRESHOLDS:
            last=-10**9
            for i,v in enumerate(a):
                if np.isfinite(v) and v>=thr and i-last>EPISODE_LOCK:
                    d=scores.iloc[i]["date"]
                    rows.append({
                        "variant":variant,"threshold":thr,"episode_start":d,
                        "score":v,"price":scores.iloc[i]["price"],
                        "dd63_pct":future_drawdown(scores,i,63),
                        "dd126_pct":future_drawdown(scores,i,126),
                        "dd252_pct":future_drawdown(scores,i,252),
                        "era":"CURRENT_CENSORED" if d>=pd.Timestamp("2025-01-01") else "LEGACY"
                    })
                    last=i
    return pd.DataFrame(rows)

def window_scan(scores: pd.DataFrame):
    rows=[]
    for name,s,e,kind in EVENT_WINDOWS:
        x=scores[(scores.date>=pd.Timestamp(s))&(scores.date<=pd.Timestamp(e))]
        row={"window":name,"kind":kind,"start":s,"end":e,"n":len(x)}
        for v in VARIANTS:
            if x[v].notna().any():
                k=x[v].idxmax()
                row[f"{v}_max"]=float(x.loc[k,v])
                row[f"{v}_max_date"]=str(x.loc[k,"date"].date())
            else:
                row[f"{v}_max"]=np.nan
                row[f"{v}_max_date"]=""
            for t in THRESHOLDS:
                row[f"{v}_ge_{int(t)}"]=bool((x[v]>=t).any())
        rows.append(row)
    return pd.DataFrame(rows)

def threshold_grid(ep: pd.DataFrame):
    rows=[]
    for v in VARIANTS:
        for t in THRESHOLDS:
            x=ep[(ep.variant==v)&(ep.threshold==t)&(ep.era=="LEGACY")]
            rows.append({
                "variant":v,"threshold":t,
                "legacy_episode_count":len(x),
                "median_dd63_pct":x.dd63_pct.median() if len(x) else np.nan,
                "median_dd126_pct":x.dd126_pct.median() if len(x) else np.nan,
                "median_dd252_pct":x.dd252_pct.median() if len(x) else np.nan,
            })
    return pd.DataFrame(rows)

def main():
    fsi, raw_fsi, fsi_meta = load_fsi()
    fails, raw_d, raw_r = load_fails()
    spx, raw_spx = load_spx()

    scores=build_scores(fsi,fails,spx)
    ep=episodes(scores)
    windows=window_scan(scores)
    grid=threshold_grid(ep)

    scores.to_csv(OUT/"SLF_V0_SCORES.csv",index=False)
    ep.to_csv(OUT/"SLF_V0_EPISODES.csv",index=False)
    windows.to_csv(OUT/"SLF_V0_EVENT_WINDOWS.csv",index=False)
    grid.to_csv(OUT/"SLF_V0_THRESHOLD_GRID_126.csv",index=False)

    manifest={
        "generated_utc":pd.Timestamp.utcnow().isoformat(),
        "status":"RESEARCH_ONLY_LATEST_VINTAGE_RETRO",
        "formula_version":"SLF_V0_PREREG_2026-10-19",
        "sources":{
            "ofr_fsi":{"url":fsi_meta.get("source_url",FSI_URL),"sha256":sha256_bytes(raw_fsi),"meta":fsi_meta},
            "nypd_fails_deliver":{"mnemonic":"NYPD-PD_AFtD_TOT-A","sha256":sha256_bytes(raw_d)},
            "nypd_fails_receive":{"mnemonic":"NYPD-PD_AFtR_TOT-A","sha256":sha256_bytes(raw_r)},
            "stooq_spx":{"url":STOOQ_URL,"sha256":sha256_bytes(raw_spx),"role":"research-only top-location proxy"},
        },
        "coverage":{
            "fsi_source_start":str(fsi.source_date.min().date()),
            "fsi_source_end":str(fsi.source_date.max().date()),
            "fails_source_start":str(fails.source_date.min().date()),
            "fails_source_end":str(fails.source_date.max().date()),
            "spx_source_start":str(spx.source_date.min().date()),
            "spx_source_end":str(spx.source_date.max().date()),
            "score_start":str(scores.loc[scores.slf_raw.notna(),"date"].min().date()) if scores.slf_raw.notna().any() else None,
            "score_end":str(scores.loc[scores.slf_raw.notna(),"date"].max().date()) if scores.slf_raw.notna().any() else None,
        }
    }
    (OUT/"SLF_V0_SOURCE_MANIFEST.json").write_text(json.dumps(manifest,indent=2,default=str),encoding="utf-8")

    current=scores[scores.date>=pd.Timestamp("2025-01-01")]
    legacy=scores[scores.date<pd.Timestamp("2025-01-01")]
    lines=[
        "# MASTER TOP V3 — SLF V0 First Frozen-Formula Scan",
        "",
        "## 中文定位",
        "SLF = Systemic Liquidity / Fragility（系统性流动性与金融脆弱性路线）。",
        "这是 V3 第四核心主路线的首次冻结公式实现，不是正式交易信号。",
        "",
        "## Data QA",
        f"- Score coverage: {manifest['coverage']['score_start']} to {manifest['coverage']['score_end']}",
        f"- OFR FSI SHA256: {manifest['sources']['ofr_fsi']['sha256']}",
        f"- NYPD FTD SHA256: {manifest['sources']['nypd_fails_deliver']['sha256']}",
        f"- NYPD FTR SHA256: {manifest['sources']['nypd_fails_receive']['sha256']}",
        f"- Stooq ^SPX SHA256: {manifest['sources']['stooq_spx']['sha256']}",
        "",
        "## Governance",
        "- Threshold grid 70/80/90 is diagnostic only; no threshold is promoted from this retrospective scan.",
        "- 2025-2026 is current/censored and is not used to select formula, threshold or top gate.",
        "- OFR/NYPD historical values are latest-vintage retrospective inputs; this is not genuine historical PIT proof.",
        "",
        "## Threshold grid (legacy only)",
        "",
        grid.to_markdown(index=False),
        "",
        "## Pre-declared event/control windows",
        "",
        windows.to_markdown(index=False),
        "",
        "## Current-era read (censored; descriptive only)",
    ]
    if current[VARIANTS].notna().any().any():
        last=current.dropna(subset=["slf_raw"]).tail(1)
        if len(last):
            r=last.iloc[0]
            lines += [
                f"- Latest score date: {r.date.date()}",
                f"- SLF_RAW: {r.slf_raw:.2f}",
                f"- SLF90: {r.slf90:.2f}" if pd.notna(r.slf90) else "- SLF90: NA",
                f"- SLF95: {r.slf95:.2f}" if pd.notna(r.slf95) else "- SLF95: NA",
            ]
    else:
        lines += ["- No eligible current-era score."]
    (OUT/"SLF_V0_FINDINGS.md").write_text("\n".join(lines)+"\n",encoding="utf-8")

    qa={
        "fsi_rows":len(fsi),"fails_rows":len(fails),"spx_rows":len(spx),"score_rows":len(scores),
        "eligible_slf_raw":int(scores.slf_raw.notna().sum()),
        "eligible_slf90":int(scores.slf90.notna().sum()),
        "eligible_slf95":int(scores.slf95.notna().sum()),
        "legacy_episodes":int((ep.era=="LEGACY").sum()) if len(ep) else 0,
        "current_censored_episodes":int((ep.era=="CURRENT_CENSORED").sum()) if len(ep) else 0,
    }
    (OUT/"SLF_V0_DATA_QA.json").write_text(json.dumps(qa,indent=2),encoding="utf-8")
    print(json.dumps(qa,indent=2))
    print((OUT/"SLF_V0_FINDINGS.md").read_text(encoding="utf-8")[:12000])

if __name__=="__main__":
    main()
