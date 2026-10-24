"""MarketParquet historical stock_daily authorized archive recovery (RESEARCH ONLY).

No charge or purchase, login bypass, source imputation, or production snapshot
changes. Requires pre-existing, user-authorized MARKETPARQUET_API_KEY.
Does not assert date-PIT common-stock security identity/FIGI or original V2.1.8
model correctness merely because all daily stock price bars were downloaded.

Usage:
  MARKETPARQUET_API_KEY=... python -m research.v218_full_archive_ingest \
    --start 2000-01-01 --end 2026-10-22 --root private-data/v218_stock_daily

  # Use --manifest-only to inspect entitlement/coverage before bulk download.
"""
from __future__ import annotations
import argparse,csv,hashlib,io,json,os,re,time
from datetime import date,datetime,timezone
from pathlib import Path
from urllib.parse import urlsplit
import requests

BASE="https://marketparquet.com/api/v1"
STATUS_REQUIRES_ID="REAL_STOCK_BARS_RECOVERED_BUT_PIT_SECURITY_IDENTITY_NOT_PROVEN"


def safe_filename(dt:str)->str:
    date.fromisoformat(dt)
    return f"stock_daily_{dt}.parquet"


def authorize_manifest(session:requests.Session,start:str,end:str,key:str)->list[dict]:
    if not key:raise RuntimeError("BLOCKED_NO_AUTHORIZED_MARKETPARQUET_API_KEY")
    r=session.get(BASE+"/manifest/stock_daily",params={"start":start,"end":end},
        headers={"Authorization":"Bearer "+key},timeout=90)
    if r.status_code in (401,403):
        raise RuntimeError("BLOCKED_PROVIDER_ACCESS_OR_ARCHIVE_ENTITLEMENT")
    r.raise_for_status()
    files=(r.json() or {}).get("files") or []
    if not files:raise RuntimeError("BLOCKED_EMPTY_AUTHORIZED_HISTORICAL_STOCK_MANIFEST")
    out=[];seen=set()
    for item in files:
        d=item.get("date")
        if not isinstance(d,str):raise ValueError("manifest date absent")
        date.fromisoformat(d)
        if not start<=d<=end:raise ValueError("manifest contains date outside requested period")
        if d in seen:raise ValueError("manifest duplicate trading date")
        seen.add(d)
        url=item.get("download_url")
        if not isinstance(url,str) or not url.startswith("https://"):
            raise ValueError("manifest missing https download URL")
        if urlsplit(url).hostname not in ("marketparquet.com","www.marketparquet.com"):
            # Avoid credential exfiltration; never forward Authorization to item URLs.
            # Some archives use signed CDN URLs; require explicit review before allowing.
            raise ValueError("unapproved third-party archive host")
        out.append({"date":d,"url":url,"filename":safe_filename(d)})
    return sorted(out,key=lambda x:x["date"])


def read_verify_stock_parquet(blob:bytes,dt:str)->dict:
    if not (blob.startswith(b"PAR1") and blob.endswith(b"PAR1")):
        raise ValueError("download bytes are not parquet")
    import pandas as pd
    frame=pd.read_parquet(io.BytesIO(blob),columns=["date","symbol","close","asset_type"])
    if frame.empty or len(frame)<1000:raise ValueError("stock_daily incomplete day")
    d=pd.to_datetime(frame["date"],errors="raise").dt.strftime("%Y-%m-%d")
    if not d.eq(dt).all():raise ValueError("download trading date mismatch")
    if not frame["symbol"].notna().all() or frame["symbol"].duplicated().any():
        raise ValueError("missing/duplicate stock symbol")
    if not frame["asset_type"].astype(str).str.lower().eq("stock").all():
        raise ValueError("ETF/futures labels in stock partition")
    c=pd.to_numeric(frame["close"],errors="coerce")
    if c.isna().any() or c.le(0).any():raise ValueError("invalid security close")
    return {"date":dt,"rows":len(frame),"symbols":frame.symbol.nunique(),
        "sha256":hashlib.sha256(blob).hexdigest()}


