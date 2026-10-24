"""Actually fetch the publicly available 2000-2018 FINSABER S&P500-style universe.

This is a historical SUBSET PROXY with delisted-symbol histories, NOT the
user's frozen ORIGINAL ALL-US breadth universe. Public research sample is
licensed under Apache-2.0, no paid API/account required. This script never
writes or alters the user's 2019-2026 original approved data.

Reuses real ^GSPC and U.S. 2Y Treasury observations and original V2.1.8
mathematics from PR #21's gate audit. Source start Jan 2000: first 252
per-security bar sessions are NOT warm; do not score dot-com 2000 as full.
"""
from __future__ import annotations
import argparse,hashlib,json,os,time
from datetime import datetime,timezone
from pathlib import Path
import numpy as np
import pandas as pd
import requests

from master_top_v218 import hl_persistence_score,route_score,EPISODE_LOCK_SESSIONS
from research.master_top_v218_historical_gates import fetch_gspc,fetch_dgs2,audit

DATA_URL="https://huggingface.co/datasets/finsaber-team/FINSABER-reproduce/resolve/main/data/price/all_sp500_prices_2000_2024_delisted_include.csv"
REPORT_CLASS="REAL_PUBLIC_S_AND_P_500_UNIVERSE_PROXY_NOT_ALL_US_PIT_V218"
START="2000-01-03"
END="2018-12-31"
COLS=["date","symbol","close","adjusted_close"]

def get_public_file(dst:Path,session:requests.Session|None=None)->dict:
    """Download to a local scratch directory. No raw data redistribution."""
    dst.parent.mkdir(parents=True,exist_ok=True)
    if not dst.exists() or dst.stat().st_size<1_000_000:
        s=session or requests.Session()
        for attempt in range(3):
            try:
                with s.get(DATA_URL,timeout=(30,180),stream=True,
                           headers={"User-Agent":"V218AcademicPublicSourceAudit/1.0"}) as resp:
                    if resp.status_code in (401,403,429):
                        raise RuntimeError(f"PUBLIC_SOURCE_NOT_AVAILABLE_HTTP_{resp.status_code}")
                    resp.raise_for_status()
                    tmp=dst.with_suffix(".downloading")
                    with tmp.open("wb") as f:
                        for data in resp.iter_content(chunk_size=1<<20):
                            if data:f.write(data)
                    if tmp.stat().st_size<1_000_000:
                        raise RuntimeError("Hugging Face source unexpectedly small")
                    tmp.replace(dst)
                    break
            except requests.RequestException as exc:
                if attempt>=2:raise RuntimeError("PUBLIC_SOURCE_NETWORK_UNAVAILABLE "+str(exc)[:180]) from None
                time.sleep(2**attempt)
    digest=hashlib.sha256()
    with dst.open("rb") as f:
        for block in iter(lambda:f.read(4<<20),b""):digest.update(block)
    return {"sha256":digest.hexdigest(),"bytes":dst.stat().st_size,"source":DATA_URL}

def parse_subset(path:Path,start:str=START,end:str=END)->tuple[pd.DataFrame,dict]:
    records=[];raw_rows=0;bad_values=0
    for batch in pd.read_csv(path,dtype={"date":str,"symbol":str},
                             chunksize=150_000,low_memory=False):
        missing=set(COLS)-set(batch.columns)
        if missing:raise ValueError("Academic dataset missing required columns "+repr(missing))
        raw_rows+=len(batch)
        sub=batch.loc[batch.date.between(start,end),COLS]
        if sub.empty:continue
        sub=sub.copy()
        sub["symbol"]=sub.symbol.astype(str).str.strip().str.upper()
        sub["price"]=pd.to_numeric(sub["adjusted_close"],errors="coerce")
        invalid=(sub.symbol.eq("") | sub.symbol.eq("NAN") |
                 sub.price.isna() | ~np.isfinite(sub.price) | sub.price.le(0))
        bad_values+=int(invalid.sum())
        records.append(sub.loc[~invalid,["date","symbol","price"]])
    if not records:raise ValueError("No usable 2000-2018 public stock subset observations")
    df=pd.concat(records,ignore_index=True)
    df["date"]=pd.to_datetime(df.date,errors="raise")
    duplicates=int(df.duplicated(["symbol","date"]).sum())
    if duplicates:
        raise ValueError(f"Duplicated date/ticker identities must be resolved explicitly: {duplicates}")
    df.sort_values(["symbol","date"],inplace=True)
    df.reset_index(drop=True,inplace=True)
    if df.date.min()>pd.Timestamp("2000-01-04") or df.date.max()<pd.Timestamp("2018-12-28"):
        raise ValueError("Date coverage does not cover requested 2000–2018 window")
    if df.symbol.nunique()<200 or df.date.nunique()<4500:
        raise ValueError("Subset unusually small; not enough market-session price data")
    summary={"raw_original_full_csv_rows":raw_rows,
             "selected_valid_rows":len(df),"invalid_selected_rows":bad_values,
             "selected_distinct_ticker_strings":int(df.symbol.nunique()),
             "selected_trading_sessions":int(df.date.nunique()),
             "date_first":df.date.min().date().isoformat(),
             "date_last":df.date.max().date().isoformat(),
             "data_vendor_scope":"FINSABER S&P500 cohort, includes some delisted, NOT all US equities",
             "source_identity":"ticker only; daily PIT permanent share-class membership unverified",
             "price_column":"adjusted_close (dividend+split adjustment, differs from MarketParquet split-only)"}
    return df,summary

