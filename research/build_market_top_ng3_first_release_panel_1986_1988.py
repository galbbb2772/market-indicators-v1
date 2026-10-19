from __future__ import annotations

import argparse
import io
import json
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone

import requests
from pypdf import PdfReader

MONTH_NAMES = [
    "January","February","March","April","May","June",
    "July","August","September","October","November","December",
]
MONTH_NUM = {m.lower(): i + 1 for i, m in enumerate(MONTH_NAMES)}
PANEL_MONTHS = [(y, m) for y in (1986, 1987, 1988) for m in range(1, 13)]
SOURCE_MONTHS = [(1985, 12)] + PANEL_MONTHS


def pdf_url(year: int, month: int) -> str:
    return (
        "https://fraser.stlouisfed.org/files/docs/publications/ppi/1980s/"
        f"ppi_{month:02d}{year}.pdf"
    )


def fetch_text(year: int, month: int) -> dict:
    url = pdf_url(year, month)
    try:
        r = requests.get(
            url,
            timeout=(5, 25),
            headers={"User-Agent": "market-top-ng3-first-release-panel/1.0"},
        )
        r.raise_for_status()
        reader = PdfReader(io.BytesIO(r.content))
        flow_pages = []
        layout_pages = []
        for i, page in enumerate(reader.pages):
            if i >= 7:
                break
            flow_pages.append(page.extract_text() or "")
            try:
                layout_pages.append(page.extract_text(extraction_mode="layout") or "")
            except TypeError:
                layout_pages.append(page.extract_text() or "")
        return {
            "source_month": f"{year:04d}-{month:02d}",
            "url": url,
            "status": "SOURCE_TEXT_RECOVERED",
            "text_flow": "\n".join(flow_pages),
            "text_layout": "\n".join(layout_pages),
        }
    except Exception as exc:
        return {
            "source_month": f"{year:04d}-{month:02d}",
            "url": url,
            "status": "SOURCE_UNAVAILABLE",
            "error": repr(exc),
            "text_flow": "",
            "text_layout": "",
        }


def norm(s: str) -> str:
    s = s.replace("\\u00ad", "")
    # Repair line-wrap hyphenation such as "per- cent" and OCR spacing such as "0 .4".
    s = re.sub(r"(?<=\w)-\s+(?=\w)", "", s)
    s = re.sub(r"(?<=\d)\s+\.(?=\d)", ".", s)
    s = re.sub(r"\s+", " ", s)
    return s.strip()

def movement_segment(text: str, year: int, month: int) -> str:
    x = norm(text)
    label = f"Price Movements {MONTH_NAMES[month-1]} {year}"
    i = x.lower().find(label.lower())
    if i < 0:
        # tolerate OCR punctuation/layout loss
        i = x.lower().find("price movements")
    if i < 0:
        return ""
    y = x[i:]
    j = y.lower().find("table a.")
    if j > 0:
        y = y[:j]
    return y[:12000]


UP = (
    "moved up","rose","increased","advanced","climbed","edged up","turned up",
    "surged","jumped","was up","were up","gained",
)
DOWN = (
    "moved down","fell","fall","decreased","declined","dropped","edged down",
    "turned down","was down","were down","slipped","eased",
)
ZERO = (
    "showed no change","was unchanged","remained unchanged",
    "virtually unchanged","was virtually unchanged","no change",
)


def signed_first_percent(body: str) -> float | None:
    b = body.lower()
    first_sentence = re.split(r"(?<=[.!?])\s+", b, maxsplit=1)[0]
    # A headline zero-change sentence must win over a later sentence that
    # describes the previous month (for example, "fell 0.2 percent in October").
    if any(z in first_sentence for z in ZERO):
        return 0.0

    m = re.search(r"(\d+(?:\.\d+)?)\s*(?:-| )?percent", first_sentence)
    search_text = first_sentence
    if not m:
        m = re.search(r"(\d+(?:\.\d+)?)\s*(?:-| )?percent", b)
        search_text = b
    if not m:
        return None

    n = float(m.group(1))
    prefix = search_text[:m.start()]
    up_pos = max([prefix.rfind(v) for v in UP])
    down_pos = max([prefix.rfind(v) for v in DOWN])
    if down_pos > up_pos:
        return -n
    if up_pos >= 0:
        return n
    return None


