#!/usr/bin/env python3
# API schema probe trigger: legacy NY Fed fails coverage
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
ERC_HISTORY_URL = "https://economicriskclock.org/api/v1/data/metric_history"
ERC_FUNDING_ID = "us_ofr_funding_contribution"
ERC_SAFE_ID = "us_ofr_safe_assets_contribution"
NYPD_URL = "https://data.financialresearch.gov/v1/series/timeseries"
NYFED_PD_TREASURY_FAILS_URL = "https://markets.newyorkfed.org/api/pd/get/PDFTD-USTET_PDFTR-USTET.json"
YAHOO_SPY_URL = "https://query1.finance.yahoo.com/v8/finance/chart/SPY"

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

def _erc_items_to_rows(items, entity_id):
    rows = []
    for item in items:
        data = item.get("data", item)
        period = data.get("period")
        value = data.get("value")
        if period is not None:
            rows.append((period, value))
    return rows

def load_erc_metric(entity_id: str):
    # API limit is capped below the complete ~6.8k-point history, so use calendar-year
    # chunks fixed before scoring. Each year is below the 500-point API cap.
    rows = []
    raw_parts = []
    current_year = pd.Timestamp.now(tz="UTC").year
    for year in range(2000, current_year + 1):
        params = {
            "entity_id": entity_id,
            "limit": 500,
            "period_from": f"{year}-01-01",
            "period_to": f"{year}-12-31",
        }
        r = requests.get(
            ERC_HISTORY_URL,
            params=params,
            headers={"User-Agent": UA, "Accept": "application/json"},
            timeout=60,
        )
        r.raise_for_status()
        raw_parts.append((r.url + "\n").encode("utf-8") + r.content + b"\n")
        obj = r.json()
        sel = obj.get("history_selection", {})
        matching = int(sel.get("matching_points", 0) or 0)
        returned = int(sel.get("returned_points", len(obj.get("items", []))) or 0)
        if matching > 500 or returned < matching:
            raise RuntimeError(f"ERC yearly chunk incomplete for {entity_id} {year}: {sel}")
        rows.extend(_erc_items_to_rows(obj.get("items", []), entity_id))

    df = pd.DataFrame(rows, columns=["source_date", entity_id])
    df["source_date"] = pd.to_datetime(df["source_date"], errors="coerce")
    df[entity_id] = pd.to_numeric(df[entity_id], errors="coerce")
    df = df.dropna(subset=["source_date"]).drop_duplicates("source_date", keep="last").sort_values("source_date")
    if len(df) < 6000:
        raise RuntimeError(f"ERC history incomplete for {entity_id}: rows={len(df)}")
    return df, b"".join(raw_parts)

def load_fsi():
    source_url = FSI_URL
    source_role = "official_ofr_csv"
    try:
        raw = get_bytes(FSI_URL)
        df = pd.read_csv(io.BytesIO(raw))
        date_col = pick_col(df.columns, "date")
        funding_col = pick_col(df.columns, "fund")
        try:
            safe_col = pick_col(df.columns, "safe")
        except KeyError:
            safe_col = pick_col(df.columns, "flight")
        out = df[[date_col, funding_col, safe_col]].copy()
        out.columns = ["source_date", "funding", "safe_assets"]
        out["source_date"] = pd.to_datetime(out["source_date"], errors="coerce")
        out["funding"] = pd.to_numeric(out["funding"], errors="coerce")
        out["safe_assets"] = pd.to_numeric(out["safe_assets"], errors="coerce")
        meta = {"date_col": str(date_col), "funding_col": str(funding_col), "safe_col": str(safe_col),
                "columns": [str(c) for c in df.columns], "source_url": source_url, "source_role": source_role}
    except Exception as official_error:
        source_role = "economic_risk_clock_retained_ofr_history_retro_only"
        fund, raw_fund = load_erc_metric(ERC_FUNDING_ID)
        safe, raw_safe = load_erc_metric(ERC_SAFE_ID)
        out = fund.merge(safe, on="source_date", how="inner")
        out = out.rename(columns={ERC_FUNDING_ID:"funding", ERC_SAFE_ID:"safe_assets"})
        raw = raw_fund + b"\n---SAFE_ASSETS---\n" + raw_safe
        source_url = ERC_HISTORY_URL
        meta = {
            "date_col":"source_date","funding_col":ERC_FUNDING_ID,"safe_col":ERC_SAFE_ID,
            "columns":list(out.columns),"source_url":source_url,"source_role":source_role,
            "official_download_error":str(official_error),
            "note":"retrospective mirror only; official OFR publication lag rules applied separately"
        }
    out = out.dropna(subset=["source_date"]).sort_values("source_date")
    # Conservative rule frozen in data contract: observation t -> effective t+3 US business-day proxy.
    out["date"] = out["source_date"] + pd.offsets.BDay(3)
    return out, raw, meta

