"""Real 2000-2018 Quandl WIKI Kaggle public mirror V2.1.8 PROXY replay.

The Kaggle mirror includes many more tickers than the academic FINSABER
S&P500 universe. It is nevertheless a curated ~3,199-ticker US sample, NOT
full historic point-in-time all-US common stocks; retired symbols may be
present, not necessarily ALL delisted securities.

Use official Kagglehub public download without bypassing authorization,
process ~1.8 GB CSV out-of-core with DuckDB+Arrow, keep downloaded prices
outside git and only export research-level DAILY summaries, with input hash.
Historical adjusted closes include dividends (frozen source split-only).
Do not splice this proxy into user's user-validated 2019-2026 source.
"""
from __future__ import annotations

import argparse,hashlib,json,math
from collections import defaultdict,deque
from datetime import datetime,timezone
from pathlib import Path
import numpy as np
import pandas as pd

from master_top_v218 import hl_persistence_score
from research.master_top_v218_historical_gates import fetch_gspc,fetch_dgs2,audit
from research.v218_2000_2018_finsaber_public_backtest import combine

DATASET="marketneutral/quandl-wiki-prices-us-equites"
STATUS="REAL_WIKI_2000_2018_BROADER_US_SAMPLE_PROXY_NOT_ALL_US_PIT_V218"
START="2000-01-03"
END="2018-03-27"
WARMUP_START="1997-01-01"
HISTORY=252


class StockRolling:
    """One symbol, chronological, exact prior-252-V-A-L-I-D-close H/L check."""
    def __init__(self):
        self.n=0
        self.hi=deque()
        self.lo=deque()

    def update(self,p:float)->tuple[bool,bool,bool]:
        if not math.isfinite(p) or p<=0:raise ValueError("nonpositive input to rolling H/L")
        i=self.n
        while self.hi and self.hi[0][0]<i-HISTORY:self.hi.popleft()
        while self.lo and self.lo[0][0]<i-HISTORY:self.lo.popleft()
        mature=i>=HISTORY
        newhigh=bool(mature and p>=self.hi[0][1])
        newlow=bool(mature and p<=self.lo[0][1])
        while self.hi and self.hi[-1][1]<=p:self.hi.pop()
        while self.lo and self.lo[-1][1]>=p:self.lo.pop()
        self.hi.append((i,p))
        self.lo.append((i,p))
        self.n+=1
        return mature,newhigh,newlow


def hash_file(p:Path)->str:
    sha=hashlib.sha256()
    with p.open("rb") as f:
        for part in iter(lambda:f.read(8<<20),b""):
            sha.update(part)
    return sha.hexdigest()


