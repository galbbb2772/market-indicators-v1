from __future__ import annotations

import json
import math
import statistics
from datetime import datetime, timezone

import requests

HTTP = requests.Session()
HTTP.headers.update({
    "User-Agent": "MarketRegimeLab/1.0 research dashboard contact https://github.com/galbbb2772",
    "Accept-Encoding": "gzip, deflate",
})

COMPANIES = {
    "AAPL": "0000320193",
    "MSFT": "0000789019",
    "NVDA": "0001045810",
    "AMZN": "0001018724",
    "GOOGL": "0001652044",
    "META": "0001326801",
    "TSLA": "0001318605",
    "AVGO": "0001730168",
    "AMD": "0000002488",
}

REVENUE_TAGS = [
    "RevenueFromContractWithCustomerExcludingAssessedTax",
    "Revenues",
    "SalesRevenueNet",
]
NET_INCOME_TAGS = ["NetIncomeLoss", "ProfitLoss"]
OCF_TAGS = ["NetCashProvidedByUsedInOperatingActivities"]
CAPEX_TAGS = [
    "PaymentsToAcquirePropertyPlantAndEquipment",
    "PaymentsForAdditionsToPropertyPlantAndEquipment",
]
CASH_TAGS = [
    "CashAndCashEquivalentsAtCarryingValue",
    "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents",
]
ASSET_TAGS = ["Assets"]
DEBT_TAGS = [
    "LongTermDebtCurrent",
    "LongTermDebtNoncurrent",
    "LongTermDebt",
    "ShortTermBorrowings",
    "ShortTermDebtCurrent",
]


def _clip(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, float(x)))


def _safe_div(a: float | None, b: float | None) -> float | None:
    if a is None or b is None or not math.isfinite(a) or not math.isfinite(b) or abs(b) < 1e-12:
        return None
    return a / b


def _fetch(cik: str) -> dict:
    url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
    r = HTTP.get(url, timeout=20)
    r.raise_for_status()
    return r.json()


def _fact(payload: dict, tags: list[str]) -> dict | None:
    usgaap = ((payload.get("facts") or {}).get("us-gaap") or {})
    for tag in tags:
        obj = usgaap.get(tag)
        if isinstance(obj, dict):
            return obj
    return None


def _unit_rows(fact: dict | None) -> list[dict]:
    if not fact:
        return []
    units = fact.get("units") or {}
    preferred = []
    for unit in ("USD", "USD/shares", "pure"):
        rows = units.get(unit)
        if isinstance(rows, list) and rows:
            preferred = rows
            break
    if not preferred:
        for rows in units.values():
            if isinstance(rows, list) and rows:
                preferred = rows
                break
    return [x for x in preferred if isinstance(x, dict) and x.get("val") is not None]


def _duration_days(row: dict) -> int | None:
    try:
        a = datetime.fromisoformat(str(row["start"])).date()
        b = datetime.fromisoformat(str(row["end"])).date()
        return (b - a).days
    except Exception:
        return None


def _dedupe_period(rows: list[dict]) -> list[dict]:
    # Keep the latest-filed value for each period end/form combination.
    best = {}
    for row in rows:
        end = row.get("end")
        form = row.get("form")
        if not end or form not in {"10-Q", "10-K"}:
            continue
        key = (end, form)
        if key not in best or str(row.get("filed", "")) > str(best[key].get("filed", "")):
            best[key] = row
    return sorted(best.values(), key=lambda x: (str(x.get("end", "")), str(x.get("filed", ""))))


def _latest_quarter_and_yoy(fact: dict | None) -> tuple[float | None, float | None, str | None]:
    rows = _dedupe_period(_unit_rows(fact))
    q = []
    for row in rows:
        if row.get("form") != "10-Q":
            continue
        d = _duration_days(row)
        if d is not None and 65 <= d <= 115:
            q.append(row)
    if not q:
        return _latest_annual_and_yoy(fact)
    latest = q[-1]
    latest_end = datetime.fromisoformat(str(latest["end"])).date()
    prior = None
    for row in reversed(q[:-1]):
        try:
            end = datetime.fromisoformat(str(row["end"])).date()
        except Exception:
            continue
        gap = (latest_end - end).days
        if 300 <= gap <= 430:
            prior = row
            break
    cur = float(latest["val"])
    yoy = None if prior is None or float(prior["val"]) == 0 else (cur / float(prior["val"]) - 1.0) * 100.0
    return cur, yoy, str(latest.get("end"))


