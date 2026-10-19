from __future__ import annotations

import argparse
import json
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone

try:
    from research.build_market_top_ng3_first_release_panel_1986_1988 import (
        MONTH_NAMES,
        PANEL_MONTHS,
        SOURCE_MONTHS,
        fetch_text,
        parse_schedule,
        pdf_url,
    )
except ModuleNotFoundError:
    from build_market_top_ng3_first_release_panel_1986_1988 import (
        MONTH_NAMES,
        PANEL_MONTHS,
        SOURCE_MONTHS,
        fetch_text,
        parse_schedule,
        pdf_url,
    )


def _numbers(s: str) -> list[float]:
    vals = []
    for tok in re.findall(r"[+-]?(?:\d+\.\d+|\.\d+|\d+)", s):
        try:
            vals.append(float(tok))
        except ValueError:
            pass
    return vals


def parse_table1_aggregate(text_layout: str, label: str) -> dict:
    lines = text_layout.splitlines()
    start = next(
        (
            i for i, line in enumerate(lines)
            if "Table 1." in line
            and "Producer price indexes and percent changes by stage of processing" in line
        ),
        None,
    )
    if start is None:
        return {"status": "TABLE1_NOT_FOUND"}

    end = next(
        (
            i for i in range(start + 1, len(lines))
            if "Table 2." in lines[i]
        ),
        min(len(lines), start + 260),
    )
    block = lines[start:end]

    if label == "finished_goods":
        pat = re.compile(r"^\s*Finished goods\s{2,}", flags=re.I)
    elif label == "intermediate_goods":
        pat = re.compile(
            r"^\s*Intermediate materials,?\s+supplies and components\.?\s{2,}",
            flags=re.I,
        )
    else:
        raise ValueError(label)

    line = next((x for x in block if pat.search(x)), None)
    if line is None:
        return {"status": "ROW_NOT_FOUND"}

    vals = _numbers(line)
    if len(vals) < 6:
        return {
            "status": "ROW_NUMERIC_COLUMNS_INCOMPLETE",
            "numeric_columns_found": len(vals),
            "values": vals,
            "row_excerpt": line.strip(),
        }

    # Table 1 aggregate row layout:
    # relative importance, Jan level, previous-month level, current-month level,
    # NSA YoY percent, NSA MoM percent, then SA monthly-change columns.
    return {
        "status": "PARSED",
        "relative_importance": vals[0],
        "january_level_nsa": vals[1],
        "previous_month_level_nsa": vals[2],
        "current_month_level_nsa": vals[3],
        "yoy_nsa_pct": vals[4],
        "mom_nsa_pct": vals[5],
        "remaining_numeric_columns": vals[6:],
        "row_excerpt": line.strip(),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", default="market_top_ng3_first_release_nsa_panel_1986_1988.json")
    args = ap.parse_args()

    docs = {}
    with ThreadPoolExecutor(max_workers=8) as ex:
        futs = {ex.submit(fetch_text, y, m): (y, m) for y, m in SOURCE_MONTHS}
        for fut in as_completed(futs):
            d = fut.result()
            docs[d["source_month"]] = d

    schedule = {}
    for source_month, d in sorted(docs.items()):
        if d["status"] != "SOURCE_TEXT_RECOVERED":
            continue
        sy, sm = map(int, source_month.split("-"))
        for item in parse_schedule(d["text_layout"], sy, sm):
            schedule[item["observation_month"]] = item

    rows = []
    for y, m in PANEL_MONTHS:
        key = f"{y:04d}-{m:02d}"
        d = docs[key]
        finished = parse_table1_aggregate(d["text_layout"], "finished_goods")
        intermediate = parse_table1_aggregate(d["text_layout"], "intermediate_goods")
        release = schedule.get(key, {})
        complete = (
            finished.get("status") == "PARSED"
            and intermediate.get("status") == "PARSED"
            and bool(release.get("release_date"))
        )
        rows.append(
            {
                "observation_month": key,
                "release_date": release.get("release_date"),
                "publication_pdf": pdf_url(y, m),
                "reference_basis_note": "native basis printed in contemporaneous report",
                "finished_goods": finished,
                "intermediate_goods": intermediate,
                "status": "COMPLETE" if complete else "AMBIGUOUS",
            }
        )

    known = {r["observation_month"]: r for r in rows}
    may = known["1987-05"]
    checks = {
        "all_36_rows_complete": all(r["status"] == "COMPLETE" for r in rows),
        "all_36_release_dates": all(bool(r["release_date"]) for r in rows),
        "may_1987_release": may["release_date"] == "1987-06-12",
        "may_1987_finished_level": (
            may["finished_goods"].get("current_month_level_nsa") == 296.3
        ),
        "may_1987_finished_yoy": (
            may["finished_goods"].get("yoy_nsa_pct") == 2.6
        ),
        "may_1987_intermediate_level": (
            may["intermediate_goods"].get("current_month_level_nsa") == 312.7
        ),
        "may_1987_intermediate_yoy": (
            may["intermediate_goods"].get("yoy_nsa_pct") == 2.0
        ),
    }

    result = {
        "schema_version": "market-top-ng3-first-release-nsa-panel-1986-1988-1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "PASS" if all(checks.values()) else "PARTIAL",
        "research_only": True,
        "production_effect": "none",
        "purpose": (
            "Recover contemporaneous not-seasonally-adjusted stage-of-processing "
            "levels and YoY changes without annual seasonal-factor revision."
        ),
        "checks": checks,
        "summary": {
            "months": len(rows),
            "complete_rows": sum(r["status"] == "COMPLETE" for r in rows),
            "ambiguous_rows": sum(r["status"] != "COMPLETE" for r in rows),
        },
        "rows": rows,
        "boundary": {
            "historical_concept_bridge_to_modern_fdid_required": True,
            "cpi_release_alignment_not_yet_frozen": True,
            "faster_ng3_formula_preregistered": False,
            "market_outcome_test_authorized": False,
        },
    }

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)
        f.write("\n")

    print(json.dumps({k: result[k] for k in ("status", "checks", "summary")}, indent=2))
    for r in rows:
        fg = r["finished_goods"]
        im = r["intermediate_goods"]
        print(
            r["observation_month"],
            r["release_date"],
            "FG", fg.get("current_month_level_nsa"), fg.get("yoy_nsa_pct"),
            "IM", im.get("current_month_level_nsa"), im.get("yoy_nsa_pct"),
            r["status"],
        )


if __name__ == "__main__":
    main()
