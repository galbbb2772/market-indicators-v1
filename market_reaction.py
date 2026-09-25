from __future__ import annotations

import math
from urllib.parse import quote

import requests

HTTP = requests.Session()
HTTP.headers.update({"User-Agent": "Mozilla/5.0 MarketRegimeLab-MarketReaction/1.0"})

ASSETS = {
    "vix": {"symbol": "^VIX", "label": "VIX", "threshold_1d": 5.0},
    "oil": {"symbol": "CL=F", "label": "WTI原油", "threshold_1d": 2.0},
    "gold": {"symbol": "GC=F", "label": "黄金", "threshold_1d": 1.0},
    "spy": {"symbol": "SPY", "label": "SPY", "threshold_1d": 1.0},
}

# +1 means an increase confirms risk; -1 means a decline confirms risk.
CATEGORY_WEIGHTS = {
    "policy": {"vix": (0.45, +1), "spy": (0.45, -1), "gold": (0.10, +1)},
    "geopolitical": {"oil": (0.35, +1), "gold": (0.25, +1), "vix": (0.25, +1), "spy": (0.15, -1)},
    "systemic": {"vix": (0.40, +1), "spy": (0.35, -1), "gold": (0.15, +1), "oil": (0.10, -1)},
    "ai": {"spy": (0.65, -1), "vix": (0.35, +1)},
    "negative_narrative": {"vix": (0.45, +1), "spy": (0.40, -1), "gold": (0.15, +1)},
}


def _request(url: str, timeout: int = 12) -> requests.Response:
    last = None
    for base in (url, url.replace("query1.finance.yahoo.com", "query2.finance.yahoo.com")):
        try:
            r = HTTP.get(base, timeout=timeout)
            if r.ok:
                return r
            last = RuntimeError(f"HTTP {r.status_code}: {r.text[:160]}")
        except Exception as exc:
            last = exc
    raise last or RuntimeError("request failed")


def _price_changes(symbol: str) -> dict:
    sym = quote(symbol, safe="")
    url = (
        f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}"
        "?range=15d&interval=1d&events=history&includeAdjustedClose=true"
    )
    data = _request(url).json()
    res = (data.get("chart") or {}).get("result")
    if not res:
        raise ValueError(str((data.get("chart") or {}).get("error")))
    obj = res[0]
    ts = obj.get("timestamp") or []
    q = ((obj.get("indicators") or {}).get("quote") or [{}])[0]
    adj = ((obj.get("indicators") or {}).get("adjclose") or [{}])[0].get("adjclose")
    closes = adj if adj and len(adj) == len(ts) else q.get("close")
    rows = [(t, float(c)) for t, c in zip(ts, closes or []) if c is not None]
    if len(rows) < 2:
        raise ValueError("not enough price history")
    last_t, last_close = rows[-1]
    prev_close = rows[-2][1]
    base_5d = rows[-6][1] if len(rows) >= 6 else rows[0][1]
    d1 = (last_close / prev_close - 1.0) * 100.0
    d5 = (last_close / base_5d - 1.0) * 100.0
    return {
        "close": round(last_close, 4),
        "day_pct": round(d1, 3),
        "five_day_pct": round(d5, 3),
        "timestamp": int(last_t),
    }


def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, float(x)))


def _direction_strength(day_pct: float, five_day_pct: float, direction: int, threshold_1d: float) -> tuple[float, float]:
    # 70% current-day reaction + 30% short-window persistence.  5D needs roughly
    # twice the one-day threshold to count as fully confirming.
    signed_1d = direction * day_pct
    signed_5d = direction * five_day_pct
    confirm = 0.70 * _clamp01(signed_1d / threshold_1d) + 0.30 * _clamp01(signed_5d / (2.0 * threshold_1d))
    contradict = 0.70 * _clamp01(-signed_1d / threshold_1d) + 0.30 * _clamp01(-signed_5d / (2.0 * threshold_1d))
    return confirm, contradict


def _state(score: float, contradiction: float) -> str:
    if score >= 60 and contradiction < 35:
        return "confirmed"
    if score >= 30:
        return "partial"
    if contradiction >= 60:
        return "contradicted"
    return "unconfirmed"


def build_market_reaction() -> dict:
    assets: dict[str, dict] = {}
    errors: dict[str, str] = {}
    for key, cfg in ASSETS.items():
        try:
            row = _price_changes(cfg["symbol"])
            row["label"] = cfg["label"]
            row["symbol"] = cfg["symbol"]
            assets[key] = row
        except Exception as exc:
            errors[key] = repr(exc)

    categories = {}
    for category, spec in CATEGORY_WEIGHTS.items():
        used_weight = 0.0
        confirm_sum = 0.0
        contradict_sum = 0.0
        detail = []
        for asset_key, (weight, direction) in spec.items():
            row = assets.get(asset_key)
            if not row:
                continue
            threshold = float(ASSETS[asset_key]["threshold_1d"])
            confirm, contradict = _direction_strength(
                float(row["day_pct"]), float(row["five_day_pct"]), int(direction), threshold
            )
            used_weight += weight
            confirm_sum += weight * confirm
            contradict_sum += weight * contradict
            detail.append({
                "asset": asset_key,
                "label": row["label"],
                "expected_direction": "up" if direction > 0 else "down",
                "day_pct": row["day_pct"],
                "five_day_pct": row["five_day_pct"],
                "weight": weight,
                "confirm_strength": round(confirm * 100.0, 1),
                "contradict_strength": round(contradict * 100.0, 1),
            })
        if used_weight <= 0:
            score = 0.0
            contradiction = 0.0
        else:
            score = 100.0 * confirm_sum / used_weight
            contradiction = 100.0 * contradict_sum / used_weight
        categories[category] = {
            "score": round(score, 2),
            "contradiction_score": round(contradiction, 2),
            "state": _state(score, contradiction),
            "confirmed_by": [x["label"] for x in detail if x["confirm_strength"] >= 45.0],
            "contradicted_by": [x["label"] for x in detail if x["contradict_strength"] >= 45.0],
            "assets": detail,
        }

    return {
        "version": "MARKET-REACTION-V1",
        "method": "70% 1D + 30% 5D directional confirmation; category-specific asset weights",
        "assets": assets,
        "categories": categories,
        "errors": errors,
    }


if __name__ == "__main__":
    import json
    print(json.dumps(build_market_reaction(), ensure_ascii=False, indent=2))
