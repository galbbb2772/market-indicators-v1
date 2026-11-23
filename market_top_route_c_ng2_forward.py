from __future__ import annotations

import argparse
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from audit_market_top_ng1_a_independent import (
    FF25_URL,
    FF3_URL,
    compounded,
    expanding_pct,
    parse_ff3,
    parse_portfolio_block,
)
from market_top_canonical_inputs import valuation_history
from market_top_ng3_forward import (
    add_months,
    fetch_spy,
    top_gate,
    unzip_current_ff,
)
from update_market_top_shadow import fetch_shiller

THRESHOLD = 85.0
HANDOFF_MIN = 0.40
WARMUP_MONTHS = 120
PREREGISTRATION_DATE = "2026-10-19"
FIRST_PROSPECTIVE_EFFECTIVE_MONTH = "202701"

OUT_CURRENT = Path("docs/data/market_top_route_c_ng2_current.json")
OUT_HISTORY = Path("docs/data/market_top_route_c_ng2_history.json")


def median25(xs: list[float]) -> float:
    if len(xs) != 25:
        raise ValueError("expected 25 portfolio returns")
    return sorted(float(x) for x in xs)[12]


def leadership_handoff_share(
    leader_gap_raw: float,
    big_growth_gap_raw: float,
) -> float:
    leader = float(leader_gap_raw)
    if leader <= 1e-12:
        return 0.0
    return max(
        0.0,
        min(
            1.0,
            (leader - float(big_growth_gap_raw)) / leader,
        ),
    )


def build_ff25_states() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    ff25_text, ff25_prov = unzip_current_ff(FF25_URL)
    ff3_text, ff3_prov = unzip_current_ff(FF3_URL)

    headers, r25 = parse_portfolio_block(
        ff25_text,
        "Average Value Weighted Returns -- Monthly",
        25,
    )
    ff3 = parse_ff3(ff3_text)
    if "BIG LoBM" not in headers:
        raise ValueError(f"BIG LoBM missing from FF25 headers: {headers}")
    big_growth_i = headers.index("BIG LoBM")

    ff3_map = {
        ym: (i, mkt)
        for i, (ym, mkt, _smb) in enumerate(ff3)
    }

    rows: list[dict[str, Any]] = []
    for i in range(5, len(r25)):
        ym, _ = r25[i]
        if ym not in ff3_map:
            continue
        fi, _ = ff3_map[ym]
        if fi < 5:
            continue

        p6 = [
            compounded(
                [r25[k][1][j] for k in range(i - 5, i + 1)]
            )
            for j in range(25)
        ]
        mkt6 = compounded(
            [ff3[k][1] for k in range(fi - 5, fi + 1)]
        )
        med = median25(p6)
        leader = max(p6)
        leader_gap = leader - med
        big_growth_gap = p6[big_growth_i] - med

        rows.append(
            {
                "source_month": ym,
                "portfolio_exhaustion_raw": (
                    1.0 - sum(x > mkt6 for x in p6) / 25.0
                ),
                "leader_gap_raw": leader_gap,
                "big_growth_gap_raw": big_growth_gap,
                "leadership_handoff_share": leadership_handoff_share(
                    leader_gap,
                    big_growth_gap,
                ),
                "leader_6m": leader,
                "big_growth_6m": p6[big_growth_i],
                "median_6m": med,
            }
        )

    for raw_name, score_name in (
        ("portfolio_exhaustion_raw", "portfolio_exhaustion_score"),
        ("leader_gap_raw", "leader_gap_score"),
        ("big_growth_gap_raw", "big_growth_gap_score"),
    ):
        vals = [float(x[raw_name]) for x in rows]
        for i, row in enumerate(rows):
            row[score_name] = expanding_pct(vals, i)

    for i, row in enumerate(rows):
        row["concentration_breadth_ng1"] = (
            float(row["portfolio_exhaustion_score"])
            * float(row["leader_gap_score"])
            * float(row["big_growth_gap_score"])
        ) ** (1.0 / 3.0)
        row["effective_history_months"] = i + 1
        row["effective_month"] = add_months(
            str(row["source_month"]),
            2,
        )

    return rows, {
        "source": "Kenneth R. French official current ZIPs",
        "ff25_last_month": r25[-1][0],
        "ff3_last_month": ff3[-1][0],
        "ff25_provenance": ff25_prov,
        "ff3_provenance": ff3_prov,
    }


