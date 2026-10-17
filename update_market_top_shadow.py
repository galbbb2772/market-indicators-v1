from __future__ import annotations

import argparse
import io
import json
import math
import zipfile
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import requests
from pandas.tseries.holiday import USFederalHolidayCalendar
from pandas.tseries.offsets import CustomBusinessDay

from market_top_canonical_inputs import (
    size_block_from_smb_6m,
    size_weakness_history,
    valuation_history,
)
from policyshock_v211 import ARMED_THRESHOLD, compute_policy_shock, route_b
from t_v24r import compute_t_v24r_series


OUT_CURRENT = Path("docs/data/market_top_shadow_current.json")
OUT_HISTORY = Path("docs/data/market_top_shadow_history.json")

FRED_CSV = "https://fred.stlouisfed.org/graph/fredgraph.csv"
TREASURY_2Y_CSV = (
    "https://home.treasury.gov/resource-center/data-chart-center/interest-rates/"
    "daily-treasury-rates.csv/{year}/all"
    "?_format=csv&field_tdr_date_value={year}&page=&type=daily_treasury_yield_curve"
)
FED_ASSETS_MIRROR = (
    "https://raw.githubusercontent.com/zifanzhou1024/market-weather-map/"
    "main/public/data/series/fed_assets.json"
)
YAHOO_SPY = (
    "https://query1.finance.yahoo.com/v8/finance/chart/SPY"
    "?range=5y&interval=1d&events=history&includeAdjustedClose=false"
)
SHILLER_FEED = (
    "https://raw.githubusercontent.com/adambnash-afk/shiller-data/"
    "main/data/stock_market_data.json"
)
FF_OFFICIAL = (
    "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/"
    "F-F_Research_Data_Factors_CSV.zip"
)
FF_MIRROR = (
    "https://raw.githubusercontent.com/engineerinvestor/summitward-research/"
    "main/cliff-asness-investing-pet-peeves/data/"
    "F-F_Research_Data_Factors.csv"
)

UA = "market-top-shadow-research/1.0"

MAX_MARKET_STALENESS_DAYS = 5
MAX_DGS2_LAG_DAYS = 7
MAX_WALCL_LAG_DAYS = 14
MAX_FF_FACTOR_LAG_MONTHS = 3

HTTP = requests.Session()
HTTP.headers.update({"User-Agent": UA})


def _get(url: str, *, timeout: int = 30) -> requests.Response:
    last: Exception | None = None
    candidates = [url]
    if "query1.finance.yahoo.com" in url:
        candidates.append(url.replace("query1.finance.yahoo.com", "query2.finance.yahoo.com"))
    for candidate in candidates:
        try:
            r = HTTP.get(candidate, timeout=timeout)
            r.raise_for_status()
            return r
        except Exception as exc:
            last = exc
    raise RuntimeError(f"request failed for {url}: {last!r}")


def fetch_fred_series(series_id: str, start: str) -> pd.Series:
    # FRED is a fallback in the forward path because its CSV endpoint can
    # intermittently time out from GitHub Actions.
    r = HTTP.get(
        FRED_CSV,
        params={"id": series_id, "cosd": start},
        timeout=12,
    )
    r.raise_for_status()
    df = pd.read_csv(io.StringIO(r.text))
    if df.empty or series_id not in df.columns:
        raise ValueError(f"FRED returned no {series_id} column")
    dcol = df.columns[0]
    idx = pd.to_datetime(df[dcol], errors="coerce")
    vals = pd.to_numeric(df[series_id], errors="coerce")
    s = pd.Series(vals.to_numpy(), index=idx, name=series_id).dropna().sort_index()
    if s.empty:
        raise ValueError(f"FRED {series_id} is empty")
    s.attrs["source"] = f"FRED {series_id}"
    return s


def parse_treasury_2y_csv(text: str) -> pd.Series:
    df = pd.read_csv(io.StringIO(text))
    date_candidates = ["Date", "date", "DATE"]
    value_candidates = ["2 Yr", "2-Year", "2 Year", "2 YR"]
    dcol = next((x for x in date_candidates if x in df.columns), None)
    vcol = next((x for x in value_candidates if x in df.columns), None)
    if dcol is None or vcol is None:
        raise ValueError(
            f"Treasury CSV missing Date/2 Yr columns: {list(df.columns)}"
        )
    idx = pd.to_datetime(df[dcol], errors="coerce")
    vals = pd.to_numeric(df[vcol], errors="coerce")
    s = pd.Series(vals.to_numpy(), index=idx, name="DGS2").dropna().sort_index()
    s = s[~s.index.duplicated(keep="last")]
    if s.empty:
        raise ValueError("Treasury 2Y series is empty")
    return s


