from __future__ import annotations

import argparse
import hashlib
import json
import math
import statistics
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
from market_top_ng3_forward import (
    add_months,
    build_credit_scores,
    completed_month_ym,
    fetch_credit,
    fetch_spy,
    top_gate,
    unzip_current_ff,
)
from update_market_top_shadow import (
    SHILLER_FEED,
    _get as shadow_get,
    parse_shiller_feed,
)

ROUTE_THRESHOLD = 85.0
CONCENTRATION_MIN = 85.0
SPREAD_MAX = 50.0
WARMUP_MONTHS = 120
VALUATION_CONTEXT_MONTHS = 120
FIRST_PROSPECTIVE_EFFECTIVE_MONTH = "202612"

OUT_CURRENT = Path("docs/data/market_top_route_c_ng3_current.json")
OUT_HISTORY = Path("docs/data/market_top_route_c_ng3_history.json")


def trailing_percentile_current(values: list[float], i: int, window: int) -> float | None:
    if i + 1 < window:
        return None
    xs = [float(x) for x in values[i - window + 1:i + 1]]
    cur = xs[-1]
    return 100.0 * sum(x <= cur for x in xs) / len(xs)


def build_concentration_rows() -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    ff25_text, ff25_prov = unzip_current_ff(FF25_URL)
    ff3_text, ff3_prov = unzip_current_ff(FF3_URL)

    headers, r25 = parse_portfolio_block(
        ff25_text,
        "Average Value Weighted Returns -- Monthly",
        25,
    )
    ff3 = parse_ff3(ff3_text)
    ff3_map = {ym: (i, mkt, smb) for i, (ym, mkt, smb) in enumerate(ff3)}

    big_growth_i = None
    for i, h in enumerate(headers):
        z = h.lower().replace(" ", "")
        if "big" in z and ("lobm" in z or "bm1" in z):
            big_growth_i = i
            break
    if big_growth_i is None:
        raise ValueError(f"BIG LoBM portfolio not found in headers: {headers}")

    rows: list[dict[str, Any]] = []
    for i in range(5, len(r25)):
        ym, _ = r25[i]
        if ym not in ff3_map:
            continue
        fi, _, _ = ff3_map[ym]
        if fi < 5:
            continue

        p6 = [
            compounded([r25[k][1][j] for k in range(i - 5, i + 1)])
            for j in range(25)
        ]
        mkt6 = compounded([ff3[k][1] for k in range(fi - 5, fi + 1)])
        med = float(statistics.median(p6))
        leader = float(max(p6))
        big = float(p6[big_growth_i])

        rows.append(
            {
                "source_month": ym,
                "portfolio_exhaustion_raw": (
                    1.0 - sum(x > mkt6 for x in p6) / 25.0
                ),
                "leader_gap_raw": leader - med,
                "big_growth_gap_raw": big - med,
            }
        )

    for raw_name, score_name in (
        ("portfolio_exhaustion_raw", "portfolio_exhaustion_score"),
        ("leader_gap_raw", "leader_gap_score"),
        ("big_growth_gap_raw", "big_growth_gap_score"),
    ):
        vals = [float(x[raw_name]) for x in rows]
        for i, row in enumerate(rows):
            row[score_name] = float(expanding_pct(vals, i))

    for i, row in enumerate(rows):
        row["concentration_breadth"] = (
            row["portfolio_exhaustion_score"]
            * row["leader_gap_score"]
            * row["big_growth_gap_score"]
        ) ** (1.0 / 3.0)
        row["big_growth_gap_change_3m"] = (
            None
            if i < 3
            else float(
                row["big_growth_gap_raw"]
                - rows[i - 3]["big_growth_gap_raw"]
            )
        )

    return (
        {x["source_month"]: x for x in rows},
        {
            "source": "Kenneth R. French official current ZIPs",
            "big_growth_header": headers[big_growth_i],
            "ff25_last_month": r25[-1][0],
            "ff3_last_month": ff3[-1][0],
            "ff25_provenance": ff25_prov,
            "ff3_provenance": ff3_prov,
        },
    )


