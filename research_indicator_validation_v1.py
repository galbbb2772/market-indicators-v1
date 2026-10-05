from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean, median

import numpy as np
import pandas as pd

import ablation_runner as abl

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "docs" / "data" / "indicator_validation_v1.json"
SPEC = "research/indicator_validation_v1/STUDY_SPEC.md"
HORIZONS = (1, 5, 10, 20, 60)
PRIMARY_HORIZONS = (5, 10, 20)
MIN_OBS = 252
MIN_UNIQUE = 10
MIN_PAIR = 120
ROLL_WINDOW = 252
ROLL_STEP = 21


def finite(x):
    try:
        v = float(x)
        return v if math.isfinite(v) else None
    except (TypeError, ValueError):
        return None


def qtile(vals, p):
    a = sorted(v for v in (finite(x) for x in vals) if v is not None)
    if not a:
        return None
    z = (len(a) - 1) * p
    i = int(z)
    j = min(i + 1, len(a) - 1)
    f = z - i
    return a[i] + (a[j] - a[i]) * f


def rho(a: pd.Series, b: pd.Series):
    z = pd.concat([a, b], axis=1).dropna()
    if len(z) < 3 or z.iloc[:, 0].nunique() < 2 or z.iloc[:, 1].nunique() < 2:
        return None, len(z)
    r = z.iloc[:, 0].rank(method="average").corr(z.iloc[:, 1].rank(method="average"))
    return (None if pd.isna(r) else float(r)), len(z)


def summarize_values(vals):
    x = [finite(v) for v in vals]
    x = [v for v in x if v is not None]
    if not x:
        return {"n": 0}
    return {
        "n": len(x),
        "mean": round(float(mean(x)), 4),
        "median": round(float(median(x)), 4),
        "p10": round(float(qtile(x, 0.10)), 4),
        "p90": round(float(qtile(x, 0.90)), 4),
        "min": round(float(min(x)), 4),
        "max": round(float(max(x)), 4),
        "positive_pct": round(100.0 * sum(v > 0 for v in x) / len(x), 2),
    }


def forward_frame(close: pd.Series) -> pd.DataFrame:
    x = pd.DataFrame({"close": close.astype(float).sort_index()})
    for h in HORIZONS:
        x[f"fwd_{h}d"] = (x["close"].shift(-h) / x["close"] - 1.0) * 100.0
    ret = x["close"].pct_change()
    x["rv20"] = ret.rolling(20).std() * math.sqrt(252) * 100.0
    x["ma200"] = x["close"].rolling(200).mean()
    x["price_regime"] = np.where(x["ma200"].isna(), None, np.where(x["close"] >= x["ma200"], "above200", "below200"))
    x["vol_regime"] = np.where(x["rv20"].isna(), None, np.where(x["rv20"] >= 20.0, "high_ge20", "low_lt20"))
    return x


def phase_robustness(score: pd.Series, target: pd.Series, h: int, full_rho):
    z = pd.concat([score.rename("score"), target.rename("target")], axis=1).dropna().reset_index(drop=False)
    phase = []
    if len(z) < 3:
        return {"valid_phases": 0}
    for off in range(h):
        s = z.iloc[off::h]
        r, n = rho(s["score"], s["target"])
        if r is not None:
            phase.append({"offset": off, "n": n, "rho": round(r, 4)})
    vals = [p["rho"] for p in phase]
    same = None
    if vals and full_rho is not None and full_rho != 0:
        same = 100.0 * sum((v > 0) == (full_rho > 0) for v in vals) / len(vals)
    return {
        "valid_phases": len(vals),
        "median_rho": None if not vals else round(float(median(vals)), 4),
        "min_rho": None if not vals else round(float(min(vals)), 4),
        "max_rho": None if not vals else round(float(max(vals)), 4),
        "same_sign_as_full_pct": None if same is None else round(same, 2),
        "phases": phase,
    }


