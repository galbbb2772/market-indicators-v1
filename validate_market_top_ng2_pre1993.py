from __future__ import annotations

import argparse
import json
import math
from datetime import datetime, timezone

import pandas as pd

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
    get,
)

THRESHOLD = 85.0
HOLDOUT_END = "199212"
OUTCOME_SESSIONS = 252


def add_months(ym: str, n: int) -> str:
    y = int(ym[:4])
    m = int(ym[4:6]) - 1 + n
    y += m // 12
    m %= 12
    return f"{y:04d}{m+1:02d}"


def build_ff_scores() -> dict[str, dict]:
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

    rows: list[dict] = []
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
        money6 = compounded(
            [r12[k][1][money_i] for k in range(qi - 5, qi + 1)]
        )
        rows.append(
            {
                "ym": ym,
                "portfolio_exhaustion_raw": (
                    1.0 - sum(x > mkt6 for x in p6) / 25.0
                ),
                "size_weakness_raw": -compounded(
                    [ff3[k][2] for k in range(fi - 5, fi + 1)]
                ),
                "finance_weakness_raw": -(money6 - mkt6),
            }
        )

    for raw_name, score_name in (
        ("portfolio_exhaustion_raw", "portfolio_exhaustion_score"),
        ("size_weakness_raw", "size_weakness_score"),
        ("finance_weakness_raw", "finance_weakness_score"),
    ):
        vals = [x[raw_name] for x in rows]
        for i, row in enumerate(rows):
            row[score_name] = expanding_pct(vals, i)

    return {x["ym"]: x for x in rows}


def build_credit_scores() -> dict[str, dict]:
    baa = credit_snapshot_series(BAA_URL, "BAA")
    gs10 = credit_snapshot_series(GS10_URL, "GS10")
    common = sorted(set(baa.index) & set(gs10.index))
    levels = [
        (d.strftime("%Y%m"), float(baa.loc[d] - gs10.loc[d]))
        for d in common
    ]
    rows: list[dict] = []
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


def build_effective_states(ff: dict[str, dict], credit: dict[str, dict]) -> list[dict]:
    effective_months = sorted(
        set(add_months(ym, 2) for ym in ff)
        & set(add_months(ym, 1) for ym in credit)
    )
    rows: list[dict] = []
    for eff in effective_months:
        ff_ym = add_months(eff, -2)
        cr_ym = add_months(eff, -1)
        f = ff.get(ff_ym)
        c = credit.get(cr_ym)
        if not f or not c:
            continue

        parts = {
            "spread_shock_score": float(c["spread_shock_score"]),
            "finance_weakness_score": float(f["finance_weakness_score"]),
            "size_weakness_score": float(f["size_weakness_score"]),
            "portfolio_exhaustion_score": float(
                f["portfolio_exhaustion_score"]
            ),
        }
        route_ng1 = math.prod(parts.values()) ** 0.25
        lead_raw = (
            parts["finance_weakness_score"]
            - parts["spread_shock_score"]
        )
        rows.append(
            {
                "effective_month": eff,
                "ff_source_month": ff_ym,
                "credit_source_month": cr_ym,
                **parts,
                "route_a_ng1": route_ng1,
                "financial_lead_gap_raw": lead_raw,
            }
        )

    lead_vals = [x["financial_lead_gap_raw"] for x in rows]
    for i, row in enumerate(rows):
        row["financial_lead_gap_score"] = expanding_pct(lead_vals, i)
        row["route_a_ng2"] = math.sqrt(
            row["route_a_ng1"] * row["financial_lead_gap_score"]
        )
    return rows


def fetch_sp500(start="1950-01-01", end="1994-12-31") -> pd.Series:
    p1 = int(pd.Timestamp(start, tz="UTC").timestamp())
    p2 = int((pd.Timestamp(end, tz="UTC") + pd.Timedelta(days=1)).timestamp())
    url = (
        "https://query1.finance.yahoo.com/v8/finance/chart/%5EGSPC"
        f"?period1={p1}&period2={p2}&interval=1d&events=history"
        "&includeAdjustedClose=false"
    )
    last = None
    for host in ("query1.finance.yahoo.com", "query2.finance.yahoo.com"):
        try:
            r = get(url.replace("query1.finance.yahoo.com", host))
            obj = r.json()["chart"]["result"][0]
            ts = obj["timestamp"]
            close = obj["indicators"]["quote"][0]["close"]
            s = pd.Series(
                pd.to_numeric(close, errors="coerce"),
                index=pd.to_datetime(ts, unit="s", utc=True)
                .tz_convert(None)
                .normalize(),
                dtype=float,
            ).dropna().sort_index()
            if len(s) < 5000:
                raise ValueError(f"^GSPC history too short: {len(s)}")
            return s
        except Exception as exc:
            last = exc
    raise RuntimeError(f"^GSPC fetch failed: {last!r}")


def month_gate(price: pd.Series, ym: str) -> dict | None:
    y, m = int(ym[:4]), int(ym[4:6])
    start = pd.Timestamp(year=y, month=m, day=1)
    end = start + pd.offsets.MonthEnd(1)
    month = price.loc[(price.index >= start) & (price.index <= end)]
    if month.empty:
        return None
    asof = pd.Timestamp(month.index[-1])
    close = float(month.iloc[-1])
    window = price.loc[
        (price.index >= asof - pd.DateOffset(months=24))
        & (price.index <= asof)
    ]
    if window.empty:
        return None
    high = float(window.max())
    high_date = pd.Timestamp(window.idxmax())
    within = close >= 0.95 * high
    recent = high_date >= asof - pd.DateOffset(months=3)
    return {
        "asof": asof,
        "close": close,
        "high24": high,
        "high24_date": high_date,
        "within_5pct": bool(within),
        "high_within_3m": bool(recent),
        "passes": bool(within and recent),
    }


