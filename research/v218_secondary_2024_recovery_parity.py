"""Compare an authorized secondary 2024 grouped EOD source with corrupt archived bars.

This never splices Massive/Polygon bars into the canonical frozen 2019-2026
source, even where overlap is good: split/adjusted conventions, historical
share-class membership and full-market common-stock identity remain unproven.
All results are forensic audit receipts, not trading signals.
"""
from __future__ import annotations
import argparse,hashlib,json
from pathlib import Path
import numpy as np
import pandas as pd

DATE="2024-11-13"
REQUIRED_REPLACEMENT=("date","ticker","close","open","high","low","volume","otc","utc_timestamp_ms")
STATUS="SECONDARY_2024_RECOVERY_CANDIDATE_QUARANTINED_NO_AUTO_MERGE"

def secondary_audit(secondary:pd.DataFrame, archive:pd.DataFrame,
                    min_secondary_rows:int=10000)->dict:
    if not set(REQUIRED_REPLACEMENT)<=set(secondary):
        raise ValueError("Incomplete secondary grouped source fields")
    if not {"date","ticker","close"}<=set(archive):
        raise ValueError("Original historical parquet must have date/ticker/close")
    s=secondary.copy();a=archive.copy()
    for z,src in ((s,"secondary"),(a,"archive")):
        z["date"]=pd.to_datetime(z.date,errors="raise").dt.strftime("%Y-%m-%d")
        if not (z.date==DATE).all() or z.date.isna().any():
            raise ValueError(f"{src}: one exact supported date is mandatory")
        z["ticker"]=z.ticker.astype(str).str.strip()
        if (z.ticker=="").any() or z.ticker.duplicated().any():
            raise ValueError(f"{src}: missing or duplicate ticker")
        z["close"]=pd.to_numeric(z.close,errors="coerce")
        if z.close.isna().any() or (z.close<=0).any():
            raise ValueError(f"{src}: invalid close")
    if len(s)<min_secondary_rows:raise ValueError("Secondary market day below minimum expected universe coverage")
    if len(a)>=len(s)*.85:raise ValueError("Archive is not evidently truncated; this reconstruction case is not justified")
    if not (pd.to_numeric(s.utc_timestamp_ms,errors="raise")==1731531600000).all():
        raise ValueError("Secondary bar timestamp differs from original NYSE 2024-11-13 UTC day")
    m=a[["ticker","close"]].merge(s[["ticker","close"]],how="inner",on="ticker",
                                  validate="one_to_one",suffixes=("_original","_secondary"))
    if len(m)<min(len(a)*.70,2000) and min_secondary_rows>=10000:
        raise ValueError("Secondary source overlap too small; likely unrelated data or tickers")
    m["relative_close_abs_diff_pct"]=100*(m.close_secondary/m.close_original-1).abs()
    p=float(m.relative_close_abs_diff_pct.quantile(.95)) if len(m) else None
    med=float(m.relative_close_abs_diff_pct.median()) if len(m) else None
    new_tickers=set(s.ticker)-set(a.ticker)
    bad_open=s.loc[pd.to_numeric(s.open,errors="coerce").le(0),"ticker"].tolist()
    receipt={
        "schema":"v218-secondary-historical-day-candidate-v1",
        "date":DATE,
        "status":STATUS,
        "actual_private_recovery_rows":len(s),
        "original_corrupt_rows":len(a),
        "secondary_symbols_not_in_corrupt_archive":len(new_tickers),
        "corrupt_archive_symbols_not_in_secondary":len(set(a.ticker)-set(s.ticker)),
        "comparison_overlap":len(m),
        "p95_absolute_close_disagreement_pct":round(p,5) if p is not None else None,
        "median_absolute_close_disagreement_pct":round(med,5) if med is not None else None,
        "unusual_open_price_symbols":bad_open[:25],
        "split_adjusted_price_parity_verified":bool(p is not None and p<.25 and med is not None and med<.1),
        "market_universe_equivalence_verified":False,
        "pit_common_stock_universe_verified":False,
        "automatically_replace_canonical_archive":False,
        "scorer_source_eligibility":"BLOCKED_NEEDS_PERMANENT_ID_PIT_SECURITY_CLASSIFICATION_AND_ADJUSTMENT_RECONCILIATION",
        "why_not_merge":"Incomplete original data cannot be patched with a different provider's bars without verifying eligible stock universe, adjustments and bar/IPO/delisting rules.",
    }
    return receipt

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--secondary",required=True,help="Authorized private Massive 2024-11-13 snapshot")
    p.add_argument("--archived-parquet",required=True,help="Original private US_DAILY parquet")
    p.add_argument("--out",required=True)
    a=p.parse_args()
    raw=pd.read_parquet(a.archived_parquet,columns=["date","ticker","close"],
                        filters=[("date","==",DATE)])
    raw["date"]=pd.to_datetime(raw.date).dt.strftime("%Y-%m-%d")
    sec=pd.read_csv(a.secondary)
    receipt=secondary_audit(sec,raw)
    receipt["source_fingerprints_sha256"]={
        "secondary":hashlib.sha256(Path(a.secondary).read_bytes()).hexdigest(),
        "archive":hashlib.sha256(Path(a.archived_parquet).read_bytes()).hexdigest(),
    }
    path=Path(a.out);path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({k:receipt[k] for k in (
        "status","actual_private_recovery_rows","original_corrupt_rows",
        "secondary_symbols_not_in_corrupt_archive","split_adjusted_price_parity_verified",
        "automatically_replace_canonical_archive")},ensure_ascii=False))
if __name__=="__main__":main()
