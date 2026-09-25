from __future__ import annotations

import json

from market_reaction import build_market_reaction
from news_signal import build_news_signals

SIGNAL_TO_REACTION = {
    "us_policy_event_sentiment": "policy",
    "geopolitical_news_risk": "geopolitical",
    "systemic_news_risk": "systemic",
    "ai_narrative_risk": "ai",
    "negative_narrative_density": "negative_narrative",
}


def build_confirmed_news_signals() -> dict:
    news = build_news_signals()
    reaction = build_market_reaction()
    categories = reaction.get("categories") or {}

    for signal_id, category in SIGNAL_TO_REACTION.items():
        signal = (news.get("signals") or {}).get(signal_id)
        if not isinstance(signal, dict):
            continue
        confirm = categories.get(category) or {}
        confirmation_score = float(confirm.get("score") or 0.0)
        raw_score = float(signal.get("score") or 0.0)
        # Research-only view: preserve at least 50% of the text signal and let
        # observed market reaction add the other 50%.  This is NOT fed into
        # Market Model V2; it exists so forward tests can compare raw vs confirmed.
        adjusted = raw_score * (0.50 + 0.50 * confirmation_score / 100.0)
        signal["market_confirmation"] = confirm
        signal["reaction_adjusted_score"] = round(adjusted, 2)

    news["version"] = "NEWS-SIGNAL-V1.4"
    news["market_reaction"] = reaction
    news["feeds_market_model"] = False
    news["policy"] = (
        "News Signal V1.4 records both text risk and observed VIX/WTI/gold/SPY reaction. "
        "Neither the raw news score nor reaction-adjusted score votes in Market Model V2 "
        "until forward validation is available."
    )
    return news


if __name__ == "__main__":
    print(json.dumps(build_confirmed_news_signals(), ensure_ascii=False, indent=2))
