from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone

import requests

BLS_API = "https://api.bls.gov/publicAPI/v2/timeseries/data/"

SERIES = {
    "cpi_u_all_items_nsa": {
        "id": "CUUR0000SA0",
        "role": "consumer inflation",
        "expected_pre1993": True,
    },
    "ppi_finished_goods_nsa": {
        "id": "WPUFD49207",
        "role": "producer finished-goods prices",
        "expected_pre1993": True,
    },
    "ppi_intermediate_legacy_nsa": {
        "id": "WPUSOP2000",
        "role": "legacy intermediate materials / supplies / components",
        "expected_pre1993": True,
    },
}

START_YEAR = 1947
END_YEAR = 1992
CHUNK = 10


def fetch_bls(series_id: str, start: int, end: int) -> list[dict]:
    r = requests.post(
        BLS_API,
        json={
            "seriesid": [series_id],
            "startyear": str(start),
            "endyear": str(end),
        },
        timeout=45,
    )
    r.raise_for_status()
    obj = r.json()
    if obj.get("status") != "REQUEST_SUCCEEDED":
        raise RuntimeError(f"BLS failure for {series_id}: {obj}")
    rows = []
    for s in obj.get("Results", {}).get("series", []):
        for x in s.get("data", []):
            p = x.get("period", "")
            if not (p.startswith("M") and len(p) == 3 and p != "M13"):
                continue
            rows.append(
                {
                    "year": int(x["year"]),
                    "month": int(p[1:]),
                    "value": float(x["value"]),
                }
            )
    return rows


def audit_series(series_id: str) -> dict:
    by_month = {}
    for start in range(START_YEAR, END_YEAR + 1, CHUNK):
        end = min(start + CHUNK - 1, END_YEAR)
        for x in fetch_bls(series_id, start, end):
            by_month[(x["year"], x["month"])] = x["value"]

    keys = sorted(by_month)
    if not keys:
        return {
            "series_id": series_id,
            "observations": 0,
            "first": None,
            "last": None,
            "missing_months": None,
        }

    expected = []
    y, m = START_YEAR, 1
    while (y, m) <= (END_YEAR, 12):
        expected.append((y, m))
        m += 1
        if m == 13:
            y += 1
            m = 1

    missing = [x for x in expected if x not in by_month]
    return {
        "series_id": series_id,
        "observations": len(keys),
        "first": f"{keys[0][0]:04d}-{keys[0][1]:02d}",
        "last": f"{keys[-1][0]:04d}-{keys[-1][1]:02d}",
        "missing_months": [
            f"{y:04d}-{m:02d}" for y, m in missing
        ],
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output")
    args = ap.parse_args()

    results = {}
    for name, spec in SERIES.items():
        x = audit_series(spec["id"])
        x["role"] = spec["role"]
        x["expected_pre1993"] = spec["expected_pre1993"]
        results[name] = x

    out = {
        "schema_version": "market-top-ng3-source-feasibility-1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "research_only": True,
        "production_effect": "none",
        "audit_window": {
            "start": f"{START_YEAR}-01",
            "end": f"{END_YEAR}-12",
        },
        "bls": results,
        "notes": {
            "cpi_revision_boundary": (
                "Use CPI-U not-seasonally-adjusted for historical model input; "
                "BLS states CPI-U/CPI-W are final when issued except rare corrections."
            ),
            "ppi_revision_boundary": (
                "PPI observations are preliminary and may be revised for up to "
                "4 months after first publication. A genuine PIT backtest needs "
                "first-published/release-vintage values or a conservative lag."
            ),
            "bea_profit_margin_candidate": (
                "NIPA Table 1.15 line 7 (unit profits from current production) "
                "and line 9 (after-tax unit profits) provide quarterly history "
                "back to 1947, but NIPA revisions require explicit vintage handling."
            ),
            "formula_status": "NOT_FROZEN",
        },
    }

    text = json.dumps(out, indent=2)
    print(text)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(text + "\n")


if __name__ == "__main__":
    main()
