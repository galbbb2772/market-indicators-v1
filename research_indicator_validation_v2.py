from __future__ import annotations

import json
import math
from collections import defaultdict, deque
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

import ablation_runner as ar

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "docs/data/indicator_validation_v1.json"
SUMMARY = ROOT / "docs/data/indicator_validation_v1_summary.json"
SPEC = "research/indicator_validation_v1/STUDY_SPEC_V2.md"
HORIZONS = (1, 5, 10, 20)
MIN_OBS = 252
MIN_YEAR_OBS = 60
REDUNDANCY_CUT = 0.80
OOS_START = pd.Timestamp("2022-01-01")


def spearman(a: pd.Series, b: pd.Series):
    z = pd.concat([a.rename("a"), b.rename("b")], axis=1).dropna()
    if len(z) < 20 or z["a"].nunique() < 2 or z["b"].nunique() < 2:
        return None, int(len(z))
    r = z["a"].rank().corr(z["b"].rank())
    return (None if pd.isna(r) else float(r)), int(len(z))


def expanding_percentile(s: pd.Series, min_periods: int = 60):
    vals = s.astype(float)
    return vals.expanding(min_periods=min_periods).apply(lambda a: 100.0 * np.mean(a <= a[-1]) if len(a) else np.nan, raw=True)


def build_market_frame(close: pd.Series):
    x = pd.DataFrame({"close": close.dropna().sort_index()})
    for h in HORIZONS:
        x[f"fwd_{h}d"] = (x["close"].shift(-h) / x["close"] - 1.0) * 100.0
    x["ma200"] = x["close"].rolling(200, min_periods=150).mean()
    ret = x["close"].pct_change()
    x["rv20"] = ret.rolling(20).std() * math.sqrt(252) * 100.0
    x["rv20_pct_expanding"] = expanding_percentile(x["rv20"], 60)
    x["above_ma200"] = x["close"] >= x["ma200"]
    x["high_vol"] = x["rv20_pct_expanding"] >= 70.0
    return x


def model_meta(model: dict, ordered: list[dict]):
    active = {x["id"]: x for x in model.get("active", [])}
    context = set(model.get("context_only", [])); archived = set(model.get("archived", []))
    out = {}
    for obj in ordered:
        k = obj["id"]
        if k in active:
            role, bucket, mult = "active", active[k].get("bucket"), active[k].get("multiplier")
        elif k in context:
            role, bucket, mult = "context", None, None
        elif k in archived:
            role, bucket, mult = "archived", None, None
        else:
            role, bucket, mult = "other", None, None
        out[k] = {"name": obj.get("name"), "category": obj.get("category"), "type": obj.get("type"), "importance_score": obj.get("importance_score"), "impact_polarity": obj.get("impact_polarity", 0), "model_role": role, "model_bucket": bucket, "model_multiplier": mult}
    return out