def quintile_stats(score: pd.Series, target: pd.Series):
    z = pd.concat([score.rename("score"), target.rename("target")], axis=1).dropna()
    if len(z) < 20 or z["score"].nunique() < 5:
        return {"n": len(z)}
    pct = z["score"].rank(method="average", pct=True)
    q1 = z.loc[pct <= 0.20, "target"]
    q5 = z.loc[pct > 0.80, "target"]
    if q1.empty or q5.empty:
        return {"n": len(z)}
    return {
        "n": len(z),
        "q1_n": int(len(q1)),
        "q5_n": int(len(q5)),
        "q1_mean_pct": round(float(q1.mean()), 4),
        "q5_mean_pct": round(float(q5.mean()), 4),
        "q5_minus_q1_pp": round(float(q5.mean() - q1.mean()), 4),
        "q1_positive_pct": round(float((q1 > 0).mean() * 100.0), 2),
        "q5_positive_pct": round(float((q5 > 0).mean() * 100.0), 2),
    }


def split_ic(score: pd.Series, target: pd.Series, mask: pd.Series):
    idx = mask.index[mask.fillna(False)]
    r, n = rho(score.reindex(idx), target.reindex(idx))
    return {"n": n, "rho": None if r is None else round(r, 4)}


def era_ics(score: pd.Series, target: pd.Series):
    eras = {
        "2017_2019": (pd.Timestamp("2017-01-01"), pd.Timestamp("2019-12-31")),
        "2020_2021": (pd.Timestamp("2020-01-01"), pd.Timestamp("2021-12-31")),
        "2022_present": (pd.Timestamp("2022-01-01"), pd.Timestamp("2100-01-01")),
    }
    out = {}
    for k, (a, b) in eras.items():
        idx = score.index[(score.index >= a) & (score.index <= b)]
        r, n = rho(score.reindex(idx), target.reindex(idx))
        out[k] = {"n": n, "rho": None if r is None else round(r, 4)}
    return out


def rolling_ic(score: pd.Series, target: pd.Series):
    z = pd.concat([score.rename("score"), target.rename("target")], axis=1).dropna()
    vals = []
    if len(z) < ROLL_WINDOW:
        return {"windows": 0}
    for end in range(ROLL_WINDOW - 1, len(z), ROLL_STEP):
        w = z.iloc[end - ROLL_WINDOW + 1 : end + 1]
        r, n = rho(w["score"], w["target"])
        if r is None:
            continue
        vals.append({"end": str(w.index[-1].date()), "n": n, "rho": round(r, 4)})
    xs = [v["rho"] for v in vals]
    return {
        "windows": len(xs),
        "median_rho": None if not xs else round(float(median(xs)), 4),
        "p10_rho": None if not xs else round(float(qtile(xs, 0.10)), 4),
        "p90_rho": None if not xs else round(float(qtile(xs, 0.90)), 4),
        "min_rho": None if not xs else round(float(min(xs)), 4),
        "max_rho": None if not xs else round(float(max(xs)), 4),
        "positive_pct": None if not xs else round(100.0 * sum(x > 0 for x in xs) / len(xs), 2),
        "points": vals,
    }


