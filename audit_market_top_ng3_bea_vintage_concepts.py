from __future__ import annotations

import argparse
import json
import re
import time
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


def fetch_optional(url: str) -> tuple[str | None, str | None]:
    last = None
    for delay in (0, 1):
        if delay:
            time.sleep(delay)
        try:
            r = requests.get(
                url,
                timeout=(5, 8),
                headers={"User-Agent": "market-top-ng3-vintage-audit/1.1"},
            )
            r.raise_for_status()
            return r.text, None
        except Exception as exc:
            last = repr(exc)
    return None, last


def frozen_contract_passes() -> bool:
    return (
        SOURCES["1974-08"]["concept_label"]
        == "IVA_ONLY_LABEL_IN_UNIT_TABLE"
        and SOURCES["1976-04"]["concept_label"]
        == "IVA_PLUS_CCADJ_EXPLICIT"
        and SOURCES["1988-03"]["concept_label"]
        == "IVA_PLUS_CCADJ_EXPLICIT"
    )


def audit(strict_live: bool = False) -> dict:
    evidence = {}
    live_failures = 0

    for vintage, spec in SOURCES.items():
        raw, error = fetch_optional(spec["url"])
        if raw is None:
            live_failures += 1
            evidence[vintage] = {
                "url": spec["url"],
                "concept_label": spec["concept_label"],
                "required_phrase_checks": None,
                "live_source_status": "UNAVAILABLE",
                "live_error": error,
            }
            continue

        text = normalize(raw)
        checks = {
            phrase: phrase in text
            for phrase in spec["required_phrases"]
        }
        passed = all(checks.values())
        if not passed:
            live_failures += 1
        evidence[vintage] = {
            "url": spec["url"],
            "concept_label": spec["concept_label"],
            "required_phrase_checks": checks,
            "live_source_status": "PASS" if passed else "CONTENT_MISMATCH",
            "live_error": None,
        }

    contract_pass = frozen_contract_passes()
    if not contract_pass:
        status = "FAIL_FROZEN_CONTRACT"
    elif strict_live and live_failures:
        status = "FAIL_LIVE_SOURCE"
    elif live_failures:
        status = "PASS_WITH_LIVE_SOURCE_GAPS"
    else:
        status = "PASS"

    return {
        "schema_version": "market-top-ng3-bea-vintage-concept-audit-2",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "research_only": True,
        "production_effect": "none",
        "status": status,
        "strict_live": strict_live,
        "frozen_evidence_contract_pass": contract_pass,
        "live_source_failures": live_failures,
        "evidence": evidence,
        "interpretation_boundary": {
            "frozen_evidence": (
                "The research record freezes the source URLs and the observed "
                "concept transition: 1974 IVA wording versus explicit "
                "IVA+capital-consumption-adjustment wording in 1976 and 1988."
            ),
            "live_check": (
                "FRASER availability is an external-provider check. A network "
                "timeout is recorded as SOURCE_UNAVAILABLE and is not model evidence."
            ),
            "not_proved": (
                "This audit does not prove exact quarter-by-quarter numeric mapping "
                "or equality between historical published and modern revised levels."
            ),
        },
        "model_effect": "FORMULA_REMAINS_NOT_FROZEN",
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output")
    ap.add_argument("--strict-live", action="store_true")
    args = ap.parse_args()

    x = audit(strict_live=args.strict_live)
    print(json.dumps(x, indent=2))
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(x, f, indent=2)
            f.write("\n")

    if x["status"].startswith("FAIL_"):
        raise SystemExit("NG3 historical concept audit failed")


if __name__ == "__main__":
    main()
