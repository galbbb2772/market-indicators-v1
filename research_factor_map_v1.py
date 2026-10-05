from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from pathlib import Path
from statistics import median

import numpy as np
import pandas as pd

import ablation_runner as abl

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "docs" / "data" / "factor_map_v1.json"
SUMMARY = ROOT / "docs" / "data" / "factor_map_v1_summary.json"
SPEC = "research/factor_map_v1/STUDY_SPEC.md"
MIN_OBS = 252
MIN_UNIQUE = 10
MIN_PAIR = 120
REDUNDANCY_CUTOFF = 0.85
RIDGE_ALPHA = 10.0

# Frozen semantic placements. Fallback rules below are only for newly added indicators.
FAMILY_MEMBERS = {
    "valuation_price_structure": {
        "valuation_cycle", "valuation_percentile", "valuation_speed", "market_overextension",
        "market_move_speed", "market_support", "money_making_effect",
    },
    "breadth_participation": {
        "breadth_concentration", "concentration", "retail_participation",
        "retail_holdings_concentration", "sme_survival_growth",
    },
    "fear_volatility": {
        "market_fear", "largecap_panic", "retail_panic", "institutional_panic", "options_anomaly",
        "systemic_risk", "risk_60d", "tech100_volatility", "vol_60d_change",
        "mag7_volatility", "ai7_volatility", "mega_liquidity_blowup",
        "sector_it_vol", "sector_comm_vol", "sector_cons_disc_vol", "sector_cons_staples_vol",
        "sector_fin_vol", "sector_health_vol", "sector_industrial_vol", "sector_energy_vol",
        "sector_materials_vol", "sector_utilities_vol", "sector_realestate_vol",
    },
    "liquidity_credit": {
        "high_yield", "liquidity_risk", "leverage_liquidity", "market_liquidity",
        "credit_cycle", "us_loans_speed", "us_loans_total", "usd_credit",
    },
    "rates_policy": {
        "treasury_rate_regime", "yield_curve", "global_cb_rhythm", "global_cb_cycle_entry",
        "rate_cycle_sensitivity",
    },
    "sentiment_event": {
        "market_optimism", "market_pessimism", "market_bias", "geopolitical_risk",
        "geo_news_impact", "geo_lag_reaction", "market_topic_heat",
    },
    "macro_cycle_labor_fiscal": {
        "business_cycle", "inventory_cycle", "employment", "fiscal_deficit",
    },
    "crowding_mega": {
        "quant_crowding", "mag7_volume", "ai7_volume", "retail_cash_reserve",
        "ib_holdings_concentration",
    },
    "cross_asset_commodity": {
        "cross_asset_correlation", "gold", "oil",
    },
    "volume_flow": {
        "market_volume", "volume_speed",
    },
}


def finite(v):
    try:
        x = float(v)
        return x if math.isfinite(x) else None
    except Exception:
        return None


def spearman(a: pd.Series, b: pd.Series):
    z = pd.concat([a.rename("a"), b.rename("b")], axis=1).dropna()
    if len(z) < 3 or z["a"].nunique() < 2 or z["b"].nunique() < 2:
        return None, len(z)
    r = z["a"].rank(method="average").corr(z["b"].rank(method="average"))
    return (None if pd.isna(r) else float(r)), len(z)


def forward_frame(close: pd.Series):
    x = pd.DataFrame({"close": close.astype(float).sort_index()})
    for h in (5, 10, 20):
        x[f"fwd_{h}d"] = (x["close"].shift(-h) / x["close"] - 1.0) * 100.0
    ret = x["close"].pct_change()
    x["rv20"] = ret.rolling(20).std() * math.sqrt(252) * 100.0
    x["ma200"] = x["close"].rolling(200).mean()
    x["above200"] = x["close"] >= x["ma200"]
    x["below200"] = x["close"] < x["ma200"]
    x["high_vol"] = x["rv20"] >= 20.0
    x["low_vol"] = x["rv20"] < 20.0
    return x


