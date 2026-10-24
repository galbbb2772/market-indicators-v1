"""2019-2026 preserved-raw vs archived V2.1.8 breadth continuity QA.

Supply existing private source files locally. DO NOT add licensed source data to
the public repository. A 20% symbol-count change is only a data-QA test;
it is not a frozen strategy modification, nor proof of a false alert.

Inputs:
  --reconciliation archive_vs_raw_daily_count_reconciliation.csv
  --breadth reconstructed_allus_breadth_2019_2026-03.csv
  --replay exploratory_all_days.csv
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

HISTORY = 252
PERSISTENCE = 20
SENSITIVITY_LAST_SESSION = HISTORY + PERSISTENCE - 1
QA_RELATIVE_CHANGE = 0.20


def qa_results(recon: pd.DataFrame, breadth: pd.DataFrame,
               replay: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    required = (
        (recon, {"date", "raw_parquet_rows", "archived_issues", "difference_raw_minus_archived"}),
        (breadth, {"date", "issues"}),
        (replay, {"date", "route_archive_breadth_proxy", "trigger"}),
    )
    for frame, columns in required:
        if not columns <= set(frame.columns):
            raise ValueError(f"Missing input columns: {sorted(columns-set(frame.columns))}")
    x,b,s=(v.copy() for v,_ in required)
    for frame in (x,b,s):
        frame["date"]=pd.to_datetime(frame.date, errors="raise").dt.normalize()
        frame.sort_values("date",inplace=True)
        frame.reset_index(drop=True,inplace=True)
        if frame.date.hasnans or frame.date.duplicated().any():
            raise ValueError("Missing/duplicate source market date")
    if not x.date.equals(b.date):
        raise ValueError("Raw and aggregated market calendars disagree")
    if not x.archived_issues.equals(b.issues):
        raise ValueError("Reconciliation and original breadth counts disagree")
    if not (x.raw_parquet_rows - x.archived_issues == x.difference_raw_minus_archived).all():
        raise ValueError("Invalid reconciliation count arithmetic")
    if (x[["raw_parquet_rows","archived_issues"]] < 0).any().any():
        raise ValueError("Negative source counts")

    x["raw_daily_pct"] = x.raw_parquet_rows.pct_change(fill_method=None)*100
    x["aggregate_daily_pct"] = x.archived_issues.pct_change(fill_method=None)*100
    x["raw_large_jump"] = x.raw_daily_pct.abs()>100*QA_RELATIVE_CHANGE
    x["aggregate_large_jump"] = x.aggregate_daily_pct.abs()>100*QA_RELATIVE_CHANGE
    # Day-1 archived warmup issues = 0, not an interpretable source break.
    source_jump=(x.raw_large_jump|x.aggregate_large_jump)&(x.date>=pd.Timestamp("2020-01-01"))
    flags=np.zeros(len(x), dtype=bool)
    last=np.full(len(x),-1,dtype=np.int32)
    for i in np.flatnonzero(source_jump.to_numpy()):
        end=min(len(x),i+SENSITIVITY_LAST_SESSION+1)
        flags[i:end]=True
        last[i:end]=i
    x["lookback_source_review"] = flags
    x["source_break_date"] = [
        x.date.iloc[k].strftime("%Y-%m-%d") if k>=0 else None for k in last
    ]
    x["source_break_session_gap"] = [i-k if k>=0 else None for i,k in enumerate(last)]

    signals=s.loc[s.trigger.eq(True)].merge(
        x[["date","raw_parquet_rows","archived_issues","source_break_date",
           "source_break_session_gap","lookback_source_review"]],
        on="date",how="left",validate="one_to_one",
    )
    if signals.raw_parquet_rows.isna().any():
        raise ValueError("Exploratory trigger lacks raw-source audit date")
    episodes=[
        {"date":z.date.date().isoformat(),
         "research_route":round(float(z.route_archive_breadth_proxy),5),
         "review_252_plus_20_window":bool(z.lookback_source_review),
         "last_count_break":z.source_break_date,
         "sessions_since_break":int(z.source_break_session_gap) if pd.notna(z.source_break_session_gap) else None}
        for z in signals.itertuples(index=False)
    ]
    incidents=[
        {"date":z.date.date().isoformat(),
         "raw_rows":int(z.raw_parquet_rows),"archive_rows":int(z.archived_issues),
         "raw_delta_pct":round(float(z.raw_daily_pct),2),
         "archive_delta_pct":round(float(z.aggregate_daily_pct),2),
         "raw_only":bool(z.raw_large_jump and not z.aggregate_large_jump)}
        for z in x.loc[source_jump].itertuples(index=False)
    ]
    receipt={
        "schema":"v218_source_qa_historical_raw_vs_archived_v1",
        "status":"SOURCE_SENSITIVITY_ONLY_NOT_PIT_CERTIFIED",
        "frozen_formula_changed":False,
        "stock_universe_PIT_verified":False,
        "new_actual_v218_production_score":False,
        "market_days":len(x),
        "raw_vs_aggregate_count_mismatch_days":int(x.difference_raw_minus_archived.ne(0).sum()),
        "source_count_jump_days":len(incidents),
        "source_count_jumps":incidents,
        "source_review_days_271":int(flags.sum()),
        "possible_alert_days":len(episodes),
        "possible_alert_days_in_source_review":sum(x["review_252_plus_20_window"] for x in episodes),
        "candidate_days":episodes,
        "true_alarm_validity":"UNDETERMINED",
        "notes":[
            "271 sessions is a conservative feature-memory QA window, not a market signal rule.",
            "Raw price count spikes are not proof that the archived per-stock features are wrong.",
            "252 prior valid observations PER SECURITY need not coincide with 252 market calendar days.",
            "The source includes ETFs and lacks PIT stable security IDs, so candidate signals are uncertified.",
        ],
    }
    return x,receipt


def main()->None:
    p=argparse.ArgumentParser()
    p.add_argument("--reconciliation",required=True)
    p.add_argument("--breadth",required=True)
    p.add_argument("--replay",required=True)
    p.add_argument("--outdir",default="research/out/raw_archive_qa")
    a=p.parse_args()
    source_paths=(a.reconciliation,a.breadth,a.replay)
    frames=[pd.read_csv(x) for x in source_paths]
    full,receipt=qa_results(*frames)
    receipt["source_sha256"]={
        k:hashlib.sha256(Path(v).read_bytes()).hexdigest()
        for k,v in zip(("reconciliation","breadth","replay"),source_paths)
    }
    root=Path(a.outdir);root.mkdir(parents=True,exist_ok=True)
    (root/"receipt.json").write_text(json.dumps(receipt,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    full[["date","raw_parquet_rows","archived_issues","difference_raw_minus_archived",
          "raw_daily_pct","aggregate_daily_pct","raw_large_jump",
          "aggregate_large_jump","lookback_source_review",
          "source_break_date","source_break_session_gap"]].to_csv(root/"daily.csv",index=False)
    print(json.dumps({k:receipt[k] for k in ("status","market_days","source_count_jump_days",
                                           "possible_alert_days","possible_alert_days_in_source_review")}))
if __name__=="__main__":
    main()
