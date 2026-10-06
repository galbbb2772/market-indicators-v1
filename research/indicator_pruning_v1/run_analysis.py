from __future__ import annotations

import json
import math
from collections import defaultdict, deque
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

import ablation_runner as abl

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "docs" / "data"
OUT = DATA / "indicator_pruning_v1.json"
SUMMARY = DATA / "indicator_pruning_v1_summary.json"
REPORT = ROOT / "research" / "indicator_pruning_v1" / "REPORT.md"
VALIDATION = DATA / "indicator_validation_v1_summary.json"
COMPONENTS = DATA / "factor_components_source_invariant_v1.json"
SIG = DATA / "source_invariant_component_significance_v1_summary.json"

TARGET_HORIZON = 10
REDUNDANCY_CUTOFF = 0.85
RIDGE_ALPHA = 10.0


def spearman(a: pd.Series, b: pd.Series):
    z = pd.concat([a.rename("a"), b.rename("b")], axis=1).dropna()
    if len(z) < 120 or z["a"].nunique() < 2 or z["b"].nunique() < 2:
        return None, len(z)
    r = z["a"].rank(method="average").corr(z["b"].rank(method="average"))
    return (None if pd.isna(r) else float(r)), len(z)


def future_10d(close: pd.Series) -> pd.Series:
    close = close.astype(float).sort_index()
    return (close.shift(-TARGET_HORIZON) / close - 1.0) * 100.0


def ridge_fit_predict(Xtr, ytr, Xte, alpha=RIDGE_ALPHA):
    med = np.nanmedian(Xtr, axis=0)
    med = np.where(np.isfinite(med), med, 50.0)
    Xtr = np.where(np.isfinite(Xtr), Xtr, med)
    Xte = np.where(np.isfinite(Xte), Xte, med)
    mu = np.mean(Xtr, axis=0)
    sd = np.std(Xtr, axis=0)
    sd = np.where(sd > 1e-12, sd, 1.0)
    A = (Xtr - mu) / sd
    B = (Xte - mu) / sd
    ymean = float(np.mean(ytr))
    yc = ytr - ymean
    if A.shape[1] == 0:
        return np.repeat(ymean, len(Xte))
    beta = np.linalg.solve(A.T @ A + alpha * np.eye(A.shape[1]), A.T @ yc)
    return ymean + B @ beta


def active_loyo_ablation(X: pd.DataFrame, y: pd.Series):
    z = X.copy()
    z["target"] = y
    z = z[z.index.year >= 2017]
    cols = list(X.columns)
    actual, full_pred = [], []
    without = {c: [] for c in cols}
    folds = []
    for yr in sorted(set(z.index.year)):
        te = z[z.index.year == yr]
        tr = z[z.index.year != yr]
        te = te[te["target"].notna()]
        tr = tr[tr["target"].notna()]
        if len(te) < 20 or len(tr) < 252:
            continue
        Xtr = tr[cols].to_numpy(float)
        Xte = te[cols].to_numpy(float)
        ytr = tr["target"].to_numpy(float)
        yte = te["target"].to_numpy(float)
        fp = ridge_fit_predict(Xtr, ytr, Xte)
        actual.extend(yte.tolist())
        full_pred.extend(fp.tolist())
        for j, c in enumerate(cols):
            keep = [k for k in range(len(cols)) if k != j]
            without[c].extend(ridge_fit_predict(Xtr[:, keep], ytr, Xte[:, keep]).tolist())
        folds.append({"year": int(yr), "n": int(len(te))})
    yv = np.asarray(actual)
    fp = np.asarray(full_pred)
    full_mse = float(np.mean((fp - yv) ** 2))
    out = {}
    for c in cols:
        p = np.asarray(without[c])
        mse = float(np.mean((p - yv) ** 2))
        delta = mse - full_mse
        out[c] = {
            "without_mse": round(mse, 6),
            "delta_mse_without_minus_full": round(delta, 6),
            "delta_pct_of_full_mse": round(100.0 * delta / full_mse, 4) if full_mse > 0 else None,
            "helps_full_model_if_positive": bool(delta > 0),
        }
    return {"n": len(yv), "full_mse": round(full_mse, 6), "indicators": out, "folds": folds}


