from __future__ import annotations

import json
from pathlib import Path

import research_factor_map_v1 as fm
import research_indicator_validation_marketprice_v1 as mp
from research_indicator_validation_v1_sourceaware import FRED_DEPENDENT

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "docs" / "data" / "factor_map_source_invariant_v1.json"
SUMMARY = ROOT / "docs" / "data" / "factor_map_source_invariant_v1_summary.json"
BASE_SUMMARY = ROOT / "docs" / "data" / "factor_map_v1_summary.json"
SPEC = "research/factor_map_source_invariant_v1/STUDY_SPEC.md"


def source_invariant_capture():
    ns, cap = mp.run_market_price_capture()
    if not cap:
        raise RuntimeError("No market-price capture generated")
    out = dict(cap)
    out["series_store"] = {
        k: v for k, v in (cap.get("series_store") or {}).items()
        if k not in FRED_DEPENDENT
    }
    return ns, out


def fam_map(payload):
    return {x["family"]: x for x in (payload.get("families") or payload.get("summary_rows") or [])}


def build_comparison(source_payload: dict, base_summary: dict):
    src = {x["family"]: x for x in source_payload.get("summary_rows", [])}
    base = {x["family"]: x for x in base_summary.get("families", [])}
    names = sorted(set(src) | set(base))
    rows = []
    for fam in names:
        a = base.get(fam)
        b = src.get(fam)
        if b is None:
            rows.append({
                "family": fam,
                "status": "not_source_invariant_evaluable",
                "base": a,
                "source_invariant": None,
            })
            continue
        def g(x, key):
            return None if x is None else x.get(key)
        b10 = g(b, "ic10")
        a10 = g(a, "ic10")
        bp = g(b, "partial_ic10")
        ap = g(a, "partial_ic10")
        def sign_agree(x, y):
            if x is None or y is None or x == 0 or y == 0:
                return None
            return (x > 0) == (y > 0)
        rows.append({
            "family": fam,
            "status": "evaluable",
            "base": a,
            "source_invariant": b,
            "ic10_sign_agrees": sign_agree(a10, b10),
            "partial_ic10_sign_agrees": sign_agree(ap, bp),
            "ic10_delta_source_minus_base": None if a10 is None or b10 is None else round(float(b10) - float(a10), 4),
            "partial_ic10_delta_source_minus_base": None if ap is None or bp is None else round(float(bp) - float(ap), 4),
        })
    return rows


def main():
    # Reuse the frozen Factor Map implementation with only the source capture changed.
    fm.OUT = OUT
    fm.SUMMARY = SUMMARY
    fm.SPEC = SPEC
    fm.abl.run_update_and_capture = source_invariant_capture
    fm.main()

    d = json.loads(OUT.read_text(encoding="utf-8"))
    s = json.loads(SUMMARY.read_text(encoding="utf-8"))
    base = json.loads(BASE_SUMMARY.read_text(encoding="utf-8"))

    comparison = build_comparison(d, base)
    source_ids = sorted(d.get("assignment", {}).keys())
    d["schema"] = "MARKET-FACTOR-MAP-SOURCE-INVARIANT-V1"
    d["study_spec"] = SPEC
    d["source_invariant"] = {
        "official_macro_sources_forced_off": True,
        "excluded_fred_or_official_source_dependent_ids": sorted(FRED_DEPENDENT),
        "remaining_directional_indicator_ids": source_ids,
        "remaining_directional_count": len(source_ids),
        "comparison_to_factor_map_v1": comparison,
        "rule": "Only formula-invariant market-price/derived indicators are allowed into family composites.",
    }
    d["guardrails"]["may_change_production"] = False
    d["guardrails"]["may_reweight_model"] = False
    d["guardrails"]["may_remove_indicator"] = False
    OUT.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")

    s["schema"] = "MARKET-FACTOR-MAP-SOURCE-INVARIANT-V1-SUMMARY"
    s["study_spec"] = SPEC
    s["excluded_source_dependent_count"] = len(FRED_DEPENDENT)
    s["remaining_directional_count"] = len(source_ids)
    s["comparison_to_factor_map_v1"] = comparison
    s["guardrails"] = d["guardrails"]
    SUMMARY.write_text(json.dumps(s, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps({
        "remaining_directional_count": len(source_ids),
        "family_count": d["coverage"]["family_count"],
        "families": [[
            x["family"], x.get("ic10"), x.get("ic10_2022_present"),
            x.get("partial_ic10"), x.get("loyo_ablation_delta_pct")
        ] for x in d.get("summary_rows", [])],
        "comparison": [[
            x["family"], x["status"], x.get("ic10_sign_agrees"),
            x.get("partial_ic10_sign_agrees")
        ] for x in comparison],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
