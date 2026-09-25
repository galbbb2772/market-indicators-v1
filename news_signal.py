from __future__ import annotations

import hashlib
import html
import json
import math
import re
import time
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
    "User-Agent": "MarketRegimeLab-News/1.3 (+https://github.com/galbbb2772/market-indicators-v1)"
})

RISK_TERMS = {
    "crisis": 1.0, "crash": 1.0, "default": 1.0, "panic": 0.9, "contagion": 1.0,
    "bank failure": 1.0, "bankruptcy": 0.9, "recession": 0.8, "war": 0.9,
    "missile": 0.9, "attack": 0.8, "sanction": 0.6, "sanctions": 0.6, "tariff": 0.5,
    "liquidity stress": 0.9, "credit stress": 0.9, "debt ceiling": 0.8,
    "emergency": 0.8, "downgrade": 0.8, "bubble": 0.6, "layoff": 0.5,
}
RELIEF_TERMS = {
    "ceasefire": 0.9, "de-escalation": 0.9, "deal reached": 0.8, "agreement reached": 0.8,
    "rate cut": 0.5, "liquidity support": 0.8, "stabilize": 0.5, "rescue": 0.6,
}

# Google News is only the broad discovery layer.  These anchors force each
# category to stay in a financial/economic context instead of treating every
# mention of "war", "default", "crash" or "AI" as a market event.
MARKET_CONTEXT = {
    "policy": [
        "market", "markets", "economy", "economic", "inflation", "stock", "stocks",
        "bond", "bonds", "rate", "rates", "trade", "prices", "earnings",
    ],
    "geopolitical": [
        "market", "markets", "oil", "energy", "shipping", "stock", "stocks", "bond",
        "bonds", "economy", "economic", "trade", "supply", "prices", "commodity",
        "commodities", "company", "companies", "operations",
    ],
    "systemic": [
        "bank", "banks", "banking", "credit", "bond", "bonds", "finance", "financial",
        "market", "markets", "economy", "economic", "funding", "liquidity", "debt",
    ],
    "ai": [
        "stock", "stocks", "market", "markets", "investment", "investor", "investors",
        "capex", "earnings", "debt", "finance", "financing", "valuation", "valuations",
        "revenue", "profit", "spending", "data center", "hyperscaler", "chip", "chips",
        "semiconductor", "semiconductors",
    ],
    "negative_narrative": [
        "stock", "stocks", "market", "markets", "economy", "economic", "bank", "banking",
        "credit", "bond", "bonds", "finance", "financial", "investor", "investors",
        "recession",
    ],
}

QUERY_EXCLUSIONS = {
    "geopolitical": ["game", "gaming", "movie", "film", "sports"],
    "negative_narrative": ["traffic", "car crash", "road crash", "plane crash"],
}

DEFAULT_SOURCES = {
    "google_news": {
        "enabled": True,
        "kind": "google_news_search",
        "endpoint": "https://news.google.com/rss/search",
        "hl": "en-US",
        "gl": "US",
        "ceid": "US:en",
        "max_age_hours": 36,
    },
    "gdelt": {
        "enabled": False,
        "endpoint": "https://api.gdeltproject.org/api/v2/doc/doc",
        "timespan": "24h",
        "maxrecords": 250,
    },
    "fed_monetary": {
        "enabled": True,
        "url": "https://www.federalreserve.gov/feeds/press_monetary.xml",
        "kind": "official_rss",
        "max_age_hours": 72,
    },
    "sec_press": {
        "enabled": True,
        "url": "https://www.sec.gov/news/pressreleases.rss",
        "kind": "official_rss",
        "max_age_hours": 72,
    },
}

