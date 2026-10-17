from __future__ import annotations

import argparse
import io
import json
import zipfile
from datetime import datetime

import requests

from audit_ff_2022_archive import audit, parse_ff3_monthly_csv

ORIGINAL_URLS = [
    "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/F-F_Research_Data_Factors_CSV.zip",
    "http://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/F-F_Research_Data_Factors_CSV.zip",
]
CDX = "https://web.archive.org/cdx/search/cdx"
CUTOFF = "20220103235959"


def session() -> requests.Session:
    s = requests.Session()
    s.headers.update({"User-Agent": "market-top-wayback-vintage-audit/1.0"})
    return s


def find_latest_snapshot() -> dict:
    s = session()
    candidates: list[dict] = []
    errors: list[str] = []
    for original in ORIGINAL_URLS:
        try:
            r = s.get(
                CDX,
                params={
                    "url": original,
                    "from": "2020",
                    "to": "20220103",
                    "output": "json",
                    "fl": "timestamp,original,statuscode,mimetype,digest",
                    "filter": "statuscode:200",
                    "collapse": "digest",
                },
                timeout=30,
            )
            r.raise_for_status()
            data = r.json()
            if not data or len(data) < 2:
                continue
            hdr = data[0]
            for row in data[1:]:
                x = dict(zip(hdr, row))
                ts = str(x.get("timestamp") or "")
                if ts and ts <= CUTOFF:
                    candidates.append(x)
        except Exception as exc:
            errors.append(f"{original}: {exc!r}")
    if not candidates:
        raise RuntimeError("No pre-2022-01-03 Wayback snapshot found; " + "; ".join(errors))
    return max(candidates, key=lambda x: x["timestamp"])


def download_snapshot(snapshot: dict) -> tuple[str, str]:
    s = session()
    ts = snapshot["timestamp"]
    original = snapshot["original"]
    raw_url = f"https://web.archive.org/web/{ts}id_/{original}"
    r = s.get(raw_url, timeout=60)
    r.raise_for_status()
    content = r.content

    if content[:2] != b"PK":
        raise ValueError(
            f"Wayback snapshot is not ZIP bytes; content-type={r.headers.get('content-type')}, "
            f"prefix={content[:80]!r}"
        )
    with zipfile.ZipFile(io.BytesIO(content)) as z:
        names = [n for n in z.namelist() if n.lower().endswith(".csv")]
        if not names:
            raise ValueError("Wayback ZIP contains no CSV")
        name = names[0]
        text = z.read(name).decode("utf-8", "replace")
    parse_ff3_monthly_csv(text)
    return name, text


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output")
    args = ap.parse_args()

    snap = find_latest_snapshot()
    member, text = download_snapshot(snap)
    result = audit(text)
    result.update(
        {
            "schema_version": "route-b-2022-wayback-vintage-audit-1",
            "wayback_timestamp": snap["timestamp"],
            "wayback_original": snap["original"],
            "wayback_mimetype": snap.get("mimetype"),
            "wayback_digest": snap.get("digest"),
            "zip_member": member,
            "exact_or_pre_cutoff_vintage": True,
            "cutoff": CUTOFF,
            "interpretation": (
                "Wayback snapshot of the Ken French factor ZIP captured no later "
                "than 2022-01-03 23:59:59 UTC. This is the closest recoverable "
                "web-published vintage evidence."
            ),
        }
    )
    print(json.dumps(result, indent=2))
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2)
            f.write("\n")


if __name__ == "__main__":
    main()
