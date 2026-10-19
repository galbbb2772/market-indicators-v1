from __future__ import annotations

import argparse
import json
import math
from datetime import datetime, timezone

import requests

CURRENT_REVISED_SNAPSHOT = {
    "1976-01-01": {
        "price_per_unit": 0.376,
        "unit_profit": 0.052,
        "price_source": "https://fred.stlouisfed.org/data/A455RD3Q052SBEA",
        "profit_source": "https://fred.stlouisfed.org/data/A463RD3Q052SBEA",
        "snapshot_note": "Current revised BEA/FRED history observed 2026-10-19",
    },
    "1987-10-01": {
        "price_per_unit": 0.621,
        "unit_profit": 0.062,
        "price_source": "https://fred.stlouisfed.org/data/A455RD3Q052SBEA",
        "profit_source": "https://fred.stlouisfed.org/data/A463RD3Q052SBEA",
        "snapshot_note": "Current revised BEA/FRED history observed 2026-10-19",
    },
}

FRED_SERIES = {
    "price": {
        "id": "A455RD3Q052SBEA",
        "url": "https://fred.stlouisfed.org/data/A455RD3Q052SBEA.txt",
    },
    "profit": {
        "id": "A463RD3Q052SBEA",
        "url": "https://fred.stlouisfed.org/data/A463RD3Q052SBEA.txt",
    },
}

HISTORICAL_VINTAGES = {
    "1976Q1_in_Apr1976_SCB": {
        "publication": "Survey of Current Business — April 1976",
        "source_url": (
            "https://fraser.stlouisfed.org/title/"
            "survey-current-business-46/april-1976-9659/fulltext"
        ),
        "table": (
            "Table 28 — Current Dollar Cost and Profit Per Unit of "
            "Constant Dollar Gross Domestic Product of Nonfinancial Corporate Business"
        ),
        "observation_date": "1976-01-01",
        "price_per_unit": 1.296,
        "unit_profit": 0.131,
        "column_mapping": (
            "1974 annual, 1975 annual, 1975 Q1-Q4, 1976 Q1; "
            "1976 Q1 is the final column"
        ),
        "concept": "corporate profits with IVA and capital consumption adjustments",
    },
    "1987Q4_in_Mar1988_SCB": {
        "publication": "Survey of Current Business — March 1988",
        "source_url": (
            "https://fraser.stlouisfed.org/title/"
            "survey-current-business-46/march-1988-10083/fulltext"
        ),
        "table": (
            "Table 7.18 — Current-Dollar Cost and Profit Per Unit of "
            "Constant-Dollar Gross Domestic Product of Nonfinancial Corporate Business"
        ),
        "observation_date": "1987-10-01",
        "price_per_unit": 1.123,
        "unit_profit": 0.108,
        "column_mapping": (
            "1986 annual, 1987 revised annual, 1986 Q3-Q4, 1987 Q1-Q4; "
            "1987 Q4 is the final column"
        ),
        "concept": "corporate profits with IVA and capital consumption adjustments",
    },
}


def fetch_fred_table(url: str) -> dict[str, float]:
    r = requests.get(
        url,
        timeout=45,
        headers={"User-Agent": "market-top-ng3-vintage-profit-share/1.0"},
    )
    r.raise_for_status()

    out: dict[str, float] = {}
    for raw in r.text.splitlines():
        line = raw.strip()
        if not line or line.startswith(("DATE", "Title:", "Series ID:", "Source:", "Release:", "Seasonal", "Frequency:", "Units:", "Date Range:", "Last Updated:", "Notes:")):
            continue
        parts = line.split()
        if len(parts) < 2:
            continue
        d, v = parts[0], parts[1]
        if len(d) != 10 or d[4] != "-" or d[7] != "-":
            continue
        try:
            out[d] = float(v)
        except ValueError:
            continue
    if not out:
        raise ValueError(f"no observations parsed from {url}")
    return out


def pct(x: float) -> float:
    return 100.0 * x


def audit(live: bool = False) -> dict:
    live_status = "SKIPPED"
    live_price = None
    live_profit = None
    live_error = None

    if live:
        try:
            live_price = fetch_fred_table(FRED_SERIES["price"]["url"])
            live_profit = fetch_fred_table(FRED_SERIES["profit"]["url"])
            live_status = "PASS"
        except Exception as exc:
            live_status = "UNAVAILABLE"
            live_error = repr(exc)

    cases = {}
    for key, vintage in HISTORICAL_VINTAGES.items():
        d = vintage["observation_date"]
        snap = CURRENT_REVISED_SNAPSHOT[d]

        hist_price = float(vintage["price_per_unit"])
        hist_profit = float(vintage["unit_profit"])
        cur_price = float(snap["price_per_unit"])
        cur_profit = float(snap["unit_profit"])

        hist_share = hist_profit / hist_price
        cur_share = cur_profit / cur_price
        diff_pp = pct(cur_share - hist_share)
        rel_diff_pct = pct(cur_share / hist_share - 1.0)

        cases[key] = {
            **vintage,
            "historical_profit_share_pct": pct(hist_share),
            "current_revised": {
                "price_per_unit": cur_price,
                "unit_profit": cur_profit,
                "profit_share_pct": pct(cur_share),
                "snapshot_note": snap["snapshot_note"],
                "price_source": snap["price_source"],
                "profit_source": snap["profit_source"],
            },
            "optional_live_check": {
                "status": live_status,
                "price_per_unit": (
                    None if live_price is None else live_price.get(d)
                ),
                "unit_profit": (
                    None if live_profit is None else live_profit.get(d)
                ),
                "error": live_error,
            },
            "revision_diagnostic": {
                "profit_share_difference_pp": diff_pp,
                "profit_share_relative_difference_pct": rel_diff_pct,
                "absolute_difference_pp": abs(diff_pp),
            },
        }

    return {
        "schema_version": "market-top-ng3-vintage-profit-share-diagnostic-1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "research_only": True,
        "production_effect": "none",
        "status": "PASS",
        "current_series": FRED_SERIES,
        "current_revised_snapshot": CURRENT_REVISED_SNAPSHOT,
        "live_requested": live,
        "live_status": live_status,
        "cases": cases,
        "interpretation_boundary": {
            "allowed": (
                "Profit/unit-price is used only as a scale-free revision diagnostic "
                "within a historical publication whose numerator and denominator are "
                "from the same table and column."
            ),
            "not_allowed": (
                "Do not interpret the difference from today's revised ratio as pure "
                "statistical revision when historical accounting/classification concepts "
                "may also differ."
            ),
            "scoring_effect": "NONE",
        },
    }

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output")
    ap.add_argument("--live", action="store_true")
    args = ap.parse_args()

    x = audit(live=args.live)
    text = json.dumps(x, indent=2)
    print(text)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as fh:
            fh.write(text + "\n")


if __name__ == "__main__":
    main()
