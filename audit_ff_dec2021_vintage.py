from __future__ import annotations

import argparse
import hashlib
import io
import json
import zipfile

import requests

from audit_ff_2022_archive import parse_ff3_monthly_csv
from market_top_canonical_inputs import size_weakness_history
from policyshock_v211 import route_b

URL = (
    "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/"
    "Data_Library/Historical_Archives/12%202021%20Update/ftp/"
    "F-F_Research_Data_Factors_CSV.zip"
)
TARGET_MONTH = "202111"
VALUATION_PRE_CUTOFF = 98.57904085257549
POLICY_SHOCK_PRIMARY_PIT = 74.38861925775049
THRESHOLD = 85.0


def download() -> tuple[bytes, dict[str, str]]:
    r = requests.get(
        URL,
        headers={"User-Agent": "market-top-ff-dec2021-vintage-audit/1.0"},
        timeout=45,
    )
    r.raise_for_status()
    return r.content, {
        "content_type": r.headers.get("content-type") or "",
        "last_modified": r.headers.get("last-modified") or "",
        "etag": r.headers.get("etag") or "",
    }


def audit(content: bytes, headers: dict[str, str] | None = None) -> dict:
    if content[:2] != b"PK":
        raise ValueError("official December-2021 payload is not ZIP bytes")
    with zipfile.ZipFile(io.BytesIO(content)) as z:
        names = [n for n in z.namelist() if n.lower().endswith(".csv")]
        if not names:
            raise ValueError("official December-2021 ZIP contains no CSV")
        member = names[0]
        text = z.read(member).decode("utf-8", "replace")

    header_lines = [
        line.strip()
        for line in text.splitlines()[:20]
        if "CRSP database" in line or "Copyright" in line
    ]
    rows = parse_ff3_monthly_csv(text)
    last_month = str(rows[-1]["ym"])
    if last_month != TARGET_MONTH:
        raise ValueError(
            f"December-2021 vintage expected last month {TARGET_MONTH}, got {last_month}"
        )

    target_i = next(i for i, x in enumerate(rows) if str(x["ym"]) == TARGET_MONTH)
    truncated = rows[: target_i + 1]
    smb = [float(x["smb"]) for x in truncated]
    size_scores = size_weakness_history(smb)
    size = size_scores[-1]
    if size is None:
        raise ValueError("SizeWeakness missing")

    six = truncated[-6:]
    rb = route_b(VALUATION_PRE_CUTOFF, POLICY_SHOCK_PRIMARY_PIT, float(size))
    if rb is None:
        raise ValueError("Route_B missing")

    critical_size = (
        THRESHOLD**3 / (VALUATION_PRE_CUTOFF * POLICY_SHOCK_PRIMARY_PIT)
    )
    return {
        "schema_version": "route-b-2022-ff-dec2021-official-vintage-audit-1",
        "status": "PASS_OFFICIAL_DEC2021_VINTAGE",
        "research_only": True,
        "production_effect": "none",
        "source": "Kenneth R. French official Historical_Archives December 2021 Update",
        "url": URL,
        "target_month": TARGET_MONTH,
        "last_month": last_month,
        "zip_member": member,
        "vintage_header_lines": header_lines,
        "zip_sha256": hashlib.sha256(content).hexdigest(),
        "http_headers": headers or {},
        "smb_202106_to_202111": [
            {"ym": str(x["ym"]), "smb": float(x["smb"])} for x in six
        ],
        "size_weakness": float(size),
        "valuation_pre_cutoff": VALUATION_PRE_CUTOFF,
        "policy_shock_primary_pit": POLICY_SHOCK_PRIMARY_PIT,
        "route_b": float(rb),
        "threshold": THRESHOLD,
        "passes": bool(rb >= THRESHOLD),
        "critical_size_weakness": float(critical_size),
        "size_margin_above_critical": float(size - critical_size),
        "route_margin_above_threshold": float(rb - THRESHOLD),
        "evidence_interpretation": (
            "Uses the official December 2021 Historical_Archives factor ZIP whose "
            "monthly table ends at 2021-11. This closes the factor-vintage content "
            "gap for the frozen publication-lag input. HTTP metadata is recorded "
            "separately and must not be overinterpreted as publication-time proof."
        ),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output")
    args = ap.parse_args()
    content, headers = download()
    result = audit(content, headers)
    print(json.dumps(result, indent=2))
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2)
            f.write("\n")


if __name__ == "__main__":
    main()
