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
    for tok in re.findall(r"[+-]?(?:\\d+\\.\\d+|\\.\\d+|\\d+)", t):
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

        # Some archived PDFs lose the printed table title during extraction.
        # Fall back to structural fingerprints unique to the aggregate Table 1:
        # both aggregate stage labels plus its relative-importance / adjustment
        # headers. Table 2 does not carry the aggregate relative-importance block.
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
    # A combined row span may contain the label followed immediately by the
    # numeric columns. Do not accept named subcomponents such as
    # "Finished goods, excluding foods".
    return bool(re.match(r"^[+\\-]?(?:\\d|\\.)", tail))


def _row_spans(spans: list[dict], anchor_y: float, *, y_tol: float = 1.55) -> list[dict]:
    return [
        s
        for s in spans
        if s["font_size"] >= 6.0 and abs(float(s["y"]) - anchor_y) <= y_tol
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

FIELD_CENTERS = {
    "relative_importance": 283.0,
    "january_level_nsa": 331.0,
    "previous_month_level_nsa": 361.0,
    "current_month_level_nsa": 392.0,
    "yoy_nsa_pct": 427.0,
    "mom_nsa_pct": 457.0,
    "sa_prev2_to_prev1": 488.0,
    "sa_prev1_to_current": 516.0,
    "sa_current_aux": 544.0,
}


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
    candidates: dict[str, list[dict]] = {name: [] for name in FIELD_ORDER}

    for s in row:
        text = _norm(s["text"])
        nums = _numbers_in_text(text)
        if not nums:
            continue

        # If the label and all values were emitted as one PDF text object,
        # start at relative importance. Otherwise infer the first logical
        # column from the object's x coordinate.
        if _label_prefix(text, label):
            if label == "finished_goods":
                base = "finished goods"
            else:
                base = "intermediate materials, supplies and components"
            tail = text.lower().split(base, 1)[1]
            nums = _numbers_in_text(tail)
            start = 0
        else:
            start = _start_field_for_x(float(s["x"]))

        if start is None or not nums:
            continue

        # A single PDF object can encode the rest of a printed row, e.g.
        # "287.6 290.5 290.7 -1.9 0.1 0.4 0.3 0.2". Map those tokens in
        # printed left-to-right column order.
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
        # De-duplicate the same numeric value when the PDF emits overlapping
        # text objects for the same printed cell.
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


def parse_table1_aggregate_geometry(spans: list[dict], label: str) -> dict:
    if label not in {"finished_goods", "intermediate_goods"}:
        raise ValueError(label)

    label_candidates = [
        s
        for s in spans
        if s["x"] < 190
        and s["font_size"] >= 6.0
        and _label_prefix(s["text"], label)
    ]

    # Collapse duplicate extraction objects sitting on the same printed row.
    by_y = {}
    for s in label_candidates:
        by_y.setdefault(round(float(s["y"]), 1), s)
    labels = list(by_y.values())

    parsed_rows = []
    for anchor in labels:
        row = _row_spans(spans, float(anchor["y"]))
        parsed = _assign_row_tokens(row, label)
        required = FIELD_ORDER[:6]
        if not all(parsed[name]["status"] == "PARSED" for name in required):
            parsed_rows.append(
                {
                    "status": "COLUMN_GEOMETRY_INCOMPLETE",
                    "anchor": anchor,
                    "columns": parsed,
                }
            )
            continue

        values = {name: float(parsed[name]["value"]) for name in required}
        if not (50.0 <= values["relative_importance"] <= 110.0):
            continue
        if not (
            values["january_level_nsa"] > 20
            and values["previous_month_level_nsa"] > 20
            and values["current_month_level_nsa"] > 20
        ):
            continue
        if abs(values["yoy_nsa_pct"]) > 50 or abs(values["mom_nsa_pct"]) > 25:
            continue

        parsed_rows.append(
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

    good = [x for x in parsed_rows if x["status"] == "PARSED_GEOMETRY"]
    if len(good) == 1:
        return good[0]

    return {
        "status": "AGGREGATE_ROW_NOT_UNIQUE",
        "label_candidates": len(labels),
        "valid_rows": len(good),
        "diagnostics": parsed_rows[:4],
    }

