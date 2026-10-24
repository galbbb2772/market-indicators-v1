"""Source-universe continuity screen for already archived V2.1.8 daily breadth.

RESEARCH ONLY. A 20% abrupt change in the size of a daily universe is a
forensic QA flag, not proof of bad data. Quarantine 252 prior symbol closes
plus 19 persistence days after each flag as a conservative contamination
SENSITIVITY TEST, never as a new trading or backtested selection rule.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

QA_BREAK_RATIO = 0.20
HILO_PRIOR = 252
PERSISTENCE = 20
DEPENDENCY_RADIUS_SESSIONS = HILO_PRIOR + PERSISTENCE - 1
REPORT_CLASS = "EXPLORATORY_BREADTH_SOURCE_QUARANTINE_NOT_PIT_PROVEN"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_qa(breadth: pd.DataFrame, score_rows: pd.DataFrame,
              break_ratio: float = QA_BREAK_RATIO) -> tuple[pd.DataFrame, dict]:
    if not 0 < break_ratio < 1:
        raise ValueError("QA break ratio must be in (0,1); NOT a trading parameter")
    required = {"date", "issues", "adv", "dec", "unch", "nh", "nl"}
    if not required.issubset(breadth.columns):
        raise ValueError("Missing original daily stock breadth counts")
    b = breadth.copy()
    b["date"] = pd.to_datetime(b.date, errors="raise").dt.normalize()
    b = b.sort_values("date").reset_index(drop=True)
    if b.date.hasnans or b.date.duplicated().any():
        raise ValueError("Source dates missing or duplicated")
    count_cols = ["issues", "adv", "dec", "unch", "nh", "nl"]
    if b[count_cols].isna().any().any() or (b[count_cols] < 0).any().any():
        raise ValueError("Source counts cannot be missing or negative")
    if ((b[["adv", "dec", "unch"]].sum(axis=1) > b.issues) |
            (b.nh + b.nl > b.issues)).any():
        raise ValueError("Classification counts exceed source issues")
    prev = b.issues.shift(1).astype(float)
    pct = (b.issues / prev - 1).where(prev > 0)
    b["universe_pct_change"] = pct * 100
    jumps = (pct.abs() > break_ratio).fillna(False)
    b["qa_jump_gt_20pct"] = jumps
    at = np.flatnonzero(jumps.to_numpy())
    flag = np.zeros(len(b), dtype=bool)
    for i in at:
        flag[i:min(len(b), i + DEPENDENCY_RADIUS_SESSIONS + 1)] = True
    b["may_depend_on_jump_in_frozen_252_plus_20_window"] = flag
    b["sessions_since_latest_jump"] = pd.Series([
        int(i - at[at <= i][-1]) if (at <= i).any() else pd.NA
        for i in range(len(b))
    ], dtype="Int64")

    s = score_rows.copy()
    if not {"date", "trigger", "route_archive_breadth_proxy"}.issubset(s.columns):
        raise ValueError("Must provide the original exploratory replay result")
    s["date"] = pd.to_datetime(s.date, errors="raise").dt.normalize()
    if s.date.hasnans or s.date.duplicated().any() or s.trigger.dtype != bool:
        raise ValueError("Source replay dates and boolean trigger must be valid")
    fields = ["date", "issues", "universe_pct_change", "qa_jump_gt_20pct",
              "may_depend_on_jump_in_frozen_252_plus_20_window", "sessions_since_latest_jump"]
    merged = s.merge(b[fields], on="date", suffixes=("", "_source"),
                     how="inner", validate="one_to_one")
    if len(merged) != len(s):
        raise ValueError("Missing QA source day for exploratory score day")
    if "issues" in s and (merged.issues != merged.issues_source).any():
        raise ValueError("Archived breadth and scored daily universe counts disagree")
    breaks = [
        {"date": r.date.date().isoformat(), "issues": int(r.issues),
         "daily_change_pct": round(float(r.universe_pct_change), 2)}
        for r in b.loc[jumps].itertuples(index=False)
    ]
    triggers = [
        {"date": r.date.date().isoformat(), "proxy_route": round(float(r.route_archive_breadth_proxy), 5),
         "possible_contamination": bool(r.may_depend_on_jump_in_frozen_252_plus_20_window),
         "market_sessions_since_last_jump": (int(r.sessions_since_latest_jump)
                                            if pd.notna(r.sessions_since_latest_jump) else None)}
        for r in merged.loc[merged.trigger].itertuples(index=False)
    ]
    report = {
        "classification": REPORT_CLASS,
        "data_quality_ratio": break_ratio,
        "quality_ratio_is_a_trading_rule": False,
        "prior_closes_needed": HILO_PRIOR,
        "persistence_sessions": PERSISTENCE,
        "conservative_dependency_radius_sessions": DEPENDENCY_RADIUS_SESSIONS,
        "archive_rows": len(b),
        "source_start": b.date.iloc[0].date().isoformat(),
        "source_end": b.date.iloc[-1].date().isoformat(),
        "universe_break_dates": breaks,
        "break_day_count": len(breaks),
        "market_sessions_flagged_for_source_review": int(flag.sum()),
        "candidate_trigger_day_count": len(triggers),
        "candidate_trigger_days_with_possible_lookback_issue": sum(t["possible_contamination"] for t in triggers),
        "candidate_triggers": triggers,
        "pit_certified_triggers": 0,
        "this_source_passes_pit_validation": False,
        "source_jump_proves_wrong_stock_prices": False,
        "delisted_security_identity_verified": False,
        "full_model_history_verified": False,
        "note": "An anomalous stock-count change flags further review, but does not prove that the model output is invalid. A 271-session sensitivity screen is conservative, not an authorization to retune the original 55-point warning threshold."
    }
    return merged, report


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--breadth", required=True)
    p.add_argument("--exploratory", required=True)
    p.add_argument("--outdir", default="research/out/v218_archived_universe_qa")
    a = p.parse_args()
    breadth, explored = Path(a.breadth), Path(a.exploratory)
    merged, report = source_qa(pd.read_csv(breadth), pd.read_csv(explored))
    report["source_breadth_sha256"] = sha256(breadth)
    report["source_exploratory_sha256"] = sha256(explored)
    outdir = Path(a.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    (outdir/"receipt.json").write_text(json.dumps(report, indent=2, ensure_ascii=False)+"\n", encoding="utf-8")
    merged[["date", "issues", "universe_pct_change", "qa_jump_gt_20pct",
            "may_depend_on_jump_in_frozen_252_plus_20_window",
            "sessions_since_latest_jump", "route_archive_breadth_proxy", "trigger"]].to_csv(
                outdir/"daily_quality_flags.csv", index=False
            )
    print(json.dumps({
        "classification": report["classification"],
        "days": report["archive_rows"],
        "universe_jumps": report["break_day_count"],
        "candidate_signal_days": report["candidate_trigger_day_count"],
        "signal_days_exposed_to_source_break": report["candidate_trigger_days_with_possible_lookback_issue"],
        "PIT_certified_triggers": report["pit_certified_triggers"],
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
