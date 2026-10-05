from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

import research_indicator_validation_v1 as base
import research_indicator_validation_marketprice_v1 as mp

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "docs" / "data" / "indicator_family_validation_v1.json"
SPEC = "research/indicator_family_validation_v1/STUDY_SPEC.md"

FAMILIES = {
    "volatility_risk": [
        "largecap_panic","retail_panic","options_anomaly","tech100_volatility","vol_60d_change",
        "mag7_volatility","ai7_volatility","sector_it_vol","sector_comm_vol","sector_cons_disc_vol",
        "sector_cons_staples_vol","sector_fin_vol","sector_health_vol","sector_industrial_vol",
        "sector_energy_vol","sector_materials_vol","sector_utilities_vol","sector_realestate_vol",
    ],
    "valuation_structure": [
        "valuation_cycle","valuation_percentile","valuation_speed","market_overextension",
        "market_support","money_making_effect","sme_survival_growth",
    ],
    "participation_concentration": [
        "retail_participation","retail_holdings_concentration","concentration","breadth_concentration","quant_crowding",
    ],
    "volume_activity": ["market_volume","volume_speed","market_topic_heat","mag7_volume","ai7_volume"],
    "cross_asset_event": [
        "cross_asset_correlation","rate_cycle_sensitivity","gold","oil","geo_news_impact","geo_lag_reaction","global_cb_cycle_entry",
    ],
    "price_speed_context": ["market_move_speed"],
}


def oriented_series(series_store, meta_map, key, index):
    s = series_store.get(key)
    m = meta_map.get(key) or {}
    pol = int(m.get("impact_polarity", 0) or 0)
    if s is None or pol not in (-1, 1):
        return None
    a = pd.Series(s).sort_index().reindex(index).ffill()
    return 50.0 + pol * (a - 50.0)


def build_family(series_store, meta_map, members, index, allow_single=False):
    parts = {}
    for k in members:
        s = oriented_series(series_store, meta_map, k, index)
        if s is not None:
            parts[k] = s
    if not parts:
        return pd.Series(dtype=float), parts
    df = pd.concat(parts, axis=1)
    min_count = 1 if allow_single else 2
    comp = df.mean(axis=1, skipna=True).where(df.notna().sum(axis=1) >= min_count).dropna()
    return comp, parts


def validate_family(name, comp, parts, frame):
    out = {
        "family": name,
        "member_count_oriented": len(parts),
        "oriented_members": sorted(parts),
        "sample_start": str(comp.index.min().date()) if len(comp) else None,
        "sample_end": str(comp.index.max().date()) if len(comp) else None,
        "observations": int(len(comp)),
        "horizons": {},
        "rolling_ic": {},
        "lomo_10d": [],
    }
    for h in base.HORIZONS:
        target = frame[f"fwd_{h}d"]
        r, n = base.rho(comp, target)
        out["horizons"][f"{h}d"] = {
            "ic": {"n": n, "rho": None if r is None else round(r, 4)},
            "quintiles": base.quintile_stats(comp, target),
            "overlap_phase": base.phase_robustness(comp, target, h, r),
            "era_ic": base.era_ics(comp, target),
            "regime_ic": {
                "above200": base.split_ic(comp, target, frame["price_regime"].eq("above200")),
                "below200": base.split_ic(comp, target, frame["price_regime"].eq("below200")),
                "high_ge20": base.split_ic(comp, target, frame["vol_regime"].eq("high_ge20")),
                "low_lt20": base.split_ic(comp, target, frame["vol_regime"].eq("low_lt20")),
            },
        }
    for h in (10, 20):
        out["rolling_ic"][f"{h}d"] = base.rolling_ic(comp, frame[f"fwd_{h}d"])

    full10 = out["horizons"]["10d"]["ic"].get("rho")
    if len(parts) >= 2:
        df = pd.concat(parts, axis=1)
        for removed in sorted(parts):
            cols = [c for c in df.columns if c != removed]
            min_count = 1 if len(cols) == 1 else 2
            alt = df[cols].mean(axis=1, skipna=True).where(df[cols].notna().sum(axis=1) >= min_count).dropna()
            r, n = base.rho(alt, frame["fwd_10d"])
            out["lomo_10d"].append({
                "removed": removed,
                "n": n,
                "rho": None if r is None else round(r, 4),
                "delta_vs_full": None if r is None or full10 is None else round(float(r) - float(full10), 4),
            })
    return out