def fetch_treasury_2y(start: str, end: pd.Timestamp) -> pd.Series:
    start_ts = pd.Timestamp(start)
    years = range(start_ts.year, end.year + 1)
    parts = []
    errors = []
    for year in years:
        try:
            url = TREASURY_2Y_CSV.format(year=year)
            parts.append(parse_treasury_2y_csv(_get(url, timeout=20).text))
        except Exception as exc:
            errors.append(f"{year}={exc!r}")
    if not parts:
        raise RuntimeError("Treasury 2Y download failed: " + "; ".join(errors))
    s = pd.concat(parts).sort_index()
    s = s[~s.index.duplicated(keep="last")]
    s = s.loc[start_ts:end].dropna()
    if s.empty:
        raise ValueError("Treasury 2Y has no observations in requested range")
    s.attrs["source"] = "U.S. Treasury Daily Treasury Par Yield Curve Rates"
    return s


def fetch_two_year_series(start: str, end: pd.Timestamp) -> pd.Series:
    errors = []
    try:
        return fetch_treasury_2y(start, end)
    except Exception as exc:
        errors.append(f"treasury={exc!r}")
    try:
        s = fetch_fred_series("DGS2", start)
        s = s.loc[:end]
        return s
    except Exception as exc:
        errors.append(f"fred={exc!r}")
    raise RuntimeError("2Y Treasury sources failed: " + "; ".join(errors))


def parse_fed_assets_mirror(obj: dict[str, Any]) -> pd.Series:
    rows = obj.get("observations") or []
    pts = {}
    for row in rows:
        try:
            d = pd.Timestamp(row["date"])
            v = float(row["value"])
        except (KeyError, TypeError, ValueError):
            continue
        pts[d] = v
    if len(pts) < 100:
        raise ValueError(f"fed-assets mirror too short: {len(pts)} rows")
    s = pd.Series(pts, dtype=float, name="WALCL").sort_index()
    s.attrs["source"] = (
        "FRED WALCL via market-weather-map static GitHub mirror"
    )
    s.attrs["mirror_generated_at_utc"] = obj.get("generated_at_utc")
    return s


def fetch_walcl_series(start: str, end: pd.Timestamp) -> pd.Series:
    errors = []
    try:
        obj = _get(FED_ASSETS_MIRROR, timeout=20).json()
        s = parse_fed_assets_mirror(obj).loc[pd.Timestamp(start):end]
        if len(s) < 27:
            raise ValueError(f"fed-assets mirror range too short: {len(s)}")
        return s
    except Exception as exc:
        errors.append(f"mirror={exc!r}")
    try:
        s = fetch_fred_series("WALCL", start).loc[:end]
        return s
    except Exception as exc:
        errors.append(f"fred={exc!r}")
    raise RuntimeError("WALCL sources failed: " + "; ".join(errors))


def fetch_spy_close() -> pd.Series:
    obj = _get(YAHOO_SPY, timeout=20).json()
    results = ((obj.get("chart") or {}).get("result") or [])
    if not results:
        raise ValueError(f"Yahoo SPY returned no result: {(obj.get('chart') or {}).get('error')}")
    x = results[0]
    ts = x.get("timestamp") or []
    q = (((x.get("indicators") or {}).get("quote") or [{}])[0])
    close = q.get("close") or []
    if not ts or len(ts) != len(close):
        raise ValueError("Yahoo SPY timestamp/close mismatch")
    idx = pd.to_datetime(ts, unit="s", utc=True).tz_convert(None).normalize()
    s = pd.Series(pd.to_numeric(close, errors="coerce"), index=idx, name="SPY").dropna()
    s = s[~s.index.duplicated(keep="last")].sort_index()
    if len(s) < 600:
        raise ValueError(f"SPY history too short: {len(s)} rows")
    return s


