from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone

import requests

SOURCES = {
    "1974-08": {
        "url": "https://fraser.stlouisfed.org/title/survey-current-business-46/august-1974-part-i-9638/fulltext",
        "required_phrases": [
            "current dollar cost per unit",
            "corporate profits and inventory valuation adjustment",
        ],
        "concept_label": "IVA_ONLY_LABEL_IN_UNIT_TABLE",
    },
    "1976-04": {
        "url": "https://fraser.stlouisfed.org/title/survey-current-business-46/april-1976-9659/fulltext",
        "required_phrases": [
            "corporate profits with inventory valuation and capital consumption adjustments",
        ],
        "concept_label": "IVA_PLUS_CCADJ_EXPLICIT",
    },
    "1988-03": {
        "url": "https://fraser.stlouisfed.org/title/survey-current-business-46/march-1988-10083/fulltext",
        "required_phrases": [
            "corporate profits with inventory valuation and capital consumption adjustments",
        ],
        "concept_label": "IVA_PLUS_CCADJ_EXPLICIT",
    },
}


def normalize(text: str) -> str:
    text = text.lower().replace("\u00ad", "")
    text = re.sub(r"\s+", " ", text)
    return text


def fetch(url: str) -> str:
    r = requests.get(
        url,
        timeout=45,
        headers={"User-Agent": "market-top-ng3-vintage-audit/1.0"},
    )
    r.raise_for_status()
    return r.text


def audit() -> dict:
    evidence = {}
    all_pass = True

    for vintage, spec in SOURCES.items():
        text = normalize(fetch(spec["url"]))
        checks = {
            phrase: phrase in text
            for phrase in spec["required_phrases"]
        }
        passed = all(checks.values())
        all_pass = all_pass and passed
        evidence[vintage] = {
            "url": spec["url"],
            "concept_label": spec["concept_label"],
            "required_phrase_checks": checks,
            "source_retrieval_pass": passed,
        }

    return {
        "schema_version": "market-top-ng3-bea-vintage-concept-audit-1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "research_only": True,
        "production_effect": "none",
        "status": "PASS" if all_pass else "FAIL",
        "evidence": evidence,
        "interpretation_boundary": {
            "proved": (
                "Archived SCB full text is retrievable and the 1974 unit-table "
                "profit label uses IVA wording, while the 1976 and 1988 "
                "publications explicitly use IVA+capital-consumption-adjustment wording."
            ),
            "not_proved": (
                "This text audit does not itself prove exact quarter-by-quarter "
                "numeric mapping, nor does it claim that modern revised levels are "
                "identical to historical published levels."
            ),
        },
        "model_effect": "FORMULA_REMAINS_NOT_FROZEN",
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output")
    args = ap.parse_args()

    x = audit()
    print(json.dumps(x, indent=2))
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(x, f, indent=2)
            f.write("\n")
    if x["status"] != "PASS":
        raise SystemExit("NG3 historical concept source audit failed")


if __name__ == "__main__":
    main()
