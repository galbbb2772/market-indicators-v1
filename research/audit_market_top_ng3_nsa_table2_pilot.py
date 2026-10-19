from __future__ import annotations

import argparse
import io
import json

import requests
from pypdf import PdfReader

URL = "https://fraser.stlouisfed.org/files/docs/publications/ppi/1980s/ppi_051987.pdf"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", default="market_top_ng3_nsa_table2_pilot.json")
    args = ap.parse_args()

    r = requests.get(
        URL,
        timeout=(10, 45),
        headers={"User-Agent": "market-top-ng3-nsa-table2-pilot/1.0"},
    )
    r.raise_for_status()
    reader = PdfReader(io.BytesIO(r.content))

    pages = []
    for page_no, page in enumerate(reader.pages[:18], start=1):
        try:
            text = page.extract_text(extraction_mode="layout") or ""
        except TypeError:
            text = page.extract_text() or ""
        pages.append((page_no, text))

    hits = []
    for page_no, text in pages:
        lines = text.splitlines()
        for i, line in enumerate(lines):
            if (
                ("Table 1." in line or "Table 2." in line)
                and "Producer price indexes" in line
            ):
                excerpt = lines[max(0, i - 8): min(len(lines), i + 180)]
                hits.append(
                    {
                        "table": "Table 1" if "Table 1." in line else "Table 2",
                        "page": page_no,
                        "line_index": i,
                        "excerpt": excerpt,
                    }
                )

    found = {h["table"] for h in hits}
    result = {
        "schema_version": "market-top-ng3-nsa-table-pilot-2",
        "source_url": URL,
        "status": "TABLE1_AND_TABLE2_FOUND" if {"Table 1", "Table 2"} <= found else "PARTIAL",
        "hits": hits,
        "research_only": True,
        "production_effect": "none",
    }

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)
        f.write("\n")

    print("status =", result["status"])
    for hit in hits:
        print(hit["table"], "PAGE", hit["page"], "LINE", hit["line_index"])
        for n, line in enumerate(hit["excerpt"]):
            print(f"{n:03d}: {line}")


if __name__ == "__main__":
    main()