def parse_first_values(text: str, year: int, month: int) -> dict:
    seg = movement_segment(text, year, month)
    if not seg:
        return {"status": "MOVEMENT_SEGMENT_NOT_FOUND"}

    fg_match = re.search(
        r"The Producer Price Index for Finished Goods(?P<body>.{0,700})",
        seg,
        flags=re.I,
    )
    fg = signed_first_percent(fg_match.group("body")) if fg_match else None

    im_patterns = [
        r"The Producer Price Index for Intermediate Materials,?\s*Supplies,?\s*and Components(?P<body>.{0,700})",
        r"The index for Intermediate Materials,?\s*Supplies,?\s*and Components(?P<body>.{0,700})",
        r"Prices received by (?:domestic )?producers of intermediate goods(?P<body>.{0,700})",
        r"(?:The )?Intermediate Goods Price Index(?P<body>.{0,700})",
        r"Intermediate goods prices(?P<body>.{0,700})",
        r"The index for intermediate goods(?P<body>.{0,700})",
    ]
    im_candidates = []
    current_month_name = MONTH_NAMES[month - 1].lower()
    for pat in im_patterns:
        for match in re.finditer(pat, seg, flags=re.I):
            body = match.group("body")
            context = body[:350].lower()
            annual_context = bool(
                re.search(
                    r"(?:12 months|over the year|year earlier|"
                    r"from\s+[a-z]+\s+\d{4}\s+to\s+[a-z]+\s+\d{4})",
                    context[:260],
                    flags=re.I,
                )
            )
            # The stage-of-processing headline paragraph is the first portion of
            # Price Movements. Its first intermediate-goods statement is a
            # current-month observation even when the month name is omitted.
            lead_statement = match.start() < 1800
            temporal_match = (
                current_month_name in context
                or "over the month" in context
                or ("from " in context and " to " in context)
                or "this month" in context
                or lead_statement
            )
            value = signed_first_percent(body)
            if value is not None and temporal_match and not annual_context:
                im_candidates.append((match.start(), value, match.group(0)[:500]))
    im_candidates.sort(key=lambda x: x[0])
    im = im_candidates[0][1] if im_candidates else None
    im_evidence = im_candidates[0][2] if im_candidates else None

    return {
        "status": "PARSED" if fg is not None and im is not None else "AMBIGUOUS",
        "finished_goods_mom_sa_pct": fg,
        "intermediate_goods_mom_sa_pct": im,
        "intermediate_match_excerpt": im_evidence,
        "segment_excerpt": seg[:1800],
    }



def parse_table_a_current(text_layout: str, year: int, month: int) -> dict:
    lines = text_layout.splitlines()
    heading_re = re.compile(
        r"\bTable\s+A[.\-:]?\s*Percent changes from preceding month",
        flags=re.I,
    )
    start = next(
        (i for i, line in enumerate(lines) if heading_re.search(line)),
        None,
    )
    if start is None:
        return {"status": "TABLE_A_NOT_FOUND"}

    end = next(
        (
            i for i in range(start + 1, len(lines))
            if re.match(r"^\s*Table B\.", lines[i], flags=re.I)
        ),
        min(len(lines), start + 260),
    )
    block = lines[start:end]

    year_re = re.compile(rf"^\s*{year}\s*:\s*$")
    year_start = next(
        (i for i, line in enumerate(block) if year_re.match(line)),
        None,
    )
    if year_start is None:
        return {"status": "YEAR_SECTION_NOT_FOUND"}

    year_end = next(
        (
            i for i in range(year_start + 1, len(block))
            if re.match(r"^\s*\d{4}\s*:\s*$", block[i])
        ),
        len(block),
    )
    section = block[year_start + 1:year_end]

    month_name = MONTH_NAMES[month - 1]
    row_re = re.compile(rf"^\s*{month_name}\b", flags=re.I)
    row_index = next(
        (i for i, line in enumerate(section) if row_re.search(line)),
        None,
    )
    if row_index is None:
        return {
            "status": "MONTH_ROW_NOT_FOUND",
            "year_section_excerpt": [norm(x)[:500] for x in section[:40]],
        }

    # Historical PDF extraction can wrap one printed row onto multiple text lines.
    row_lines = [section[row_index]]
    for nxt in section[row_index + 1:row_index + 4]:
        if re.match(r"^\s*(?:" + "|".join(MONTH_NAMES) + r")\b", nxt, flags=re.I):
            break
        if re.match(r"^\s*\d{4}\s*:\s*$", nxt):
            break
        # Only append numeric-looking continuation lines. Stop before footnotes/prose.
        if re.search(r"[A-Za-z]{2,}", nxt):
            break
        row_lines.append(nxt)

    merged = " ".join(row_lines)
    pos = row_re.search(merged)
    tail = merged[pos.end():] if pos else merged
    # Permit historical forms such as .4, -.3, 0, 1.2r, and .5p.
    # Do not pre-split before decimal points: OCR strings such as "-.1.5"
    # naturally tokenize as "-.1", ".5", while "1.4" must remain one value.
    num_re = re.compile(
        r"[+-]?(?:\d+\.\d+|\.\d+|\d+)(?:[rp])?",
        flags=re.I,
    )
    vals = []
    raw_tokens = num_re.findall(tail)
    for token in raw_tokens:
        token = re.sub(r"[rp]$", "", token, flags=re.I)
        try:
            vals.append(float(token))
        except ValueError:
            pass

    if len(vals) < 9:
        return {
            "status": "ROW_NUMERIC_COLUMNS_INCOMPLETE",
            "numeric_columns_found": len(vals),
            "raw_numeric_tokens": raw_tokens,
            "row_excerpt": norm(merged)[:1400],
        }

    return {
        "status": "PARSED",
        "finished_goods_mom_sa_pct": vals[0],
        "intermediate_goods_mom_sa_pct": vals[3],
        "numeric_columns_found": len(vals),
        "all_numeric_columns": vals[:9],
        "row_excerpt": norm(merged)[:1400],
    }


