from __future__ import annotations

import argparse
import io
import json
import zipfile
from dataclasses import dataclass, asdict

import requests

from audit_ff_2022_archive import parse_ff3_monthly_csv

BASE = (
    "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/"
    "Data_Library/Historical_Archives/{mm}%20{yyyy}%20Update/ftp/"
    "F-F_Research_Data_Factors_CSV.zip"
)

CANDIDATES = [
    (2021, 10),
    (2021, 11),
    (2021, 12),
    (2022, 1),
    (2022, 2),
    (2022, 8),  # positive-control directory already used by the official audit
]


@dataclass
class Probe:
    year: int
    month: int
    url: str
    http_status: int | None
    content_type: str | None
    bytes: int | None
    valid_zip: bool
    last_month: str | None
    has_202111: bool
    error: str | None


def archive_url(year: int, month: int) -> str:
    return BASE.format(mm=f"{month:02d}", yyyy=year)


def probe_one(year: int, month: int, *, timeout: int = 40) -> Probe:
    url = archive_url(year, month)
    try:
        r = requests.get(
            url,
            headers={"User-Agent": "market-top-ff-monthly-archive-probe/1.0"},
            timeout=timeout,
        )
        status = int(r.status_code)
        ctype = r.headers.get("content-type")
        if status != 200:
            return Probe(
                year, month, url, status, ctype, len(r.content),
                False, None, False, None,
            )
        content = r.content
        if content[:2] != b"PK":
            return Probe(
                year, month, url, status, ctype, len(content),
                False, None, False, "HTTP 200 but payload is not ZIP bytes",
            )
        with zipfile.ZipFile(io.BytesIO(content)) as z:
            names = [n for n in z.namelist() if n.lower().endswith(".csv")]
            if not names:
                raise ValueError("ZIP contains no CSV")
            text = z.read(names[0]).decode("utf-8", "replace")
        rows = parse_ff3_monthly_csv(text)
        last = str(rows[-1]["ym"]) if rows else None
        has_target = any(str(x["ym"]) == "202111" for x in rows)
        return Probe(
            year, month, url, status, ctype, len(content),
            True, last, has_target, None,
        )
    except Exception as exc:
        return Probe(
            year, month, url, None, None, None,
            False, None, False, repr(exc),
        )


def run_probe() -> dict:
    rows = [asdict(probe_one(y, m)) for y, m in CANDIDATES]
    positive = next(x for x in rows if x["year"] == 2022 and x["month"] == 8)
    hidden_pre_cutoff = [
        x for x in rows
        if (x["year"], x["month"]) <= (2022, 1)
        and x["valid_zip"]
        and x["has_202111"]
    ]
    return {
        "schema_version": "ff-monthly-official-archive-probe-1",
        "research_only": True,
        "production_effect": "none",
        "candidate_directories": rows,
        "positive_control_2022_08_valid": bool(positive["valid_zip"]),
        "pre_cutoff_official_snapshot_with_202111_found": bool(hidden_pre_cutoff),
        "matching_candidates": hidden_pre_cutoff,
        "interpretation": (
            "Directly probes plausible monthly Kenneth French Historical_Archives "
            "directory names. The 2022-08 archive is a positive control. "
            "A pre-cutoff hit is evidence only if the returned ZIP parses and "
            "contains the 2021-11 FF3 monthly row."
        ),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output")
    args = ap.parse_args()
    result = run_probe()
    print(json.dumps(result, indent=2))
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2)
            f.write("\n")


if __name__ == "__main__":
    main()
