"""Quarantine partial historical source days; NEVER fabricate bars or alerts.

Read-only repair overlay for user's archived raw and aggregated daily counts.
Requires the original historical sources supplied locally. Does not republish
licensed stock-level data and does not touch official V2.1.8 production score.
"""
from __future__ import annotations
import argparse,hashlib,json
from pathlib import Path
import numpy as np
import pandas as pd

SCHEMA = "v218-historical-source-coverage-repair-v1"
QA_PCT = .20 # QA only, NOT a trading rule

def repair(recon:pd.DataFrame,breadth:pd.DataFrame,score:pd.DataFrame):
    for name,df in (("raw",recon),("breadth",breadth),("score",score)):
        if "date" not in df: raise ValueError(f"{name}: date is required")
        df["date"]=pd.to_datetime(df.date,errors="raise").dt.normalize()
        if df.date.duplicated().any() or df.date.isna().any():
            raise ValueError(f"{name}: missing or duplicate dates")
    for df,cols in (
        (recon,{"archived_issues","raw_parquet_rows","difference_raw_minus_archived"}),
        (breadth,{"issues","nh","nl"}),
        (score,{"trigger","route_archive_breadth_proxy"}),
    ):
        if not cols<=set(df):raise ValueError("Missing required source/replay fields")
    b=recon.merge(breadth[["date","issues","nh","nl"]],
                  how="inner",on="date",validate="one_to_one")
    b=b.merge(score[["date","trigger","route_archive_breadth_proxy"]],
              how="inner",on="date",validate="one_to_one").sort_values("date").reset_index(drop=True)
    if not len(b)==len(recon)==len(breadth)==len(score):
        raise ValueError("Calendar is not complete across original sources")
    if not b.issues.equals(b.archived_issues):
        raise ValueError("Raw and aggregate universe count disagreement")
    if not ((b.raw_parquet_rows-b.archived_issues)==b.difference_raw_minus_archived).all():
        raise ValueError("Raw aggregation reconciliation invalid")
    if (b[["issues","raw_parquet_rows","nh","nl"]]<0).any().any():
        raise ValueError("Negative universe or high-low counts")
    a=b.raw_parquet_rows.astype(float)
    before,after=a.shift(1),a.shift(-1)
    b["raw_daily_pct_change"]=(a.pct_change(fill_method=None)*100).replace([np.inf,-np.inf],np.nan)
    # Extreme *isolated* missing central partition: both neighbours are 1.67x
    # larger and agree to within 15%; a sustained real regime break isn't an
    # automatically reconstructed missing day.
    b["suspected_partial_partition"]=((a<before*.6)&(a<after*.6)&
          (before/after).between(.85,1.15)).fillna(False)
    b["raw_universe_break_for_source_review"]=b.raw_daily_pct_change.abs()>20.0
    b.loc[b.date<pd.Timestamp("2020-01-01"),"raw_universe_break_for_source_review"]=False
    b["source_status"]="UNCERTIFIED_HISTORICAL_SECURITY_UNIVERSE"
    b.loc[b.raw_universe_break_for_source_review,
          "source_status"]="SOURCE_COUNT_DISCONTINUITY_REQUIRES_REVIEW"
    b.loc[b.suspected_partial_partition,
          "source_status"]="QUARANTINED_PARTIAL_DAY_NEEDS_ORIGINAL_REDOWNLOAD"
    b["frozen_55_signal_certified"]=False
    b["canonical_v218_score"]=np.nan
    b["historical_score_kind"]="UNVERIFIED_ARCHIVE_EXPLORATORY"
    b.loc[b.trigger,"historical_score_kind"]="UNVERIFIED_ARCHIVE_CANDIDATE"
    b.loc[b.suspected_partial_partition,"historical_score_kind"]="QUARANTINED_NO_SCORE"
    truncated=[{"date":r.date.date().isoformat(),"raw_rows":int(r.raw_parquet_rows),
                "previous":int(a.iloc[i-1]),"following":int(a.iloc[i+1])}
               for i,r in b.loc[b.suspected_partial_partition].iterrows()]
    receipt={
       "schema":SCHEMA,"status":"SOURCE_QA_PARTIALLY_REPAIRED_NO_HISTORICAL_MARKET_BAR_BACKFILL",
       "market_sessions_evaluated":len(b),
       "partial_historical_dates_quarantined":truncated,
       "raw_universe_jump_dates":int(b.raw_universe_break_for_source_review.sum()),
       "former_exploratory_trigger_days":int(b.trigger.eq(True).sum()),
       "qualified_original_frozen_trigger_days":0,
       "underlying_2021_signal_correctness":"UNDETERMINED",
       "new_historical_security_prices_invented":False,
       "frozen_model_math_threshold_episode_lock_unchanged":True,
       "PIT_full_US_stock_universe_available":False,
       "historic_security_type_normalization_complete":False,
       "rerun_requirements":[
         "re-download dated stock_daily partitions from an entitled provider",
         "attach DATE-SPECIFIC CS/ADRC reference and permanent security identity",
         "independently validate earliest IPO, delisting, split adjustment and ticker reuse",
         "verify 252 prior per-security valid closes plus 20-day persistence",
         "preserve benchmark ^GSPC and Treasury vintage provenance before promotion"
       ],
    }
    return b,receipt

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--reconciliation",required=True)
    p.add_argument("--breadth",required=True)
    p.add_argument("--exploratory",required=True)
    p.add_argument("--outdir",required=True)
    z=p.parse_args()
    source_files=list(map(Path,(z.reconciliation,z.breadth,z.exploratory)))
    daily,receipt=repair(*(pd.read_csv(path) for path in source_files))
    receipt["source_file_sha256"]={p.name:hashlib.sha256(p.read_bytes()).hexdigest()
                                    for p in source_files}
    out=Path(z.outdir);out.mkdir(parents=True,exist_ok=True)
    daily.to_csv(out/"historical_source_quality_overlay.csv",index=False)
    (out/"repair_receipt.json").write_text(json.dumps(receipt,indent=2)+"\n")
    print(json.dumps({"status":receipt["status"],"quarantined_dates":receipt["partial_historical_dates_quarantined"],"true_model_signal_count_certified":0}))
if __name__=="__main__":main()