def parse_shiller_feed(obj: dict[str, Any]) -> pd.DataFrame:
    rows = obj.get("data") or []
    out = []
    for row in rows:
        cape = row.get("cape")
        year = row.get("year")
        month = row.get("month")
        if cape is None or year is None or month is None:
            continue
        try:
            out.append(
                {
                    "date": pd.Timestamp(year=int(year), month=int(month), day=1),
                    "cape": float(cape),
                }
            )
        except Exception:
            continue
    df = pd.DataFrame(out).dropna().sort_values("date")
    if len(df) < 1500:
        raise ValueError(f"Shiller feed too short: {len(df)} rows")
    return df


def fetch_shiller() -> tuple[pd.DataFrame, dict[str, Any]]:
    obj = _get(SHILLER_FEED, timeout=30).json()
    return parse_shiller_feed(obj), (obj.get("metadata") or {})


def parse_ff_monthly(text: str) -> pd.DataFrame:
    rows = []
    started = False
    for raw in text.splitlines():
        p = [x.strip() for x in raw.split(",")]
        if p and p[0].isdigit() and len(p[0]) == 6:
            started = True
            if len(p) < 5:
                continue
            try:
                rows.append(
                    {
                        "ym": p[0],
                        "date": pd.Timestamp(
                            year=int(p[0][:4]), month=int(p[0][4:6]), day=1
                        ),
                        "mkt_rf": float(p[1]),
                        "smb": float(p[2]),
                        "hml": float(p[3]),
                        "rf": float(p[4]),
                    }
                )
            except ValueError:
                continue
        elif started and rows:
            # First non-monthly line after the monthly block ends that block.
            break
    df = pd.DataFrame(rows)
    if len(df) < 1000:
        raise ValueError(f"Fama-French monthly history too short: {len(df)} rows")
    return df.sort_values("date").reset_index(drop=True)


def fetch_ff_monthly() -> tuple[pd.DataFrame, str]:
    errors: list[str] = []
    try:
        raw = _get(FF_OFFICIAL, timeout=45).content
        with zipfile.ZipFile(io.BytesIO(raw)) as z:
            names = [n for n in z.namelist() if n.lower().endswith(".csv")]
            if not names:
                raise ValueError("official FF ZIP contains no CSV")
            text = z.read(names[0]).decode("utf-8", "replace")
        return parse_ff_monthly(text), "Ken French Data Library"
    except Exception as exc:
        errors.append(f"official={exc!r}")

    try:
        text = _get(FF_MIRROR, timeout=30).text
        return parse_ff_monthly(text), "GitHub mirror of Ken French factors"
    except Exception as exc:
        errors.append(f"mirror={exc!r}")

    raise RuntimeError("Fama-French download failed: " + "; ".join(errors))


def last_on_or_before(s: pd.Series, when: pd.Timestamp) -> tuple[pd.Timestamp, float]:
    x = s.loc[:when].dropna()
    if x.empty:
        raise ValueError(f"no observation on/before {when.date()}")
    return pd.Timestamp(x.index[-1]), float(x.iloc[-1])


FED_BUSINESS_DAY = CustomBusinessDay(calendar=USFederalHolidayCalendar())


def walcl_actionable_eod_date(observation_date: pd.Timestamp) -> pd.Timestamp:
    """First market EOD that may use an H.4.1 observation without lookahead.

    H.4.1 is normally released Thursday at 4:30 p.m. ET, after the U.S.
    equity close, and may shift to the next federal business day on holidays.

    We therefore:
      1. move from the observation date to the next federal business day
         (the release date);
      2. move one additional federal business day before allowing an EOD
         state update.
    """
    obs = pd.Timestamp(observation_date).normalize()
    release_date = obs + FED_BUSINESS_DAY
    return pd.Timestamp(release_date + FED_BUSINESS_DAY).normalize()


def last_released_walcl_for_eod(
    walcl: pd.Series,
    asof: pd.Timestamp,
) -> tuple[pd.Timestamp, float]:
    asof = pd.Timestamp(asof).normalize()
    candidates = []
    for idx, value in walcl.dropna().sort_index().items():
        obs = pd.Timestamp(idx).normalize()
        if walcl_actionable_eod_date(obs) <= asof:
            candidates.append((obs, float(value)))
    if not candidates:
        raise ValueError(f"no H.4.1 observation actionable by {asof.date()}")
    return candidates[-1]


