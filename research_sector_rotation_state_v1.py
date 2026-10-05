from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

import update_data as ud
import research_sector_rotation_stage2_v1 as sr

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "docs" / "data" / "sector_rotation_state_v1.json"
SUMMARY = ROOT / "docs" / "data" / "sector_rotation_state_v1_summary.json"
SPEC = "research/sector_rotation_state_v1/STUDY_SPEC.md"
FROZEN = pd.Timestamp("2026-10-02")
SECTORS = sr.SECTORS


def agg(s: pd.Series):
    x = s.dropna().astype(float)
    return {
        "n": int(len(x)),
        "mean": None if x.empty else round(float(x.mean()), 6),
        "median": None if x.empty else round(float(x.median()), 6),
        "positive_pct": None if x.empty else round(float((x > 0).mean() * 100), 2),
    }


def yearly(s: pd.Series):
    out = {}
    for y in sorted(set(s.dropna().index.year)):
        out[str(y)] = agg(s[s.index.year == y])
    vals = [v["mean"] for v in out.values() if v["mean"] is not None]
    full = float(s.dropna().mean()) if len(s.dropna()) else None
    same = None
    if full not in (None, 0) and vals:
        same = round(100 * sum((v > 0) == (full > 0) for v in vals) / len(vals), 2)
    return {"years": out, "same_sign_pct": same}


