from __future__ import annotations

import argparse
import io
import json
import math
import time
import zipfile
from datetime import datetime, timezone

import pandas as pd
import requests

FF25_URL = (
    "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/"
    "25_Portfolios_5x5_CSV.zip"
)
FF12_URL = (
    "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/"
    "12_Industry_Portfolios_CSV.zip"
)
FF3_URL = (
    "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/"
    "F-F_Research_Data_Factors_CSV.zip"
)

CREDIT_SNAPSHOT_COMMIT = "71af02cba3493ffa15ac47f512dc346598f2e23f"
CREDIT_BASE = (
    "https://raw.githubusercontent.com/Snow-Ouyang/"
    "Market-Regime-Clustering/"
    + CREDIT_SNAPSHOT_COMMIT
    + "/"
)
BAA_URL = CREDIT_BASE + "data_raw/macro/Credit/BAA.csv"
GS10_URL = CREDIT_BASE + "data_raw/macro/rate/GS10.csv"

TARGET_FF_MONTH = "200709"
TARGET_SPREAD_MONTH = "200710"
EFFECTIVE_MONTH = "200711"
THRESHOLD = 85.0

EXPECTED_BAA_200710 = 6.48
EXPECTED_GS10_200710 = 4.53
EXPECTED_SPREAD_SHOCK_RAW = 0.30
EXPECTED_SPREAD_SHOCK_SCORE = 75.80893682588598

UA = "market-top-ng1-a-independent-audit/1.0"
HTTP = requests.Session()
HTTP.headers.update({"User-Agent": UA})


def get(url: str, **kwargs) -> requests.Response:
    last = None
    for delay in (0, 2, 5):
        if delay:
            time.sleep(delay)
        try:
            r = HTTP.get(url, timeout=45, **kwargs)
            r.raise_for_status()
            return r
        except Exception as exc:
            last = exc
    raise RuntimeError(f"request failed: {url}: {last!r}")


def unzip_csv(url: str) -> str:
    raw = get(url).content
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        names = [n for n in z.namelist() if n.lower().endswith(".csv")]
        if not names:
            raise ValueError(f"no CSV in {url}")
        return z.read(names[0]).decode("utf-8", "replace")


def parse_portfolio_block(text: str, label: str, ncols: int):
    lines = text.splitlines()
    start = next(i for i, x in enumerate(lines) if label in x)
    headers = [x.strip() for x in lines[start + 1].split(",")[1:]]
    rows = []
    for raw in lines[start + 2:]:
        p = [x.strip() for x in raw.split(",")]
        if not p or len(p[0]) != 6 or not p[0].isdigit():
            break
        vals = [float(x) for x in p[1:1 + ncols]]
        if len(vals) == ncols:
            rows.append((p[0], vals))
    return headers, rows


def parse_ff3(text: str):
    rows = []
    for raw in text.splitlines():
        p = [x.strip() for x in raw.split(",")]
        if p and len(p[0]) == 6 and p[0].isdigit() and len(p) >= 5:
            try:
                # Market total return = Mkt-RF + RF.
                rows.append((p[0], float(p[1]) + float(p[4]), float(p[2])))
            except ValueError:
                pass
    return rows


def compounded(xs):
    p = 1.0
    for x in xs:
        p *= 1.0 + float(x) / 100.0
    return (p - 1.0) * 100.0


def expanding_pct(values, i):
    v = float(values[i])
    hist = values[: i + 1]
    return 100.0 * sum(float(x) <= v for x in hist) / len(hist)