def load_nypd_series(mnemonic: str):
    raw = get_bytes(NYPD_URL, {"mnemonic": mnemonic})
    arr = json.loads(raw.decode("utf-8"))
    df = pd.DataFrame(arr, columns=["source_date", mnemonic])
    df["source_date"] = pd.to_datetime(df["source_date"], errors="coerce")
    df[mnemonic] = pd.to_numeric(df[mnemonic], errors="coerce")
    return df.dropna(subset=["source_date"]).sort_values("source_date"), raw

def load_fails():
    """Official NY Fed long-history Treasury settlement fails, ex-TIPS.

    Frozen pre-full-rerun choice under the preregistered priority to use
    Treasury-specific fails when a consistent long-history series is available.
    """
    r = requests.get(
        NYFED_PD_TREASURY_FAILS_URL,
        headers={"User-Agent":"Mozilla/5.0 MarketRegimeLab/SLF-V0","Accept":"application/json"},
        timeout=60,
    )
    r.raise_for_status()
    raw = r.content
    obj = r.json()
    rows = ((obj.get("pd") or {}).get("timeseries") or [])
    if not rows:
        raise RuntimeError("Official NY Fed Primary Dealer fails endpoint returned no timeseries rows")

    parsed = []
    for item in rows:
        key = str(item.get("keyid") or "").strip()
        if key not in {"PDFTD-USTET","PDFTR-USTET"}:
            continue
        dt = pd.to_datetime(item.get("asofdate") or item.get("asOfDate"), errors="coerce")
        val = pd.to_numeric(item.get("value"), errors="coerce")
        if pd.notna(dt) and pd.notna(val):
            parsed.append((dt, key, float(val)))
    if not parsed:
        raise RuntimeError("Official NY Fed response contained no numeric Treasury fails rows")

    z = pd.DataFrame(parsed, columns=["source_date","keyid","value"])
    wide = z.pivot_table(index="source_date", columns="keyid", values="value", aggfunc="last").reset_index()
    if "PDFTD-USTET" not in wide or "PDFTR-USTET" not in wide:
        raise RuntimeError(f"Missing one Treasury fails leg; columns={list(wide.columns)}")
    x = wide.rename(columns={
        "PDFTD-USTET":"fails_deliver",
        "PDFTR-USTET":"fails_receive",
    }).sort_values("source_date")
    x["fails_total"] = x["fails_deliver"] + x["fails_receive"]
    x["log_fails"] = np.log1p(x["fails_total"].clip(lower=0))
    x["med52"] = x["log_fails"].rolling(52, min_periods=52).median()
    x["settlement_raw"] = (x["log_fails"] - x["med52"]).clip(lower=0)

    # NY Fed releases prior-week Primary Dealer statistics Thursday ~4:15 p.m.;
    # next-session actionability => week-ending Wednesday + 9 calendar days (Friday).
    x["date"] = x["source_date"] + pd.to_timedelta(9, unit="D")
    x["date"] = x["date"] + pd.offsets.BDay(0)

    first = x["source_date"].min()
    if pd.isna(first) or first > pd.Timestamp("2000-01-31"):
        raise RuntimeError(f"Treasury fails legacy coverage insufficient; first source date={first}")

    return x[["source_date","date","fails_deliver","fails_receive","fails_total","settlement_raw"]], raw, raw

