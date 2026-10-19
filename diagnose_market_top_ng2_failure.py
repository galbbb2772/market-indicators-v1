from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone

from validate_market_top_ng2_pre1993 import (
    HOLDOUT_END,
    THRESHOLD,
    build_credit_scores,
    build_effective_states,
    build_ff_scores,
    fetch_sp500,
    month_gate,
)


def compact(row: dict) -> dict:
    return {
        "effective_month": row["effective_month"],
        "route_a_ng1": row["route_a_ng1"],
        "financial_lead_gap_raw": row["financial_lead_gap_raw"],
        "financial_lead_gap_score": row["financial_lead_gap_score"],
        "route_a_ng2": row["route_a_ng2"],
        "spread_shock_score": row["spread_shock_score"],
        "finance_weakness_score": row["finance_weakness_score"],
        "size_weakness_score": row["size_weakness_score"],
        "portfolio_exhaustion_score": row["portfolio_exhaustion_score"],
        "top_location_pass": row["top_location_pass"],
    }


def diagnose() -> dict:
    ff = build_ff_scores()
    credit = build_credit_scores()
    states = build_effective_states(ff, credit)
    price = fetch_sp500()

    rows = []
    for row in states:
        if row["effective_month"] > HOLDOUT_END:
            continue
        gate = month_gate(price, row["effective_month"])
        if gate is None:
            continue
        x = dict(row)
        x["top_location_pass"] = gate["passes"]
        rows.append(x)

    if not rows:
        raise ValueError("no pre-1993 rows")

    route_pass = [x for x in rows if x["route_a_ng2"] >= THRESHOLD]
    gate_pass = [x for x in rows if x["top_location_pass"]]
    armed = [
        x for x in rows
        if x["route_a_ng2"] >= THRESHOLD and x["top_location_pass"]
    ]
    ng1_armed = [
        x for x in rows
        if x["route_a_ng1"] >= THRESHOLD and x["top_location_pass"]
    ]

    top_ng2 = sorted(rows, key=lambda x: x["route_a_ng2"], reverse=True)[:10]
    top_ng1 = sorted(rows, key=lambda x: x["route_a_ng1"], reverse=True)[:10]
    gate_top_ng2 = sorted(
        gate_pass, key=lambda x: x["route_a_ng2"], reverse=True
    )[:10]

    lead_scores = [x["financial_lead_gap_score"] for x in rows]

    return {
        "schema_version": "market-top-route-a-ng2-failure-diagnostic-1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "research_only": True,
        "production_effect": "none",
        "status": "HYPOTHESIS_GENERATION_ONLY",
        "ng2_decision_locked": "REJECT_NG2_TOP_ROUTE",
        "formula_changed": False,
        "sample": {
            "first_effective_month": rows[0]["effective_month"],
            "last_effective_month": rows[-1]["effective_month"],
            "months": len(rows),
        },
        "counts": {
            "route_ng2_ge_85_without_price_gate": len(route_pass),
            "top_location_gate_pass_months": len(gate_pass),
            "ng2_armed_months": len(armed),
            "ng1_armed_months_under_same_price_gate": len(ng1_armed),
        },
        "maxima": {
            "max_route_ng2": compact(top_ng2[0]),
            "max_route_ng2_when_top_gate_passes": (
                compact(gate_top_ng2[0]) if gate_top_ng2 else None
            ),
            "max_route_ng1": compact(top_ng1[0]),
            "lead_gap_score_min": min(lead_scores),
            "lead_gap_score_max": max(lead_scores),
        },
        "top_route_ng2_months": [compact(x) for x in top_ng2],
        "top_gate_route_ng2_months": [compact(x) for x in gate_top_ng2],
        "ng1_armed_months": [compact(x) for x in ng1_armed],
        "interpretation_rule": (
            "Diagnostic only. It may explain why frozen NG2 produced zero "
            "episodes, but it cannot alter NG2 threshold, formula, lags, or "
            "decision. Any redesign must be NG3 or later."
        ),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output")
    args = ap.parse_args()
    x = diagnose()
    print(json.dumps(x, indent=2))
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(x, f, indent=2)
            f.write("\n")


if __name__ == "__main__":
    main()
