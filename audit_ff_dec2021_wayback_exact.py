from __future__ import annotations

import argparse
import hashlib
import io
import json
import zipfile

import requests

from audit_ff_2022_archive import parse_ff3_monthly_csv

CUTOFF = "20220103235959"
TARGET_SHA256 = "e3c1eb5dd56764be0ed851ef1c7cedb48fab895bc24302c932a15d8474938d86"
TARGET_MONTH = "202111"
URLS = [
    "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/Data_Library/Historical_Archives/12%202021%20Update/ftp/F-F_Research_Data_Factors_CSV.zip",
    "http://mba.tuck.dartmouth.edu/pages/faculty/ken.french/Data_Library/Historical_Archives/12%202021%20Update/ftp/F-F_Research_Data_Factors_CSV.zip",
]
CDX = "https://web.archive.org/cdx/search/cdx"


def session() -> requests.Session:
    s=requests.Session()
    s.headers.update({"User-Agent":"market-top-ff-dec2021-wayback-audit/1.0"})
    return s


def find() -> tuple[list[dict], list[str]]:
    s=session()
    out=[]
    errors=[]
    for url in URLS:
        try:
            r=s.get(
                CDX,
                params={
                    "url":url,
                    "to":"20220103",
                    "output":"json",
                    "fl":"timestamp,original,statuscode,mimetype,digest",
                    "filter":"statuscode:200",
                    "collapse":"digest",
                },
                timeout=30,
            )
            r.raise_for_status()
            data=r.json()
            if data and len(data)>1:
                hdr=data[0]
                for row in data[1:]:
                    x=dict(zip(hdr,row))
                    ts=str(x.get("timestamp") or "")
                    if ts and ts<=CUTOFF:
                        out.append(x)
        except Exception as exc:
            errors.append(f"{url}: {exc!r}")
    dedup={}
    for x in out:
        dedup[(str(x.get("timestamp")),str(x.get("digest")))] = x
    return sorted(dedup.values(),key=lambda x:x["timestamp"],reverse=True),errors


def inspect_snapshot(x: dict) -> dict:
    ts=x["timestamp"]; original=x["original"]
    raw=f"https://web.archive.org/web/{ts}id_/{original}"
    r=session().get(raw,timeout=60)
    r.raise_for_status()
    content=r.content
    sha=hashlib.sha256(content).hexdigest()
    if content[:2] != b"PK":
        raise ValueError("captured payload is not ZIP")
    with zipfile.ZipFile(io.BytesIO(content)) as z:
        names=[n for n in z.namelist() if n.lower().endswith(".csv")]
        if not names:
            raise ValueError("ZIP has no CSV")
        text=z.read(names[0]).decode("utf-8","replace")
    rows=parse_ff3_monthly_csv(text)
    header=[
        line.strip() for line in text.splitlines()[:20]
        if "CRSP database" in line or "Copyright" in line
    ]
    return {
        "timestamp":ts,
        "original":original,
        "sha256":sha,
        "matches_current_official_archive_sha256": sha == TARGET_SHA256,
        "last_month":str(rows[-1]["ym"]),
        "has_202111":any(str(r["ym"])==TARGET_MONTH for r in rows),
        "header":header,
    }


def run() -> dict:
    snaps,errors=find()
    inspected=[]
    for x in snaps:
        try:
            inspected.append(inspect_snapshot(x))
        except Exception as exc:
            inspected.append({
                "timestamp":x.get("timestamp"),
                "original":x.get("original"),
                "error":repr(exc),
            })
    valid=[
        x for x in inspected
        if x.get("has_202111") and x.get("last_month") >= TARGET_MONTH
    ]
    exact=[
        x for x in valid
        if x.get("matches_current_official_archive_sha256")
    ]
    if exact:
        status="EXACT_DEC2021_ARCHIVE_BYTES_CAPTURED_PRE_CUTOFF"
    elif valid:
        status="PRE_CUTOFF_DEC2021_VINTAGE_CAPTURED_DIFFERENT_BYTES"
    else:
        status="NO_PRE_CUTOFF_CAPTURE_OF_DEC2021_ARCHIVE_URL"
    return {
        "schema_version":"ff-dec2021-wayback-exact-url-audit-1",
        "research_only":True,
        "production_effect":"none",
        "cutoff":CUTOFF,
        "status":status,
        "snapshot_count":len(snaps),
        "errors":errors,
        "inspected":inspected,
        "exact_sha_capture_found":bool(exact),
        "pre_cutoff_vintage_capture_found":bool(valid),
        "interpretation":(
            "Checks the exact official December-2021 Historical_Archives URL, "
            "not the generic live Ken French ZIP URL. A matching SHA would prove "
            "the currently recovered bytes were archived before the cutoff; a "
            "different valid 202111 vintage would still prove pre-cutoff delivery "
            "of that vintage family."
        ),
    }


def main() -> None:
    ap=argparse.ArgumentParser()
    ap.add_argument("--output")
    args=ap.parse_args()
    result=run()
    print(json.dumps(result,indent=2))
    if args.output:
        with open(args.output,"w",encoding="utf-8") as f:
            json.dump(result,f,indent=2)
            f.write("\n")


if __name__=="__main__":
    main()
