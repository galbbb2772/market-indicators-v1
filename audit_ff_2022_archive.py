from __future__ import annotations

import argparse
import io
import json
import zipfile

import requests

from market_top_canonical_inputs import size_weakness_history
from policyshock_v211 import route_b

ARCHIVE_URL = (
    "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/"
    "Data_Library/Historical_Archives/08%202022%20Update/ftp/"
    "F-F_Research_Data_Factors_CSV.zip"
)

VALUATION_2021_11 = 98.5807214666
POLICY_SHOCK_2022_01_03 = 74.3886192578
ROUTE_B_THRESHOLD = 85.0
TARGET_MONTH = "202111"


def parse_ff3_monthly_csv(text: str) -> list[dict[str, float | str]]:
    rows: list[dict[str, float | str]] = []
    started = False
    for raw in text.splitlines():
        p = [x.strip() for x in raw.split(",")]
        if p and p[0].isdigit() and len(p[0]) == 6:
            started = True
            if len(p) < 5:
                continue
            try:
                rows.append(
                    {
                        "ym": p[0],
                        "mkt_rf": float(p[1]),
                        "smb": float(p[2]),
                        "hml": float(p[3]),
                        "rf": float(p[4]),
                    }
                )
            except ValueError:
                continue
        elif started and rows:
            break
    if len(rows) < 500:
        raise ValueError(f"parsed monthly block too short: {len(rows)}")
    return rows


def download_archive(url: str = ARCHIVE_URL) -> tuple[str, str]:
    r = requests.get(
        url,
        headers={"User-Agent": "market-top-vintage-audit/1.0"},
        timeout=45,
    )
    r.raise_for_status()
    with zipfile.ZipFile(io.BytesIO(r.content)) as z:
        names = [n for n in z.namelist() if n.lower().endswith(".csv")]
        if not names:
            raise ValueError("Ken French archive ZIP contains no CSV")
        name = names[0]
        text = z.read(name).decode("utf-8", "replace")
    return name, text


def audit(text: str) -> dict:
    rows = parse_ff3_monthly_csv(text)
    target_i = next((i for i, x in enumerate(rows) if x["ym"] == TARGET_MONTH), None)
    if target_i is None:
        raise ValueError(f"{TARGET_MONTH} not found")
    if target_i < 5:
        raise ValueError("not enough SMB months")

    truncated = rows[: target_i + 1]
    smb = [float(x["smb"]) for x in truncated]
    scores = size_weakness_history(smb)
    size = scores[-1]
    if size is None:
        raise ValueError("SizeWeakness missing")

    six = truncated[-6:]
    rb = route_b(VALUATION_2021_11, POLICY_SHOCK_2022_01_03, float(size))
    if rb is None:
        raise ValueError("Route_B missing")

    critical_size = (
        ROUTE_B_THRESHOLD**3
        / (VALUATION_2021_11 * POLICY_SHOCK_2022_01_03)
    )

    return {
        "schema_version": "route-b-2022-official-archive-audit-1",
        "source": "Kenneth R. French official historical archive",
        "archive_cut": "July 2022 data / August 2022 release",
        "archive_url": ARCHIVE_URL,
        "target_month": TARGET_MONTH,
        "monthly_rows_through_target": len(truncated),
        "smb_202106_to_202111": [
            {"ym": str(x["ym"]), "smb": float(x["smb"])}
            for x in six
        ],
        "size_weakness": float(size),
        "valuation": VALUATION_2021_11,
        "policy_shock": POLICY_SHOCK_2022_01_03,
        "route_b": float(rb),
        "threshold": ROUTE_B_THRESHOLD,
        "passes": bool(rb >= ROUTE_B_THRESHOLD),
        "critical_size_weakness": float(critical_size),
        "size_margin_above_critical": float(size - critical_size),
        "route_margin_above_threshold": float(rb - ROUTE_B_THRESHOLD),
        "exact_2022_01_03_vintage": False,
        "interpretation": (
            "Official July-2022 CRSP-cut robustness check. "
            "This is near-vintage evidence, not the exact factor file "
            "published by 2022-01-03."
        ),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output")
    args = ap.parse_args()

    name, text = download_archive()
    result = audit(text)
    result["zip_member"] = name
    print(json.dumps(result, indent=2))

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2)
            f.write("\n")


if __name__ == "__main__":
    main()
