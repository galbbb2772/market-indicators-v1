from __future__ import annotations

import argparse
import json
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone

try:
    from research.build_market_top_ng3_first_release_panel_1986_1988 import (
        PANEL_MONTHS,
        fetch_text,
        parse_first_values,
        parse_table_a_current,
        pdf_url,
        resolve_first_publication,
    )
except ModuleNotFoundError:
    from build_market_top_ng3_first_release_panel_1986_1988 import (
        PANEL_MONTHS,
        fetch_text,
        parse_first_values,
        parse_table_a_current,
        pdf_url,
        resolve_first_publication,
    )

FINAL_VINTAGE_OFFSETS = (4, 5, 6, 7)


def add_months(year: int, month: int, delta: int) -> tuple[int, int]:
    z = year * 12 + (month - 1) + delta
    return z // 12, z % 12 + 1


def consensus(values: list[tuple[str, float]]) -> dict:
    rounded = [(src, round(float(v), 1)) for src, v in values]
    counts = Counter(v for _, v in rounded)
    if not counts:
        return {"status": "NO_VALUE", "value": None, "support": 0, "sources": []}
    value, support = counts.most_common(1)[0]
    winners = [src for src, v in rounded if v == value]
    status = "CONSENSUS" if support >= 2 else "NO_CONSENSUS"
    return {
        "status": status,
        "value": value if status == "CONSENSUS" else None,
        "support": support,
        "sources": winners,
        "all_candidates": [{"source_month": s, "value": v} for s, v in rounded],
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--output",
        default="market_top_ng3_finalized_panel_1986_1988.json",
    )
    args = ap.parse_args()

    needed = set(PANEL_MONTHS)
    for y, m in PANEL_MONTHS:
        for offset in FINAL_VINTAGE_OFFSETS:
            needed.add(add_months(y, m, offset))

    docs = {}
    with ThreadPoolExecutor(max_workers=10) as ex:
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

        later = []
        fg_candidates = []
        im_candidates = []
        for offset in FINAL_VINTAGE_OFFSETS:
            sy, sm = add_months(y, m, offset)
            source_key = f"{sy:04d}-{sm:02d}"
            d = docs[source_key]
            parsed = parse_table_a_current(d["text_layout"], y, m)
            later.append(
                {
                    "offset_months": offset,
                    "source_month": source_key,
                    "source_pdf": pdf_url(sy, sm),
                    "table_a": parsed,
                }
            )
            if parsed.get("status") == "PARSED":
                if parsed.get("finished_goods_mom_sa_pct") is not None:
                    fg_candidates.append(
                        (source_key, parsed["finished_goods_mom_sa_pct"])
                    )
                if parsed.get("intermediate_goods_mom_sa_pct") is not None:
                    im_candidates.append(
                        (source_key, parsed["intermediate_goods_mom_sa_pct"])
                    )

        fg_final = consensus(fg_candidates)
        im_final = consensus(im_candidates)
        first_fg = first.get("finished_goods_mom_sa_pct")
        first_im = first.get("intermediate_goods_mom_sa_pct")
        final_fg = fg_final["value"]
        final_im = im_final["value"]
        complete = all(v is not None for v in (first_fg, first_im, final_fg, final_im))

        rows.append(
            {
                "observation_month": key,
                "first_publication_pdf": pdf_url(y, m),
                "first_publication": first,
                "finalized_consensus_window_offsets_months": list(FINAL_VINTAGE_OFFSETS),
                "later_vintages": later,
                "period_finalized": {
                    "status": (
                        "CONSENSUS"
                        if fg_final["status"] == "CONSENSUS"
                        and im_final["status"] == "CONSENSUS"
                        else "AMBIGUOUS"
                    ),
                    "finished_goods_mom_sa_pct": final_fg,
                    "intermediate_goods_mom_sa_pct": final_im,
                    "finished_goods_consensus": fg_final,
                    "intermediate_goods_consensus": im_final,
                },
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
        "all_finalized_values_consensus": all(
            r["period_finalized"]["status"] == "CONSENSUS"
            for r in rows
        ),
        "jan_1987_final_finished": (
            known["1987-01"]["period_finalized"].get("finished_goods_mom_sa_pct")
            == 0.4
        ),
        "jan_1987_final_intermediate": (
            known["1987-01"]["period_finalized"].get("intermediate_goods_mom_sa_pct")
            == 0.9
        ),
        "may_1987_final_finished": (
            known["1987-05"]["period_finalized"].get("finished_goods_mom_sa_pct")
            == -0.1
        ),
        "may_1987_final_intermediate": (
            known["1987-05"]["period_finalized"].get("intermediate_goods_mom_sa_pct")
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
        final = r["period_finalized"]
        for field, label in (
            ("finished_goods_mom_sa_pct", "finished_goods"),
            ("intermediate_goods_mom_sa_pct", "intermediate_goods"),
        ):
            a = float(first[field])
            b = float(final[field])
            if (a < 0 < b) or (b < 0 < a):
                sign_flips.append(
                    {
                        "observation_month": r["observation_month"],
                        "series": label,
                        "first": a,
                        "final": b,
                    }
                )

    result = {
        "schema_version": "market-top-ng3-finalized-panel-1986-1988-2",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "PASS" if all(checks.values()) else "PARTIAL",
        "research_only": True,
        "production_effect": "none",
        "purpose": "source/revision engineering only; no market outcome test",
        "revision_rule": (
            "Use repeated historical Table A snapshots at observation-month +4, "
            "+5, +6 and +7. A period-finalized value requires at least two "
            "independent later snapshots agreeing at the published 0.1pp precision. "
            "This rejects isolated PDF/OCR extraction errors."
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

    print(
        json.dumps(
            {k: result[k] for k in ("status", "checks", "summary", "sign_flips")},
            indent=2,
        )
    )
    for r in rows:
        first = r["first_publication"]
        final = r["period_finalized"]
        print(
            r["observation_month"],
            first.get("finished_goods_mom_sa_pct"),
            final.get("finished_goods_mom_sa_pct"),
            r["revision_delta_pp"]["finished_goods"],
            "|",
            first.get("intermediate_goods_mom_sa_pct"),
            final.get("intermediate_goods_mom_sa_pct"),
            r["revision_delta_pp"]["intermediate_goods"],
            r["status"],
        )


if __name__ == "__main__":
    main()
