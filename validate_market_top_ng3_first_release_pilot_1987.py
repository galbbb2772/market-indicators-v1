from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent
EVIDENCE = ROOT / "research" / "market_top_ng3_first_release_pilot_1987.json"


def validate() -> dict:
    x = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    may = x["cases"]["1987-05"]
    pub = may["first_publication"]
    final = may["period_finalized_publication"]
    rev = may["revision_contract"]

    fg = pub["finished_goods"]
    im = pub["intermediate_materials"]

    fg_calc = (float(fg["may_level"]) / float(fg["april_level"]) - 1.0) * 100.0
    im_calc = (float(im["may_level"]) / float(im["april_level"]) - 1.0) * 100.0

    fg_final = float(final["finished_goods"]["may_1987_mom_pct"])
    im_final = float(final["intermediate_materials"]["may_1987_mom_pct"])
    fg_delta = fg_final - float(fg["reported_mom_pct"])
    im_delta = im_final - float(im["reported_mom_pct"])

    checks = {
        "pilot_status_upgraded": x["status"] == "PASS_FIRST_TO_FINAL_REVISION_DELTA_RECOVERED",
        "release_date_recovered": may["exact_initial_release_date"] == "1987-06-12",
        "finished_status": fg["status"] == "FIRST_PUBLICATION_VALUE_RECOVERED",
        "intermediate_status": im["status"] == "FIRST_PUBLICATION_VALUE_RECOVERED",
        "finished_calc_matches_frozen": math.isclose(
            fg_calc, float(fg["level_implied_mom_pct"]), abs_tol=1e-12
        ),
        "intermediate_calc_matches_frozen": math.isclose(
            im_calc, float(im["level_implied_mom_pct"]), abs_tol=1e-12
        ),
        "finished_rounds_to_first_report": round(fg_calc, 1) == float(fg["reported_mom_pct"]),
        "intermediate_rounds_to_first_report": round(im_calc, 1) == float(im["reported_mom_pct"]),
        "finalized_timing_beyond_window": final["timing_status"] == "BEYOND_FOUR_MONTH_REVISION_WINDOW",
        "finished_finalized_recovered": math.isclose(fg_final, -0.1, abs_tol=1e-12),
        "intermediate_finalized_recovered": math.isclose(im_final, 0.5, abs_tol=1e-12),
        "finished_revision_delta": math.isclose(fg_delta, -0.4, abs_tol=1e-12),
        "intermediate_revision_delta": math.isclose(im_delta, 0.0, abs_tol=1e-12),
        "finished_delta_matches_frozen": math.isclose(
            fg_delta,
            float(rev["first_to_final_revision_delta_pp"]["finished_goods"]),
            abs_tol=1e-12,
        ),
        "intermediate_delta_matches_frozen": math.isclose(
            im_delta,
            float(rev["first_to_final_revision_delta_pp"]["intermediate_materials"]),
            abs_tol=1e-12,
        ),
        "finalized_precision_not_overclaimed": (
            rev["finalized_value_status"] == "RECOVERED_AT_PUBLISHED_0_1PP_PRECISION"
        ),
        "january_revision_not_overclaimed": (
            x["cases"]["1987-01"]["revision_event"]["status"]
            == "REVISION_EVENT_CONFIRMED_NUMERIC_DELTA_PENDING"
        ),
        "no_outcome_test": not x["model_boundary"]["historical_outcome_test_authorized"],
        "no_faster_formula": not x["model_boundary"]["faster_ng3_formula_preregistered"],
        "v1_not_reopened": not x["model_boundary"]["v1_reopened"],
    }

    status = "PASS" if all(checks.values()) else "FAIL"
    return {
        "schema_version": "market-top-ng3-first-release-pilot-validation-2",
        "status": status,
        "checks": checks,
        "derived": {
            "first_published": {
                "finished_goods_mom_pct": float(fg["reported_mom_pct"]),
                "intermediate_materials_mom_pct": float(im["reported_mom_pct"]),
            },
            "period_finalized": {
                "finished_goods_mom_pct": fg_final,
                "intermediate_materials_mom_pct": im_final,
            },
            "revision_delta_pp": {
                "finished_goods": fg_delta,
                "intermediate_materials": im_delta,
            },
            "first_publication_level_implied": {
                "finished_goods_mom_pct": fg_calc,
                "intermediate_materials_mom_pct": im_calc,
            },
        },
        "research_only": True,
        "production_effect": "none",
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output")
    args = ap.parse_args()
    x = validate()
    text = json.dumps(x, indent=2)
    print(text)
    if args.output:
        Path(args.output).write_text(text + "\n", encoding="utf-8")
    if x["status"] != "PASS":
        raise SystemExit("NG3 first-release pilot contract failed")


if __name__ == "__main__":
    main()