def download_one(session:requests.Session,url:str,destination:Path,dt:str)->dict:
    if destination.exists():
        data=destination.read_bytes()
        try:
            receipt=read_verify_stock_parquet(data,dt)
            receipt["cached_and_rechecked"]=True
            return receipt
        except (ValueError,KeyError,Exception) as exc:
            # Bad cache is not trusted; re-download but do not mask repeated error.
            destination.unlink()
    for attempt in range(5):
        try:
            response=session.get(url,timeout=120)
            if response.status_code in (401,403):
                raise RuntimeError("BLOCKED_PROVIDER_FULL_HISTORY_DOWNLOAD_ACCESS")
            if response.status_code in (429,500,502,503,504):
                retry_header=response.headers.get("Retry-After")
                try:delay=float(retry_header) if retry_header else 2**attempt
                except ValueError:delay=2**attempt
                time.sleep(min(max(delay,1),60))
                continue
            response.raise_for_status()
            receipt=read_verify_stock_parquet(response.content,dt)
            tmp=destination.with_suffix(".part")
            tmp.write_bytes(response.content)
            tmp.replace(destination)
            receipt["cached_and_rechecked"]=False
            return receipt
        except requests.RequestException as e:
            if attempt==4:raise RuntimeError(f"transport failed on {dt}: {type(e).__name__}") from None
            time.sleep(min(2**attempt,30))
    raise RuntimeError(f"provider failed after retries on {dt}")


def run(start:str,end:str,root:Path,manifest_only:bool=False,
        expected_calendar:Path|None=None)->dict:
    date.fromisoformat(start);date.fromisoformat(end)
    if end<start:raise ValueError("start>end")
    key=os.environ.get("MARKETPARQUET_API_KEY","").strip()
    session=requests.Session();session.headers.update({"User-Agent":"V218FullArchiveSourceQA/1.0"})
    items=authorize_manifest(session,start,end,key)
    dates=[r["date"] for r in items]
    missing=[]
    if expected_calendar is not None:
        import pandas as pd
        f=pd.read_csv(expected_calendar)
        if "date" not in f:raise ValueError("expected_calendar missing date")
        expected=set(str(v)[:10] for v in f["date"] if start<=str(v)[:10]<=end)
        missing=sorted(expected-set(dates))
        if missing:raise RuntimeError(f"HISTORICAL_MARKET_SESSIONS_MISSING_FROM_MANIFEST: {len(missing)} first={missing[:8]}")
    result={"status":"MANIFEST_ONLY_ARCHIVE_SCOPE_UNVERIFIED" if manifest_only else STATUS_REQUIRES_ID,
        "date_start":start,"date_end":end,"manifest_days":len(items),
        "first_available":dates[0],"last_available":dates[-1],
        "missing_known_market_sessions":missing,
        "will_not_modify_production_snapshot":True,
        "permanent_security_id_and_delisted_point_in_time_verified":False,
        "full_frozen_model_validation_done":False,
        "not_a_purchase_or_billing_action":True}
    root.mkdir(parents=True,exist_ok=True)
    (root/"authorized_archive_receipt.json").write_text(json.dumps(result,indent=2)+"\n")
    if manifest_only:return result
    receipts=[];stock_dir=root/"stock_daily";stock_dir.mkdir(exist_ok=True)
    for i,item in enumerate(items,1):
        data=download_one(session,item["url"],stock_dir/item["filename"],item["date"])
        receipts.append(data)
        if i%50==0:print("verified_stock_days",i,"of",len(items),flush=True)
    with (root/"authorized_stock_days.csv").open("w",newline="") as f:
        w=csv.DictWriter(f,fieldnames=receipts[0].keys());w.writeheader();w.writerows(receipts)
    result["verified_days"]=len(receipts)
    result["verified_stock_bars"]=sum(x["rows"] for x in receipts)
    result["per_day_sha256_recorded"]=True
    (root/"authorized_archive_receipt.json").write_text(json.dumps(result,indent=2)+"\n")
    return result


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--start",required=True)
    p.add_argument("--end",required=True)
    p.add_argument("--root",type=Path,required=True)
    p.add_argument("--manifest-only",action="store_true")
    p.add_argument("--expected-calendar",type=Path,default=None)
    a=p.parse_args()
    result=run(a.start,a.end,a.root,a.manifest_only,a.expected_calendar)
    print(json.dumps(result,ensure_ascii=False,indent=2))
