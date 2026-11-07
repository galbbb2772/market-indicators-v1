"""Forward drawdown target study for three-factor weighted MASTER TOP research.

Target definition is intentionally explicit:
- from the SIGNAL-DAY S&P 500 close, not from a future local peak;
- first close <= signal_close*(1-drop);
- market-session waiting time;
- primary target: -5% within 60 sessions;
- secondary target: -10% within 126 sessions.

This module is research-only and does not mutate frozen V2.1.8.
"""
from __future__ import annotations
import argparse,json
from pathlib import Path
import numpy as np
import pandas as pd

LOCK=126

def first_passage_days(close:np.ndarray,drop:float,max_horizon:int=252)->np.ndarray:
    n=len(close);out=np.full(n,np.nan)
    for i in range(n):
        future=close[i+1:min(n,i+max_horizon+1)]
        hit=np.flatnonzero(future<=close[i]*(1-drop))
        if len(hit):out[i]=int(hit[0]+1)
    return out

def summarize(signal_positions,first_map,n_market,horizon):
    p=np.asarray(signal_positions,dtype=int)
    p=p[(p>=0)&(p+horizon<n_market)]
    out={"fully_observable":len(p)}
    for drop,arr in first_map.items():
        h=np.isfinite(arr[p])&(arr[p]<=horizon)
        pct=int(round(drop*100))
        vals=arr[p][h]
        out[f"hit_{pct}_pct"]=float(h.mean()*100) if len(p) else None
        out[f"median_days_to_{pct}"]=float(np.median(vals)) if len(vals) else None
        out[f"p25_days_to_{pct}"]=float(np.percentile(vals,25)) if len(vals) else None
        out[f"p75_days_to_{pct}"]=float(np.percentile(vals,75)) if len(vals) else None
    return out

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--daily",required=True,help="weighted daily CSV with date and score")
    ap.add_argument("--score-col",default="weighted_score")
    ap.add_argument("--gates",required=True,help="real ^GSPC daily gate series")
    ap.add_argument("--outdir",required=True)
    a=ap.parse_args()
    d=pd.read_csv(a.daily,parse_dates=["date"])
    g=pd.read_csv(a.gates,parse_dates=["date"]).sort_values("date")
    market=g.set_index("date").gspc_close.astype(float)
    pos={dt:i for i,dt in enumerate(market.index)}
    if d.date.duplicated().any():raise ValueError("duplicate signal dates")
    d["_pos"]=[pos.get(dt,-1) for dt in d.date]
    if (d._pos<0).any():raise ValueError("signal date not on S&P market calendar")
    first={x:first_passage_days(market.to_numpy(),x,252) for x in (.05,.10,.15)}
    rows=[]
    for threshold in (50,55,60,65,70):
        sig=d.loc[pd.to_numeric(d[a.score_col],errors="coerce")>=threshold,"_pos"].to_numpy()
        for horizon in (20,40,60,126,252):
            rows.append({"threshold":threshold,"horizon_sessions":horizon,
                         "signal_days":len(sig),
                         **summarize(sig,first,len(market),horizon)})
    results=pd.DataFrame(rows)
    out=Path(a.outdir);out.mkdir(parents=True,exist_ok=True)
    results.to_csv(out/"forward_drawdown_target_summary.csv",index=False)
    receipt={
      "status":"RESEARCH_FORWARD_DRAWDOWN_TARGET_ONLY",
      "primary_target":"S&P500 first close <= 95% of signal-day close within 60 market sessions",
      "secondary_target":"S&P500 first close <= 90% of signal-day close within 126 market sessions",
      "first_passage_reference":"signal-day close, NOT a future peak",
      "waiting_time_unit":"market sessions",
      "right_censoring":"probability denominators include only signals with full requested horizon",
      "frozen_v218_modified":False}
    (out/"receipt.json").write_text(json.dumps(receipt,indent=2)+"\n")
    print(results.to_string(index=False))

if __name__=="__main__":main()
