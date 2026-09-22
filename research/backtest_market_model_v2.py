from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from update_data import yahoo, _box_metrics

OUT = ROOT / "research" / "market_model_v2_backtest.json"
SUMMARY = ROOT / "research" / "market_model_v2_backtest.md"

SYMBOLS = ["SPY", "QQQ", "DIA"]
COST_PER_UNIT_TURNOVER = 0.0005  # 5 bps
TRAFFIC_EXPOSURE = {"green": 1.00, "blue": 0.60, "yellow": 0.375, "red": 0.125}


def light(v: float) -> str:
    if v < 45:
        return "red"
    if v < 55:
        return "yellow"
    if v < 65:
        return "blue"
    return "green"


def metrics(ret: pd.Series, exposure: pd.Series, trades: int) -> dict:
    ret = ret.dropna().astype(float)
    if ret.empty:
        return {}
    eq = (1.0 + ret).cumprod()
    years = max((ret.index[-1] - ret.index[0]).days / 365.25, len(ret) / 252.0)
    total = float(eq.iloc[-1] - 1.0)
    cagr = float(eq.iloc[-1] ** (1.0 / years) - 1.0) if years > 0 and eq.iloc[-1] > 0 else np.nan
    peak = eq.cummax()
    dd = eq / peak - 1.0
    ann_vol = float(ret.std(ddof=1) * math.sqrt(252)) if len(ret) > 2 else np.nan
    sharpe = float(ret.mean() / ret.std(ddof=1) * math.sqrt(252)) if ret.std(ddof=1) > 0 else np.nan
    neg = ret[ret < 0]
    sortino = float(ret.mean() / neg.std(ddof=1) * math.sqrt(252)) if len(neg) > 2 and neg.std(ddof=1) > 0 else np.nan
    mdd = float(dd.min())
    calmar = float(cagr / abs(mdd)) if mdd < 0 and np.isfinite(cagr) else np.nan
    return {
        "total_return_pct": round(total * 100, 2),
        "cagr_pct": round(cagr * 100, 2) if np.isfinite(cagr) else None,
        "max_drawdown_pct": round(mdd * 100, 2),
        "ann_vol_pct": round(ann_vol * 100, 2) if np.isfinite(ann_vol) else None,
        "sharpe": round(sharpe, 3) if np.isfinite(sharpe) else None,
        "sortino": round(sortino, 3) if np.isfinite(sortino) else None,
        "calmar": round(calmar, 3) if np.isfinite(calmar) else None,
        "time_in_market_pct": round(float(exposure.reindex(ret.index).fillna(0).mean()) * 100, 2),
        "trades": int(trades),
        "ending_1usd": round(float(eq.iloc[-1]), 4),
    }


def apply_exposure(asset_ret: pd.Series, exposure: pd.Series) -> tuple[pd.Series, int]:
    exp = exposure.reindex(asset_ret.index).fillna(0.0).clip(0, 1)
    turnover = exp.diff().abs().fillna(exp.iloc[0])
    net = exp * asset_ret - COST_PER_UNIT_TURNOVER * turnover
    trades = int(((exp > 0) & (exp.shift(1).fillna(0) <= 0)).sum())
    return net, trades


def build_traffic_exposure(state: pd.Series, idx: pd.DatetimeIndex) -> pd.Series:
    s = state.reindex(idx).ffill()
    decision = s.map(lambda x: TRAFFIC_EXPOSURE[light(float(x))] if pd.notna(x) else np.nan)
    # Score known at close t can only size the close(t)->close(t+1) interval.
    return decision.shift(1).fillna(0.0)


def build_box_exposure(df: pd.DataFrame, mode: str) -> pd.Series:
    idx = df.index
    exp = pd.Series(0.0, index=idx)
    holding = False
    active = None
    held = 0

    for i in range(len(idx) - 1):
        hist = df.iloc[: i + 1]
        candidates = {}
        if mode in ("small", "combined") and len(hist) >= 20:
            candidates["small"] = _box_metrics(hist, 20)
        if mode in ("large", "combined") and len(hist) >= 60:
            candidates["large"] = _box_metrics(hist, 60)

        if not holding:
            eligible = []
            for name, m in candidates.items():
                if m and m.get("formed") and float(m.get("position_pct", 100)) <= 30:
                    eligible.append((float(m.get("formation_score", 0)), name, m))
            if eligible:
                _, active, _ = max(eligible)
                holding = True
                held = 0
        else:
            m = candidates.get(active)
            max_hold = 20 if active == "small" else 60
            exit_now = False
            if not m or not m.get("formed"):
                exit_now = True
            else:
                width = float(m["upper"]) - float(m["lower"])
                close = float(m["last_close"])
                if float(m.get("position_pct", 0)) >= 70:
                    exit_now = True
                if close < float(m["lower"]) - 0.10 * width:
                    exit_now = True
                if held >= max_hold:
                    exit_now = True
            if exit_now:
                holding = False
                active = None
                held = 0

        exp.iloc[i + 1] = 1.0 if holding else 0.0
        if holding:
            held += 1

    return exp


