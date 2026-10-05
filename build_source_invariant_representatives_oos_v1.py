from __future__ import annotations

import json
from datetime import datetime, time, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

import research_factor_map_source_invariant_v1 as sfm

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "docs" / "data" / "source_invariant_representatives_oos_v1.json"
PREREG = "research/source_invariant_representatives_oos_v1/PREREGISTRATION.md"
FROZEN_THROUGH = pd.Timestamp("2026-10-02")
NY = ZoneInfo("America/New_York")
TOL = 1e-9

CANDIDATES = {
    "fear_volatility::c15": {
        "member": "sector_utilities_vol",
        "expected_ic10_sign": "negative",
        "historical_ic10": -0.142824,
        "historical_bh_fdr_q": 0.061938,
    },
    "fear_volatility::c10": {
        "member": "sector_fin_vol",
        "expected_ic10_sign": "negative",
        "historical_ic10": -0.133312,
        "historical_bh_fdr_q": 0.077423,
    },
    "sentiment_event::c2": {
        "member": "geo_news_impact",
        "expected_ic10_sign": "negative",
        "historical_ic10": -0.093116,
        "historical_bh_fdr_q": 0.030969,
    },
}


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def load_existing():
    if not OUT.exists():
        return None
    return json.loads(OUT.read_text(encoding="utf-8"))


def completed_cutoff(close: pd.Series) -> pd.Timestamp:
    close = close.dropna().sort_index()
    if close.empty:
        raise RuntimeError("SPY close series is empty")
    latest = pd.Timestamp(close.index.max()).normalize()
    now_et = datetime.now(timezone.utc).astimezone(NY)
    if latest.date() == now_et.date() and now_et.time() < time(17, 0):
        prior = close.index[pd.DatetimeIndex(close.index).normalize() < latest]
        if len(prior) == 0:
            raise RuntimeError("No completed SPY session before current intraday bar")
        latest = pd.Timestamp(prior.max()).normalize()
    return latest


def supportive_series(series_store: dict, ordered: list[dict], member: str):
    s = series_store.get(member)
    if s is None:
        raise RuntimeError(f"Missing source-invariant series: {member}")
    meta = {x.get("id"): x for x in ordered}.get(member)
    if not meta:
        raise RuntimeError(f"Missing metadata for {member}")
    pol = int(meta.get("impact_polarity", 0) or 0)
    if pol not in (-1, 1):
        raise RuntimeError(f"Candidate {member} has non-directional polarity {pol}")
    x = pd.Series(s).dropna().sort_index().astype(float)
    return x if pol == 1 else 100.0 - x, pol


def init_payload(generated: str):
    return {
        "schema": "SOURCE-INVARIANT-REPRESENTATIVES-OOS-V1",
        "generated_at": generated,
        "research_only": True,
        "observation_only": True,
        "production_effect": "none",
        "preregistration": PREREG,
        "frozen_through_market_date": str(FROZEN_THROUGH.date()),
        "candidates": {
            key: {
                **cfg,
                "observations": [],
                "source_recompute_discrepancies": [],
            }
            for key, cfg in CANDIDATES.items()
        },
        "confirmatory_protocol": {
            "minimum_matured_daily_observations": 252,
            "minimum_calendar_months": 12,
            "block_sessions": 20,
            "bootstrap_replications": 1000,
            "circular_shift_replications": 1000,
            "multiple_testing": "BH-FDR across exactly three preregistered candidates",
            "automatic_promotion": False,
        },
        "confirmatory_lock": None,
        "warnings": [
            "Historical evidence through 2026-10-02 is excluded from the prospective sample.",
            "First-seen scores are immutable; later recomputation disagreements are logged separately.",
            "Adjusted-close forward returns are frozen at first maturity and are not rewritten later.",
        ],
    }


def add_discrepancy(bucket: dict, date: str, stored: float, recomputed: float, generated: str):
    key = (date, round(float(stored), 10), round(float(recomputed), 10))
    seen = {
        (x.get("market_date"), round(float(x.get("stored_score")), 10), round(float(x.get("recomputed_score")), 10))
        for x in bucket.get("source_recompute_discrepancies", [])
        if x.get("stored_score") is not None and x.get("recomputed_score") is not None
    }
    if key not in seen:
        bucket.setdefault("source_recompute_discrepancies", []).append({
            "market_date": date,
            "stored_score": float(stored),
            "recomputed_score": float(recomputed),
            "detected_at": generated,
        })


