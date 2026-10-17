from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROUTE_B_PATH = Path("docs/data/market_top_shadow_current.json")
MASTER_TOP_PATH = Path("docs/data/master_top_v218.json")
OUT_CURRENT = Path("docs/data/market_top_cross_monitor_current.json")
OUT_HISTORY = Path("docs/data/market_top_cross_monitor_history.json")

ROUTE_B_THRESHOLD = 85.0
MASTER_TOP_THRESHOLD = 55.0
ROUTE_B_SCHEMA = "market-top-shadow-forward-1"
MASTER_TOP_VERSION = "MASTER-TOP-V2.1.8-FROZEN"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def master_top_live_status(payload: dict[str, Any]) -> tuple[bool, str]:
    latest = payload.get("latest") or {}
    status = str(latest.get("research_status") or "").lower()
    symbol = str(latest.get("price_symbol") or "")
    breadth_source = str(latest.get("breadth_source") or "")

    if payload.get("version") != MASTER_TOP_VERSION:
        return False, "MASTER_TOP_WRONG_VERSION"
    if payload.get("formula_frozen") is not True:
        return False, "MASTER_TOP_FORMULA_NOT_FROZEN"

    if "seed snapshot" in status or "proxy seed" in symbol.lower():
        return False, "MASTER_TOP_SEED_ONLY"

    asof = latest.get("asof")
    route = latest.get("supplemental_route")
    if not asof or route is None:
        return False, "MASTER_TOP_MISSING_LIVE_FIELDS"

    if symbol != "^GSPC":
        return False, "MASTER_TOP_NONCANONICAL_PRICE_SOURCE"
    if "MarketParquet stock_daily" not in breadth_source:
        return False, "MASTER_TOP_NONCANONICAL_BREADTH_SOURCE"
    if "frozen formula" not in status:
        return False, "MASTER_TOP_NONCANONICAL_RESEARCH_STATUS"

    return True, "MASTER_TOP_LIVE"


def route_b_live_status(payload: dict[str, Any]) -> tuple[bool, str]:
    if payload.get("schema_version") != ROUTE_B_SCHEMA:
        return False, "ROUTE_B_WRONG_SCHEMA"
    if payload.get("research_only") is not True:
        return False, "ROUTE_B_NOT_MARKED_RESEARCH_ONLY"

    asof = payload.get("asof")
    route = (payload.get("route_b") or {}).get("score")
    live_status = (
        (payload.get("full_legacy_model") or {}).get("route_b")
    )
    if not asof or route is None:
        return False, "ROUTE_B_MISSING_LIVE_FIELDS"
    if live_status != "RESOLVED":
        return False, "ROUTE_B_NOT_RESOLVED"
    return True, "ROUTE_B_LIVE"


