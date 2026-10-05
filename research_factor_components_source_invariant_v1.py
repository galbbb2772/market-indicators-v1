from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

import research_factor_map_v1 as fm
import research_factor_map_source_invariant_v1 as sfm

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "docs" / "data" / "factor_components_source_invariant_v1.json"
SUMMARY = ROOT / "docs" / "data" / "factor_components_source_invariant_v1_summary.json"
FACTOR_SUMMARY = ROOT / "docs" / "data" / "factor_map_source_invariant_v1_summary.json"
SPEC = "research/factor_components_source_invariant_v1/STUDY_SPEC.md"


def partial_spearman(feature: pd.Series, target: pd.Series, controls: pd.DataFrame, start=None):
    z = pd.concat([feature.rename("feature"), controls, target.rename("target")], axis=1)
    if start is not None:
        z = z[z.index >= pd.Timestamp(start)]
    z = z.dropna()
    if len(z) < 120 or z["feature"].nunique() < 2 or z["target"].nunique() < 2:
        return {"n": len(z), "rho": None}
    ranks = z.rank(method="average")
    cols = [c for c in controls.columns if c in ranks]
    xf = ranks["feature"].to_numpy(float)
    yt = ranks["target"].to_numpy(float)
    if cols:
        X = ranks[cols].to_numpy(float)
        X = np.column_stack([np.ones(len(X)), X])
        bx = np.linalg.lstsq(X, xf, rcond=None)[0]
        by = np.linalg.lstsq(X, yt, rcond=None)[0]
        rx = xf - X @ bx
        ry = yt - X @ by
    else:
        rx = xf
        ry = yt
    if np.std(rx) <= 1e-12 or np.std(ry) <= 1e-12:
        return {"n": len(z), "rho": None}
    r = float(np.corrcoef(rx, ry)[0, 1])
    return {"n": len(z), "rho": None if not np.isfinite(r) else round(r, 4)}


