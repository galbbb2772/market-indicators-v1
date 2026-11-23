from __future__ import annotations

import argparse
import json
import re
from html import unescape
from typing import Any

import requests

CDX = "https://web.archive.org/cdx/search/cdx"
CUTOFF = "20220103235959"
TARGET_MONTH = "202111"

PAGES = [
    "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/Data_Library/f-f_factors.html",
    "http://mba.tuck.dartmouth.edu/pages/faculty/ken.french/Data_Library/f-f_factors.html",
    "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/data_library.html",
    "http://mba.tuck.dartmouth.edu/pages/faculty/ken.french/data_library.html",
]


def session() -> requests.Session:
    s = requests.Session()
    s.headers.update({"User-Agent": "market-top-ff-publication-page-audit/1.0"})
    return s


def find_snapshots() -> tuple[list[dict[str, str]], list[str]]:
    s = session()
    rows: list[dict[str, str]] = []
    errors: list[str] = []
    for page in PAGES:
        try:
            r = s.get(
                CDX,
                params={
                    "url": page,
                    "from": "20211201",
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
            header = data[0]
            for item in data[1:]:
                x = dict(zip(header, item))
                ts = str(x.get("timestamp") or "")
                if ts and ts <= CUTOFF:
                    rows.append(x)
        except Exception as exc:
            errors.append(f"{page}: {exc!r}")

    dedup: dict[tuple[str, str, str], dict[str, str]] = {}
    for x in rows:
        key = (
            str(x.get("timestamp")),
            str(x.get("original")),
            str(x.get("digest")),
        )
        dedup[key] = x
    return sorted(dedup.values(), key=lambda x: x["timestamp"], reverse=True), errors


def normalize_html(text: str) -> str:
    text = unescape(text)
    text = re.sub(r"<script\b.*?</script>", " ", text, flags=re.I | re.S)
    text = re.sub(r"<style\b.*?</style>", " ", text, flags=re.I | re.S)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def extract_factor_page_evidence(html: str) -> dict[str, Any]:
    text = normalize_html(html)
    lower = text.lower()

    # Historical versions of the factor description page normally expose
    # "Monthly Returns: July 1926 - <month> <year>". Keep the parser
    # deliberately tolerant to spacing/punctuation while requiring both
    # the Monthly Returns label and a November 2021 terminal month.
    monthly_match = re.search(
        r"monthly\s+returns\s*:?\s*"
        r"(?:july\s+1926\s*[-–—]\s*)?"
        r"([a-z]+)\s+(\d{4})",
        lower,
    )
    terminal = None
    terminal_ym = None
    if monthly_match:
        month_name = monthly_match.group(1).lower()
        year = int(monthly_match.group(2))
        month_map = {
            "january": 1,
            "february": 2,
            "march": 3,
            "april": 4,
            "may": 5,
            "june": 6,
            "july": 7,
            "august": 8,
            "september": 9,
            "october": 10,
            "november": 11,
            "december": 12,
        }
        month = month_map.get(month_name)
        if month is not None:
            terminal = f"{month_name.title()} {year}"
            terminal_ym = f"{year:04d}{month:02d}"

    target_visible = bool(
        terminal_ym is not None
        and terminal_ym >= TARGET_MONTH
    )

    has_factor_identity = (
        "description of fama/french factors" in lower
        or (
            "fama/french" in lower
            and "smb" in lower
            and "hml" in lower
        )
    )

    archive_link_visible = bool(
        re.search(
            r"12(?:%20|\s)+2021(?:%20|\s)+update",
            html,
            flags=re.I,
        )
    )

    return {
        "has_factor_identity": has_factor_identity,
        "monthly_returns_terminal": terminal,
        "monthly_returns_terminal_ym": terminal_ym,
        "target_202111_publication_visible": target_visible,
        "dec2021_archive_link_visible": archive_link_visible,
    }


def download_snapshot(snapshot: dict[str, str]) -> dict[str, Any]:
    s = session()
    ts = snapshot["timestamp"]
    original = snapshot["original"]
    url = f"https://web.archive.org/web/{ts}id_/{original}"
    r = s.get(url, timeout=60)
    r.raise_for_status()
    evidence = extract_factor_page_evidence(r.text)
    return {
        "timestamp": ts,
        "original": original,
        "digest": snapshot.get("digest"),
        "mimetype": snapshot.get("mimetype"),
        "bytes": len(r.content),
        **evidence,
    }


def run_audit() -> dict[str, Any]:
    snaps, query_errors = find_snapshots()
    attempts: list[dict[str, Any]] = []
    recovered = None

    for snap in snaps:
        try:
            row = download_snapshot(snap)
            attempts.append(row)
            if (
                row["has_factor_identity"]
                and row["target_202111_publication_visible"]
            ):
                recovered = row
                break
        except Exception as exc:
            attempts.append(
                {
                    "timestamp": snap.get("timestamp"),
                    "original": snap.get("original"),
                    "error": repr(exc),
                }
            )

    status = (
        "PRE_CUTOFF_PUBLICATION_PAGE_PROVES_202111"
        if recovered is not None
        else "NO_PRE_CUTOFF_PUBLICATION_PAGE_PROOF"
    )

    return {
        "schema_version": "route-b-2022-ff-publication-page-wayback-audit-1",
        "research_only": True,
        "production_effect": "none",
        "cutoff": CUTOFF,
        "target_month": TARGET_MONTH,
        "status": status,
        "publication_time_202111_independently_proven": recovered is not None,
        "snapshot_count": len(snaps),
        "recovered_snapshot": recovered,
        "attempts": attempts,
        "query_errors": query_errors,
        "interpretation": (
            "This audit asks only whether an official Ken French page captured "
            "before the 2022-01-03 cutoff independently showed the FF3 monthly "
            "series through November 2021. It does not claim the exact ZIP bytes "
            "were archived."
        ),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output")
    args = ap.parse_args()
    result = run_audit()
    print(json.dumps(result, indent=2))
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2)
            f.write("\n")


if __name__ == "__main__":
    main()