def indicator_stats(key, s, meta, market):
    pol = float(meta.get("impact_polarity") or 0.0)
    raw = pd.Series(s).dropna().astype(float).sort_index()
    aligned = market.join(raw.rename("score"), how="inner").dropna(subset=["score"])
    if len(aligned) < MIN_OBS:
        return None
    aligned["directional_score"] = pol * (aligned["score"] - 50.0)
    feature = aligned["directional_score"] if pol != 0 else aligned["score"]
    full_ic, oos_ic = {}, {}
    for h in HORIZONS:
        r, n = spearman(feature, aligned[f"fwd_{h}d"])
        full_ic[str(h)] = {"rho": None if r is None else round(r, 4), "n": n}
        o = aligned[aligned.index >= OOS_START]
        ro, no = spearman(o["directional_score"] if pol != 0 else o["score"], o[f"fwd_{h}d"])
        oos_ic[str(h)] = {"rho": None if ro is None else round(ro, 4), "n": no}
    yearly, vals = {}, []
    for yr, g in aligned.groupby(aligned.index.year):
        r, n = spearman(g["directional_score"] if pol != 0 else g["score"], g["fwd_10d"])
        if n >= MIN_YEAR_OBS and r is not None:
            yearly[str(int(yr))] = {"rho_10d": round(r, 4), "n": n}; vals.append(r)
    regimes = {}
    masks = {"above_ma200": aligned["above_ma200"] == True, "below_ma200": aligned["above_ma200"] == False, "high_vol": aligned["high_vol"] == True, "low_normal_vol": aligned["high_vol"] == False}
    for name, mask in masks.items():
        g = aligned[mask]; r, n = spearman(g["directional_score"] if pol != 0 else g["score"], g["fwd_10d"])
        regimes[name] = {"rho_10d": None if r is None else round(r, 4), "n": n}
    choices = [(h, full_ic[str(h)]["rho"]) for h in HORIZONS if full_ic[str(h)]["rho"] is not None]
    best_h, best_r = (None, None) if not choices else max(choices, key=lambda x: abs(x[1]))
    return {"id": key, **meta, "history_start": str(aligned.index.min().date()), "history_end": str(aligned.index.max().date()), "usable_observations": int(len(aligned)), "full_ic": full_ic, "oos_2022_present_ic": oos_ic, "yearly_ic_10d": yearly, "stability": {"years_with_ic": len(vals), "positive_year_share": None if not vals else round(sum(x > 0 for x in vals) / len(vals), 4), "median_yearly_ic_10d": None if not vals else round(float(np.median(vals)), 4), "min_yearly_ic_10d": None if not vals else round(float(np.min(vals)), 4), "max_yearly_ic_10d": None if not vals else round(float(np.max(vals)), 4)}, "regime_ic_10d": regimes, "decay": {"best_abs_ic_horizon_days": best_h, "best_abs_ic_rho": best_r, "rho_by_horizon": {str(h): full_ic[str(h)]["rho"] for h in HORIZONS}}}


def redundancy(series_store, eligible):
    changes = {k: pd.Series(series_store[k]).dropna().astype(float).sort_index().diff(5).dropna() for k in sorted(eligible)}
    pairs, graph = [], defaultdict(set); keys = sorted(changes)
    for i, a in enumerate(keys):
        if len(changes[a]) < 120: continue
        for b in keys[i+1:]:
            if len(changes[b]) < 120: continue
            z = pd.concat([changes[a].rename("a"), changes[b].rename("b")], axis=1).dropna()
            if len(z) < 120: continue
            r = z["a"].rank().corr(z["b"].rank())
            if pd.isna(r) or abs(r) < REDUNDANCY_CUT: continue
            rr = round(float(r), 4); pairs.append({"a": a, "b": b, "rho_5d_change": rr, "n": int(len(z))}); graph[a].add(b); graph[b].add(a)
    pairs.sort(key=lambda x: abs(x["rho_5d_change"]), reverse=True)
    seen, clusters = set(), []
    for k in sorted(graph):
        if k in seen: continue
        q, comp = deque([k]), []
        while q:
            x = q.popleft()
            if x in seen: continue
            seen.add(x); comp.append(x); q.extend(graph[x] - seen)
        if len(comp) > 1: clusters.append(sorted(comp))
    clusters.sort(key=lambda x: (-len(x), x[0])); return pairs, clusters