def ff_scores():
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
        money6 = compounded(
            [r12[k][1][money_i] for k in range(qi - 5, qi + 1)]
        )

        rows.append(
            {
                "ym": ym,
                "exhaust_raw": 1.0 - sum(x > mkt6 for x in p6) / 25.0,
                "size_raw": -compounded(
                    [ff3[k][2] for k in range(fi - 5, fi + 1)]
                ),
                "finance_raw": -(money6 - mkt6),
            }
        )

    for raw_name, score_name in (
        ("exhaust_raw", "exhaust_score"),
        ("size_raw", "size_score"),
        ("finance_raw", "finance_score"),
    ):
        values = [x[raw_name] for x in rows]
        for i, row in enumerate(rows):
            row[score_name] = expanding_pct(values, i)

    target = next(x for x in rows if x["ym"] == TARGET_FF_MONTH)
    return target, {
        "ff25_url": FF25_URL,
        "ff12_url": FF12_URL,
        "ff3_url": FF3_URL,
        "ff25_last_month": r25[-1][0],
        "ff12_last_month": r12[-1][0],
        "ff3_last_month": ff3[-1][0],
    }


def parse_monthly_snapshot(text: str, value_col: str) -> pd.Series:
    df = pd.read_csv(io.StringIO(text), dtype=str)
    if df.empty:
        raise ValueError("empty monthly snapshot")
    dcol = next((x for x in df.columns if "date" in x.lower()), df.columns[0])
    if value_col not in df.columns:
        raise ValueError(f"{value_col} missing: {list(df.columns)}")

    idx = pd.to_datetime(df[dcol], errors="coerce")
    raw = df[value_col].astype(str).str.strip()
    vals = pd.to_numeric(raw.where(~raw.isin(["", ".", "NA", "N/A"])), errors="coerce")
    s = pd.Series(vals.to_numpy(), index=idx, name=value_col).dropna().sort_index()
    s = s[~s.index.duplicated(keep="last")]
    if len(s) < 500:
        raise ValueError(f"{value_col} monthly snapshot too short: {len(s)}")
    return s


def credit_snapshot_series(url: str, value_col: str) -> pd.Series:
    return parse_monthly_snapshot(get(url).text, value_col)


def spread_score():
    baa = credit_snapshot_series(BAA_URL, "BAA")
    gs10 = credit_snapshot_series(GS10_URL, "GS10")

    target_date = pd.Timestamp("2007-10-01")
    target_baa = float(baa.loc[target_date])
    target_gs10 = float(gs10.loc[target_date])

    if not math.isclose(target_baa, EXPECTED_BAA_200710, abs_tol=1e-12):
        raise ValueError(
            f"independent BAA parity failed: {target_baa} != {EXPECTED_BAA_200710}"
        )
    if not math.isclose(target_gs10, EXPECTED_GS10_200710, abs_tol=1e-12):
        raise ValueError(
            f"independent GS10 parity failed: {target_gs10} != {EXPECTED_GS10_200710}"
        )

    common = sorted(set(baa.index) & set(gs10.index))
    rows = [
        (d.strftime("%Y%m"), float(baa.loc[d] - gs10.loc[d]))
        for d in common
    ]

    shocks = []
    for i in range(6, len(rows)):
        raw = max(
            rows[i][1] - rows[i - 3][1],
            rows[i][1] - rows[i - 6][1],
        )
        shocks.append({"ym": rows[i][0], "raw": raw})

    values = [x["raw"] for x in shocks]
    for i, row in enumerate(shocks):
        row["score"] = expanding_pct(values, i)

    target = next(x for x in shocks if x["ym"] == TARGET_SPREAD_MONTH)
    if not math.isclose(
        target["raw"], EXPECTED_SPREAD_SHOCK_RAW, abs_tol=1e-10
    ):
        raise ValueError(f"spread-shock raw parity failed: {target['raw']}")
    if not math.isclose(
        target["score"], EXPECTED_SPREAD_SHOCK_SCORE, abs_tol=1e-10
    ):
        raise ValueError(f"spread-shock percentile parity failed: {target['score']}")

    return {
        **target,
        "baa": target_baa,
        "gs10": target_gs10,
        "history_start": common[0].date().isoformat(),
        "history_end": common[-1].date().isoformat(),
    }


