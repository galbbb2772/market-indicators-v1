from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import requests

ROOT = Path(__file__).resolve().parent
DATA_PATH = ROOT / "docs" / "data" / "current.json"
BASE = "https://api.fiscaldata.treasury.gov/services/api/fiscal_service/v1/accounting/dts/"
HTTP = requests.Session()
HTTP.headers.update({"User-Agent":"Mozilla/5.0 MarketRegimeLab/1.0"})


def _fetch(endpoint: str) -> list[dict]:
    params = {
        "filter": "record_date:gte:2023-01-01",
        "sort": "record_date",
        "page[size]": "10000",
    }
    r = HTTP.get(BASE + endpoint, params=params, timeout=20)
    r.raise_for_status()
    rows = (r.json() or {}).get("data") or []
    if not rows:
        raise RuntimeError(f"Treasury {endpoint}: no rows")
    return rows


def _num(v):
    try:
        if v in (None, "", "null", "None"):
            return None
        return float(v)
    except Exception:
        return None


def _percentile(s: pd.Series, window: int = 504) -> pd.Series:
    s = pd.to_numeric(s, errors="coerce").astype(float)
    def f(a):
        a = a[np.isfinite(a)]
        if len(a) < 20:
            return np.nan
        return 100.0 * np.mean(a <= a[-1])
    return s.rolling(window, min_periods=60).apply(f, raw=True)


def _tga_series(rows: list[dict]) -> pd.Series:
    pts = {}
    for row in rows:
        account = str(row.get("account_type") or "")
        if "closing balance" not in account.lower() or "tga" not in account.lower():
            continue
        val = _num(row.get("close_today_bal"))
        # In the current DTS schema the closing-balance row is carried in open_today_bal.
        if val is None:
            val = _num(row.get("open_today_bal"))
        if val is None:
            continue
        dt = pd.to_datetime(row.get("record_date"), errors="coerce")
        if pd.isna(dt):
            continue
        pts[dt] = val
    if not pts:
        raise RuntimeError("Treasury operating_cash_balance: TGA closing rows missing")
    return pd.Series(pts, dtype=float).sort_index()


def _debt_headroom(rows: list[dict]) -> pd.Series:
    by_date = {}
    for row in rows:
        dt = pd.to_datetime(row.get("record_date"), errors="coerce")
        if pd.isna(dt):
            continue
        cat = str(row.get("debt_catg") or "").strip().lower()
        val = _num(row.get("close_today_bal"))
        if val is None:
            continue
        x = by_date.setdefault(dt, {})
        if cat == "statutory debt limit":
            x["limit"] = val
        elif "total public debt subject to limit" in cat:
            x["subject"] = val
    pts = {}
    for dt, x in by_date.items():
        if x.get("limit") is not None and x.get("subject") is not None:
            pts[dt] = x["limit"] - x["subject"]
    return pd.Series(pts, dtype=float).sort_index() if pts else pd.Series(dtype=float)


def _weighted_score(components: list[tuple[pd.Series, float]]) -> pd.Series:
    all_idx = pd.DatetimeIndex([])
    for s, _ in components:
        all_idx = all_idx.union(pd.DatetimeIndex(s.index))
    all_idx = all_idx.sort_values()
    cols = []
    ws = []
    for s, w in components:
        cols.append(s.reindex(all_idx).ffill())
        ws.append(float(w))
    frame = pd.concat(cols, axis=1)
    values = frame.to_numpy(dtype=float)
    valid = np.isfinite(values)
    w = np.array(ws, dtype=float)
    num = np.nansum(values * w, axis=1)
    den = np.sum(valid * w, axis=1)
    return pd.Series(np.where(den > 0, num / den, np.nan), index=all_idx).clip(0,100).dropna()


def main() -> None:
    data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    ocb = _fetch("operating_cash_balance")
    debt = _fetch("debt_subject_to_limit")
    tga = _tga_series(ocb)
    headroom = _debt_headroom(debt)

    # 55% cash-buffer level, 25% four-week cash drawdown, 20% debt-limit headroom.
    # Debt-limit component is naturally omitted during legal suspension periods.
    low_tga = 100.0 - _percentile(tga)
    tga_draw = -(tga.pct_change(20) * 100.0)
    draw_stress = _percentile(tga_draw)
    components = [(low_tga, 0.55), (draw_stress, 0.25)]
    headroom_stress = pd.Series(dtype=float)
    if len(headroom.dropna()) >= 60:
        headroom_stress = 100.0 - _percentile(headroom)
        components.append((headroom_stress, 0.20))

    stress = _weighted_score(components)
    if stress.empty:
        raise RuntimeError("Treasury short-term stress score is empty")

    d1 = stress.diff(); d2 = d1.diff()
    last_tga_m = float(tga.iloc[-1])
    last_headroom_m = float(headroom.iloc[-1]) if not headroom.empty else None

    for item in data.get("indicators", []):
        if item.get("id") != "treasury_short_default":
            continue
        item["score"] = round(float(stress.iloc[-1]), 2)
        item["raw"] = round(last_tga_m / 1000.0, 2)
        item["raw_unit"] = "USD billions TGA; Treasury cash/funding-stress proxy"
        item["d1"] = round(float(d1.dropna().iloc[-1]), 2) if not d1.dropna().empty else None
        item["d2"] = round(float(d2.dropna().iloc[-1]), 2) if not d2.dropna().empty else None
        item["asof"] = str(stress.index[-1].date())
        item["history"] = [{"date":str(i.date()),"score":round(float(v),2)} for i,v in stress.tail(180).items()]
        item["quality"] = "official_treasury_context"
        item["source_note"] = (
            "U.S. Treasury Fiscal Data Daily Treasury Statement: Operating Cash Balance + Debt Subject to Limit. "
            "This is a short-term cash/funding-stress proxy, NOT a literal sovereign default probability. "
            "Archive/context only; no Market Model V2 vote."
        )
        item["context_detail"] = {
            "tga_closing_balance_usd_bn": round(last_tga_m / 1000.0, 2),
            "debt_limit_headroom_usd_bn": round(last_headroom_m / 1000.0, 2) if last_headroom_m is not None else None,
            "components": {
                "low_tga_weight": 0.55,
                "tga_drawdown_weight": 0.25,
                "debt_limit_headroom_weight_when_available": 0.20,
            },
        }
        break

    model = data.get("market_model_v2")
    if isinstance(model, dict):
        model["treasury_short_stress_status"] = {
            "connected": True,
            "feeds_market_model": False,
            "source": "U.S. Treasury Fiscal Data / Daily Treasury Statement",
            "latest_tga_usd_bn": round(last_tga_m / 1000.0, 2),
            "latest_debt_limit_headroom_usd_bn": round(last_headroom_m / 1000.0, 2) if last_headroom_m is not None else None,
            "interpretation": "cash/funding stress proxy, not default probability"
        }

    DATA_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        "Treasury short stress:", round(float(stress.iloc[-1]),2),
        "TGA bn", round(last_tga_m/1000.0,2),
        "headroom bn", round(last_headroom_m/1000.0,2) if last_headroom_m is not None else None,
    )


if __name__ == "__main__":
    main()