def assign_family(ind_id: str, meta: dict):
    for fam, ids in FAMILY_MEMBERS.items():
        if ind_id in ids:
            return fam, "frozen_id_map"
    cat = str(meta.get("category") or "").lower()
    k = ind_id.lower()
    if any(t in k for t in ("valuation", "overextension", "market_support", "money_making")):
        return "valuation_price_structure", "fallback_keyword"
    if any(t in k for t in ("breadth", "concentration", "participation", "sme_")):
        return "breadth_participation", "fallback_keyword"
    if any(t in k for t in ("panic", "fear", "volatility", "risk_60d", "systemic", "options")):
        return "fear_volatility", "fallback_keyword"
    if any(t in k for t in ("liquidity", "credit", "high_yield", "loans")):
        return "liquidity_credit", "fallback_keyword"
    if any(t in k for t in ("yield", "treasury", "rate_", "cb_")):
        return "rates_policy", "fallback_keyword"
    if any(t in k for t in ("optim", "pessim", "bias", "geo_", "geopolit", "topic")) or "情绪" in cat:
        return "sentiment_event", "fallback_keyword"
    if any(t in k for t in ("business", "inventory", "employment", "fiscal")):
        return "macro_cycle_labor_fiscal", "fallback_keyword"
    if any(t in k for t in ("mag7", "ai7", "crowding", "holdings")):
        return "crowding_mega", "fallback_keyword"
    if any(t in k for t in ("cross_asset", "gold", "oil")):
        return "cross_asset_commodity", "fallback_keyword"
    if any(t in k for t in ("volume", "flow")):
        return "volume_flow", "fallback_keyword"
    return "other_structural", "fallback_other"


def connected_components(ids: list[str], series: dict[str, pd.Series], index: pd.Index):
    ids = sorted(ids)
    adj = {k: set() for k in ids}
    pairs = []
    for i, a in enumerate(ids):
        da = series[a].reindex(index).ffill().diff(5)
        for b in ids[i + 1 :]:
            db = series[b].reindex(index).ffill().diff(5)
            r, n = spearman(da, db)
            if r is None or n < MIN_PAIR:
                continue
            if abs(r) >= REDUNDANCY_CUTOFF:
                adj[a].add(b)
                adj[b].add(a)
                pairs.append({"a": a, "b": b, "rho": round(r, 4), "abs_rho": round(abs(r), 4), "n": n})
    seen = set()
    comps = []
    for root in ids:
        if root in seen:
            continue
        stack = [root]
        comp = []
        seen.add(root)
        while stack:
            x = stack.pop()
            comp.append(x)
            for y in sorted(adj[x]):
                if y not in seen:
                    seen.add(y)
                    stack.append(y)
        comps.append(sorted(comp))
    comps.sort(key=lambda c: (-len(c), c[0]))
    pairs.sort(key=lambda x: x["abs_rho"], reverse=True)
    return comps, pairs


def quintile(score: pd.Series, target: pd.Series):
    z = pd.concat([score.rename("s"), target.rename("y")], axis=1).dropna()
    if len(z) < 40 or z["s"].nunique() < 5:
        return {"n": len(z)}
    p = z["s"].rank(pct=True)
    q1 = z.loc[p <= 0.2, "y"]
    q5 = z.loc[p > 0.8, "y"]
    return {
        "n": len(z), "q1_n": len(q1), "q5_n": len(q5),
        "q1_mean_pct": round(float(q1.mean()), 4),
        "q5_mean_pct": round(float(q5.mean()), 4),
        "q5_minus_q1_pp": round(float(q5.mean() - q1.mean()), 4),
    }


