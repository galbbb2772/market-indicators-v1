from __future__ import annotations

import json
import math
import statistics
import time
from datetime import datetime, timezone

import requests

from sec_fundamentals import COMPANIES, _score_earnings, _score_liquidity, _score_debt

HTTP = requests.Session()
HTTP.headers.update({"User-Agent": "Mozilla/5.0 MarketRegimeLab/1.0"})

TYPES = [
    "quarterlyTotalRevenue",
    "quarterlyNetIncome",
    "annualTotalRevenue",
    "annualOperatingCashFlow",
    "annualCapitalExpenditure",
    "quarterlyCashCashEquivalentsAndShortTermInvestments",
    "quarterlyCashAndCashEquivalents",
    "quarterlyCashFinancial",
    "quarterlyTotalAssets",
    "quarterlyTotalDebt",
]


def _safe_div(a: float | None, b: float | None) -> float | None:
    if a is None or b is None or not math.isfinite(a) or not math.isfinite(b) or abs(b) < 1e-12:
        return None
    return a / b


def _fetch(symbol: str) -> dict:
    now = int(time.time())
    url = f"https://query2.finance.yahoo.com/ws/fundamentals-timeseries/v1/finance/timeseries/{symbol}"
    params = {
        "symbol": symbol,
        "type": ",".join(TYPES),
        "period1": now - 60 * 60 * 24 * 365 * 6,
        "period2": now,
    }
    last = None
    for attempt in range(3):
        try:
            r = HTTP.get(url, params=params, timeout=20)
            if r.status_code in {429, 500, 502, 503, 504} and attempt < 2:
                time.sleep(1.5 * (attempt + 1))
                continue
            r.raise_for_status()
            return r.json()
        except Exception as exc:
            last = exc
            if attempt < 2:
                time.sleep(1.0 * (attempt + 1))
    raise last or RuntimeError("Yahoo fundamentals request failed")


def _series(payload: dict, type_name: str) -> list[dict]:
    out = []
    for block in ((payload.get("timeseries") or {}).get("result") or []):
        if not isinstance(block, dict):
            continue
        meta_types = (block.get("meta") or {}).get("type") or []
        if type_name not in meta_types and type_name not in block:
            continue
        rows = block.get(type_name) or []
        for row in rows:
            try:
                value = float((row.get("reportedValue") or {}).get("raw"))
                date = str(row.get("asOfDate"))
                if date and math.isfinite(value):
                    out.append({"date": date, "value": value})
            except Exception:
                pass
    # de-duplicate by as-of date and return chronologically
    best = {x["date"]: x for x in out}
    return [best[k] for k in sorted(best)]


def _latest(payload: dict, names: list[str]) -> tuple[float | None, str | None]:
    for name in names:
        rows = _series(payload, name)
        if rows:
            return rows[-1]["value"], rows[-1]["date"]
    return None, None


def _yoy_quarter(payload: dict, name: str) -> tuple[float | None, str | None]:
    rows = _series(payload, name)
    if not rows:
        return None, None
    latest = rows[-1]
    if len(rows) < 5:
        return None, latest["date"]
    # Find roughly the same quarter one year earlier rather than blindly using index -5.
    latest_dt = datetime.fromisoformat(latest["date"]).date()
    prior = None
    for row in reversed(rows[:-1]):
        try:
            gap = (latest_dt - datetime.fromisoformat(row["date"]).date()).days
        except Exception:
            continue
        if 300 <= gap <= 430:
            prior = row
            break
    if prior is None or prior["value"] == 0:
        return None, latest["date"]
    return (latest["value"] / prior["value"] - 1.0) * 100.0, latest["date"]