DEFAULT_KEYWORDS = {
    "policy": ["Federal Reserve", "FOMC", "interest rates", "tariff", "tariffs", "trade policy", "Treasury Department"],
    "geopolitical": ["war", "armed conflict", "sanctions", "missile", "ceasefire", "geopolitical", "Iran", "Ukraine", "Russia", "Israel"],
    "systemic": ["bank failure", "banking crisis", "liquidity crisis", "credit stress", "credit crisis", "debt default", "sovereign default", "debt ceiling", "funding stress", "credit spreads"],
    "ai": ["artificial intelligence", "AI spending", "AI capex", "AI bubble", "data center debt", "AI regulation", "hyperscaler capex"],
    "negative_narrative": ["recession", "market crash", "stock market crash", "financial crisis", "credit crisis", "debt crisis", "market panic", "debt default", "sovereign default", "asset bubble", "stock bubble", "contagion"],
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
    core = " ".join(_norm_title(title).split()[:12])
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


def _contains_term(text: str, term: str) -> bool:
    t = re.sub(r"\s+", " ", (term or "").strip().lower())
    if not t:
        return False
    pattern = re.escape(t).replace(r"\ ", r"\s+")
    return re.search(r"(?<![a-z0-9])" + pattern + r"(?![a-z0-9])", text.lower()) is not None


def _token_match(text: str, terms: list[str]) -> list[str]:
    return [t for t in terms if _contains_term(text, t)]


def _severity(text: str) -> float:
    risk = sum(w for term, w in RISK_TERMS.items() if _contains_term(text, term))
    relief = sum(w for term, w in RELIEF_TERMS.items() if _contains_term(text, term))
    return max(-1.0, min(1.0, (risk - relief) / 2.2))


def _rss_items(content: bytes) -> list[ET.Element]:
    root = ET.fromstring(content)
    return list(root.findall(".//item"))


def _google_query(category: str, terms: list[str]) -> str:
    query_terms = " OR ".join(f'"{t}"' if " " in t else t for t in terms if t.strip())
    context_terms = MARKET_CONTEXT.get(category, [])
    context = " OR ".join(f'"{t}"' if " " in t else t for t in context_terms)
    exclusions = " ".join(f'-"{t}"' if " " in t else f"-{t}" for t in QUERY_EXCLUSIONS.get(category, []))
    pieces = [f"({query_terms})"]
    if context:
        pieces.append(f"({context})")
    if exclusions:
        pieces.append(exclusions)
    pieces.append("when:1d")
    return " ".join(pieces)


def _fetch_google_news(category: str, terms: list[str], cfg: dict, errors: dict) -> list[dict]:
    query = _google_query(category, terms)
    if not query:
        return []
    params = {
        "q": query,
        "hl": cfg.get("hl", "en-US"),
        "gl": cfg.get("gl", "US"),
        "ceid": cfg.get("ceid", "US:en"),
    }
    try:
        r = HTTP.get(cfg.get("endpoint", DEFAULT_SOURCES["google_news"]["endpoint"]), params=params, timeout=20)
        r.raise_for_status()
        max_age = float(cfg.get("max_age_hours", 36))
        out = []
        for item in _rss_items(r.content):
            title = _clean(item.findtext("title"))
            link = _clean(item.findtext("link"))
            pub = _clean(item.findtext("pubDate"))
            dt = _parse_dt(pub)
            source_el = item.find("source")
            source_name = _clean(source_el.text if source_el is not None else "") or "Google News"
            if not title or (dt is not None and _age_hours(dt) > max_age):
                continue
            # Precision gate: a discovery result must show both a category term and
            # a financial/economic anchor in the headline itself.  Search-body-only
            # matches are discarded so generic politics, gaming and accident stories
            # cannot contaminate the signal.
            if not _token_match(title, terms):
                continue
            anchors = MARKET_CONTEXT.get(category, [])
            if anchors and not _token_match(title, anchors):
                continue
            out.append({
                "title": title,
                "url": link,
                "source": source_name,
                "published_at": pub,
                "published_dt": dt,
                "origin": "google_news",
                "query_category": category,
                "text": title,
            })
        return out
    except Exception as exc:
        errors[f"google_news:{category}"] = repr(exc)
        return []


def _gdelt_query_terms(keywords: dict[str, list[str]]) -> list[str]:
    out, seen = [], set()
    for terms in keywords.values():
        for term in terms:
            key = term.strip().lower()
            if key and key not in seen:
                seen.add(key)
                out.append(term.strip())
    return out


def _fetch_gdelt(keywords: dict[str, list[str]], cfg: dict, errors: dict) -> list[dict]:
    terms = _gdelt_query_terms(keywords)
    if not terms:
        return []
    query_terms = " OR ".join(f'"{t}"' if " " in t else t for t in terms)
    params = {
        "query": f"({query_terms}) sourcelang:English",
        "mode": "ArtList",
        "maxrecords": min(250, int(cfg.get("maxrecords", 250))),
        "format": "json",
        "sort": "HybridRel",
        "timespan": cfg.get("timespan", "24h"),
    }
    endpoint = cfg.get("endpoint", DEFAULT_SOURCES["gdelt"]["endpoint"])
    last_error: Exception | None = None
    for attempt in range(2):
        try:
            r = HTTP.get(endpoint, params=params, timeout=25)
            if r.status_code == 429 and attempt == 0:
                time.sleep(4.0)
                continue
            r.raise_for_status()
            payload = r.json()
            out = []
            for row in payload.get("articles") or []:
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
                    "query_category": None,
                    "text": title,
                })
            return out
        except Exception as exc:
            last_error = exc
            if attempt == 0:
                time.sleep(2.0)
    errors["gdelt"] = repr(last_error)
    return []


def _fetch_rss(source_id: str, cfg: dict, errors: dict) -> list[dict]:
    try:
        r = HTTP.get(cfg["url"], timeout=20)
        r.raise_for_status()
        max_age = float(cfg.get("max_age_hours", 72))
        out = []
        for item in _rss_items(r.content):
            title = _clean(item.findtext("title"))
            desc = _clean(item.findtext("description"))
            link = _clean(item.findtext("link"))
            pub = _clean(item.findtext("pubDate"))
            dt = _parse_dt(pub)
            if not title or (dt is not None and _age_hours(dt) > max_age):
                continue
            out.append({
                "title": title,
                "url": link,
                "source": source_id,
                "published_at": pub,
                "published_dt": dt,
                "origin": "official",
                "query_category": None,
                "text": f"{title} {desc}".strip(),
            })
        return out
    except Exception as exc:
        errors[f"rss:{source_id}"] = repr(exc)
        return []


