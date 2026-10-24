"""Limited sensitivity: unexplained +256 NH/NL counts on three 2021 dates.

The original source recount is NOT a verified stock-only point-in-time universe.
This deliberately changes only observed input counts and reuses the frozen
V2.1.8 H/L persistence + Route math; no coefficient/threshold optimization.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from master_top_v218 import hl_persistence_score, route_score

RAW_UNVERIFIED_COUNTS = {
    "2021-12-27": (614,330),
    "2021-12-28": (435,487),
    "2021-12-29": (565,595),
}
THRESHOLD=55.0


def compute(breadth: pd.DataFrame, policy_top: pd.DataFrame,
            perturb: bool) -> pd.DataFrame:
    if not {"date","nh","nl"}.issubset(breadth.columns):
        raise ValueError("Missing historical high/low counts")
    if not {"date","policy","top_ratio"}.issubset(policy_top.columns):
        raise ValueError("Missing ^GSPC and 2Y frozen policy gates")
    b=breadth[["date","nh","nl"]].copy()
    g=policy_top[["date","policy","top_ratio"]].copy()
    for x in (b,g):
        x["date"]=pd.to_datetime(x.date,errors="raise").dt.normalize()
        x.sort_values("date",inplace=True)
        x.reset_index(drop=True,inplace=True)
        if x.date.duplicated().any() or x.date.hasnans:
            raise ValueError("Nonunique/missing source date")
    if perturb:
        for day,(hi,lo) in RAW_UNVERIFIED_COUNTS.items():
            subset=b.index[b.date.eq(pd.Timestamp(day))]
            if len(subset)!=1: raise ValueError(f"Missing original daily breadth {day}")
            b.loc[subset,["nh","nl"]]=[hi,lo]
    if (b[["nh","nl"]]<0).any().any():raise ValueError("Negative high/low counts")
    denom=b.nh+b.nl
    balance=pd.Series(np.where(denom>0,(b.nh-b.nl)/denom,np.nan))
    b["hl"]=[
        hl_persistence_score(balance.iloc[max(0,i-19):i+1].to_numpy())
        for i in range(len(balance))
    ]
    merged=b.merge(g,on="date",how="inner",validate="one_to_one")
    def score(x):
        if pd.isna(x.hl) or pd.isna(x.policy) or pd.isna(x.top_ratio):return np.nan
        return route_score(float(x.policy),float(x.hl),float(x.top_ratio))
    merged["route"]=merged.apply(score,axis=1)
    merged["trigger"]=merged.route>=THRESHOLD
    return merged


def audit(breadth: pd.DataFrame, gates: pd.DataFrame) -> tuple[pd.DataFrame,dict]:
    before=compute(breadth,gates,False)
    after=compute(breadth,gates,True)
    out=before.merge(after[["date","nh","nl","hl","route","trigger"]],
          on="date",validate="one_to_one",suffixes=("_archive","_raw_unverified"))
    window=out.loc[out.date.between("2021-12-01","2022-02-01")].copy()
    window["delta_score"]=window.route_raw_unverified-window.route_archive
    window["trigger_changed"]=window.trigger_raw_unverified!=window.trigger_archive
    changed=window.loc[window.delta_score.abs()>1e-8]
    report={
        "status":"UNVERIFIED_UNIVERSE_NHNL_INPUT_STRESS_ONLY",
        "frozen_formula_changed":False,
        "data_provider_PIT_proven":False,
        "input_count_replacements":RAW_UNVERIFIED_COUNTS,
        "changed_trigger_days":int(window.trigger_changed.sum()),
        "number_of_score_changed_days":len(changed),
        "score_changes":[
            {"date":r.date.date().isoformat(),
             "archive_score":round(float(r.route_archive),5),
             "unverified_raw_score":round(float(r.route_raw_unverified),5)}
            for r in changed.itertuples(index=False)
        ],
        "warning":"No threshold crossings in this limited stress test does NOT validate the original raw recount, ticker identity, ETF exclusion, or baseline full-history score."
    }
    return window,report


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--breadth",required=True)
    p.add_argument("--gates",required=True)
    p.add_argument("--outdir",default="research/out/2021_raw_hilo_256_sensitivity")
    a=p.parse_args()
    output,receipt=audit(pd.read_csv(a.breadth),pd.read_csv(a.gates))
    root=Path(a.outdir);root.mkdir(parents=True,exist_ok=True)
    output.to_csv(root/"daily.csv",index=False)
    (root/"receipt.json").write_text(json.dumps(receipt,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(receipt))
if __name__=="__main__":
    main()