def overlap_phase(score: pd.Series, target: pd.Series, h=10):
    z = pd.concat([score.rename("s"), target.rename("y")], axis=1).dropna().reset_index(drop=True)
    full, _ = spearman(z["s"], z["y"])
    vals = []
    for off in range(h):
        w = z.iloc[off::h]
        r, n = spearman(w["s"], w["y"])
        if r is not None:
            vals.append({"offset": off, "n": n, "rho": round(r, 4)})
    xs = [v["rho"] for v in vals]
    same = None
    if xs and full is not None and full != 0:
        same = 100 * sum((x > 0) == (full > 0) for x in xs) / len(xs)
    return {
        "full_rho": None if full is None else round(full, 4),
        "median_rho": None if not xs else round(float(median(xs)), 4),
        "min_rho": None if not xs else round(float(min(xs)), 4),
        "max_rho": None if not xs else round(float(max(xs)), 4),
        "same_sign_pct": None if same is None else round(same, 2),
        "phases": vals,
    }


def rolling_ic(score: pd.Series, target: pd.Series, window=252, step=21):
    z = pd.concat([score.rename("s"), target.rename("y")], axis=1).dropna()
    vals = []
    for end in range(window - 1, len(z), step):
        w = z.iloc[end - window + 1 : end + 1]
        r, n = spearman(w["s"], w["y"])
        if r is not None:
            vals.append({"end": str(w.index[-1].date()), "n": n, "rho": round(r, 4)})
    xs = [x["rho"] for x in vals]
    return {
        "windows": len(xs),
        "median_rho": None if not xs else round(float(median(xs)), 4),
        "positive_pct": None if not xs else round(100 * sum(x > 0 for x in xs) / len(xs), 2),
        "min_rho": None if not xs else round(float(min(xs)), 4),
        "max_rho": None if not xs else round(float(max(xs)), 4),
        "points": vals,
    }


def family_metrics(score: pd.Series, frame: pd.DataFrame):
    out = {"horizons": {}}
    for h in (5, 10, 20):
        y = frame[f"fwd_{h}d"]
        r, n = spearman(score, y)
        out["horizons"][f"{h}d"] = {
            "ic": {"rho": None if r is None else round(r, 4), "n": n},
            "quintile": quintile(score, y),
        }
    y = frame["fwd_10d"]
    eras = {
        "2017_2019": ("2017-01-01", "2019-12-31"),
        "2020_2021": ("2020-01-01", "2021-12-31"),
        "2022_present": ("2022-01-01", "2100-01-01"),
    }
    out["era_ic_10d"] = {}
    for k, (a, b) in eras.items():
        idx = score.index[(score.index >= pd.Timestamp(a)) & (score.index <= pd.Timestamp(b))]
        r, n = spearman(score.reindex(idx), y.reindex(idx))
        out["era_ic_10d"][k] = {"rho": None if r is None else round(r, 4), "n": n}
    out["regime_ic_10d"] = {}
    for k in ("above200", "below200", "high_vol", "low_vol"):
        idx = frame.index[frame[k].fillna(False)]
        r, n = spearman(score.reindex(idx), y.reindex(idx))
        out["regime_ic_10d"][k] = {"rho": None if r is None else round(r, 4), "n": n}
    out["rolling_ic_10d"] = rolling_ic(score, y)
    out["overlap_phase_10d"] = overlap_phase(score, y, 10)
    return out


def univariate_loyo(score: pd.Series, target: pd.Series):
    z = pd.concat([score.rename("x"), target.rename("y")], axis=1).dropna()
    z = z[z.index.year >= 2017]
    preds, base, actual = [], [], []
    folds = []
    for yr in sorted(set(z.index.year)):
        te = z[z.index.year == yr]
        tr = z[z.index.year != yr]
        if len(te) < 20 or len(tr) < 252:
            continue
        mu = float(tr["x"].mean())
        sd = float(tr["x"].std()) or 1.0
        xtr = (tr["x"].to_numpy(float) - mu) / sd
        xte = (te["x"].to_numpy(float) - mu) / sd
        ytr = tr["y"].to_numpy(float)
        ymean = float(np.mean(ytr))
        denom = float(np.dot(xtr, xtr))
        beta = 0.0 if denom <= 1e-12 else float(np.dot(xtr, ytr - ymean) / denom)
        yp = ymean + beta * xte
        yb = np.repeat(ymean, len(te))
        ya = te["y"].to_numpy(float)
        mse = float(np.mean((yp - ya) ** 2))
        bmse = float(np.mean((yb - ya) ** 2))
        folds.append({"year": int(yr), "n": len(te), "mse": round(mse, 6), "baseline_mse": round(bmse, 6)})
        preds.extend(yp.tolist()); base.extend(yb.tolist()); actual.extend(ya.tolist())
    if not actual:
        return {"folds": []}
    mse = float(np.mean((np.asarray(preds) - np.asarray(actual)) ** 2))
    bmse = float(np.mean((np.asarray(base) - np.asarray(actual)) ** 2))
    imp = 100 * (bmse - mse) / bmse if bmse > 0 else None
    return {"n": len(actual), "mse": round(mse, 6), "baseline_mse": round(bmse, 6), "mse_improvement_pct": None if imp is None else round(imp, 3), "folds": folds}