def load_spx():
    params = {
        "period1": 946684800,  # 2000-01-01 UTC
        "period2": int(pd.Timestamp.now(tz="UTC").timestamp()),
        "interval": "1d",
        "events": "history",
        "includeAdjustedClose": "true",
    }
    raw = None
    last_error = None
    for url in (YAHOO_SPY_URL, YAHOO_SPY_URL.replace("query1.", "query2.")):
        try:
            r = requests.get(url, params=params, headers={"User-Agent":"Mozilla/5.0 MarketRegimeLab/SLF-V0"}, timeout=60)
            r.raise_for_status()
            raw = r.content
            obj = r.json()
            res = (obj.get("chart") or {}).get("result")
            if not res:
                raise RuntimeError(str((obj.get("chart") or {}).get("error")))
            item = res[0]
            ts = item.get("timestamp") or []
            quote = ((item.get("indicators") or {}).get("quote") or [{}])[0]
            adj = ((item.get("indicators") or {}).get("adjclose") or [{}])[0].get("adjclose")
            close = adj if adj and len(adj) == len(ts) else quote.get("close")
            if not ts or not close:
                raise RuntimeError("Yahoo SPY history empty")
            x = pd.DataFrame({
                "source_date": pd.to_datetime(ts, unit="s", utc=True).tz_convert(None).normalize(),
                "price": pd.to_numeric(close, errors="coerce"),
            }).dropna().sort_values("source_date")
            x["hh_60m"] = x["price"].rolling(1260, min_periods=1260).max()
            x["top_ratio"] = x["price"] / x["hh_60m"]
            x["top_prox90"] = ((x["top_ratio"] - 0.90) / 0.10).clip(0, 1)
            x["top_prox95"] = ((x["top_ratio"] - 0.95) / 0.05).clip(0, 1)
            x["date"] = x["source_date"] + pd.offsets.BDay(1)
            return x, raw
        except Exception as exc:
            last_error = exc
    raise RuntimeError(f"Yahoo SPY history failed: {last_error}")

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

def probe_nyfed_pd_schema():
    """Temporary research probe for official NY Fed Primary Dealer API paths/catalog.
    This does not alter SLF inputs, formula, thresholds, or scores.
    """
    try:
        base = "https://markets.newyorkfed.org/api/pd"
        h = {"User-Agent":"Mozilla/5.0 MarketRegimeLab/SLF-V0","Accept":"application/json"}
        br = requests.get(base + "/list/seriesbreaks.json", headers=h, timeout=30)
        br.raise_for_status()
        print("NYFED_SERIESBREAKS", json.dumps((br.json().get("pd") or {}).get("seriesbreaks") or [], indent=2))

        tr = requests.get(base + "/list/timeseries.json", headers=h, timeout=30)
        tr.raise_for_status()
        rows = (tr.json().get("pd") or {}).get("timeseries") or []
        candidates = []
        for row in rows:
            textv = " ".join(str(row.get(k) or "") for k in ("keyid","description","seriesbreak")).lower()
            if "fail" in textv and ("treasury" in textv or "u.s. government" in textv or "government securities" in textv):
                candidates.append(row)
        print("NYFED_TREASURY_FAIL_CANDIDATES", json.dumps(candidates, indent=2))
        raise SystemExit("PD catalog probe complete")
    except SystemExit:
        raise
    except Exception as exc:
        print(f"NYFED_PD_SCHEMA_PROBE_ERROR: {exc!r}")
        raise


def main():
    probe_nyfed_pd_schema()
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
            "nyfed_treasury_fails_deliver":{"keyid":"PDFTD-USTET","sha256":sha256_bytes(raw_d),"source":NYFED_PD_TREASURY_FAILS_URL},
            "nyfed_treasury_fails_receive":{"keyid":"PDFTR-USTET","sha256":sha256_bytes(raw_r),"source":NYFED_PD_TREASURY_FAILS_URL},
            "yahoo_spy":{"url":YAHOO_SPY_URL,"sha256":sha256_bytes(raw_spx),"role":"research-only broad-market top-location proxy"},
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
        f"- NY Fed Treasury FTD SHA256: {manifest['sources']['nyfed_treasury_fails_deliver']['sha256']}",
        f"- NY Fed Treasury FTR SHA256: {manifest['sources']['nyfed_treasury_fails_receive']['sha256']}",
        f"- Yahoo SPY SHA256: {manifest['sources']['yahoo_spy']['sha256']}",
        "",
        "## Governance",
        "- Threshold grid 70/80/90 is diagnostic only; no threshold is promoted from this retrospective scan.",
        "- 2025-2026 is current/censored and is not used to select formula, threshold or top gate.",
        "- OFR and NY Fed historical values are latest-vintage retrospective inputs; this is not genuine historical PIT proof.",
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