def _latest_annual_and_yoy(fact: dict | None) -> tuple[float | None, float | None, str | None]:
    rows = _dedupe_period(_unit_rows(fact))
    annual = []
    for row in rows:
        if row.get("form") != "10-K":
            continue
        d = _duration_days(row)
        if d is not None and 300 <= d <= 400:
            annual.append(row)
    if not annual:
        return None, None, None
    latest = annual[-1]
    prior = annual[-2] if len(annual) >= 2 else None
    cur = float(latest["val"])
    yoy = None if prior is None or float(prior["val"]) == 0 else (cur / float(prior["val"]) - 1.0) * 100.0
    return cur, yoy, str(latest.get("end"))


def _latest_instant(fact: dict | None) -> tuple[float | None, str | None]:
    rows = _dedupe_period(_unit_rows(fact))
    rows = [x for x in rows if x.get("form") in {"10-Q", "10-K"}]
    if not rows:
        return None, None
    latest = rows[-1]
    return float(latest["val"]), str(latest.get("end"))


def _annual_value(fact: dict | None) -> tuple[float | None, str | None]:
    val, _, end = _latest_annual_and_yoy(fact)
    return val, end


def _sum_latest_instants(payload: dict, tags: list[str]) -> tuple[float | None, str | None]:
    vals = []
    ends = []
    seen = set()
    usgaap = ((payload.get("facts") or {}).get("us-gaap") or {})
    for tag in tags:
        obj = usgaap.get(tag)
        if not isinstance(obj, dict) or tag in seen:
            continue
        seen.add(tag)
        val, end = _latest_instant(obj)
        if val is not None:
            vals.append(val)
            if end:
                ends.append(end)
    if not vals:
        return None, None
    # Avoid obvious double counting of LongTermDebt vs current/noncurrent pieces:
    # if aggregate LongTermDebt exists, prefer it plus short-term borrowings.
    aggregate = usgaap.get("LongTermDebt")
    agg_val, agg_end = _latest_instant(aggregate) if isinstance(aggregate, dict) else (None, None)
    if agg_val is not None:
        short = 0.0
        short_end = None
        for tag in ("ShortTermBorrowings", "ShortTermDebtCurrent"):
            obj = usgaap.get(tag)
            if isinstance(obj, dict):
                v, e = _latest_instant(obj)
                if v is not None:
                    short += v
                    short_end = e or short_end
        return agg_val + short, max([x for x in (agg_end, short_end) if x], default=agg_end)
    return sum(vals), max(ends) if ends else None


def _score_earnings(rev_yoy: float | None, ni_yoy: float | None) -> float | None:
    parts = []
    if rev_yoy is not None:
        # -20% revenue growth -> 0, 0% -> 40, +15% -> 70, +30% -> 100.
        parts.append(_clip(40.0 + 2.0 * rev_yoy, 0, 100))
    if ni_yoy is not None:
        # Profit is more volatile; use gentler slope and cap extremes.
        parts.append(_clip(45.0 + 0.75 * _clip(ni_yoy, -60, 80), 0, 100))
    return statistics.mean(parts) if parts else None


def _score_liquidity(cash_assets: float | None, fcf_margin: float | None) -> float | None:
    parts = []
    if cash_assets is not None:
        parts.append(_clip(20.0 + 240.0 * cash_assets, 0, 100))
    if fcf_margin is not None:
        parts.append(_clip(35.0 + 220.0 * fcf_margin, 0, 100))
    return statistics.mean(parts) if parts else None


def _score_debt(cash_debt: float | None, ocf_debt: float | None, debt_assets: float | None) -> float | None:
    parts = []
    if cash_debt is not None:
        parts.append(_clip(25.0 + 45.0 * min(cash_debt, 1.7), 0, 100))
    if ocf_debt is not None:
        parts.append(_clip(25.0 + 70.0 * min(ocf_debt, 1.1), 0, 100))
    if debt_assets is not None:
        parts.append(_clip(100.0 - 180.0 * debt_assets, 0, 100))
    return statistics.mean(parts) if parts else None