def stream_wiki_counts(csvpath:Path, memory_limit:str="3GB")->tuple[pd.DataFrame,dict]:
    import duckdb
    if not csvpath.is_file():raise FileNotFoundError(csvpath)
    conn=duckdb.connect(database=":memory:")
    conn.execute("SET memory_limit='"+memory_limit+"'")
    conn.execute("SET temp_directory='/tmp/v218_wiki_duckdb_temp'")
    safe_path=str(csvpath).replace("'","''")
    # read_csv_auto understands WIKI's 14-column format. Scope dates first,
    # then order by ticker/date. Use 50k-row fetchmany batches to cap Python RAM usage.
    sql=(f"SELECT trim(ticker) AS ticker, date, "
         f"TRY_CAST(adj_close AS DOUBLE) AS adj_close "
         f"FROM read_csv_auto('{safe_path}', header=true, all_varchar=true) "
         f"WHERE date BETWEEN '{WARMUP_START}' AND '{END}' "
         f"ORDER BY ticker, date")
    cursor=conn.execute(sql)
    counters=defaultdict(lambda:[0,0,0,0])
    valid=0;invalid=0;symbols=0;older_rows=0
    previous_symbol=None;prev_date=""
    state=None
    while True:
        rows=cursor.fetchmany(50000)
        if not rows:break
        for ticker,date_str,p in rows:
            if not ticker or not date_str:invalid+=1;continue
            if ticker!=previous_symbol:
                if previous_symbol is not None and ticker<=previous_symbol:
                    raise ValueError("Input source order is not monotonic by ticker")
                previous_symbol=ticker;prev_date=""
                state=StockRolling()
                symbols+=1
            if date_str<=prev_date:
                raise ValueError(f"duplicated or disordered ticker/day: {ticker}/{date_str}")
            prev_date=date_str
            if p is None or not math.isfinite(p) or p<=0:
                invalid+=1
                continue
            mature,hi,lo=state.update(float(p))
            valid+=1
            if date_str < START:
                older_rows+=1
                continue
            x=counters[date_str]
            x[0]+=1;x[1]+=int(mature);x[2]+=int(hi);x[3]+=int(lo)
    conn.close()
    if not counters:raise ValueError("WIKI stock archive has no 2000-2018 data")
    daily=pd.DataFrame([{"date":pd.Timestamp(day),"issues":vals[0],
         "mature":vals[1],"nh":vals[2],"nl":vals[3]}
        for day,vals in sorted(counters.items())])
    den=daily.nh+daily.nl
    daily["hl_balance"]=np.where(den>0,(daily.nh-daily.nl)/den,np.nan)
    z=daily.hl_balance.to_numpy(dtype=float)
    daily["hl_persistence"]=[hl_persistence_score(z[max(0,i-19):i+1])
                                 for i in range(len(z))]
    profile={"selected_input_valid_bars_including_1997_1999_warmup":valid,
             "selected_invalid_or_missing_rows":invalid,
             "warmup_valid_bars_before_2000":older_rows,
             "all_sample_ticker_strings_from_1997":symbols,
             "scored_market_sessions":len(daily),
             "year_start":daily.date.iloc[0].strftime("%Y-%m-%d"),
             "year_end":daily.date.iloc[-1].strftime("%Y-%m-%d"),
             "price_column":"adj_close (split-and-dividend adjusted, NOT identical to original 2019+ source)",
             "source":"Kaggle mirror of Quandl WIKI/PRICES, frozen Mar 27, 2018"}
    if daily.date.iloc[0]>pd.Timestamp("2000-01-04"):
        raise ValueError("Real 2000 inception coverage missing")
    if daily.date.iloc[-1]<pd.Timestamp("2018-03-26") or len(daily)<4500 or symbols<2500:
        raise ValueError("WIKI 2000–Mar2018 candidate incomplete or too narrow")
    return daily,profile


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--outdir",default="research/out/v218_wiki_2000_2018_real_replay")
    args=ap.parse_args()
    import kagglehub
    try:
        root=Path(kagglehub.dataset_download(DATASET))
    except Exception as exc:
        raise RuntimeError("WIKI_KAGGLE_PUBLIC_SOURCE_NOT_AVAILABLE "+type(exc).__name__) from None
    filenames=list(root.rglob("WIKI_PRICES.csv"))
    if len(filenames)!=1:raise ValueError(f"Expected one WIKI_PRICES.csv, got {len(filenames)}")
    file=filenames[0]
    profile_sha=hash_file(file)
    dates,profile=stream_wiki_counts(file)
    gates,macros=audit(fetch_gspc(),fetch_dgs2())
    result,events=combine(dates,gates,min_required_gspc_sessions=4500)
    years=[]
    for year,g in result.groupby(result.date.dt.year):
        years.append({"year":int(year),"trading_days":len(g),
                      "scored_days":int(g.proxy_route.notna().sum()),
                      "sample_mean_tickers":round(float(g.issues.mean()),1),
                      "max_route":round(float(g.proxy_route.max()),4) if g.proxy_route.notna().any() else None,
                      "trigger_days":int(g.proxy_alert_day.sum())})
    receipt={"schema":"v218-wiki-historical-public-broader-sample-v1",
       "run_at_utc":datetime.now(timezone.utc).isoformat(),
       "classification":STATUS,"requested_window":[START,END],
       "source_file":"WIKI_PRICES.csv","source_sha256":profile_sha,
       "source_bytes":file.stat().st_size,
       "input_profile":profile,
       "freeze_threshold":55.0,"freeze_episode_sessions":126,
       "valid_route_score_days":int(result.proxy_route.notna().sum()),
       "alert_days":int(result.proxy_alert_day.sum()),"events":events,
       "years":years,"macro_gspc_source":macros["source_gspc"],
       "macro_2y_source":macros["source_dgs2"],
       "all_US_stock_universe_PIT_proven":False,
       "fully_delisted_equity_membership_proven":False,
       "company_permanent_ID_verified":False,
       "user_approved_2019_2026_data_modified":False,
       "full_2000_2026_certified":False,
       "notes":["WIKI prices end March 27 2018; Apr–Dec 2018 requires separate source.",
                "WIKI includes a historical selection of 3199 tickers rather than all US stock listings.",
                "Dividends and splits are back-adjusted; original V2.1.8 price source may differ.",
                "Use only as independent 2000–Mar2018 research proxy, not official model."]
       }
    out=Path(args.outdir);out.mkdir(parents=True,exist_ok=True)
    result.to_csv(out/"v218_wiki_2000_2018_daily_proxy.csv",index=False)
    (out/"source_receipt.json").write_text(json.dumps(receipt,indent=2,ensure_ascii=False)+"\n")
    (out/"candidate_episodes.json").write_text(json.dumps(events,indent=2)+"\n")
    print(json.dumps({"classification":STATUS,"dates":len(result),
          "route_days":receipt["valid_route_score_days"],"alerts":receipt["alert_days"],
          "events":events,"profile":profile},ensure_ascii=False))


if __name__=="__main__":
    main()