def month_start(d: pd.Timestamp) -> pd.Timestamp:
    return pd.Timestamp(year=d.year, month=d.month, day=1)


def previous_month_start(d: pd.Timestamp) -> pd.Timestamp:
    return month_start(d) - pd.offsets.MonthBegin(1)


def calendar_month_lag(later: pd.Timestamp, earlier: pd.Timestamp) -> int:
    later = month_start(pd.Timestamp(later))
    earlier = month_start(pd.Timestamp(earlier))
    return (later.year - earlier.year) * 12 + (later.month - earlier.month)


def validate_source_freshness(
    *,
    generated_at: datetime,
    market_asof: pd.Timestamp,
    policy: dict[str, Any],
    valuation: dict[str, Any],
    size_weakness: dict[str, Any],
) -> dict[str, Any]:
    gen_date = pd.Timestamp(generated_at.astimezone(timezone.utc).date())
    market_asof = pd.Timestamp(market_asof).normalize()

    market_lag_days = int((gen_date - market_asof).days)
    if market_lag_days < 0 or market_lag_days > MAX_MARKET_STALENESS_DAYS:
        raise ValueError(
            f"market as-of freshness failure: lag={market_lag_days} days"
        )

    dgs2_date = pd.Timestamp(policy["dgs2_latest_date"])
    dgs2_lag_days = int((market_asof - dgs2_date).days)
    if dgs2_lag_days < 0 or dgs2_lag_days > MAX_DGS2_LAG_DAYS:
        raise ValueError(
            f"DGS2 freshness failure: lag={dgs2_lag_days} days"
        )

    walcl_date = pd.Timestamp(policy["walcl_latest_date"])
    walcl_lag_days = int((market_asof - walcl_date).days)
    if walcl_lag_days < 2 or walcl_lag_days > MAX_WALCL_LAG_DAYS:
        raise ValueError(
            f"WALCL freshness failure: lag={walcl_lag_days} days"
        )

    expected_valuation_month = previous_month_start(market_asof)
    valuation_month = pd.Timestamp(f"{valuation['signal_month']}-01")
    valuation_lag_months = calendar_month_lag(
        expected_valuation_month,
        valuation_month,
    )
    if valuation_lag_months != 0:
        raise ValueError(
            "CAPE freshness failure: signal month must equal the last "
            f"completed calendar month; lag={valuation_lag_months}"
        )

    factor_month = pd.Timestamp(f"{size_weakness['factor_month']}-01")
    factor_lag_months = calendar_month_lag(market_asof, factor_month)
    if factor_lag_months < 1 or factor_lag_months > MAX_FF_FACTOR_LAG_MONTHS:
        raise ValueError(
            f"Fama-French freshness failure: lag={factor_lag_months} months"
        )

    return {
        "status": "PASS",
        "market_lag_days": market_lag_days,
        "dgs2_lag_days": dgs2_lag_days,
        "walcl_lag_days": walcl_lag_days,
        "valuation_signal_month": valuation["signal_month"],
        "valuation_expected_month": expected_valuation_month.strftime("%Y-%m"),
        "ff_factor_month": size_weakness["factor_month"],
        "ff_factor_lag_months": factor_lag_months,
        "limits": {
            "market_days": MAX_MARKET_STALENESS_DAYS,
            "dgs2_days": MAX_DGS2_LAG_DAYS,
            "walcl_days": MAX_WALCL_LAG_DAYS,
            "ff_factor_months": MAX_FF_FACTOR_LAG_MONTHS,
        },
    }


def compute_valuation(
    shiller: pd.DataFrame,
    *,
    asof: pd.Timestamp,
) -> dict[str, Any]:
    # A live day may never use the unfinished current calendar month.
    latest_allowed = previous_month_start(asof)
    x = shiller.loc[shiller["date"] <= latest_allowed].copy()
    if x.empty:
        raise ValueError("no completed-month CAPE data available")
    scores = valuation_history(x["cape"].tolist())
    row = x.iloc[-1]
    return {
        "signal_month": pd.Timestamp(row["date"]).strftime("%Y-%m"),
        "cape": float(row["cape"]),
        "score": float(scores[-1]),
        "source_latest_month": pd.Timestamp(shiller.iloc[-1]["date"]).strftime("%Y-%m"),
    }


