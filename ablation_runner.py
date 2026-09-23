from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "update_data.py"
OUT = ROOT / "docs" / "data" / "current.json"
OOS_START = pd.Timestamp("2022-01-01")


def run_update_and_capture():
    source = SRC.read_text(encoding="utf-8")
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
    return ns, ns.get("_ABLATION_CAPTURE")


def historical_state(model: dict, active_members: list[dict], series_store: dict, ordered: list[dict], idx: pd.DatetimeIndex):
    item_by_id = {x["id"]: x for x in ordered}
    parts, weights = [], []
    for bucket, bw in model.get("bucket_weights", {}).items():
        members = [m for m in active_members if m.get("bucket") == bucket]
        num_parts, den_parts = [], []
        for m in members:
            item = item_by_id.get(m["id"])
            ser = series_store.get(m["id"])
            if not item or ser is None or ser.empty:
                continue
            pol = float(item.get("impact_polarity", 0) or 0)
            if pol == 0:
                continue
            w = max(0.0, float(item.get("importance_score", 50)) * float(m.get("multiplier", 1.0)))
            a = pd.Series(ser).reindex(idx).ffill()
            num_parts.append(pol * (a - 50.0) * w)
            den_parts.append(a.notna().astype(float) * w)
        if not num_parts:
            continue
        n = pd.concat(num_parts, axis=1).sum(axis=1, min_count=1)
        d = pd.concat(den_parts, axis=1).sum(axis=1, min_count=1)
        bs = (50.0 + n / d).where(d > 0)
        parts.append((bs - 50.0) * float(bw))
        weights.append(bs.notna().astype(float) * float(bw))
    if not parts:
        return pd.Series(dtype=float)
    n = pd.concat(parts, axis=1).sum(axis=1, min_count=1)
    d = pd.concat(weights, axis=1).sum(axis=1, min_count=1)
    return (50.0 + n / d).clip(0, 100).where(d >= 0.70).dropna()


def build_eval_frame(state: pd.Series, close: pd.Series):
    x = pd.DataFrame({"state": state, "close": close.reindex(state.index)}).dropna()
    vals = x["close"].to_numpy(float)
    worst20 = []
    for i in range(len(x)):
        tail = vals[i + 1 : min(len(vals), i + 21)]
        worst20.append((np.nanmin(tail) / vals[i] - 1.0) * 100.0 if len(tail) else np.nan)
    x["worst20"] = worst20
    return x


def metrics_from_frame(x: pd.DataFrame):
    x = x.dropna(subset=["state", "worst20"]).copy()
    if len(x) < 100:
        return None
    corr = float(x["state"].rank().corr(x["worst20"].rank()))
    q25, q50, q75 = x["state"].quantile([0.25, 0.50, 0.75])
    q1 = x[x["state"] <= q25]["worst20"]
    q4 = x[x["state"] >= q75]["worst20"]
    separation = float(q4.mean() - q1.mean()) if len(q1) and len(q4) else np.nan
    tail_cut = -5.0
    low_tail = float((q1 <= tail_cut).mean() * 100.0) if len(q1) else np.nan
    high_tail = float((q4 <= tail_cut).mean() * 100.0) if len(q4) else np.nan
    tail_gap = low_tail - high_tail
    bins = [x["state"] <= q25, (x["state"] > q25) & (x["state"] <= q50), (x["state"] > q50) & (x["state"] < q75), x["state"] >= q75]
    means = [float(x.loc[b, "worst20"].mean()) for b in bins]
    monotonic_steps = sum(1 for a, b in zip(means, means[1:]) if b >= a)
    noise = float(x["state"].diff().std())
    span = float(x["state"].std())
    noise_ratio = noise / span if span > 0 else np.nan
    objective = 4.0 * separation + 0.08 * tail_gap + 0.75 * monotonic_steps + 8.0 * corr - 0.8 * noise_ratio
    return {
        "n": int(len(x)),
        "risk_rank_corr": round(corr, 4),
        "quartile_worst20_separation_pct": round(separation, 4),
        "bottom_minus_top_5pct_tail_rate_pp": round(tail_gap, 2),
        "quartile_monotonic_steps": int(monotonic_steps),
        "quartile_worst20_means_pct": [round(v, 4) for v in means],
        "daily_score_change_std": round(noise, 4),
        "score_std": round(span, 4),
        "noise_to_span": round(noise_ratio, 4) if np.isfinite(noise_ratio) else None,
        "objective": round(float(objective), 4),
    }


def split_metrics(state: pd.Series, close: pd.Series):
    x = build_eval_frame(state, close)
    full = metrics_from_frame(x)
    train = metrics_from_frame(x[x.index < OOS_START])
    oos = metrics_from_frame(x[x.index >= OOS_START])
    return {"full": full, "train_2016_2021": train, "oos_2022_present": oos}


def max_peer_corr(active: list[dict], series_store: dict):
    out = {}
    by_bucket = {}
    for m in active:
        by_bucket.setdefault(m.get("bucket"), []).append(m["id"])
    for _, ids in by_bucket.items():
        changes = {}
        for k in ids:
            s = series_store.get(k)
            if s is not None and not s.empty:
                changes[k] = pd.Series(s).sort_index().diff(5).dropna()
        for k in ids:
            best = (None, 0.0)
            a = changes.get(k)
            if a is None:
                out[k] = {"peer": None, "abs_corr_5d_change": None}
                continue
            for j in ids:
                if j == k or j not in changes:
                    continue
                z = pd.concat([a, changes[j]], axis=1, join="inner").dropna()
                if len(z) < 60:
                    continue
                c = float(z.iloc[:, 0].corr(z.iloc[:, 1]))
                if np.isfinite(c) and abs(c) > best[1]:
                    best = (j, abs(c))
            out[k] = {"peer": best[0], "abs_corr_5d_change": round(best[1], 4) if best[0] else None}
    return out


