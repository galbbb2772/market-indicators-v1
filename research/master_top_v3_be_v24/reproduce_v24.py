#!/usr/bin/env python3
"""Bubble Exhaustion V2.4 retrospective rolling forecast (NOT PIT/OOS).
Usage: python reproduce_v24.py MONTHLY_FORECAST_OUTCOMES.csv EXTENDED_FEATURES.csv OUTPUT.csv
Python standard library only. Annual anchor models train only on fully matured prior outcomes.
"""
from __future__ import annotations
import csv, datetime as dt, math, sys

FEATURES = {
    "PRIOR": (),
    "CAPE": ("cape",),
    "CAPE_TOP": ("cape", "top"),
    "CAPE_TOP_ROLL": ("cape", "top", "roll"),
    "CAPE_TOP_MEMORY": ("cape", "top", "memory"),
}
RIDGE_LAMBDA = 2.0
PURGE_DAYS = 395
MIN_TRAIN = 11

def read(path):
    with open(path, newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))

def sig(x):
    if x>=0:
        return 1/(1+math.exp(-x))
    y=math.exp(x)
    return y/(1+y)

def transform(k,r):
    return {
        "cape": lambda: (r["cape"]-75)/25,
        "top": lambda: (1-r["top"])/.1,
        "roll": lambda: r["roll"]/25,
        "memory": lambda: (r["memory"]-50)/25
    }[k]()

def solve(H,g):
    n=len(g)
    M=[list(H[i])+[g[i]] for i in range(n)]
    for k in range(n):
        pivot=max(range(k,n),key=lambda j:abs(M[j][k]))
        if abs(M[pivot][k])<1e-10: raise ValueError("singular")
        M[k],M[pivot]=M[pivot],M[k]
        d=M[k][k]
        for j in range(k,n+1):M[k][j]/=d
        for i in range(n):
            if i==k:continue
            c=M[i][k]
            for j in range(k,n+1):M[i][j]-=c*M[k][j]
    return [row[n] for row in M]

def fit(train, features):
    d=len(features)+1
    events=sum(r["outcome_mdd20"] for r in train)
    beta=[0.0]*d
    beta[0]=math.log((events+.5)/(len(train)-events+.5))
    for _ in range(35):
        grad=[0.0]*d
        H=[[0.0]*d for k in range(d)]
        for r in train:
            x=[1.0]+[transform(k,r) for k in features]
            p=sig(sum(a*b for a,b in zip(beta,x)))
            w=p*(1-p)
            for i in range(d):
                grad[i]+=(p-r["outcome_mdd20"])*x[i]
                for j in range(d):H[i][j]+=w*x[i]*x[j]
        for j in range(1,d):
            grad[j]+=RIDGE_LAMBDA*beta[j]
            H[j][j]+=RIDGE_LAMBDA
        for j in range(d):H[j][j]+=1e-7
        step=solve(H,grad)
        beta=[a-b for a,b in zip(beta,step)]
        if sum(abs(v) for v in step)<1e-8:break
    return beta

def predict(beta, features, row):
    x=[1]+[transform(k,row) for k in features]
    return sig(sum(a*b for a,b in zip(beta,x)))

def generate(outcomes, monthly):
    source={r["month"]:r for r in monthly}
    records=[]
    for r in outcomes:
        if r["complete_12m"]!="true" or r["data_status"]!="OK":continue
        if r["month"] not in source: raise ValueError("missing input: "+r["month"])
        v=source[r["month"]]
        if v["data_status"]!="OK":raise ValueError("status mismatch: "+r["month"])
        row={
            "month":r["month"],
            "date":dt.date.fromisoformat(r["date"]),
            "year":int(r["month"][:4]),
            "anchor":r["month"][5:],
            "cape":float(r["cape_pct"]),
            "top":float(v["top_ratio"]),
            "roll":float(v["rollover"]),
            "memory":float(v["lev_memory"]),
            "outcome_mdd20":int(r["fwd12_mdd20"]=="true"),
            "outcome_entry20":int(float(r["forward_12m_entry_to_min"])<=-20),
        }
        if row["anchor"] in ("01","04","07","10"):records.append(row)
    rows=[]
    for anchor in ("01","04","07","10"):
        group=sorted((r for r in records if r["anchor"]==anchor),key=lambda x:x["date"])
        for target in (r for r in group if r["year"]>=2013):
            prior=[r for r in group if r["date"]+dt.timedelta(days=PURGE_DAYS)<=target["date"]]
            if len(prior)<MIN_TRAIN or len(set(x["outcome_mdd20"] for x in prior))<2:
                continue
            pred={"month":target["month"],"year":target["year"],"offset":anchor,
                  "outcome_mdd20":target["outcome_mdd20"],"outcome_entry20":target["outcome_entry20"],
                  "trained_months":len(prior),"train_end":prior[-1]["month"]}
            n=sum(x["outcome_mdd20"] for x in prior)
            for name,fs in FEATURES.items():
                p=(n+.5)/(len(prior)+1) if name=="PRIOR" else predict(fit(prior,fs),fs,target)
                pred["p_"+name]=f"{p:.7f}"
            rows.append(pred)
    return rows

def main():
    if len(sys.argv)!=4:raise SystemExit(__doc__)
    rows=generate(read(sys.argv[1]),read(sys.argv[2]))
    if len(rows)!=51:print("WARNING: source/forecast count differs from V2.4 frozen baseline (51)")
    with open(sys.argv[3],"w",encoding="utf-8",newline="") as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]))
        w.writeheader();w.writerows(rows)
    print("V2.4 retrospective rolling forecasts:",len(rows),"NO PIT or untouched OOS certification")

if __name__=="__main__":main()
