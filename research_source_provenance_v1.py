from __future__ import annotations

import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

import update_data as ud
from research_indicator_validation_v1_sourceaware import FRED_DEPENDENT

ROOT = Path(__file__).resolve().parent
PROV = ROOT / "docs" / "data" / "source_provenance_v1.json"
HISTORY = ROOT / "docs" / "data" / "source_provenance_history_v1.json"
CANON = ROOT / "docs" / "data" / "fred_canonical_v1.json"
REVISIONS = ROOT / "docs" / "data" / "fred_revision_ledger_v1.json"
SPEC = "research/source_provenance_v1/STUDY_SPEC.md"
TOL = 1e-12


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def load_json(path: Path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def norm_series(s: pd.Series):
    x = pd.Series(s).dropna().astype(float).sort_index()
    out = []
    for dt, v in x.items():
        if not math.isfinite(float(v)):
            continue
        out.append([str(pd.Timestamp(dt).date()), float(v)])
    return out


def series_hash(rows):
    raw = "\n".join(f"{d}={format(v, '.15g')}" for d, v in rows).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def fetch_fred_with_single_recovery(ids):
    initial_errors = {}
    fs = ud.get_fred(list(ids), initial_errors)
    recovered = []
    recovery_errors = {}
    missing = [sid for sid in ids if sid not in fs]
    for sid in missing:
        try:
            one = ud.fred_chunk([sid])
            if sid in one and not one[sid].empty:
                fs[sid] = one[sid]
                recovered.append(sid)
            else:
                recovery_errors[f"fred:{sid}"] = "single-series retry returned no usable observations"
        except Exception as exc:
            recovery_errors[f"fred:{sid}"] = repr(exc)
    unresolved = [sid for sid in ids if sid not in fs]
    return fs, initial_errors, recovery_errors, recovered, unresolved


def formula_modes(avail: set[str]):
    def anyof(*ids): return any(x in avail for x in ids)
    def allof(*ids): return all(x in avail for x in ids)
    modes = {}
    modes["global_cb_rhythm"] = "fred_direct" if anyof("DFF", "ECBDFR") else "market_fallback_tnx"
    modes["market_fear"] = "fred_credit_plus_market" if "BAMLH0A0HYM2" in avail else "market_fallback_hyg_lqd_plus_vix"
    modes["liquidity_risk"] = "fred_plus_market" if anyof("NFCI", "BAMLH0A0HYM2") else "market_fallback_hyg_lqd"
    modes["treasury_rate_regime"] = "fred_direct_dgs10_dgs2" if allof("DGS10", "DGS2") else "market_fallback_tnx"
    fx = "fred_dtwexbgs" if "DTWEXBGS" in avail else "market_dxy"
    cr = "fred_baa10y" if "BAA10Y" in avail else "market_hyg_lqd"
    modes["usd_credit"] = f"mixed:{fx}+{cr}"
    modes["high_yield"] = "fred_direct_baml_oas" if "BAMLH0A0HYM2" in avail else "market_fallback_hyg_lqd"
    modes["inventory_cycle"] = "fred_direct_or_partial" if anyof("ISRATIO", "BUSINV") else "market_fallback_xli_copper"
    modes["fiscal_deficit"] = "fred_direct_mts" if "MTSDS133FMS" in avail else "official_fallback_treasury_api"
    modes["employment"] = "fred_direct_or_partial" if anyof("UNRATE", "ICSA") else "official_fallback_bls_api"
    modes["leverage_liquidity"] = modes["liquidity_risk"]
    sys_parts = []
    if "BAMLH0A0HYM2" in avail: sys_parts.append("fred_baml")
    else: sys_parts.append("market_hyg_lqd")
    if "NFCI" in avail: sys_parts.append("fred_nfci")
    sys_parts.extend(["market_vix", "market_drawdown"])
    modes["systemic_risk"] = "mixed:" + "+".join(sys_parts)
    modes["risk_60d"] = "downstream_of_systemic_risk"
    modes["credit_cycle"] = "fred_direct_loaninv" if "LOANINV" in avail else "market_fallback_hyg_lqd"
    modes["yield_curve"] = "fred_direct_or_partial" if anyof("T10Y2Y", "T10Y3M") else "market_fallback_tnx_irx"
    modes["institutional_panic"] = "downstream_mixed:high_yield+liquidity_risk+market_fear"
    modes["business_cycle"] = "downstream_mixed:inventory_cycle+market_industrials+copper"
    modes["geopolitical_risk"] = "downstream_mixed:geo_market_reaction+market_fear+gold+oil"
    loan_mode = "fred_direct_loaninv" if "LOANINV" in avail else "downstream_credit_cycle_fallback"
    modes["us_loans_total"] = loan_mode
    modes["us_loans_speed"] = loan_mode
    modes["market_optimism"] = "downstream_mixed:market_support+money_making_effect+market_fear"
    modes["market_pessimism"] = "downstream_mixed:market_fear+largecap_panic+institutional_panic"
    modes["market_liquidity"] = "inverse_of_liquidity_risk:" + modes["liquidity_risk"]
    modes["mega_liquidity_blowup"] = "downstream_mixed:mag7_volatility+market_fear+liquidity_risk"
    modes["market_bias"] = "downstream_mixed:market_optimism+market_pessimism"
    for k in sorted(FRED_DEPENDENT):
        modes.setdefault(k, "official_source_dependent_unspecified")
    return modes


def main():
    generated = now_iso()
    fs, initial_errors, recovery_errors, recovered_ids, unresolved_ids = fetch_fred_with_single_recovery(ud.FRED_IDS)
    avail = set(fs)

    current_series = {}
    status = {}
    for sid in ud.FRED_IDS:
        rows = norm_series(fs[sid]) if sid in fs else []
        current_series[sid] = rows
        status[sid] = {
            "available": bool(rows),
            "observations": len(rows),
            "start": rows[0][0] if rows else None,
            "end": rows[-1][0] if rows else None,
            "latest_value": rows[-1][1] if rows else None,
            "sha256": series_hash(rows) if rows else None,
            "recovered_by_single_series_retry": sid in recovered_ids,
        }

    old_canon = load_json(CANON, {"series": {}})
    old_series = old_canon.get("series") or {}
    revision_ledger = load_json(REVISIONS, {"schema": "FRED-REVISION-LEDGER-V1", "research_only": True, "revisions": []})
    seen_revision_keys = {
        (x.get("source_id"), x.get("observation_date"), x.get("old_value"), x.get("new_value"))
        for x in revision_ledger.get("revisions", [])
    }
    new_revisions = []
    for sid, rows in current_series.items():
        if not rows:
            continue
        before = {str(d): float(v) for d, v in (old_series.get(sid) or [])}
        after = {str(d): float(v) for d, v in rows}
        for d in sorted(set(before) & set(after)):
            a, b = before[d], after[d]
            if abs(a - b) > TOL:
                key = (sid, d, a, b)
                if key in seen_revision_keys:
                    continue
                rec = {
                    "source_id": sid,
                    "observation_date": d,
                    "old_value": a,
                    "new_value": b,
                    "detected_at": generated,
                }
                new_revisions.append(rec)
                seen_revision_keys.add(key)
    revision_ledger.setdefault("revisions", []).extend(new_revisions)
    revision_ledger["updated_at"] = generated

    canon = {
        "schema": "FRED-CANONICAL-V1",
        "generated_at": generated,
        "research_only": True,
        "archive_start_note": "Point-in-time revision reconstruction is only supported from the first V1 archive onward.",
        "series": current_series,
    }

    modes = formula_modes(avail)
    direct_complete = len(avail) == len(ud.FRED_IDS)
    provenance = {
        "schema": "SOURCE-PROVENANCE-V1",
        "generated_at": generated,
        "research_only": True,
        "diagnostic_only": True,
        "production_effect": "none",
        "study_spec": SPEC,
        "fred": {
            "configured_ids": list(ud.FRED_IDS),
            "available_count": len(avail),
            "configured_count": len(ud.FRED_IDS),
            "direct_complete": direct_complete,
            "initial_chunk_errors": {k: v for k, v in initial_errors.items() if str(k).startswith("fred:")},
            "single_series_recovery_errors": recovery_errors,
            "recovered_by_single_series_retry": sorted(recovered_ids),
            "unresolved_ids": sorted(unresolved_ids),
            "series_status": status,
            "new_revision_count": len(new_revisions),
        },
        "formula_modes": modes,
        "source_dependent_indicator_ids": sorted(FRED_DEPENDENT),
        "guardrails": {
            "may_change_production": False,
            "may_reweight_model": False,
            "may_change_formula": False,
            "note": "Fallback modes are provenance labels only and are never relabelled as official-source evidence.",
        },
    }

    history = load_json(HISTORY, {"schema": "SOURCE-PROVENANCE-HISTORY-V1", "research_only": True, "runs": []})
    run_key = generated[:10]
    run = {
        "run_date": run_key,
        "generated_at": generated,
        "fred_available_count": len(avail),
        "fred_configured_count": len(ud.FRED_IDS),
        "fred_direct_complete": direct_complete,
        "fred_hashes": {sid: status[sid]["sha256"] for sid in ud.FRED_IDS},
        "fred_latest_dates": {sid: status[sid]["end"] for sid in ud.FRED_IDS},
        "formula_modes": modes,
        "new_revision_count": len(new_revisions),
        "recovered_by_single_series_retry": sorted(recovered_ids),
        "unresolved_ids": sorted(unresolved_ids),
        "initial_chunk_errors": provenance["fred"]["initial_chunk_errors"],
        "single_series_recovery_errors": recovery_errors,
    }
    runs = history.setdefault("runs", [])
    runs[:] = [x for x in runs if x.get("run_date") != run_key]
    runs.append(run)
    runs.sort(key=lambda x: x.get("generated_at") or "")
    history["updated_at"] = generated

    PROV.parent.mkdir(parents=True, exist_ok=True)
    PROV.write_text(json.dumps(provenance, ensure_ascii=False, indent=2), encoding="utf-8")
    HISTORY.write_text(json.dumps(history, ensure_ascii=False, indent=2), encoding="utf-8")
    CANON.write_text(json.dumps(canon, ensure_ascii=False, indent=2), encoding="utf-8")
    REVISIONS.write_text(json.dumps(revision_ledger, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps({
        "fred_available": len(avail),
        "fred_configured": len(ud.FRED_IDS),
        "direct_complete": direct_complete,
        "recovered_by_single_series_retry": sorted(recovered_ids),
        "unresolved_ids": sorted(unresolved_ids),
        "new_revisions": len(new_revisions),
        "formula_modes_sample": {k: modes[k] for k in ["liquidity_risk", "high_yield", "treasury_rate_regime", "yield_curve"]},
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
