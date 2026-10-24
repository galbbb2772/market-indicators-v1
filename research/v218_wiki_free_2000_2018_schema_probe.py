"""Probe Kaggle's public WIKI/PRICES mirror (larger 3,199-ticker candidate).

A feasibility and schema audit, not another V2.1.8 all-US score, and never
writes to production or redistributes the historical vendor prices.

Kaggle's official kagglehub client permits downloading ordinary public
resources without a token. If this resource requires user consent or auth,
fail visibly instead of circumventing it.
"""
from __future__ import annotations
import argparse,hashlib,json
from datetime import datetime,timezone
from pathlib import Path

HANDLE="marketneutral/quandl-wiki-prices-us-equites"
RESULT="WIKI_1962_2018_DOWNLOADED_SCHEMA_ONLY_PIT_STILL_UNCERTIFIED"


def snapshot_files(root:Path)->list[dict]:
    result=[]
    for p in sorted(root.rglob("*")):
        if not p.is_file():continue
        result.append({"name":p.relative_to(root).as_posix(),"size_bytes":p.stat().st_size})
    return result


def inspect(root:Path)->dict:
    files=snapshot_files(root)
    if not files:raise ValueError("Kaggle dataset was downloaded but no usable files found")
    candidates=[x for x in files if x["name"].lower().endswith((".csv",".csv.gz",".parquet",".pq"))]
    if not candidates:raise ValueError("Kaggle dataset has no recognized structured EOD price file")
    import pandas as pd
    probes=[]
    for info in candidates:
        p=root/info["name"];name=p.name.lower()
        try:
            if name.endswith((".parquet",".pq")):
                import pyarrow.parquet as pq
                f=pq.ParquetFile(p)
                columns=f.schema.names
                n=f.metadata.num_rows
                head=next(f.iter_batches(batch_size=3)).to_pandas()
            else:
                head=pd.read_csv(p,nrows=3)
                columns=list(head.columns)
                n=None
            lower=[str(z).lower().replace(" ","_") for z in columns]
            has_prices=any(z in lower for z in ("close","adj_close","adjusted_close"))
            has_symbol=any(z in lower for z in ("ticker","symbol"))
            has_date=any(z in lower for z in ("date","timestamp"))
            status="SCHEMA_RELEVANT" if all((has_prices,has_symbol,has_date)) else "SCHEMA_NOT_RELEVANT"
            probes.append({"name":info["name"],"bytes":info["size_bytes"],"columns":columns,
                           "rows_metadata":n,"status":status,
                           "first_three_date_values_redacted":True})
        except Exception as exc:
            probes.append({"name":info["name"],"bytes":info["size_bytes"],
                           "status":"UNREADABLE","error_type":type(exc).__name__})
    if not any(x["status"]=="SCHEMA_RELEVANT" for x in probes):
        raise ValueError("No Kaggle historical price file has expected ticker/date/price")
    return {
        "schema":"v218-wiki-public-mirror-schema-audit-v1",
        "status":RESULT,"dataset_handle":HANDLE,
        "asof_utc":datetime.now(timezone.utc).isoformat(),
        "files":files,"prices":probes,
        "real_prices_actually_scored":False,
        "full_all_US_delisted_stock_universe_PIT_proven":False,
        "data_ingested_into_approved_2019_2026_history":False,
        "requires_further_validation":["1962-2018 historical coverage and number of distinct securities",
            "no hidden current-constituent survivorship filter",
            "split vs dividend-adjusted prices consistent with frozen source",
            "daily identifier reuse and former delisted listing identity",
            "no full all-US market universe coverage implied by 3,199 names"]}


def main()->None:
    p=argparse.ArgumentParser()
    p.add_argument("--outdir",default="research/out/v218_wiki_public_probe")
    a=p.parse_args()
    import kagglehub
    try:
        root=Path(kagglehub.dataset_download(HANDLE))
    except Exception as exc:
        raise RuntimeError("WIKI_KAGGLE_PUBLIC_ACCESS_NOT_AVAILABLE: "+type(exc).__name__) from None
    result=inspect(root)
    dest=Path(a.outdir);dest.mkdir(parents=True,exist_ok=True)
    (dest/"schema_audit.json").write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps({"status":result["status"],"structured":result["prices"],
                      "raw_data_not_uploaded":True}))


if __name__=="__main__":main()
