from __future__ import annotations

import io
import json
import re

import requests
from pypdf import PdfReader

CASES = [
    ("1986-02", "https://fraser.stlouisfed.org/files/docs/publications/ppi/1980s/ppi_021986.pdf"),
    ("1986-09", "https://fraser.stlouisfed.org/files/docs/publications/ppi/1980s/ppi_091986.pdf"),
    ("1986-11", "https://fraser.stlouisfed.org/files/docs/publications/ppi/1980s/ppi_111986.pdf"),
    ("1987-05", "https://fraser.stlouisfed.org/files/docs/publications/ppi/1980s/ppi_051987.pdf"),
    ("1988-03", "https://fraser.stlouisfed.org/files/docs/publications/ppi/1980s/ppi_031988.pdf"),
    ("1988-05", "https://fraser.stlouisfed.org/files/docs/publications/ppi/1980s/ppi_051988.pdf"),
    ("1988-08", "https://fraser.stlouisfed.org/files/docs/publications/ppi/1980s/ppi_081988.pdf"),
]


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def page_with_table1(reader: PdfReader):
    for idx, page in enumerate(reader.pages[:16]):
        text = page.extract_text() or ""
        if "Table 1." in text and "stage of processing" in text:
            return idx, page
    return None, None


def collect(page):
    spans = []
    def visitor(text, cm, tm, font_dict, font_size):
        t = norm(text)
        if not t:
            return
        spans.append({
            "text": t,
            "x": round(float(tm[4]), 3),
            "y": round(float(tm[5]), 3),
            "font_size": round(float(font_size or 0), 3),
        })
    page.extract_text(visitor_text=visitor)
    return spans


def around_label(spans, needle: str):
    hits = [s for s in spans if needle.lower() in s["text"].lower()]
    out = []
    for h in hits:
        nearby = [
            s for s in spans
            if abs(s["y"] - h["y"]) <= 12
        ]
        nearby.sort(key=lambda s: (-s["y"], s["x"]))
        out.append({"label": h, "nearby": nearby})
    return out


def main():
    result = {}
    for key, url in CASES:
        r = requests.get(url, timeout=(10, 45), headers={"User-Agent":"ng3-table1-geometry/1.0"})
        r.raise_for_status()
        reader = PdfReader(io.BytesIO(r.content))
        page_idx, page = page_with_table1(reader)
        if page is None:
            result[key] = {"status":"TABLE1_NOT_FOUND"}
            continue
        spans = collect(page)
        result[key] = {
            "status":"FOUND",
            "page_zero_based": page_idx,
            "finished": around_label(spans, "Finished goods"),
            "intermediate": around_label(spans, "Intermediate materials"),
            "top_table_window": sorted(
                [
                    s for s in spans
                    if 560 <= s["y"] <= 730
                ],
                key=lambda s: (-s["y"], s["x"]),
            ) if key == "1988-05" else [],
        }
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