def build_valuation_map(shiller: pd.DataFrame) -> dict[str, dict[str, float]]:
    x = shiller.copy().sort_values("date")
    scores = valuation_history(x["cape"].tolist())
    out: dict[str, dict[str, float]] = {}
    for (_, row), score in zip(x.iterrows(), scores):
        ym = pd.Timestamp(row["date"]).strftime("%Y%m")
        out[ym] = {
            "cape": float(row["cape"]),
            "score": float(score),
        }
    return out


def last_completed_month(now: datetime) -> str:
    x = pd.Timestamp(now.astimezone(timezone.utc)).tz_localize(None)
    prev = pd.Timestamp(year=x.year, month=x.month, day=1) - pd.offsets.MonthBegin(1)
    return prev.strftime("%Y%m")


def source_temporality(
    ff_source_month: str,
    shiller_source_month: str,
) -> dict[str, Any]:
    prereg = pd.Timestamp(PREREGISTRATION_DATE)

    def relation(ym: str) -> str:
        start = pd.Timestamp(
            year=int(ym[:4]),
            month=int(ym[4:6]),
            day=1,
        )
        end = start + pd.offsets.MonthEnd(1)
        if start > prereg:
            return "FULLY_POST_PREREGISTRATION"
        if start <= prereg <= end:
            return "STRADDLES_PREREGISTRATION_DATE"
        return "PRE_PREREGISTRATION"

    detail = {
        "fama_french": {
            "source_month": ff_source_month,
            "relation": relation(ff_source_month),
        },
        "shiller_cape": {
            "source_month": shiller_source_month,
            "relation": relation(shiller_source_month),
        },
    }
    fully_post = all(
        x["relation"] == "FULLY_POST_PREREGISTRATION"
        for x in detail.values()
    )
    return {
        "preregistration_date": PREREGISTRATION_DATE,
        "all_source_months_fully_post_preregistration": fully_post,
        "detail": detail,
    }


