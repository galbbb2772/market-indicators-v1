from __future__ import annotations

import json
from pathlib import Path

import research_indicator_validation_v1 as study

ROOT = Path(__file__).resolve().parent
CURRENT = ROOT / "docs" / "data" / "current.json"
OUT = ROOT / "docs" / "data" / "indicator_validation_v1.json"

# These indicators either directly consume FRED/official macro series or are
# downstream composites that can change formula when those sources are absent.
# They remain in the report, but are marked source-dependent so a transient
# network fallback cannot be mixed with formula-invariant market-price factors.
FRED_DEPENDENT = {
    "global_cb_rhythm", "market_fear", "liquidity_risk", "treasury_rate_regime",
    "usd_credit", "high_yield", "inventory_cycle", "fiscal_deficit", "employment",
    "leverage_liquidity", "systemic_risk", "risk_60d", "credit_cycle", "yield_curve",
    "institutional_panic", "business_cycle", "geopolitical_risk", "us_loans_total",
    "us_loans_speed", "market_optimism", "market_pessimism", "market_liquidity",
    "mega_liquidity_blowup", "market_bias",
}


def main():
    study.main()

    current = json.loads(CURRENT.read_text(encoding="utf-8"))
    out = json.loads(OUT.read_text(encoding="utf-8"))
    errors = current.get("errors") or {}
    fred_errors = {k: v for k, v in errors.items() if str(k).startswith("fred:")}
    current_items = {x.get("id"): x for x in (current.get("indicators") or [])}

    market_price = []
    source_dependent = []
    for row in out.get("indicators", []):
        cur = current_items.get(row.get("id")) or {}
        row["source_quality"] = cur.get("quality")
        row["source_asof"] = cur.get("asof")
        dep = row.get("id") in FRED_DEPENDENT
        row["fred_or_official_source_dependent"] = dep
        (source_dependent if dep else market_price).append(row)

    def compact(rows):
        return {
            "n": len(rows),
            "active": sum(x.get("model_v2_role") == "active" for x in rows),
            "context": sum(x.get("model_v2_role") == "context" for x in rows),
            "archived": sum(x.get("model_v2_role") == "archived" for x in rows),
            "phase_same_sign_ge70": {
                f"{h}d": sum(
                    (x["horizons"][f"{h}d"]["raw_overlap_phase"].get("same_sign_as_full_pct") or 0) >= 70
                    for x in rows
                ) for h in (5, 10, 20)
            },
        }

    out["source_run"] = {
        "status": current.get("status"),
        "working_count": current.get("working_count"),
        "total_count": current.get("total_count"),
        "generated_at": current.get("generated_at"),
        "fred_error_count": len(fred_errors),
        "fred_errors": fred_errors,
        "all_errors": errors,
        "direct_fred_complete": len(fred_errors) == 0,
    }
    out["source_strata"] = {
        "formula_invariant_market_price_or_derived": compact(market_price),
        "fred_or_official_source_dependent": compact(source_dependent),
        "rule": "If FRED/official retrieval fails, only the formula-invariant stratum is treated as source-stable evidence; source-dependent factors remain provisional because configured fallbacks can change their historical formula.",
    }
    if fred_errors:
        out["warnings"].append(
            "FRED retrieval failed in this run. Formula-invariant market-price factors remain comparable; FRED/official-source-dependent factors are provisional and may be using configured fallbacks."
        )
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({
        "eligible": out["coverage"]["eligible_indicator_count"],
        "fred_error_count": len(fred_errors),
        "source_strata": out["source_strata"],
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