def family_redundancy(composites):
    ids = sorted(composites)
    pairs = []
    max_peer = {k: {"peer": None, "abs_rho": None, "rho": None, "n": 0} for k in ids}
    changes = {k: pd.Series(composites[k]).sort_index().diff(5) for k in ids}
    for i, a in enumerate(ids):
        for b in ids[i + 1:]:
            r, n = base.rho(changes[a], changes[b])
            if r is None:
                continue
            ar = abs(r)
            if max_peer[a]["abs_rho"] is None or ar > max_peer[a]["abs_rho"]:
                max_peer[a] = {"peer": b, "abs_rho": round(ar, 4), "rho": round(r, 4), "n": n}
            if max_peer[b]["abs_rho"] is None or ar > max_peer[b]["abs_rho"]:
                max_peer[b] = {"peer": a, "abs_rho": round(ar, 4), "rho": round(r, 4), "n": n}
            if ar >= 0.70:
                pairs.append({"a": a, "b": b, "n": n, "rho": round(r, 4), "abs_rho": round(ar, 4)})
    pairs.sort(key=lambda x: x["abs_rho"], reverse=True)
    return {"threshold_abs_rho": 0.70, "pairs": pairs, "max_peer": max_peer}


def main():
    ns, cap = mp.run_market_price_capture()
    if not cap:
        raise RuntimeError("No market-price capture")
    series_store = cap["series_store"]
    ordered = cap["ordered"]
    mk = cap["mk"]
    close = mk["SPY"]["Close"].dropna().sort_index()
    frame = base.forward_frame(close)
    meta_map = {x["id"]: x for x in ordered}

    families = []
    composites = {}
    membership_diag = {}
    for name, members in FAMILIES.items():
        allow_single = name == "price_speed_context"
        comp, parts = build_family(series_store, meta_map, members, frame.index, allow_single=allow_single)
        composites[name] = comp
        membership_diag[name] = {
            "declared_members": members,
            "oriented_members_used": sorted(parts),
            "neutral_or_unavailable_members": sorted(set(members) - set(parts)),
        }
        families.append(validate_family(name, comp, parts, frame))

    red = family_redundancy(composites)
    for row in families:
        row["family_redundancy_5d_change"] = red["max_peer"].get(row["family"])

    ranked = sorted(
        families,
        key=lambda x: abs(x["horizons"]["10d"]["overlap_phase"].get("median_rho") or 0),
        reverse=True,
    )

    out = {
        "schema": "INDICATOR-FAMILY-VALIDATION-V1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "research_only": True,
        "diagnostic_only": True,
        "production_effect": "none",
        "weights_changed": False,
        "membership_changed": False,
        "study_spec": SPEC,
        "model_version": ns["MODEL"].get("version"),
        "coverage": {
            "spy_start": str(frame.index.min().date()),
            "spy_end": str(frame.index.max().date()),
            "spy_observations": int(len(frame)),
            "family_count": len(families),
        },
        "family_membership": membership_diag,
        "summary": {
            "ranked_by_abs_10d_phase_median_ic_descriptive_only": [
                {
                    "family": x["family"],
                    "observations": x["observations"],
                    "member_count_oriented": x["member_count_oriented"],
                    "full_10d_rho": x["horizons"]["10d"]["ic"].get("rho"),
                    "phase_median_10d_rho": x["horizons"]["10d"]["overlap_phase"].get("median_rho"),
                    "phase_same_sign_10d_pct": x["horizons"]["10d"]["overlap_phase"].get("same_sign_as_full_pct"),
                    "q5_minus_q1_10d_pp": x["horizons"]["10d"]["quintiles"].get("q5_minus_q1_pp"),
                    "rolling_10d_median_rho": x["rolling_ic"]["10d"].get("median_rho"),
                    "rolling_10d_positive_pct": x["rolling_ic"]["10d"].get("positive_pct"),
                    "max_family_peer": red["max_peer"].get(x["family"]),
                }
                for x in ranked
            ],
            "family_redundancy_pairs_abs_rho_ge070": len(red["pairs"]),
        },
        "family_redundancy": red,
        "families": families,
        "decision": {
            "may_change_market_model_v2": False,
            "may_change_weights": False,
            "may_change_family_membership": False,
            "historical_best_selection_allowed": False,
        },
        "warnings": [
            "This study intentionally excludes FRED/official-source-dependent formulas.",
            "Family composites are equal-weight and polarity-aligned; no fitted weights or member selection are used.",
            "Historical family results are diagnostic only and require separate prospective validation before production use.",
        ],
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(out["summary"], ensure_ascii=False))


if __name__ == "__main__":
    main()
