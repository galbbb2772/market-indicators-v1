from __future__ import annotations

import argparse
import io
import json
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone

import requests
from pypdf import PdfReader

try:
    from research.build_market_top_ng3_first_release_panel_1986_1988 import (
        PANEL_MONTHS,
        SOURCE_MONTHS,
        parse_schedule,
        pdf_url,
    )
except ModuleNotFoundError:
    from build_market_top_ng3_first_release_panel_1986_1988 import (
        PANEL_MONTHS,
        SOURCE_MONTHS,
        parse_schedule,
        pdf_url,
    )


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def _one_number(text: str) -> float | None:
    t = _norm(text).replace(",", "")
    if not re.fullmatch(r"[+-]?(?:\d+\.\d+|\.\d+|\d+)", t):
        return None
    try:
        return float(t)
    except ValueError:
        return None


def _collect_spans(page) -> list[dict]:
    spans: list[dict] = []

    def visitor(text, cm, tm, font_dict, font_size):
        t = _norm(text)
        if not t:
            return
        spans.append(
            {
                "text": t,
                "x": float(tm[4]),
                "y": float(tm[5]),
                "font_size": float(font_size or 0.0),
            }
        )

    page.extract_text(visitor_text=visitor)
    return spans


def _find_table1_page(reader: PdfReader):
    for idx, page in enumerate(reader.pages[:18]):
        text = page.extract_text() or ""
        low = text.lower()
        if (
            "table 1." in low
            and "producer price indexes" in low
            and "stage of processing" in low
        ):
            return idx, page
    return None, None


def fetch_nsa_document(year: int, month: int) -> dict:
    url = pdf_url(year, month)
    try:
        r = requests.get(
            url,
            timeout=(6, 35),
            headers={"User-Agent": "market-top-ng3-nsa-panel/2.0"},
        )
        r.raise_for_status()
        reader = PdfReader(io.BytesIO(r.content))

        layout_pages = []
        for page in reader.pages[:7]:
            try:
                layout_pages.append(page.extract_text(extraction_mode="layout") or "")
            except TypeError:
                layout_pages.append(page.extract_text() or "")

        page_idx, table1_page = _find_table1_page(reader)
        spans = _collect_spans(table1_page) if table1_page is not None else []

        return {
            "source_month": f"{year:04d}-{month:02d}",
            "url": url,
            "status": "SOURCE_RECOVERED",
            "schedule_text_layout": "\n".join(layout_pages),
            "table1_page_zero_based": page_idx,
            "table1_spans": spans,
        }
    except Exception as exc:
        return {
            "source_month": f"{year:04d}-{month:02d}",
            "url": url,
            "status": "SOURCE_UNAVAILABLE",
            "error": repr(exc),
            "schedule_text_layout": "",
            "table1_page_zero_based": None,
            "table1_spans": [],
        }


def _aggregate_label_match(text: str, label: str) -> bool:
    t = _norm(text).lower().rstrip(".")
    if label == "finished_goods":
        return t == "finished goods"
    if label == "intermediate_goods":
        return t == "intermediate materials, supplies and components"
    raise ValueError(label)


def _value_in_band(
    spans: list[dict],
    y: float,
    x_lo: float,
    x_hi: float,
    *,
    y_tol: float = 1.25,
) -> dict:
    candidates = []
    for s in spans:
        if s["font_size"] < 6.0:
            continue
        if not (x_lo <= s["x"] < x_hi):
            continue
        if abs(s["y"] - y) > y_tol:
            continue
        value = _one_number(s["text"])
        if value is None:
            continue
        candidates.append(
            {
                "value": value,
                "x": round(s["x"], 3),
                "y": round(s["y"], 3),
                "text": s["text"],
                "font_size": round(s["font_size"], 3),
            }
        )

    if len(candidates) != 1:
        return {
            "status": "AMBIGUOUS_COLUMN",
            "candidates": candidates,
            "x_band": [x_lo, x_hi],
        }
    return {
        "status": "PARSED",
        **candidates[0],
        "x_band": [x_lo, x_hi],
    }


