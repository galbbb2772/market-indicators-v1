from __future__ import annotations

import argparse
import io
import json
import re
from typing import Any

import pandas as pd
import requests

from policyshock_v211 import compute_policy_shock, route_b

ASOF = pd.Timestamp("2022-01-03")
STRICT_LAG_LATEST = pd.Timestamp("2021-12-31")
RATE_ANCHOR_TARGET = pd.Timestamp("2021-06-30")

TREASURY_2021_CSV = (
    "https://home.treasury.gov/resource-center/data-chart-center/interest-rates/"
    "daily-treasury-rates.csv/2021/all"
    "?_format=csv&field_tdr_date_value=2021&page=&type=daily_treasury_yield_curve"
)

H41_RELEASES = [
    {
        "release_date": "2021-07-01",
        "observation_date": "2021-06-30",
        "url": "https://www.federalreserve.gov/releases/h41/20210701/",
        "total_assets": 8_078_544.0,
    },
    {
        "release_date": "2021-09-30",
        "observation_date": "2021-09-29",
        "url": "https://www.federalreserve.gov/releases/h41/20210930/",
        "total_assets": 8_447_981.0,
    },
    {
        "release_date": "2021-12-30",
        "observation_date": "2021-12-29",
        "url": "https://www.federalreserve.gov/releases/h41/20211230/",
        "total_assets": 8_757_460.0,
    },
]

VALUATION_PRE_CUTOFF = 98.5790408526
SIZE_WEAKNESS_CURRENT_CONSERVATIVE = 84.73684210526316
ROUTE_B_THRESHOLD = 85.0

UA = "market-top-policyshock-2022-pit-audit/1.0"


def http() -> requests.Session:
    s = requests.Session()
    s.headers.update({"User-Agent": UA})
    return s


def parse_treasury_2y_csv(text: str) -> pd.Series:
    df = pd.read_csv(io.StringIO(text))
    dcol = next((x for x in ("Date", "date", "DATE") if x in df.columns), None)
    vcol = next((x for x in ("2 Yr", "2-Year", "2 Year", "2 YR") if x in df.columns), None)
    if dcol is None or vcol is None:
        raise ValueError(f"Treasury CSV columns unexpected: {list(df.columns)}")
    idx = pd.to_datetime(df[dcol], errors="coerce")
    vals = pd.to_numeric(df[vcol], errors="coerce")
    out = pd.Series(vals.to_numpy(), index=idx, dtype=float).dropna().sort_index()
    if out.empty:
        raise ValueError("Treasury 2Y series is empty")
    return out[~out.index.duplicated(keep="last")]


def fetch_treasury_inputs() -> dict[str, Any]:
    r = http().get(TREASURY_2021_CSV, timeout=30)
    r.raise_for_status()
    s = parse_treasury_2y_csv(r.text)

    latest = s.loc[s.index <= STRICT_LAG_LATEST]
    if latest.empty:
        raise ValueError("no Treasury observation by strict-lag date")
    latest_date = pd.Timestamp(latest.index[-1])
    latest_value = float(latest.iloc[-1])

    anchor = s.loc[s.index <= RATE_ANCHOR_TARGET]
    if anchor.empty:
        raise ValueError("no Treasury observation by six-month anchor")
    anchor_date = pd.Timestamp(anchor.index[-1])
    anchor_value = float(anchor.iloc[-1])

    return {
        "source": "U.S. Treasury Daily Treasury Par Yield Curve Rates",
        "strict_lag_asof": STRICT_LAG_LATEST.date().isoformat(),
        "latest_date": latest_date.date().isoformat(),
        "latest_2y_pct": latest_value,
        "anchor_target": RATE_ANCHOR_TARGET.date().isoformat(),
        "anchor_date": anchor_date.date().isoformat(),
        "anchor_2y_pct": anchor_value,
        "delta_6m_bp": (latest_value - anchor_value) * 100.0,
    }


def normalize_text(html: str) -> str:
    text = re.sub(r"<script\b[^>]*>.*?</script>", " ", html, flags=re.I | re.S)
    text = re.sub(r"<style\b[^>]*>.*?</style>", " ", text, flags=re.I | re.S)
    text = re.sub(r"<[^>]+>", " ", text)
    text = text.replace("&nbsp;", " ").replace("&#160;", " ")
    return re.sub(r"\s+", " ", text)


