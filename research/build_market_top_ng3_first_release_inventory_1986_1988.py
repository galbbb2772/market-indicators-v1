from __future__ import annotations

import argparse
import io
import json
import re
from datetime import datetime, timezone

import requests
from pypdf import PdfReader

MONTHS = [
    (y, m)
    for y in (1986, 1987, 1988)
    for m in range(1, 13)
]


def pdf_url(year: int, month: int) -> str:
    return (
        "https://fraser.stlouisfed.org/files/docs/publications/ppi/1980s/"
        f"ppi_{month:02d}{year}.pdf"
    )


def normalize_line(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def fetch_text(url: str) -> tuple[str | None, str | None]:
    try:
        r = requests.get(
            url,
            timeout=(5, 20),
            headers={"User-Agent": "market-top-ng3-first-release-panel/1.0"},
        )
        r.raise_for_status()
        reader = PdfReader(io.BytesIO(r.content))
        pages = []
        for i, page in enumerate(reader.pages):
            if i >= 6:
                break
            pages.append(page.extract_text() or "")
        return "\n".join(pages), None
    except Exception as exc:
        return None, repr(exc)


def candidates(text: str, needle: str) -> list[str]:
    out = []
    for raw in text.splitlines():
        line = normalize_line(raw)
        if needle.lower() in line.lower():
            out.append(line[:500])
    return out[:20]


def release_candidates(text: str) -> list[str]:
    out = []
    for raw in text.splitlines()[:300]:
        line = normalize_line(raw)
        if re.search(r"release|released|transmission", line, flags=re.I):
            out.append(line[:500])
    return out[:20]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", default="market_top_ng3_first_release_inventory_1986_1988.json")
    args = ap.parse_args()

    def one(pair):
        year, month = pair
        url = pdf_url(year, month)
        text, error = fetch_text(url)
        if text is None:
            return {
                "observation_month": f"{year:04d}-{month:02d}",
                "url": url,
                "status": "SOURCE_UNAVAILABLE",
                "error": error,
            }
        return {
            "observation_month": f"{year:04d}-{month:02d}",
            "url": url,
            "status": "SOURCE_TEXT_RECOVERED",
            "text_chars_first_6_pages": len(text),
            "release_candidates": release_candidates(text),
            "finished_goods_candidates": candidates(text, "finished goods"),
            "intermediate_candidates": candidates(text, "intermediate"),
        }

    rows = []
    with ThreadPoolExecutor(max_workers=6) as ex:
        futures = {ex.submit(one, pair): pair for pair in MONTHS}
        for fut in as_completed(futures):
            rows.append(fut.result())
    rows.sort(key=lambda x: x["observation_month"])

    result = {
        "schema_version": "market-top-ng3-first-release-inventory-1986-1988-1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "research_only": True,
        "production_effect": "none",
        "rows": rows,
        "summary": {
            "months": len(rows),
            "source_text_recovered": sum(r["status"] == "SOURCE_TEXT_RECOVERED" for r in rows),
            "source_unavailable": sum(r["status"] == "SOURCE_UNAVAILABLE" for r in rows),
        },
    }
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)
        f.write("\n")

    print(json.dumps(result["summary"], indent=2))
    for r in rows:
        print("\n==", r["observation_month"], r["status"], "==")
        if r["status"] != "SOURCE_TEXT_RECOVERED":
            print(r.get("error"))
            continue
        print("release:", r["release_candidates"][:3])
        print("finished:", r["finished_goods_candidates"][:5])
        print("intermediate:", r["intermediate_candidates"][:5])


if __name__ == "__main__":
    main()
