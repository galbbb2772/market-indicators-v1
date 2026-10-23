"""Re-evaluate V2.1.8 math on user's archived aggregate US breadth (research only).

This is NOT a certified historical V2.1.8 backtest: the 2019–2026
aggregated breadth CSV does not certify dated common-stock-only universe
or delisted stock membership. A genuine 2017 control or current
2026-10 prospective score cannot be derived from it.

Inputs:
  --breadth reconstructed_allus_breadth_2019_2026-03.csv
  --gates all_days.csv   # PR #21's Yahoo ^GSPC + 2Y Treasury real-data artifact
No inputs are downloaded and no canonical production outputs are modified.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from master_top_v218 import hl_persistence_score, route_score

STATUS = "EXPLORATORY_ARCHIVED_UNIVERSE_NONPIT_NOT_FROZEN_PRODUCTION_REPLAY"
THRESHOLD = 55.0
LOCK_SESSIONS = 126


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def archived_hl(source: pd.DataFrame) -> pd.DataFrame:
    needed = {"date", "issues", "nh", "nl", "hl_balance", "hl_persist_score"}
    if not needed.issubset(source.columns):
        raise ValueError("Missing archived breadth observations")
    b=source.copy()
    b["date"]=pd.to_datetime(b.date,errors="raise").dt.normalize()
    b=b.sort_values("date").reset_index(drop=True)
    if b.date.duplicated().any():
        raise ValueError("Duplicate breadth session date")
    if (b[["issues","nh","nl"]].isna().any().any() or (b[["issues","nh","nl"]]<0).any().any()):
        raise ValueError("Invalid archived breadth counts")
    if ((b.nh+b.nl)>2*b.issues).any():
        raise ValueError("High/low counts exceed conceivable securities")
    den=b.nh+b.nl
    b["hl_from_counts"]=np.where(den>0,(b.nh-b.nl)/den,np.nan)
    mask=b.hl_from_counts.notna() & b.hl_balance.notna()
    if mask.any() and abs(b.loc[mask,"hl_from_counts"]-b.loc[mask,"hl_balance"]).max()>1e-8:
        raise ValueError("Archived H/L balance is not reproducible from counts")
    b["frozen_hl"] = [
        hl_persistence_score(b.hl_from_counts.iloc[max(0,i-19):i+1].to_numpy())
        for i in range(len(b))
    ]
    both=b.frozen_hl.notna() & b.hl_persist_score.notna()
    if both.sum()<250 or abs(b.loc[both,"frozen_hl"]-b.loc[both,"hl_persist_score"]).max()>1e-8:
        raise ValueError("Archived persistence inconsistent with frozen formula")
    return b


def replay(breadth:pd.DataFrame, gates:pd.DataFrame)->tuple[pd.DataFrame,list[dict]]:
    b=archived_hl(breadth)
    g=gates.copy()
    cols={"date","policy","top_ratio","route_upper_bound_if_hl100","gspc_close"}
    if not cols.issubset(g.columns):
        raise ValueError("Missing real policy or ^GSPC price fields")
    g["date"]=pd.to_datetime(g.date,errors="raise").dt.normalize()
    if g.date.duplicated().any():
        raise ValueError("Duplicate real market session")
    frame=g.merge(b[["date","issues","nh","nl","hl_balance","frozen_hl"]],
                  on="date",how="inner",validate="one_to_one").sort_values("date")
    if frame.empty or len(frame)<1000:
        raise ValueError("Not enough full-span matching market days")
    frame["proxy_route"]=[
        route_score(float(p),float(h),float(t)) if np.isfinite(h) else np.nan
        for p,h,t in zip(frame.policy,frame.frozen_hl,frame.top_ratio)
    ]
    good=frame.proxy_route.notna()
    if ((frame.loc[good,"proxy_route"]-frame.loc[good,"route_upper_bound_if_hl100"])>1e-4).any():
        raise ValueError("Proxy score exceeds frozen upper bound; source mismatch")
    frame["proxy_trigger"]=frame.proxy_route>=THRESHOLD
    # Lock is measured on market session calendar, not only on scored dates.
    market=g.set_index("date")["gspc_close"].sort_index()
    episodes=[]
    last_start=None
    for row in frame.loc[good & frame.proxy_trigger].itertuples(index=False):
        start=pd.Timestamp(row.date)
        if last_start is not None:
            sessions=(market.index>last_start)&(market.index<=start)
            if int(sessions.sum()) < LOCK_SESSIONS:
                continue
        episodes.append({
            "start_date":start.date().isoformat(),
            "proxy_route":round(float(row.proxy_route),5),
            "frozen_hl_from_archive":round(float(row.frozen_hl),5),
            "issues":int(row.issues),
            "status":"UNVERIFIED_ARCHIVE_UNIVERSE_PROXY",
        })
        last_start=start
    for e in episodes:
        start=pd.Timestamp(e["start_date"])
        end=start+pd.DateOffset(months=12)
        window=market.loc[(market.index>=start)&(market.index<=end)]
        if len(window)<2 or window.index[0]!=start:
            raise ValueError("Missing exact index close at episode start")
        dd=(window/window.cummax()-1)*100
        complete=bool(end<=market.index[-1])
        e.update({
            "outcome_matured_12m":complete,
            "outcome_mdd_12m_pct":round(float(dd.min()),4) if complete else None,
            "censored_mdd_to_date_pct":round(float(dd.min()),4) if not complete else None,
            "outcome_bucket":("CENSORED" if not complete else
                "MAJOR_BEAR" if dd.min()<=-20 else
                "SEVERE_NEAR_MISS" if dd.min()<=-15 else
                "CORRECTION" if dd.min()<=-10 else "FALSE_POSITIVE"),
        })
    return frame,episodes


def anomaly_summary(b:pd.DataFrame)->dict:
    d=b.copy().sort_values("date")
    pct=d.issues.pct_change(fill_method=None).replace([np.inf,-np.inf],np.nan)
    anomalies=d.loc[(d.date>=pd.Timestamp("2020-01-01")) & (pct.abs()>0.20)]
    return {
        "count_large_daily_universe_shifts":len(anomalies),
        "definition":"Absolute day-on-day archived issues change >20%; does NOT prove delisting",
        "notable":[{"date":x.date.date().isoformat(),"issues":int(x.issues),
                    "pct_change":round(float(pct.loc[i])*100,2)}
                   for i,x in anomalies.iterrows()][:20],
        "maximum_daily_issues":int(d.issues.max()),
        "median_issues_2021":float(d.loc[d.date.dt.year==2021,"issues"].median()),
    }


def main()->None:
    ap=argparse.ArgumentParser()
    ap.add_argument("--breadth",required=True)
    ap.add_argument("--gates",required=True)
    ap.add_argument("--outdir",default="research/out/archived_breadth_exploratory")
    args=ap.parse_args()
    bp,gp=Path(args.breadth),Path(args.gates)
    b=pd.read_csv(bp,parse_dates=["date"])
    g=pd.read_csv(gp,parse_dates=["date"])
    daily,episodes=replay(b,g)
    eligible=daily.loc[daily.proxy_route.notna()]
    if eligible.empty:
        raise ValueError("No qualified historical breadth days")
    peryear={}
    for year,group in eligible.groupby(eligible.date.dt.year):
        peryear[str(year)]={
            "scored_days":len(group),
            "proxy_trigger_days":int(group.proxy_trigger.sum()),
            "proxy_max_route":round(float(group.proxy_route.max()),4)
        }
    receipt={
        "schema":"master-top-v218-archived-universe-replay-v1",
        "asof_utc":datetime.now(timezone.utc).isoformat(),
        "status":STATUS,
        "frozen_threshold_unchanged":55.0,
        "episode_lock_sessions":126,
        "breadth_sha256":sha256(bp),
        "policy_top_sha256":sha256(gp),
        "matched_market_days":len(daily),
        "valid_hl_days":len(eligible),
        "date_range":[str(daily.date.min().date()),str(daily.date.max().date())],
        "proxy_trigger_days":int(eligible.proxy_trigger.sum()),
        "proxy_episode_count":len(episodes),
        "proxy_episodes":episodes,
        "by_year":peryear,
        "archived_source_universe_red_flags":anomaly_summary(b),
        "frozen_formula_persistence_recomputed":True,
        "is_true_pit_stock_breadth":False,
        "is_certified_unchanged_historical_v218":False,
        "has_2017_negative_control":False,
        "has_postfreeze_2026_score":False,
        "interpretation":"Research diagnostic ONLY; archived security universe has unresolved ETF/ADR/delisted/ticker reuse and sudden row-coverage shifts."
    }
    out=Path(args.outdir);out.mkdir(parents=True,exist_ok=True)
    daily[["date","issues","nh","nl","hl_balance","frozen_hl","policy","top_ratio",
           "route_upper_bound_if_hl100","proxy_route","proxy_trigger"]].to_csv(out/"exploratory_daily.csv",index=False)
    (out/"receipt.json").write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({
        "status":STATUS,
        "matched":len(daily),"scored":len(eligible),
        "trigger_days":receipt["proxy_trigger_days"],
        "episodes":episodes,
        "large_universe_shifts":receipt["archived_source_universe_red_flags"]["count_large_daily_universe_shifts"],
        "outdir":str(out)},ensure_ascii=False))


if __name__=="__main__":
    main()
