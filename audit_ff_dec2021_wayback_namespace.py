from __future__ import annotations

import argparse
import json
import time
from urllib.parse import unquote

import requests

CDX = "https://web.archive.org/cdx/search/cdx"
CUTOFF = "20220103235959"

PREFIXES = [
    "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/Data_Library/Historical_Archives/12%202021%20Update/",
    "http://mba.tuck.dartmouth.edu/pages/faculty/ken.french/Data_Library/Historical_Archives/12%202021%20Update/",
    "https://mba.tuck.dartmouth.edu/pages/Faculty/ken.french/Data_Library/Historical_Archives/12%202021%20Update/",
    "http://mba.tuck.dartmouth.edu/pages/Faculty/ken.french/Data_Library/Historical_Archives/12%202021%20Update/",
]


def session() -> requests.Session:
    s = requests.Session()
    s.headers.update({
        "User-Agent": "market-top-ff-dec2021-namespace-wayback-audit/1.0"
    })
    return s


def _is_target_namespace(url: str) -> bool:
    x = unquote(str(url)).lower()
    return (
        "mba.tuck.dartmouth.edu/pages/faculty/ken.french/"
        "data_library/historical_archives/12 2021 update/"
    ) in x


def _query_prefix(
    s: requests.Session,
    prefix: str,
    *,
    attempts: int = 2,
    timeout: int = 45,
) -> tuple[list | None, str | None]:
    """Query one CDX prefix with bounded retry.

    The audit remains fail-closed: if every attempt fails, the caller records
    a query error and CI rejects the coverage conclusion. Retrying only avoids
    turning one transient Wayback timeout into a false negative.
    """
    last: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            r = s.get(
                CDX,
                params={
                    "url": prefix,
                    "matchType": "prefix",
                    "from": "2021",
                    "to": "20220103",
                    "output": "json",
                    "fl": (
                        "timestamp,original,statuscode,mimetype,digest,length"
                    ),
                    "filter": "statuscode:200",
                    "collapse": "digest",
                },
                timeout=timeout,
            )
            r.raise_for_status()
            return r.json(), None
        except Exception as exc:
            last = exc
            if attempt < attempts:
                time.sleep(2)

    return None, f"{prefix}: {last!r}"


def find_namespace_captures() -> tuple[list[dict], list[str]]:
    s = session()
    captures: list[dict] = []
    errors: list[str] = []

    for prefix in PREFIXES:
        data, error = _query_prefix(s, prefix)
        if error is not None:
            errors.append(error)
            continue
        if not data or len(data) < 2:
            continue
        hdr = data[0]
        for row in data[1:]:
            x = dict(zip(hdr, row))
            ts = str(x.get("timestamp") or "")
            original = str(x.get("original") or "")
            if (
                ts
                and ts <= CUTOFF
                and _is_target_namespace(original)
            ):
                captures.append(x)

    dedup: dict[tuple[str, str, str], dict] = {}
    for x in captures:
        key = (
            str(x.get("timestamp")),
            str(x.get("original")),
            str(x.get("digest")),
        )
        dedup[key] = x

    return (
        sorted(
            dedup.values(),
            key=lambda x: (
                str(x.get("timestamp")),
                str(x.get("original")),
            ),
            reverse=True,
        ),
        errors,
    )


def run() -> dict:
    captures, errors = find_namespace_captures()

    status = (
        "PRE_CUTOFF_DEC2021_NAMESPACE_CAPTURE_FOUND"
        if captures
        else "NO_PRE_CUTOFF_DEC2021_NAMESPACE_CAPTURE"
    )

    originals = sorted({str(x.get("original")) for x in captures})
    return {
        "schema_version": "ff-dec2021-wayback-namespace-audit-1",
        "research_only": True,
        "production_effect": "none",
        "cutoff": CUTOFF,
        "status": status,
        "query_errors": errors,
        "capture_count": len(captures),
        "captures": captures,
        "unique_originals": originals,
        "namespace_pre_cutoff_delivery_evidence": bool(captures),
        "interpretation": (
            "Queries the full Kenneth French Historical_Archives/12 2021 "
            "Update namespace with Wayback CDX prefix matching. Any qualifying "
            "capture would independently prove that at least one resource in "
            "that official December-2021 archive namespace was publicly "
            "reachable before the 2022-01-03 cutoff. No capture does not prove "
            "non-publication; it preserves an archive-coverage gap."
        ),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output")
    args = ap.parse_args()
    result = run()
    print(json.dumps(result, indent=2))
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2)
            f.write("\n")


if __name__ == "__main__":
    main()