def classify(
    route_b_payload: dict[str, Any],
    master_payload: dict[str, Any],
    *,
    generated_at: str | None = None,
) -> dict[str, Any]:
    rb_ok, rb_reason = route_b_live_status(route_b_payload)
    mt_ok, mt_reason = master_top_live_status(master_payload)

    rb_asof = route_b_payload.get("asof")
    mt_latest = master_payload.get("latest") or {}
    mt_asof = mt_latest.get("asof")

    reasons: list[str] = []
    if not rb_ok:
        reasons.append(rb_reason)
    if not mt_ok:
        reasons.append(mt_reason)
    if rb_asof and mt_asof and rb_asof != mt_asof:
        reasons.append("ASOF_MISMATCH")

    comparable = rb_ok and mt_ok and rb_asof == mt_asof

    rb_score = (route_b_payload.get("route_b") or {}).get("score")
    mt_score = mt_latest.get("supplemental_route")

    prospective_start = payload_start = master_payload.get("prospective_evidence_start")
    evidence_phase = None
    if comparable and rb_asof:
        if prospective_start and str(rb_asof) >= str(prospective_start):
            evidence_phase = "POST_FREEZE_PROSPECTIVE"
        else:
            evidence_phase = "PRE_FREEZE_ASOF_DIAGNOSTIC"

    out: dict[str, Any] = {
        "schema_version": "market-top-cross-monitor-2",
        "generated_at": generated_at or datetime.now(timezone.utc).isoformat(),
        "research_only": True,
        "production_effect": "none",
        "comparable": comparable,
        "evidence_phase": evidence_phase,
        "input_provenance": {
            "route_b_schema_version": route_b_payload.get("schema_version"),
            "master_top_version": master_payload.get("version"),
            "master_top_formula_frozen": master_payload.get("formula_frozen"),
            "master_top_prospective_start": prospective_start,
            "master_top_generated_at_utc": master_payload.get("generated_at_utc"),
        },
        "status": "COMPARABLE" if comparable else "NOT_COMPARABLE",
        "reasons": reasons,
        "route_b_shadow": {
            "asof": rb_asof,
            "score": rb_score,
            "threshold": ROUTE_B_THRESHOLD,
            "policy_path_state": (
                (route_b_payload.get("policy_path") or {}).get("state")
            ),
            "source_status": rb_reason,
        },
        "master_top_v218": {
            "asof": mt_asof,
            "score": mt_score,
            "threshold": MASTER_TOP_THRESHOLD,
            "triggered": mt_latest.get("route_triggered"),
            "source_status": mt_reason,
            "research_status": mt_latest.get("research_status"),
        },
        "comparison": None,
        "interpretation": (
            "Scores are not combined. The monitor only labels agreement or "
            "mechanism disagreement when both models are live on the same as-of date."
        ),
    }

    if comparable:
        rb_high = float(rb_score) >= ROUTE_B_THRESHOLD
        mt_high = float(mt_score) >= MASTER_TOP_THRESHOLD

        if rb_high and mt_high:
            label = "BOTH_HIGH"
        elif (not rb_high) and (not mt_high):
            label = "BOTH_LOW"
        elif mt_high:
            label = "MASTER_TOP_ONLY"
        else:
            label = "ROUTE_B_ONLY"

        out["comparison"] = {
            "label": label,
            "route_b_high": rb_high,
            "master_top_high": mt_high,
            "same_asof": rb_asof,
            "evidence_phase": evidence_phase,
            "ensemble_score": None,
            "action_signal": None,
        }

    return out


def load_history(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    obj = load_json(path)
    return list(obj.get("history") or [])


def write_outputs(result: dict[str, Any]) -> None:
    OUT_CURRENT.parent.mkdir(parents=True, exist_ok=True)
    OUT_CURRENT.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    hist = load_history(OUT_HISTORY)
    comparison_label = (result.get("comparison") or {}).get("label")
    key = "|".join(
        [
            str(result["route_b_shadow"].get("asof")),
            str(result["master_top_v218"].get("asof")),
            str(result["route_b_shadow"].get("source_status")),
            str(result["master_top_v218"].get("source_status")),
            str(comparison_label),
        ]
    )
    row = {
        "key": key,
        "generated_at": result["generated_at"],
        "comparable": result["comparable"],
        "status": result["status"],
        "reasons": result["reasons"],
        "route_b_asof": result["route_b_shadow"].get("asof"),
        "route_b_score": result["route_b_shadow"].get("score"),
        "master_top_asof": result["master_top_v218"].get("asof"),
        "master_top_score": result["master_top_v218"].get("score"),
        "comparison": comparison_label,
        "evidence_phase": result.get("evidence_phase"),
        "route_b_source_status": result["route_b_shadow"].get("source_status"),
        "master_top_source_status": result["master_top_v218"].get("source_status"),
    }

    by_key = {x.get("key"): x for x in hist if x.get("key")}
    by_key[key] = row
    rows = sorted(by_key.values(), key=lambda x: x.get("generated_at") or "")
    OUT_HISTORY.write_text(
        json.dumps(
            {
                "schema_version": "market-top-cross-monitor-history-1",
                "research_only": True,
                "history": rows[-500:],
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

    route_b = load_json(ROUTE_B_PATH)
    master = load_json(MASTER_TOP_PATH)
    result = classify(route_b, master)
    print(json.dumps(result, ensure_ascii=False, indent=2))

    if not args.dry_run:
        write_outputs(result)


if __name__ == "__main__":
    main()
