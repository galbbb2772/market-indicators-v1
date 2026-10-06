from __future__ import annotations

import io
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

import numpy as np
import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

# Resilient FRED patch copied from the repository's established ablation runner
# wrapper so a transient multi-series timeout does not silently erase macro inputs.
_ORIGINAL_GET = requests.sessions.Session.get

def _single_fred(self, url: str, sid: str, **kwargs):
    parsed = urlparse(url)
    query = parse_qs(parsed.query)
    query["id"] = [sid]
    single_url = urlunparse(parsed._replace(query=urlencode({k: v[-1] for k, v in query.items()})))
    last = None
    for attempt in range(3):
        try:
            kw = dict(kwargs); kw["timeout"] = (5, 25)
            r = _ORIGINAL_GET(self, single_url, **kw)
            r.raise_for_status()
            df = pd.read_csv(io.StringIO(r.text))
            date_col = df.columns[0]
            value_col = sid if sid in df.columns else df.columns[1]
            out = df[[date_col, value_col]].copy()
            out.columns = ["DATE", sid]
            return out
        except Exception as exc:
            last = exc
            if attempt < 2:
                time.sleep(1.5 * (attempt + 1))
    raise last or RuntimeError(f"FRED {sid}: request failed")

def resilient_get(self, url, **kwargs):
    if not isinstance(url, str) or "fred.stlouisfed.org/graph/fredgraph.csv" not in url:
        return _ORIGINAL_GET(self, url, **kwargs)
    parsed = urlparse(url)
    ids = (parse_qs(parsed.query).get("id") or [""])[-1]
    series_ids = [x.strip() for x in ids.split(",") if x.strip()]
    last = None
    for attempt in range(2):
        try:
            kw = dict(kwargs); kw["timeout"] = (5, 20)
            r = _ORIGINAL_GET(self, url, **kw)
            if r.ok:
                return r
            last = RuntimeError(f"FRED HTTP {r.status_code}")
        except Exception as exc:
            last = exc
        if attempt == 0:
            time.sleep(1.0)
    if len(series_ids) > 1:
        merged = None
        for sid in series_ids:
            try:
                one = _single_fred(self, url, sid, **kwargs)
                merged = one if merged is None else merged.merge(one, on="DATE", how="outer")
            except Exception:
                continue
        if merged is not None:
            response = requests.Response()
            response.status_code = 200
            response.url = url
            response.encoding = "utf-8"
            response._content = merged.sort_values("DATE").to_csv(index=False).encode("utf-8")
            return response
    raise last or RuntimeError("FRED request failed")

requests.sessions.Session.get = resilient_get

import ablation_runner as abl

DATA = ROOT / "docs" / "data"
PRUNE = DATA / "indicator_pruning_v1_summary.json"
OUT = DATA / "indicator_pruning_score_ab_v1.json"
OOS_START = pd.Timestamp("2022-01-01")

CANDIDATE_ORDER = [
    "high_yield",
    "business_cycle",
    "employment",
    "geopolitical_risk",
    "market_overextension",
    "money_making_effect",
    "sme_survival_growth",
    "yield_curve",
]


def future_10d(close):
    return (close.shift(-10) / close - 1.0) * 100.0


def spearman(a, b):
    z = pd.concat([a.rename("a"), b.rename("b")], axis=1).dropna()
    if len(z) < 100:
        return None
    r = z["a"].rank().corr(z["b"].rank())
    return None if pd.isna(r) else float(r)


def eval_state(state, close):
    return {
        "risk": abl.split_metrics(state, close),
        "fwd10_full": spearman(state, future_10d(close).reindex(state.index)),
        "fwd10_oos": spearman(
            state[state.index >= OOS_START],
            future_10d(close).reindex(state.index[state.index >= OOS_START]),
        ),
    }