def collapse_episodes(rows: list[dict]) -> list[list[dict]]:
    episodes: list[list[dict]] = []
    cur: list[dict] = []
    prev = None
    for row in rows:
        if not row["armed"]:
            if cur:
                episodes.append(cur)
                cur = []
            prev = row["effective_month"]
            continue
        if cur and prev is not None and add_months(prev, 1) != row["effective_month"]:
            episodes.append(cur)
            cur = []
        cur.append(row)
        prev = row["effective_month"]
    if cur:
        episodes.append(cur)
    return episodes


def classify_outcome(price: pd.Series, anchor: pd.Timestamp) -> dict | None:
    after = price.loc[price.index > anchor]
    if len(after) < OUTCOME_SESSIONS:
        return None
    path = after.iloc[:OUTCOME_SESSIONS]
    anchor_close = float(price.loc[anchor])
    end_close = float(path.iloc[-1])
    forward = (end_close / anchor_close - 1.0) * 100.0
    worst = (float(path.min()) / anchor_close - 1.0) * 100.0
    running_high = path.cummax()
    dd = (path / running_high - 1.0) * 100.0
    max_dd = float(dd.min())

    if worst <= -15.0:
        label = "MAJOR_TOP"
    elif worst > -7.5 and forward > 0.0:
        label = "CLEAR_FALSE"
    else:
        label = "CORRECTION_OR_AMBIGUOUS"

    return {
        "end_date": path.index[-1].date().isoformat(),
        "forward_return_pct": forward,
        "worst_return_from_anchor_pct": worst,
        "max_peak_to_trough_dd_pct": max_dd,
        "classification": label,
    }


def evaluate() -> dict:
    ff = build_ff_scores()
    credit = build_credit_scores()
    states = build_effective_states(ff, credit)
    price = fetch_sp500()

    holdout = []
    for row in states:
        if row["effective_month"] > HOLDOUT_END:
            continue
        gate = month_gate(price, row["effective_month"])
        if gate is None:
            continue
        x = dict(row)
        x["top_location"] = {
            "asof": gate["asof"].date().isoformat(),
            "close": gate["close"],
            "high24": gate["high24"],
            "high24_date": gate["high24_date"].date().isoformat(),
            "within_5pct": gate["within_5pct"],
            "high_within_3m": gate["high_within_3m"],
            "passes": gate["passes"],
        }
        x["armed"] = bool(
            x["route_a_ng2"] >= THRESHOLD and gate["passes"]
        )
        holdout.append(x)

    eps = collapse_episodes(holdout)
    results = []
    for ep in eps:
        first = ep[0]
        anchor = pd.Timestamp(first["top_location"]["asof"])
        outcome = classify_outcome(price, anchor)
        results.append(
            {
                "start_month": first["effective_month"],
                "end_month": ep[-1]["effective_month"],
                "max_route_a_ng2": max(x["route_a_ng2"] for x in ep),
                "first_month_route_a_ng2": first["route_a_ng2"],
                "first_month_route_a_ng1": first["route_a_ng1"],
                "first_month_financial_lead_gap_raw": (
                    first["financial_lead_gap_raw"]
                ),
                "first_month_financial_lead_gap_score": (
                    first["financial_lead_gap_score"]
                ),
                "anchor": first["top_location"],
                "outcome_252": outcome,
            }
        )

    evaluable = [x for x in results if x["outcome_252"] is not None]
    major = sum(
        x["outcome_252"]["classification"] == "MAJOR_TOP"
        for x in evaluable
    )
    false = sum(
        x["outcome_252"]["classification"] == "CLEAR_FALSE"
        for x in evaluable
    )
    n = len(evaluable)
    major_share = major / n if n else 0.0
    false_share = false / n if n else 0.0
    passes = (
        n >= 2
        and major_share >= 0.50
        and false_share <= 0.25
    )

    return {
        "schema_version": "market-top-route-a-ng2-pre1993-holdout-1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "research_only": True,
        "production_effect": "none",
        "preregistration": "market-top-route-a-ng2-preregistration-1",
        "sample": {
            "first_effective_month": (
                holdout[0]["effective_month"] if holdout else None
            ),
            "last_effective_month": (
                holdout[-1]["effective_month"] if holdout else None
            ),
            "months": len(holdout),
            "price_source": "Yahoo Finance ^GSPC unadjusted Close",
            "ff_source": "official Kenneth R. French live ZIPs",
            "credit_source": (
                "Snow-Ouyang/Market-Regime-Clustering pinned immutable "
                "BAA/GS10 snapshots"
            ),
        },
        "formula": {
            "route_a_ng2": "sqrt(route_a_ng1*financial_lead_gap_score)",
            "threshold": THRESHOLD,
        },
        "episodes": results,
        "decision_metrics": {
            "evaluable_episodes": n,
            "major_top_count": major,
            "clear_false_count": false,
            "major_top_share": major_share,
            "clear_false_share": false_share,
            "minimum_evaluable_episodes": 2,
            "minimum_major_top_share": 0.50,
            "maximum_clear_false_share": 0.25,
        },
        "decision": (
            "ACCEPT_RESEARCH_SCREENING_CANDIDATE"
            if passes
            else "REJECT_NG2_TOP_ROUTE"
        ),
        "post_validation_tuning_allowed": False,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output")
    args = ap.parse_args()
    x = evaluate()
    print(json.dumps(x, indent=2))
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(x, f, indent=2)
            f.write("\n")


if __name__ == "__main__":
    main()
