from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone

import screen_inflation_margin_v1 as im


WINDOWS = {
    "training_1966": ("1965-12", "1966-06"),
    "validation_1968_69": ("1968-08", "1969-02"),
    "training_1972_73": ("1972-10", "1973-03"),
    "validation_1980_81": ("1980-08", "1981-02"),
    "negative_1987": ("1987-06", "1987-10"),
}


def build_rows():
    cpi = im.fetch_cpi_snapshot()
    bls, provider = im.fetch_bls_quarterly_yoy(
        [im.ULC_ID, im.UNIT_PROFIT_ID]
    )
    states = im.build_monthly_states(
        im.build_cpi_rows(cpi),
        im.build_ulc_rows(bls[im.ULC_ID]),
        im.build_margin_rows(bls[im.UNIT_PROFIT_ID]),
    )
    price = im.fetch_sp500()

    rows = []
    for row in states:
        if row["history_months"] < im.WARMUP_MONTHS:
            continue
        gate = im.month_gate(price, row["effective_month"])
        if gate is None:
            continue
        x = dict(row)
        x["top_location_pass"] = gate["passes"]
        x["pressure_pass"] = x["route_im_v1"] >= im.THRESHOLD
        rows.append(x)
    return rows, provider


def compact(row):
    return {
        "month": row["effective_month"],
        "route": row["route_im_v1"],
        "top_location_pass": row["top_location_pass"],
        "pressure_pass": row["pressure_pass"],
        "inflation_score": row["inflation_score"],
        "ulc_score": row["ulc_score"],
        "margin_compression_score": row["margin_compression_score"],
        "cpi_yoy": row["raw"]["cpi_yoy"],
        "ulc_yoy": row["raw"]["ulc_yoy"],
        "unit_profit_yoy": row["raw"]["unit_profit_yoy"],
        "cost_profit_gap_yoy": (
            row["raw"]["ulc_yoy"] - row["raw"]["unit_profit_yoy"]
        ),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--output")
    args = ap.parse_args()

    rows, provider = build_rows()
    windows = {}
    for name, (a, b) in WINDOWS.items():
        subset = [
            compact(x) for x in rows
            if im.in_window(x["effective_month"], (a, b))
        ]
        windows[name] = {
            "rows": subset,
            "max_route": max(subset, key=lambda x: x["route"]) if subset else None,
            "max_cost_profit_gap": (
                max(subset, key=lambda x: x["cost_profit_gap_yoy"])
                if subset else None
            ),
        }

    route85 = [compact(x) for x in rows if x["pressure_pass"]]
    gate_rows = [compact(x) for x in rows if x["top_location_pass"]]

    result = {
        "schema_version": "market-top-inflation-margin-v1.1-diagnostic-1",
        "status": "HYPOTHESIS_GENERATION_ONLY",
        "research_only": True,
        "production_effect": "none",
        "frozen_decision": "REJECT",
        "formula_changed": False,
        "threshold_changed": False,
        "windows": windows,
        "counts": {
            "route_ge_85_months": len(route85),
            "route_ge_85_and_top_gate_months": sum(
                x["top_location_pass"] for x in route85
            ),
            "top_gate_months": len(gate_rows),
        },
        "maxima": {
            "max_route": max(
                (compact(x) for x in rows),
                key=lambda x: x["route"],
            ),
            "max_route_when_top_gate_passes": max(
                gate_rows, key=lambda x: x["route"]
            ) if gate_rows else None,
            "max_cost_profit_gap_when_top_gate_passes": max(
                gate_rows, key=lambda x: x["cost_profit_gap_yoy"]
            ) if gate_rows else None,
        },
        "route_ge_85_months": route85,
        "provider": provider,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }

    print(json.dumps(result, indent=2))
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2)
            f.write("\n")


if __name__ == "__main__":
    main()