def parse_table1_aggregate_geometry(spans: list[dict], label: str) -> dict:
    if label not in {"finished_goods", "intermediate_goods"}:
        raise ValueError(label)

    labels = [
        s
        for s in spans
        if s["x"] < 180
        and s["font_size"] >= 6.0
        and _aggregate_label_match(s["text"], label)
    ]
    if len(labels) != 1:
        return {
            "status": "AGGREGATE_LABEL_NOT_UNIQUE",
            "label_count": len(labels),
            "labels": [
                {
                    "text": s["text"],
                    "x": round(s["x"], 3),
                    "y": round(s["y"], 3),
                }
                for s in labels
            ],
        }

    anchor = labels[0]
    y = float(anchor["y"])

    # Column bands are deliberately broad enough for the 1986-1988 layouts
    # but separated by the printed column centers observed in the source PDFs.
    # Small-font superscript footnote markers are discarded above.
    bands = {
        "relative_importance": (270.0, 320.0),
        "january_level_nsa": (320.0, 350.0),
        "previous_month_level_nsa": (350.0, 380.0),
        "current_month_level_nsa": (380.0, 415.0),
        "yoy_nsa_pct": (415.0, 445.0),
        "mom_nsa_pct": (445.0, 475.0),
    }
    parsed = {name: _value_in_band(spans, y, *band) for name, band in bands.items()}

    required = (
        "relative_importance",
        "january_level_nsa",
        "previous_month_level_nsa",
        "current_month_level_nsa",
        "yoy_nsa_pct",
        "mom_nsa_pct",
    )
    if not all(parsed[name]["status"] == "PARSED" for name in required):
        return {
            "status": "COLUMN_GEOMETRY_INCOMPLETE",
            "label": {
                "text": anchor["text"],
                "x": round(anchor["x"], 3),
                "y": round(anchor["y"], 3),
            },
            "columns": parsed,
        }

    values = {name: float(parsed[name]["value"]) for name in required}

    # Fail closed on physically implausible column assignment. This catches
    # accidental footnotes or neighboring columns without using market outcomes.
    if not (50.0 <= values["relative_importance"] <= 110.0):
        return {"status": "RELATIVE_IMPORTANCE_IMPLAUSIBLE", "values": values}
    if not (
        values["january_level_nsa"] > 20
        and values["previous_month_level_nsa"] > 20
        and values["current_month_level_nsa"] > 20
    ):
        return {"status": "NSA_LEVEL_IMPLAUSIBLE", "values": values}
    if abs(values["yoy_nsa_pct"]) > 50 or abs(values["mom_nsa_pct"]) > 25:
        return {"status": "RATE_IMPLAUSIBLE", "values": values}

    return {
        "status": "PARSED_GEOMETRY",
        **values,
        "label": {
            "text": anchor["text"],
            "x": round(anchor["x"], 3),
            "y": round(anchor["y"], 3),
        },
        "columns": parsed,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--output",
        default="market_top_ng3_first_release_nsa_panel_1986_1988.json",
    )
    args = ap.parse_args()

    docs = {}
    with ThreadPoolExecutor(max_workers=8) as ex:
        futs = {
            ex.submit(fetch_nsa_document, y, m): (y, m)
            for y, m in SOURCE_MONTHS
        }
        for fut in as_completed(futs):
            d = fut.result()
            docs[d["source_month"]] = d

    schedule = {}
    for source_month, d in sorted(docs.items()):
        if d["status"] != "SOURCE_RECOVERED":
            continue
        sy, sm = map(int, source_month.split("-"))
        for item in parse_schedule(d["schedule_text_layout"], sy, sm):
            schedule[item["observation_month"]] = item

    rows = []
    for y, m in PANEL_MONTHS:
        key = f"{y:04d}-{m:02d}"
        d = docs[key]
        finished = parse_table1_aggregate_geometry(
            d["table1_spans"], "finished_goods"
        )
        intermediate = parse_table1_aggregate_geometry(
            d["table1_spans"], "intermediate_goods"
        )
        release = schedule.get(key, {})
        complete = (
            finished.get("status") == "PARSED_GEOMETRY"
            and intermediate.get("status") == "PARSED_GEOMETRY"
            and bool(release.get("release_date"))
        )
        rows.append(
            {
                "observation_month": key,
                "release_date": release.get("release_date"),
                "publication_pdf": pdf_url(y, m),
                "table1_page_zero_based": d.get("table1_page_zero_based"),
                "reference_basis_note": (
                    "native basis printed in contemporaneous report; YoY is "
                    "taken from the same publication row"
                ),
                "finished_goods": finished,
                "intermediate_goods": intermediate,
                "status": "COMPLETE" if complete else "AMBIGUOUS",
            }
        )

    known = {r["observation_month"]: r for r in rows}
    may = known["1987-05"]
    feb86 = known["1986-02"]
    mar88 = known["1988-03"]
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
        "feb_1986_geometry_guard": (
            feb86["finished_goods"].get("current_month_level_nsa") == 292.3
            and feb86["finished_goods"].get("yoy_nsa_pct") == -0.1
        ),
        "mar_1988_geometry_guard": (
            mar88["intermediate_goods"].get("current_month_level_nsa") == 104.6
            and mar88["intermediate_goods"].get("yoy_nsa_pct") == 5.0
        ),
    }

    result = {
        "schema_version": "market-top-ng3-first-release-nsa-panel-1986-1988-2",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "PASS" if all(checks.values()) else "PARTIAL",
        "research_only": True,
        "production_effect": "none",
        "purpose": (
            "Recover contemporaneous not-seasonally-adjusted stage-of-processing "
            "levels and YoY changes using PDF coordinate geometry so footnote "
            "superscripts cannot merge into numeric columns."
        ),
        "checks": checks,
        "summary": {
            "months": len(rows),
            "source_recovered": sum(
                docs[f"{y:04d}-{m:02d}"]["status"] == "SOURCE_RECOVERED"
                for y, m in PANEL_MONTHS
            ),
            "table1_pages_found": sum(
                docs[f"{y:04d}-{m:02d}"]["table1_page_zero_based"] is not None
                for y, m in PANEL_MONTHS
            ),
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

    print(
        json.dumps(
            {k: result[k] for k in ("status", "checks", "summary")},
            indent=2,
        )
    )
    for r in rows:
        fg = r["finished_goods"]
        im = r["intermediate_goods"]
        print(
            r["observation_month"],
            r["release_date"],
            "FG", fg.get("current_month_level_nsa"), fg.get("yoy_nsa_pct"),
            "IM", im.get("current_month_level_nsa"), im.get("yoy_nsa_pct"),
            r["status"],
            fg.get("status"),
            im.get("status"),
        )


if __name__ == "__main__":
    main()