def build_snapshot(
    *,
    now: datetime,
    ff_rows: list[dict[str, Any]],
    ff_meta: dict[str, Any],
    shiller: pd.DataFrame,
    shiller_meta: dict[str, Any],
    spy: pd.Series,
) -> dict[str, Any]:
    completed = last_completed_month(now)
    eligible = [
        x for x in ff_rows
        if str(x["effective_month"]) <= completed
    ]
    if not eligible:
        raise ValueError("no completed Route_C NG2 state")
    row = eligible[-1]
    effective = str(row["effective_month"])
    if effective != completed:
        raise ValueError(
            "Route_C NG2 source data are stale for the latest completed "
            f"month: effective {effective} != completed {completed}"
        )

    val_month = add_months(effective, -1)
    val_map = build_valuation_map(shiller)
    if val_month not in val_map:
        raise ValueError(
            f"Shiller valuation month {val_month} is unavailable"
        )
    valuation = val_map[val_month]

    route_c_ng1 = math.sqrt(
        float(valuation["score"])
        * float(row["concentration_breadth_ng1"])
    )
    handoff = float(row["leadership_handoff_share"])
    price_gate = top_gate(spy, effective)

    gates = {
        "route_ge_85": bool(route_c_ng1 >= THRESHOLD),
        "handoff_ge_40pct": bool(handoff >= HANDOFF_MIN),
        "warmup_ge_120": bool(
            int(row["effective_history_months"]) >= WARMUP_MONTHS
        ),
        "top_location": price_gate,
    }
    armed = (
        gates["route_ge_85"]
        and gates["handoff_ge_40pct"]
        and gates["warmup_ge_120"]
        and price_gate["passes"]
    )

    counts = effective >= FIRST_PROSPECTIVE_EFFECTIVE_MONTH
    phase = (
        "POST_PREREGISTRATION_PROSPECTIVE"
        if counts
        else "RETROSPECTIVE_HYPOTHESIS_DIAGNOSTIC"
    )
    temporality = source_temporality(
        str(row["source_month"]),
        val_month,
    )
    if counts and not temporality[
        "all_source_months_fully_post_preregistration"
    ]:
        raise ValueError(
            "countable NG2 state does not have wholly post-preregistration "
            "source months"
        )

    return {
        "schema_version": "market-top-route-c-ng2-forward-1",
        "generated_at": now.astimezone(timezone.utc).isoformat(),
        "research_only": True,
        "production_effect": "none",
        "validation_status": "PROSPECTIVE_VALIDATION_PENDING",
        "effective_month": effective,
        "evidence_phase": phase,
        "counts_toward_prospective_validation": counts,
        "prospective_start_effective_month": (
            FIRST_PROSPECTIVE_EFFECTIVE_MONTH
        ),
        "source_months": {
            "fama_french": str(row["source_month"]),
            "shiller_cape": val_month,
        },
        "components": {
            "portfolio_exhaustion_score": float(
                row["portfolio_exhaustion_score"]
            ),
            "leader_gap_score": float(row["leader_gap_score"]),
            "big_growth_gap_score": float(
                row["big_growth_gap_score"]
            ),
            "concentration_breadth_ng1": float(
                row["concentration_breadth_ng1"]
            ),
            "leader_gap_raw": float(row["leader_gap_raw"]),
            "big_growth_gap_raw": float(
                row["big_growth_gap_raw"]
            ),
            "leadership_handoff_share": handoff,
            "leader_6m": float(row["leader_6m"]),
            "big_growth_6m": float(row["big_growth_6m"]),
            "median_6m": float(row["median_6m"]),
            "valuation": float(valuation["score"]),
            "cape": float(valuation["cape"]),
            "effective_history_months": int(
                row["effective_history_months"]
            ),
        },
        "route_c_ng1_score": float(route_c_ng1),
        "route_c_ng2_score": float(route_c_ng1),
        "gates": gates,
        "state": "ARMED" if armed else "IDLE",
        "source_temporality": temporality,
        "sources": {
            "fama_french": ff_meta,
            "shiller": {
                "source": shiller_meta.get("source"),
                "latest_date": shiller_meta.get("latest_date"),
            },
            "price": {
                "source": spy.attrs.get("source"),
                "payload_sha256": spy.attrs.get("payload_sha256"),
                "latest_date": spy.attrs.get("latest_date"),
            },
        },
        "governance": {
            "historical_validation_authorized": False,
            "production_promotion_authorized": False,
            "post_preregistration_tuning_allowed": False,
            "legacy_route_c_recovery": False,
        },
    }


def load_history(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    obj = json.loads(path.read_text(encoding="utf-8"))
    return list(obj.get("history") or [])


def write_outputs(snapshot: dict[str, Any]) -> None:
    OUT_CURRENT.parent.mkdir(parents=True, exist_ok=True)
    OUT_CURRENT.write_text(
        json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    hist = load_history(OUT_HISTORY)
    row = {
        "effective_month": snapshot["effective_month"],
        "generated_at": snapshot["generated_at"],
        "evidence_phase": snapshot["evidence_phase"],
        "counts_toward_prospective_validation": (
            snapshot["counts_toward_prospective_validation"]
        ),
        "route_c_ng2_score": snapshot["route_c_ng2_score"],
        "leadership_handoff_share": (
            snapshot["components"]["leadership_handoff_share"]
        ),
        "top_location": snapshot["gates"]["top_location"]["passes"],
        "state": snapshot["state"],
        "source_temporality": snapshot["source_temporality"],
    }
    by_month = {
        x.get("effective_month"): x
        for x in hist
        if x.get("effective_month")
    }
    by_month[row["effective_month"]] = row
    rows = [by_month[k] for k in sorted(by_month)]

    OUT_HISTORY.write_text(
        json.dumps(
            {
                "schema_version": "market-top-route-c-ng2-history-1",
                "research_only": True,
                "history": rows,
            },
            ensure_ascii=False,
            indent=2,
        ) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    now = datetime.now(timezone.utc)
    ff_rows, ff_meta = build_ff25_states()
    shiller, shiller_meta = fetch_shiller()
    spy = fetch_spy()

    snapshot = build_snapshot(
        now=now,
        ff_rows=ff_rows,
        ff_meta=ff_meta,
        shiller=shiller,
        shiller_meta=shiller_meta,
        spy=spy,
    )
    print(json.dumps(snapshot, ensure_ascii=False, indent=2))
    if not args.dry_run:
        write_outputs(snapshot)


if __name__ == "__main__":
    main()
