#!/usr/bin/env python3
"""Retrospective BE V2.3 annual-anchor audit; NOT independent OOS/PIT.
Usage: python analyze_v23.py V22_MONTHLY.csv V21_STATE.csv OUTPUT_DIR
Stdlib-only. The four annual offsets are correlated replicates.
"""
import csv
from pathlib import Path
import sys

def read(path):
    with open(path, newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))

def write(path, rows):
    if not rows: raise ValueError("empty results")
    with open(path, "w", newline="", encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]))
        w.writeheader();w.writerows(rows)

def auc(rows, score, outcome):
    v=[]
    for row in rows:
        try:
            if not row.get(score): continue
            n=float(row[score])
            if n != n or abs(n)==float("inf"): continue
            v.append((n,bool(row[outcome])))
        except (KeyError, ValueError, TypeError): continue
    yes=[x for x,b in v if b];no=[x for x,b in v if not b]
    if not yes or not no: return None
    return sum(1 if a>b else .5 if a==b else 0 for a in yes for b in no)/(len(yes)*len(no))

class LCG:
    def __init__(self): self.s=20261019
    def draw(self,n):
        self.s=(self.s*1664525+1013904223)&0xffffffff
        return (self.s*n)>>32

def ci(rows,rng,rep=2500):
    vals=[]
    for _ in range(rep):
        x=[rows[rng.draw(len(rows))] for __ in rows]
        a=auc(x,"bubble_build","mdd20"); b=auc(x,"cape_pct","mdd20")
        if a is not None and b is not None: vals.append(a-b)
    vals.sort()
    if len(vals)<200:return (None,None,len(vals))
    return (vals[int(.025*(len(vals)-1))],vals[int(.975*(len(vals)-1))],len(vals))

def fmt(x):return "" if x is None else f"{x:.3f}"

def analyze(price,state):
    index={x["month"]:x for x in state}
    if len(index)!=len(state): raise ValueError("duplicate state month")
    rows=[]
    for v in price:
        if v.get("complete_12m")!="true": continue
        m=v["month"]
        if m not in index: raise ValueError("missing state "+m)
        s=index[m]
        if v["data_status"]!="OK" or s["data_status"]!="OK" or v["state"]!=s["state_v21"]:
            raise ValueError("unverified/mismatched state "+m)
        d={**v,**s}
        d["mdd20"]=v["fwd12_mdd20"]=="true"
        d["entry20"]=float(v["forward_12m_entry_to_min"])<=-20
        rows.append(d)
    rng=LCG();summary=[];counts=[];recent=[]
    for period in ("pre2019","2019plus","all"):
        for mo in ("01","04","07","10"):
            selected=[r for r in rows if r["month"][5:7]==mo and
                      (period=="all" or r["period"]==period)]
            if not selected:continue
            a=auc(selected,"bubble_build","mdd20")
            b=auc(selected,"cape_pct","mdd20")
            low,hi,reps=ci(selected,rng)
            summary.append(dict(
                period=period,month_offset=mo,n=len(selected),
                events_mdd20=sum(r["mdd20"] for r in selected),
                auc_build=fmt(a),auc_cape=fmt(b),
                auc_rollover=fmt(auc(selected,"rollover","mdd20")),
                auc_build_minus_cape=fmt(a-b) if a is not None and b is not None else "",
                bootstrap_delta_low=fmt(low),bootstrap_delta_high=fmt(hi),
                bootstrap_valid_draws=reps,
                entry_loss20_count=sum(r["entry20"] for r in selected),
                auc_build_entry_loss20=fmt(auc(selected,"bubble_build","entry20")),
                auc_cape_entry_loss20=fmt(auc(selected,"cape_pct","entry20"))))
            for name in ("IDLE","ARMED","ROLLOVER_ACTIVE","ARMED_REHEATED"):
                s=[r for r in selected if r["state_v21"]==name]
                counts.append(dict(period=period,month_offset=mo,state=name,n=len(s),
                                   mdd20=sum(r["mdd20"] for r in s),
                                   entry_loss20=sum(r["entry20"] for r in s)))
            if period=="2019plus":
                for r in selected:
                    recent.append(dict(sample_month=mo,observation=r["month"],
                                       state=r["state_v21"],
                                       mdd20=str(r["mdd20"]).lower(),
                                       entry_loss20=str(r["entry20"]).lower(),
                                       build=r["bubble_build"],cape=r["cape_pct"]))
    return summary,counts,recent

if __name__=="__main__":
    if len(sys.argv)!=4:raise SystemExit(__doc__)
    out=Path(sys.argv[3]);out.mkdir(parents=True,exist_ok=True)
    result=analyze(read(sys.argv[1]),read(sys.argv[2]))
    for name,rows in zip(("V23_ANNUAL_DISCRIMINATION.csv",
                          "V23_ANNUAL_STATE_COUNTS.csv",
                          "V23_POST2019_ANNUAL_OBSERVATIONS.csv"),result):
        write(out/name,rows)
    print("V2.3 annual-anchor research done; NOT true OOS or vintage PIT.")
