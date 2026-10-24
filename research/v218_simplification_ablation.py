"""Research-only ablation study for MASTER TOP V2.1.8.

Inputs are derived daily research CSVs already generated from the user's approved
historical/forward price sources. This script never touches production V2.1.8.

Primary comparison:
  1) frozen original
  2) remove HL>=75 hard gate
  3) lower HL gate to 60
  4) remove TopProx from multiplication
  5) remove Policy from multiplication
  6) breadth-only
  7) use R6 only
  8) use R1 only
  9) use max(R1,R6)
 10) use arithmetic mean of R1/R6
 11) soften top band to 90%-100%

All variants retain threshold=55 for sensitivity comparability only.
Changing a component changes the score distribution; this is not a claim that
55 is optimally calibrated for a revised model.
"""
from __future__ import annotations
import argparse,json
from pathlib import Path
import numpy as np
import pandas as pd

THRESHOLD=55.0
LOCK=126

def clip(x,lo=0.0,hi=1.0):
    return np.minimum(hi,np.maximum(lo,x))

def build_variants(df:pd.DataFrame,hl_col:str,gates:pd.DataFrame)->pd.DataFrame:
    x=df.copy()
    x["date"]=pd.to_datetime(x.date,errors="raise")
    if not {"delta_1m_bp","delta_6m_bp"}<=set(x):
        g=gates[["date","delta_1m_bp","delta_6m_bp"]].copy()
        g["date"]=pd.to_datetime(g.date,errors="raise")
        x=x.merge(g,on="date",how="left",validate="one_to_one")
    needed={hl_col,"policy","top_ratio","gspc_close","delta_1m_bp","delta_6m_bp"}
    if not needed<=set(x):raise ValueError("Missing derived frozen inputs: "+repr(sorted(needed-set(x))))
    hl=pd.to_numeric(x[hl_col],errors="coerce")
    policy=pd.to_numeric(x.policy,errors="coerce")
    tr=pd.to_numeric(x.top_ratio,errors="coerce")
    top5=clip((tr-.95)/.05)
    top10=clip((tr-.90)/.10)
    r1=100*clip(pd.to_numeric(x.delta_1m_bp,errors="coerce")/20)
    r6=100*clip((pd.to_numeric(x.delta_6m_bp,errors="coerce")-10)/60)

    def score(pol,top,topgate=None,hlgate=None):
        pol=np.asarray(pol,dtype=float);top=np.asarray(top,dtype=float)
        value=pol*np.sqrt(clip(hl/100))*np.sqrt(top)
        mask=hl.notna().to_numpy() & np.isfinite(pol) & tr.notna().to_numpy()
        if topgate is not None:mask &= tr.to_numpy()>=topgate
        if hlgate is not None:mask &= hl.to_numpy()>=hlgate
        return np.where(mask,value,0.0)

    out=pd.DataFrame({"date":x.date,"gspc_close":x.gspc_close,
                      "hl":hl,"policy":policy,"top_ratio":tr,"r1":r1,"r6":r6})
    out["original"]=score(policy,top5,.95,75)
    out["no_hl_gate"]=score(policy,top5,.95,None)
    out["hl_gate_60"]=score(policy,top5,.95,60)
    out["no_top_factor"]=score(policy,np.ones(len(x)),None,75)
    out["no_policy_factor"]=score(np.full(len(x),100.0),top5,.95,75)
    out["breadth_only"]=hl.fillna(0)
    out["policy_r6_only"]=score(r6,top5,.95,75)
    out["policy_r1_only"]=score(r1,top5,.95,75)
    out["policy_either_max"]=score(np.maximum(r1,r6),top5,.95,75)
    out["policy_arith_mean"]=score((r1+r6)/2,top5,.95,75)
    out["top_10pct_soft"]=score(policy,top10,.90,75)
    return out

def dedup_events(v:pd.DataFrame,col:str,gspc:pd.Series,threshold:float=THRESHOLD)->pd.DataFrame:
    alerts=v.loc[v[col]>=threshold,["date",col]].sort_values("date")
    market=gspc.index
    events=[];last=None
    for row in alerts.itertuples(index=False):
        d=pd.Timestamp(row.date)
        if last is not None and int(((market>last)&(market<=d)).sum())<LOCK:continue
        end=d+pd.DateOffset(months=12)
        w=gspc.loc[(gspc.index>=d)&(gspc.index<=end)]
        matured=end<=gspc.index[-1]
        mdd=float((w/w.cummax()-1).min()*100) if len(w)>=2 else np.nan
        events.append({"date":d.date().isoformat(),"score":float(getattr(row,col)),
                       "mdd_12m_or_to_date_pct":mdd,"matured_12m":matured})
        last=d
    return pd.DataFrame(events)

