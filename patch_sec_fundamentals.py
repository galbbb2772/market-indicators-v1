from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from sec_fundamentals import build_sec_fundamentals

ROOT = Path(__file__).resolve().parent
DATA_PATH = ROOT / "docs" / "data" / "current.json"
HISTORY_PATH = ROOT / "docs" / "data" / "fundamental_history.json"
MARKET_TZ = ZoneInfo("America/New_York")


def _today() -> str:
    return datetime.now(MARKET_TZ).date().isoformat()


def _load(path: Path, fallback):
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        pass
    return fallback


def _series(history: list[dict], signal_id: str) -> list[tuple[str, float]]:
    out = []
    for row in history:
        v = (row.get("signals") or {}).get(signal_id)
        if v is None:
            continue
        try:
            out.append((str(row.get("date")), float(v)))
        except Exception:
            pass
    return out


def _patch_indicator(data: dict, history: list[dict], signal_id: str, raw_unit: str) -> None:
    sec = data.get("sec_fundamentals_v1") or {}
    score = (sec.get("signals") or {}).get(signal_id)
    if score is None:
        return
    vals = _series(history, signal_id)
    d1 = vals[-1][1] - vals[-2][1] if len(vals) >= 2 else None
    d2 = None
    if len(vals) >= 3:
        d2 = (vals[-1][1] - vals[-2][1]) - (vals[-2][1] - vals[-3][1])
    for item in data.get("indicators", []):
        if item.get("id") != signal_id:
            continue
        item["score"] = round(float(score), 2)
        item["raw"] = round(float(score), 2)
        item["raw_unit"] = raw_unit
        item["d1"] = round(d1, 2) if d1 is not None else None
        item["d2"] = round(d2, 2) if d2 is not None else None
        item["asof"] = sec.get("asof") or _today()
        item["history"] = [{"date": d, "score": round(v, 2)} for d, v in vals[-180:]]
        item["quality"] = "direct_sec_fundamental_context"
        item["source_note"] = (
            "SEC Company Facts V1; mega-cap median context score. Archive/context only; "
            "does not vote in Market Model V2 pending validation."
        )
        break


def main() -> None:
    data = _load(DATA_PATH, None)
    if not isinstance(data, dict):
        raise RuntimeError("docs/data/current.json is missing or invalid")

    sec = build_sec_fundamentals()
    data["sec_fundamentals_v1"] = sec

    today = _today()
    hist_obj = _load(HISTORY_PATH, {"version": "SEC-FUNDAMENTALS-HISTORY-V1", "history": []})
    history = list(hist_obj.get("history") or [])
    row = {
        "date": today,
        "generated_at": sec.get("generated_at"),
        "asof": sec.get("asof"),
        "company_count": sec.get("company_count"),
        "signals": sec.get("signals", {}),
        "errors": sec.get("errors", {}),
    }
    history = [x for x in history if x.get("date") != today]
    history.append(row)
    history = sorted(history, key=lambda x: x.get("date", ""))[-400:]
    hist_obj = {"version": "SEC-FUNDAMENTALS-HISTORY-V1", "history": history}

    _patch_indicator(data, history, "mega_earnings_health", "SEC fundamentals score / 0-100")
    _patch_indicator(data, history, "mega_excess_cash", "SEC liquidity score / 0-100")
    _patch_indicator(data, history, "mega_debt_capacity", "SEC debt-capacity score / 0-100")

    model = data.get("market_model_v2")
    if isinstance(model, dict):
        model["sec_fundamentals_status"] = {
            "connected": True,
            "version": sec.get("version"),
            "feeds_market_model": False,
            "company_count": sec.get("company_count"),
            "history_days": len(history),
        }

    DATA_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    HISTORY_PATH.write_text(json.dumps(hist_obj, ensure_ascii=False, indent=2), encoding="utf-8")
    print("SEC fundamentals updated:", json.dumps(sec.get("signals", {}), ensure_ascii=False), "errors:", len(sec.get("errors", {})))


if __name__ == "__main__":
    main()
