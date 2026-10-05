from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

import research_factor_map_v1 as fm
import research_factor_map_source_invariant_v1 as sfm

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "docs" / "data" / "source_invariant_component_significance_v1.json"
SUMMARY = ROOT / "docs" / "data" / "source_invariant_component_significance_v1_summary.json"
PRIOR = ROOT / "docs" / "data" / "factor_components_source_invariant_v1.json"
SPEC = "research/source_invariant_component_significance_v1/STUDY_SPEC.md"
SEED = 20261005
BLOCK = 20
BOOT_N = 1000
SHIFT_N = 1000
FROZEN_THROUGH = pd.Timestamp("2026-10-02")


def corr(a: np.ndarray, b: np.ndarray):
    if len(a) < 3 or np.std(a) <= 1e-12 or np.std(b) <= 1e-12:
        return np.nan
    return float(np.corrcoef(a, b)[0, 1])


def moving_block_bootstrap(x: np.ndarray, y: np.ndarray, rng: np.random.Generator):
    n = len(x)
    if n < max(120, BLOCK * 4):
        return []
    starts_max = n - BLOCK
    nblocks = int(np.ceil(n / BLOCK))
    vals = []
    base = np.arange(BLOCK)
    for _ in range(BOOT_N):
        starts = rng.integers(0, starts_max + 1, size=nblocks)
        idx = np.concatenate([s + base for s in starts])[:n]
        r = corr(x[idx], y[idx])
        if np.isfinite(r):
            vals.append(r)
    return vals


def circular_shift_null(x: np.ndarray, y: np.ndarray, rng: np.random.Generator):
    n = len(x)
    valid = np.arange(BLOCK, max(BLOCK + 1, n - BLOCK))
    if len(valid) == 0:
        return []
    shifts = rng.choice(valid, size=SHIFT_N, replace=True)
    vals = []
    for s in shifts:
        r = corr(x, np.roll(y, int(s)))
        if np.isfinite(r):
            vals.append(r)
    return vals


def bh_adjust(rows: list[dict]):
    valid = [(i, r["shift_p_two_sided"]) for i, r in enumerate(rows) if r.get("shift_p_two_sided") is not None]
    if not valid:
        return
    valid.sort(key=lambda z: z[1])
    m = len(valid)
    raw = [p for _, p in valid]
    adj = [None] * m
    running = 1.0
    for j in range(m - 1, -1, -1):
        rank = j + 1
        q = min(1.0, raw[j] * m / rank)
        running = min(running, q)
        adj[j] = running
    for (item, _), q in zip(valid, adj):
        rows[item]["bh_fdr_q"] = round(float(q), 6)


def same_nonzero_sign(a, b):
    if a is None or b is None or a == 0 or b == 0:
        return False
    return (a > 0) == (b > 0)


