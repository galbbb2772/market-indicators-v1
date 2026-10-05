from __future__ import annotations

import json
from pathlib import Path

import research_indicator_validation_v1 as study
from research_indicator_validation_v1_sourceaware import FRED_DEPENDENT

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "update_data.py"
OUT = ROOT / "docs" / "data" / "indicator_validation_marketprice_v1.json"
_CAPTURE = None


def run_market_price_capture():
    global _CAPTURE
    source = SRC.read_text(encoding="utf-8")

    # This validation intentionally turns official macro retrieval off. We are
    # validating only the formula-invariant market-price stratum, so network
    # availability must not change the formulas under test.
    source = source.replace('    fs = get_fred(FRED_IDS, errors)\n', '    fs = {}\n', 1)
    source = source.replace('        tdef = treasury_deficit(errors)\n', '        tdef = None\n', 1)
    source = source.replace('        unrate = bls_unemployment(errors)\n', '        unrate = None\n', 1)

    needle = '    OUT.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding="utf-8")\n'
    injected = (
        '    global _ABLATION_CAPTURE\n'
        '    _ABLATION_CAPTURE={"series_store":series_store,"mk":mk,"ordered":ordered}\n'
        + needle
    )
    if needle not in source:
        raise RuntimeError("Could not instrument update_data.py")
    source = source.replace(needle, injected, 1)
    ns = {"__name__": "__main__", "__file__": str(SRC)}
    exec(compile(source, str(SRC), "exec"), ns, ns)
    _CAPTURE = ns.get("_ABLATION_CAPTURE")
    return ns, _CAPTURE


def main():
    study.OUT = OUT
    study.abl.run_update_and_capture = run_market_price_capture
    study.main()

    d = json.loads(OUT.read_text(encoding="utf-8"))
    all_rows = d.get("indicators") or []
    invariant = [x for x in all_rows if x.get("id") not in FRED_DEPENDENT]
    dep = [x for x in all_rows if x.get("id") in FRED_DEPENDENT]
    invariant_ids = {x["id"] for x in invariant}

    # Recompute redundancy strictly inside the invariant universe.
    cap = _CAPTURE or {}
    series_store = cap.get("series_store") or {}
    mk = cap.get("mk") or {}
    frame_index = mk["SPY"]["Close"].dropna().sort_index().index
    subset_series = {k: v for k, v in series_store.items() if k in invariant_ids}
    red = study.redundancy(subset_series, frame_index)
    for row in invariant:
        row["redundancy_5d_change_marketprice_only"] = red["max_peer"].get(row["id"])

    def compact_h(h):
        key = f"{h}d"
        return {
            "same_sign_ge70_n": sum((x["horizons"][key]["raw_overlap_phase"].get("same_sign_as_full_pct") or 0) >= 70 for x in invariant),
            "abs_phase_median_ge010_n": sum(abs(x["horizons"][key]["raw_overlap_phase"].get("median_rho") or 0) >= 0.10 for x in invariant),
            "abs_phase_median_ge015_n": sum(abs(x["horizons"][key]["raw_overlap_phase"].get("median_rho") or 0) >= 0.15 for x in invariant),
        }

    ranked = sorted(
        invariant,
        key=lambda x: abs(x["horizons"]["10d"]["raw_overlap_phase"].get("median_rho") or 0),
        reverse=True,
    )
    d["market_price_validation"] = {
        "official_macro_sources_forced_off": True,
        "purpose": "Source-invariant validation. FRED/BLS/Treasury-dependent and downstream formulas are excluded from the valid evidence stratum.",
        "eligible_invariant_count": len(invariant),
        "excluded_source_dependent_count": len(dep),
        "role_counts": {
            "active": sum(x.get("model_v2_role") == "active" for x in invariant),
            "context": sum(x.get("model_v2_role") == "context" for x in invariant),
            "archived": sum(x.get("model_v2_role") == "archived" for x in invariant),
        },
        "phase_robustness": {f"{h}d": compact_h(h) for h in (5, 10, 20)},
        "redundancy_pairs_abs_rho_ge085": len(red["pairs"]),
        "top15_abs_10d_phase_median_descriptive_only": [
            {
                "id": x["id"],
                "name": x["name"],
                "role": x.get("model_v2_role"),
                "phase_median_rho": x["horizons"]["10d"]["raw_overlap_phase"].get("median_rho"),
                "full_rho": x["horizons"]["10d"]["raw_ic"].get("rho"),
                "same_sign_pct": x["horizons"]["10d"]["raw_overlap_phase"].get("same_sign_as_full_pct"),
                "max_peer": red["max_peer"].get(x["id"]),
            }
            for x in ranked[:15]
        ],
        "valid_indicator_ids": sorted(invariant_ids),
        "source_dependent_excluded_ids": sorted(x["id"] for x in dep),
        "redundancy": red,
    }
    d["warnings"].append(
        "Only market_price_validation is source-stable evidence in this file. Rows in the broader indicators array that are FRED/official-source-dependent were computed under forced fallback and are retained only for diagnostics."
    )
    OUT.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(d["market_price_validation"], ensure_ascii=False))


if __name__ == "__main__":
    main()