def compute_size_weakness(
    ff: pd.DataFrame,
    *,
    asof: pd.Timestamp,
) -> dict[str, Any]:
    # Factor rows are used only when they actually exist in the downloaded
    # published dataset. Do not synthesize the current month.
    latest_allowed = previous_month_start(asof)
    x = ff.loc[ff["date"] <= latest_allowed].copy()
    if len(x) < 6:
        raise ValueError("not enough published SMB history")
    scores = size_weakness_history(x["smb"].tolist())
    score = scores[-1]
    if score is None:
        raise ValueError("latest SizeWeakness score is missing")
    six = x["smb"].iloc[-6:].tolist()
    block = size_block_from_smb_6m(six)
    return {
        "factor_month": pd.Timestamp(x.iloc[-1]["date"]).strftime("%Y-%m"),
        "smb_6m_pct": float(-block),
        "b_size": float(block),
        "score": float(score),
    }


def compute_policy(
    dgs2: pd.Series,
    walcl: pd.Series,
    *,
    asof: pd.Timestamp,
) -> dict[str, Any]:
    d_date, d_now = last_on_or_before(dgs2, asof)
    anchor_target = d_date - pd.DateOffset(months=6)
    a_date, d_anchor = last_on_or_before(dgs2, anchor_target)

    # H.4.1 observations are normally published Thursday at 4:30 p.m. ET,
    # after the equity close. Holiday releases can shift to the next federal
    # business day. Use the release-aware EOD gate rather than observation
    # date alone.
    w0_date, w0 = last_released_walcl_for_eod(walcl, asof)
    w13_date, w13 = last_on_or_before(walcl, w0_date - pd.Timedelta(weeks=13))
    w26_date, w26 = last_on_or_before(walcl, w0_date - pd.Timedelta(weeks=26))

    out = compute_policy_shock(
        dgs2_latest_pct=d_now,
        dgs2_6m_ago_pct=d_anchor,
        walcl_now=w0,
        walcl_13w_ago=w13,
        walcl_26w_ago=w26,
    )
    if out.policy_shock is None:
        raise ValueError("PolicyShock is missing")

    g_prev = w13 / w26 - 1.0
    g_cur = w0 / w13 - 1.0

    return {
        "dgs2_latest_date": d_date.date().isoformat(),
        "dgs2_latest_pct": d_now,
        "dgs2_anchor_date": a_date.date().isoformat(),
        "dgs2_anchor_pct": d_anchor,
        "delta_6m_bp": (d_now - d_anchor) * 100.0,
        "walcl_latest_date": w0_date.date().isoformat(),
        "walcl_latest": w0,
        "walcl_13w_date": w13_date.date().isoformat(),
        "walcl_13w": w13,
        "walcl_26w_date": w26_date.date().isoformat(),
        "walcl_26w": w26,
        "g_prev_pct": g_prev * 100.0,
        "g_cur_pct": g_cur * 100.0,
        "deceleration_pp": (g_prev - g_cur) * 100.0,
        "rate_shock": float(out.rate_shock),
        "taper_shock": float(out.taper_shock),
        "policy_shock": float(out.policy_shock),
    }


def compute_price(spy: pd.Series) -> dict[str, Any]:
    t = compute_t_v24r_series(spy)
    row = t.dropna(subset=["dd12_pct", "ma10m_prev", "t_v24r"]).iloc[-1]
    asof = pd.Timestamp(row.name)

    # 24 calendar-month high-location gate for the policy Route_B arm path.
    s = spy.loc[:asof]
    last_24m = s.loc[asof - pd.DateOffset(months=24):asof]
    if last_24m.empty:
        raise ValueError("no SPY observations in trailing 24 calendar months")
    high24 = float(last_24m.max())
    high24_date = pd.Timestamp(last_24m.idxmax())
    within_5pct = float(row["close"]) >= 0.95 * high24
    recent_cutoff = asof - pd.DateOffset(months=3)
    high_recent = high24_date >= recent_cutoff

    return {
        "asof": asof.date().isoformat(),
        "close": float(row["close"]),
        "high12_close": float(row["high12_close"]),
        "dd12_pct": float(row["dd12_pct"]),
        "ma10m_prev": float(row["ma10m_prev"]),
        "ma_gap_pct": float(row["ma_gap_pct"]),
        "t_v24r": float(row["t_v24r"]),
        "price_breakdown_v24r": bool(row["price_breakdown_v24r"]),
        "high24_close": high24,
        "high24_date": high24_date.date().isoformat(),
        "within_5pct_of_24m_high": bool(within_5pct),
        "high_formed_within_3m": bool(high_recent),
        "top_location_gate": bool(within_5pct and high_recent),
    }