def load_state() -> pd.Series:
    obj = json.loads((ROOT / "docs" / "data" / "current.json").read_text(encoding="utf-8"))
    rows = obj["regime_backtest"]["history"]
    s = pd.Series(
        {pd.Timestamp(x["date"]): float(x["score"]) for x in rows},
        dtype=float,
    ).sort_index()
    return s


def main() -> int:
    state = load_state()
    market = {sym: yahoo(sym) for sym in SYMBOLS}
    start = max(state.index.min(), max(df.index.min() for df in market.values()))
    end = min(state.index.max(), min(df.index.max() for df in market.values()))
    common = state.loc[start:end].index
    for sym in SYMBOLS:
        common = common.intersection(market[sym].loc[start:end].index)
    common = common.sort_values()

    state = state.reindex(common).ffill()
    results = {
        "method_version": "MARKET-MODEL-V2-BACKTEST-2026-09-22",
        "sample_start": str(common.min().date()),
        "sample_end": str(common.max().date()),
        "trading_days": int(len(common)),
        "transaction_cost_bps_per_unit_turnover": 5,
        "benchmark_definition": "Long-only buy-and-hold SPY / QQQ / DIA.",
        "traffic_definition": {
            "green": 1.0, "blue": 0.60, "yellow": 0.375, "red": 0.125,
            "timing": "signal at close t, exposure begins for t->t+1; no same-close return capture",
        },
        "box_definition": {
            "small_window": 20,
            "large_window": 60,
            "entry": "formed box and prior-close position <=30%",
            "exit": "prior-close position >=70%, box invalid, 10%-of-box downside break, or max hold 20/60 trading days",
            "timing": "all box decisions lagged one trading interval",
        },
        "caveat": "Traffic composite is reconstructed research history and some macro observation dates may not equal true release timestamps. Box signals are price-only and mechanically point-in-time.",
        "symbols": {},
    }

    eq3_bh_rets = []
    for sym in SYMBOLS:
        df = market[sym].reindex(common).copy()
        ar = df["Close"].pct_change().fillna(0.0)

        benchmark_exp = pd.Series(1.0, index=common)
        bh_net, bh_trades = apply_exposure(ar, benchmark_exp)

        traffic_exp = build_traffic_exposure(state, common)
        traffic_net, traffic_trades = apply_exposure(ar, traffic_exp)

        small_exp = build_box_exposure(df, "small")
        small_net, small_trades = apply_exposure(ar, small_exp)

        large_exp = build_box_exposure(df, "large")
        large_net, large_trades = apply_exposure(ar, large_exp)

        box_exp = build_box_exposure(df, "combined")
        box_net, box_trades = apply_exposure(ar, box_exp)

        combo_exp = (box_exp * traffic_exp).clip(0, 1)
        combo_net, combo_trades = apply_exposure(ar, combo_exp)

        results["symbols"][sym] = {
            "BUY_HOLD": metrics(bh_net, benchmark_exp, bh_trades),
            "TRAFFIC_MID": metrics(traffic_net, traffic_exp, traffic_trades),
            "BOX_SMALL": metrics(small_net, small_exp, small_trades),
            "BOX_LARGE": metrics(large_net, large_exp, large_trades),
            "BOX_COMBINED": metrics(box_net, box_exp, box_trades),
            "BOX_X_TRAFFIC": metrics(combo_net, combo_exp, combo_trades),
        }
        eq3_bh_rets.append(bh_net.rename(sym))

    eq3 = pd.concat(eq3_bh_rets, axis=1).mean(axis=1)
    results["equal_weight_3index_buy_hold"] = metrics(
        eq3,
        pd.Series(1.0, index=eq3.index),
        1,
    )

    OUT.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        "# Market Model V2 backtest vs passive index benchmarks",
        "",
        f"Sample: {results['sample_start']} to {results['sample_end']} ({results['trading_days']} trading days)",
        "",
        "| Symbol | Variant | Total % | CAGR % | MaxDD % | Sharpe | Time in market % | Trades |",
        "|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for sym, variants in results["symbols"].items():
        for name, m in variants.items():
            lines.append(
                f"| {sym} | {name} | {m['total_return_pct']} | {m['cagr_pct']} | {m['max_drawdown_pct']} | "
                f"{m['sharpe']} | {m['time_in_market_pct']} | {m['trades']} |"
            )
    lines += [
        "",
        "## Interpretation guardrails",
        "",
        "- BUY_HOLD is the primary benchmark for each index.",
        "- TRAFFIC_MID tests only the regime score as a risk-allocation overlay.",
        "- BOX_SMALL / BOX_LARGE / BOX_COMBINED test price-only range mean reversion.",
        "- BOX_X_TRAFFIC tests the full idea: box entry context multiplied by the regime risk budget.",
        "- Traffic history is exploratory rather than strict point-in-time because some macro series may have release-date mismatch.",
    ]
    SUMMARY.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(results, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