def build_valuation_context_rows() -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    response = shadow_get(SHILLER_FEED, timeout=30)
    payload = response.content
    obj = response.json()
    df = parse_shiller_feed(obj).sort_values("date").reset_index(drop=True)

    capes = [float(x) for x in df["cape"].tolist()]
    rows: list[dict[str, Any]] = []
    for i, row in df.iterrows():
        score = trailing_percentile_current(
            capes, i, VALUATION_CONTEXT_MONTHS
        )
        if score is None:
            continue
        source_month = pd.Timestamp(row["date"]).strftime("%Y%m")
        rows.append(
            {
                "source_month": source_month,
                "cape": float(row["cape"]),
                "valuation_context_120": float(score),
            }
        )

    if not rows:
        raise ValueError("no 120-month Shiller valuation context rows")

    return (
        {x["source_month"]: x for x in rows},
        {
            "source": "Robert Shiller / Yale feed mirror",
            "url": SHILLER_FEED,
            "payload_sha256": hashlib.sha256(payload).hexdigest(),
            "latest_month": df.iloc[-1]["date"].strftime("%Y%m"),
        },
    )


def build_effective_states(
    concentration: dict[str, dict[str, Any]],
    valuation: dict[str, dict[str, Any]],
    credit: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    eff_ff = {add_months(k, 2): k for k in concentration}
    eff_val = {add_months(k, 1): k for k in valuation}
    eff_credit = {add_months(k, 1): k for k in credit}

    months = sorted(set(eff_ff) & set(eff_val) & set(eff_credit))
    rows: list[dict[str, Any]] = []

    for eff in months:
        fy = eff_ff[eff]
        vy = eff_val[eff]
        cy = eff_credit[eff]
        f = concentration[fy]
        v = valuation[vy]
        c = credit[cy]

        gap_change = f["big_growth_gap_change_3m"]
        context = float(v["valuation_context_120"])
        cb = float(f["concentration_breadth"])
        route = math.sqrt(context * cb)

        rows.append(
            {
                "effective_month": eff,
                "ff_source_month": fy,
                "cape_source_month": vy,
                "credit_source_month": cy,
                "effective_history_months": len(rows) + 1,
                "cape": float(v["cape"]),
                "valuation_context_120": context,
                "portfolio_exhaustion_score": float(
                    f["portfolio_exhaustion_score"]
                ),
                "leader_gap_score": float(f["leader_gap_score"]),
                "big_growth_gap_score": float(f["big_growth_gap_score"]),
                "concentration_breadth": cb,
                "big_growth_gap_change_3m": (
                    None if gap_change is None else float(gap_change)
                ),
                "spread_shock_raw": float(c["spread_shock_raw"]),
                "spread_shock_score": float(c["spread_shock_score"]),
                "route_c_ng3_score": float(route),
            }
        )
    return rows


def select_completed_state(
    states: list[dict[str, Any]],
    completed_month: str,
) -> dict[str, Any]:
    eligible = [
        x for x in states if x["effective_month"] <= completed_month
    ]
    if not eligible:
        raise ValueError("no completed Route_C NG3 state")
    x = eligible[-1]
    if x["effective_month"] != completed_month:
        raise ValueError(
            "Route_C NG3 monthly inputs are stale: "
            f"latest effective {x['effective_month']} != completed "
            f"{completed_month}"
        )
    return x


def build_snapshot(
    now: datetime | None = None,
    price: pd.Series | None = None,
) -> dict[str, Any]:
    now = now or datetime.now(timezone.utc)
    completed = completed_month_ym(now)

    concentration, ff_meta = build_concentration_rows()
    valuation, valuation_meta = build_valuation_context_rows()
    baa, gs10, credit_meta = fetch_credit(now)
    credit = build_credit_scores(baa, gs10)

    states = build_effective_states(concentration, valuation, credit)
    x = select_completed_state(states, completed)

    route_gate = x["route_c_ng3_score"] >= ROUTE_THRESHOLD
    warmup_gate = x["effective_history_months"] >= WARMUP_MONTHS
    concentration_gate = x["concentration_breadth"] >= CONCENTRATION_MIN
    spread_gate = x["spread_shock_score"] <= SPREAD_MAX
    gap_gate = (
        x["big_growth_gap_change_3m"] is not None
        and x["big_growth_gap_change_3m"] > 0.0
    )
    phase_gate = bool(
        warmup_gate
        and concentration_gate
        and spread_gate
        and gap_gate
    )

    price = price if price is not None else fetch_spy()
    location = top_gate(price, x["effective_month"])
    armed = bool(route_gate and phase_gate and location["passes"])

    prospective = (
        x["effective_month"] >= FIRST_PROSPECTIVE_EFFECTIVE_MONTH
    )
    evidence_phase = (
        "PROSPECTIVE"
        if prospective
        else "RETROSPECTIVE_TRAINING_DIAGNOSTIC"
    )

    return {
        "schema_version": "market-top-route-c-ng3-forward-1",
        "generated_at": now.astimezone(timezone.utc).isoformat(),
        "research_only": True,
        "production_effect": "none",
        "legacy_route_c_status": "UNRESOLVED",
        "validation_status": "PROSPECTIVE_VALIDATION_PENDING",
        "effective_month": x["effective_month"],
        "evidence_phase": evidence_phase,
        "counts_toward_prospective_validation": bool(prospective),
        "prospective_start_effective_month": (
            FIRST_PROSPECTIVE_EFFECTIVE_MONTH
        ),
        "source_months": {
            "fama_french": x["ff_source_month"],
            "cape": x["cape_source_month"],
            "credit": x["credit_source_month"],
        },
        "components": {
            "cape": x["cape"],
            "valuation_context_120": x["valuation_context_120"],
            "portfolio_exhaustion_score": x[
                "portfolio_exhaustion_score"
            ],
            "leader_gap_score": x["leader_gap_score"],
            "big_growth_gap_score": x["big_growth_gap_score"],
            "concentration_breadth": x["concentration_breadth"],
            "big_growth_gap_change_3m": x[
                "big_growth_gap_change_3m"
            ],
            "spread_shock_raw": x["spread_shock_raw"],
            "spread_shock_score": x["spread_shock_score"],
            "effective_history_months": x[
                "effective_history_months"
            ],
        },
        "route_c_ng3_score": x["route_c_ng3_score"],
        "gates": {
            "route_ge_85": bool(route_gate),
            "warmup_ge_120": bool(warmup_gate),
            "concentration_ge_85": bool(concentration_gate),
            "spread_shock_le_50": bool(spread_gate),
            "big_growth_gap_change_positive": bool(gap_gate),
            "phase_gate": bool(phase_gate),
            "top_location": location,
        },
        "state": "ARMED" if armed else "IDLE",
        "sources": {
            "fama_french": ff_meta,
            "valuation": valuation_meta,
            "credit": credit_meta,
            "price": {
                "source": price.attrs.get(
                    "source",
                    "Yahoo Finance SPY unadjusted Close",
                ),
                "payload_sha256": price.attrs.get("payload_sha256"),
                "latest_date": price.attrs.get("latest_date"),
            },
        },
        "governance": {
            "historical_validation_authorized": False,
            "production_promotion_authorized": False,
            "post_preregistration_tuning_allowed": False,
        },
    }


def _load_history(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    obj = json.loads(path.read_text(encoding="utf-8"))
    return list(obj.get("history") or [])


def write_outputs(snapshot: dict[str, Any]) -> None:
    OUT_CURRENT.parent.mkdir(parents=True, exist_ok=True)
    history = _load_history(OUT_HISTORY)

    row = {
        "effective_month": snapshot["effective_month"],
        "generated_at": snapshot["generated_at"],
        "evidence_phase": snapshot["evidence_phase"],
        "counts_toward_prospective_validation": snapshot[
            "counts_toward_prospective_validation"
        ],
        "route_c_ng3_score": snapshot["route_c_ng3_score"],
        "valuation_context_120": snapshot["components"][
            "valuation_context_120"
        ],
        "concentration_breadth": snapshot["components"][
            "concentration_breadth"
        ],
        "spread_shock_score": snapshot["components"][
            "spread_shock_score"
        ],
        "big_growth_gap_change_3m": snapshot["components"][
            "big_growth_gap_change_3m"
        ],
        "phase_gate": snapshot["gates"]["phase_gate"],
        "top_location": snapshot["gates"]["top_location"]["passes"],
        "state": snapshot["state"],
    }

    by_month = {
        str(x.get("effective_month")): x
        for x in history
        if x.get("effective_month")
    }
    by_month[row["effective_month"]] = row
    ordered = [by_month[k] for k in sorted(by_month)]

    OUT_CURRENT.write_text(
        json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    OUT_HISTORY.write_text(
        json.dumps(
            {
                "schema_version": (
                    "market-top-route-c-ng3-forward-history-1"
                ),
                "research_only": True,
                "production_effect": "none",
                "prospective_start_effective_month": (
                    FIRST_PROSPECTIVE_EFFECTIVE_MONTH
                ),
                "history": ordered,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    snapshot = build_snapshot()
    print(json.dumps(snapshot, ensure_ascii=False, indent=2))
    if not args.dry_run:
        write_outputs(snapshot)


if __name__ == "__main__":
    main()
