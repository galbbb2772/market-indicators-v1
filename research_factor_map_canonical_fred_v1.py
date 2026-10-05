from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

import research_factor_map_v1 as fm

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "update_data.py"
PROV = ROOT / "docs" / "data" / "source_provenance_v1.json"
CANON = ROOT / "docs" / "data" / "fred_canonical_v1.json"
OUT = ROOT / "docs" / "data" / "factor_map_canonical_fred_v1.json"
SUMMARY = ROOT / "docs" / "data" / "factor_map_canonical_fred_v1_summary.json"
SOURCE_INVARIANT = ROOT / "docs" / "data" / "factor_map_source_invariant_v1_summary.json"
SPEC = "research/factor_map_canonical_fred_v1/STUDY_SPEC.md"


def load_gate():
    p = json.loads(PROV.read_text(encoding="utf-8"))
    c = json.loads(CANON.read_text(encoding="utf-8"))
    ids = list(p.get("fred", {}).get("configured_ids") or [])
    series = c.get("series") or {}
    missing = [sid for sid in ids if not (series.get(sid) or [])]
    ok = bool(ids) and p.get("fred", {}).get("direct_complete") is True and not missing
    return p, c, ids, missing, ok


def canonical_capture():
    p, c, ids, missing, ok = load_gate()
    if not ok:
        raise RuntimeError(f"Canonical FRED gate not satisfied; missing={missing}, direct_complete={p.get('fred',{}).get('direct_complete')}")

    source = SRC.read_text(encoding="utf-8")
    source_line = '    fs = get_fred(FRED_IDS, errors)\n'
    replacement = (
        '    fs = {}\n'
        '    for _sid in FRED_IDS:\n'
        '        _rows = (_CANONICAL_FRED_ROWS.get(_sid) or [])\n'
        '        if _rows:\n'
        '            fs[_sid] = pd.Series({pd.Timestamp(_d): float(_v) for _d, _v in _rows}, dtype=float).sort_index().rename(_sid)\n'
    )
    if source_line not in source:
        raise RuntimeError("Could not replace live FRED retrieval in update_data.py")
    source = source.replace(source_line, replacement, 1)

    needle = '    OUT.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding="utf-8")\n'
    injected = (
        '    global _ABLATION_CAPTURE\n'
        '    _ABLATION_CAPTURE={"series_store":series_store,"mk":mk,"ordered":ordered}\n'
        + needle
    )
    if needle not in source:
        raise RuntimeError("Could not instrument update_data.py")
    source = source.replace(needle, injected, 1)

    ns = {
        "__name__": "__main__",
        "__file__": str(SRC),
        "_CANONICAL_FRED_ROWS": c.get("series") or {},
    }
    exec(compile(source, str(SRC), "exec"), ns, ns)
    return ns, ns.get("_ABLATION_CAPTURE")


def fam_map(summary: dict):
    return {x["family"]: x for x in summary.get("families", [])}


def comparison(canonical_summary: dict, source_summary: dict):
    a = fam_map(canonical_summary)
    b = fam_map(source_summary)
    rows = []
    for fam in sorted(set(a) | set(b)):
        ca = a.get(fam)
        si = b.get(fam)
        rows.append({
            "family": fam,
            "canonical": ca,
            "source_invariant": si,
            "ic10_delta_canonical_minus_invariant": None if not ca or not si or ca.get("ic10") is None or si.get("ic10") is None else round(float(ca["ic10"]) - float(si["ic10"]), 4),
            "partial_ic10_delta_canonical_minus_invariant": None if not ca or not si or ca.get("partial_ic10") is None or si.get("partial_ic10") is None else round(float(ca["partial_ic10"]) - float(si["partial_ic10"]), 4),
        })
    return rows


def main():
    p, c, ids, missing, ok = load_gate()
    if not ok:
        raise RuntimeError(f"Canonical FRED gate not satisfied; missing={missing}")

    fm.OUT = OUT
    fm.SUMMARY = SUMMARY
    fm.SPEC = SPEC
    fm.abl.run_update_and_capture = canonical_capture
    fm.main()

    d = json.loads(OUT.read_text(encoding="utf-8"))
    s = json.loads(SUMMARY.read_text(encoding="utf-8"))
    source_summary = json.loads(SOURCE_INVARIANT.read_text(encoding="utf-8"))

    status = p.get("fred", {}).get("series_status") or {}
    snapshot = {
        "canonical_generated_at": c.get("generated_at"),
        "provenance_generated_at": p.get("generated_at"),
        "configured_ids": ids,
        "series_hashes": {sid: (status.get(sid) or {}).get("sha256") for sid in ids},
        "series_transport": c.get("series_transport") or p.get("fred", {}).get("series_transport") or {},
        "direct_complete": True,
        "live_fred_network_used_by_factor_map": False,
    }
    comp = comparison(s, source_summary)

    d["schema"] = "MARKET-FACTOR-MAP-CANONICAL-FRED-V1"
    d["study_spec"] = SPEC
    d["canonical_fred_snapshot"] = snapshot
    d["comparison_to_source_invariant"] = comp
    d["guardrails"]["may_change_production"] = False
    d["guardrails"]["may_reweight_model"] = False
    d["guardrails"]["historical_results_count_as_forward_oos"] = False
    OUT.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")

    s["schema"] = "MARKET-FACTOR-MAP-CANONICAL-FRED-V1-SUMMARY"
    s["study_spec"] = SPEC
    s["canonical_fred_snapshot"] = snapshot
    s["comparison_to_source_invariant"] = comp
    s["guardrails"] = d["guardrails"]
    SUMMARY.write_text(json.dumps(s, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps({
        "canonical_generated_at": c.get("generated_at"),
        "families": [[x["family"], x.get("ic10"), x.get("partial_ic10"), x.get("loyo_ablation_delta_pct")] for x in s.get("families", [])],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
