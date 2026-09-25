from __future__ import annotations

import hashlib
import html
import json
import math
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.parse import urlparse

import requests

ROOT = Path(__file__).resolve().parent
KEYWORDS_PATH = ROOT / "news_keywords.json"
SOURCES_PATH = ROOT / "news_sources.json"

HTTP = requests.Session()
HTTP.headers.update({
    "User-Agent": "MarketRegimeLab-News/1.0 (+https://github.com/galbbb2772/market-indicators-v1)"
})

RISK_TERMS = {
    "crisis": 1.0, "crash": 1.0, "default": 1.0, "panic": 0.9, "contagion": 1.0,
    "bank failure": 1.0, "bankruptcy": 0.9, "recession": 0.8, "war": 0.9,
    "missile": 0.9, "attack": 0.8, "sanction": 0.6, "tariff": 0.5,
    "liquidity stress": 0.9, "credit stress": 0.9, "debt ceiling": 0.8,
    "emergency": 0.8, "downgrade": 0.8, "bubble": 0.6, "layoff": 0.5,
}
RELIEF_TERMS = {
    "ceasefire": 0.9, "de-escalation": 0.9, "deal reached": 0.8, "agreement reached": 0.8,
    "rate cut": 0.5, "liquidity support": 0.8, "stabilize": 0.5, "rescue": 0.6,
}

DEFAULT_SOURCES = {
    "gdelt": {
        "enabled": True,
        "endpoint": "https://api.gdeltproject.org/api/v2/doc/doc",
        "timespan": "24h",
        "maxrecords": 75
    },
    "fed_all": {
        "enabled": True,
        "url": "https://www.federalreserve.gov/feeds/press_all.xml",
        "kind": "official_rss"
    },
    "fed_monetary": {
        "enabled": True,
        "url": "https://www.federalreserve.gov/feeds/press_monetary.xml",
        "kind": "official_rss"
    },
    "sec_press": {
        "enabled": True,
        "url": "https://www.sec.gov/news/pressreleases.rss",
        "kind": "official_rss"
    }
}

DEFAULT_KEYWORDS = {
    "policy": ["Federal Reserve", "FOMC", "interest rates", "tariff", "trade policy", "Treasury"],
    "geopolitical": ["war", "conflict", "sanctions", "missile", "ceasefire", "geopolitical"],
    "systemic": ["bank failure", "liquidity crisis", "credit stress", "default", "debt ceiling", "funding stress"],
    "ai": ["artificial intelligence", "AI spending", "AI capex", "AI bubble", "data center debt", "AI regulation"],
    "negative_narrative": ["recession", "crash", "crisis", "panic", "default", "bubble", "contagion"]
}


def _load_json(path: Path, fallback: dict) -> dict:
    try:
        if path.exists():
            obj = json.loads(path.read_text(encoding="utf-8"))
            return obj if isinstance(obj, dict) else fallback
    except Exception:
        pass
    return fallback


def _clean(text: str | None) -> str:
    text = html.unescape(text or "")
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _norm_title(title: str) -> str:
    s = re.sub(r"[^a-z0-9 ]+", " ", title.lower())
    stop = {"the", "a", "an", "to", "of", "in", "on", "for", "and", "or", "with", "as", "at", "by"}
    return " ".join(x for x in s.split() if x not in stop)[:220]