def _classify(article: dict, keywords: dict) -> list[str]:
    text = article.get("text", article.get("title", ""))
    cats = []
    for category, terms in keywords.items():
        if _token_match(text, list(terms)):
            if article.get("origin") == "google_news":
                anchors = MARKET_CONTEXT.get(category, [])
                if anchors and not _token_match(text, anchors):
                    continue
            cats.append(category)
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
    source_hits: dict[str, int] = {}
    ranked = []
    for x in rows:
        age = _age_hours(x.get("published_dt"))
        decay = math.exp(-age / 18.0)
        sev = _severity(x.get("text", x["title"]))
        sources = x.get("sources", []) or ["unknown"]
        source_count = max(1, len(sources))
        confirmation = min(1.45, 1.0 + 0.12 * (source_count - 1))
        official = 1.18 if "official" in x.get("origins", []) else 1.0
        primary_source = str(sources[0])
        prior_hits = source_hits.get(primary_source, 0)
        source_diversity_penalty = 1.0 / math.sqrt(1.0 + prior_hits)
        source_hits[primary_source] = prior_hits + 1
        weight = decay * confirmation * official * source_diversity_penalty
        risk_component = max(0.0, sev) * weight
        weighted_attention += weight
        weighted_risk += risk_component
        source_names.update(sources)
        ranked.append((risk_component + 0.20 * weight, x, sev))

    # V1.3 intentionally saturates much more slowly than V1.2.  A category now
    # needs sustained, diverse coverage to reach extreme values.
    density = 100.0 * (1.0 - math.exp(-weighted_attention / 20.0))
    risk = 100.0 * (1.0 - math.exp(-weighted_risk / 10.0))
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
            "severity": round(float(sev), 3),
        })
    return {
        "score": round(float(score), 2),
        "risk_component": round(float(risk), 2),
        "attention_component": round(float(density), 2),
        "event_count": len(rows),
        "source_count": len(source_names),
        "top_events": top,
    }


def build_news_signals() -> dict:
    source_cfg = _load_json(SOURCES_PATH, {"sources": DEFAULT_SOURCES}).get("sources", DEFAULT_SOURCES)
    if isinstance(source_cfg, list):
        source_cfg = DEFAULT_SOURCES
    keywords = _load_json(KEYWORDS_PATH, DEFAULT_KEYWORDS)
    errors: dict[str, str] = {}
    rows: list[dict] = []

    google_cfg = source_cfg.get("google_news", DEFAULT_SOURCES["google_news"])
    if google_cfg.get("enabled", True):
        for category, terms in keywords.items():
            rows.extend(_fetch_google_news(category, list(terms), google_cfg, errors))

    gdelt_cfg = source_cfg.get("gdelt", DEFAULT_SOURCES["gdelt"])
    if gdelt_cfg.get("enabled", False):
        rows.extend(_fetch_gdelt(keywords, gdelt_cfg, errors))

    for source_id, cfg in source_cfg.items():
        if source_id in {"gdelt", "google_news"} or not isinstance(cfg, dict) or not cfg.get("enabled", True):
            continue
        if cfg.get("kind") == "official_rss":
            rows.extend(_fetch_rss(source_id, cfg, errors))

    classified_rows = []
    for row in rows:
        row["categories"] = _classify(row, keywords)
        if row["categories"]:
            classified_rows.append(row)
    events = _dedupe(classified_rows)

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
        "version": "NEWS-SIGNAL-V1.3",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "feeds_market_model": False,
        "policy": "News is an explanatory/context layer in V1. It does not vote in Market Model V2 until forward validation is available.",
        "source_status": {
            "configured": sorted(source_cfg.keys()),
            "query_mode": "market_context_headline_confirmed",
            "unique_sources_seen": len(all_sources),
            "article_rows_before_classification": len(rows),
            "classified_rows": len(classified_rows),
            "events_after_dedupe": len(events),
            "errors": errors,
        },
        "signals": {
            "us_policy_event_sentiment": {
                "score": policy.get("score", 0.0),
                "note": "Market-relevant U.S. policy/monetary/regulatory event risk and attention; not a score of any political person or party.",
                **{k: v for k, v in policy.items() if k != "score"},
            },
            "geopolitical_news_risk": {"score": geo.get("score", 0.0), **{k: v for k, v in geo.items() if k != "score"}},
            "systemic_news_risk": {"score": systemic.get("score", 0.0), **{k: v for k, v in systemic.items() if k != "score"}},
            "ai_narrative_risk": {"score": ai.get("score", 0.0), **{k: v for k, v in ai.items() if k != "score"}},
            "negative_narrative_density": {"score": negative.get("score", 0.0), **{k: v for k, v in negative.items() if k != "score"}},
        },
    }


if __name__ == "__main__":
    print(json.dumps(build_news_signals(), ensure_ascii=False, indent=2))
