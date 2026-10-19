from __future__ import annotations

import argparse
import json
import math
from datetime import datetime, timezone

import pandas as pd
import requests

from screen_market_top_ng2_a_pre1993 import yahoo_daily

BLS_API = "https://api.bls.gov/publicAPI/v2/timeseries/data/"
SERIES = {
    "cpi": "CUUR0000SA0",
    "finished": "WPUFD49207",
    "intermediate": "WPUID61",
}

SOURCE_START_YEAR = 1947
SOURCE_END_YEAR = 2006
EFFECTIVE_LAG_MONTHS = 6
WARMUP_VALID_SOURCE_MONTHS = 120
THRESHOLD = 85.0

SCREEN_WINDOWS = [
    (pd.Period("1957-01", freq="M"), pd.Period("1967-12", freq="M")),
    (pd.Period("1975-01", freq="M"), pd.Period("1986-12", freq="M")),
    (pd.Period("1988-01", freq="M"), pd.Period("2006-12", freq="M")),
]
EXCLUDED_HYPOTHESIS_WINDOWS = [
    (pd.Period("1968-01", freq="M"), pd.Period("1974-12", freq="M")),
    (pd.Period("1987-01", freq="M"), pd.Period("1987-12", freq="M")),
]

MODEL_KEYS = (
    "ng3_costpressure",
    "inflation_only",
    "producer_gap",
    "top_location_only",
)


def fetch_bls_series(series_id: str) -> pd.Series:
    values: dict[pd.Period, float] = {}
    for start in range(SOURCE_START_YEAR, SOURCE_END_YEAR + 1, 10):
        end = min(start + 9, SOURCE_END_YEAR)
        r = requests.post(
            BLS_API,
            json={
                "seriesid": [series_id],
                "startyear": str(start),
                "endyear": str(end),
            },
            timeout=45,
        )
        r.raise_for_status()
        obj = r.json()
        if obj.get("status") != "REQUEST_SUCCEEDED":
            raise RuntimeError(f"BLS failure {series_id}: {obj}")
        for series in obj.get("Results", {}).get("series", []):
            for row in series.get("data", []):
                period = row.get("period", "")
                if not (
                    period.startswith("M")
                    and len(period) == 3
                    and period != "M13"
                ):
                    continue
                p = pd.Period(
                    f"{int(row['year']):04d}-{int(period[1:]):02d}",
                    freq="M",
                )
                values[p] = float(row["value"])

    if not values:
        raise ValueError(f"no BLS values for {series_id}")
    s = pd.Series(values, dtype=float).sort_index()
    s.name = series_id
    return s


def expanding_percentile(values: list[float], i: int) -> float:
    v = float(values[i])
    hist = values[: i + 1]
    return 100.0 * sum(float(x) <= v for x in hist) / len(hist)


def build_source_rows() -> list[dict]:
    cpi = fetch_bls_series(SERIES["cpi"])
    finished = fetch_bls_series(SERIES["finished"])
    intermediate = fetch_bls_series(SERIES["intermediate"])

    common = sorted(set(cpi.index) & set(finished.index) & set(intermediate.index))
    rows: list[dict] = []
    for p in common:
        prev = p - 12
        if prev not in cpi.index or prev not in finished.index or prev not in intermediate.index:
            continue
        cpi_yoy = 100.0 * (float(cpi.loc[p]) / float(cpi.loc[prev]) - 1.0)
        finished_yoy = 100.0 * (
            float(finished.loc[p]) / float(finished.loc[prev]) - 1.0
        )
        intermediate_yoy = 100.0 * (
            float(intermediate.loc[p]) / float(intermediate.loc[prev]) - 1.0
        )
        rows.append(
            {
                "source_period": p,
                "source_month": str(p),
                "effective_period": p + EFFECTIVE_LAG_MONTHS,
                "effective_month": str(p + EFFECTIVE_LAG_MONTHS),
                "cpi_yoy": cpi_yoy,
                "finished_ppi_yoy": finished_yoy,
                "intermediate_ppi_yoy": intermediate_yoy,
                "finished_gap_raw": finished_yoy - cpi_yoy,
                "intermediate_gap_raw": intermediate_yoy - cpi_yoy,
            }
        )

    for raw_name, score_name in (
        ("cpi_yoy", "inflation_level_score"),
        ("finished_gap_raw", "finished_gap_score"),
        ("intermediate_gap_raw", "intermediate_gap_score"),
    ):
        vals = [float(x[raw_name]) for x in rows]
        for i, row in enumerate(rows):
            row[score_name] = expanding_percentile(vals, i)

    for i, row in enumerate(rows):
        row["valid_source_history_months"] = i + 1
        row["producer_gap_score"] = math.sqrt(
            row["finished_gap_score"] * row["intermediate_gap_score"]
        )
        row["costpressure_ng3"] = (
            row["inflation_level_score"]
            * row["finished_gap_score"]
            * row["intermediate_gap_score"]
        ) ** (1.0 / 3.0)

    return rows


def in_screen_window(p: pd.Period) -> bool:
    return any(a <= p <= b for a, b in SCREEN_WINDOWS)


