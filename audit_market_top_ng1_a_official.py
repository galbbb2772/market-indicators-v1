from __future__ import annotations

import argparse
import io
import json
import math
import time
import zipfile
from datetime import datetime, timezone
from statistics import median

import pandas as pd
import requests

FF25_URL = "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/25_Portfolios_5x5_CSV.zip"
FF12_URL = "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/12_Industry_Portfolios_CSV.zip"
FF3_URL = "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/F-F_Research_Data_Factors_CSV.zip"
FED_DDP = "https://www.federalreserve.gov/datadownload/Output.aspx"
FED_BAA_SERIES_ID = "H15/H15/RIMLPBAAR_N.M"
FED_GS10_SERIES_ID = "H15/H15/RIFLGFCY10_N.M"
FED_BAA_HASH = "ccd455e753647ae509d6cb29970c6b1b"
FED_GS10_HASH = "0809abf197c17f1ff0b2180fe7015cc3"
TARGET_FF_MONTH = "200709"
TARGET_SPREAD_MONTH = "200710"
EFFECTIVE_MONTH = "200711"
THRESHOLD = 85.0
UA = "market-top-ng1-a-official-audit/1.0"

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

    h25, r25 = parse_portfolio_block(
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
        ym, vals_now = r25[i]
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
        exhaust = 1.0 - sum(x > mkt6 for x in p6) / 25.0
        size_raw = -compounded([ff3[k][2] for k in range(fi - 5, fi + 1)])
        finance_raw = -(money6 - mkt6)
        rows.append(
            {
                "ym": ym,
                "exhaust_raw": exhaust,
                "size_raw": size_raw,
                "finance_raw": finance_raw,
            }
        )

    for key, score_name in (
        ("exhaust_raw", "exhaust_score"),
        ("size_raw", "size_score"),
        ("finance_raw", "finance_score"),
    ):
        vals = [x[key] for x in rows]
        for i, row in enumerate(rows):
            row[score_name] = expanding_pct(vals, i)

    target = next(x for x in rows if x["ym"] == TARGET_FF_MONTH)
    return target, {
        "ff25_url": FF25_URL,
        "ff12_url": FF12_URL,
        "ff3_url": FF3_URL,
        "ff25_last_month": r25[-1][0],
        "ff12_last_month": r12[-1][0],
        "ff3_last_month": ff3[-1][0],
    }


def parse_fed_ddp_monthly(text: str) -> pd.Series:
    import csv
    import re

    pts = {}
    for row in csv.reader(io.StringIO(text)):
        if len(row) < 2:
            continue
        ym = str(row[0]).strip()
        raw = str(row[1]).strip()
        if not re.fullmatch(r"\d{4}-\d{2}", ym):
            continue
        if raw in {"", ".", "NA", "N/A"}:
            continue
        try:
            pts[pd.Timestamp(ym + "-01")] = float(raw)
        except ValueError:
            continue
    if len(pts) < 500:
        raise ValueError(f"Federal Reserve DDP monthly history too short: {len(pts)}")
    return pd.Series(pts, dtype=float).sort_index()


def fed_ddp_monthly(series_hash: str) -> pd.Series:
    r = get(
        FED_DDP,
        params={
            "rel": "H15",
            "series": series_hash,
            "lastObs": "",
            "from": "",
            "to": "",
            "filetype": "csv",
            "label": "include",
            "layout": "seriescolumn",
        },
    )
    return parse_fed_ddp_monthly(r.text)

def spread_score():
    baa = fed_ddp_monthly(FED_BAA_HASH)
    gs10 = fed_ddp_monthly(FED_GS10_HASH)
    common = sorted(set(baa.index) & set(gs10.index))
    rows = [(d.strftime("%Y%m"), float(baa.loc[d] - gs10.loc[d])) for d in common]
    shock = []
    for i in range(6, len(rows)):
        raw = max(rows[i][1] - rows[i - 3][1], rows[i][1] - rows[i - 6][1])
        shock.append({"ym": rows[i][0], "raw": raw})
    vals = [x["raw"] for x in shock]
    for i, row in enumerate(shock):
        row["score"] = expanding_pct(vals, i)
    return next(x for x in shock if x["ym"] == TARGET_SPREAD_MONTH)


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
                index=pd.to_datetime(ts, unit="s", utc=True).tz_convert(None).normalize(),
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
    recent = high_date >= asof - pd.DateOffset(months=3)
    within = close >= 0.95 * high
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
    ff, source = ff_scores()
    spread = spread_score()
    gate = top_gate()

    credit = math.sqrt(spread["score"] * ff["finance_score"])
    breadth = math.sqrt(ff["size_score"] * ff["exhaust_score"])
    route = math.sqrt(credit * breadth)

    return {
        "schema_version": "market-top-route-a-ng1-official-audit-1",
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
            "finance_weakness": ff["finance_raw"],
            "size_weakness": ff["size_raw"],
            "portfolio_exhaustion": ff["exhaust_raw"],
        },
        "top_location": gate,
        "sources": {
            **source,
            "baa": (
                "Federal Reserve H.15 DDP monthly "
                + FED_BAA_SERIES_ID
            ),
            "gs10": (
                "Federal Reserve H.15 DDP monthly "
                + FED_GS10_SERIES_ID
            ),
            "spy": "Yahoo Finance SPY unadjusted close",
        },
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "interpretation": (
            "Independent live-source replay of the preregistered 2007-11 "
            "Route_A_NG1 screening hit. No NG1 parameters are changed."
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
        raise SystemExit("Route_A_NG1 independent replay failed")


if __name__ == "__main__":
    main()
