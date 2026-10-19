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


UP = ("moved up","rose","increased","advanced","climbed","edged up","turned up","surged","jumped")
DOWN = ("moved down","fell","decreased","declined","dropped","edged down","turned down")
ZERO = ("showed no change","was unchanged","remained unchanged","virtually unchanged","was virtually unchanged")


def signed_first_percent(body: str) -> float | None:
    b = body.lower()
    zero_pos = min([b.find(z) for z in ZERO if b.find(z) >= 0] or [10**9])
    m = re.search(r"(\d+(?:\.\d+)?)\s*(?:-| )?percent", b)
    if not m:
        return 0.0 if zero_pos < 10**9 else None
    n = float(m.group(1))
    prefix = b[:m.start()]
    # nearest directional phrase before the first percentage
    up_pos = max([prefix.rfind(v) for v in UP])
    down_pos = max([prefix.rfind(v) for v in DOWN])
    if zero_pos < m.start() and zero_pos > max(up_pos, down_pos):
        return 0.0
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
    for pat in im_patterns:
        for match in re.finditer(pat, seg, flags=re.I):
            value = signed_first_percent(match.group("body"))
            if value is not None:
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
        parsed = (
            parse_first_values(d.get("text_flow", ""), year, month)
            if d.get("status") == "SOURCE_TEXT_RECOVERED"
            else {"status": "SOURCE_UNAVAILABLE"}
        )
        rows.append({
            "observation_month": key,
            "publication_pdf": pdf_url(year, month),
            "source_status": d.get("status", "SOURCE_UNAVAILABLE"),
            "release": schedule.get(key, {
                "observation_month": key,
                "release_date": None,
                "schedule_source_month": None,
            }),
            "first_publication": parsed,
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

    result = {
        "schema_version": "market-top-ng3-first-release-panel-1986-1988-1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "PASS" if all(checks.values()) else "PARTIAL",
        "research_only": True,
        "production_effect": "none",
        "purpose": "source engineering only; no market outcomes or score thresholds",
        "checks": checks,
        "summary": {
            "months": 36,
            "source_recovered": sum(r["source_status"] == "SOURCE_TEXT_RECOVERED" for r in rows),
            "release_dates_recovered": sum(bool(r["release"]["release_date"]) for r in rows),
            "first_values_both_parsed": sum(r["first_publication"]["status"] == "PARSED" for r in rows),
            "first_values_ambiguous": sum(r["first_publication"]["status"] != "PARSED" for r in rows),
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

    print(json.dumps({k: result[k] for k in ("status","checks","summary")}, indent=2))
    for r in rows:
        fp = r["first_publication"]
        print(
            r["observation_month"],
            r["release"].get("release_date"),
            fp.get("finished_goods_mom_sa_pct"),
            fp.get("intermediate_goods_mom_sa_pct"),
            fp.get("status"),
        )


if __name__ == "__main__":
    main()