def partial_spearman(X: pd.DataFrame, y: pd.Series, target_col: str):
    z = X.copy()
    z["target"] = y
    z = z.dropna(subset=["target"])
    cols = list(X.columns)
    ranks = z[cols + ["target"]].rank(method="average")
    others = [c for c in cols if c != target_col]
    if len(ranks) < 120:
        return None, len(ranks)
    xt = ranks[target_col].to_numpy(float)
    yt = ranks["target"].to_numpy(float)
    if others:
        A = ranks[others].to_numpy(float)
        med = np.nanmedian(A, axis=0)
        A = np.where(np.isfinite(A), A, med)
        A = np.column_stack([np.ones(len(A)), A])
        bx = np.linalg.lstsq(A, np.where(np.isfinite(xt), xt, np.nanmedian(xt)), rcond=None)[0]
        by = np.linalg.lstsq(A, yt, rcond=None)[0]
        rx = xt - A @ bx
        ry = yt - A @ by
    else:
        rx, ry = xt, yt
    if np.std(rx) <= 1e-12 or np.std(ry) <= 1e-12:
        return None, len(ranks)
    r = float(np.corrcoef(rx, ry)[0, 1])
    return (None if not np.isfinite(r) else r), len(ranks)


def redundancy_pairs(Xraw: pd.DataFrame):
    ch = Xraw.diff(5)
    cols = list(ch.columns)
    pairs = []
    graph = defaultdict(set)
    for i, a in enumerate(cols):
        for b in cols[i + 1:]:
            r, n = spearman(ch[a], ch[b])
            if r is None:
                continue
            ar = abs(r)
            if ar >= REDUNDANCY_CUTOFF:
                pairs.append({"a": a, "b": b, "rho": round(r, 4), "abs_rho": round(ar, 4), "n": n})
                graph[a].add(b)
                graph[b].add(a)
    pairs.sort(key=lambda x: x["abs_rho"], reverse=True)
    seen, comps = set(), []
    for k in sorted(graph):
        if k in seen:
            continue
        q = deque([k]); comp = []
        while q:
            x = q.popleft()
            if x in seen:
                continue
            seen.add(x); comp.append(x)
            q.extend(graph[x] - seen)
        if len(comp) > 1:
            comps.append(sorted(comp))
    comps.sort(key=lambda x: (-len(x), x))
    return pairs, comps