def top_location_gate(price: pd.Series, p: pd.Period) -> dict:
    month = price.loc[p.start_time.normalize():p.end_time.normalize()]
    if month.empty:
        raise ValueError(f"no price observations for {p}")
    asof = pd.Timestamp(month.index[-1])
    close = float(month.iloc[-1])

    trailing = price.loc[asof - pd.DateOffset(months=24):asof]
    if trailing.empty:
        raise ValueError(f"empty 24m price window for {p}")
    high = float(trailing.max())
    high_date = pd.Timestamp(trailing.idxmax())
    within = close >= 0.95 * high
    recent = high_date >= asof - pd.DateOffset(months=3)

    return {
        "asof": asof.date().isoformat(),
        "close": close,
        "high24_close": high,
        "high24_date": high_date.date().isoformat(),
        "within_5pct": bool(within),
        "high_within_3m": bool(recent),
        "passes": bool(within and recent),
    }


def build_states(price: pd.Series, rows: list[dict]) -> list[dict]:
    states = []
    for row in rows:
        p = row["effective_period"]
        if not in_screen_window(p):
            continue
        if row["valid_source_history_months"] < WARMUP_VALID_SOURCE_MONTHS:
            continue

        gate = top_location_gate(price, p)
        x = dict(row)
        x["top_location"] = gate
        x["armed"] = {
            "ng3_costpressure": bool(
                row["costpressure_ng3"] >= THRESHOLD and gate["passes"]
            ),
            "inflation_only": bool(
                row["inflation_level_score"] >= THRESHOLD and gate["passes"]
            ),
            "producer_gap": bool(
                row["producer_gap_score"] >= THRESHOLD and gate["passes"]
            ),
            "top_location_only": bool(gate["passes"]),
        }
        states.append(x)
    return states


def collapse_episodes(states: list[dict], model: str) -> list[list[dict]]:
    armed = [x for x in states if x["armed"][model]]
    episodes: list[list[dict]] = []
    for row in armed:
        if not episodes:
            episodes.append([row])
            continue
        prev = episodes[-1][-1]["effective_period"]
        cur = row["effective_period"]
        if cur.ordinal == prev.ordinal + 1:
            episodes[-1].append(row)
        else:
            episodes.append([row])
    return episodes


def max_drawdown_pct(signal_close: float, future: pd.Series) -> float:
    vals = pd.Series(
        [signal_close] + [float(x) for x in future.tolist()],
        dtype=float,
    )
    peak = vals.cummax()
    dd = vals / peak - 1.0
    return float(dd.min() * 100.0)


def classify_episode(price: pd.Series, episode: list[dict], model: str) -> dict:
    first = episode[0]
    gate = first["top_location"]
    anchor_date = pd.Timestamp(gate["asof"])
    signal_close = float(gate["close"])
    future = price.loc[price.index > anchor_date]

    horizons = {}
    for n in (63, 126, 252):
        block = future.iloc[:n]
        if len(block) < n:
            horizons[f"h{n}"] = {
                "complete": False,
                "sessions": int(len(block)),
            }
            continue
        rel = block / signal_close - 1.0
        horizons[f"h{n}"] = {
            "complete": True,
            "end_date": pd.Timestamp(block.index[-1]).date().isoformat(),
            "forward_return_pct": float(rel.iloc[-1] * 100.0),
            "worst_return_from_anchor_pct": float(rel.min() * 100.0),
            "max_peak_to_trough_dd_pct": max_drawdown_pct(
                signal_close, block
            ),
        }

    h252 = horizons["h252"]
    if not h252["complete"]:
        classification = None
    else:
        worst = float(h252["worst_return_from_anchor_pct"])
        if worst <= -20.0:
            classification = "MAJOR_TOP_HIT"
        elif worst <= -10.0:
            classification = "CORRECTION_RISK_NOT_MAJOR_TOP"
        else:
            classification = "CLEAR_TOP_FALSE_POSITIVE"

    return {
        "model": model,
        "start": first["effective_month"],
        "end": episode[-1]["effective_month"],
        "armed_months": len(episode),
        "source_month_at_start": first["source_month"],
        "anchor_date": anchor_date.date().isoformat(),
        "signal_close": signal_close,
        "scores_at_start": {
            "costpressure_ng3": first["costpressure_ng3"],
            "inflation_level_score": first["inflation_level_score"],
            "producer_gap_score": first["producer_gap_score"],
            "finished_gap_score": first["finished_gap_score"],
            "intermediate_gap_score": first["intermediate_gap_score"],
        },
        "raw_at_start": {
            "cpi_yoy": first["cpi_yoy"],
            "finished_ppi_yoy": first["finished_ppi_yoy"],
            "intermediate_ppi_yoy": first["intermediate_ppi_yoy"],
            "finished_gap_raw": first["finished_gap_raw"],
            "intermediate_gap_raw": first["intermediate_gap_raw"],
        },
        "top_location_at_start": first["top_location"],
        "classification": classification,
        "horizons": horizons,
    }


