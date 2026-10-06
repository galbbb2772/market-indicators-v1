from __future__ import annotations

import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import ablation_runner as abl

DATA = ROOT / "docs" / "data"
PRUNE = DATA / "indicator_pruning_v1_summary.json"
OUT = DATA / "indicator_pruning_score_ab_v1.json"

OOS_START = pd.Timestamp("2022-01-01")


def future_10d(close: pd.Series):
    return (close.shift(-10) / close - 1.0) * 100.0


def spearman(a: pd.Series, b: pd.Series):
    z = pd.concat([a.rename("a"), b.rename("b")], axis=1).dropna()
    if len(z) < 100:
        return None
    r = z["a"].rank().corr(z["b"].rank())
    return None if pd.isna(r) else float(r)


def eval_state(state: pd.Series, close: pd.Series):
    risk = abl.split_metrics(state, close)
    fwd = future_10d(close).reindex(state.index)
    full_ic = spearman(state, fwd)
    oos_idx = state.index[state.index >= OOS_START]
    oos_ic = spearman(state.reindex(oos_idx), fwd.reindex(oos_idx))
    return {
        "risk": risk,
        "fwd10_spearman_full": None if full_ic is None else round(full_ic, 4),
        "fwd10_spearman_oos_2022_present": None if oos_ic is None else round(oos_ic, 4),
    }


def main():
    prune = json.loads(PRUNE.read_text(encoding="utf-8"))
    keep_ids = set(prune["keep_active"])

    ns, cap = abl.run_update_and_capture()
    if not cap:
        raise RuntimeError("No ablation capture generated")
    model = ns["MODEL"]
    active = list(model.get("active", []))
    store = cap["series_store"]
    mk = cap["mk"]
    ordered = cap["ordered"]

    # Keep the 11 approved directional candidates. Zero-polarity volume_speed
    # moves to Context because it contributes no independent vote.
    pruned_active = [m for m in active if m["id"] in keep_ids]
    current_directional = []
    item_by_id = {x["id"]: x for x in ordered}
    for m in active:
        pol = float((item_by_id.get(m["id"]) or {}).get("impact_polarity", 0) or 0)
        if pol != 0:
            current_directional.append(m)

    close = mk["SPY"]["Close"].dropna().sort_index()
    idx = close.index
    base_state = abl.historical_state(model, current_directional, store, ordered, idx)
    pruned_state = abl.historical_state(model, pruned_active, store, ordered, idx)

    z = pd.concat([base_state.rename("base"), pruned_state.rename("pruned")], axis=1).dropna()
    diff = z["pruned"] - z["base"]
    corr = float(z["base"].corr(z["pruned"]))
    mae = float(diff.abs().mean())
    p95 = float(diff.abs().quantile(.95))
    max_abs = float(diff.abs().max())

    base_eval = eval_state(base_state, close)
    prune_eval = eval_state(pruned_state, close)

    def delta(block, key):
        a = prune_eval["risk"][block].get(key)
        b = base_eval["risk"][block].get(key)
        if a is None or b is None:
            return None
        return round(float(a) - float(b), 4)

    payload = {
        "schema": "INDICATOR-PRUNING-SCORE-PRESERVATION-AB-V1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "research_only": True,
        "production_effect": "none",
        "current_directional_active_count": len(current_directional),
        "pruned_active_count": len(pruned_active),
        "current_directional_ids": [m["id"] for m in current_directional],
        "pruned_active_ids": [m["id"] for m in pruned_active],
        "demoted_or_archived_ids": [m["id"] for m in current_directional if m["id"] not in keep_ids],
        "zero_polarity_active_to_context": [m["id"] for m in active if m["id"] not in {x["id"] for x in current_directional}],
        "series_similarity": {
            "n": int(len(z)),
            "pearson_corr": round(corr, 6),
            "mean_abs_score_diff": round(mae, 4),
            "p95_abs_score_diff": round(p95, 4),
            "max_abs_score_diff": round(max_abs, 4),
        },
        "baseline": base_eval,
        "pruned": prune_eval,
        "deltas_pruned_minus_baseline": {
            "full_objective": delta("full", "objective"),
            "oos_objective": delta("oos_2022_present", "objective"),
            "full_risk_separation_pct": delta("full", "quartile_worst20_separation_pct"),
            "oos_risk_separation_pct": delta("oos_2022_present", "quartile_worst20_separation_pct"),
            "full_tail_gap_pp": delta("full", "bottom_minus_top_5pct_tail_rate_pp"),
            "oos_tail_gap_pp": delta("oos_2022_present", "bottom_minus_top_5pct_tail_rate_pp"),
            "full_noise_to_span": delta("full", "noise_to_span"),
            "oos_noise_to_span": delta("oos_2022_present", "noise_to_span"),
            "full_fwd10_ic": None if base_eval["fwd10_spearman_full"] is None or prune_eval["fwd10_spearman_full"] is None else round(prune_eval["fwd10_spearman_full"] - base_eval["fwd10_spearman_full"], 4),
            "oos_fwd10_ic": None if base_eval["fwd10_spearman_oos_2022_present"] is None or prune_eval["fwd10_spearman_oos_2022_present"] is None else round(prune_eval["fwd10_spearman_oos_2022_present"] - base_eval["fwd10_spearman_oos_2022_present"], 4),
        },
        "decision_gate": {
            "score_corr_ge_0_90": corr >= .90,
            "oos_objective_not_materially_worse": (delta("oos_2022_present", "objective") or -999) >= -0.25,
            "oos_risk_separation_not_worse": (delta("oos_2022_present", "quartile_worst20_separation_pct") or -999) >= -0.10,
            "raw_history_delete_allowed": False,
        },
    }
    payload["decision_gate"]["passes"] = all([
        payload["decision_gate"]["score_corr_ge_0_90"],
        payload["decision_gate"]["oos_objective_not_materially_worse"],
        payload["decision_gate"]["oos_risk_separation_not_worse"],
    ])

    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({
        "counts": [len(current_directional), len(pruned_active)],
        "similarity": payload["series_similarity"],
        "deltas": payload["deltas_pruned_minus_baseline"],
        "gate": payload["decision_gate"],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
