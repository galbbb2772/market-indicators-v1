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


def _numbers_in_text(text: str) -> list[float]:
    t = _norm(text).replace(",", "")
    out = []
    for tok in re.findall(r"[+-]?(?:[0-9]+[.][0-9]+|[.][0-9]+|[0-9]+)", t):
        try:
            out.append(float(tok))
        except ValueError:
            pass
    return out


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
    fallback = []
    for idx, page in enumerate(reader.pages[:18]):
        text = page.extract_text() or ""
        low = _norm(text).lower()
        if (
            "table 1." in low
            and "producer price indexes" in low
            and "stage of processing" in low
        ):
            return idx, page

        # Some archived PDFs lose the table title in text extraction. Use
        # structural fingerprints of the aggregate stage-of-processing table.
        try:
            layout = page.extract_text(extraction_mode="layout") or ""
        except TypeError:
            layout = text
        q = _norm(layout).lower()
        score = 0
        if "finished goods" in q:
            score += 1
        if "intermediate materials" in q:
            score += 1
        if "relative importance" in q:
            score += 2
        if "unadjusted" in q:
            score += 1
        if "seasonally adjusted" in q:
            score += 1
        if "crude materials" in q:
            score += 1
        if score >= 6:
            fallback.append((score, idx, page))

    if fallback:
        fallback.sort(key=lambda x: (-x[0], x[1]))
        _, idx, page = fallback[0]
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


def _label_prefix(text: str, label: str) -> bool:
    t = _norm(text).lower().rstrip(".")
    if label == "finished_goods":
        base = "finished goods"
    elif label == "intermediate_goods":
        base = "intermediate materials, supplies and components"
    else:
        raise ValueError(label)

    if t == base:
        return True
    if not t.startswith(base):
        return False

    tail = t[len(base):].lstrip(" .:-")
    # Accept a combined row only when the label is followed by a number,
    # never a named subcomponent such as "Finished goods, excluding foods".
    return bool(re.match(r"^[+-]?(?:[0-9]|[.])", tail))


def _row_spans(
    spans: list[dict],
    anchor_y: float,
    *,
    y_tol: float = 1.55,
) -> list[dict]:
    return [
        s
        for s in spans
        if s["font_size"] >= 6.0
        and abs(float(s["y"]) - anchor_y) <= y_tol
    ]


FIELD_ORDER = (
    "relative_importance",
    "january_level_nsa",
    "previous_month_level_nsa",
    "current_month_level_nsa",
    "yoy_nsa_pct",
    "mom_nsa_pct",
    "sa_prev2_to_prev1",
    "sa_prev1_to_current",
    "sa_current_aux",
)


def _start_field_for_x(x: float) -> int | None:
    if x < 180:
        return 0
    if 265 <= x < 320:
        return 0
    if 320 <= x < 350:
        return 1
    if 350 <= x < 380:
        return 2
    if 380 <= x < 415:
        return 3
    if 415 <= x < 445:
        return 4
    if 445 <= x < 475:
        return 5
    if 475 <= x < 505:
        return 6
    if 505 <= x < 532:
        return 7
    if 532 <= x < 565:
        return 8
    return None


def _assign_row_tokens(row: list[dict], label: str) -> dict:
    candidates: dict[str, list[dict]] = {
        name: [] for name in FIELD_ORDER
    }

    for s in row:
        text = _norm(s["text"])
        nums = _numbers_in_text(text)
        if not nums:
            continue

        if _label_prefix(text, label):
            base = (
                "finished goods"
                if label == "finished_goods"
                else "intermediate materials, supplies and components"
            )
            tail = text.lower().split(base, 1)[1]
            nums = _numbers_in_text(tail)
            start = 0
        else:
            start = _start_field_for_x(float(s["x"]))

        if start is None or not nums:
            continue

        # Historical PDFs sometimes emit all remaining printed cells as one
        # text object. Map its numeric tokens in left-to-right column order.
        for offset, value in enumerate(nums):
            idx = start + offset
            if idx >= len(FIELD_ORDER):
                break
            name = FIELD_ORDER[idx]
            candidates[name].append(
                {
                    "value": float(value),
                    "source_text": text,
                    "source_x": round(float(s["x"]), 3),
                    "source_y": round(float(s["y"]), 3),
                    "token_offset": offset,
                }
            )

    resolved = {}
    for name in FIELD_ORDER:
        vals = candidates[name]
        # Duplicate extraction objects with the same printed value are benign.
        unique = {}
        for item in vals:
            unique.setdefault(round(float(item["value"]), 9), item)
        vals = list(unique.values())
        if len(vals) == 1:
            resolved[name] = {"status": "PARSED", **vals[0]}
        else:
            resolved[name] = {
                "status": "AMBIGUOUS_COLUMN",
                "candidates": vals,
            }
    return resolved


def parse_table1_aggregate_geometry(
    spans: list[dict],
    label: str,
) -> dict:
    if label not in {"finished_goods", "intermediate_goods"}:
        raise ValueError(label)

    label_candidates = [
        s
        for s in spans
        if s["x"] < 190
        and s["font_size"] >= 6.0
        and _label_prefix(s["text"], label)
    ]

    # Collapse duplicated PDF text objects at effectively the same row.
    by_y = {}
    for s in label_candidates:
        by_y.setdefault(round(float(s["y"]), 1), s)
    labels = list(by_y.values())

    diagnostics = []
    good = []
    for anchor in labels:
        row = _row_spans(spans, float(anchor["y"]))
        parsed = _assign_row_tokens(row, label)
        required = FIELD_ORDER[:6]

        if not all(
            parsed[name]["status"] == "PARSED"
            for name in required
        ):
            diagnostics.append(
                {
                    "status": "COLUMN_GEOMETRY_INCOMPLETE",
                    "anchor": {
                        "text": anchor["text"],
                        "x": round(float(anchor["x"]), 3),
                        "y": round(float(anchor["y"]), 3),
                    },
                    "columns": parsed,
                }
            )
            continue

        values = {
            name: float(parsed[name]["value"])
            for name in required
        }
        plausible = (
            50.0 <= values["relative_importance"] <= 110.0
            and values["january_level_nsa"] > 20
            and values["previous_month_level_nsa"] > 20
            and values["current_month_level_nsa"] > 20
            and abs(values["yoy_nsa_pct"]) <= 50
            and abs(values["mom_nsa_pct"]) <= 25
        )
        if not plausible:
            diagnostics.append(
                {
                    "status": "ROW_PLAUSIBILITY_FAIL",
                    "values": values,
                }
            )
            continue

        good.append(
            {
                "status": "PARSED_GEOMETRY",
                **values,
                "label": {
                    "text": anchor["text"],
                    "x": round(float(anchor["x"]), 3),
                    "y": round(float(anchor["y"]), 3),
                },
                "columns": parsed,
            }
        )

    if len(good) == 1:
        return good[0]
    if len(good) == 0 and len(labels) == 1 and len(diagnostics) == 1:
        return diagnostics[0]

    return {
        "status": "AGGREGATE_ROW_NOT_UNIQUE",
        "label_candidates": len(labels),
        "valid_rows": len(good),
        "diagnostics": diagnostics[:4],
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