def validate_indicator(ind_id, ser, meta, frame):
    score = pd.Series(ser).sort_index().reindex(frame.index).ffill()
    score = score.where(score.notna())
    valid_n = int(pd.concat([score, frame["close"]], axis=1).dropna().shape[0])
    polarity = int(meta.get("impact_polarity", 0) or 0)
    supportive = (50.0 + polarity * (score - 50.0)) if polarity in (-1, 1) else None
    out = {
        "id": ind_id,
        "name": meta.get("name"),
        "category": meta.get("category"),
        "type": meta.get("type"),
        "model_v2_role": meta.get("model_v2_role"),
        "model_v2_bucket": meta.get("model_v2_bucket"),
        "impact_polarity": polarity,
        "source_start": str(pd.Series(ser).dropna().index.min().date()),
        "source_end": str(pd.Series(ser).dropna().index.max().date()),
        "aligned_observations": valid_n,
        "distinct_scores": int(pd.Series(ser).dropna().nunique()),
        "horizons": {},
        "rolling_ic": {},
    }
    for h in HORIZONS:
        target = frame[f"fwd_{h}d"]
        rr, rn = rho(score, target)
        hv = {
            "raw_ic": {"n": rn, "rho": None if rr is None else round(rr, 4)},
            "raw_quintiles": quintile_stats(score, target),
            "raw_overlap_phase": phase_robustness(score, target, h, rr),
            "raw_era_ic": era_ics(score, target),
            "raw_regime_ic": {
                "above200": split_ic(score, target, frame["price_regime"].eq("above200")),
                "below200": split_ic(score, target, frame["price_regime"].eq("below200")),
                "high_ge20": split_ic(score, target, frame["vol_regime"].eq("high_ge20")),
                "low_lt20": split_ic(score, target, frame["vol_regime"].eq("low_lt20")),
            },
        }
        if supportive is not None:
            sr, sn = rho(supportive, target)
            hv["supportive_ic"] = {"n": sn, "rho": None if sr is None else round(sr, 4)}
            hv["supportive_overlap_phase"] = phase_robustness(supportive, target, h, sr)
            hv["supportive_era_ic"] = era_ics(supportive, target)
            hv["supportive_regime_ic"] = {
                "above200": split_ic(supportive, target, frame["price_regime"].eq("above200")),
                "below200": split_ic(supportive, target, frame["price_regime"].eq("below200")),
                "high_ge20": split_ic(supportive, target, frame["vol_regime"].eq("high_ge20")),
                "low_lt20": split_ic(supportive, target, frame["vol_regime"].eq("low_lt20")),
            }
        out["horizons"][f"{h}d"] = hv
    for h in (10, 20):
        out["rolling_ic"][f"raw_{h}d"] = rolling_ic(score, frame[f"fwd_{h}d"])
        if supportive is not None:
            out["rolling_ic"][f"supportive_{h}d"] = rolling_ic(supportive, frame[f"fwd_{h}d"])
    # Compact stability flags. These are descriptive and do not alter model membership.
    primary = []
    for h in PRIMARY_HORIZONS:
        d = out["horizons"][f"{h}d"]
        p = d["raw_overlap_phase"].get("same_sign_as_full_pct")
        m = d["raw_overlap_phase"].get("median_rho")
        primary.append({"h": h, "phase_same_sign_pct": p, "phase_median_rho": m})
    out["primary_phase_summary"] = primary
    return out