def _load_history(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    obj = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(obj, dict):
        return list(obj.get("history") or [])
    return list(obj)


def _prior_policy_state(
    history: list[dict[str, Any]],
    *,
    asof: pd.Timestamp,
) -> dict[str, str | None]:
    """Recover the Route_B-only shadow state without resetting the arm clock."""
    triggered = [x for x in history if x.get("policy_path_state") == "TRIGGERED"]
    if triggered:
        last = sorted(triggered, key=lambda x: x.get("asof") or "")[-1]
        return {
            "state": "TRIGGERED",
            "armed_at": last.get("armed_at"),
            "triggered_at": last.get("triggered_at") or last.get("asof"),
        }

    armed_dates = [
        pd.Timestamp(x["armed_at"])
        for x in history
        if x.get("armed_at")
    ]
    if not armed_dates:
        return {"state": "IDLE", "armed_at": None, "triggered_at": None}

    armed_at = max(armed_dates)
    expires = armed_at + pd.DateOffset(months=6)
    if asof > expires:
        return {"state": "IDLE", "armed_at": None, "triggered_at": None}
    return {
        "state": "ARMED",
        "armed_at": armed_at.date().isoformat(),
        "triggered_at": None,
    }

def build_snapshot(
    *,
    now: datetime | None = None,
    dgs2: pd.Series,
    walcl: pd.Series,
    spy: pd.Series,
    shiller: pd.DataFrame,
    shiller_meta: dict[str, Any],
    ff: pd.DataFrame,
    ff_source: str,
    prior_history: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    generated = now or datetime.now(timezone.utc)
    price = compute_price(spy)
    asof = pd.Timestamp(price["asof"])
    policy = compute_policy(dgs2, walcl, asof=asof)
    valuation = compute_valuation(shiller, asof=asof)
    size = compute_size_weakness(ff, asof=asof)
    freshness = validate_source_freshness(
        generated_at=generated,
        market_asof=asof,
        policy=policy,
        valuation=valuation,
        size_weakness=size,
    )

    rb = route_b(valuation["score"], policy["policy_shock"], size["score"])
    if rb is None:
        raise ValueError("Route_B is missing")
    pressure_pass = rb >= ARMED_THRESHOLD
    arm_today = pressure_pass and price["top_location_gate"]

    prior_history = prior_history or []
    prior_state = _prior_policy_state(prior_history, asof=asof)

    armed_at = prior_state["armed_at"]
    triggered_at = prior_state["triggered_at"]

    if prior_state["state"] == "TRIGGERED":
        policy_path_state = "TRIGGERED"
    else:
        if armed_at is None and arm_today:
            armed_at = price["asof"]

        if armed_at is not None:
            expires_ts = pd.Timestamp(armed_at) + pd.DateOffset(months=6)
            expires = expires_ts.date().isoformat()
            active_arm = asof <= expires_ts
        else:
            expires = None
            active_arm = False

        if active_arm and price["price_breakdown_v24r"]:
            policy_path_state = "TRIGGERED"
            triggered_at = price["asof"]
        elif active_arm:
            policy_path_state = "ARMED"
        else:
            policy_path_state = "IDLE"
            armed_at = None
    if armed_at is not None:
        expires = (pd.Timestamp(armed_at) + pd.DateOffset(months=6)).date().isoformat()
    else:
        expires = None

    snap = {
        "schema_version": "market-top-shadow-forward-1",
        "generated_at": generated.astimezone(timezone.utc).isoformat(),
        "research_only": True,
        "production_effect": "none",
        "asof": price["asof"],
        "sources": {
            "dgs2": dgs2.attrs.get("source", "unknown"),
            "walcl": walcl.attrs.get("source", "unknown"),
            "walcl_mirror_generated_at_utc": walcl.attrs.get(
                "mirror_generated_at_utc"
            ),
            "spy": "Yahoo Finance unadjusted close",
            "shiller": shiller_meta.get("source") or "Robert Shiller feed mirror",
            "shiller_latest_date": shiller_meta.get("latest_date"),
            "fama_french": ff_source,
        },
        "freshness": freshness,
        "policy": policy,
        "valuation": valuation,
        "size_weakness": size,
        "route_b": {
            "score": float(rb),
            "threshold": ARMED_THRESHOLD,
            "pressure_pass": bool(pressure_pass),
            "top_location_gate": bool(price["top_location_gate"]),
            "arm_today": bool(arm_today),
        },
        "price_confirmation": price,
        "policy_path": {
            "state": policy_path_state,
            "armed_at": armed_at,
            "armed_expires_at": expires,
            "triggered_at": triggered_at,
            "breakdown_today": bool(
                policy_path_state == "TRIGGERED"
                and triggered_at == price["asof"]
            ),
            "scope": "Route_B-only shadow path; does not represent unresolved Route_A/Route_C",
        },
        "full_legacy_model": {
            "status": "PARTIAL_ROUTE_COVERAGE",
            "route_a": "UNRESOLVED",
            "route_b": "RESOLVED",
            "route_c": "UNRESOLVED",
            "pressure_authoritative": False,
        },
    }
    return snap


def history_row(snapshot: dict[str, Any]) -> dict[str, Any]:
    return {
        "asof": snapshot["asof"],
        "generated_at": snapshot["generated_at"],
        "policy_shock": snapshot["policy"]["policy_shock"],
        "rate_shock": snapshot["policy"]["rate_shock"],
        "taper_shock": snapshot["policy"]["taper_shock"],
        "valuation": snapshot["valuation"]["score"],
        "size_weakness": snapshot["size_weakness"]["score"],
        "route_b": snapshot["route_b"]["score"],
        "route_b_pressure_pass": snapshot["route_b"]["pressure_pass"],
        "top_location_gate": snapshot["route_b"]["top_location_gate"],
        "t_v24r": snapshot["price_confirmation"]["t_v24r"],
        "dd12_pct": snapshot["price_confirmation"]["dd12_pct"],
        "price_breakdown_v24r": snapshot["price_confirmation"]["price_breakdown_v24r"],
        "policy_path_state": snapshot["policy_path"]["state"],
        "armed_at": snapshot["policy_path"]["armed_at"],
        "triggered_at": snapshot["policy_path"]["triggered_at"],
    }


def write_outputs(snapshot: dict[str, Any]) -> None:
    OUT_CURRENT.parent.mkdir(parents=True, exist_ok=True)
    history = _load_history(OUT_HISTORY)
    row = history_row(snapshot)

    by_date = {x.get("asof"): x for x in history if x.get("asof")}
    by_date[row["asof"]] = row
    ordered = [by_date[k] for k in sorted(by_date)]

    OUT_CURRENT.write_text(
        json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    OUT_HISTORY.write_text(
        json.dumps(
            {
                "schema_version": "market-top-shadow-forward-history-1",
                "research_only": True,
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

    spy = fetch_spy_close()
    latest_market_date = pd.Timestamp(spy.index[-1])
    fred_start = (latest_market_date - pd.DateOffset(years=2)).date().isoformat()

    dgs2 = fetch_two_year_series(fred_start, latest_market_date)
    walcl = fetch_walcl_series(fred_start, latest_market_date)
    shiller, shiller_meta = fetch_shiller()
    ff, ff_source = fetch_ff_monthly()

    prior = _load_history(OUT_HISTORY)
    snapshot = build_snapshot(
        dgs2=dgs2,
        walcl=walcl,
        spy=spy,
        shiller=shiller,
        shiller_meta=shiller_meta,
        ff=ff,
        ff_source=ff_source,
        prior_history=prior,
    )

    print(json.dumps(snapshot, ensure_ascii=False, indent=2))
    if not args.dry_run:
        write_outputs(snapshot)


if __name__ == "__main__":
    main()