def run(early:pd.DataFrame,late:pd.DataFrame,robust:pd.DataFrame,gates:pd.DataFrame):
    g=gates.copy();g["date"]=pd.to_datetime(g.date,errors="raise")
    gspc=g.set_index("date")["gspc_close"].sort_index()
    E=build_variants(early,"hl_persistence",g)
    L=build_variants(late,"hl_score",g)
    R=build_variants(robust,"hl_persistence",g)
    variants=[c for c in E.columns if c not in {"date","gspc_close","hl","policy","top_ratio","r1","r6"}]
    summaries=[];details=[]
    for col in variants:
        ev=[]
        for label,v in (("WIKI_2000_2018",E),("USER_2019_2026",L)):
            z=dedup_events(v,col,gspc)
            if len(z):
                z["source"]=label;z["variant"]=col;ev.append(z)
        d=pd.concat(ev,ignore_index=True) if ev else pd.DataFrame()
        m=d.loc[d.matured_12m] if len(d) else pd.DataFrame()
        summaries.append({
            "variant":col,
            "alert_days_primary":int((E[col]>=THRESHOLD).sum()+(L[col]>=THRESHOLD).sum()),
            "dedup_episodes_primary":len(d),
            "matured_episodes":len(m),
            "major_bear_mdd_le_-20":int((m.mdd_12m_or_to_date_pct<=-20).sum()) if len(m) else 0,
            "severe_mdd_le_-15":int((m.mdd_12m_or_to_date_pct<=-15).sum()) if len(m) else 0,
            "correction_mdd_le_-10":int((m.mdd_12m_or_to_date_pct<=-10).sum()) if len(m) else 0,
            "weak_mdd_gt_-10":int((m.mdd_12m_or_to_date_pct>-10).sum()) if len(m) else 0,
            "wiki_alert_days":int((E[col]>=THRESHOLD).sum()),
            "2019_2026_alert_days":int((L[col]>=THRESHOLD).sum()),
            "finsaber_robustness_alert_days":int((R[col]>=THRESHOLD).sum()),
        })
        if len(d):details.append(d)
    return pd.DataFrame(summaries),pd.concat(details,ignore_index=True),E,L,R

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--early",required=True)
    p.add_argument("--late",required=True)
    p.add_argument("--robust",required=True)
    p.add_argument("--gates",required=True)
    p.add_argument("--outdir",required=True)
    a=p.parse_args()
    summary,events,early,late,robust=run(
        pd.read_csv(a.early),pd.read_csv(a.late),pd.read_csv(a.robust),pd.read_csv(a.gates))
    out=Path(a.outdir);out.mkdir(parents=True,exist_ok=True)
    summary.to_csv(out/"variant_summary.csv",index=False)
    events.to_csv(out/"deduplicated_event_details.csv",index=False)
    candidate=pd.concat([
        early.assign(source_segment="WIKI_2000_2018"),
        late.assign(source_segment="USER_2019_2026")],ignore_index=True)
    candidate=candidate[["date","source_segment","hl","policy","top_ratio","no_policy_factor"]]
    candidate["candidate_alert"]=candidate.no_policy_factor>=THRESHOLD
    candidate.to_csv(out/"candidate_A_top_plus_breadth_daily.csv",index=False)
    best=summary.loc[summary.variant=="no_policy_factor"].iloc[0].to_dict()
    (out/"receipt.json").write_text(json.dumps({
        "status":"RESEARCH_ABLATION_ONLY_PRODUCTION_UNCHANGED",
        "candidate_A":"TopProx + HL, policy retained as confirmation metadata but removed from mandatory multiplication",
        "candidate_A_metrics":best,
        "threshold_note":"55 retained only for sensitivity comparability; revised score requires independent recalibration/OOS validation",
        "frozen_v218_modified":False},indent=2)+"\n")
    print(summary.sort_values(["severe_mdd_le_-15","weak_mdd_gt_-10","alert_days_primary"],
          ascending=[False,True,True]).to_string(index=False))

if __name__=="__main__":main()
