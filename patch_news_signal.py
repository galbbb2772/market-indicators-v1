from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from news_signal import build_news_signals

ROOT = Path(__file__).resolve().parent
DATA_PATH = ROOT / "docs" / "data" / "current.json"
HISTORY_PATH = ROOT / "docs" / "data" / "news_history.json"
MARKET_TZ = ZoneInfo("America/New_York")


def _market_today() -> str:
    return datetime.now(MARKET_TZ).date().isoformat()


def _load(path: Path, fallback):
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        pass
    return fallback


def _history_values(history: list[dict], signal_id: str) -> list[tuple[str, float]]:
    out = []
    for row in history:
        value = (row.get("signals") or {}).get(signal_id)
        if value is None:
            continue
        try:
            out.append((str(row.get("date")), float(value)))
        except Exception:
            continue
    return out


def _set_indicator(data: dict, indicator_id: str, signal_id: str, history: list[dict], quality: str) -> None:
    signal = ((data.get("news_signal_v1") or {}).get("signals") or {}).get(signal_id) or {}
    score = signal.get("score")
    if score is None:
        return
    values = _history_values(history, signal_id)
    d1 = values[-1][1] - values[-2][1] if len(values) >= 2 else None
    d2 = None
    if len(values) >= 3:
        d2 = (values[-1][1] - values[-2][1]) - (values[-2][1] - values[-3][1])
    for item in data.get("indicators", []):
        if item.get("id") != indicator_id:
            continue
        item["score"] = round(float(score), 2)
        item["raw"] = int(signal.get("event_count") or 0)
        item["raw_unit"] = "deduped news events / 24h"
        item["d1"] = round(float(d1), 2) if d1 is not None else None
        item["d2"] = round(float(d2), 2) if d2 is not None else None
        item["asof"] = values[-1][0] if values else _market_today()
        item["history"] = [{"date": d, "score": round(v, 2)} for d, v in values[-180:]]
        item["quality"] = quality
        item["source_note"] = "News Signal V1; context/archive only, no Market Model V2 vote."
        break


def main() -> None:
    data = _load(DATA_PATH, None)
    if not isinstance(data, dict):
        raise RuntimeError("docs/data/current.json is missing or invalid")

    news = build_news_signals()
    data["news_signal_v1"] = news

    # Keep daily history aligned with the U.S. market/session date.  The scheduled
    # workflow runs in the evening New York time, which can already be the next
    # UTC calendar day.
    today = _market_today()
    history_obj = _load(HISTORY_PATH, {"version": "NEWS-SIGNAL-HISTORY-V1", "history": []})
    history = list(history_obj.get("history") or [])
    score_row = {
        "date": today,
        "generated_at": news.get("generated_at"),
        "signals": {
            key: value.get("score")
            for key, value in (news.get("signals") or {}).items()
            if isinstance(value, dict)
        },
        "source_status": news.get("source_status", {})
    }
    history = [x for x in history if x.get("date") != today]
    history.append(score_row)
    history = sorted(history, key=lambda x: x.get("date", ""))[-400:]
    history_obj = {"version": "NEWS-SIGNAL-HISTORY-V1", "history": history}

    _set_indicator(
        data,
        indicator_id="ghost_story_density",
        signal_id="negative_narrative_density",
        history=history,
        quality="direct_news_text_context"
    )

    narrative = data.get("narrative_layer")
    if isinstance(narrative, dict):
        narrative["news_nlp_connected"] = True
        narrative["news_feeds_market_model"] = False
        narrative["news_context"] = {
            key: value.get("score")
            for key, value in (news.get("signals") or {}).items()
            if isinstance(value, dict)
        }
        narrative["news_note"] = (
            "News Signal V1 is context-only. Narrative scores remain quantitative-proxy based; "
            "news does not vote in Market Model V2 until forward validation."
        )

    model = data.get("market_model_v2")
    if isinstance(model, dict):
        model["news_signal_status"] = {
            "connected": True,
            "version": news.get("version"),
            "feeds_market_model": False,
            "history_days": len(history)
        }

    DATA_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    HISTORY_PATH.write_text(json.dumps(history_obj, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        "news signal updated:",
        json.dumps(
            {k: v.get("score") for k, v in (news.get("signals") or {}).items()},
            ensure_ascii=False
        )
    )


if __name__ == "__main__":
    main()
