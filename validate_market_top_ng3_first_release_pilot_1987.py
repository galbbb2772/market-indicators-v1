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

    fg = pub["finished_goods"]
    im = pub["intermediate_materials"]

    fg_calc = (float(fg["may_level"]) / float(fg["april_level"]) - 1.0) * 100.0
    im_calc = (float(im["may_level"]) / float(im["april_level"]) - 1.0) * 100.0

    checks = {
        "release_date_recovered": may["exact_initial_release_date"] == "1987-06-12",
        "finished_status": fg["status"] == "FIRST_PUBLICATION_VALUE_RECOVERED",
        "intermediate_status": im["status"] == "FIRST_PUBLICATION_VALUE_RECOVERED",
        "finished_calc_matches_frozen": math.isclose(
            fg_calc, float(fg["level_implied_mom_pct"]), abs_tol=1e-12
        ),
        "intermediate_calc_matches_frozen": math.isclose(
            im_calc, float(im["level_implied_mom_pct"]), abs_tol=1e-12
        ),
        "finished_rounds_to_report": round(fg_calc, 1) == float(fg["reported_mom_pct"]),
        "intermediate_rounds_to_report": round(im_calc, 1) == float(im["reported_mom_pct"]),
        "finalized_not_overclaimed": (
            may["revision_contract"]["finalized_value_status"] == "RECOVERY_PENDING"
        ),
        "january_revision_not_overclaimed": (
            x["cases"]["1987-01"]["revision_event"]["status"]
            == "REVISION_EVENT_CONFIRMED_NUMERIC_DELTA_PENDING"
        ),
        "no_outcome_test": not x["model_boundary"]["historical_outcome_test_authorized"],
        "no_faster_formula": not x["model_boundary"]["faster_ng3_formula_preregistered"],
    }

    status = "PASS" if all(checks.values()) else "FAIL"
    return {
        "schema_version": "market-top-ng3-first-release-pilot-validation-1",
        "status": status,
        "checks": checks,
        "derived": {
            "finished_goods_mom_pct": fg_calc,
            "intermediate_materials_mom_pct": im_calc,
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
