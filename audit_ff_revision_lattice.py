from __future__ import annotations

import argparse
import io
import json
import zipfile

import requests

from audit_ff_2022_archive import parse_ff3_monthly_csv
from market_top_canonical_inputs import size_weakness_history
from policyshock_v211 import route_b

TARGET_MONTH = "202111"
VALUATION_2021_11 = 98.5807214666
POLICY_SHOCK_2022_01_03 = 74.3886192578
ROUTE_B_THRESHOLD = 85.0

ARCHIVES = [
    {
        "id": "JULY_2022",
        "label": "July 2022 data / August 2022 release",
        "url": (
            "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/"
            "Data_Library/Historical_Archives/08%202022%20Update/ftp/"
            "F-F_Research_Data_Factors_CSV.zip"
        ),
    },
    {
        "id": "JULY_2023",
        "label": "July 2023 data / August 2023 release",
        "url": (
            "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/"
            "Data_Library/Historical_Archives/08%202023%20Update/ftp/"
            "F-F_Research_Data_Factors_CSV.zip"
        ),
    },
    {
        "id": "JULY_2024",
        "label": "July 2024 data / August 2024 release",
        "url": (
            "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/"
            "Data_Library/Historical_Archives/08%202024%20Update/ftp/"
            "F-F_Research_Data_Factors_CSV.zip"
        ),
    },
    {
        "id": "JULY_2025",
        "label": "July 2025 data / August 2025 release",
        "url": (
            "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/"
            "Data_Library/Historical_Archives/08%202025%20Update/ftp/"
            "F-F_Research_Data_Factors_CSV.zip"
        ),
    },
    {
        "id": "AUGUST_2026",
        "label": "August 2026 data / September 2026 release",
        "url": (
            "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/"
            "Data_Library/Historical_Archives/09%202026%20Update/ftp/"
            "F-F_Research_Data_Factors_CSV.zip"
        ),
    },
]


def download_archive(url: str) -> tuple[str, str]:
    r = requests.get(
        url,
        headers={"User-Agent": "market-top-ff-revision-lattice/1.0"},
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


def audit_text(*, archive_id: str, label: str, url: str, text: str) -> dict:
    rows = parse_ff3_monthly_csv(text)
    target_i = next(
        (i for i, x in enumerate(rows) if str(x["ym"]) == TARGET_MONTH),
        None,
    )
    if target_i is None:
        raise ValueError(f"{archive_id}: target month {TARGET_MONTH} not found")
    if target_i < 5:
        raise ValueError(f"{archive_id}: not enough SMB history")

    truncated = rows[: target_i + 1]
    smb = [float(x["smb"]) for x in truncated]
    size = size_weakness_history(smb)[-1]
    if size is None:
        raise ValueError(f"{archive_id}: SizeWeakness missing")

    rb = route_b(
        VALUATION_2021_11,
        POLICY_SHOCK_2022_01_03,
        float(size),
    )
    if rb is None:
        raise ValueError(f"{archive_id}: Route_B missing")

    critical_size = (
        ROUTE_B_THRESHOLD**3
        / (VALUATION_2021_11 * POLICY_SHOCK_2022_01_03)
    )
    six = truncated[-6:]

    return {
        "id": archive_id,
        "label": label,
        "url": url,
        "target_month": TARGET_MONTH,
        "monthly_rows_through_target": len(truncated),
        "smb_202106_to_202111": [
            {"ym": str(x["ym"]), "smb": float(x["smb"])}
            for x in six
        ],
        "size_weakness": float(size),
        "critical_size_weakness": float(critical_size),
        "size_margin": float(size - critical_size),
        "route_b": float(rb),
        "route_margin": float(rb - ROUTE_B_THRESHOLD),
        "passes": bool(rb >= ROUTE_B_THRESHOLD),
    }


def build_lattice(results: list[dict]) -> dict:
    if not results:
        raise ValueError("revision results must not be empty")
    sizes = [float(x["size_weakness"]) for x in results]
    routes = [float(x["route_b"]) for x in results]
    all_pass = all(bool(x["passes"]) for x in results)

    months = [str(x["ym"]) for x in results[0]["smb_202106_to_202111"]]
    raw_revision_range = {}
    for ym in months:
        vals = []
        for result in results:
            row = next(
                x for x in result["smb_202106_to_202111"]
                if str(x["ym"]) == ym
            )
            vals.append(float(row["smb"]))
        raw_revision_range[ym] = {
            "min": min(vals),
            "max": max(vals),
            "range": max(vals) - min(vals),
        }

    return {
        "schema_version": "route-b-2022-ff-revision-lattice-1",
        "target_month": TARGET_MONTH,
        "valuation": VALUATION_2021_11,
        "policy_shock": POLICY_SHOCK_2022_01_03,
        "threshold": ROUTE_B_THRESHOLD,
        "archive_count": len(results),
        "all_archives_pass": all_pass,
        "size_weakness": {
            "min": min(sizes),
            "max": max(sizes),
            "range": max(sizes) - min(sizes),
        },
        "route_b": {
            "min": min(routes),
            "max": max(routes),
            "range": max(routes) - min(routes),
            "minimum_margin_above_threshold": min(routes) - ROUTE_B_THRESHOLD,
        },
        "raw_smb_revision_range": raw_revision_range,
        "archives": results,
        "interpretation": (
            "Annual official Ken French archive cuts quantify historical "
            "revision sensitivity of the 2021-11 SMB-derived SizeWeakness. "
            "No threshold or weight is changed across archive versions."
        ),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output")
    args = ap.parse_args()

    results = []
    for spec in ARCHIVES:
        member, text = download_archive(spec["url"])
        row = audit_text(
            archive_id=spec["id"],
            label=spec["label"],
            url=spec["url"],
            text=text,
        )
        row["zip_member"] = member
        results.append(row)

    lattice = build_lattice(results)
    print(json.dumps(lattice, indent=2))
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(lattice, f, indent=2)
            f.write("\n")


if __name__ == "__main__":
    main()