def main():
    raw = {}
    errors = {}
    for sym in ["SPY"] + SECTORS:
        try:
            df = ud.yahoo(sym)
            df = df[df.index <= FROZEN].copy()
            if df.empty:
                raise RuntimeError("empty history")
            raw[sym] = df
        except Exception as exc:
            errors[sym] = repr(exc)
    if "SPY" not in raw:
        raise RuntimeError(f"SPY missing: {errors}")
    available = [s for s in SECTORS if s in raw]
    if len(available) < 9:
        raise RuntimeError(f"Need >=9 sectors, got {len(available)}; errors={errors}")

    close = pd.concat({s: raw[s]["Close"] for s in ["SPY"] + available}, axis=1).sort_index().ffill()
    volume = pd.concat({s: raw[s]["Volume"] for s in available}, axis=1).sort_index().reindex(close.index)
    close = close[close.index <= FROZEN]
    volume = volume.reindex(close.index)
    if close.index.max() != FROZEN:
        raise RuntimeError(f"Frozen date missing; latest={close.index.max()}")

    spy = close["SPY"]
    sec = close[available]
    rel20 = sec.pct_change(20) * 100 - (spy.pct_change(20) * 100).to_numpy()[:, None]
    rel60 = sec.pct_change(60) * 100 - (spy.pct_change(60) * 100).to_numpy()[:, None]
    momentum = 0.5 * rel20.rank(axis=1, pct=True) + 0.5 * rel60.rank(axis=1, pct=True)
    contrarian = 1.0 - momentum

    ret1 = sec.pct_change() * 100
    spy1 = spy.pct_change() * 100
    abs_excess = ret1.sub(spy1, axis=0).abs()
    volratio = volume / volume.rolling(20, min_periods=15).mean()
    activity = 0.5 * abs_excess.rank(axis=1, pct=True) + 0.5 * volratio.rank(axis=1, pct=True)
    interaction = contrarian * activity

    sec10 = (sec.shift(-10) / sec - 1) * 100
    spy10 = (spy.shift(-10) / spy - 1) * 100
    out10 = sec10.sub(spy10, axis=0)

    plain_ic = {}
    int_ic = {}
    spread = {}
    persistence = {}
    dispersion = (0.5 * rel20 + 0.5 * rel60).std(axis=1)
    disp_med = dispersion.rolling(252, min_periods=126).median()
    high_disp = dispersion >= disp_med
    low_disp = dispersion < disp_med

    dates = list(momentum.index)
    for i, dt in enumerate(dates):
        y = out10.loc[dt]
        c = contrarian.loc[dt]
        it = interaction.loc[dt]
        r0 = sr.xsec_spearman(c, y)
        r1 = sr.xsec_spearman(it, y)
        if r0 is not None:
            plain_ic[dt] = r0
        if r1 is not None:
            int_ic[dt] = r1
        z = pd.concat([momentum.loc[dt].rename("m"), y.rename("y")], axis=1).dropna().sort_values("m")
        if len(z) >= 8:
            spread[dt] = float(z.head(2).y.mean() - z.tail(2).y.mean())
        if i >= 5:
            now = momentum.loc[dt].dropna()
            prev = momentum.loc[dates[i - 5]].dropna()
            common = now.index.intersection(prev.index)
            if len(common) >= 8:
                persistence[dt] = len(set(now.reindex(common).nlargest(3).index) & set(prev.reindex(common).nlargest(3).index)) / 3

    plain_ic = pd.Series(plain_ic, dtype=float).sort_index()
    int_ic = pd.Series(int_ic, dtype=float).sort_index()
    spread = pd.Series(spread, dtype=float).sort_index()
    persistence = pd.Series(persistence, dtype=float).sort_index()

    high_persist = persistence >= (2 / 3)
    low_persist = persistence <= (1 / 3)

    masks = {
        "high_dispersion": high_disp,
        "low_dispersion": low_disp,
        "high_persistence": high_persist,
        "low_persistence": low_persist,
        "high_dispersion_low_persistence": high_disp & low_persist.reindex(high_disp.index).fillna(False),
        "high_dispersion_high_persistence": high_disp & high_persist.reindex(high_disp.index).fillna(False),
        "low_dispersion_low_persistence": low_disp & low_persist.reindex(low_disp.index).fillna(False),
        "low_dispersion_high_persistence": low_disp & high_persist.reindex(low_disp.index).fillna(False),
    }

    state = {}
    for k, m in masks.items():
        idx = spread.index.intersection(m.index[m.fillna(False)])
        s = spread.reindex(idx).dropna()
        state[k] = {
            "contrarian_bottom2_minus_top2_10d": agg(s),
            "phase10": sr.phase_robustness(s, 10),
            "yearly": yearly(s),
        }

    payload = {
        "schema": "SECTOR-ROTATION-STATE-V1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "research_only": True,
        "diagnostic_only": True,
        "production_effect": "none",
        "study_spec": SPEC,
        "frozen_through_market_date": str(FROZEN.date()),
        "coverage": {"start": str(close.index.min().date()), "end": str(close.index.max().date()), "trading_days": len(close), "sector_count": len(available), "download_errors": errors},
        "activity_interaction": {
            "plain_contrarian_ic10": agg(plain_ic),
            "activity_weighted_contrarian_ic10": agg(int_ic),
            "delta_mean_ic": round(float(int_ic.mean() - plain_ic.reindex(int_ic.index).mean()), 6),
            "plain_phase10": sr.phase_robustness(plain_ic, 10),
            "interaction_phase10": sr.phase_robustness(int_ic, 10),
        },
        "dispersion": {"full": agg(dispersion), "high_pct": round(float(high_disp.dropna().mean() * 100), 2)},
        "leader_persistence_5d": {"full": agg(persistence), "high_pct": round(float(high_persist.dropna().mean() * 100), 2), "low_pct": round(float(low_persist.dropna().mean() * 100), 2)},
        "state_results": state,
        "guardrails": {"may_change_production": False, "may_optimize_thresholds": False, "historical_results_count_as_forward_oos": False},
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    summary = {
        "schema": "SECTOR-ROTATION-STATE-V1-SUMMARY",
        "generated_at": payload["generated_at"],
        "research_only": True,
        "frozen_through_market_date": payload["frozen_through_market_date"],
        "coverage": payload["coverage"],
        "activity_interaction": payload["activity_interaction"],
        "leader_persistence_5d": payload["leader_persistence_5d"],
        "state_results": state,
        "guardrails": payload["guardrails"],
    }
    SUMMARY.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({
        "activity": payload["activity_interaction"],
        "states": {k: v["contrarian_bottom2_minus_top2_10d"] for k, v in state.items()},
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