def summarize(episodes: list[dict]) -> dict:
    complete = [
        x for x in episodes
        if x["horizons"]["h252"]["complete"]
    ]
    major = sum(x["classification"] == "MAJOR_TOP_HIT" for x in complete)
    correction = sum(
        x["classification"] == "CORRECTION_RISK_NOT_MAJOR_TOP"
        for x in complete
    )
    false = sum(
        x["classification"] == "CLEAR_TOP_FALSE_POSITIVE"
        for x in complete
    )
    n = len(complete)
    return {
        "episodes": len(episodes),
        "complete_episodes": n,
        "major_top_hits": major,
        "correction_risk_not_major_top": correction,
        "clear_top_false_positives": false,
        "major_fraction": (major / n) if n else None,
        "false_fraction": (false / n) if n else None,
    }


def structural_decision(summary: dict) -> str:
    if summary["complete_episodes"] < 3:
        return "INSUFFICIENT_SCREEN_EVENTS"
    passed = (
        summary["major_top_hits"] >= 2
        and summary["clear_top_false_positives"] <= 1
        and summary["major_fraction"] >= 0.50
    )
    return "STRUCTURAL_PASS" if passed else "STRUCTURAL_FAIL"


def compare_baseline(candidate: dict, baseline: dict) -> dict:
    if baseline["complete_episodes"] == 0:
        return {
            "status": "BASELINE_INSUFFICIENT",
            "passes": False,
        }
    if candidate["complete_episodes"] == 0:
        return {
            "status": "CANDIDATE_INSUFFICIENT",
            "passes": False,
        }

    major_gte = candidate["major_fraction"] >= baseline["major_fraction"]
    false_lte = candidate["false_fraction"] <= baseline["false_fraction"]
    strict = (
        candidate["major_fraction"] > baseline["major_fraction"]
        or candidate["false_fraction"] < baseline["false_fraction"]
    )
    return {
        "status": "PASS" if (major_gte and false_lte and strict) else "FAIL",
        "passes": bool(major_gte and false_lte and strict),
        "major_fraction_gte": bool(major_gte),
        "false_fraction_lte": bool(false_lte),
        "strict_improvement": bool(strict),
    }


def serialize_state(row: dict) -> dict:
    x = dict(row)
    x.pop("source_period", None)
    x.pop("effective_period", None)
    return x


def run_screen() -> dict:
    rows = build_source_rows()
    price = yahoo_daily("^GSPC", "1954-01-01", "2009-01-15")
    states = build_states(price, rows)

    all_episodes = {}
    summaries = {}
    for model in MODEL_KEYS:
        groups = collapse_episodes(states, model)
        eps = [classify_episode(price, g, model) for g in groups]
        all_episodes[model] = eps
        summaries[model] = summarize(eps)

    candidate = summaries["ng3_costpressure"]
    structural = structural_decision(candidate)
    comparisons = {
        name: compare_baseline(candidate, summaries[name])
        for name in ("inflation_only", "producer_gap")
    }
    incremental = (
        "INCREMENTAL_VALUE_PASS"
        if all(x["passes"] for x in comparisons.values())
        else "INCREMENTAL_VALUE_FAIL"
    )

    if structural == "INSUFFICIENT_SCREEN_EVENTS":
        final = "INSUFFICIENT_SCREEN_EVENTS"
    elif structural == "STRUCTURAL_PASS" and incremental == "INCREMENTAL_VALUE_PASS":
        final = "ACCEPT_SCREENING_CANDIDATE"
    else:
        final = "REJECT"

    return {
        "schema_version": "market-top-ng3-costpressure-screen-1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "research_only": True,
        "production_effect": "none",
        "formula_version": "NG3-CostPressure",
        "preregistration": (
            "research/market_top_ng3_costpressure_preregistration.json"
        ),
        "frozen_parameters": {
            "series": SERIES,
            "effective_lag_months": EFFECTIVE_LAG_MONTHS,
            "warmup_valid_source_months": WARMUP_VALID_SOURCE_MONTHS,
            "threshold": THRESHOLD,
            "screen_windows": [
                [str(a), str(b)] for a, b in SCREEN_WINDOWS
            ],
            "hypothesis_generation_exclusions": [
                [str(a), str(b)] for a, b in EXCLUDED_HYPOTHESIS_WINDOWS
            ],
        },
        "coverage": {
            "source_rows": len(rows),
            "screen_monthly_states": len(states),
            "first_screen_month": (
                states[0]["effective_month"] if states else None
            ),
            "last_screen_month": (
                states[-1]["effective_month"] if states else None
            ),
        },
        "summaries": summaries,
        "episodes": all_episodes,
        "decision": {
            "structural": structural,
            "baseline_comparisons": comparisons,
            "incremental": incremental,
            "final": final,
        },
        "monthly_states": [serialize_state(x) for x in states],
        "governance": {
            "post_result_tuning_allowed": False,
            "margin_confirm_used": False,
            "legacy_route_a_recovered": False,
            "legacy_route_c_recovered": False,
            "production_pressure_inclusion_authorized": False,
        },
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output")
    args = ap.parse_args()

    result = run_screen()
    text = json.dumps(result, indent=2)
    print(text)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(text + "\n")


if __name__ == "__main__":
    main()