def resolve_first_publication(narrative: dict, table_a: dict) -> dict:
    nfg = narrative.get("finished_goods_mom_sa_pct")
    nim = narrative.get("intermediate_goods_mom_sa_pct")
    tfg = table_a.get("finished_goods_mom_sa_pct")
    tim = table_a.get("intermediate_goods_mom_sa_pct")

    table_complete = tfg is not None and tim is not None
    narrative_complete = nfg is not None and nim is not None

    if narrative_complete:
        fg_conflict = (
            table_complete
            and abs(float(nfg) - float(tfg)) > 0.051
        )
        im_conflict = (
            table_complete
            and abs(float(nim) - float(tim)) > 0.051
        )
        if table_complete and not fg_conflict and not im_conflict:
            status = "VERIFIED_DUAL_PATH"
        elif table_complete and (fg_conflict or im_conflict):
            status = "NARRATIVE_PRIMARY_TABLE_OCR_CONFLICT"
        else:
            status = "NARRATIVE_RECOVERED"
        return {
            "status": status,
            "finished_goods_mom_sa_pct": float(nfg),
            "intermediate_goods_mom_sa_pct": float(nim),
            "fg_conflict": bool(fg_conflict),
            "im_conflict": bool(im_conflict),
            "primary_source_path": "CURRENT_REPORT_HEADLINE_NARRATIVE",
        }

    if table_complete:
        return {
            "status": "TABLE_A_ONLY_PROVISIONAL",
            "finished_goods_mom_sa_pct": float(tfg),
            "intermediate_goods_mom_sa_pct": float(tim),
            "fg_conflict": False,
            "im_conflict": False,
            "primary_source_path": "TABLE_A_CURRENT_MONTH_ROW",
        }

    return {
        "status": "AMBIGUOUS",
        "finished_goods_mom_sa_pct": None,
        "intermediate_goods_mom_sa_pct": None,
        "fg_conflict": False,
        "im_conflict": False,
        "primary_source_path": None,
    }


