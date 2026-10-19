from __future__ import annotations

import json
from pathlib import Path
from statistics import mean

SRC = Path(__file__).with_name("market_top_ng3_margin_revision_diagnostic_input.json")
OUT = Path(__file__).with_name("market_top_ng3_margin_revision_diagnostic_result.json")


def to_map(rows):
    return {q: {"den": float(den), "num": float(num)} for q, den, num in rows}


def share(x):
    return x["num"] / x["den"]


def compare(vintage_rows, revised_rows):
    v = to_map(vintage_rows)
    r = to_map(revised_rows)
    out = []
    for q in v:
        vp = share(v[q])
        rp = share(r[q])
        out.append(
            {
                "quarter": q,
                "vintage_profit_share_pct": round(vp * 100, 6),
                "current_revised_profit_share_pct": round(rp * 100, 6),
                "vintage_minus_current_pp": round((vp - rp) * 100, 6),
            }
        )
    return {
        "rows": out,
        "mean_abs_difference_pp": round(mean(abs(x["vintage_minus_current_pp"]) for x in out), 6),
        "max_abs_difference_pp": round(max(abs(x["vintage_minus_current_pp"]) for x in out), 6),
    }


def main():
    x = json.loads(SRC.read_text(encoding="utf-8"))
    revised = x["current_revised_snapshot"]["rows"]
    revised_map = {q: [q, den, num] for q, den, num in revised}

    def revised_subset(vrows):
        return [revised_map[q] for q, _, _ in vrows]

    result = {
        "schema_version": "market-top-ng3-margin-revision-diagnostic-result-1",
        "research_only": True,
        "production_effect": "none",
        "formula": x["formula"],
        "vintage_1976_04_vs_current": compare(
            x["vintage_1976_04"]["rows"],
            revised_subset(x["vintage_1976_04"]["rows"]),
        ),
        "vintage_1988_06_vs_current": compare(
            x["vintage_1988_06"]["rows"],
            revised_subset(x["vintage_1988_06"]["rows"]),
        ),
        "decision": {
            "modern_revised_history_as_pit_substitute": "PROHIBITED",
            "pre_1976_marginconfirm": "MARGIN_NOT_COMPARABLE",
            "numerical_ng3_formula": "NOT_FROZEN",
            "historical_hit_rate": "NOT_TESTED",
        },
    }
    OUT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
