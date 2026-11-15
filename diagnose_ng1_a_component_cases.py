from __future__ import annotations

import argparse
import json
import math
from datetime import datetime, timezone

from audit_market_top_ng1_a_independent import (
    FF25_URL,
    FF12_URL,
    FF3_URL,
    BAA_URL,
    GS10_URL,
    unzip_csv,
    parse_portfolio_block,
    parse_ff3,
    compounded,
    expanding_pct,
    credit_snapshot_series,
)

TARGETS = {
    "1998-11": {"ff": "199809", "credit": "199810"},
    "2007-11": {"ff": "200709", "credit": "200710"},
    "2012-02": {"ff": "201112", "credit": "201201"},
}


def all_ff_rows():
    ff25_text = unzip_csv(FF25_URL)
    ff12_text = unzip_csv(FF12_URL)
    ff3_text = unzip_csv(FF3_URL)

    _, r25 = parse_portfolio_block(
        ff25_text, "Average Value Weighted Returns -- Monthly", 25
    )
    h12, r12 = parse_portfolio_block(
        ff12_text, "Average Value Weighted Returns -- Monthly", 12
    )
    ff3 = parse_ff3(ff3_text)

    money_i = h12.index("Money")
    ff3_map = {ym: (i, mkt, smb) for i, (ym, mkt, smb) in enumerate(ff3)}
    r12_map = {ym: (i, vals) for i, (ym, vals) in enumerate(r12)}

    rows = []
    for i in range(5, len(r25)):
        ym, _ = r25[i]
        if ym not in ff3_map or ym not in r12_map:
            continue
        fi, _, _ = ff3_map[ym]
        qi, _ = r12_map[ym]
        if fi < 5 or qi < 5:
            continue
        p6 = [
            compounded([r25[k][1][j] for k in range(i - 5, i + 1)])
            for j in range(25)
        ]
        mkt6 = compounded([ff3[k][1] for k in range(fi - 5, fi + 1)])
        money6 = compounded([r12[k][1][money_i] for k in range(qi - 5, qi + 1)])
        rows.append({
            "ym": ym,
            "exhaust_raw": 1.0 - sum(x > mkt6 for x in p6) / 25.0,
            "size_raw": -compounded([ff3[k][2] for k in range(fi - 5, fi + 1)]),
            "finance_raw": -(money6 - mkt6),
        })

    for raw_name, score_name in (
        ("exhaust_raw", "portfolio_exhaustion_score"),
        ("size_raw", "size_weakness_score"),
        ("finance_raw", "finance_weakness_score"),
    ):
        vals = [x[raw_name] for x in rows]
        for i, row in enumerate(rows):
            row[score_name] = expanding_pct(vals, i)
    return {x["ym"]: x for x in rows}


def all_credit_rows():
    baa = credit_snapshot_series(BAA_URL, "BAA")
    gs10 = credit_snapshot_series(GS10_URL, "GS10")
    common = sorted(set(baa.index) & set(gs10.index))
    levels = [
        (d.strftime("%Y%m"), float(baa.loc[d] - gs10.loc[d]))
        for d in common
    ]
    rows = []
    for i in range(6, len(levels)):
        raw = max(
            levels[i][1] - levels[i - 3][1],
            levels[i][1] - levels[i - 6][1],
        )
        rows.append({"ym": levels[i][0], "spread_shock_raw": raw})
    vals = [x["spread_shock_raw"] for x in rows]
    for i, row in enumerate(rows):
        row["spread_shock_score"] = expanding_pct(vals, i)
    return {x["ym"]: x for x in rows}


def route(parts):
    vals = [
        parts["spread_shock_score"],
        parts["finance_weakness_score"],
        parts["size_weakness_score"],
        parts["portfolio_exhaustion_score"],
    ]
    prod = math.prod(vals)
    return prod ** 0.25


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--output")
    args = ap.parse_args()

    ff = all_ff_rows()
    credit = all_credit_rows()
    cases = {}
    for effective, src in TARGETS.items():
        f = ff[src["ff"]]
        c = credit[src["credit"]]
        parts = {
            "spread_shock_score": float(c["spread_shock_score"]),
            "finance_weakness_score": float(f["finance_weakness_score"]),
            "size_weakness_score": float(f["size_weakness_score"]),
            "portfolio_exhaustion_score": float(f["portfolio_exhaustion_score"]),
        }
        cases[effective] = {
            "source_months": src,
            "components": parts,
            "route_a_ng1": route(parts),
            "component_min": min(parts.values()),
            "component_max": max(parts.values()),
            "finance_minus_spread": (
                parts["finance_weakness_score"] - parts["spread_shock_score"]
            ),
            "credit_pair_geometric": math.sqrt(
                parts["spread_shock_score"] * parts["finance_weakness_score"]
            ),
            "breadth_pair_geometric": math.sqrt(
                parts["size_weakness_score"] * parts["portfolio_exhaustion_score"]
            ),
        }

    result = {
        "schema_version": "market-top-ng1-a-case-component-diagnostic-1",
        "research_only": True,
        "production_effect": "none",
        "formula_changed": False,
        "purpose": (
            "Compare frozen NG1-A component structure across the 1998 false positive, "
            "2007 major-top hit, and 2012 correction-risk episode before any NG2 "
            "hypothesis is preregistered."
        ),
        "cases": cases,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    print(json.dumps(result, indent=2))
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2)
            f.write("\n")


if __name__ == "__main__":
    main()