def main():
    summary = json.loads(VALIDATION.read_text(encoding="utf-8"))
    active_rows = summary["active_all"]
    active_ids = [x["id"] for x in active_rows]
    legacy = {x["id"]: x for x in active_rows}

    comp = json.loads(COMPONENTS.read_text(encoding="utf-8"))
    source_invariant = set(comp.get("assignment", {}))
    sig = json.loads(SIG.read_text(encoding="utf-8"))
    forward_priority_members = {
        m for row in sig.get("forward_oos_priority", []) for m in (row.get("members") or [])
    }
    descriptive_members = {
        m for row in sig.get("regime_or_descriptive", []) for m in (row.get("members") or [])
    }

    ns, cap = abl.run_update_and_capture()
    if not cap:
        raise RuntimeError("No ablation capture generated")
    store = cap["series_store"]
    mk = cap["mk"]
    ordered = cap["ordered"]
    meta = {x["id"]: x for x in ordered}
    if "SPY" not in mk:
        raise RuntimeError("SPY missing from market capture")

    close = mk["SPY"]["Close"].dropna().sort_index()
    y = future_10d(close)
    raw = {}
    supportive = {}
    missing = []
    for k in active_ids:
        if k not in store:
            missing.append(k)
            continue
        s = pd.Series(store[k]).sort_index().reindex(close.index).ffill()
        raw[k] = s
        pol = int((meta.get(k) or {}).get("impact_polarity", legacy[k].get("polarity", 0)) or 0)
        supportive[k] = 50.0 + pol * (s - 50.0) if pol in (-1, 1) else s
    if missing:
        raise RuntimeError(f"Missing active series: {missing}")

    Xraw = pd.DataFrame(raw, index=close.index)
    X = pd.DataFrame(supportive, index=close.index)
    pairs, comps = redundancy_pairs(Xraw)
    loyo = active_loyo_ablation(X, y)

    metrics = {}
    for k in active_ids:
        pr, pn = partial_spearman(X, y, k)
        recent_idx = y.index[y.index >= pd.Timestamp("2022-01-01")]
        rr, rn = spearman(X[k].reindex(recent_idx), y.reindex(recent_idx))
        full_r, full_n = spearman(X[k], y)
        base = legacy[k]
        metrics[k] = {
            "id": k,
            "name": base.get("name"),
            "bucket": base.get("bucket"),
            "source_invariant": k in source_invariant,
            "forward_oos_priority_member": k in forward_priority_members,
            "component_watchlist_member": k in descriptive_members,
            "rho10": None if full_r is None else round(full_r, 4),
            "rho10_2022_present": None if rr is None else round(rr, 4),
            "partial_rho10_vs_other_active": None if pr is None else round(pr, 4),
            "phase_same_sign_pct10": base.get("phase_same_sign_pct10"),
            "rolling_median_rho10": base.get("rolling_median_rho10"),
            "max_peer_all": base.get("max_peer"),
            "max_peer_abs_rho_all": base.get("max_peer_abs_rho"),
            "loyo": loyo["indicators"][k],
        }

    # Deterministic ranking inside active-only redundancy components.
    def rep_score(k):
        m = metrics[k]
        return (
            1 if m["source_invariant"] else 0,
            float(m["loyo"].get("delta_pct_of_full_mse") or -999),
            abs(float(m["partial_rho10_vs_other_active"] or 0)),
            abs(float(m["rho10_2022_present"] or 0)),
            float(m["phase_same_sign_pct10"] or 0),
            abs(float(m["rho10"] or 0)),
            k,
        )

    representative = {}
    component_of = {}
    for idx, comp_ids in enumerate(comps, 1):
        best = max(comp_ids, key=rep_score)
        for k in comp_ids:
            representative[k] = best
            component_of[k] = idx

    actions = {}
    reasons = {}
    for k in active_ids:
        m = metrics[k]
        delta = float(m["loyo"].get("delta_pct_of_full_mse") or 0)
        partial = abs(float(m["partial_rho10_vs_other_active"] or 0))
        recent = abs(float(m["rho10_2022_present"] or 0))
        full = abs(float(m["rho10"] or 0))
        phase = float(m["phase_same_sign_pct10"] or 0)

        if k in representative and representative[k] != k:
            rep = representative[k]
            # Exact / near-exact duplicate gets Archive; otherwise Context.
            pair_rho = max(
                [p["abs_rho"] for p in pairs if {p["a"], p["b"]} == {k, rep}] or [0]
            )
            if pair_rho >= 0.98:
                actions[k] = "ARCHIVE_DUPLICATE"
                reasons[k] = f"active-active duplicate of {rep}; abs 5d-change rho={pair_rho:.3f}"
            else:
                actions[k] = "CONTEXT_REDUNDANT"
                reasons[k] = f"redundancy cluster representative={rep}; keep for context, not scoring"
            continue

        strong_incremental = delta >= 0.05 or partial >= 0.04
        stable_recent = recent >= 0.05 and phase >= 80
        clearly_weak = full < 0.03 and recent < 0.03 and phase < 80
        source_uncertain = not m["source_invariant"]

        if clearly_weak:
            actions[k] = "CONTEXT_WEAK"
            reasons[k] = "weak absolute/recent IC and limited phase stability"
        elif strong_incremental and (m["source_invariant"] or stable_recent):
            actions[k] = "KEEP_ACTIVE"
            reasons[k] = "incremental information survives active-set controls"
        elif stable_recent and not source_uncertain:
            actions[k] = "KEEP_ACTIVE"
            reasons[k] = "source-invariant and recent/stable directional information"
        elif source_uncertain and not strong_incremental:
            actions[k] = "CONTEXT_SOURCE_DEPENDENT"
            reasons[k] = "not source-invariant and no strong active-set incremental evidence"
        else:
            actions[k] = "CONTEXT_LOW_INCREMENTAL"
            reasons[k] = "historically informative but weak incremental evidence after controls"

    # Guarantee one representative per active redundancy component is not archived solely due duplication.
    for comp_ids in comps:
        rep = representative[comp_ids[0]]
        if actions[rep].startswith("ARCHIVE"):
            actions[rep] = "CONTEXT_LOW_INCREMENTAL"
            reasons[rep] = "retained as redundancy-cluster representative"

    rows = []
    for k in active_ids:
        rows.append({
            **metrics[k],
            "active_redundancy_component": component_of.get(k),
            "cluster_representative": representative.get(k),
            "proposed_action": actions[k],
            "reason": reasons[k],
        })

    counts = {}
    for r in rows:
        counts[r["proposed_action"]] = counts.get(r["proposed_action"], 0) + 1

    payload = {
        "schema": "INDICATOR-PRUNING-V1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "research_only": True,
        "production_effect": "none",
        "current_active_count": len(active_ids),
        "target_horizon_days": TARGET_HORIZON,
        "redundancy_cutoff_abs_spearman_5d_change": REDUNDANCY_CUTOFF,
        "active_only_redundancy_pairs": pairs,
        "active_only_redundancy_components": comps,
        "active_ridge_loyo": loyo,
        "proposed_action_counts": counts,
        "rows": rows,
        "guardrails": {
            "raw_history_deleted": False,
            "production_membership_changed": False,
            "automatic_removal": False,
            "note": "Pruning proposal only. Archive means remove from active scoring while retaining source/history.",
        },
    }
    DATA.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    compact = {
        "schema": "INDICATOR-PRUNING-V1-SUMMARY",
        "generated_at": payload["generated_at"],
        "research_only": True,
        "current_active_count": len(active_ids),
        "proposed_action_counts": counts,
        "active_only_redundancy_components": comps,
        "rows": rows,
        "guardrails": payload["guardrails"],
    }
    SUMMARY.write_text(json.dumps(compact, ensure_ascii=False, indent=2), encoding="utf-8")

    keep = [r for r in rows if r["proposed_action"] == "KEEP_ACTIVE"]
    context = [r for r in rows if r["proposed_action"].startswith("CONTEXT")]
    archive = [r for r in rows if r["proposed_action"].startswith("ARCHIVE")]

    md = [
        "# Indicator Pruning V1",
        "",
        "**Research-only. No production indicator has been physically deleted or reweighted.**",
        "",
        f"Current active directional indicators: **{len(active_ids)}**.",
        f"Proposed KEEP_ACTIVE: **{len(keep)}**; Context: **{len(context)}**; Archive duplicate: **{len(archive)}**.",
        "",
        "The pruning order is: active-only redundancy -> active-set partial Spearman -> leave-one-year-out Ridge ablation -> recent/phase stability -> source invariance.",
        "",
        "## Proposed KEEP_ACTIVE",
        "",
        "| indicator | rho10 | recent rho10 | partial rho10 | LOYO delta % | source-invariant | reason |",
        "|---|---:|---:|---:|---:|---|---|",
    ]
    for r in sorted(keep, key=lambda x: abs(x.get("partial_rho10_vs_other_active") or 0), reverse=True):
        md.append(
            f"| {r['id']} | {r['rho10']} | {r['rho10_2022_present']} | "
            f"{r['partial_rho10_vs_other_active']} | {r['loyo']['delta_pct_of_full_mse']} | "
            f"{r['source_invariant']} | {r['reason']} |"
        )
    md += [
        "",
        "## Proposed Context",
        "",
        "| indicator | action | cluster rep | rho10 | recent rho10 | partial rho10 | LOYO delta % | reason |",
        "|---|---|---|---:|---:|---:|---:|---|",
    ]
    for r in context:
        md.append(
            f"| {r['id']} | {r['proposed_action']} | {r.get('cluster_representative') or ''} | "
            f"{r['rho10']} | {r['rho10_2022_present']} | {r['partial_rho10_vs_other_active']} | "
            f"{r['loyo']['delta_pct_of_full_mse']} | {r['reason']} |"
        )
    md += ["", "## Proposed Archive duplicates", ""]
    if archive:
        md += [
            "| indicator | representative | reason |",
            "|---|---|---|",
        ]
        for r in archive:
            md.append(f"| {r['id']} | {r.get('cluster_representative') or ''} | {r['reason']} |")
    else:
        md.append("No active indicator met the exact/near-exact active-active duplicate archive rule.")

    md += [
        "",
        "## Guardrail",
        "",
        "This result proposes membership changes only. Raw indicator histories stay intact. "
        "A second exact scoring/backtest pass should compare the current active set with the pruned set before changing the dashboard/model role labels.",
    ]
    REPORT.write_text("\n".join(md) + "\n", encoding="utf-8")

    print(json.dumps({
        "active": len(active_ids),
        "counts": counts,
        "redundancy_components": comps,
        "keep": [x["id"] for x in keep],
        "context": [x["id"] for x in context],
        "archive": [x["id"] for x in archive],
        "full_mse": loyo["full_mse"],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
