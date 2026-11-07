"""Three-factor weighted-sum research for MASTER TOP V2.1.8.

All three 0-100 factors are retained:
  Policy, market breadth HL, and Top proximity.

Research score:
    weighted = w_policy*Policy + w_hl*HL + w_top*Top
    where weights sum to 1.

This module deliberately does NOT mutate frozen V2.1.8 and does not assert that
the legacy threshold 55 is calibrated for a new score distribution.
"""
from __future__ import annotations
import argparse,json
from pathlib import Path
import numpy as np
import pandas as pd

THRESHOLD=55.0
LOCK=126

def top_score(top_ratio):
    x=pd.to_numeric(top_ratio,errors="coerce")
    return 100*np.clip((x-.95)/.05,0,1)

def weighted_score(policy,hl,top_ratio,w_policy,w_hl,w_top,hl_floor=None):
    if abs((w_policy+w_hl+w_top)-1.0)>1e-9:raise ValueError("weights must sum to one")
    if min(w_policy,w_hl,w_top)<0:raise ValueError("weights cannot be negative")
    p=pd.to_numeric(policy,errors="coerce").clip(0,100)
    h=pd.to_numeric(hl,errors="coerce").clip(0,100)
    t=top_score(top_ratio)
    out=w_policy*p+w_hl*h+w_top*t
    out=out.where(p.notna() & h.notna() & t.notna(),np.nan)
    if hl_floor is not None:out=out.where(h>=hl_floor,0.0)
    return out

def grid(step=.05,min_weight=.10):
    n=round(1/step)
    vals=[round(i*step,10) for i in range(round(min_weight/step),n+1)]
    for wp in vals:
        for wh in vals:
            wt=round(1-wp-wh,10)
            if wt+1e-9<min_weight:continue
            yield wp,wh,wt

def dedup_events(frame,score_col,gspc,threshold=THRESHOLD):
    alerts=frame.loc[frame[score_col]>=threshold,["date",score_col]].sort_values("date")
    idx=gspc.index;last=None;rows=[]
    for r in alerts.itertuples(index=False):
        d=pd.Timestamp(r.date)
        if last is not None and int(((idx>last)&(idx<=d)).sum())<LOCK:continue
        end=d+pd.DateOffset(months=12)
        path=gspc.loc[(idx>=d)&(idx<=end)]
        matured=bool(end<=idx[-1])
        mdd=float((path/path.cummax()-1).min()*100) if len(path)>=2 else np.nan
        rows.append({"date":d.date().isoformat(),"score":float(getattr(r,score_col)),
                     "mdd_12m_or_to_date_pct":mdd,"matured_12m":matured})
        last=d
    return pd.DataFrame(rows)