def compare(base_state, test_state, base_eval, test_eval):
    z = pd.concat([base_state.rename("base"), test_state.rename("test")], axis=1).dropna()
    d = z["test"] - z["base"]

    def metric_delta(block, key):
        a = test_eval["risk"][block].get(key)
        b = base_eval["risk"][block].get(key)
        return None if a is None or b is None else float(a) - float(b)

    corr = float(z["base"].corr(z["test"]))
    oos_obj = metric_delta("oos_2022_present", "objective")
    oos_sep = metric_delta("oos_2022_present", "quartile_worst20_separation_pct")
    full_obj = metric_delta("full", "objective")
    full_sep = metric_delta("full", "quartile_worst20_separation_pct")
    result = {
        "n": int(len(z)),
        "score_corr": round(corr, 6),
        "mean_abs_score_diff": round(float(d.abs().mean()), 4),
        "p95_abs_score_diff": round(float(d.abs().quantile(.95)), 4),
        "full_objective_delta": None if full_obj is None else round(full_obj, 4),
        "oos_objective_delta": None if oos_obj is None else round(oos_obj, 4),
        "full_risk_separation_delta_pct": None if full_sep is None else round(full_sep, 4),
        "oos_risk_separation_delta_pct": None if oos_sep is None else round(oos_sep, 4),
        "full_fwd10_ic_delta": None if base_eval["fwd10_full"] is None or test_eval["fwd10_full"] is None else round(test_eval["fwd10_full"] - base_eval["fwd10_full"], 4),
        "oos_fwd10_ic_delta": None if base_eval["fwd10_oos"] is None or test_eval["fwd10_oos"] is None else round(test_eval["fwd10_oos"] - base_eval["fwd10_oos"], 4),
    }
    # Conservative score-preservation gate. Small positive/negative wiggles are fine,
    # but the OOS risk objective may not materially deteriorate.
    result["passes"] = bool(
        corr >= 0.95
        and (oos_obj is not None and oos_obj >= -0.50)
        and (oos_sep is not None and oos_sep >= -0.15)
    )
    return result


def state_for(model, active, store, ordered, idx):
    return abl.historical_state(model, active, store, ordered, idx)


def main():
    pruning = json.loads(PRUNE.read_text(encoding="utf-8"))

    ns, cap = abl.run_update_and_capture()
    if not cap:
        raise RuntimeError("No ablation capture generated")
    model = ns["MODEL"]
    store = cap["series_store"]
    mk = cap["mk"]
    ordered = cap["ordered"]
    item_by_id = {x["id"]: x for x in ordered}

    current_all = list(model.get("active", []))
    current = []
    zero_polarity = []
    for m in current_all:
        pol = float((item_by_id.get(m["id"]) or {}).get("impact_polarity", 0) or 0)
        if pol == 0:
            zero_polarity.append(m["id"])
        else:
            current.append(m)

    close = mk["SPY"]["Close"].dropna().sort_index()
    idx = close.index
    base_state = state_for(model, current, store, ordered, idx)
    base_eval = eval_state(base_state, close)

    single = {}
    for m in current:
        test = [x for x in current if x["id"] != m["id"]]
        st = state_for(model, test, store, ordered, idx)
        ev = eval_state(st, close)
        single[m["id"]] = compare(base_state, st, base_eval, ev)

    accepted = []
    rejected = []
    stages = []
    for cid in CANDIDATE_ORDER:
        if cid not in {x["id"] for x in current}:
            continue
        trial_removed = accepted + [cid]
        trial = [x for x in current if x["id"] not in set(trial_removed)]
        st = state_for(model, trial, store, ordered, idx)
        ev = eval_state(st, close)
        cmp = compare(base_state, st, base_eval, ev)
        stages.append({"candidate": cid, "trial_removed": trial_removed, "comparison": cmp})
        if cmp["passes"]:
            accepted.append(cid)
        else:
            rejected.append(cid)

    final_active = [x["id"] for x in current if x["id"] not in set(accepted)]
    final_state = state_for(model, [x for x in current if x["id"] in set(final_active)], store, ordered, idx)
    final_eval = eval_state(final_state, close)
    final_cmp = compare(base_state, final_state, base_eval, final_eval)

    payload = {
        "schema": "INDICATOR-PRUNING-SCORE-PRESERVATION-AB-V2",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "sample_start": str(base_state.index.min().date()),
        "sample_end": str(base_state.index.max().date()),
        "oos_start": str(OOS_START.date()),
        "research_only": True,
        "production_effect": "none",
        "current_directional_active_count": len(current),
        "current_directional_ids": [x["id"] for x in current],
        "zero_polarity_active_to_context": zero_polarity,
        "single_removal_tests": single,
        "greedy_candidate_order": CANDIDATE_ORDER,
        "greedy_stages": stages,
        "accepted_removals": accepted,
        "rejected_removals": rejected,
        "final_active_ids": final_active,
        "final_active_count": len(final_active),
        "final_comparison": final_cmp,
        "baseline_evaluation": base_eval,
        "final_evaluation": final_eval,
        "guardrails": {
            "raw_history_deleted": False,
            "production_changed": False,
            "acceptance_gate": "score corr>=0.95; OOS objective delta>=-0.50; OOS risk-separation delta>=-0.15pp",
            "note": "A removal can be statistically interesting yet remain rejected if the cumulative score-preservation gate fails.",
        },
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({
        "sample": [payload["sample_start"], payload["sample_end"]],
        "zero_polarity_to_context": zero_polarity,
        "single_safe": [k for k,v in single.items() if v["passes"]],
        "accepted_removals": accepted,
        "rejected_removals": rejected,
        "final_active_count": len(final_active),
        "final_active": final_active,
        "final_comparison": final_cmp,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