def main():
    ns, cap = ar.run_update_and_capture()
    if not cap: raise RuntimeError("ablation capture missing")
    series_store, mk, ordered, model = cap["series_store"], cap["mk"], cap["ordered"], ns["MODEL"]
    if "SPY" not in mk: raise RuntimeError("SPY history unavailable")
    market = build_market_frame(mk["SPY"]["Close"]); metas = model_meta(model, ordered)
    results, excluded = [], []
    for key in sorted(series_store):
        s = pd.Series(series_store[key]).dropna(); overlap = market.index.intersection(s.index)
        if len(overlap) < MIN_OBS:
            excluded.append({"id": key, "reason": "insufficient_overlap", "overlap": int(len(overlap))}); continue
        st = indicator_stats(key, s, metas.get(key, {"impact_polarity": 0}), market)
        if st is None: excluded.append({"id": key, "reason": "unusable"})
        else: results.append(st)
    eligible = {x["id"] for x in results}; pairs, clusters = redundancy(series_store, eligible)
    directional = [x for x in results if float(x.get("impact_polarity") or 0) != 0]
    def getrho(x, sec): return (x.get(sec) or {}).get("10", {}).get("rho")
    top_full = sorted([x for x in directional if getrho(x,"full_ic") is not None], key=lambda x:getrho(x,"full_ic"), reverse=True)
    top_oos = sorted([x for x in directional if getrho(x,"oos_2022_present_ic") is not None], key=lambda x:getrho(x,"oos_2022_present_ic"), reverse=True)
    stable = sorted([x for x in directional if x["stability"]["years_with_ic"]>=3 and x["stability"]["positive_year_share"] is not None], key=lambda x:(x["stability"]["positive_year_share"], x["stability"]["median_yearly_ic_10d"] or -9), reverse=True)
    role_counts, bucket_counts = defaultdict(int), defaultdict(int)
    for x in results: role_counts[x.get("model_role") or "unknown"] += 1; bucket_counts[x.get("model_bucket") or "none"] += 1
    payload = {"schema":"INDICATOR-VALIDATION-V1","generated_at":datetime.now(timezone.utc).isoformat(),"research_only":True,"diagnostic_only":True,"production_effect":"none","weights_changed":False,"thresholds_changed":False,"study_spec":SPEC,"coverage":{"market_start":str(market.index.min().date()),"market_end":str(market.index.max().date()),"captured_series_count":len(series_store),"eligible_indicator_count":len(results),"excluded_count":len(excluded)},"definitions":{"min_overlap":MIN_OBS,"min_year_obs":MIN_YEAR_OBS,"horizons_days":list(HORIZONS),"oos_start":str(OOS_START.date()),"redundancy_abs_spearman_5d_change_cut":REDUNDANCY_CUT},"role_counts":dict(role_counts),"bucket_counts":dict(bucket_counts),"indicators":results,"excluded":excluded,"redundancy":{"pairs":pairs,"clusters":clusters},"decision":{"may_change_production":False,"may_reweight_model":False,"may_remove_indicator":False,"requires_separate_preregistration_for_any_candidate":True},"warnings":["Reconstructed history is not fully point-in-time.","Macro current-history data may contain revisions and publication-date mismatch.","Rankings are discovery diagnostics and are not promotion tests.","Best horizon is descriptive only and must not be optimized into production from this output."]}
    OUT.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding="utf-8")
    def compact(x, sec): return {"id":x["id"],"name":x.get("name"),"role":x.get("model_role"),"bucket":x.get("model_bucket"),"rho10":x[sec]["10"]["rho"],"n10":x[sec]["10"]["n"],"positive_year_share":x["stability"]["positive_year_share"],"median_year_ic10":x["stability"]["median_yearly_ic_10d"]}
    summary={"schema":"INDICATOR-VALIDATION-V1-SUMMARY","generated_at":payload["generated_at"],"research_only":True,"eligible_indicator_count":len(results),"top_full_10d_directional_ic":[compact(x,"full_ic") for x in top_full[:15]],"bottom_full_10d_directional_ic":[compact(x,"full_ic") for x in list(reversed(top_full[-15:]))],"top_oos_2022_present_10d_directional_ic":[compact(x,"oos_2022_present_ic") for x in top_oos[:15]],"most_year_stable":[compact(x,"full_ic") for x in stable[:15]],"redundancy_pair_count":len(pairs),"redundancy_cluster_count":len(clusters),"largest_redundancy_clusters":clusters[:10],"role_counts":dict(role_counts),"decision":payload["decision"]}
    SUMMARY.write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps({"eligible":len(results),"excluded":len(excluded),"redundancy_pairs":len(pairs),"clusters":len(clusters),"top_full10":[(x["id"],x["full_ic"]["10"]["rho"]) for x in top_full[:10]],"top_oos10":[(x["id"],x["oos_2022_present_ic"]["10"]["rho"]) for x in top_oos[:10]]},ensure_ascii=False))

if __name__ == "__main__": main()
