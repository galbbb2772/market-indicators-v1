from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "docs" / "data"
OUT = DATA / "indicator_pruning_v1.json"
SUMMARY = DATA / "indicator_pruning_v1_summary.json"
REPORT = ROOT / "research" / "indicator_pruning_v1" / "REPORT.md"

VALID_SUMMARY = DATA / "indicator_validation_v1_summary.json"
VALID_FULL = DATA / "indicator_validation_v1.json"
COMP_FULL = DATA / "factor_components_source_invariant_v1.json"
COMP_SIG = DATA / "source_invariant_component_significance_v1_summary.json"

FROZEN_THROUGH = "2026-10-02"
REDUNDANCY = 0.85
NEAR_DUP = 0.90
EXACT_DUP = 0.98


def sgn(x):
    if x is None:
        return 0
    x = float(x)
    return 1 if x > 0 else (-1 if x < 0 else 0)


def absn(x):
    return abs(float(x or 0.0))


def main():
    vs = json.loads(VALID_SUMMARY.read_text(encoding="utf-8"))
    vf = json.loads(VALID_FULL.read_text(encoding="utf-8"))
    comp = json.loads(COMP_FULL.read_text(encoding="utf-8"))
    sig = json.loads(COMP_SIG.read_text(encoding="utf-8"))

    active = {x["id"]: dict(x) for x in vs["active_all"]}
    active_ids = list(active)
    source_invariant = set(comp.get("assignment", {}))

    # Component-level incremental evidence already contains partial IC and
    # leave-one-year-out / multivariate ablation from the frozen 2026-10-02 study.
    member_component = {}
    for row in comp.get("component_rows", []):
        for m in row.get("members") or []:
            member_component[m] = {
                "key": row.get("key"),
                "family": row.get("family"),
                "partial_ic10": row.get("partial_ic10"),
                "partial_ic10_2022_present": row.get("partial_ic10_2022_present"),
                "univariate_loyo_improvement_pct": row.get("univariate_loyo_improvement_pct"),
                "component_ablation_delta_pct": row.get("component_ablation_delta_pct"),
                "component_helps_full_model_if_positive": row.get("component_helps_full_model_if_positive"),
            }

    forward_members = {
        m for row in sig.get("forward_oos_priority", []) for m in (row.get("members") or [])
    }
    watch_members = {
        m for row in sig.get("regime_or_descriptive", []) for m in (row.get("members") or [])
    }

    # Pull active-active redundancy from the already frozen full validation.
    pairs = []
    for p in (vf.get("redundancy") or {}).get("pairs", []):
        if p.get("a") in active and p.get("b") in active and float(p.get("abs_rho") or 0) >= REDUNDANCY:
            pairs.append({
                "a": p["a"], "b": p["b"],
                "rho": p.get("rho"), "abs_rho": p.get("abs_rho"), "n": p.get("n")
            })
    pairs.sort(key=lambda x: float(x["abs_rho"]), reverse=True)

    def quality(k):
        r = active[k]
        c = member_component.get(k, {})
        full = absn(r.get("rho10_supportive"))
        recent = absn(r.get("era_2022_present_rho10"))
        phase = float(r.get("phase_same_sign_pct10") or 0)
        partial = absn(c.get("partial_ic10"))
        loyo = float(c.get("univariate_loyo_improvement_pct") or 0)
        abl = float(c.get("component_ablation_delta_pct") or 0)
        recent_agrees = (
            sgn(r.get("rho10_supportive")) != 0 and
            sgn(r.get("rho10_supportive")) == sgn(r.get("era_2022_present_rho10"))
        )
        return (
            1 if k in forward_members else 0,
            1 if k in source_invariant else 0,
            1 if recent_agrees else 0,
            phase,
            max(0.0, abl),
            max(0.0, loyo),
            partial,
            recent,
            full,
            k,
        )

    actions = {k: None for k in active_ids}
    reasons = {k: [] for k in active_ids}
    representative_of = {}

    # 1) Direct redundancy pruning. Exact duplicates are the only automatic Archive.
    # Near duplicates become Context only when the other member has a strictly better
    # deterministic evidence tuple. We do not collapse transitive clusters.
    for p in pairs:
        a, b, ar = p["a"], p["b"], float(p["abs_rho"])
        qa, qb = quality(a), quality(b)
        rep, weak = (a, b) if qa >= qb else (b, a)
        if actions.get(weak) == "ARCHIVE_DUPLICATE":
            continue
        representative_of[weak] = rep
        if ar >= EXACT_DUP:
            actions[weak] = "ARCHIVE_DUPLICATE"
            reasons[weak].append(f"near-identical active signal to {rep} (|rho|={ar:.3f})")
        elif ar >= NEAR_DUP:
            if actions.get(weak) is None:
                actions[weak] = "CONTEXT_REDUNDANT"
            reasons[weak].append(f"high active-active redundancy with {rep} (|rho|={ar:.3f})")

    # 2) Strength / stability / incremental classification for remaining active indicators.
    for k in active_ids:
        if actions[k] is not None:
            continue
        r = active[k]
        c = member_component.get(k, {})
        full = absn(r.get("rho10_supportive"))
        recent = absn(r.get("era_2022_present_rho10"))
        phase = float(r.get("phase_same_sign_pct10") or 0)
        partial = absn(c.get("partial_ic10"))
        loyo = float(c.get("univariate_loyo_improvement_pct") or 0)
        abl = float(c.get("component_ablation_delta_pct") or 0)
        full_sign = sgn(r.get("rho10_supportive"))
        recent_sign = sgn(r.get("era_2022_present_rho10"))
        recent_agrees = full_sign != 0 and full_sign == recent_sign

        weak = full < 0.03 and recent < 0.03 and phase <= 80
        unstable = full_sign != 0 and recent_sign != 0 and full_sign != recent_sign
        incremental = partial >= 0.04 or loyo > 0.10 or abl > 0.05
        strong_stable = full >= 0.075 and recent >= 0.04 and phase >= 90 and recent_agrees
        moderate_stable = full >= 0.04 and recent >= 0.05 and phase >= 90 and recent_agrees

        if weak:
            actions[k] = "CONTEXT_WEAK"
            reasons[k].append("weak full/recent IC with limited phase stability")
        elif unstable and not incremental:
            actions[k] = "CONTEXT_UNSTABLE"
            reasons[k].append("2022+ direction conflicts with full-sample direction")
        elif strong_stable:
            actions[k] = "KEEP_ACTIVE"
            reasons[k].append("strong, same-sign, phase-stable historical signal")
        elif incremental and moderate_stable:
            actions[k] = "KEEP_ACTIVE"
            reasons[k].append("incremental component/LOYO evidence plus stable recent direction")
        elif incremental and k in source_invariant:
            actions[k] = "KEEP_ACTIVE"
            reasons[k].append("source-invariant component retains incremental evidence")
        else:
            actions[k] = "CONTEXT_LOW_INCREMENTAL"
            reasons[k].append("historically informative but insufficient incremental/stability evidence for active scoring")

    rows = []
    for k in active_ids:
        r = active[k]
        c = member_component.get(k, {})
        rows.append({
            "id": k,
            "name": r.get("name"),
            "bucket": r.get("bucket"),
            "current_role": r.get("role"),
            "rho10_supportive": r.get("rho10_supportive"),
            "rho10_2022_present": r.get("era_2022_present_rho10"),
            "phase_same_sign_pct10": r.get("phase_same_sign_pct10"),
            "rolling_median_rho10": r.get("rolling_median_rho10"),
            "max_peer_all": r.get("max_peer"),
            "max_peer_abs_rho_all": r.get("max_peer_abs_rho"),
            "source_invariant": k in source_invariant,
            "forward_oos_priority_member": k in forward_members,
            "component_watchlist_member": k in watch_members,
            "component_key": c.get("key"),
            "component_family": c.get("family"),
            "component_partial_ic10": c.get("partial_ic10"),
            "component_partial_ic10_2022_present": c.get("partial_ic10_2022_present"),
            "component_univariate_loyo_improvement_pct": c.get("univariate_loyo_improvement_pct"),
            "component_ablation_delta_pct": c.get("component_ablation_delta_pct"),
            "proposed_action": actions[k],
            "representative": representative_of.get(k),
            "reason": "; ".join(reasons[k]),
        })

    counts = {}
    for r in rows:
        counts[r["proposed_action"]] = counts.get(r["proposed_action"], 0) + 1

    keep = [r for r in rows if r["proposed_action"] == "KEEP_ACTIVE"]
    context = [r for r in rows if r["proposed_action"].startswith("CONTEXT")]
    archive = [r for r in rows if r["proposed_action"].startswith("ARCHIVE")]

    payload = {
        "schema": "INDICATOR-PRUNING-V1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "frozen_through_market_date": FROZEN_THROUGH,
        "research_only": True,
        "production_effect": "none",
        "method": {
            "current_active_count": len(active_ids),
            "direct_active_redundancy_cutoff": REDUNDANCY,
            "near_duplicate_cutoff": NEAR_DUP,
            "archive_duplicate_cutoff": EXACT_DUP,
            "incremental_evidence": "source-invariant component partial IC + LOYO + component ablation",
            "stability_evidence": "10d full/recent IC + overlap phase sign stability",
            "no_new_market_data": True,
        },
        "active_active_redundancy_pairs": pairs,
        "proposed_action_counts": counts,
        "rows": rows,
        "guardrails": {
            "raw_indicator_history_deleted": False,
            "production_membership_changed": False,
            "weights_changed": False,
            "automatic_removal": False,
            "archive_semantics": "remove from active scoring only; retain history and source series",
        },
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    compact = {
        "schema": "INDICATOR-PRUNING-V1-SUMMARY",
        "generated_at": payload["generated_at"],
        "frozen_through_market_date": FROZEN_THROUGH,
        "current_active_count": len(active_ids),
        "proposed_action_counts": counts,
        "keep_active": [x["id"] for x in keep],
        "context": [x["id"] for x in context],
        "archive": [x["id"] for x in archive],
        "active_active_redundancy_pairs": pairs,
        "rows": rows,
        "guardrails": payload["guardrails"],
    }
    SUMMARY.write_text(json.dumps(compact, ensure_ascii=False, indent=2), encoding="utf-8")

    md = [
        "# Indicator Pruning V1",
        "",
        f"Frozen evidence through **{FROZEN_THROUGH}**. Research-only; no production membership/weight change.",
        "",
        f"Current active directional set: **{len(active_ids)}**.",
        f"Proposed KEEP_ACTIVE: **{len(keep)}**; Context: **{len(context)}**; Archive duplicate: **{len(archive)}**.",
        "",
        "## KEEP_ACTIVE",
        "",
        "| indicator | full IC10 | 2022+ IC10 | phase sign % | component partial IC | component LOYO % | reason |",
        "|---|---:|---:|---:|---:|---:|---|",
    ]
    for r in keep:
        md.append(
            f"| {r['id']} | {r['rho10_supportive']} | {r['rho10_2022_present']} | "
            f"{r['phase_same_sign_pct10']} | {r['component_partial_ic10']} | "
            f"{r['component_univariate_loyo_improvement_pct']} | {r['reason']} |"
        )
    md += [
        "",
        "## CONTEXT",
        "",
        "| indicator | proposed action | representative | full IC10 | 2022+ IC10 | reason |",
        "|---|---|---|---:|---:|---|",
    ]
    for r in context:
        md.append(
            f"| {r['id']} | {r['proposed_action']} | {r['representative'] or ''} | "
            f"{r['rho10_supportive']} | {r['rho10_2022_present']} | {r['reason']} |"
        )
    md += ["", "## ARCHIVE duplicates", ""]
    if archive:
        md += ["| indicator | representative | reason |", "|---|---|---|"]
        for r in archive:
            md.append(f"| {r['id']} | {r['representative'] or ''} | {r['reason']} |")
    else:
        md.append("No current Active indicator met the >=0.98 direct active-active duplicate rule.")

    md += [
        "",
        "## Interpretation",
        "",
        "Pruning here means **stop giving redundant/weak indicators an independent vote**. "
        "Context indicators remain visible for explanation/regime inspection. Archive indicators retain raw history, "
        "but should not independently enter the aggregate score.",
        "",
        "A separate score-preservation A/B should be run before changing live role labels: "
        "current Active set vs proposed pruned Active set, using the same frozen historical dates and Forward-OOS guardrails.",
    ]
    REPORT.write_text("\n".join(md) + "\n", encoding="utf-8")

    print(json.dumps({
        "active": len(active_ids),
        "counts": counts,
        "keep": [x["id"] for x in keep],
        "context": [x["id"] for x in context],
        "archive": [x["id"] for x in archive],
        "active_active_redundancy_pairs": pairs,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