def residual_corr(factors: pd.DataFrame, target: pd.Series, family: str, start=None):
    z = factors.copy()
    z["target"] = target
    if start is not None:
        z = z[z.index >= pd.Timestamp(start)]
    z = z.dropna()
    if family not in z or len(z) < 120:
        return {"n": len(z), "rho": None}
    cols = [c for c in factors.columns if c != family]
    ranks = z[[family] + cols + ["target"]].rank(method="average")
    if cols:
        X = ranks[cols].to_numpy(float)
        X = np.column_stack([np.ones(len(X)), X])
        xf = ranks[family].to_numpy(float)
        yt = ranks["target"].to_numpy(float)
        bx = np.linalg.lstsq(X, xf, rcond=None)[0]
        by = np.linalg.lstsq(X, yt, rcond=None)[0]
        rx = xf - X @ bx
        ry = yt - X @ by
    else:
        rx = ranks[family].to_numpy(float)
        ry = ranks["target"].to_numpy(float)
    r = float(np.corrcoef(rx, ry)[0, 1]) if np.std(rx) > 0 and np.std(ry) > 0 else np.nan
    return {"n": len(z), "rho": None if not np.isfinite(r) else round(r, 4)}


def ridge_fit_predict(Xtr, ytr, Xte, alpha=RIDGE_ALPHA):
    med = np.nanmedian(Xtr, axis=0)
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


def multivariate_loyo_ablation(factors: pd.DataFrame, target: pd.Series):
    z = factors.copy()
    z["target"] = target
    z = z[z.index.year >= 2017]
    fams = list(factors.columns)
    y_all, full_all = [], []
    without_all = {f: [] for f in fams}
    folds = []
    for yr in sorted(set(z.index.year)):
        te = z[z.index.year == yr]
        tr = z[z.index.year != yr]
        te = te[te["target"].notna()]
        tr = tr[tr["target"].notna()]
        if len(te) < 20 or len(tr) < 252:
            continue
        Xtr = tr[fams].to_numpy(float)
        Xte = te[fams].to_numpy(float)
        ytr = tr["target"].to_numpy(float)
        yte = te["target"].to_numpy(float)
        full = ridge_fit_predict(Xtr, ytr, Xte)
        y_all.extend(yte.tolist()); full_all.extend(full.tolist())
        row = {"year": int(yr), "n": len(te)}
        for j, f in enumerate(fams):
            keep = [k for k in range(len(fams)) if k != j]
            pred = ridge_fit_predict(Xtr[:, keep], ytr, Xte[:, keep])
            without_all[f].extend(pred.tolist())
        folds.append(row)
    if not y_all:
        return {"families": {}, "folds": []}
    y = np.asarray(y_all)
    full = np.asarray(full_all)
    full_mse = float(np.mean((full - y) ** 2))
    famout = {}
    for f in fams:
        p = np.asarray(without_all[f])
        mse = float(np.mean((p - y) ** 2))
        delta = mse - full_mse
        famout[f] = {
            "without_family_mse": round(mse, 6),
            "delta_mse_without_minus_full": round(delta, 6),
            "delta_pct_of_full_mse": round(100 * delta / full_mse, 3) if full_mse > 0 else None,
            "helps_full_model_if_positive": bool(delta > 0),
        }
    return {"n": len(y), "full_mse": round(full_mse, 6), "families": famout, "folds": folds, "ridge_alpha": RIDGE_ALPHA}