def _company_metrics(ticker: str) -> dict:
    p = _fetch(ticker)
    rev_yoy, rev_end = _yoy_quarter(p, "quarterlyTotalRevenue")
    ni_yoy, ni_end = _yoy_quarter(p, "quarterlyNetIncome")
    annual_rev, annual_rev_end = _latest(p, ["annualTotalRevenue"])
    ocf, ocf_end = _latest(p, ["annualOperatingCashFlow"])
    capex, capex_end = _latest(p, ["annualCapitalExpenditure"])
    cash, cash_end = _latest(p, [
        "quarterlyCashCashEquivalentsAndShortTermInvestments",
        "quarterlyCashAndCashEquivalents",
        "quarterlyCashFinancial",
    ])
    assets, assets_end = _latest(p, ["quarterlyTotalAssets"])
    debt, debt_end = _latest(p, ["quarterlyTotalDebt"])

    fcf = None if ocf is None or capex is None else ocf + capex  # Yahoo capex is normally negative.
    cash_assets = _safe_div(cash, assets)
    fcf_margin = _safe_div(fcf, annual_rev)
    cash_debt = None if debt is None or debt <= 0 else _safe_div(cash, debt)
    ocf_debt = None if debt is None or debt <= 0 else _safe_div(ocf, debt)
    debt_assets = _safe_div(debt, assets)

    earnings = _score_earnings(rev_yoy, ni_yoy)
    liquidity = _score_liquidity(cash_assets, fcf_margin)
    debt_score = _score_debt(cash_debt, ocf_debt, debt_assets)
    ends = [x for x in (rev_end, ni_end, annual_rev_end, ocf_end, capex_end, cash_end, assets_end, debt_end) if x]
    return {
        "ticker": ticker,
        "asof": max(ends) if ends else None,
        "revenue_yoy_pct": round(rev_yoy, 2) if rev_yoy is not None else None,
        "net_income_yoy_pct": round(ni_yoy, 2) if ni_yoy is not None else None,
        "cash_assets_pct": round(cash_assets * 100, 2) if cash_assets is not None else None,
        "fcf_margin_pct": round(fcf_margin * 100, 2) if fcf_margin is not None else None,
        "cash_to_debt": round(cash_debt, 3) if cash_debt is not None else None,
        "ocf_to_debt": round(ocf_debt, 3) if ocf_debt is not None else None,
        "debt_assets_pct": round(debt_assets * 100, 2) if debt_assets is not None else None,
        "earnings_health_score": round(earnings, 2) if earnings is not None else None,
        "excess_cash_score": round(liquidity, 2) if liquidity is not None else None,
        "debt_capacity_score": round(debt_score, 2) if debt_score is not None else None,
    }


def _aggregate(rows: list[dict], key: str) -> float | None:
    vals = [float(x[key]) for x in rows if x.get(key) is not None and math.isfinite(float(x[key]))]
    return round(statistics.median(vals), 2) if vals else None


def build_fundamentals() -> dict:
    rows = []
    errors = {}
    for ticker in COMPANIES:
        try:
            rows.append(_company_metrics(ticker))
        except Exception as exc:
            errors[ticker] = repr(exc)
        time.sleep(0.12)
    asofs = [x.get("asof") for x in rows if x.get("asof")]
    signals = {
        "mega_earnings_health": _aggregate(rows, "earnings_health_score"),
        "mega_excess_cash": _aggregate(rows, "excess_cash_score"),
        "mega_debt_capacity": _aggregate(rows, "debt_capacity_score"),
    }
    return {
        "version": "MEGA-FUNDAMENTALS-V1.1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": "Yahoo Finance fundamentals timeseries",
        "source_note": "SEC Company Facts remains the preferred official source, but data.sec.gov returns HTTP 403 from GitHub-hosted runners in current tests. Yahoo is used as the automated fallback; scores remain context/archive only.",
        "method": "Median across AAPL/MSFT/NVDA/AMZN/GOOGL/META/TSLA/AVGO/AMD; quarterly revenue/net-income YoY, annual FCF, latest cash/assets/debt.",
        "feeds_market_model": False,
        "asof": max(asofs) if asofs else None,
        "company_count": len(rows),
        "signals": signals,
        "companies": rows,
        "errors": errors,
    }


if __name__ == "__main__":
    print(json.dumps(build_fundamentals(), ensure_ascii=False, indent=2))
