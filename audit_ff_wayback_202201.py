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


def find_snapshots() -> tuple[list[dict], list[str]]:
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
    candidates = sorted(candidates, key=lambda x: x["timestamp"], reverse=True)
    return candidates, errors


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

    snaps, errors = find_snapshots()
    attempts = []
    recovered = None

    for snap in snaps:
        try:
            member, text = download_snapshot(snap)
            rows = parse_ff3_monthly_csv(text)
            last_month = str(rows[-1]["ym"]) if rows else None
            has_target = any(str(x["ym"]) == "202111" for x in rows)
            attempts.append(
                {
                    "timestamp": snap["timestamp"],
                    "original": snap["original"],
                    "digest": snap.get("digest"),
                    "mimetype": snap.get("mimetype"),
                    "last_month": last_month,
                    "has_202111": has_target,
                    "zip_member": member,
                }
            )
            if has_target:
                recovered = (snap, member, text)
                break
        except Exception as exc:
            attempts.append(
                {
                    "timestamp": snap.get("timestamp"),
                    "original": snap.get("original"),
                    "digest": snap.get("digest"),
                    "mimetype": snap.get("mimetype"),
                    "error": repr(exc),
                }
            )

    if recovered is not None:
        snap, member, text = recovered
        result = audit(text)
        result.update(
            {
                "schema_version": "route-b-2022-wayback-vintage-audit-1",
                "status": "RECOVERED_PRE_CUTOFF_SNAPSHOT_WITH_202111",
                "wayback_timestamp": snap["timestamp"],
                "wayback_original": snap["original"],
                "wayback_mimetype": snap.get("mimetype"),
                "wayback_digest": snap.get("digest"),
                "zip_member": member,
                "exact_or_pre_cutoff_vintage": True,
                "cutoff": CUTOFF,
                "attempts": attempts,
                "errors": errors,
                "interpretation": (
                    "Wayback snapshot of the Ken French factor ZIP captured no later "
                    "than 2022-01-03 23:59:59 UTC and containing 2021-11."
                ),
            }
        )
    else:
        usable = [x for x in attempts if x.get("last_month")]
        latest_ts = max(
            (str(x.get("timestamp")) for x in usable),
            default=None,
        )
        latest_variants = [
            x for x in usable
            if latest_ts is not None and str(x.get("timestamp")) == latest_ts
        ]
        latest_max_last_month = max(
            (str(x.get("last_month")) for x in latest_variants),
            default=None,
        )
        result = {
            "schema_version": "route-b-2022-wayback-vintage-audit-2",
            "status": "NO_PRE_CUTOFF_SNAPSHOT_WITH_202111",
            "cutoff": CUTOFF,
            "exact_or_pre_cutoff_vintage": False,
            "snapshot_count": len(snaps),
            "attempts": attempts,
            "errors": errors,
            "latest_usable_capture_timestamp": latest_ts,
            "latest_usable_variants": latest_variants,
            "latest_usable_max_last_month": latest_max_last_month,
            "interpretation": (
                "Wayback snapshots of the Ken French ZIP were reachable, but no "
                "snapshot captured on/before 2022-01-03 contained the 2021-11 "
                "monthly row required by the frozen publication-lag replay. "
                "Multiple archived digests may share one capture timestamp; "
                "coverage is summarized by the maximum last_month across all "
                "usable variants at the latest timestamp."
            ),
        }

    print(json.dumps(result, indent=2))
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2)
            f.write("\n")


if __name__ == "__main__":
    main()