def main():
    _, cap = sfm.source_invariant_capture()
    if not cap:
        raise RuntimeError("No source-invariant capture generated")
    series_store = cap.get("series_store") or {}
    mk = cap.get("mk") or {}
    ordered = cap.get("ordered") or []
    if "SPY" not in mk:
        raise RuntimeError("SPY missing")

    prior = json.loads(PRIOR.read_text(encoding="utf-8"))
    prior_rows = {x["key"]: x for x in prior.get("component_rows", [])}

    close = mk["SPY"]["Close"].dropna().sort_index()
    close = close[close.index <= FROZEN_THROUGH]
    if close.empty or close.index.max() != FROZEN_THROUGH:
        raise RuntimeError(f"Frozen cutoff {FROZEN_THROUGH.date()} is not present as a completed SPY session")
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
        ss = ss[ss.index <= FROZEN_THROUGH]
        aligned = ss.reindex(frame.index).ffill().dropna()
        if len(aligned) < fm.MIN_OBS or ss.nunique() < fm.MIN_UNIQUE:
            excluded[k] = "insufficient_history_or_unique_values"
            continue
        eligible[k] = ss if pol == 1 else 100.0 - ss
        fam, method = fm.assign_family(k, m)
        assignment[k] = {"family": fam, "method": method, "polarity": pol, "name": m.get("name")}

    by_family = {}
    for k, info in assignment.items():
        by_family.setdefault(info["family"], []).append(k)

    components = []
    for fam in sorted(by_family):
        ids = sorted(by_family[fam])
        comps, _ = fm.connected_components(ids, eligible, frame.index)
        for i, members in enumerate(comps, 1):
            key = f"{fam}::c{i}"
            xs = [eligible[k].reindex(frame.index).ffill().rename(k) for k in members]
            score = pd.concat(xs, axis=1).mean(axis=1, skipna=True).dropna()
            components.append((key, fam, members, score))

    rows = []
    for ordinal, (key, fam, members, score) in enumerate(components):
        z = pd.concat([score.rename("x"), frame["fwd_10d"].rename("y")], axis=1).dropna()
        if len(z) < 120 or z["x"].nunique() < 2 or z["y"].nunique() < 2:
            continue
        ranks = z.rank(method="average")
        x = ranks["x"].to_numpy(float)
        y = ranks["y"].to_numpy(float)
        observed = corr(x, y)

        rng_boot = np.random.default_rng(SEED + ordinal * 2)
        rng_shift = np.random.default_rng(SEED + ordinal * 2 + 1)
        boots = moving_block_bootstrap(x, y, rng_boot)
        nulls = circular_shift_null(x, y, rng_shift)

        ci_lo = float(np.percentile(boots, 2.5)) if boots else None
        ci_hi = float(np.percentile(boots, 97.5)) if boots else None
        p = None
        if nulls and np.isfinite(observed):
            p = (1 + sum(abs(v) >= abs(observed) for v in nulls)) / (1 + len(nulls))

        hist = prior_rows.get(key, {})
        row = {
            "key": key,
            "family": fam,
            "members": members,
            "n": len(z),
            "ic10": None if not np.isfinite(observed) else round(float(observed), 6),
            "ic10_2022_present": hist.get("ic10_2022_present"),
            "partial_ic10": hist.get("partial_ic10"),
            "partial_ic10_2022_present": hist.get("partial_ic10_2022_present"),
            "phase_same_sign_pct10": hist.get("phase_same_sign_pct10"),
            "univariate_loyo_improvement_pct": hist.get("univariate_loyo_improvement_pct"),
            "q5_minus_q1_10d_pp": hist.get("q5_minus_q1_10d_pp"),
            "block_bootstrap": {
                "block_sessions": BLOCK,
                "replications": len(boots),
                "ci95_low": None if ci_lo is None else round(ci_lo, 6),
                "ci95_high": None if ci_hi is None else round(ci_hi, 6),
                "median": None if not boots else round(float(np.median(boots)), 6),
            },
            "circular_shift": {
                "replications": len(nulls),
                "p_two_sided": None if p is None else round(float(p), 6),
            },
            "shift_p_two_sided": None if p is None else float(p),
            "bh_fdr_q": None,
        }
        rows.append(row)

    bh_adjust(rows)

    for r in rows:
        ic = r.get("ic10")
        recent = r.get("ic10_2022_present")
        partial = r.get("partial_ic10")
        ci = r["block_bootstrap"]
        ci_excludes_zero = ci.get("ci95_low") is not None and ci.get("ci95_high") is not None and (ci["ci95_low"] > 0 or ci["ci95_high"] < 0)
        gates = {
            "abs_ic10_ge_0_05": ic is not None and abs(ic) >= 0.05,
            "recent_same_sign": same_nonzero_sign(ic, recent),
            "block_ci_excludes_zero": ci_excludes_zero,
            "bh_fdr_le_0_10": r.get("bh_fdr_q") is not None and r["bh_fdr_q"] <= 0.10,
            "phase_same_sign_ge_80": (r.get("phase_same_sign_pct10") or 0) >= 80.0,
            "partial_same_sign": same_nonzero_sign(ic, partial),
            "loyo_positive": (r.get("univariate_loyo_improvement_pct") or 0) > 0,
        }
        r["screening_gates"] = gates
        passed = sum(bool(v) for v in gates.values())
        if all(gates.values()):
            label = "forward_oos_priority"
        elif gates["abs_ic10_ge_0_05"] and passed >= 4:
            label = "regime_or_descriptive"
        else:
            label = "weak_or_unstable"
        r["screening_label"] = label
        r["screening_gate_pass_count"] = passed
        r.pop("shift_p_two_sided", None)

    rows.sort(key=lambda r: (r["screening_label"] == "forward_oos_priority", r["screening_gate_pass_count"], abs(r.get("ic10") or 0)), reverse=True)
    priority = [r for r in rows if r["screening_label"] == "forward_oos_priority"]
    regime = [r for r in rows if r["screening_label"] == "regime_or_descriptive"]

    payload = {
        "schema": "SOURCE-INVARIANT-COMPONENT-SIGNIFICANCE-V1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "research_only": True,
        "diagnostic_only": True,
        "post_discovery_screening": True,
        "production_effect": "none",
        "study_spec": SPEC,
        "frozen_through_market_date": str(FROZEN_THROUGH.date()),
        "coverage": {
            "spy_start": str(frame.index.min().date()),
            "spy_end": str(frame.index.max().date()),
            "spy_observations": len(frame),
            "eligible_directional_indicator_count": len(eligible),
            "component_count": len(rows),
        },
        "inference": {
            "seed": SEED,
            "block_sessions": BLOCK,
            "bootstrap_replications": BOOT_N,
            "circular_shift_replications": SHIFT_N,
            "multiple_testing": "Benjamini-Hochberg across all component 10D shift p-values",
        },
        "rows": rows,
        "forward_oos_priority_keys": [r["key"] for r in priority],
        "regime_or_descriptive_keys": [r["key"] for r in regime],
        "guardrails": {
            "may_change_production": False,
            "may_reweight_model": False,
            "may_remove_indicator": False,
            "historical_results_count_as_forward_oos": False,
        },
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    compact = {
        "schema": "SOURCE-INVARIANT-COMPONENT-SIGNIFICANCE-V1-SUMMARY",
        "generated_at": payload["generated_at"],
        "research_only": True,
        "frozen_through_market_date": payload["frozen_through_market_date"],
        "coverage": payload["coverage"],
        "forward_oos_priority": priority,
        "regime_or_descriptive": regime,
        "top_by_gate_count": rows[:15],
        "guardrails": payload["guardrails"],
    }
    SUMMARY.write_text(json.dumps(compact, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps({
        "frozen_through_market_date": payload["frozen_through_market_date"],
        "coverage": payload["coverage"],
        "priority": [[r["key"], r["ic10"], r["ic10_2022_present"], r["bh_fdr_q"], r["block_bootstrap"]["ci95_low"], r["block_bootstrap"]["ci95_high"], r["univariate_loyo_improvement_pct"]] for r in priority],
        "top": [[r["key"], r["screening_label"], r["screening_gate_pass_count"], r["ic10"], r["bh_fdr_q"]] for r in rows[:12]],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