def main():
    generated = now_iso()
    _, cap = sfm.source_invariant_capture()
    if not cap:
        raise RuntimeError("No source-invariant capture generated")
    series_store = cap.get("series_store") or {}
    mk = cap.get("mk") or {}
    ordered = cap.get("ordered") or []
    if "SPY" not in mk:
        raise RuntimeError("SPY missing")

    close = mk["SPY"]["Close"].dropna().sort_index().astype(float)
    cutoff = completed_cutoff(close)
    close = close[close.index <= cutoff]
    market_dates = pd.DatetimeIndex(close.index).normalize()
    date_to_pos = {str(pd.Timestamp(d).date()): i for i, d in enumerate(market_dates)}

    payload = load_existing() or init_payload(generated)
    if payload.get("frozen_through_market_date") != str(FROZEN_THROUGH.date()):
        raise RuntimeError("Existing ledger freeze date does not match V1 preregistration")
    if set(payload.get("candidates", {})) != set(CANDIDATES):
        raise RuntimeError("Existing ledger candidate set differs from preregistered V1 candidates")

    newly_added = {k: 0 for k in CANDIDATES}
    newly_matured = {k: 0 for k in CANDIDATES}

    for key, cfg in CANDIDATES.items():
        bucket = payload["candidates"][key]
        score, pol = supportive_series(series_store, ordered, cfg["member"])
        score = score[score.index <= cutoff]
        score_by_date = {str(pd.Timestamp(d).date()): float(v) for d, v in score.items()}
        existing = {x["market_date"]: x for x in bucket.get("observations", [])}

        eligible_dates = [
            str(pd.Timestamp(d).date())
            for d in market_dates
            if pd.Timestamp(d).normalize() > FROZEN_THROUGH and str(pd.Timestamp(d).date()) in score_by_date
        ]

        for d in eligible_dates:
            recomputed = score_by_date[d]
            if d in existing:
                stored = float(existing[d]["score"])
                if abs(stored - recomputed) > TOL:
                    add_discrepancy(bucket, d, stored, recomputed, generated)
                continue
            pos = date_to_pos[d]
            obs = {
                "market_date": d,
                "first_seen_at": generated,
                "first_seen_market_date": d,
                "score": recomputed,
                "impact_polarity": pol,
                "spy_close_first_seen": float(close.iloc[pos]),
                "outcome_10d_pct": None,
                "maturity_market_date": None,
                "outcome_matured_at": None,
                "entry_close_at_maturity": None,
                "exit_close_at_maturity": None,
            }
            bucket.setdefault("observations", []).append(obs)
            existing[d] = obs
            newly_added[key] += 1

        bucket["observations"].sort(key=lambda x: x["market_date"])

        for obs in bucket["observations"]:
            if obs.get("outcome_10d_pct") is not None:
                continue
            d = obs["market_date"]
            pos = date_to_pos.get(d)
            if pos is None or pos + 10 >= len(close):
                continue
            maturity_date = str(pd.Timestamp(close.index[pos + 10]).date())
            entry = float(close.iloc[pos])
            exit_ = float(close.iloc[pos + 10])
            obs["outcome_10d_pct"] = (exit_ / entry - 1.0) * 100.0
            obs["maturity_market_date"] = maturity_date
            obs["outcome_matured_at"] = generated
            obs["entry_close_at_maturity"] = entry
            obs["exit_close_at_maturity"] = exit_
            newly_matured[key] += 1

    counts = {}
    first_dates = []
    for key, bucket in payload["candidates"].items():
        obs = bucket.get("observations", [])
        matured = [x for x in obs if x.get("outcome_10d_pct") is not None]
        first = obs[0]["market_date"] if obs else None
        if first:
            first_dates.append(pd.Timestamp(first))
        counts[key] = {
            "forward_observation_count": len(obs),
            "matured_10d_count": len(matured),
            "first_forward_market_date": first,
            "latest_forward_market_date": obs[-1]["market_date"] if obs else None,
            "discrepancy_count": len(bucket.get("source_recompute_discrepancies", [])),
        }

    min_matured = min((v["matured_10d_count"] for v in counts.values()), default=0)
    months_ready = False
    if first_dates:
        first_common = min(first_dates)
        months_ready = cutoff >= first_common + pd.DateOffset(months=12)
    sample_ready = min_matured >= 252

    if payload.get("confirmatory_lock") is None and sample_ready and months_ready:
        common_matured = None
        for key, bucket in payload["candidates"].items():
            dates = [x["market_date"] for x in bucket.get("observations", []) if x.get("outcome_10d_pct") is not None]
            common_matured = set(dates) if common_matured is None else common_matured & set(dates)
        locked = sorted(common_matured or [])[:252]
        if len(locked) >= 252:
            payload["confirmatory_lock"] = {
                "locked_at": generated,
                "locked_market_date": str(cutoff.date()),
                "locked_observation_count": 252,
                "locked_market_dates": locked,
            }

    payload["generated_at"] = generated
    payload["latest_completed_market_date"] = str(cutoff.date())
    payload["status"] = {
        "counts": counts,
        "minimum_matured_count_across_candidates": min_matured,
        "sample_gate_ready": sample_ready,
        "calendar_gate_ready": months_ready,
        "confirmatory_lock_ready": payload.get("confirmatory_lock") is not None,
        "automatic_promotion": False,
    }
    payload["last_run_changes"] = {
        "new_observations": newly_added,
        "newly_matured_10d": newly_matured,
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({
        "latest_completed_market_date": payload["latest_completed_market_date"],
        "counts": counts,
        "new_observations": newly_added,
        "newly_matured": newly_matured,
        "confirmatory_lock": payload.get("confirmatory_lock"),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