def verify_h41_release(spec: dict[str, Any]) -> dict[str, Any]:
    r = http().get(spec["url"], timeout=30)
    r.raise_for_status()
    text = normalize_text(r.text)

    expected = int(spec["total_assets"])
    formatted = f"{expected:,}"

    release_dt = pd.Timestamp(spec["release_date"])
    obs_dt = pd.Timestamp(spec["observation_date"])

    total_assets_match = re.search(
        rf"Total assets.{0,120}{re.escape(formatted)}",
        text,
        flags=re.I,
    )
    if total_assets_match is None:
        raise ValueError(
            f"H.4.1 {spec['release_date']} does not pair Total assets with {formatted}"
        )

    # The historical H.4.1 page must identify both its release date and the
    # Wednesday observation represented by the total-assets figure.
    release_tokens = [
        release_dt.strftime("%B %d, %Y"),
        release_dt.strftime("%B %-d, %Y"),
    ]
    obs_tokens = [
        obs_dt.strftime("%b %d, %Y"),
        obs_dt.strftime("%b %-d, %Y"),
        obs_dt.strftime("%B %d, %Y"),
        obs_dt.strftime("%B %-d, %Y"),
    ]
    if not any(x in text for x in release_tokens):
        raise ValueError(f"H.4.1 release date missing for {spec['release_date']}")
    if not any(x in text for x in obs_tokens):
        raise ValueError(f"H.4.1 observation date missing for {spec['observation_date']}")

    return {
        "release_date": spec["release_date"],
        "observation_date": spec["observation_date"],
        "url": spec["url"],
        "total_assets_millions": float(spec["total_assets"]),
        "verified_in_official_release_page": True,
    }


def audit() -> dict[str, Any]:
    treasury = fetch_treasury_inputs()
    h41 = [verify_h41_release(x) for x in H41_RELEASES]

    by_obs = {x["observation_date"]: x for x in h41}
    w26 = by_obs["2021-06-30"]["total_assets_millions"]
    w13 = by_obs["2021-09-29"]["total_assets_millions"]
    w0 = by_obs["2021-12-29"]["total_assets_millions"]

    out = compute_policy_shock(
        dgs2_latest_pct=treasury["latest_2y_pct"],
        dgs2_6m_ago_pct=treasury["anchor_2y_pct"],
        walcl_now=w0,
        walcl_13w_ago=w13,
        walcl_26w_ago=w26,
    )
    if out.policy_shock is None:
        raise ValueError("PolicyShock missing")

    rb = route_b(
        VALUATION_PRE_CUTOFF,
        out.policy_shock,
        SIZE_WEAKNESS_CURRENT_CONSERVATIVE,
    )
    if rb is None:
        raise ValueError("Route_B missing")

    critical_policy = (
        ROUTE_B_THRESHOLD**3
        / (VALUATION_PRE_CUTOFF * SIZE_WEAKNESS_CURRENT_CONSERVATIVE)
    )

    return {
        "schema_version": "policyshock-2022-primary-source-pit-audit-1",
        "status": "PASS_PRIMARY_SOURCE_PIT_CHAIN",
        "asof": ASOF.date().isoformat(),
        "strict_same_day_market_input_excluded": True,
        "treasury": treasury,
        "h41": h41,
        "walcl_spacing_days": {
            "w0_minus_w13": (
                pd.Timestamp("2021-12-29") - pd.Timestamp("2021-09-29")
            ).days,
            "w13_minus_w26": (
                pd.Timestamp("2021-09-29") - pd.Timestamp("2021-06-30")
            ).days,
        },
        "rate_shock": float(out.rate_shock),
        "taper_shock": float(out.taper_shock),
        "policy_shock": float(out.policy_shock),
        "conservative_route_b_check": {
            "valuation_pre_cutoff": VALUATION_PRE_CUTOFF,
            "size_weakness_current_conservative": SIZE_WEAKNESS_CURRENT_CONSERVATIVE,
            "route_b": float(rb),
            "threshold": ROUTE_B_THRESHOLD,
            "passes": bool(rb >= ROUTE_B_THRESHOLD),
            "critical_policy_shock": float(critical_policy),
            "policy_margin_above_critical": float(out.policy_shock - critical_policy),
        },
        "provenance": {
            "dgs2": (
                "Current official U.S. Treasury historical table; validates the "
                "frozen historical rate observations, not archived Jan-3 page bytes."
            ),
            "walcl": (
                "Dated Federal Reserve H.4.1 historical release pages. These pages "
                "directly establish the three balance-sheet values and that they "
                "were released before 2022-01-03."
            ),
        },
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output")
    args = ap.parse_args()

    result = audit()
    print(json.dumps(result, indent=2))

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2)
            f.write("\n")


if __name__ == "__main__":
    main()