def evaluate(primary,robust,gspc,wp,wh,wt,hl_floor=None):
    p=primary.copy();r=robust.copy()
    p["score"]=weighted_score(p.policy,p.hl,p.top_ratio,wp,wh,wt,hl_floor)
    r["score"]=weighted_score(r.policy,r.hl,r.top_ratio,wp,wh,wt,hl_floor)
    ev=dedup_events(p,"score",gspc)
    matured=ev.loc[ev.matured_12m] if len(ev) else ev
    windows={"dotcom":("2000-02-01","2001-12-31"),"gfc":("2007-06-01","2009-03-31"),
             "covid":("2020-01-01","2020-06-30"),"bear2022":("2021-09-01","2022-06-30")}
    first={}
    for name,(a,b) in windows.items():
        z=p.loc[(p.date>=a)&(p.date<=b)&(p.score>=THRESHOLD)]
        first[name]=(z.date.min().date().isoformat() if len(z) else None)
    return {
      "w_policy":wp,"w_hl":wh,"w_top":wt,"hl_floor":hl_floor or 0,
      "alert_days":int((p.score>=THRESHOLD).sum()),"episodes":len(ev),"matured":len(matured),
      "major20":int((matured.mdd_12m_or_to_date_pct<=-20).sum()) if len(matured) else 0,
      "severe15":int((matured.mdd_12m_or_to_date_pct<=-15).sum()) if len(matured) else 0,
      "correction10":int((matured.mdd_12m_or_to_date_pct<=-10).sum()) if len(matured) else 0,
      "weak_gt10":int((matured.mdd_12m_or_to_date_pct>-10).sum()) if len(matured) else 0,
      "precision10":float((matured.mdd_12m_or_to_date_pct<=-10).mean()) if len(matured) else None,
      "precision15":float((matured.mdd_12m_or_to_date_pct<=-15).mean()) if len(matured) else None,
      "robustness_alert_days":int((r.score>=THRESHOLD).sum()),**{"first_"+k:v for k,v in first.items()}
    },ev,p

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--wiki",required=True)
    ap.add_argument("--late",required=True)
    ap.add_argument("--finsaber",required=True)
    ap.add_argument("--gates",required=True)
    ap.add_argument("--outdir",required=True)
    a=ap.parse_args()
    wiki=pd.read_csv(a.wiki,parse_dates=["date"]).rename(columns={"hl_persistence":"hl"})
    late=pd.read_csv(a.late,parse_dates=["date"]).rename(columns={"hl_score":"hl"})
    fin=pd.read_csv(a.finsaber,parse_dates=["date"]).rename(columns={"hl_persistence":"hl"})
    primary=pd.concat([wiki[["date","hl","policy","top_ratio","gspc_close"]],
                       late[["date","hl","policy","top_ratio","gspc_close"]]],ignore_index=True).sort_values("date")
    robust=fin[["date","hl","policy","top_ratio","gspc_close"]].copy()
    gates=pd.read_csv(a.gates,parse_dates=["date"])
    gspc=gates.set_index("date").gspc_close.sort_index()
    rows=[]
    for floor in (None,40):
        for wp,wh,wt in grid():
            r,_,_=evaluate(primary,robust,gspc,wp,wh,wt,floor);rows.append(r)
    results=pd.DataFrame(rows)
    fixed=[("user_initial",.30,.50,.20),("balanced_alt",.20,.50,.30),
           ("top_warning",.10,.45,.45),("crisis_coverage",.25,.55,.20)]
    fixed_rows=[];events=[]
    for name,wp,wh,wt in fixed:
        r,e,_=evaluate(primary,robust,gspc,wp,wh,wt,None);r["name"]=name;fixed_rows.append(r)
        if len(e):e["name"]=name;events.append(e)
    out=Path(a.outdir);out.mkdir(parents=True,exist_ok=True)
    results.to_csv(out/"weight_grid_5pct.csv",index=False)
    pd.DataFrame(fixed_rows).to_csv(out/"fixed_weight_comparison.csv",index=False)
    pd.concat(events,ignore_index=True).to_csv(out/"fixed_weight_events.csv",index=False)
    # Two explicit research candidates.
    for name,wp,wh,wt in (("top_warning",.10,.45,.45),("crisis_coverage",.25,.55,.20)):
        _,e,daily=evaluate(primary,robust,gspc,wp,wh,wt,None)
        daily[["date","hl","policy","top_ratio","score"]].to_csv(out/f"{name}_daily.csv",index=False)
        e.to_csv(out/f"{name}_events.csv",index=False)
    (out/"receipt.json").write_text(json.dumps({
        "status":"WEIGHTED_SUM_RESEARCH_ONLY_PRODUCTION_UNCHANGED",
        "legacy_threshold_used_for_comparability":55,
        "grid_step_pct":5,"minimum_factor_weight_pct":10,
        "top_warning_weights":{"HL":45,"Top":45,"Policy":10},
        "crisis_coverage_weights":{"HL":55,"Policy":25,"Top":20},
        "note":"COVID cannot be a pre-peak weighted-three-factor alert at threshold55 when pre-peak HL and Policy are zero unless Top weight itself exceeds55%, which would make new highs almost sufficient alone.",
        "frozen_v218_modified":False},indent=2)+"\n")
if __name__=="__main__":main()
