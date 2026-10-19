from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent
EVIDENCE = ROOT / "research" / "market_top_ng3_first_release_pilot_1987.json"


def validate() -> dict:
    x = json.loads(EVIDENCE.read_text(encoding="utf-8"))

    jan = x["cases"]["1987-01"]
    jan_first = jan["pre_revision_publication"]
    jan_rev = jan["four_month_revision_publication"]
    jan_contract = jan["revision_contract"]

    may = x["cases"]["1987-05"]
    may_pub = may["first_publication"]
    may_final = may["period_finalized_publication"]
    may_contract = may["revision_contract"]

    fg = may_pub["finished_goods"]
    im = may_pub["intermediate_materials"]

    fg_calc = (float(fg["may_level"]) / float(fg["april_level"]) - 1.0) * 100.0
    im_calc = (float(im["may_level"]) / float(im["april_level"]) - 1.0) * 100.0

    jan_fg_first = float(jan_first["finished_goods"]["january_1987_mom_pct"])
    jan_im_first = float(jan_first["intermediate_materials"]["january_1987_mom_pct"])
    jan_fg_rev = float(jan_rev["finished_goods"]["january_1987_mom_pct"])
    jan_im_rev = float(jan_rev["intermediate_materials"]["january_1987_mom_pct"])
    jan_fg_delta = jan_fg_rev - jan_fg_first
    jan_im_delta = jan_im_rev - jan_im_first

    may_fg_final = float(may_final["finished_goods"]["may_1987_mom_pct"])
    may_im_final = float(may_final["intermediate_materials"]["may_1987_mom_pct"])
    may_fg_delta = may_fg_final - float(fg["reported_mom_pct"])
    may_im_delta = may_im_final - float(im["reported_mom_pct"])

    checks = {
        "pilot_status": x["status"] == "PASS_TWO_MONTH_FIRST_TO_FINAL_REVISION_DELTAS_RECOVERED",
        "january_release_date": jan["exact_initial_release_date"] == "1987-02-13",
        "january_provenance_boundary": jan_first["provenance_status"] == "PRE_REVISION_CARRY_FORWARD",
        "january_finished_first": math.isclose(jan_fg_first, 0.6, abs_tol=1e-12),
        "january_intermediate_first": math.isclose(jan_im_first, 0.9, abs_tol=1e-12),
        "january_finished_revised": math.isclose(jan_fg_rev, 0.4, abs_tol=1e-12),
        "january_intermediate_revised": math.isclose(jan_im_rev, 0.9, abs_tol=1e-12),
        "january_finished_delta": math.isclose(jan_fg_delta, -0.2, abs_tol=1e-12),
        "january_intermediate_delta": math.isclose(jan_im_delta, 0.0, abs_tol=1e-12),
        "january_finished_delta_frozen": math.isclose(
            jan_fg_delta,
            float(jan_contract["first_to_revision_delta_pp"]["finished_goods"]),
            abs_tol=1e-12,
        ),
        "january_intermediate_delta_frozen": math.isclose(
            jan_im_delta,
            float(jan_contract["first_to_revision_delta_pp"]["intermediate_materials"]),
            abs_tol=1e-12,
        ),
        "may_release_date": may["exact_initial_release_date"] == "1987-06-12",
        "may_finished_first_status": fg["status"] == "FIRST_PUBLICATION_VALUE_RECOVERED",
        "may_intermediate_first_status": im["status"] == "FIRST_PUBLICATION_VALUE_RECOVERED",
        "may_finished_calc_matches_frozen": math.isclose(
            fg_calc, float(fg["level_implied_mom_pct"]), abs_tol=1e-12
        ),
        "may_intermediate_calc_matches_frozen": math.isclose(
            im_calc, float(im["level_implied_mom_pct"]), abs_tol=1e-12
        ),
        "may_finished_rounding": round(fg_calc, 1) == float(fg["reported_mom_pct"]),
        "may_intermediate_rounding": round(im_calc, 1) == float(im["reported_mom_pct"]),
        "may_finalized_timing": may_final["timing_status"] == "BEYOND_FOUR_MONTH_REVISION_WINDOW",
        "may_finished_final": math.isclose(may_fg_final, -0.1, abs_tol=1e-12),
        "may_intermediate_final": math.isclose(may_im_final, 0.5, abs_tol=1e-12),
        "may_finished_delta": math.isclose(may_fg_delta, -0.4, abs_tol=1e-12),
        "may_intermediate_delta": math.isclose(may_im_delta, 0.0, abs_tol=1e-12),
        "may_finished_delta_frozen": math.isclose(
            may_fg_delta,
            float(may_contract["first_to_final_revision_delta_pp"]["finished_goods"]),
            abs_tol=1e-12,
        ),
        "may_intermediate_delta_frozen": math.isclose(
            may_im_delta,
            float(may_contract["first_to_final_revision_delta_pp"]["intermediate_materials"]),
            abs_tol=1e-12,
        ),
        "no_outcome_test": not x["model_boundary"]["historical_outcome_test_authorized"],
        "no_faster_formula": not x["model_boundary"]["faster_ng3_formula_preregistered"],
        "v1_not_reopened": not x["model_boundary"]["v1_reopened"],
    }

    status = "PASS" if all(checks.values()) else "FAIL"
    return {
        "schema_version": "market-top-ng3-first-release-pilot-validation-3",
        "status": status,
        "checks": checks,
        "derived": {
            "1987-01": {
                "pre_revision": {
                    "finished_goods_mom_pct": jan_fg_first,
                    "intermediate_materials_mom_pct": jan_im_first,
                },
                "four_month_revision": {
                    "finished_goods_mom_pct": jan_fg_rev,
                    "intermediate_materials_mom_pct": jan_im_rev,
                },
                "revision_delta_pp": {
                    "finished_goods": jan_fg_delta,
                    "intermediate_materials": jan_im_delta,
                },
            },
            "1987-05": {
                "first_published": {
                    "finished_goods_mom_pct": float(fg["reported_mom_pct"]),
                    "intermediate_materials_mom_pct": float(im["reported_mom_pct"]),
                },
                "period_finalized": {
                    "finished_goods_mom_pct": may_fg_final,
                    "intermediate_materials_mom_pct": may_im_final,
                },
                "revision_delta_pp": {
                    "finished_goods": may_fg_delta,
                    "intermediate_materials": may_im_delta,
                },
                "first_publication_level_implied": {
                    "finished_goods_mom_pct": fg_calc,
                    "intermediate_materials_mom_pct": im_calc,
                },
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