def delta(a, b, key):
    if not a or not b or a.get(key) is None or b.get(key) is None:
        return None
    return float(a[key]) - float(b[key])


def main():
    ns, cap = run_update_and_capture()
    if not cap:
        raise RuntimeError("No ablation capture generated")
    model = ns["MODEL"]
    active = list(model.get("active", []))
    series_store = cap["series_store"]
    mk = cap["mk"]
    ordered = cap["ordered"]
    if "SPY" not in mk:
        raise RuntimeError("SPY missing")
    close = mk["SPY"]["Close"].dropna().sort_index()
    idx = close.index
    baseline_state = historical_state(model, active, series_store, ordered, idx)
    baseline = split_metrics(baseline_state, close)
    if baseline["full"] is None or baseline["oos_2022_present"] is None:
        raise RuntimeError("Baseline metrics unavailable")
    redundancy = max_peer_corr(active, series_store)
    rows = []
    for member in active:
        reduced = [m for m in active if m["id"] != member["id"]]
        state = historical_state(model, reduced, series_store, ordered, idx)
        met = split_metrics(state, close)
        if met["full"] is None or met["oos_2022_present"] is None:
            continue
        d_full_sep = delta(met["full"], baseline["full"], "quartile_worst20_separation_pct")
        d_oos_sep = delta(met["oos_2022_present"], baseline["oos_2022_present"], "quartile_worst20_separation_pct")
        d_full_obj = delta(met["full"], baseline["full"], "objective")
        d_oos_obj = delta(met["oos_2022_present"], baseline["oos_2022_present"], "objective")
        d_noise = delta(met["full"], baseline["full"], "noise_to_span")
        red = redundancy.get(member["id"], {})
        peer_corr = red.get("abs_corr_5d_change")

        # Conservative recommendation: an automatic remove candidate must improve
        # both full-history and OOS risk separation, or be extremely redundant
        # without hurting OOS. This avoids deleting useful macro/credit anchors on
        # the basis of one in-sample objective.
        improves_both = (d_full_sep is not None and d_oos_sep is not None and d_full_sep >= 0.12 and d_oos_sep >= 0.10)
        oos_not_hurt = d_oos_sep is not None and d_oos_sep >= -0.05
        highly_redundant = peer_corr is not None and peer_corr >= 0.90
        objective_support = d_full_obj is not None and d_oos_obj is not None and d_full_obj > 0 and d_oos_obj > 0
        if improves_both and (objective_support or (d_noise is not None and d_noise <= 0.02)):
            rec = "remove"
        elif highly_redundant and oos_not_hurt:
            rec = "remove"
        elif (d_oos_sep is not None and d_oos_sep > 0.05) or (peer_corr is not None and peer_corr >= 0.80):
            rec = "review"
        else:
            rec = "keep"

        rows.append({
            "id": member["id"],
            "bucket": member.get("bucket"),
            "full_delta_objective_if_removed": round(d_full_obj, 4) if d_full_obj is not None else None,
            "oos_delta_objective_if_removed": round(d_oos_obj, 4) if d_oos_obj is not None else None,
            "full_delta_risk_separation_if_removed_pct": round(d_full_sep, 4) if d_full_sep is not None else None,
            "oos_delta_risk_separation_if_removed_pct": round(d_oos_sep, 4) if d_oos_sep is not None else None,
            "full_delta_noise_to_span_if_removed": round(d_noise, 4) if d_noise is not None else None,
            "max_peer": red.get("peer"),
            "max_peer_abs_corr_5d_change": peer_corr,
            "without": met,
            "recommendation": rec,
        })

    rows.sort(key=lambda x: (x["recommendation"] == "remove", x["oos_delta_risk_separation_if_removed_pct"] or -999), reverse=True)
    report = {
        "status": "ok",
        "version": "ABLATION-V2-OOS-2026-09-23",
        "method": "leave-one-out on Market Model V2 active indicators with full-history and OOS checks",
        "sample_start": str(baseline_state.index.min().date()),
        "sample_end": str(baseline_state.index.max().date()),
        "oos_start": str(OOS_START.date()),
        "baseline": baseline,
        "interpretation": "Positive risk-separation delta means removing the factor improved the gap between high-score and low-score future worst-20d outcomes. Remove recommendations require cross-checking OOS and redundancy, not one in-sample objective.",
        "objective_definition": "4*quartile future-worst20 separation + 0.08*tail-risk-rate gap + 0.75*monotonic quartile steps + 8*rank-correlation - 0.8*noise/span",
        "results": rows,
        "remove_candidates": [x["id"] for x in rows if x["recommendation"] == "remove"],
        "review_candidates": [x["id"] for x in rows if x["recommendation"] == "review"],
        "note": "Still exploratory because reconstructed history is not fully point-in-time. OOS here means a chronological holdout, not a perfect publication-time backtest."
    }
    payload = json.loads(OUT.read_text(encoding="utf-8"))
    payload["ablation_test"] = report
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({
        "baseline": baseline,
        "remove": report["remove_candidates"],
        "review": report["review_candidates"]
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
