from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "update_data.py"
OUT = ROOT / "docs" / "data" / "current.json"


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
    parts = []
    weights = []
    for bucket, bw in model.get("bucket_weights", {}).items():
        members = [m for m in active_members if m.get("bucket") == bucket]
        num_parts = []
        den_parts = []
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


def metrics(state: pd.Series, close: pd.Series):
    x = pd.DataFrame({"state": state, "close": close.reindex(state.index)}).dropna()
    if len(x) < 120:
        return None
    vals = x["close"].to_numpy(float)
    worst20 = []
    for i in range(len(x)):
        tail = vals[i + 1 : min(len(vals), i + 21)]
        worst20.append((np.nanmin(tail) / vals[i] - 1.0) * 100.0 if len(tail) else np.nan)
    x["worst20"] = worst20
    v = x[["state", "worst20"]].dropna()
    if len(v) < 100:
        return None
    corr = float(v["state"].rank().corr(v["worst20"].rank()))
    q25, q75 = v["state"].quantile([0.25, 0.75])
    low = v[v["state"] <= q25]["worst20"]
    high = v[v["state"] >= q75]["worst20"]
    separation = float(high.mean() - low.mean()) if len(low) and len(high) else np.nan
    noise = float(x["state"].diff().std())
    span = float(x["state"].std())
    objective = 100.0 * corr + 5.0 * separation - 0.30 * noise + 0.10 * span
    return {
        "n": int(len(v)),
        "risk_rank_corr": round(corr, 4),
        "quartile_worst20_separation_pct": round(separation, 4),
        "daily_score_change_std": round(noise, 4),
        "score_std": round(span, 4),
        "objective": round(float(objective), 4),
    }


def max_peer_corr(active: list[dict], series_store: dict):
    out = {}
    by_bucket = {}
    for m in active:
        by_bucket.setdefault(m.get("bucket"), []).append(m["id"])
    for bucket, ids in by_bucket.items():
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
    baseline = metrics(baseline_state, close)
    if baseline is None:
        raise RuntimeError("Baseline metrics unavailable")
    redundancy = max_peer_corr(active, series_store)
    rows = []
    for member in active:
        reduced = [m for m in active if m["id"] != member["id"]]
        state = historical_state(model, reduced, series_store, ordered, idx)
        met = metrics(state, close)
        if met is None:
            continue
        delta = float(met["objective"] - baseline["objective"])
        red = redundancy.get(member["id"], {})
        peer_corr = red.get("abs_corr_5d_change")
        if delta >= 0.8 or (delta >= 0.25 and peer_corr is not None and peer_corr >= 0.75):
            rec = "remove"
        elif delta >= 0.0 or (peer_corr is not None and peer_corr >= 0.90):
            rec = "review"
        else:
            rec = "keep"
        rows.append({
            "id": member["id"],
            "bucket": member.get("bucket"),
            "objective_without": met["objective"],
            "delta_if_removed": round(delta, 4),
            "risk_rank_corr_without": met["risk_rank_corr"],
            "quartile_separation_without_pct": met["quartile_worst20_separation_pct"],
            "daily_noise_without": met["daily_score_change_std"],
            "max_peer": red.get("peer"),
            "max_peer_abs_corr_5d_change": peer_corr,
            "recommendation": rec,
        })
    rows.sort(key=lambda x: x["delta_if_removed"], reverse=True)
    report = {
        "status": "ok",
        "method": "leave-one-out on Market Model V2 active indicators",
        "sample_start": str(baseline_state.index.min().date()),
        "sample_end": str(baseline_state.index.max().date()),
        "baseline": baseline,
        "interpretation": "Positive delta_if_removed means the historical risk-separation objective improved when that indicator was removed. Redundancy uses absolute correlation of 5-day score changes within the same bucket.",
        "objective_definition": "100*risk-rank-correlation + 5*top-vs-bottom-quartile future worst-20d separation - 0.30*daily score noise + 0.10*score dispersion",
        "results": rows,
        "remove_candidates": [x["id"] for x in rows if x["recommendation"] == "remove"],
        "review_candidates": [x["id"] for x in rows if x["recommendation"] == "review"],
        "note": "Exploratory reconstructed-history diagnostic, not point-in-time OOS. Use as a pruning aid, not as sole evidence."
    }
    payload = json.loads(OUT.read_text(encoding="utf-8"))
    payload["ablation_test"] = report
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"baseline": baseline, "remove": report["remove_candidates"], "review": report["review_candidates"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