def main():
    ns, cap = abl.run_update_and_capture()
    if not cap:
        raise RuntimeError("No ablation capture generated")
    series_store = cap["series_store"]
    mk = cap["mk"]
    ordered = cap["ordered"]
    if "SPY" not in mk:
        raise RuntimeError("SPY missing")
    close = mk["SPY"]["Close"].dropna().sort_index()
    frame = forward_frame(close)
    meta = {x["id"]: x for x in ordered}

    eligible = {}
    assignment = {}
    excluded = {}
    for k, s in series_store.items():
        m = meta.get(k)
        if not m:
            excluded[k] = "missing_metadata"; continue
        pol = int(m.get("impact_polarity", 0) or 0)
        if pol not in (-1, 1):
            excluded[k] = "non_directional_polarity"; continue
        ss = pd.Series(s).dropna().sort_index().astype(float)
        aligned = ss.reindex(frame.index).ffill().dropna()
        if len(aligned) < MIN_OBS:
            excluded[k] = f"aligned<{MIN_OBS}"; continue
        if ss.nunique() < MIN_UNIQUE:
            excluded[k] = f"distinct<{MIN_UNIQUE}"; continue
        supportive = ss if pol == 1 else 100.0 - ss
        eligible[k] = supportive
        fam, method = assign_family(k, m)
        assignment[k] = {"family": fam, "method": method, "polarity": pol, "name": m.get("name"), "role": m.get("model_v2_role")}

    by_family = {}
    for k, info in assignment.items():
        by_family.setdefault(info["family"], []).append(k)

    family_scores = {}
    family_payload = {}
    all_redundancy_pairs = []
    for fam in sorted(by_family):
        ids = sorted(by_family[fam])
        comps, pairs = connected_components(ids, eligible, frame.index)
        all_redundancy_pairs.extend([{**p, "family": fam} for p in pairs])
        component_scores = []
        comp_payload = []
        for ci, comp in enumerate(comps, 1):
            cols = [eligible[k].reindex(frame.index).ffill().rename(k) for k in comp]
            cscore = pd.concat(cols, axis=1).mean(axis=1, skipna=True)
            component_scores.append(cscore.rename(f"c{ci}"))
            comp_payload.append({"component": ci, "members": comp, "size": len(comp)})
        fscore = pd.concat(component_scores, axis=1).mean(axis=1, skipna=True).dropna()
        family_scores[fam] = fscore
        met = family_metrics(fscore, frame)
        met["univariate_loyo_10d"] = univariate_loyo(fscore, frame["fwd_10d"])
        full10 = met["horizons"]["10d"]["ic"]["rho"]
        recent10 = met["era_ic_10d"]["2022_present"]["rho"]
        if full10 is not None and recent10 is not None and full10 >= 0.03 and recent10 >= 0:
            style = "continuation"
        elif full10 is not None and recent10 is not None and full10 <= -0.03 and recent10 <= 0:
            style = "mean_reversion"
        else:
            style = "mixed_or_regime_dependent"
        family_payload[fam] = {
            "member_count": len(ids), "members": ids,
            "redundancy_component_count": len(comps), "redundancy_components": comp_payload,
            "redundancy_pairs": pairs, "signal_style_10d": style,
            "metrics": met,
        }

    factor_df = pd.DataFrame({k: v.reindex(frame.index).ffill() for k, v in family_scores.items()}, index=frame.index)
    partial = {}
    for fam in factor_df.columns:
        partial[fam] = {
            "full": residual_corr(factor_df, frame["fwd_10d"], fam),
            "2022_present": residual_corr(factor_df, frame["fwd_10d"], fam, "2022-01-01"),
        }
        family_payload[fam]["partial_spearman_10d"] = partial[fam]

    corr = factor_df.diff(5).corr(method="spearman")
    corr_rows = []
    for i, a in enumerate(corr.columns):
        for b in corr.columns[i + 1 :]:
            v = finite(corr.loc[a, b])
            if v is not None:
                corr_rows.append({"a": a, "b": b, "rho_5d_change": round(v, 4), "abs_rho": round(abs(v), 4)})
    corr_rows.sort(key=lambda x: x["abs_rho"], reverse=True)

    mv = multivariate_loyo_ablation(factor_df, frame["fwd_10d"])
    for fam, d in mv.get("families", {}).items():
        family_payload[fam]["multivariate_loyo_ablation_10d"] = d

    summary_rows = []
    for fam, d in family_payload.items():
        m = d["metrics"]
        summary_rows.append({
            "family": fam,
            "members": d["member_count"],
            "components": d["redundancy_component_count"],
            "style": d["signal_style_10d"],
            "ic5": m["horizons"]["5d"]["ic"]["rho"],
            "ic10": m["horizons"]["10d"]["ic"]["rho"],
            "ic20": m["horizons"]["20d"]["ic"]["rho"],
            "ic10_2022_present": m["era_ic_10d"]["2022_present"]["rho"],
            "partial_ic10": d["partial_spearman_10d"]["full"]["rho"],
            "partial_ic10_2022_present": d["partial_spearman_10d"]["2022_present"]["rho"],
            "loyo_univariate_improvement_pct": m["univariate_loyo_10d"].get("mse_improvement_pct"),
            "loyo_ablation_delta_pct": d.get("multivariate_loyo_ablation_10d", {}).get("delta_pct_of_full_mse"),
            "rolling_positive_pct10": m["rolling_ic_10d"].get("positive_pct"),
            "phase_same_sign_pct10": m["overlap_phase_10d"].get("same_sign_pct"),
        })
    summary_rows.sort(key=lambda x: abs(x["partial_ic10"] or 0), reverse=True)

    payload = {
        "schema": "MARKET-FACTOR-MAP-V1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "research_only": True,
        "diagnostic_only": True,
        "production_effect": "none",
        "weights_changed": False,
        "thresholds_changed": False,
        "study_spec": SPEC,
        "coverage": {
            "spy_start": str(frame.index.min().date()), "spy_end": str(frame.index.max().date()),
            "spy_observations": len(frame), "captured_series_count": len(series_store),
            "eligible_directional_indicator_count": len(eligible), "family_count": len(family_scores),
            "excluded_count": len(excluded),
        },
        "method": {
            "orientation": "supportive-state; +1=score, -1=100-score",
            "within_family_redundancy": f"connected components of abs Spearman 5d-change >= {REDUNDANCY_CUTOFF}",
            "component_weighting": "equal weight inside component, then equal weight across components",
            "ridge_alpha": RIDGE_ALPHA,
        },
        "assignment": assignment,
        "excluded": excluded,
        "families": family_payload,
        "family_intercorrelation_5d_change": corr_rows,
        "multivariate_loyo_10d": mv,
        "summary_rows": summary_rows,
        "guardrails": {
            "may_change_production": False,
            "may_reweight_model": False,
            "may_remove_indicator": False,
            "note": "Historical reconstruction is diagnostic; any production change requires a separate preregistered OOS decision.",
        },
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    compact = {
        "schema": "MARKET-FACTOR-MAP-V1-SUMMARY",
        "generated_at": payload["generated_at"],
        "research_only": True,
        "coverage": payload["coverage"],
        "families": summary_rows,
        "top_by_abs_partial_ic10": summary_rows[:10],
        "top_family_intercorrelations": corr_rows[:20],
        "multivariate_full_mse": mv.get("full_mse"),
        "guardrails": payload["guardrails"],
    }
    SUMMARY.write_text(json.dumps(compact, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({
        "coverage": payload["coverage"],
        "families": [[x["family"], x["ic10"], x["ic10_2022_present"], x["partial_ic10"], x["loyo_ablation_delta_pct"]] for x in summary_rows]
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