def main():
    _, cap = sfm.source_invariant_capture()
    if not cap:
        raise RuntimeError("No source-invariant capture generated")
    series_store = cap.get("series_store") or {}
    mk = cap.get("mk") or {}
    ordered = cap.get("ordered") or []
    if "SPY" not in mk:
        raise RuntimeError("SPY missing")

    close = mk["SPY"]["Close"].dropna().sort_index()
    frame = fm.forward_frame(close)
    meta = {x["id"]: x for x in ordered}

    eligible = {}
    assignment = {}
    excluded = {}
    for k, s in series_store.items():
        m = meta.get(k)
        if not m:
            excluded[k] = "missing_metadata"
            continue
        pol = int(m.get("impact_polarity", 0) or 0)
        if pol not in (-1, 1):
            excluded[k] = "non_directional_polarity"
            continue
        ss = pd.Series(s).dropna().sort_index().astype(float)
        aligned = ss.reindex(frame.index).ffill().dropna()
        if len(aligned) < fm.MIN_OBS:
            excluded[k] = f"aligned<{fm.MIN_OBS}"
            continue
        if ss.nunique() < fm.MIN_UNIQUE:
            excluded[k] = f"distinct<{fm.MIN_UNIQUE}"
            continue
        supportive = ss if pol == 1 else 100.0 - ss
        eligible[k] = supportive
        fam, method = fm.assign_family(k, m)
        assignment[k] = {
            "family": fam,
            "method": method,
            "polarity": pol,
            "name": m.get("name"),
            "role": m.get("model_v2_role"),
        }

    by_family = {}
    for k, info in assignment.items():
        by_family.setdefault(info["family"], []).append(k)

    family_scores = {}
    component_scores = {}
    components_by_family = {}
    redundancy_by_family = {}

    for fam in sorted(by_family):
        ids = sorted(by_family[fam])
        comps, pairs = fm.connected_components(ids, eligible, frame.index)
        redundancy_by_family[fam] = pairs
        fam_components = []
        comp_series = []
        for i, members in enumerate(comps, 1):
            key = f"{fam}::c{i}"
            xs = [eligible[k].reindex(frame.index).ffill().rename(k) for k in members]
            score = pd.concat(xs, axis=1).mean(axis=1, skipna=True).dropna()
            component_scores[key] = score
            comp_series.append(score.rename(key))
            fam_components.append({"key": key, "component": i, "members": members, "size": len(members)})
        components_by_family[fam] = fam_components
        family_scores[fam] = pd.concat(comp_series, axis=1).mean(axis=1, skipna=True).dropna()

    factor_df = pd.DataFrame({k: v.reindex(frame.index).ffill() for k, v in family_scores.items()}, index=frame.index)
    component_df = pd.DataFrame({k: v.reindex(frame.index).ffill() for k, v in component_scores.items()}, index=frame.index)
    component_ablation = fm.multivariate_loyo_ablation(component_df, frame["fwd_10d"])

    component_rows = []
    for fam in sorted(components_by_family):
        own_keys = [x["key"] for x in components_by_family[fam]]
        other_family_cols = [c for c in factor_df.columns if c != fam]
        for comp in components_by_family[fam]:
            key = comp["key"]
            score = component_scores[key]
            met = fm.family_metrics(score, frame)
            univ = fm.univariate_loyo(score, frame["fwd_10d"])
            same_family_other = [c for c in own_keys if c != key]
            controls = pd.concat(
                [component_df[same_family_other], factor_df[other_family_cols]],
                axis=1,
            ) if (same_family_other or other_family_cols) else pd.DataFrame(index=frame.index)
            # Avoid duplicate control column names defensively.
            controls = controls.loc[:, ~controls.columns.duplicated()].copy()
            partial_full = partial_spearman(score, frame["fwd_10d"], controls)
            partial_recent = partial_spearman(score, frame["fwd_10d"], controls, "2022-01-01")
            abl = component_ablation.get("families", {}).get(key, {})
            row = {
                "key": key,
                "family": fam,
                "component": comp["component"],
                "members": comp["members"],
                "member_count": comp["size"],
                "ic5": met["horizons"]["5d"]["ic"]["rho"],
                "ic10": met["horizons"]["10d"]["ic"]["rho"],
                "ic20": met["horizons"]["20d"]["ic"]["rho"],
                "ic10_2017_2019": met["era_ic_10d"]["2017_2019"]["rho"],
                "ic10_2020_2021": met["era_ic_10d"]["2020_2021"]["rho"],
                "ic10_2022_present": met["era_ic_10d"]["2022_present"]["rho"],
                "above200_ic10": met["regime_ic_10d"]["above200"]["rho"],
                "below200_ic10": met["regime_ic_10d"]["below200"]["rho"],
                "high_vol_ic10": met["regime_ic_10d"]["high_vol"]["rho"],
                "low_vol_ic10": met["regime_ic_10d"]["low_vol"]["rho"],
                "q5_minus_q1_10d_pp": met["horizons"]["10d"]["quintile"].get("q5_minus_q1_pp"),
                "rolling_median_ic10": met["rolling_ic_10d"].get("median_rho"),
                "rolling_positive_pct10": met["rolling_ic_10d"].get("positive_pct"),
                "phase_same_sign_pct10": met["overlap_phase_10d"].get("same_sign_pct"),
                "univariate_loyo_improvement_pct": univ.get("mse_improvement_pct"),
                "partial_ic10": partial_full.get("rho"),
                "partial_ic10_2022_present": partial_recent.get("rho"),
                "component_ablation_delta_pct": abl.get("delta_pct_of_full_mse"),
                "component_helps_full_model_if_positive": abl.get("helps_full_model_if_positive"),
            }
            component_rows.append(row)

    base_factor_summary = json.loads(FACTOR_SUMMARY.read_text(encoding="utf-8"))
    family_base = {x["family"]: x for x in base_factor_summary.get("families", [])}
    family_audit = []
    for fam in sorted(components_by_family):
        rows = [x for x in component_rows if x["family"] == fam]
        base = family_base.get(fam, {})
        family_ic = base.get("ic10")
        valid = [x for x in rows if x.get("ic10") is not None]
        strongest = max(valid, key=lambda x: abs(x["ic10"])) if valid else None
        valid_partial = [x for x in rows if x.get("partial_ic10") is not None]
        strongest_partial = max(valid_partial, key=lambda x: abs(x["partial_ic10"])) if valid_partial else None
        pos = sum((x.get("ic10") or 0) > 0 for x in valid)
        neg = sum((x.get("ic10") or 0) < 0 for x in valid)
        same = None
        if family_ic not in (None, 0) and valid:
            same = round(100 * sum((x["ic10"] > 0) == (family_ic > 0) for x in valid) / len(valid), 2)
        gap = None
        if strongest is not None and family_ic is not None:
            gap = round(abs(strongest["ic10"]) - abs(family_ic), 4)
        family_audit.append({
            "family": fam,
            "family_ic10": family_ic,
            "family_partial_ic10": base.get("partial_ic10"),
            "component_count": len(rows),
            "positive_component_count": pos,
            "negative_component_count": neg,
            "component_sign_agreement_with_family_pct": same,
            "strongest_abs_component": None if strongest is None else {
                "key": strongest["key"], "members": strongest["members"],
                "ic10": strongest["ic10"], "ic10_2022_present": strongest["ic10_2022_present"],
                "partial_ic10": strongest["partial_ic10"],
                "ablation_delta_pct": strongest["component_ablation_delta_pct"],
            },
            "strongest_abs_partial_component": None if strongest_partial is None else {
                "key": strongest_partial["key"], "members": strongest_partial["members"],
                "ic10": strongest_partial["ic10"], "partial_ic10": strongest_partial["partial_ic10"],
                "partial_ic10_2022_present": strongest_partial["partial_ic10_2022_present"],
            },
            "max_component_abs_ic_minus_family_abs_ic": gap,
            "cancellation_flag": bool(gap is not None and gap >= 0.05),
        })

    component_rows.sort(key=lambda x: abs(x.get("partial_ic10") or 0), reverse=True)
    family_audit.sort(key=lambda x: x["max_component_abs_ic_minus_family_abs_ic"] if x["max_component_abs_ic_minus_family_abs_ic"] is not None else -999, reverse=True)

    payload = {
        "schema": "SOURCE-INVARIANT-FACTOR-COMPONENT-AUDIT-V1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "research_only": True,
        "diagnostic_only": True,
        "production_effect": "none",
        "weights_changed": False,
        "thresholds_changed": False,
        "study_spec": SPEC,
        "coverage": {
            "spy_start": str(frame.index.min().date()),
            "spy_end": str(frame.index.max().date()),
            "spy_observations": len(frame),
            "eligible_directional_indicator_count": len(eligible),
            "family_count": len(components_by_family),
            "component_count": len(component_rows),
            "excluded_count": len(excluded),
        },
        "assignment": assignment,
        "excluded": excluded,
        "families": components_by_family,
        "within_family_redundancy_pairs": redundancy_by_family,
        "component_rows": component_rows,
        "family_cancellation_audit": family_audit,
        "multivariate_component_loyo": component_ablation,
        "guardrails": {
            "may_change_production": False,
            "may_reweight_model": False,
            "may_remove_indicator": False,
            "may_promote_component": False,
            "note": "Component winners are descriptive historical evidence only; a separate preregistered OOS challenger is required before any production change.",
        },
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    compact = {
        "schema": "SOURCE-INVARIANT-FACTOR-COMPONENT-AUDIT-V1-SUMMARY",
        "generated_at": payload["generated_at"],
        "research_only": True,
        "coverage": payload["coverage"],
        "family_cancellation_audit": family_audit,
        "top_components_by_abs_partial_ic10": component_rows[:20],
        "guardrails": payload["guardrails"],
    }
    SUMMARY.write_text(json.dumps(compact, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps({
        "coverage": payload["coverage"],
        "family_cancellation": [[x["family"], x["family_ic10"], x["max_component_abs_ic_minus_family_abs_ic"], x["cancellation_flag"], None if x["strongest_abs_component"] is None else x["strongest_abs_component"]["members"]] for x in family_audit],
        "top_components": [[x["key"], x["members"], x["ic10"], x["ic10_2022_present"], x["partial_ic10"], x["component_ablation_delta_pct"]] for x in component_rows[:12]],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