def yahoo_spy():
    start = int(pd.Timestamp("2005-11-01", tz="UTC").timestamp())
    end = int(pd.Timestamp("2007-12-02", tz="UTC").timestamp())
    url = (
        "https://query1.finance.yahoo.com/v8/finance/chart/SPY"
        f"?period1={start}&period2={end}&interval=1d&events=history"
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
            ).dropna().sort_index()
            return s
        except Exception as exc:
            last = exc

    raise RuntimeError(f"SPY fetch failed: {last!r}")


def top_gate():
    s = yahoo_spy()
    month = s.loc["2007-11-01":"2007-11-30"]
    if month.empty:
        raise ValueError("no Nov-2007 SPY close")

    asof = month.index[-1]
    close = float(month.iloc[-1])
    window = s.loc[asof - pd.DateOffset(months=24):asof]
    high = float(window.max())
    high_date = pd.Timestamp(window.idxmax())

    within = close >= 0.95 * high
    recent = high_date >= asof - pd.DateOffset(months=3)

    return {
        "asof": asof.date().isoformat(),
        "close": close,
        "high24": high,
        "high24_date": high_date.date().isoformat(),
        "within_5pct": bool(within),
        "high_within_3m": bool(recent),
        "passes": bool(within and recent),
    }


def audit():
    ff, ff_sources = ff_scores()
    spread = spread_score()
    gate = top_gate()

    credit = math.sqrt(spread["score"] * ff["finance_score"])
    breadth = math.sqrt(ff["size_score"] * ff["exhaust_score"])
    route = math.sqrt(credit * breadth)

    return {
        "schema_version": "market-top-route-a-ng1-independent-audit-1",
        "status": "PASS" if route >= THRESHOLD and gate["passes"] else "FAIL",
        "research_only": True,
        "formula_version": "Route_A_NG1",
        "effective_month": "2007-11",
        "source_months": {
            "fama_french": TARGET_FF_MONTH,
            "credit_spread": TARGET_SPREAD_MONTH,
        },
        "scores": {
            "spread_shock_score": spread["score"],
            "finance_weakness_score": ff["finance_score"],
            "size_weakness_score": ff["size_score"],
            "portfolio_exhaustion_score": ff["exhaust_score"],
            "credit_market_stress": credit,
            "breadth_stress": breadth,
            "route_a_ng1": route,
            "threshold": THRESHOLD,
            "margin": route - THRESHOLD,
        },
        "raw": {
            "spread_shock": spread["raw"],
            "baa_200710": spread["baa"],
            "gs10_200710": spread["gs10"],
            "finance_weakness": ff["finance_raw"],
            "size_weakness": ff["size_raw"],
            "portfolio_exhaustion": ff["exhaust_raw"],
        },
        "top_location": gate,
        "sources": {
            **ff_sources,
            "credit_snapshot_repository": (
                "Snow-Ouyang/Market-Regime-Clustering"
            ),
            "credit_snapshot_commit": CREDIT_SNAPSHOT_COMMIT,
            "baa_url": BAA_URL,
            "gs10_url": GS10_URL,
            "credit_history_start": spread["history_start"],
            "credit_history_end": spread["history_end"],
            "spy": "Yahoo Finance SPY unadjusted close",
        },
        "provenance": {
            "fama_french": "official Ken French live ZIPs",
            "credit": (
                "independent immutable Git snapshot of FRED monthly BAA/GS10; "
                "2007-10 values and spread-shock percentile are parity-locked"
            ),
            "first_screen_source_reused_for_credit": False,
            "parameters_changed": False,
        },
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "interpretation": (
            "Independent-source replay of the preregistered 2007-11 "
            "Route_A_NG1 screening hit. This validates source invariance only; "
            "it does not promote NG1 to production or recover legacy Route_A."
        ),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--output")
    args = ap.parse_args()

    x = audit()
    print(json.dumps(x, indent=2))

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(x, f, indent=2)
            f.write("\n")

    if x["status"] != "PASS":
        raise SystemExit("Route_A_NG1 independent-source replay failed")


if __name__ == "__main__":
    main()