def _event_key(title: str) -> str:
    norm = _norm_title(title)
    words = norm.split()
    core = " ".join(words[:12])
    return hashlib.sha1(core.encode("utf-8")).hexdigest()[:14]


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    s = value.strip()
    for fmt in ("%Y%m%dT%H%M%SZ", "%Y%m%d%H%M%S", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(s, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            pass
    try:
        dt = parsedate_to_datetime(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return None


def _age_hours(dt: datetime | None) -> float:
    if dt is None:
        return 24.0
    return max(0.0, (datetime.now(timezone.utc) - dt).total_seconds() / 3600.0)


def _token_match(text: str, terms: list[str]) -> list[str]:
    lo = text.lower()
    return [t for t in terms if t.lower() in lo]


def _severity(text: str) -> float:
    lo = text.lower()
    risk = sum(w for term, w in RISK_TERMS.items() if term in lo)
    relief = sum(w for term, w in RELIEF_TERMS.items() if term in lo)
    return max(-1.0, min(1.0, (risk - relief) / 2.2))


def _fetch_gdelt(category: str, terms: list[str], cfg: dict, errors: dict) -> list[dict]:
    terms = [t.strip() for t in terms if t.strip()]
    if not terms:
        return []
    query_terms = " OR ".join(f'"{t}"' if " " in t else t for t in terms[:12])
    params = {
        "query": f"({query_terms}) sourcelang:English",
        "mode": "ArtList",
        "maxrecords": int(cfg.get("maxrecords", 75)),
        "format": "json",
        "sort": "HybridRel",
        "timespan": cfg.get("timespan", "24h")
    }
    try:
        r = HTTP.get(cfg.get("endpoint", DEFAULT_SOURCES["gdelt"]["endpoint"]), params=params, timeout=25)
        r.raise_for_status()
        payload = r.json()
        rows = payload.get("articles") or []
        out = []
        for row in rows:
            title = _clean(row.get("title"))
            if not title:
                continue
            url = row.get("url") or ""
            out.append({
                "title": title,
                "url": url,
                "source": row.get("domain") or urlparse(url).netloc or "gdelt",
                "published_at": row.get("seendate"),
                "published_dt": _parse_dt(row.get("seendate")),
                "origin": "gdelt",
                "query_category": category,
                "text": title
            })
        return out
    except Exception as exc:
        errors[f"gdelt:{category}"] = repr(exc)
        return []


def _fetch_rss(source_id: str, cfg: dict, errors: dict) -> list[dict]:
    try:
        r = HTTP.get(cfg["url"], timeout=20)
        r.raise_for_status()
        root = ET.fromstring(r.content)
        out = []
        for item in root.findall(".//item"):
            title = _clean(item.findtext("title"))
            desc = _clean(item.findtext("description"))
            link = _clean(item.findtext("link"))
            pub = _clean(item.findtext("pubDate"))
            if not title:
                continue
            out.append({
                "title": title,
                "url": link,
                "source": source_id,
                "published_at": pub,
                "published_dt": _parse_dt(pub),
                "origin": "official",
                "query_category": None,
                "text": f"{title} {desc}".strip()
            })
        return out
    except Exception as exc:
        errors[f"rss:{source_id}"] = repr(exc)
        return []


def _classify(article: dict, keywords: dict) -> list[str]:
    text = article.get("text", article.get("title", ""))
    cats = []
    for category, terms in keywords.items():
        if _token_match(text, terms):
            cats.append(category)
    hinted = article.get("query_category")
    if hinted and hinted not in cats:
        cats.append(hinted)
    return cats


def _dedupe(rows: list[dict]) -> list[dict]:
    groups: dict[str, dict] = {}
    for row in rows:
        key = _event_key(row["title"])
        item = groups.get(key)
        if item is None:
            item = dict(row)
            item["sources"] = {row["source"]}
            item["origins"] = {row["origin"]}
            item["categories"] = set(row.get("categories", []))
            groups[key] = item
        else:
            item["sources"].add(row["source"])
            item["origins"].add(row["origin"])
            item["categories"].update(row.get("categories", []))
            if _age_hours(row.get("published_dt")) < _age_hours(item.get("published_dt")):
                for k in ("title", "url", "published_at", "published_dt", "text"):
                    item[k] = row.get(k)
    out = []
    for item in groups.values():
        item["sources"] = sorted(item["sources"])
        item["origins"] = sorted(item["origins"])
        item["categories"] = sorted(item["categories"])
        out.append(item)
    out.sort(key=lambda x: _age_hours(x.get("published_dt")))
    return out


def _category_signal(events: list[dict], category: str) -> dict:
    rows = [x for x in events if category in x.get("categories", [])]
    if not rows:
        return {"score": 0.0, "event_count": 0, "source_count": 0, "top_events": []}
    weighted_risk = 0.0
    weighted_attention = 0.0
    source_names = set()
    ranked = []
    for x in rows:
        age = _age_hours(x.get("published_dt"))
        decay = math.exp(-age / 18.0)
        sev = _severity(x.get("text", x["title"]))
        source_count = max(1, len(x.get("sources", [])))
        confirmation = min(1.45, 1.0 + 0.12 * (source_count - 1))
        official = 1.18 if "official" in x.get("origins", []) else 1.0
        weight = decay * confirmation * official
        risk_component = max(0.0, sev) * weight
        attention_component = weight
        weighted_risk += risk_component
        weighted_attention += attention_component
        source_names.update(x.get("sources", []))
        ranked.append((risk_component + 0.20 * attention_component, x, sev))
    density = 100.0 * (1.0 - math.exp(-weighted_attention / 6.0))
    risk = 100.0 * (1.0 - math.exp(-weighted_risk / 3.5))
    score = min(100.0, 0.65 * risk + 0.35 * density)
    ranked.sort(key=lambda z: z[0], reverse=True)
    top = []
    for _, x, sev in ranked[:8]:
        top.append({
            "title": x["title"],
            "url": x.get("url"),
            "sources": x.get("sources", []),
            "origins": x.get("origins", []),
            "age_hours": round(_age_hours(x.get("published_dt")), 1),
            "severity": round(float(sev), 3)
        })
    return {
        "score": round(float(score), 2),
        "risk_component": round(float(risk), 2),
        "attention_component": round(float(density), 2),
        "event_count": len(rows),
        "source_count": len(source_names),
        "top_events": top
    }


def build_news_signals() -> dict:
    source_cfg = _load_json(SOURCES_PATH, {"sources": DEFAULT_SOURCES}).get("sources", DEFAULT_SOURCES)
    if isinstance(source_cfg, list):
        source_cfg = DEFAULT_SOURCES
    keywords = _load_json(KEYWORDS_PATH, DEFAULT_KEYWORDS)
    errors: dict[str, str] = {}
    rows: list[dict] = []

    gdelt_cfg = source_cfg.get("gdelt", DEFAULT_SOURCES["gdelt"])
    if gdelt_cfg.get("enabled", True):
        for category, terms in keywords.items():
            rows.extend(_fetch_gdelt(category, list(terms), gdelt_cfg, errors))

    for source_id, cfg in source_cfg.items():
        if source_id == "gdelt" or not isinstance(cfg, dict) or not cfg.get("enabled", True):
            continue
        if cfg.get("kind") == "official_rss":
            rows.extend(_fetch_rss(source_id, cfg, errors))

    for row in rows:
        row["categories"] = _classify(row, keywords)
    events = _dedupe(rows)

    signals = {category: _category_signal(events, category) for category in keywords}
    policy = signals.get("policy", {})
    geo = signals.get("geopolitical", {})
    systemic = signals.get("systemic", {})
    ai = signals.get("ai", {})
    negative = signals.get("negative_narrative", {})

    all_sources = set()
    for x in events:
        all_sources.update(x.get("sources", []))
    return {
        "version": "NEWS-SIGNAL-V1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "feeds_market_model": False,
        "policy": "News is an explanatory/context layer in V1. It does not vote in Market Model V2 until forward validation is available.",
        "source_status": {
            "configured": sorted(source_cfg.keys()),
            "unique_sources_seen": len(all_sources),
            "article_rows_before_dedupe": len(rows),
            "events_after_dedupe": len(events),
            "errors": errors
        },
        "signals": {
            "us_policy_event_sentiment": {
                "score": policy.get("score", 0.0),
                "note": "Market-relevant U.S. policy/monetary/regulatory event risk and attention; not a score of any political person or party.",
                **{k: v for k, v in policy.items() if k != "score"}
            },
            "geopolitical_news_risk": {
                "score": geo.get("score", 0.0),
                **{k: v for k, v in geo.items() if k != "score"}
            },
            "systemic_news_risk": {
                "score": systemic.get("score", 0.0),
                **{k: v for k, v in systemic.items() if k != "score"}
            },
            "ai_narrative_risk": {
                "score": ai.get("score", 0.0),
                **{k: v for k, v in ai.items() if k != "score"}
            },
            "negative_narrative_density": {
                "score": negative.get("score", 0.0),
                **{k: v for k, v in negative.items() if k != "score"}
            }
        }
    }


if __name__ == "__main__":
    print(json.dumps(build_news_signals(), ensure_ascii=False, indent=2))