def parse_schedule(text: str, source_year: int, source_month: int) -> list[dict]:
    x = norm(text)
    i = x.lower().find("scheduled release dates")
    if i < 0:
        return []
    y = x[i:i+2200]
    # skip headings and capture Month ReleaseMonth Day pairs.
    pat = re.compile(
        r"\b(" + "|".join(MONTH_NAMES) + r")\b\s+"
        r"(" + "|".join(MONTH_NAMES) + r")\s+(\d{1,2})\b",
        flags=re.I,
    )
    out = []
    for a, b, d in pat.findall(y):
        obs_m = MONTH_NUM[a.lower()]
        rel_m = MONTH_NUM[b.lower()]
        obs_y = source_year + (1 if obs_m <= source_month else 0)
        rel_y = obs_y + (1 if rel_m < obs_m else 0)
        try:
            release = f"{rel_y:04d}-{rel_m:02d}-{int(d):02d}"
        except Exception:
            continue
        out.append({
            "observation_month": f"{obs_y:04d}-{obs_m:02d}",
            "release_date": release,
            "schedule_source_month": f"{source_year:04d}-{source_month:02d}",
        })
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", default="market_top_ng3_first_release_panel_1986_1988.json")
    args = ap.parse_args()

    docs = {}
    with ThreadPoolExecutor(max_workers=6) as ex:
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
    for year, month in PANEL_MONTHS:
        key = f"{year:04d}-{month:02d}"
        d = docs.get(key, {})
        if d.get("status") == "SOURCE_TEXT_RECOVERED":
            narrative = parse_first_values(d.get("text_flow", ""), year, month)
            table_a = parse_table_a_current(d.get("text_layout", ""), year, month)
            resolved = resolve_first_publication(narrative, table_a)
        else:
            narrative = {"status": "SOURCE_UNAVAILABLE"}
            table_a = {"status": "SOURCE_UNAVAILABLE"}
            resolved = {"status": "SOURCE_UNAVAILABLE"}
        rows.append({
            "observation_month": key,
            "publication_pdf": pdf_url(year, month),
            "source_status": d.get("status", "SOURCE_UNAVAILABLE"),
            "release": schedule.get(key, {
                "observation_month": key,
                "release_date": None,
                "schedule_source_month": None,
            }),
            "narrative_extraction": narrative,
            "table_a_extraction": table_a,
            "first_publication": resolved,
        })

    known = {r["observation_month"]: r for r in rows}
    checks = {
        "all_36_source_pdfs_recovered": all(r["source_status"] == "SOURCE_TEXT_RECOVERED" for r in rows),
        "jan_1987_release": known["1987-01"]["release"]["release_date"] == "1987-02-13",
        "jan_1987_fg": known["1987-01"]["first_publication"].get("finished_goods_mom_sa_pct") == 0.6,
        "jan_1987_im": known["1987-01"]["first_publication"].get("intermediate_goods_mom_sa_pct") == 0.9,
        "may_1987_release": known["1987-05"]["release"]["release_date"] == "1987-06-12",
        "may_1987_fg": known["1987-05"]["first_publication"].get("finished_goods_mom_sa_pct") == 0.3,
        "may_1987_im": known["1987-05"]["first_publication"].get("intermediate_goods_mom_sa_pct") == 0.5,
    }

    table_complete = all(
        r["first_publication"].get("finished_goods_mom_sa_pct") is not None
        and r["first_publication"].get("intermediate_goods_mom_sa_pct") is not None
        for r in rows
    )
    dual_verified = sum(
        r["first_publication"]["status"] == "VERIFIED_DUAL_PATH"
        for r in rows
    )
    narrative_conflicts = sum(
        r["first_publication"]["status"] == "NARRATIVE_PRIMARY_TABLE_OCR_CONFLICT"
        for r in rows
    )

    result = {
        "schema_version": "market-top-ng3-first-release-panel-1986-1988-2",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": (
            "COMPLETE_SOURCE_PANEL"
            if all(checks.values()) and table_complete
            else "PARTIAL"
        ),
        "source_layer_status": "PASS" if all(checks.values()) else "FAIL",
        "research_only": True,
        "production_effect": "none",
        "purpose": "source engineering only; no market outcomes or score thresholds",
        "checks": checks,
        "summary": {
            "months": 36,
            "source_recovered": sum(
                r["source_status"] == "SOURCE_TEXT_RECOVERED" for r in rows
            ),
            "release_dates_recovered": sum(
                bool(r["release"]["release_date"]) for r in rows
            ),
            "table_a_values_complete": bool(table_complete),
            "narrative_values_complete": all(
                r["narrative_extraction"].get("finished_goods_mom_sa_pct") is not None
                and r["narrative_extraction"].get("intermediate_goods_mom_sa_pct") is not None
                for r in rows
            ),
            "first_values_resolved": sum(
                r["first_publication"].get("finished_goods_mom_sa_pct") is not None
                and r["first_publication"].get("intermediate_goods_mom_sa_pct") is not None
                for r in rows
            ),
            "dual_path_verified": dual_verified,
            "narrative_conflicts": narrative_conflicts,
            "ambiguous_rows": sum(
                r["first_publication"]["status"] == "AMBIGUOUS"
                for r in rows
            ),
            "narrative_only_recovered": sum(
                r["first_publication"]["status"] == "NARRATIVE_RECOVERED"
                for r in rows
            ),
        },
        "rows": rows,
        "boundary": {
            "finalized_values_complete": False,
            "market_outcome_test_authorized": False,
            "faster_ng3_formula_preregistered": False,
            "v1_reopened": False,
        },
    }

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)
        f.write("\n")

    print(json.dumps({k: result[k] for k in ("status","source_layer_status","checks","summary")}, indent=2))
    for r in rows:
        print(
            "TABLE_A_ROW",
            r["observation_month"],
            json.dumps(r["table_a_extraction"], ensure_ascii=False),
        )
    for r in rows:
        fp = r["first_publication"]
        print(
            r["observation_month"],
            r["release"].get("release_date"),
            fp.get("finished_goods_mom_sa_pct"),
            fp.get("intermediate_goods_mom_sa_pct"),
            fp.get("status"),
        )

    for r in rows:
        fp = r["first_publication"]
        im = fp.get("intermediate_goods_mom_sa_pct")
        if (
            fp.get("status") == "AMBIGUOUS"
            or (im is not None and abs(float(im)) >= 3.0)
        ):
            print(
                "NARRATIVE_DIAGNOSTIC",
                r["observation_month"],
                json.dumps(r["narrative_extraction"], ensure_ascii=False),
            )


if __name__ == "__main__":
    main()