def redundancy(series_map, frame_index):
    ids = sorted(series_map)
    changes = {}
    for k in ids:
        s = pd.Series(series_map[k]).sort_index().reindex(frame_index).ffill().diff(5)
        changes[k] = s
    pairs = []
    max_peer = {k: {"peer": None, "abs_rho": None, "rho": None, "n": 0} for k in ids}
    for i, a in enumerate(ids):
        for b in ids[i + 1 :]:
            r, n = rho(changes[a], changes[b])
            if r is None or n < MIN_PAIR:
                continue
            ar = abs(r)
            if max_peer[a]["abs_rho"] is None or ar > max_peer[a]["abs_rho"]:
                max_peer[a] = {"peer": b, "abs_rho": round(ar, 4), "rho": round(r, 4), "n": n}
            if max_peer[b]["abs_rho"] is None or ar > max_peer[b]["abs_rho"]:
                max_peer[b] = {"peer": a, "abs_rho": round(ar, 4), "rho": round(r, 4), "n": n}
            if ar >= 0.85:
                pairs.append({"a": a, "b": b, "n": n, "rho": round(r, 4), "abs_rho": round(ar, 4)})
    pairs.sort(key=lambda x: x["abs_rho"], reverse=True)
    return {"threshold_abs_rho": 0.85, "pairs": pairs, "max_peer": max_peer}


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
    meta_map = {x["id"]: x for x in ordered}

    eligible = {}
    exclusions = {}
    for k, s in series_store.items():
        if k not in meta_map:
            exclusions[k] = "missing_config_metadata"
            continue
        ss = pd.Series(s).dropna().sort_index()
        aligned = ss.reindex(frame.index).ffill().dropna()
        if len(aligned) < MIN_OBS:
            exclusions[k] = f"aligned_observations<{MIN_OBS}"
            continue
        if ss.nunique() < MIN_UNIQUE:
            exclusions[k] = f"distinct_scores<{MIN_UNIQUE}"
            continue
        eligible[k] = ss

    results = []
    for k in sorted(eligible):
        results.append(validate_indicator(k, eligible[k], meta_map[k], frame))

    red = redundancy(eligible, frame.index)
    for row in results:
        row["redundancy_5d_change"] = red["max_peer"].get(row["id"])

    def abs_phase10(row):
        x = row["horizons"]["10d"]["raw_overlap_phase"].get("median_rho")
        return -1.0 if x is None else abs(float(x))

    largest = sorted(results, key=abs_phase10, reverse=True)[:15]
    role_counts = {}
    for r in results:
        role_counts[r.get("model_v2_role") or "unknown"] = role_counts.get(r.get("model_v2_role") or "unknown", 0) + 1

    stable_counts = {}
    for h in PRIMARY_HORIZONS:
        key = f"{h}d"
        stable_counts[key] = sum(
            1 for r in results
            if (r["horizons"][key]["raw_overlap_phase"].get("same_sign_as_full_pct") or 0) >= 70.0
        )

    out = {
        "schema": "INDICATOR-VALIDATION-V1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "research_only": True,
        "diagnostic_only": True,
        "production_effect": "none",
        "weights_changed": False,
        "thresholds_changed": False,
        "study_spec": SPEC,
        "model_version": ns["MODEL"].get("version"),
        "coverage": {
            "spy_start": str(frame.index.min().date()),
            "spy_end": str(frame.index.max().date()),
            "spy_observations": int(len(frame)),
            "captured_series_count": int(len(series_store)),
            "eligible_indicator_count": int(len(results)),
            "excluded_count": int(len(exclusions)),
        },
        "eligibility": {
            "minimum_aligned_observations": MIN_OBS,
            "minimum_distinct_scores": MIN_UNIQUE,
            "excluded": exclusions,
        },
        "summary": {
            "role_counts": role_counts,
            "primary_phase_same_sign_ge70_count": stable_counts,
            "redundancy_pairs_abs_rho_ge085": len(red["pairs"]),
            "largest_abs_raw_10d_phase_median_ic_descriptive_only": [
                {
                    "id": r["id"],
                    "name": r["name"],
                    "role": r["model_v2_role"],
                    "phase_median_rho": r["horizons"]["10d"]["raw_overlap_phase"].get("median_rho"),
                    "full_rho": r["horizons"]["10d"]["raw_ic"].get("rho"),
                    "same_sign_pct": r["horizons"]["10d"]["raw_overlap_phase"].get("same_sign_as_full_pct"),
                }
                for r in largest
            ],
        },
        "redundancy": red,
        "indicators": results,
        "decision": {
            "may_change_market_model_v2": False,
            "may_change_active_context_archive_membership": False,
            "may_change_weights": False,
            "historical_best_selection_allowed": False,
        },
        "warnings": [
            "Reconstructed indicator history is not fully point-in-time; macro observation dates may differ from public release dates.",
            "Forward-return horizons overlap in the full IC. Phase-split IC is reported as a robustness diagnostic.",
            "This study validates historical behavior only and cannot promote indicators into production without separate preregistration and Forward-OOS evidence.",
        ],
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({
        "eligible": len(results),
        "captured": len(series_store),
        "roles": role_counts,
        "stable_ge70": stable_counts,
        "redundancy_pairs": len(red["pairs"]),
        "top10_abs_phase10": out["summary"]["largest_abs_raw_10d_phase_median_ic_descriptive_only"][:10],
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
