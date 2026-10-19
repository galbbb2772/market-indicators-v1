from __future__ import annotations

import argparse
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone

from research.build_market_top_ng3_first_release_panel_1986_1988 import (
    PANEL_MONTHS,
    fetch_text,
    parse_first_values,
    parse_table_a_current,
    pdf_url,
    resolve_first_publication,
)


def add_months(year: int, month: int, delta: int) -> tuple[int, int]:
    z = year * 12 + (month - 1) + delta
    return z // 12, z % 12 + 1


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--output",
        default="market_top_ng3_finalized_panel_1986_1988.json",
    )
    args = ap.parse_args()

    needed = set(PANEL_MONTHS)
    for y, m in PANEL_MONTHS:
        needed.add(add_months(y, m, 4))

    docs = {}
    with ThreadPoolExecutor(max_workers=8) as ex:
        futs = {ex.submit(fetch_text, y, m): (y, m) for y, m in sorted(needed)}
        for fut in as_completed(futs):
            d = fut.result()
            docs[d["source_month"]] = d

    rows = []
    for y, m in PANEL_MONTHS:
        key = f"{y:04d}-{m:02d}"
        first_doc = docs[key]
        first_narrative = parse_first_values(first_doc["text_flow"], y, m)
        first_table = parse_table_a_current(first_doc["text_layout"], y, m)
        first = resolve_first_publication(first_narrative, first_table)

        fy, fm = add_months(y, m, 4)
        final_key = f"{fy:04d}-{fm:02d}"
        final_doc = docs[final_key]
        final_table = parse_table_a_current(final_doc["text_layout"], y, m)

        final_fg = final_table.get("finished_goods_mom_sa_pct")
        final_im = final_table.get("intermediate_goods_mom_sa_pct")
        first_fg = first.get("finished_goods_mom_sa_pct")
        first_im = first.get("intermediate_goods_mom_sa_pct")

        complete = all(v is not None for v in (first_fg, first_im, final_fg, final_im))
        rows.append(
            {
                "observation_month": key,
                "first_publication_pdf": pdf_url(y, m),
                "first_publication": first,
                "four_month_revision_source_month": final_key,
                "four_month_revision_pdf": pdf_url(fy, fm),
                "four_month_revision": final_table,
                "revision_delta_pp": {
                    "finished_goods": (
                        round(float(final_fg) - float(first_fg), 10)
                        if complete else None
                    ),
                    "intermediate_goods": (
                        round(float(final_im) - float(first_im), 10)
                        if complete else None
                    ),
                },
                "status": "COMPLETE" if complete else "AMBIGUOUS",
            }
        )

    known = {r["observation_month"]: r for r in rows}
    checks = {
        "all_first_values_resolved": all(
            r["first_publication"].get("finished_goods_mom_sa_pct") is not None
            and r["first_publication"].get("intermediate_goods_mom_sa_pct") is not None
            for r in rows
        ),
        "all_four_month_revision_rows_parsed": all(
            r["four_month_revision"].get("status") == "PARSED"
            for r in rows
        ),
        "jan_1987_final_finished": (
            known["1987-01"]["four_month_revision"].get("finished_goods_mom_sa_pct")
            == 0.4
        ),
        "jan_1987_final_intermediate": (
            known["1987-01"]["four_month_revision"].get("intermediate_goods_mom_sa_pct")
            == 0.9
        ),
        "may_1987_final_finished": (
            known["1987-05"]["four_month_revision"].get("finished_goods_mom_sa_pct")
            == -0.1
        ),
        "may_1987_final_intermediate": (
            known["1987-05"]["four_month_revision"].get("intermediate_goods_mom_sa_pct")
            == 0.5
        ),
    }

    complete_rows = [r for r in rows if r["status"] == "COMPLETE"]
    fg_changed = [
        r for r in complete_rows
        if abs(r["revision_delta_pp"]["finished_goods"]) > 0.051
    ]
    im_changed = [
        r for r in complete_rows
        if abs(r["revision_delta_pp"]["intermediate_goods"]) > 0.051
    ]
    sign_flips = []
    for r in complete_rows:
        first = r["first_publication"]
        final = r["four_month_revision"]
        for field, label in (
            ("finished_goods_mom_sa_pct", "finished_goods"),
            ("intermediate_goods_mom_sa_pct", "intermediate_goods"),
        ):
            a = float(first[field])
            b = float(final[field])
            if (a < 0 < b) or (b < 0 < a):
                sign_flips.append({
                    "observation_month": r["observation_month"],
                    "series": label,
                    "first": a,
                    "final": b,
                })

    result = {
        "schema_version": "market-top-ng3-finalized-panel-1986-1988-1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "PASS" if all(checks.values()) else "PARTIAL",
        "research_only": True,
        "production_effect": "none",
        "purpose": "source/revision engineering only; no market outcome test",
        "revision_rule": (
            "Use the PPI report four observation-months after the initial report "
            "as the period-finalized vintage, matching the documented four-month "
            "revision convention."
        ),
        "checks": checks,
        "summary": {
            "months": len(rows),
            "complete_rows": len(complete_rows),
            "ambiguous_rows": len(rows) - len(complete_rows),
            "finished_goods_revised_gt_0_05pp": len(fg_changed),
            "intermediate_goods_revised_gt_0_05pp": len(im_changed),
            "sign_flips": len(sign_flips),
        },
        "sign_flips": sign_flips,
        "rows": rows,
        "boundary": {
            "market_outcome_test_authorized": False,
            "faster_ng3_formula_preregistered": False,
            "v1_reopened": False,
        },
    }

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)
        f.write("\n")

    print(json.dumps({k: result[k] for k in ("status", "checks", "summary", "sign_flips")}, indent=2))
    for r in rows:
        print(
            r["observation_month"],
            r["first_publication"].get("finished_goods_mom_sa_pct"),
            r["four_month_revision"].get("finished_goods_mom_sa_pct"),
            r["revision_delta_pp"]["finished_goods"],
            "|",
            r["first_publication"].get("intermediate_goods_mom_sa_pct"),
            r["four_month_revision"].get("intermediate_goods_mom_sa_pct"),
            r["revision_delta_pp"]["intermediate_goods"],
            r["status"],
        )


if __name__ == "__main__":
    main()