def raw_breadth(df:pd.DataFrame)->pd.DataFrame:
    b=df.copy()
    b=b.sort_values(["symbol","date"]).reset_index(drop=True)
    prior=b.groupby("symbol",sort=False)["price"].shift(1)
    hi=prior.groupby(b.symbol,sort=False).rolling(252,min_periods=252).max().reset_index(level=0,drop=True)
    lo=prior.groupby(b.symbol,sort=False).rolling(252,min_periods=252).min().reset_index(level=0,drop=True)
    eligible=hi.notna() & lo.notna()
    b["mature"]=eligible
    b["nh"]=eligible & (b.price>=hi)
    b["nl"]=eligible & (b.price<=lo)
    daily=b.groupby("date",sort=True).agg(issues=("symbol","size"),mature=("mature","sum"),
                  nh=("nh","sum"),nl=("nl","sum"))
    denominator=daily.nh+daily.nl
    daily["hl_balance"]=np.where(denominator>0,(daily.nh-daily.nl)/denominator,np.nan)
    values=daily.hl_balance.to_numpy(dtype=float)
    daily["hl_persistence"]=[hl_persistence_score(values[max(0,i-19):i+1]) for i in range(len(values))]
    return daily.reset_index()

def combine(daily:pd.DataFrame,gates:pd.DataFrame)->tuple[pd.DataFrame,list[dict]]:
    x=gates.copy()
    x["date"]=pd.to_datetime(x.date)
    m=daily.merge(x[["date","gspc_close","policy","top_ratio","route_upper_bound_if_hl100"]],
                  on="date",how="left",validate="one_to_one")
    if m.gspc_close.notna().sum()<4000:raise ValueError("Incomplete public ^GSPC macro gate series")
    def score(row):
        if pd.isna(row.hl_persistence) or pd.isna(row.policy) or pd.isna(row.top_ratio):
            return float("nan")
        return float(route_score(row.policy,row.hl_persistence,row.top_ratio))
    m["proxy_route"]=m.apply(score,axis=1)
    m["proxy_alert_day"]=m.proxy_route>=55.0
    episodes=[];last_start=None
    market_days=pd.DatetimeIndex(x.loc[x.gspc_close.notna(),"date"].sort_values().unique())
    for r in m.loc[m.proxy_alert_day].itertuples(index=False):
        if last_start is not None:
            distance=int(((market_days>last_start)&(market_days<=r.date)).sum())
            if distance<EPISODE_LOCK_SESSIONS:continue
        episodes.append({
            "date":r.date.date().isoformat(),"route":round(float(r.proxy_route),6),
            "policy":round(float(r.policy),6),
            "hl_persistence":round(float(r.hl_persistence),6),
            "universe_type":"FINSABER_S_AND_P_500_SUBSET_PROXY",
            "market_2000_2018_warning":"Not the same all-US stock breadth as user's frozen market model"
        })
        last_start=r.date
    return m,episodes

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--scratch",type=Path,default=Path("/tmp/v218_finsaber_2000_2018"))
    p.add_argument("--outdir",type=Path,default=Path("research/out/v218_2000_2018_public_sp500"))
    args=p.parse_args()
    file=args.scratch/"finsaber_sp500_delisted_2000_2024.csv"
    source=get_public_file(file)
    stock,profile=parse_subset(file)
    breadth=raw_breadth(stock)
    macro,macro_receipt=audit(fetch_gspc(),fetch_dgs2())
    scored,episodes=combine(breadth,macro)
    if scored.date.isna().any() or scored.date.duplicated().any():
        raise ValueError("Missing/duplicate market session dates in historical scoring")
    window=scored.loc[scored.date.between("2000-01-01","2018-12-31")]
    by_year=[]
    for y,g in window.groupby(window.date.dt.year):
        by_year.append({"year":int(y),"days":len(g),
                        "mature_days":int(g.hl_persistence.notna().sum()),
                        "alert_days":int(g.proxy_alert_day.sum()),
                        "max_score":round(float(g.proxy_route.max()),5) if g.proxy_route.notna().any() else None,
                        "avg_symbols":round(float(g.issues.mean()),1)})
    receipt={"schema":"v218-hf-finsaber-historical-crosssection-proxy-v1",
             "run_at_utc":datetime.now(timezone.utc).isoformat(),
             "status":REPORT_CLASS,"actual_public_stock_source":source,
             "profile":profile,"macro_price_source":macro_receipt["source_gspc"],
             "macro_rate_source":macro_receipt["source_dgs2"],
             "market_gate_sha256":macro_receipt["source_price_sha256"],
             "trading_dates_in_source":int(len(window)),
             "valid_full_source_score_days":int(window.proxy_route.notna().sum()),
             "alert_days":int(window.proxy_alert_day.sum()),
             "candidate_episodes":episodes,"by_year":by_year,
             "original_all_US_V218_backtest_validated":False,
             "first_year_warmup_not_available":True,
             "dividend_adjusted_close_can_differ_from_frozen_split_adjusted_close":True,
             "PIT_full_common_stock_universe_proven":False,
             "raw_licensed_prices_committed_to_public_git":False,
             "next_steps":["Find true historical all-US including delisted bars and stable security IDs.",
                           "Compare this S&P500 subset's available bearish periods to frozen macro upper gate.",
                           "Do not splice S&P500-only proxy into the existing 2019+ all-US baseline."]}
    args.outdir.mkdir(parents=True,exist_ok=True)
    (args.outdir/"source_receipt.json").write_text(json.dumps(receipt,indent=2,ensure_ascii=False)+"\n")
    window.to_csv(args.outdir/"daily_2000_2018_scored_SP500_PROXY.csv",index=False)
    (args.outdir/"episodes.json").write_text(json.dumps(episodes,indent=2,ensure_ascii=False)+"\n")
    print(json.dumps({k:receipt[k] for k in ("status","trading_dates_in_source","alert_days","candidate_episodes")},ensure_ascii=False))

if __name__=="__main__":
    main()