def _company_metrics(ticker: str, cik: str) -> dict:
    p = _fetch(cik)
    rev_fact = _fact(p, REVENUE_TAGS)
    ni_fact = _fact(p, NET_INCOME_TAGS)
    ocf_fact = _fact(p, OCF_TAGS)
    capex_fact = _fact(p, CAPEX_TAGS)
    cash_fact = _fact(p, CASH_TAGS)
    asset_fact = _fact(p, ASSET_TAGS)

    rev_q, rev_yoy, rev_end = _latest_quarter_and_yoy(rev_fact)
    ni_q, ni_yoy, ni_end = _latest_quarter_and_yoy(ni_fact)
    rev_a, rev_a_end = _annual_value(rev_fact)
    ocf_a, ocf_end = _annual_value(ocf_fact)
    capex_a, capex_end = _annual_value(capex_fact)
    cash, cash_end = _latest_instant(cash_fact)
    assets, assets_end = _latest_instant(asset_fact)
    debt, debt_end = _sum_latest_instants(p, DEBT_TAGS)

    fcf = None if ocf_a is None or capex_a is None else ocf_a - abs(capex_a)
    cash_assets = _safe_div(cash, assets)
    fcf_margin = _safe_div(fcf, rev_a)
    cash_debt = None if debt is None or debt <= 0 else _safe_div(cash, debt)
    ocf_debt = None if debt is None or debt <= 0 else _safe_div(ocf_a, debt)
    debt_assets = _safe_div(debt, assets)

    ends = [x for x in (rev_end, ni_end, rev_a_end, ocf_end, capex_end, cash_end, assets_end, debt_end) if x]
    return {
        "ticker": ticker,
        "cik": cik,
        "asof": max(ends) if ends else None,
        "revenue_yoy_pct": round(rev_yoy, 2) if rev_yoy is not None else None,
        "net_income_yoy_pct": round(ni_yoy, 2) if ni_yoy is not None else None,
        "cash_assets_pct": round(cash_assets * 100, 2) if cash_assets is not None else None,
        "fcf_margin_pct": round(fcf_margin * 100, 2) if fcf_margin is not None else None,
        "cash_to_debt": round(cash_debt, 3) if cash_debt is not None else None,
        "ocf_to_debt": round(ocf_debt, 3) if ocf_debt is not None else None,
        "debt_assets_pct": round(debt_assets * 100, 2) if debt_assets is not None else None,
        "earnings_health_score": round(_score_earnings(rev_yoy, ni_yoy), 2) if _score_earnings(rev_yoy, ni_yoy) is not None else None,
        "excess_cash_score": round(_score_liquidity(cash_assets, fcf_margin), 2) if _score_liquidity(cash_assets, fcf_margin) is not None else None,
        "debt_capacity_score": round(_score_debt(cash_debt, ocf_debt, debt_assets), 2) if _score_debt(cash_debt, ocf_debt, debt_assets) is not None else None,
    }


def _aggregate(rows: list[dict], key: str) -> float | None:
    vals = [float(x[key]) for x in rows if x.get(key) is not None and math.isfinite(float(x[key]))]
    return round(statistics.median(vals), 2) if vals else None


def build_sec_fundamentals() -> dict:
    rows = []
    errors = {}
    for ticker, cik in COMPANIES.items():
        try:
            rows.append(_company_metrics(ticker, cik))
        except Exception as exc:
            errors[ticker] = repr(exc)

    asofs = [x.get("asof") for x in rows if x.get("asof")]
    signals = {
        "mega_earnings_health": _aggregate(rows, "earnings_health_score"),
        "mega_excess_cash": _aggregate(rows, "excess_cash_score"),
        "mega_debt_capacity": _aggregate(rows, "debt_capacity_score"),
    }
    return {
        "version": "SEC-FUNDAMENTALS-V1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": "SEC data.sec.gov Company Facts API",
        "method": "Mega-cap median context score; quarterly revenue/net-income YoY where available, annual FCF, latest balance-sheet cash/assets/debt. Context/archive only pending forward validation.",
        "feeds_market_model": False,
        "asof": max(asofs) if asofs else None,
        "company_count": len(rows),
        "signals": signals,
        "companies": rows,
        "errors": errors,
    }


if __name__ == "__main__":
    print(json.dumps(build_sec_fundamentals(), ensure_ascii=False, indent=2))
